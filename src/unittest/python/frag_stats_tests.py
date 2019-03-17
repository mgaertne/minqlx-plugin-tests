from minqlx_plugin_test import *

from redis import Redis, StrictRedis

import unittest

from mockito import *
from mockito.matchers import *
from hamcrest import *

from frag_stats import *


class FragStatsTests(unittest.TestCase):

    def setUp(self):
        setup_plugin()
        setup_cvars({
            "qlx_fragstats_toplimit": "10"
        })
        setup_game_in_progress()

        self.plugin = frag_stats()
        self.reply_channel = mocked_channel()

        self.plugin.database = Redis
        self.db = mock(StrictRedis)
        self.plugin._db_instance = self.db

        when(self.db).zincrby(any, any, any).thenReturn(None)
        when(self.db).zincrby(any, any, any).thenReturn(None)
        when(self.db).set(any, any).thenReturn(None)

    def tearDown(self):
        unstub()

    def test_handle_player_disconnect_records_player_name(self):
        player = fake_player(123, "Disconnecting Player")

        self.plugin.handle_player_disconnect(player, "quit")

        verify(self.db).set("minqlx:players:{}:last_used_name".format(player.steam_id),
                            player.name)

    def test_handle_game_countdown_clears_frag_log(self):
        self.plugin.frag_log = [(123, 456)]

        self.plugin.handle_game_countdown()

        assert_that(self.plugin.frag_log, is_([]))

    def test_handle_death_records_frag_log_entry(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, killer, {"MOD": "ROCKET"})

        assert_that(self.plugin.frag_log, contains_inanyorder((killer.steam_id, victim.steam_id)))

    def test_handle_death_records_soulz_in_db(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, killer, {"MOD": "ROCKET"})

        verify(self.db).zincrby("minqlx:players:{}:soulz".format(killer.steam_id), victim.steam_id, 1)

    def test_handle_death_records_reaper_in_db(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, killer, {"MOD": "ROCKET"})

        verify(self.db).zincrby("minqlx:players:{}:reaperz".format(victim.steam_id), killer.steam_id, 1)

    def test_handle_death_on_own_death_does_nothing(self):
        victim = fake_player(123, "Fragged Player", team="red")

        connected_players(victim)

        self.plugin.handle_death(victim, victim, {"MOD": "ROCKET"})

        assert_that(self.plugin.frag_log, not_(contains(victim.steam_id)))

    def test_handle_death_in_warmup_does_not_record_frag_log_entry(self):
        setup_game_in_warmup()

        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, killer, {"MOD": "ROCKET"})

        assert_that(self.plugin.frag_log, not_(contains_inanyorder((killer.steam_id, victim.steam_id))))

    def test_handle_death_by_lava_records_frag_log_entry(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "LAVA"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("lava", victim.steam_id)))
        verify(self.db).zincrby("minqlx:players:lava:soulz", victim.steam_id, 1)
        verify(self.db).zincrby("minqlx:players:{}:reaperz".format(victim.steam_id), "lava", 1)

    def test_handle_death_by_hurt_records_frag_log_entry(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "HURT"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("void", victim.steam_id)))
        verify(self.db).zincrby("minqlx:players:void:soulz", victim.steam_id, 1)
        verify(self.db).zincrby("minqlx:players:{}:reaperz".format(victim.steam_id), "void", 1)

    def test_handle_death_by_slime_records_frag_log_entry(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "SLIME"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("acid", victim.steam_id)))
        verify(self.db).zincrby("minqlx:players:acid:soulz", victim.steam_id, 1)
        verify(self.db).zincrby("minqlx:players:{}:reaperz".format(victim.steam_id), "acid", 1)

    def test_handle_death_by_water_records_frag_log_entry(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "WATER"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("drowning", victim.steam_id)))
        verify(self.db).zincrby("minqlx:players:drowning:soulz", victim.steam_id, 1)
        verify(self.db).zincrby("minqlx:players:{}:reaperz".format(victim.steam_id), "drowning", 1)

    def test_handle_death_by_crush_records_frag_log_entry(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "CRUSH"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("squished", victim.steam_id)))
        verify(self.db).zincrby("minqlx:players:squished:soulz", victim.steam_id, 1)
        verify(self.db).zincrby("minqlx:players:{}:reaperz".format(victim.steam_id), "squished", 1)

    def test_handle_death_by_unknown_records_frag_log_entry(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, None, {"MOD": "UNKNOWN"})

        assert_that(self.plugin.frag_log, contains_inanyorder(("unknown", victim.steam_id)))
        verify(self.db).zincrby("minqlx:players:unknown:soulz", victim.steam_id, 1)
        verify(self.db).zincrby("minqlx:players:{}:reaperz".format(victim.steam_id), "unknown", 1)

    def test_handle_death_by_team_switch_is_not_recorded(self):
        victim = fake_player(123, "Fragged Player", team="red")
        killer = fake_player(456, "Fragging Player", team="blue")

        connected_players(victim, killer)

        self.plugin.handle_death(victim, victim, {"MOD": "SWITCHTEAM"})

        assert_that(self.plugin.frag_log, not_(contains_inanyorder((victim.steam_id, victim.steam_id))))

    def test_cmd_mapsoulz_with_no_frags(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, matches("Issuing Player.* didn't reap any soulz, yet."))

    def test_cmd_mapsoulz_with_a_disconnected_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        disconnected_killed2 = fake_player(5, "Disconnected Killed2", team="blue")
        connected_players(player, killed1)

        self.plugin.frag_log = [
            (player.steam_id, killed1.steam_id),
            (player.steam_id, disconnected_killed2.steam_id),
            (player.steam_id, disconnected_killed2.steam_id)
        ]
        when(self.db).exists("minqlx:players:{}:last_used_name".format(disconnected_killed2.steam_id)).thenReturn(True)
        when(self.db).get("minqlx:players:{}:last_used_name".format(disconnected_killed2.steam_id)) \
            .thenReturn(disconnected_killed2.name)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, matches("Top 10 reaped soulz for Issuing Player.*: "
                                                               "Disconnected Killed2.* \(2\), Killed1.* \(1\)"))

    def test_cmd_mapsoulz_returns_top10(self):
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

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for Issuing Player.*: "
                                           "Killed4.* \(8\), Killed3.* \(5\), Killed2.* \(3\), Killed1.* \(2\)"))

    def test_cmd_mapsoulz_for_another_player(self):
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

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "Fragging"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, matches("Top 10 reaped soulz for Fragging Player.*: "
                                                               "Killed2.* \(2\), Killed3.* \(1\)"))

    def test_cmd_mapsoulz_for_another_disconnected_player(self):
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

        when(self.db).exists("minqlx:players:{}:last_used_name".format(fragging_player.steam_id)).thenReturn(True)
        when(self.db).get("minqlx:players:{}:last_used_name".format(fragging_player.steam_id)) \
            .thenReturn(fragging_player.name)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "{}".format(fragging_player.steam_id)], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, matches("Top 10 reaped soulz for Fragging Player.*: "
                                                               "Killed2.* \(2\), Killed3.* \(1\)"))

    def test_cmd_mapsoulz_for_another_nonexisting_disconnected_player(self):
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

        when(self.db).exists("minqlx:players:{}:last_used_name".format(fragging_player.steam_id)).thenReturn(False)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "{}".format(fragging_player.steam_id)], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, any, times=0)

    def test_cmd_mapsoulz_for_another_non_existent_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "Non-existent"], self.reply_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))

    def test_cmd_mapsoulz_for_another_non_existent_lava_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "lava"], self.reply_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))
        assert_channel_was_replied(self.reply_channel, any, times=0)

    def test_cmd_mapsoulz_for_more_than_one_matching_other_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "Killed"], self.reply_channel)

        assert_player_was_told(player, matches(".*4.* players matched.*"))

    def test_cmd_mapsoulz_for_lava_backflips(self):
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

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!lava"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for lava.*: "
                                           "Fragged Player.* \(2\)"))

    def test_cmd_mapsoulz_for_void_deaths(self):
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

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!void"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for void.*: "
                                           "Issuing Player.* \(1\)"))

    def test_cmd_mapsoulz_for_drowning_deaths(self):
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

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!drowning"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for drowning.*: "
                                           "Issuing Player.* \(1\)"))

    def test_cmd_mapsoulz_for_acid_deaths(self):
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

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!acid"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for acid.*: "
                                           "Fragged Player.* \(1\)"))

    def test_cmd_mapsoulz_for_unknown_deaths(self):
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

        self.plugin.cmd_mapsoulz(player, ["!mapsoulz", "!unknown"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for unknown.*: "
                                           "Fragged Player.* \(1\)"))

    def test_cmd_mapreaperz_with_no_fragger(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Issuing Player.*'s soul was not reaped by anyone, yet."))

    def test_cmd_mapreaperz_returns_top10(self):
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

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaperz of Issuing Player.*'s soul: "
                                           "Killer4.* \(7\), Killer3.* \(5\), Killer2.* \(3\), Killer1.* \(2\)"))

    def test_cmd_mapreaperz_for_another_player(self):
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

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz", "Fragged"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaperz of Fragged Player.*'s soul: "
                                           "Killer2.* \(2\), Killer3.* \(1\)"))

    def test_cmd_mapreaperz_for_another_non_existent_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz", "Non-existent"], self.reply_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))

    def test_cmd_mapreaperz_for_more_than_one_matching_other_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz", "Killed"], self.reply_channel)

        assert_player_was_told(player, matches(".*4.* players matched.*"))

    def test_cmd_mapreaperz_with_lava_backflips(self):
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

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz", "Fragged"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaperz of Fragged Player.*'s soul: "
                                           "lava.* \(2\), void.* \(1\)"))

    def test_cmd_mapreaperz_with_a_disconnected_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        disconnected_killed2 = fake_player(5, "Disconnected Killed2", team="blue")
        connected_players(player, killed1)

        self.plugin.frag_log = [
            (killed1.steam_id, player.steam_id),
            (disconnected_killed2.steam_id, player.steam_id),
            (disconnected_killed2.steam_id, player.steam_id)
        ]
        when(self.db).exists("minqlx:players:{}:last_used_name".format(disconnected_killed2.steam_id)).thenReturn(True)
        when(self.db).get("minqlx:players:{}:last_used_name".format(disconnected_killed2.steam_id)) \
            .thenReturn(disconnected_killed2.name)

        self.plugin.cmd_mapreaperz(player, ["!mapreaperz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaperz of Issuing Player.*'s soul: "
                                           "Disconnected Killed2.* \(2\), Killed1.* \(1\)"))

    def test_cmd_soulz_with_no_frags(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format(player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True).thenReturn(list())

        self.plugin.cmd_soulz(player, ["!soulz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, matches("Issuing Player.* didn't reap any soulz, yet."))

    def test_cmd_soulz_with_a_disconnected_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        disconnected_killed2 = fake_player(5, "Disconnected Killed2", team="blue")
        connected_players(player, killed1)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format(player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed1.steam_id, 1),
                (disconnected_killed2.steam_id, 2)
            ])
        when(self.db).exists("minqlx:players:{}:last_used_name".format(disconnected_killed2.steam_id)).thenReturn(True)
        when(self.db).get("minqlx:players:{}:last_used_name".format(disconnected_killed2.steam_id)) \
            .thenReturn(disconnected_killed2.name)

        self.plugin.cmd_soulz(player, ["!soulz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, matches("Top 10 reaped soulz for Issuing Player.*: "
                                                               "Disconnected Killed2.* \(2\), Killed1.* \(1\)"))

    def test_cmd_soulz_returns_top10(self):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format(player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed1.steam_id, 2),
                (killed2.steam_id, 3),
                (killed3.steam_id, 5),
                (killed4.steam_id, 8)
            ])

        self.plugin.cmd_soulz(player, ["!soulz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for Issuing Player.*: "
                                           "Killed4.* \(8\), Killed3.* \(5\), Killed2.* \(3\), Killed1.* \(2\)"))

    def test_cmd_soulz_for_another_player(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragging_player = fake_player(456, "Fragging Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, fragging_player, killed1, killed2, killed3, killed4)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format(fragging_player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed2.steam_id, 2),
                (killed3.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "Fragging"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, matches("Top 10 reaped soulz for Fragging Player.*: "
                                                               "Killed2.* \(2\), Killed3.* \(1\)"))

    def test_cmd_soulz_for_another_disconnected_player(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragging_player = fake_player(456, "Fragging Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format(fragging_player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed2.steam_id, 2),
                (killed3.steam_id, 1)
            ])
        when(self.db).exists("minqlx:players:{}:last_used_name".format(fragging_player.steam_id)).thenReturn(True)
        when(self.db).get("minqlx:players:{}:last_used_name".format(fragging_player.steam_id)) \
            .thenReturn(fragging_player.name)

        self.plugin.cmd_soulz(player, ["!soulz", "{}".format(fragging_player.steam_id)], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, matches("Top 10 reaped soulz for Fragging Player.*: "
                                                               "Killed2.* \(2\), Killed3.* \(1\)"))

    def test_cmd_soulz_for_another_nonexisting_disconnected_player(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragging_player = fake_player(456, "Fragging Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        when(self.db).exists("minqlx:players:{}:last_used_name".format(fragging_player.steam_id)).thenReturn(False)

        self.plugin.cmd_soulz(player, ["!soulz", "{}".format(fragging_player.steam_id)], self.reply_channel)

        assert_channel_was_replied(self.reply_channel, any, times=0)

    def test_cmd_soulz_for_another_non_existent_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_soulz(player, ["!soulz", "Non-existent"], self.reply_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))

    def test_cmd_soulz_for_another_non_existent_lava_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_soulz(player, ["!soulz", "lava"], self.reply_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))
        assert_channel_was_replied(self.reply_channel, any, times=0)

    def test_cmd_soulz_for_more_than_one_matching_other_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.cmd_soulz(player, ["!soulz", "Killed"], self.reply_channel)

        assert_player_was_told(player, matches(".*4.* players matched.*"))

    def test_cmd_soulz_for_lava_backflips(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format("lava"),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (fragged_player.steam_id, 2)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!lava"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for lava.*: "
                                           "Fragged Player.* \(2\)"))

    def test_cmd_soulz_for_void_deaths(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format("void"),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (player.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!void"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for void.*: "
                                           "Issuing Player.* \(1\)"))

    def test_cmd_soulz_for_drowning_deaths(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format("drowning"),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (player.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!drowning"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for drowning.*: "
                                           "Issuing Player.* \(1\)"))

    def test_cmd_soulz_for_acid_deaths(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format("acid"),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (fragged_player.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!acid"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for acid.*: "
                                           "Fragged Player.* \(1\)"))

    def test_cmd_soulz_for_unknown_deaths(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format("unknown"),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (fragged_player.steam_id, 1)
            ])

        self.plugin.cmd_soulz(player, ["!soulz", "!unknown"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaped soulz for unknown.*: "
                                           "Fragged Player.* \(1\)"))

    def test_cmd_reaperz_with_no_fragger(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        when(self.db).zrevrangebyscore("minqlx:players:{}:reaperz".format(player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True).thenReturn(list())

        self.plugin.cmd_reaperz(player, ["!reaperz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Issuing Player.*'s soul was not reaped by anyone, yet."))

    def test_cmd_reaperz_returns_top10(self):
        player = fake_player(123, "Issuing Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        killer2 = fake_player(5, "Killer2", team="blue")
        killer3 = fake_player(6, "Killer3", team="blue")
        killer4 = fake_player(7, "Killer4", team="blue")
        connected_players(player, killer1, killer2, killer3, killer4)

        when(self.db).zrevrangebyscore("minqlx:players:{}:reaperz".format(player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killer1.steam_id, 2),
                (killer2.steam_id, 3),
                (killer3.steam_id, 5),
                (killer4.steam_id, 7),
            ])

        self.plugin.cmd_reaperz(player, ["!reaperz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaperz of Issuing Player.*'s soul: "
                                           "Killer4.* \(7\), Killer3.* \(5\), Killer2.* \(3\), Killer1.* \(2\)"))

    def test_cmd_reaperz_for_another_player(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        killer2 = fake_player(5, "Killer2", team="blue")
        killer3 = fake_player(6, "Killer3", team="blue")
        killer4 = fake_player(7, "Killer4", team="blue")
        connected_players(player, fragged_player, killer1, killer2, killer3, killer4)

        when(self.db).zrevrangebyscore("minqlx:players:{}:reaperz".format(fragged_player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killer2.steam_id, 2),
                (killer3.steam_id, 1)
            ])

        self.plugin.cmd_reaperz(player, ["!reaperz", "Fragged"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaperz of Fragged Player.*'s soul: "
                                           "Killer2.* \(2\), Killer3.* \(1\)"))

    def test_cmd_reaperz_for_another_non_existent_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        connected_players(player)

        self.plugin.cmd_reaperz(player, ["!reaperz", "Non-existent"], self.reply_channel)

        assert_player_was_told(player, matches(".*no players matched.*"))

    def test_cmd_reaperz_for_more_than_one_matching_other_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        self.plugin.cmd_reaperz(player, ["!reaperz", "Killed"], self.reply_channel)

        assert_player_was_told(player, matches(".*4.* players matched.*"))

    def test_cmd_reaperz_with_lava_backflips(self):
        player = fake_player(123, "Issuing Player", team="red")
        fragged_player = fake_player(456, "Fragged Player", team="red")

        killer1 = fake_player(4, "Killer1", team="blue")
        connected_players(player, fragged_player, killer1)

        when(self.db).zrevrangebyscore("minqlx:players:{}:reaperz".format(fragged_player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                ("lava", 2),
                ("void", 1)
            ])

        self.plugin.cmd_reaperz(player, ["!reaperz", "Fragged"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaperz of Fragged Player.*'s soul: "
                                           "lava.* \(2\), void.* \(1\)"))

    def test_cmd_reaperz_with_a_disconnected_player(self):
        player = fake_player(123, "Issuing Player", team="red")

        killer1 = fake_player(4, "Killed1", team="blue")
        disconnected_killer2 = fake_player(5, "Disconnected Killed2", team="blue")
        connected_players(player, killer1)

        when(self.db).zrevrangebyscore("minqlx:players:{}:reaperz".format(player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (disconnected_killer2.steam_id, 2),
                (killer1.steam_id, 1)
            ])
        when(self.db).exists("minqlx:players:{}:last_used_name".format(disconnected_killer2.steam_id)).thenReturn(True)
        when(self.db).get("minqlx:players:{}:last_used_name".format(disconnected_killer2.steam_id)) \
            .thenReturn(disconnected_killer2.name)

        self.plugin.cmd_reaperz(player, ["!mapreaperz"], self.reply_channel)

        assert_channel_was_replied(self.reply_channel,
                                   matches("Top 10 reaperz of Issuing Player.*'s soul: "
                                           "Disconnected Killed2.* \(2\), Killed1.* \(1\)"))

    def test_cmd_soulz_in_team_chat_channel(self):
        player = fake_player(123, "Issuing Player", team="red")
        minqlx.CHAT_CHANNEL = mocked_channel()

        killed1 = fake_player(4, "Killed1", team="blue")
        killed2 = fake_player(5, "Killed2", team="blue")
        killed3 = fake_player(6, "Killed3", team="blue")
        killed4 = fake_player(7, "Killed4", team="blue")
        connected_players(player, killed1, killed2, killed3, killed4)

        when(self.db).zrevrangebyscore("minqlx:players:{}:soulz".format(player.steam_id),
                                       "+INF", "-INF", start=0, num=10, withscores=True)\
            .thenReturn([
                (killed1.steam_id, 2),
                (killed2.steam_id, 3),
                (killed3.steam_id, 5),
                (killed4.steam_id, 8)
            ])

        self.plugin.cmd_soulz(player, ["!soulz"], minqlx.RED_TEAM_CHAT_CHANNEL)

        assert_channel_was_replied(minqlx.CHAT_CHANNEL,
                                   matches("Top 10 reaped soulz for Issuing Player.*: "
                                           "Killed4.* \(8\), Killed3.* \(5\), Killed2.* \(3\), Killed1.* \(2\)"))
