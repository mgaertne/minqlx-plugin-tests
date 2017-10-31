from minqlx_plugin_test import *

from mockito import *
from hamcrest import *
import unittest

class TestDuelArenaWorker(unittest.TestCase):

    def setUp(self):
        self.warner = thirtysecwarn()
        setup_plugin(self.warner)
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "standard")

    def tearDown(self):
        unstub()

    def test_standard(self):
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "standard")
        assert_that(self.warner.get_announcer_sound(), "sound/vo/30_second_warning.ogg")

    def test_female(self):
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "female")
        assert_that(self.warner.get_announcer_sound(), "sound/vo_female/30_second_warning.ogg")

    def test_evil(self):
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "evil")
        assert_that(self.warner.get_announcer_sound(), "sound/vo_evil/30_second_warning.ogg")

    def test_non_existing_reverts_to_standard(self):
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "invalid")
        assert_that(self.warner.get_announcer_sound(), "sound/vo/30_second_warning.ogg")

    def test_random(self):
        random.seed(42)
        setup_cvar(self.warner, "qlx_thirtySecondWarnAnnouncer", "random")
        assert_that(self.warner.get_announcer_sound(), is_("sound/vo/30_second_warning.ogg"))

    def test_plays_no_sound_when_game_is_not_running_anymore(self):
        setup_no_game()

        self.warner.undelayed_player_thirty_second_warning(4)

        verify(self.warner, times=0).play_sound(any(str))

    def test_plays_no_sound_when_game_is_not_clan_arena(self):
        setup_game_in_progress(game_type="ft")

        self.warner.undelayed_player_thirty_second_warning(4)

        verify(self.warner, times=0).play_sound(any(str))

    def test_plays_no_sound_when_game_not_in_progress(self):
        setup_game_in_warmup()

        self.warner.undelayed_player_thirty_second_warning(4)

        verify(self.warner, times=0).play_sound(any(str))


    def test_plays_no_sound_when_next_round_started(self):
        calling_round_number = 4
        setup_game_in_progress(game_type="ca")
        self.warner.timer_round_number = calling_round_number + 1

        self.warner.undelayed_player_thirty_second_warning(calling_round_number)

        verify(self.warner, times=0).play_sound(any(str))

    def test_plays_sound_when_round_still_running(self):
        calling_round_number = 4
        setup_game_in_progress(game_type="ca")
        self.warner.timer_round_number = calling_round_number

        self.warner.undelayed_player_thirty_second_warning(calling_round_number)

        verify(self.warner).play_sound(any(str))

    def test_game_start_initializes_timer_round_number(self):
        self.warner.timer_round_number = 7

        self.warner.handle_game_start(None)

        assert_that(self.warner.timer_round_number, is_(0))

    def test_round_end_increases_round_number(self):
        self.warner.timer_round_number = 4

        self.warner.handle_round_end(None)

        assert_that(self.warner.timer_round_number, is_(5))


import minqlx, time
import random

class thirtysecwarn(minqlx.Plugin):
    """Created by Thomas Jones on 01/09/2016 - thomas@tomtecsolutions.com

thirtysecwarn.py - a minqlx plugin to play unused VO when a CA game is nearing the round time limit.

This plugin is released to everyone, for any purpose. It comes with no warranty, no guarantee it works, it's released AS IS.

You can modify everything, except for lines 1-4 and the !tomtec_versions code. They're there to indicate I whacked this together originally. Please make it better :D

Completely rebuild by iouonegirl and Gelenkbusfahrer on 25/09/2017, customization of sounds and unit tests added by ShiN0 somewhen in October 2017
    """
    def __init__(self):

        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_start", self.handle_game_start)

        self.set_cvar_once("qlx_thirtySecondWarnAnnouncer", "standard")

        self.announcerMap = {
            "standard": "sound/vo/30_second_warning.ogg",
            "female": "sound/vo_female/30_second_warning.ogg",
            "evil": "sound/vo_evil/30_second_warning.ogg"
        }

        self.timer_round_number = 0

    def handle_game_start(self, game):
        self.timer_round_number = 0

    def handle_round_end(self, data):
        self.timer_round_number += 1

    def handle_round_start(self, round_number):
        self.timer_round_number = round_number
        self.warntimer(round_number)

    @minqlx.thread
    def warntimer(self, roundnumber):
        timer_delay = self.get_cvar("roundtimelimit", int) - 30
        time.sleep(timer_delay)
        self.play_thirty_second_warning(roundnumber)

    @minqlx.next_frame
    def play_thirty_second_warning(self, roundnumber):
        self.undelayed_player_thirty_second_warning(roundnumber)

    def undelayed_player_thirty_second_warning(self, roundnumber):
        if not self.game: return
        if not self.game.type_short == "ca": return
        if not self.game.state == "in_progress": return
        if not self.timer_round_number == roundnumber: return

        # passed all conditions, play sound
        self.play_sound(self.get_announcer_sound())

    def get_announcer_sound(self):
        qlx_thirtySecondWarnAnnouncer = self.get_cvar("qlx_thirtySecondWarnAnnouncer")

        if qlx_thirtySecondWarnAnnouncer == "random":
            return self.random_announcer()

        if not qlx_thirtySecondWarnAnnouncer in self.announcerMap: qlx_thirtySecondWarnAnnouncer = "standard"
        return self.announcerMap[qlx_thirtySecondWarnAnnouncer]

    def random_announcer(self):
        key, sound = random.choice(list(self.announcerMap.items()))
        return sound
