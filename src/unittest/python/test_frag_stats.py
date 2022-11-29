import pytest

import redis

from mockito import mock, when, unstub, verify  # type: ignore
from mockito.matchers import matches, any_  # type: ignore
from hamcrest import assert_that, equal_to, not_, contains_inanyorder, contains_exactly

import minqlx
from frag_stats import frag_stats

from minqlx_plugin_test import setup_cvars, fake_player, connected_players, assert_player_was_told


class TestFragStats:
    @pytest.fixture(name="fragstats_db")
    def fragstats_db(self):
        self.plugin.database = redis.Redis  # type: ignore
        db = mock(spec=redis.StrictRedis)
        self.plugin._db_instance = db  # pylint: disable=protected-access

        when(db).zincrby(any_, any_, any_).thenReturn(None)
        when(db).zincrby(any_, any_, any_).thenReturn(None)
        when(db).set(any_, any_).thenReturn(None)
        yield db
        unstub()

    def setup_method(self):
        setup_cvars({
            "qlx_fragstats_toplimit": "10"
        })

        self.plugin = frag_stats()

    @staticmethod
    def teardown_method():
        unstub()

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_player_disconnect_records_player_name(self, fragstats_db):
        player = fake_player(123, "Disconnecting Player")

        self.plugin.handle_player_disconnect(player, "quit")

        verify(fragstats_db).set(f"minqlx:players:{player.steam_id}:last_used_name", player.name)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_game_countdown_clears_frag_log(self):
        self.plugin.frag_log = [(123, 456)]

        self.plugin.handle_game_countdown()

        assert_that(self.plugin.frag_log, equal_to([]))

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_records_frag_log_entry(self, fragstats_db):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, killer, {"MOD": "ROCKET"})

        assert_that(self.plugin.frag_log, contains_inanyorder((killer.steam_id, victim.steam_id)))  # type: ignore

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_records_soulz_in_db(self, fragstats_db):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, killer, {"MOD": "ROCKET"})

        verify(fragstats_db).zincrby(f"minqlx:players:{killer.steam_id}:soulz", 1, victim.steam_id)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_records_reaper_in_db(self, fragstats_db):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, killer, {"MOD": "ROCKET"})

        verify(fragstats_db).zincrby(f"minqlx:players:{victim.steam_id}:reaperz", 1, killer.steam_id)

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_on_own_death_does_nothing(self):
        victim = fake_player(123, "Fragged Player", team="red")

        connected_players(victim)

        self.plugin.handle_death(victim, victim, {"MOD": "ROCKET"})

        assert_that(self.plugin.frag_log, not_(contains_exactly(victim.steam_id)))  # type: ignore

    @pytest.mark.usefixtures("game_in_warmup")
    def test_handle_death_in_warmup_does_not_record_frag_log_entry(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, killer, {"MOD": "ROCKET"})

        assert_that(self.plugin.frag_log, not_(contains_inanyorder((killer.steam_id, victim.steam_id))))  # type: ignore

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_by_lava_records_frag_log_entry(self, fragstats_db):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "LAVA"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("lava", victim.steam_id)))  # type: ignore
        verify(fragstats_db).zincrby("minqlx:players:lava:soulz", 1, victim.steam_id)
        verify(fragstats_db).zincrby(f"minqlx:players:{victim.steam_id}:reaperz", 1, "lava")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_by_hurt_records_frag_log_entry(self, fragstats_db):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "HURT"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("void", victim.steam_id)))  # type: ignore
        verify(fragstats_db).zincrby("minqlx:players:void:soulz", 1, victim.steam_id)
        verify(fragstats_db).zincrby(f"minqlx:players:{victim.steam_id}:reaperz", 1, "void")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_by_slime_records_frag_log_entry(self, fragstats_db):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "SLIME"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("acid", victim.steam_id)))  # type: ignore
        verify(fragstats_db).zincrby("minqlx:players:acid:soulz", 1, victim.steam_id)
        verify(fragstats_db).zincrby(f"minqlx:players:{victim.steam_id}:reaperz", 1, "acid")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_by_water_records_frag_log_entry(self, fragstats_db):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "WATER"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("drowning", victim.steam_id)))  # type: ignore
        verify(fragstats_db).zincrby("minqlx:players:drowning:soulz", 1, victim.steam_id)
        verify(fragstats_db).zincrby(f"minqlx:players:{victim.steam_id}:reaperz", 1, "drowning")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_by_crush_records_frag_log_entry(self, fragstats_db):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "CRUSH"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("squished", victim.steam_id)))  # type: ignore
        verify(fragstats_db).zincrby("minqlx:players:squished:soulz", 1, victim.steam_id)
        verify(fragstats_db).zincrby(f"minqlx:players:{victim.steam_id}:reaperz", 1, "squished")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_by_unknown_records_frag_log_entry(self, fragstats_db):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "UNKNOWN"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("unknown", victim.steam_id)))  # type: ignore
        verify(fragstats_db).zincrby("minqlx:players:unknown:soulz", 1, victim.steam_id)
        verify(fragstats_db).zincrby(f"minqlx:players:{victim.steam_id}:reaperz", 1, "unknown")

    @pytest.mark.usefixtures("game_in_progress")
    def test_handle_death_by_team_switch_is_not_recorded(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, victim, {"MOD": "SWITCHTEAM"})

        assert_that(self.plugin.frag_log, not_(contains_inanyorder((victim.steam_id, victim.steam_id))))  # type: ignore

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_with_no_frags(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz"], mock_channel)

        mock_channel.assert_was_replied(matches("Issuing Player.* didn't reap any soulz, yet."))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_with_a_disconnected_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        disconnected_killed2 = fake_player(5, "Disconnected Killed2", team="blue")
        connected_players(player, killed1)

        self.plugin.frag_log = [
            (player.steam_id, killed1.steam_id),
            (player.steam_id, disconnected_killed2.steam_id),
            (player.steam_id, disconnected_killed2.steam_id)
        ]
        when(fragstats_db).exists(f"minqlx:players:{disconnected_killed2.steam_id}:last_used_name").thenReturn(True)
        when(fragstats_db).get(f"minqlx:players:{disconnected_killed2.steam_id}:last_used_name") \
            .thenReturn(disconnected_killed2.name)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz"], mock_channel)

        mock_channel.assert_was_replied(matches(r"Top 10 reaped soulz for Issuing Player.*: "
                                                r"Disconnected Killed2.* \(2\), Killed1.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_returns_top10(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.frag_log = [
            (player.steam_id, killed1.steam_id),
            (player.steam_id, killed2.steam_id),
            (player.steam_id, killed3.steam_id),
            (player.steam_id, killed4.steam_id),
            (player.steam_id, killed4.steam_id),
            (player.steam_id, killed3.steam_id),
            (player.steam_id, killed4.steam_id),
            (player.steam_id, killed2.steam_id),
            (player.steam_id, killed4.steam_id),
            (player.steam_id, killed3.steam_id),
            (player.steam_id, killed4.steam_id),
            (player.steam_id, killed4.steam_id),
            (player.steam_id, killed2.steam_id),
            (player.steam_id, killed1.steam_id),
            (player.steam_id, killed3.steam_id),
            (player.steam_id, killed4.steam_id),
            (player.steam_id, killed4.steam_id),
            (player.steam_id, killed3.steam_id)
        ]

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for Issuing Player.*: "
                                           r"Killed4.* \(8\), Killed3.* \(5\), Killed2.* \(3\), Killed1.* \(2\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_another_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")
        fragging_player = fake_player(456, "Fragging Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, fragging_player, killed1, killed2, killed3, killed4)

        self.plugin.frag_log = [
            (player.steam_id, killed1.steam_id),
            (fragging_player.steam_id, killed2.steam_id),
            (fragging_player.steam_id, killed2.steam_id),
            (fragging_player.steam_id, killed3.steam_id)
        ]

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "Fragging"], mock_channel)

        mock_channel.assert_was_replied(matches(r"Top 10 reaped soulz for Fragging Player.*: "
                                                r"Killed2.* \(2\), Killed3.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_another_disconnected_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragging_player = fake_player(456, "Fragging Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.frag_log = [
            (player.steam_id, killed1.steam_id),
            (fragging_player.steam_id, killed2.steam_id),
            (fragging_player.steam_id, killed2.steam_id),
            (fragging_player.steam_id, killed3.steam_id)
        ]

        when(fragstats_db).exists(f"minqlx:players:{fragging_player.steam_id}:last_used_name").thenReturn(True)
        when(fragstats_db).get(f"minqlx:players:{fragging_player.steam_id}:last_used_name") \
            .thenReturn(fragging_player.name)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", f"{fragging_player.steam_id}"], mock_channel)

        mock_channel.assert_was_replied(matches(r"Top 10 reaped soulz for Fragging Player.*: "
                                                r"Killed2.* \(2\), Killed3.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_another_nonexisting_disconnected_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragging_player = fake_player(456, "Fragging Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.frag_log = [
            (player.steam_id, killed1.steam_id),
            (fragging_player.steam_id, killed2.steam_id),
            (fragging_player.steam_id, killed2.steam_id),
            (fragging_player.steam_id, killed3.steam_id)
        ]

        when(fragstats_db).exists(f"minqlx:players:{fragging_player.steam_id}:last_used_name").thenReturn(False)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", f"{fragging_player.steam_id}"], mock_channel)

        mock_channel.assert_was_replied(any_, times=0)  # type: ignore

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_another_non_existent_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "Non-existent"], mock_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_another_non_existent_lava_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "lava"], mock_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))
        mock_channel.assert_was_replied(any_, times=0)  # type: ignore

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_more_than_one_matching_other_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "Killed"], mock_channel)

        assert_player_was_told(player, matches(".*4.* players matched.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_lava_backflips(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        self.plugin.frag_log = [
            (killer1.steam_id, player.steam_id),
            ("lava", fragged_player.steam_id),
            ("lava", fragged_player.steam_id),
            ("void", player.steam_id)
        ]

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!lava"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for lava.*: "
                                           r"Fragged Player.* \(2\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_void_deaths(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        self.plugin.frag_log = [
            (killer1.steam_id, player.steam_id),
            ("lava", fragged_player.steam_id),
            ("squished", player.steam_id),
            ("acid", fragged_player.steam_id),
            ("lava", fragged_player.steam_id),
            ("drowning", player.steam_id),
            ("unknown", fragged_player.steam_id),
            ("void", player.steam_id)
        ]

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!void"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for void.*: "
                                           r"Issuing Player.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_drowning_deaths(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        self.plugin.frag_log = [
            (killer1.steam_id, player.steam_id),
            ("lava", fragged_player.steam_id),
            ("squished", player.steam_id),
            ("acid", fragged_player.steam_id),
            ("lava", fragged_player.steam_id),
            ("drowning", player.steam_id),
            ("unknown", fragged_player.steam_id),
            ("void", player.steam_id)
        ]

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!drowning"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for drowning.*: "
                                           r"Issuing Player.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_acid_deaths(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        self.plugin.frag_log = [
            (killer1.steam_id, player.steam_id),
            ("lava", fragged_player.steam_id),
            ("squished", player.steam_id),
            ("acid", fragged_player.steam_id),
            ("lava", fragged_player.steam_id),
            ("drowning", player.steam_id),
            ("unknown", fragged_player.steam_id),
            ("void", player.steam_id)
        ]

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!acid"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for acid.*: "
                                           r"Fragged Player.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapsoulz_for_unknown_deaths(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        self.plugin.frag_log = [
            (killer1.steam_id, player.steam_id),
            ("lava", fragged_player.steam_id),
            ("squished", player.steam_id),
            ("acid", fragged_player.steam_id),
            ("lava", fragged_player.steam_id),
            ("drowning", player.steam_id),
            ("unknown", fragged_player.steam_id),
            ("void", player.steam_id)
        ]

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!unknown"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for unknown.*: "
                                           r"Fragged Player.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapreaperz_with_no_fragger(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches("Issuing Player.*'s soul was not reaped by anyone, yet."))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapreaperz_returns_top10(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        killer2 = fake_player(5, "Killer2", team="blue")
        killer3 = fake_player(6, "Killer3", team="blue")
        killer4 = fake_player(7, "Killer4", team="blue")
        connected_players(player, killer1, killer2, killer3, killer4)

        self.plugin.frag_log = [
            (killer1.steam_id, player.steam_id),
            (killer2.steam_id, player.steam_id),
            (killer3.steam_id, player.steam_id),
            (killer4.steam_id, player.steam_id),
            (killer4.steam_id, player.steam_id),
            (killer3.steam_id, player.steam_id),
            (killer4.steam_id, player.steam_id),
            (killer2.steam_id, player.steam_id),
            (killer4.steam_id, player.steam_id),
            (killer3.steam_id, player.steam_id),
            (killer4.steam_id, player.steam_id),
            (killer4.steam_id, player.steam_id),
            (killer2.steam_id, player.steam_id),
            (killer1.steam_id, player.steam_id),
            (killer3.steam_id, player.steam_id),
            (killer4.steam_id, player.steam_id),
            (killer3.steam_id, player.steam_id)
        ]

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaperz of Issuing Player.*'s soul: "
                                           r"Killer4.* \(7\), Killer3.* \(5\), Killer2.* \(3\), Killer1.* \(2\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapreaperz_for_another_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        killer2 = fake_player(5, "Killer2", team="blue")
        killer3 = fake_player(6, "Killer3", team="blue")
        killer4 = fake_player(7, "Killer4", team="blue")
        connected_players(player, fragged_player, killer1, killer2, killer3, killer4)

        self.plugin.frag_log = [
            (killer1.steam_id, player.steam_id),
            (killer2.steam_id, fragged_player.steam_id),
            (killer2.steam_id, fragged_player.steam_id),
            (killer3.steam_id, fragged_player.steam_id)
        ]

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz", "Fragged"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaperz of Fragged Player.*'s soul: "
                                           r"Killer2.* \(2\), Killer3.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapreaperz_for_another_non_existent_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz", "Non-existent"], mock_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapreaperz_for_more_than_one_matching_other_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz", "Killed"], mock_channel)

        assert_player_was_told(player, matches(".*4.* players matched.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapreaperz_with_lava_backflips(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        self.plugin.frag_log = [
            (killer1.steam_id, player.steam_id),
            ("lava", fragged_player.steam_id),
            ("lava", fragged_player.steam_id),
            ("void", fragged_player.steam_id)
        ]

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz", "Fragged"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaperz of Fragged Player.*'s soul: "
                                           r"lava.* \(2\), void.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_mapreaperz_with_a_disconnected_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        disconnected_killed2 = fake_player(5, "Disconnected Killed2", team="blue")
        connected_players(player, killed1)

        self.plugin.frag_log = [
            (killed1.steam_id, player.steam_id),
            (disconnected_killed2.steam_id, player.steam_id),
            (disconnected_killed2.steam_id, player.steam_id)
        ]
        when(fragstats_db).exists(f"minqlx:players:{disconnected_killed2.steam_id}:last_used_name").thenReturn(True)
        when(fragstats_db).get(f"minqlx:players:{disconnected_killed2.steam_id}:last_used_name") \
            .thenReturn(disconnected_killed2.name)

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaperz of Issuing Player.*'s soul: "
                                           r"Disconnected Killed2.* \(2\), Killed1.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_with_no_frags(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{player.steam_id}:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True).thenReturn([])

        self.plugin.cmd_soulz(player, ["!soulz"], mock_channel)

        mock_channel.assert_was_replied(matches("Issuing Player.* didn't reap any soulz, yet."))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_with_a_disconnected_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        disconnected_killed2 = fake_player(5, "Disconnected Killed2", team="blue")
        connected_players(player, killed1)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{player.steam_id}:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed1.steam_id, 1),
                (disconnected_killed2.steam_id, 2)
            ])
        when(fragstats_db).exists(f"minqlx:players:{disconnected_killed2.steam_id}:last_used_name").thenReturn(True)
        when(fragstats_db).get(f"minqlx:players:{disconnected_killed2.steam_id}:last_used_name") \
            .thenReturn(disconnected_killed2.name)

        self.plugin.cmd_soulz(player, ["!soulz"], mock_channel)

        mock_channel.assert_was_replied(matches(r"Top 10 reaped soulz for Issuing Player.*: "
                                                r"Disconnected Killed2.* \(2\), Killed1.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_returns_top10(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{player.steam_id}:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed1.steam_id, 2),
                (killed2.steam_id, 3),
                (killed3.steam_id, 5),
                (killed4.steam_id, 8)
            ])

        self.plugin.cmd_soulz(player, ["!soulz"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for Issuing Player.*: "
                                           r"Killed4.* \(8\), Killed3.* \(5\), Killed2.* \(3\), Killed1.* \(2\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_another_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragging_player = fake_player(456, "Fragging Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, fragging_player, killed1, killed2, killed3, killed4)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{fragging_player.steam_id}:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed2.steam_id, 2),
                (killed3.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "Fragging"], mock_channel)

        mock_channel.assert_was_replied(matches(r"Top 10 reaped soulz for Fragging Player.*: "
                                                r"Killed2.* \(2\), Killed3.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_another_disconnected_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragging_player = fake_player(456, "Fragging Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{fragging_player.steam_id}:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed2.steam_id, 2),
                (killed3.steam_id, 1)
            ])
        when(fragstats_db).exists(f"minqlx:players:{fragging_player.steam_id}:last_used_name").thenReturn(True)
        when(fragstats_db).get(f"minqlx:players:{fragging_player.steam_id}:last_used_name") \
            .thenReturn(fragging_player.name)

        self.plugin.cmd_soulz(player, ["!soulz", f"{fragging_player.steam_id}"], mock_channel)

        mock_channel.assert_was_replied(matches(r"Top 10 reaped soulz for Fragging Player.*: "
                                                r"Killed2.* \(2\), Killed3.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_another_nonexisting_disconnected_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragging_player = fake_player(456, "Fragging Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        when(fragstats_db).exists(f"minqlx:players:{fragging_player.steam_id}:last_used_name").thenReturn(False)

        self.plugin.cmd_soulz(player, ["!soulz", f"{fragging_player.steam_id}"], mock_channel)

        mock_channel.assert_was_replied(any_, times=0)  # type: ignore

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_another_non_existent_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_soulz(player, ["!soulz", "Non-existent"], mock_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_another_non_existent_lava_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_soulz(player, ["!soulz", "lava"], mock_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))
        mock_channel.assert_was_replied(any_, times=0)  # type: ignore

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_more_than_one_matching_other_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.cmd_soulz(player, ["!soulz", "Killed"], mock_channel)

        assert_player_was_told(player, matches(".*4.* players matched.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_lava_backflips(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(fragstats_db).zrevrangebyscore("minqlx:players:lava:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (fragged_player.steam_id, 2)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!lava"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for lava.*: "
                                           r"Fragged Player.* \(2\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_void_deaths(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(fragstats_db).zrevrangebyscore("minqlx:players:void:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (player.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!void"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for void.*: "
                                           r"Issuing Player.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_drowning_deaths(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(fragstats_db).zrevrangebyscore("minqlx:players:drowning:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (player.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!drowning"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for drowning.*: "
                                           r"Issuing Player.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_acid_deaths(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(fragstats_db).zrevrangebyscore("minqlx:players:acid:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (fragged_player.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!acid"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for acid.*: "
                                           r"Fragged Player.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_for_unknown_deaths(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(fragstats_db).zrevrangebyscore("minqlx:players:unknown:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (fragged_player.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!unknown"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaped soulz for unknown.*: "
                                           r"Fragged Player.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_reaperz_with_no_fragger(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{player.steam_id}:reaperz",
                                            "+INF", "-INF", start=0, num=10, withscores=True).thenReturn([])

        self.plugin.cmd_reaperz(player, ["!reaperz"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches("Issuing Player.*'s soul was not reaped by anyone, yet."))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_reaperz_returns_top10(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        killer2 = fake_player(5, "Killer2", team="blue")
        killer3 = fake_player(6, "Killer3", team="blue")
        killer4 = fake_player(7, "Killer4", team="blue")
        connected_players(player, killer1, killer2, killer3, killer4)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{player.steam_id}:reaperz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killer1.steam_id, 2),
                (killer2.steam_id, 3),
                (killer3.steam_id, 5),
                (killer4.steam_id, 7),
            ])

        self.plugin.cmd_reaperz(player, ["!reaperz"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaperz of Issuing Player.*'s soul: "
                                           r"Killer4.* \(7\), Killer3.* \(5\), Killer2.* \(3\), Killer1.* \(2\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_reaperz_for_another_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        killer2 = fake_player(5, "Killer2", team="blue")
        killer3 = fake_player(6, "Killer3", team="blue")
        killer4 = fake_player(7, "Killer4", team="blue")
        connected_players(player, fragged_player, killer1, killer2, killer3, killer4)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{fragged_player.steam_id}:reaperz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killer2.steam_id, 2),
                (killer3.steam_id, 1)
            ])

        self.plugin.cmd_reaperz(player, ["!reaperz", "Fragged"], mock_channel)

        mock_channel.assert_was_replied(
                                   matches(r"Top 10 reaperz of Fragged Player.*'s soul: "
                                           r"Killer2.* \(2\), Killer3.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_reaperz_for_another_non_existent_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_reaperz(player, ["!reaperz", "Non-existent"], mock_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_reaperz_for_more_than_one_matching_other_player(self, mock_channel):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.cmd_reaperz(player, ["!reaperz", "Killed"], mock_channel)

        assert_player_was_told(player, matches(".*4.* players matched.*"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_reaperz_with_lava_backflips(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{fragged_player.steam_id}:reaperz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                ("lava", 2),
                ("void", 1)
            ])

        self.plugin.cmd_reaperz(player, ["!reaperz", "Fragged"], mock_channel)

        mock_channel.assert_was_replied(
            matches(r"Top 10 reaperz of Fragged Player.*'s soul: "
                    r"lava.* \(2\), void.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_reaperz_with_a_disconnected_player(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")

        killer1 = fake_player(4, "Killed1", team="blue")
        disconnected_killer2 = fake_player(5, "Disconnected Killed2", team="blue")
        connected_players(player, killer1)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{player.steam_id}:reaperz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (disconnected_killer2.steam_id, 2),
                (killer1.steam_id, 1)
            ])
        when(fragstats_db).exists(f"minqlx:players:{disconnected_killer2.steam_id}:last_used_name").thenReturn(True)
        when(fragstats_db).get(f"minqlx:players:{disconnected_killer2.steam_id}:last_used_name") \
            .thenReturn(disconnected_killer2.name)

        self.plugin.cmd_reaperz(player, ["!reaperz"], mock_channel)

        mock_channel.assert_was_replied(
            matches(r"Top 10 reaperz of Issuing Player.*'s soul: "
                    r"Disconnected Killed2.* \(2\), Killed1.* \(1\)"))

    @pytest.mark.usefixtures("game_in_progress")
    def test_cmd_soulz_in_team_chat_channel(self, mock_channel, fragstats_db):
        player = fake_player(123, "Issuing Player", team="red")
        minqlx.CHAT_CHANNEL = mock_channel

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        when(fragstats_db).zrevrangebyscore(f"minqlx:players:{player.steam_id}:soulz",
                                            "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed1.steam_id, 2),
                (killed2.steam_id, 3),
                (killed3.steam_id, 5),
                (killed4.steam_id, 8)
            ])

        self.plugin.cmd_soulz(player, ["!soulz"], minqlx.RED_TEAM_CHAT_CHANNEL)

        mock_channel.assert_was_replied(
            matches(r"Top 10 reaped soulz for Issuing Player.*: "
                    r"Killed4.* \(8\), Killed3.* \(5\), Killed2.* \(3\), Killed1.* \(2\)"))
