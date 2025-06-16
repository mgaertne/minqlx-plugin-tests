import pytest

import redis

from mockito import mock, when, unstub, verify  # type: ignore
from mockito.matchers import any_, matches  # type: ignore

from minqlx_plugin_test import (
    setup_cvars,
    fake_player,
    connected_players,
    assert_plugin_sent_to_console,
)

from last_played import last_played


class TestLastPlayed:
    @pytest.fixture(name="lastplayed_db")
    def lastplayed_db(self):
        self.plugin.database = redis.Redis  # type: ignore
        db = mock(spec=redis.StrictRedis)
        self.plugin._db_instance = db

        when(db).exists(any_).thenReturn(False)
        when(db).set(any_, any_).thenReturn(None)
        when(db).hset(any_, any_, any_).thenReturn(None)
        when(db).hget(any_, any_).thenReturn(None)
        yield db
        unstub()

    def setup_method(self):
        setup_cvars({"qlx_fragstats_toplimit": "10"})

        self.plugin = last_played()

    # noinspection PyMethodMayBeStatic
    def teardown_method(self):
        unstub()

    def test_handle_stats_match_report_for_aborted_match(self, lastplayed_db):
        match_report = {
            "DATA": {"ABORTED": True, "MAP": "thunderstruck"},
            "TYPE": "MATCH_REPORT",
        }
        self.plugin.handle_stats(match_report)

        verify(lastplayed_db, times=0).set("minqlx:maps:thunderstruck:last_played", any_)

    def test_handle_stats_match_report_is_logged(self, lastplayed_db):
        match_report = {
            "DATA": {"ABORTED": False, "MAP": "thunderstruck"},
            "TYPE": "MATCH_REPORT",
        }
        self.plugin.handle_stats(match_report)

        verify(lastplayed_db).set("minqlx:maps:thunderstruck:last_played", any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_stats_player_stats_for_aborted_match(self, lastplayed_db):
        match_report = {
            "DATA": {"ABORTED": True, "WARMUP": False, "STEAM_ID": "1234"},
            "TYPE": "PLAYER_STATS",
        }
        self.plugin.handle_stats(match_report)

        verify(lastplayed_db, times=0).hset("minqlx:players:1234:last_played", any_, any_)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_stats_player_stats_for_warmup_stats(self, lastplayed_db):
        match_report = {
            "DATA": {"ABORTED": False, "WARMUP": True, "STEAM_ID": "1234"},
            "TYPE": "PLAYER_STATS",
        }
        self.plugin.handle_stats(match_report)

        verify(lastplayed_db, times=0).hset("minqlx:players:1234:last_played", any_, any_)

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_stats_player_stats_no_game_running(self, lastplayed_db):
        match_report = {
            "DATA": {"ABORTED": False, "WARMUP": False, "STEAM_ID": "1234"},
            "TYPE": "PLAYER_STATS",
        }
        self.plugin.handle_stats(match_report)

        verify(lastplayed_db, times=0).hset("minqlx:players:1234:last_played", any_, any_)

    def test_handle_stats_player_stats_is_logged(self, lastplayed_db, game_in_progress):
        game_in_progress.map = "thunderstruck"
        match_report = {
            "DATA": {"ABORTED": False, "WARMUP": False, "STEAM_ID": "1234"},
            "TYPE": "PLAYER_STATS",
        }
        self.plugin.handle_stats(match_report)

        verify(lastplayed_db).hset("minqlx:players:1234:last_played", "thunderstruck", any_)

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_game_end_no_game_running(self):
        # noinspection PyTypeChecker
        self.plugin.handle_game_end({})

        assert_plugin_sent_to_console(any_, times=0)

    def test_handle_game_end_roundlimit_not_hit(self, game_in_progress):
        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 2
        game_in_progress.blue_score = 1

        # noinspection PyTypeChecker
        self.plugin.handle_game_end({})

        assert_plugin_sent_to_console(any_, times=0)

    def test_handle_game_end_maps_not_in_last_played_and_long_mapnames(self, game_in_progress, lastplayed_db):
        setup_cvars({"nextmaps": r"\map_0\campgrounds\map_1\thunderstruck\map_2\asylum"})

        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 2
        game_in_progress.blue_score = 8

        # noinspection PyTypeChecker
        self.plugin.handle_game_end({})

        assert_plugin_sent_to_console(matches(".*VOTE.*"))
        assert_plugin_sent_to_console(matches(".*campgrounds.*thunderstruck.*asylum.*"))

    def test_handle_game_end_maps_in_last_played_and_long_mapnames(self, game_in_progress, lastplayed_db):
        setup_cvars({"nextmaps": r"\map_0\ct3_20b2\map_1\ra3fusy1d\map_2\ra3azra1"})

        when(lastplayed_db).exists("minqlx:maps:longnames").thenReturn(True)
        when(lastplayed_db).hgetall("minqlx:maps:longnames").thenReturn(
            {"ra3fusy1d": "Let Chaos Entwine", "ct3_20b2": "La Petite"}
        )
        when(lastplayed_db).exists("minqlx:maps:ct3_20b2:last_played").thenReturn(False)
        when(lastplayed_db).exists("minqlx:maps:ra3fusy1d:last_played").thenReturn(True)
        when(lastplayed_db).get("minqlx:maps:ra3fusy1d:last_played").thenReturn("20230928010203+0000")
        when(lastplayed_db).exists("minqlx:maps:ra3azra1:last_played").thenReturn(True)
        when(lastplayed_db).get("minqlx:maps:ra3azra1:last_played").thenReturn("20230930010203+0000")

        game_in_progress.roundlimit = 8
        game_in_progress.red_score = 2
        game_in_progress.blue_score = 8

        # noinspection PyTypeChecker
        self.plugin.handle_game_end({})

        assert_plugin_sent_to_console(matches(".*VOTE.*"))
        assert_plugin_sent_to_console(
            matches(
                r"\^\d1: \^\dLa Petite \^\d\(\^\dct3_20b2\^\d\) "
                r"\^\d2: \^\dLet Chaos Entwine \^\d\(\^\dra3fusy1d\^\d, last played .* ago\) "
                r"\^\d3: \^\dra3azra1 \^\d\(last played .* ago\)"
            )
        )

    @pytest.mark.usefixtures("no_minqlx_game")
    def test_handle_last_played_no_game_running(self, lastplayed_db, mock_channel):
        when(lastplayed_db).exists("minqlx:maps:campgrounds:last_played").thenReturn(False)

        player = fake_player(name="FakePlayer", steam_id=1234)
        connected_players(player)

        self.plugin.cmd_last_played(player, ["!last_played"], mock_channel)

        mock_channel.assert_was_replied(any_, times=0)

    def test_handle_last_played_map_never_logged_as_played(self, lastplayed_db, game_in_warmup, mock_channel):
        game_in_warmup.map = "campgrounds"
        when(lastplayed_db).exists("minqlx:maps:campgrounds:last_played").thenReturn(False)

        player = fake_player(name="FakePlayer", steam_id=1234)
        connected_players(player)

        self.plugin.cmd_last_played(player, ["!last_played"], mock_channel)

        mock_channel.assert_was_replied(matches("I don't know when map .*campgrounds.* was played the last time."))

    def test_handle_last_played_player_never_played_on_map(self, lastplayed_db, game_in_warmup, mock_channel):
        game_in_warmup.map = "campgrounds"
        when(lastplayed_db).exists("minqlx:maps:campgrounds:last_played").thenReturn(True)
        when(lastplayed_db).get("minqlx:maps:campgrounds:last_played").thenReturn("20230928010203+0000")
        when(lastplayed_db).exists("minqlx:players:1234:last_played").thenReturn(True)
        when(lastplayed_db).hget("minqlx:players:1234:last_played", "campgrounds").thenReturn(None)

        player = fake_player(name="FakePlayer", steam_id=1234)
        connected_players(player)

        self.plugin.cmd_last_played(player, ["!last_played"], mock_channel)

        mock_channel.assert_was_replied(matches("Map .*campgrounds.* was last played .* ago here."))

    def test_handle_last_played_player_never_played_on_any_map(self, lastplayed_db, game_in_warmup, mock_channel):
        game_in_warmup.map = "campgrounds"
        when(lastplayed_db).exists("minqlx:maps:campgrounds:last_played").thenReturn(True)
        when(lastplayed_db).get("minqlx:maps:campgrounds:last_played").thenReturn("20230928010203+0000")
        when(lastplayed_db).exists("minqlx:players:1234:last_played").thenReturn(False)

        player = fake_player(name="FakePlayer", steam_id=1234)
        connected_players(player)

        self.plugin.cmd_last_played(player, ["!last_played"], mock_channel)

        mock_channel.assert_was_replied(matches("Map .*campgrounds.* was last played .* ago here."))

    def test_handle_last_played_player_played_on_map(self, lastplayed_db, game_in_warmup, mock_channel):
        game_in_warmup.map = "campgrounds"
        when(lastplayed_db).exists("minqlx:maps:campgrounds:last_played").thenReturn(True)
        when(lastplayed_db).get("minqlx:maps:campgrounds:last_played").thenReturn("20230928010203+0000")
        when(lastplayed_db).exists("minqlx:players:1234:last_played").thenReturn(True)
        when(lastplayed_db).hget("minqlx:players:1234:last_played", "campgrounds").thenReturn("20230921010203+0000")

        player = fake_player(name="FakePlayer", steam_id=1234)
        connected_players(player)

        self.plugin.cmd_last_played(player, ["!last_played"], mock_channel)

        mock_channel.assert_was_replied(
            matches("Map .*campgrounds.* was last played .* ago here. You played on it .* ago.")
        )

    def test_handle_last_played_player_played_on_map_at_last_played_time(
        self, lastplayed_db, game_in_warmup, mock_channel
    ):
        game_in_warmup.map = "campgrounds"
        when(lastplayed_db).exists("minqlx:maps:campgrounds:last_played").thenReturn(True)
        when(lastplayed_db).get("minqlx:maps:campgrounds:last_played").thenReturn("20230928010203+0000")
        when(lastplayed_db).exists("minqlx:players:1234:last_played").thenReturn(True)
        when(lastplayed_db).hget("minqlx:players:1234:last_played", "campgrounds").thenReturn("20230928010258+0000")

        player = fake_player(name="FakePlayer", steam_id=1234)
        connected_players(player)

        self.plugin.cmd_last_played(player, ["!last_played"], mock_channel)

        mock_channel.assert_was_replied(matches("Map .*campgrounds.* was last played .* ago here. So did you."))

    def test_handle_last_played_with_provided_mapname(self, lastplayed_db, game_in_warmup, mock_channel):
        game_in_warmup.map = "campgrounds"
        when(lastplayed_db).exists("minqlx:maps:thunderstruck:last_played").thenReturn(True)
        when(lastplayed_db).get("minqlx:maps:thunderstruck:last_played").thenReturn("20230928010203+0000")
        when(lastplayed_db).exists("minqlx:players:1234:last_played").thenReturn(True)
        when(lastplayed_db).hget("minqlx:players:1234:last_played", "thunderstruck").thenReturn("20230921010203+0000")

        player = fake_player(name="FakePlayer", steam_id=1234)
        connected_players(player)

        self.plugin.cmd_last_played(player, ["!last_played", "thunderstruck"], mock_channel)

        mock_channel.assert_was_replied(
            matches("Map .*thunderstruck.* was last played .* ago here. You played on it .* ago.")
        )

    def test_handle_last_played_with_provided_mapname_and_longname(self, lastplayed_db, game_in_warmup, mock_channel):
        game_in_warmup.map = "campgrounds"
        when(lastplayed_db).exists("minqlx:maps:longnames").thenReturn(True)
        when(lastplayed_db).hgetall("minqlx:maps:longnames").thenReturn({"ra3fusy1d": "Let Chaos Entwine"})
        when(lastplayed_db).exists("minqlx:maps:ra3fusy1d:last_played").thenReturn(True)
        when(lastplayed_db).get("minqlx:maps:ra3fusy1d:last_played").thenReturn("20230928010203+0000")
        when(lastplayed_db).exists("minqlx:players:1234:last_played").thenReturn(True)
        when(lastplayed_db).hget("minqlx:players:1234:last_played", "ra3fusy1d").thenReturn("20230921010203+0000")

        player = fake_player(name="FakePlayer", steam_id=1234)
        connected_players(player)

        self.plugin.cmd_last_played(player, ["!last_played", "ra3fusy1d"], mock_channel)

        mock_channel.assert_was_replied(
            matches("Map .*Let Chaos Entwine.*(ra3fusy1d.*).* was last played .* ago here. You played on it .* ago.")
        )

    def test_handle_last_played_with_provided_mapname_and_longname_not_in_lookup(
        self, lastplayed_db, game_in_warmup, mock_channel
    ):
        game_in_warmup.map = "campgrounds"
        when(lastplayed_db).exists("minqlx:maps:longnames").thenReturn(True)
        when(lastplayed_db).hgetall("minqlx:maps:longnames").thenReturn({"ra3fusy1d": "Let Chaos Entwine"})
        when(lastplayed_db).exists("minqlx:maps:ethra3map1:last_played").thenReturn(True)
        when(lastplayed_db).get("minqlx:maps:ethra3map1:last_played").thenReturn("20230928010203+0000")
        when(lastplayed_db).exists("minqlx:players:1234:last_played").thenReturn(True)
        when(lastplayed_db).hget("minqlx:players:1234:last_played", "ethra3map1").thenReturn("20230921010203+0000")

        player = fake_player(name="FakePlayer", steam_id=1234)
        connected_players(player)

        self.plugin.cmd_last_played(player, ["!last_played", "ethra3map1"], mock_channel)

        mock_channel.assert_was_replied(
            matches("Map .*ethra3map1.* was last played .* ago here. You played on it .* ago.")
        )
