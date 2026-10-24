from types import SimpleNamespace

import minqlx
from experimental import openai_bot as openai_module
from experimental.openai_bot import openai_bot


def test_openai_response_cleanup_removes_attribution_and_quotes():
    assert openai_bot._cleanup_choice('Bob: "Hello"') == "Hello"
    assert openai_bot._cleanup_choice("") is None
    assert openai_bot._cleanup_choice("A: B: answer") == "answer"


def test_openai_pick_choice_strips_last_choice():
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="  answer  "))])

    assert openai_bot._pick_choice(completion) == "answer"


def test_openai_trigger_detection_is_case_insensitive():
    plugin = openai_bot.__new__(openai_bot)
    plugin.bot_triggers = ["quake"]
    plugin.bot_name = "Bob"

    assert plugin.is_triggered_message("hello QUake")
    assert plugin.is_triggered_message("Bob, answer this")
    assert not plugin.is_triggered_message("ordinary message")


def test_openai_team_status_reports_players_and_bot(monkeypatch):
    plugin = openai_bot.__new__(openai_bot)
    plugin.bot_name = "Bob"
    plugin.map_authors_cache = {}
    player = SimpleNamespace(clean_name="Player", team="red", stats=SimpleNamespace(damage_dealt=42))
    game = SimpleNamespace(state="in_progress", map="camp", map_title="Camp", factory_title="CA")
    monkeypatch.setattr(minqlx, "Game", lambda: game)
    monkeypatch.setattr(minqlx.Plugin, "teams", classmethod(lambda cls: {"red": [player], "blue": [], "spectator": []}))
    monkeypatch.setattr(minqlx.Plugin, "clean_text", classmethod(lambda cls, text: text))

    assert "Player|red|42" in plugin.team_status()
    assert "Bob|spectator|0" in plugin.team_status()
    assert "Current map: Camp" in plugin.current_game_state()


def test_openai_text_cleanup_applies_emoji_and_database_replacements():
    plugin = openai_bot.__new__(openai_bot)

    class Database:
        def exists(self, key):
            return key == "minqlx:openai_bot:message_replacements"

        def hgetall(self, _key):
            return {"bad": "good"}

    plugin._db_instance = Database()
    plugin.database = Database

    assert plugin._ql_cleaned_up("bad :smile:") == "good :smile:"


def test_openai_role_template_and_recent_connection_cleanup():
    plugin = openai_bot.__new__(openai_bot)
    plugin.bot_role_chat = "chat role"
    plugin.recently_connected_steam_ids = {123}

    assert plugin.get_role_template("chat") == "chat role"
    assert 123 in plugin.recently_connected_steam_ids


def test_openai_token_count_and_encoding_fallback(monkeypatch):
    class Encoding:
        def encode(self, value):
            return list(value)

    monkeypatch.setattr(openai_module.tiktoken, "encoding_for_model", lambda _model: Encoding())
    assert openai_module.num_tokens_from_messages([{"role": "user", "content": "hi"}]) == 12

    monkeypatch.setattr(openai_module.tiktoken, "encoding_for_model", lambda _model: (_ for _ in ()).throw(KeyError()))
    monkeypatch.setattr(openai_module.tiktoken, "get_encoding", lambda _name: Encoding())
    assert openai_module.num_tokens_from_messages([{"role": "user", "name": "a"}]) == 10
