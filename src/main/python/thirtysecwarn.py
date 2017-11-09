from minqlx import Plugin, thread, next_frame
import time
import random


class thirtysecwarn(Plugin):
    """Created by Thomas Jones on 01/09/2016 - thomas@tomtecsolutions.com

thirtysecwarn.py - a minqlx plugin to play unused VO when a CA game is nearing the round time limit.

This plugin is released to everyone, for any purpose. It comes with no warranty, no guarantee it works, it's
released AS IS.

You can modify everything, except for lines 1-4 and the !tomtec_versions code. They're there to indicate I whacked this
together originally. Please make it better :D

Completely rebuild by iouonegirl and Gelenkbusfahrer on 25/09/2017, customization of sounds and unit tests added by
ShiN0 somewhen in October 2017
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

    @thread
    def warntimer(self, roundnumber):
        timer_delay = self.get_cvar("roundtimelimit", int) - 30
        time.sleep(timer_delay)
        self.play_thirty_second_warning(roundnumber)

    @next_frame
    def play_thirty_second_warning(self, roundnumber):
        self.undelayed_player_thirty_second_warning(roundnumber)

    def undelayed_player_thirty_second_warning(self, roundnumber):
        if not self.game:
            return
        if not self.game.type_short == "ca":
            return
        if not self.game.state == "in_progress":
            return
        if not self.timer_round_number == roundnumber:
            return

        # passed all conditions, play sound
        Plugin.play_sound(self.get_announcer_sound())

    def get_announcer_sound(self):
        qlx_thirtySecondWarnAnnouncer = self.get_cvar("qlx_thirtySecondWarnAnnouncer")

        if qlx_thirtySecondWarnAnnouncer == "random":
            return self.random_announcer()

        if qlx_thirtySecondWarnAnnouncer not in self.announcerMap:
            qlx_thirtySecondWarnAnnouncer = "standard"
        return self.announcerMap[qlx_thirtySecondWarnAnnouncer]

    def random_announcer(self):
        key, sound = random.choice(list(self.announcerMap.items()))
        return sound
