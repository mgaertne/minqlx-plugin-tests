import minqlx


# noinspection PyPep8Naming
class custom_votes(minqlx.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("vote_called", self.handle_vote_called)

    def handle_vote_called(self, caller, vote, args):
        if not self.get_cvar("g_allowSpecVote", bool) and caller.team == "spectator":
            caller.tell("You are not allowed to call a vote as spectator.")
            return minqlx.RET_NONE

        if minqlx.Plugin.is_vote_active():
            return minqlx.RET_NONE

        if vote.lower() == "thrufloors":
            if args.lower() == "off":
                minqlx.callvote("g_forceDmgThroughSurface 0", "Turn off damage through floors?")
                minqlx.client_command(caller.id, "vote yes")
                self.msg(f"{caller.name}^7 called a vote.")
                return minqlx.RET_STOP_ALL
            if args.lower() == "on":
                minqlx.callvote("g_forceDmgThroughSurface 1", "Turn on damage through floors?")
                minqlx.client_command(caller.id, "vote yes")
                self.msg(f"{caller.name}^7 called a vote.")
                return minqlx.RET_STOP_ALL
            caller.tell("^2/cv thrufloors [on/off]^7 is the usage for this callvote command.")
            return minqlx.RET_STOP_ALL

        if vote.lower() == "spec":
            target_player = self.find_target_player_or_list_alternatives(caller, args)
            if target_player is None:
                return minqlx.RET_STOP_ALL

            if target_player.team == "spectator":
                caller.tell(f"Player {target_player.name}^7 is already in the spectators.")
                return minqlx.RET_STOP_ALL

            minqlx.callvote(f"put {target_player.id} spec", f"spec {target_player.name}^7?")
            minqlx.client_command(caller.id, "vote yes")
            self.msg(f"{caller.name}^7 called a vote.")
            return minqlx.RET_STOP_ALL

        if vote.lower() == "mute":
            target_player = self.find_target_player_or_list_alternatives(caller, args)
            if target_player is None:
                return minqlx.RET_STOP_ALL

            minqlx.callvote(
                f"qlx !silence {target_player.id} 10 minutes You were call-voted silent for 10 minutes.;"
                f"mute {target_player.id}", f"Mute {target_player.name}^7 for 10 minutes?")
            minqlx.client_command(caller.id, "vote yes")
            self.msg(f"{caller.name}^7 called a vote.")
            return minqlx.RET_STOP_ALL

        if vote.lower() == "allready":
            if self.game.state == "warmup":
                minqlx.callvote("qlx !allready", "Ready all players?")
                minqlx.client_command(caller.id, "vote yes")
                return minqlx.RET_STOP_ALL
            caller.tell("The game is already in progress.")
            return minqlx.RET_STOP_ALL

        return minqlx.RET_NONE

    def find_target_player_or_list_alternatives(self, player, target):
        # Tell a player which players matched
        def list_alternatives(players, indent=2):
            amount_alternatives = len(players)
            player.tell(f"A total of ^6{amount_alternatives}^7 players matched for {target}:")
            out = ""
            for p in players:
                out += " " * indent
                out += f"{p.id}^6:^7 {p.name}\n"
            player.tell(out[:-1])

        try:
            steam_id = int(target)

            target_player = self.player(steam_id)
            if target_player:
                return target_player

        except ValueError:
            pass
        except minqlx.NonexistentPlayerError:
            pass

        target_players = self.find_player(target)

        # If there were absolutely no matches
        if not target_players:
            player.tell(f"Sorry, but no players matched your tokens: {target}.")
            return None

        # If there were more than 1 matches
        if len(target_players) > 1:
            list_alternatives(target_players)
            return None

        # By now there can only be one person left
        return target_players.pop()
