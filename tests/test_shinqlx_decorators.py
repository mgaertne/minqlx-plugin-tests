import pytest
from minqlx_plugin_test import (
    connected_players,
    fake_player,
    mocked_channel,
    register_decorated_handlers,
    setup_cvar,
)
from mockito import any_, verify, when2

import minqlx
import shinqlx


class DecoratedPlugin(shinqlx.Plugin):
    def __init__(self):
        super().__init__()
        self.calls = []

    @shinqlx.command("add", args=(int, str), min_args=1)
    def cmd_add(self, player, msg, channel, amount, name="nobody"):
        self.calls.append((amount, name))

    @shinqlx.command("ratio", args=(float,), usage="<value>")
    def cmd_ratio(self, player, msg, channel, value):
        self.calls.append(value)

    @shinqlx.command("kickit", args=(shinqlx.Player,))
    def cmd_kickit(self, player, msg, channel, target):
        self.calls.append(target)

    @shinqlx.command("ingame")
    @shinqlx.game(state="in_progress", message="not now")
    def cmd_ingame(self, player, msg, channel):
        self.calls.append("ingame")
        return minqlx.RET_NONE

    @shinqlx.game(state=("warmup", "countdown"))
    @shinqlx.hook("round_end", minqlx.PRI_LOW)
    def handle_round_end(self, data):
        self.calls.append("round_end")
        return minqlx.RET_STOP


@pytest.fixture
def plugin():
    instance = DecoratedPlugin()
    register_decorated_handlers(instance)
    return instance


def handler_of(plugin, name):
    return next(command.handler for command in plugin.commands if name in command.name)


def test_hooks_are_registered_with_their_priority(plugin):
    event, _, priority = plugin.hooks[0]

    assert (event, priority) == ("round_end", minqlx.PRI_LOW)


def test_command_parses_arguments(plugin):
    handler_of(plugin, "add")(fake_player(1, "A"), ["!add", "+5", "bob", "ignored"], mocked_channel())

    assert plugin.calls == [(5, "bob")]


def test_command_leaves_optional_arguments_at_their_defaults(plugin):
    handler_of(plugin, "add")(fake_player(1, "A"), ["!add", "7"], mocked_channel())

    assert plugin.calls == [(7, "nobody")]


@pytest.mark.parametrize("words", [[], ["5.0"], ["abc"], ["9223372036854775808"], ["1_0"]])
def test_command_returns_usage_for_unparsable_integers(plugin, words):
    result = handler_of(plugin, "add")(fake_player(1, "A"), ["!add", *words], mocked_channel())

    assert result == minqlx.RET_USAGE
    assert plugin.calls == []


@pytest.mark.parametrize(("word", "expected"), [("1.5", 1.5), (".5", 0.5), ("-2e2", -200.0), ("+3", 3.0)])
def test_command_parses_floats(plugin, word, expected):
    handler_of(plugin, "ratio")(fake_player(1, "A"), ["!ratio", word], mocked_channel())

    assert plugin.calls == [expected]


@pytest.mark.parametrize("word", ["nan", "inf", "1_0", "1e999"])
def test_command_rejects_non_finite_or_foreign_floats(plugin, word):
    result = handler_of(plugin, "ratio")(fake_player(1, "A"), ["!ratio", word], mocked_channel())

    assert result == minqlx.RET_USAGE


def test_command_resolves_players_and_reports_unknown_ones(plugin):
    target = fake_player(1234567, "Target", _id=3)
    connected_players(target)
    when2(minqlx.Plugin.player, "Target").thenReturn(target)
    channel = mocked_channel()

    assert handler_of(plugin, "kickit")(fake_player(1, "A"), ["!kickit", "Target"], channel) is None
    assert handler_of(plugin, "kickit")(fake_player(1, "A"), ["!kickit", "Nobody"], channel) == minqlx.RET_USAGE
    assert plugin.calls == [target]


def test_usage_is_built_from_parameter_names(plugin):
    usages = {command.name[0]: command.usage for command in plugin.commands}

    assert usages == {"add": "<amount> [name]", "ratio": "<value>", "kickit": "<target>", "ingame": ""}


def test_game_command_runs_in_the_required_state(plugin, game_in_progress):
    handler_of(plugin, "ingame")(fake_player(1, "A"), ["!ingame"], mocked_channel())

    assert plugin.calls == ["ingame"]


