"""Synthetic history tests: no plugin import, chat data, Redis, or API connection."""

import ast
from datetime import datetime, timezone
from pathlib import Path
import re
from types import SimpleNamespace
from typing import List
import unittest


def isolated_history_logic(tokenizer):
    path = Path(__file__).resolve().parents[1] / "src/experimental/openai_bot.py"
    tree = ast.parse(path.read_bytes(), filename=str(path))
    constants = {"CHAT_BOT_LOG", "_CHAT_HISTORY_BATCH_SIZE", "_REPLY_PRIMING_TOKENS"}
    functions = {"_token_encoding", "_message_token_count", "num_tokens_from_messages"}
    definitions: List[ast.stmt] = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id in constants for target in node.targets)
        )
        or (isinstance(node, ast.FunctionDef) and node.name in functions)
    ]
    plugin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "openai_bot")
    methods: List[ast.stmt] = [
        node
        for node in plugin.body
        if isinstance(node, ast.FunctionDef) and node.name in {"_recent_chat_history", "contextualized_chat_history"}
    ]
    if len(definitions) != 6 or len(methods) != 2:
        raise AssertionError("Expected isolated history definitions")
    isolated_class = ast.parse("class HistoryLogic: pass").body[0]
    assert isinstance(isolated_class, ast.ClassDef)
    isolated_class.body = methods
    definitions.append(isolated_class)
    namespace = {
        "tiktoken": tokenizer,
        "datetime": datetime,
        "timezone": timezone,
        "Plugin": SimpleNamespace(clean_text=lambda text: re.sub(r"\^[0-9]", "", text)),
    }
    module = ast.Module(body=definitions, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
    return namespace


class FakeEncoding:
    def __init__(self):
        self.encoded_values = []

    def encode(self, value):
        self.encoded_values.append(value)
        return value.encode("utf-8")


class FakeTokenizer:
    def __init__(self):
        self.encoding = FakeEncoding()
        self.model_lookups = []
        self.fallbacks = []

    def encoding_for_model(self, model):
        self.model_lookups.append(model)
        if model == "unknown":
            raise KeyError(model)
        return self.encoding

    def get_encoding(self, name):
        self.fallbacks.append(name)
        return self.encoding


class FakeRedis:
    def __init__(self, entries=()):
        self.history = dict(entries)
        self.reads = []
        self.removals = []

    def zrevrange(self, key, start, stop, *, withscores=False):
        if key != "minqlx:openai_bot:log" or not withscores or stop < start:
            raise AssertionError("Unexpected history read")
        ordered = sorted(self.history.items(), key=lambda item: (item[1], item[0]), reverse=True)
        batch = ordered[start : stop + 1]
        self.reads.append((start, stop, len(batch)))
        return batch

    def zrangebyscore(self, *args, **kwargs):
        raise AssertionError("Unbounded history read is not allowed")

    def zscore(self, *args, **kwargs):
        raise AssertionError("Scores should come from the batch read")

    def zremrangebyscore(self, key, minimum, maximum):
        if key != "minqlx:openai_bot:log" or minimum != "-INF":
            raise AssertionError("Unexpected history removal")
        self.removals.append(maximum)
        self.history = {message: score for message, score in self.history.items() if score > maximum}


class OpenAiHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tokenizer = FakeTokenizer()
        self.logic = isolated_history_logic(self.tokenizer)
        self.plugin = self.logic["HistoryLogic"]()
        self.plugin.db = FakeRedis()
        self.plugin.bot_name = "^1Bob"
        self.plugin.model = "synthetic-model"
        self.plugin.max_chat_history_tokens = 1000000
        self.plugin.extended_logging = False
        self.plugin.current_game_state = lambda: "warmup"
        self.plugin.system_context = "System {bot_name} {game_state}"
        self.request = "Human: request"
        self.system = {"role": "system", "content": "System Bob warmup"}
        self.user = {"role": "user", "content": self.request}
        self.base_tokens = 2 + 4 + len("system") + len(self.system["content"]) + 4 + len("user") + len(self.request)

    def context(self, trigger=None):
        return self.plugin.contextualized_chat_history(self.request, trigger_template=trigger)

    def test_empty_history_preserves_request_without_tokenizing_or_trimming(self):
        self.plugin.max_chat_history_tokens = 1

        self.assertEqual(self.context(), [self.system, self.user])
        self.assertEqual(self.plugin.db.reads, [(0, 31, 0)])
        self.assertEqual(self.plugin.db.removals, [])
        self.assertEqual(self.tokenizer.model_lookups, [])

    def test_roles_order_and_formatted_trigger_are_preserved(self):
        self.plugin.db = FakeRedis([("Ada: old", 1), ("Bob: reply", 2), ("Lin: new", 3)])

        self.assertEqual(
            self.context("Round {game_state} with {bot_name}"),
            [
                self.system,
                {"role": "user", "content": "Ada: old"},
                {"role": "assistant", "content": "Bob: reply"},
                {"role": "user", "content": "Lin: new"},
                {"role": "user", "content": "Round warmup with Bob"},
                self.user,
            ],
        )

    def test_blank_trigger_is_omitted(self):
        self.plugin.db = FakeRedis([("Ada: old", 1)])
        self.assertEqual(
            self.context("  "),
            [
                self.system,
                {"role": "user", "content": "Ada: old"},
                self.user,
            ],
        )

    def test_full_initial_context_trims_without_adding_history(self):
        for limit in (self.base_tokens - 1, self.base_tokens):
            with self.subTest(limit=limit):
                self.plugin.db = FakeRedis([("old", 1), ("new", 2)])
                self.plugin.max_chat_history_tokens = limit
                self.assertEqual(self.context(), [self.system, self.user])
                self.assertEqual(self.plugin.db.removals, [2])
                self.assertEqual(self.plugin.db.history, {})

    def test_exact_limit_after_newest_message_preserves_trim_boundary(self):
        self.plugin.db = FakeRedis([("oldest", 1), ("middle", 2), ("newest", 3)])
        self.plugin.max_chat_history_tokens = self.base_tokens + 4 + len("user") + len("newest")

        self.assertEqual(
            self.context(),
            [
                self.system,
                {"role": "user", "content": "newest"},
                self.user,
            ],
        )
        self.assertEqual(self.plugin.db.removals, [2])
        self.assertEqual(self.plugin.db.history, {"newest": 3})

    def test_pre_append_limit_rule_still_allows_last_message_to_cross_limit(self):
        newest = "a long synthetic message"
        self.plugin.db = FakeRedis([("old", 1), (newest, 2)])
        self.plugin.max_chat_history_tokens = self.base_tokens + 1

        self.assertEqual(
            self.context(),
            [
                self.system,
                {"role": "user", "content": newest},
                self.user,
            ],
        )
        self.assertEqual(self.plugin.db.removals, [1])

    def test_exhausted_history_does_not_add_an_extra_limit_check(self):
        newest = "a long final synthetic message"
        self.plugin.db = FakeRedis([(newest, 1)])
        self.plugin.max_chat_history_tokens = self.base_tokens + 1

        self.assertEqual(
            self.context(),
            [
                self.system,
                {"role": "user", "content": newest},
                self.user,
            ],
        )
        self.assertEqual(self.plugin.db.removals, [])
        self.assertNotIn(newest, self.tokenizer.encoding.encoded_values)

    def test_multiple_batches_keep_order_and_count_each_message_at_most_once(self):
        entries = [(f"record-{index:03d}", index) for index in range(95)]
        self.plugin.db = FakeRedis(entries)

        result = self.context()

        self.assertEqual(
            result, [self.system] + [{"role": "user", "content": message} for message, _score in entries] + [self.user]
        )
        self.assertEqual(self.plugin.db.reads, [(0, 31, 32), (32, 63, 32), (64, 95, 31)])
        self.assertEqual(self.tokenizer.model_lookups, ["synthetic-model"])
        encoded = self.tokenizer.encoding.encoded_values
        self.assertEqual(encoded.count(self.system["content"]), 1)
        self.assertEqual(encoded.count(self.request), 1)
        for message, _score in entries:
            self.assertLessEqual(encoded.count(message), 1)
        self.assertEqual(len(encoded), 2 * (95 - 1 + 2))
        self.assertEqual(self.plugin.db.removals, [])

    def test_full_final_batch_only_requires_one_empty_end_probe(self):
        self.plugin.db = FakeRedis([(f"message-{index:02d}", index) for index in range(32)])
        result = self.context()
        self.assertEqual(len(result), 34)
        self.assertEqual(self.plugin.db.reads, [(0, 31, 32), (32, 63, 0)])
        self.assertEqual(self.plugin.db.removals, [])

    def test_limit_at_batch_edge_uses_the_first_excluded_score(self):
        self.plugin.db = FakeRedis([(f"m{index:03d}", index) for index in range(65)])
        self.plugin.max_chat_history_tokens = self.base_tokens + 32 * (4 + len("user") + 4)

        result = self.context()

        self.assertEqual([message["content"] for message in result[1:-1]], [f"m{index:03d}" for index in range(33, 65)])
        self.assertEqual(self.plugin.db.reads, [(0, 31, 32), (32, 63, 32)])
        self.assertEqual(self.plugin.db.removals, [32])

    def test_equal_scores_across_batches_do_not_skip_or_duplicate_messages(self):
        entries = [(f"same-time-{index:03d}", 7) for index in range(70)]
        self.plugin.db = FakeRedis(reversed(entries))

        result = self.context()

        self.assertEqual([message["content"] for message in result[1:-1]], [message for message, _score in entries])
        self.assertEqual(len(self.plugin.db.reads), 3)

    def test_existing_inclusive_trim_of_equal_scores_is_preserved(self):
        self.plugin.db = FakeRedis([("a", 99), ("b", 99), ("c", 99)])
        self.plugin.max_chat_history_tokens = self.base_tokens + 4 + len("user") + 1

        self.assertEqual(
            self.context(),
            [
                self.system,
                {"role": "user", "content": "c"},
                self.user,
            ],
        )
        self.assertEqual(self.plugin.db.removals, [99])
        self.assertEqual(self.plugin.db.history, {})

    def test_small_budget_reads_only_one_batch_of_large_history(self):
        self.plugin.db = FakeRedis([(f"record-{index:05d}", index) for index in range(10000)])
        self.plugin.max_chat_history_tokens = self.base_tokens + 1

        self.assertEqual(self.context()[1], {"role": "user", "content": "record-09999"})
        self.assertEqual(self.plugin.db.reads, [(0, 31, 32)])
        self.assertEqual(self.plugin.db.removals, [9998])

    def test_unknown_model_uses_existing_encoding_fallback_once(self):
        self.plugin.model = "unknown"
        self.plugin.db = FakeRedis([("Ada: old", 1), ("Bob: reply", 2)])

        self.context()

        self.assertEqual(self.tokenizer.model_lookups, ["unknown"])
        self.assertEqual(self.tokenizer.fallbacks, ["cl100k_base"])

    def test_token_helper_preserves_name_adjustment_and_unicode(self):
        count = self.logic["num_tokens_from_messages"]
        self.assertEqual(count([{"role": "user", "content": "Hi", "name": "Ann"}]), 14)
        self.assertEqual(count([{"role": "user", "content": "ä🐢"}]), 16)
        self.assertEqual(count([]), 2)

    def test_failure_on_later_batch_does_not_return_partial_context_or_trim(self):
        class FailingRedis(FakeRedis):
            def zrevrange(self, key, start, stop, *, withscores=False):
                if start:
                    raise RuntimeError("synthetic read failure")
                return super().zrevrange(key, start, stop, withscores=withscores)

        self.plugin.db = FailingRedis([(f"record-{index:03d}", index) for index in range(50)])

        with self.assertRaisesRegex(RuntimeError, "synthetic read failure"):
            self.context()
        self.assertEqual(self.plugin.db.removals, [])


if __name__ == "__main__":
    unittest.main()