def test_game_command_replies_the_message_in_the_wrong_state(plugin, game_in_warmup):
    channel = mocked_channel()

    result = handler_of(plugin, "ingame")(fake_player(1, "A"), ["!ingame"], channel)

    assert result is None
    assert plugin.calls == []
    verify(channel).reply("not now")


def test_game_command_stays_silent_without_a_game(plugin, no_minqlx_game):
    channel = mocked_channel()

    handler_of(plugin, "ingame")(fake_player(1, "A"), ["!ingame"], channel)

    assert plugin.calls == []


def test_game_hook_returns_none_instead_of_stopping_in_the_wrong_state(plugin, game_in_progress):
    _, handler, _ = plugin.hooks[0]

    assert handler({}) is None
    assert plugin.calls == []


def test_game_hook_runs_in_one_of_its_states(plugin, game_in_countdown):
    _, handler, _ = plugin.hooks[0]

    assert handler({}) == minqlx.RET_STOP


@pytest.mark.parametrize(
    ("state", "error"),
    [("finished", ValueError), ([], ValueError), (3, TypeError), (["warmup", 1], TypeError)],
)
def test_game_rejects_invalid_states(state, error):
    with pytest.raises(error):
        shinqlx.game(state=state)


def test_game_twice_on_the_same_method_is_rejected():
    def method(self):
        pass

    with pytest.raises(TypeError):
        shinqlx.game()(shinqlx.game()(method))


class GuardedPlugin(shinqlx.Plugin):
    def __init__(self):
        super().__init__()
        self.calls = []

    @shinqlx.game(state="in_progress", message="not now")
    def on_event(self, player, msg, channel=None):
        self.calls.append(msg)
        return "ran"

    @shinqlx.command("guarded", args=(int,))
    @shinqlx.game(state="in_progress", message="not now")
    def cmd_guarded(self, player, msg, channel, amount):
        self.calls.append(amount)


def test_game_guards_methods_without_registration(game_in_warmup):
    guarded = GuardedPlugin()

    assert guarded.on_event(fake_player(1, "A"), "text") is None
    assert GuardedPlugin.on_event(guarded, fake_player(1, "A"), "text") is None
    assert guarded.calls == []


def test_game_lets_directly_called_methods_run_in_the_right_state(game_in_progress):
    guarded = GuardedPlugin()

    assert guarded.on_event(fake_player(1, "A"), "text") == "ran"


def test_game_replies_only_when_called_like_a_command(game_in_warmup):
    guarded = GuardedPlugin()
    channel = mocked_channel()

    guarded.on_event(fake_player(1, "A"), "text", channel)
    verify(channel, times=0).reply(any_)
    guarded.on_event(fake_player(1, "A"), ["!x"], channel)

    verify(channel).reply("not now")


def test_game_guard_wins_over_argument_parsing(game_in_warmup):
    guarded = GuardedPlugin()
    register_decorated_handlers(guarded)
    channel = mocked_channel()

    result = handler_of(guarded, "guarded")(fake_player(1, "A"), ["!guarded", "abc"], channel)

    assert result is None
    verify(channel).reply("not now")


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"args": "int"}, TypeError),
        ({"args": (list,)}, ValueError),
        ({"min_args": 1}, TypeError),
        ({"args": (int,), "min_args": 2}, ValueError),
    ],
)
def test_command_rejects_invalid_arguments(kwargs, error):
    with pytest.raises(error):
        shinqlx.command("x", **kwargs)


def test_command_rejects_methods_that_cannot_take_the_parsed_arguments():
    def method(self, player, msg, channel):
        pass

    with pytest.raises(TypeError):
        shinqlx.command("x", args=(int,))(method)


@pytest.mark.parametrize(
    ("value", "kind", "expected"),
    [
        ("2, 4 ,6", list, ["2", "4", "6"]),
        ("a,,b", list, ["a", "", "b"]),
        ("a, a ,b", set, {"a", "b"}),
        ("x , y", tuple, ("x", "y")),
        ("", list, []),
        ("  ", set, set()),
        (" ", tuple, ()),
    ],
)
def test_collection_cvars_are_stripped_and_empty_values_give_empty_collections(value, kind, expected):
    setup_cvar("qlx_values", value)

    assert shinqlx.Plugin.get_cvar("qlx_values", kind) == expected
