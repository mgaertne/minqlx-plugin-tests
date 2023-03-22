"""
This is a plugin created by ShiN0
Copyright (c) 2023 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one.

You need to install openai in your python installation, i.e. python3 -m pip install -U openai
"""
import re
import time
from datetime import datetime, timezone
from threading import RLock

import emoji
import openai
import tiktoken
from openai import OpenAIError, Model, ChatCompletion

import minqlx
from minqlx import Plugin, CHAT_CHANNEL
from minqlx.database import Redis

DATETIMEFORMAT = "%Y%m%d%H%M%S"

CHAT_BOT_LOG = "minqlx:openai_bot:log"


def num_tokens_from_messages(messages, *, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    if model not in ["gpt-3.5-turbo-0301", "gpt-3.5-turbo"]:
        return -1

    num_tokens = 0
    for message in messages:
        num_tokens += (
            4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        )
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens


# noinspection PyPep8Naming
class openai_bot(Plugin):
    """
    This plugin offers a customizeable openai chat bot in your server using the completion API from openai.

    For this plugin to work, you need to provide an API key from openai, potentially with added costs applied according
    to their terms of service. Please check their pricing for the model you configure here. You may also want to set a
    hard limit for the spendings at their platform.

    For explanations on the various parameters for the openai API, please consult the openai API documentation.

    Uses:
    * qlx_openai_botname (default: "Bob") The name of the bot as it will appear in in-game chat.
    * qlx_openai_clanprefix (default: "") An optional clan prefix that will show up whenever your bot says something.
    * qlx_openai_bot_triggers (default: "") Comma-separated list of bot triggers to use in addition to the bot's name
    * qlx_openai_model (default: "gpt-3.5-turbo") The AI model used for creating chat interactions.
    * qlx_openai_max_tokens (default: 1024, max: 4096) The maximum amount of tokens a completion may consume.
    * qlx_openai_max_chat_history_tokens (default: 512) Maximum number of tokens the chat history may consume.
            Values are limited to be between 0 and 4096.
    * qlx_openai_temperature (default: 1.0) What sampling temperature to use, between 0 and 2.
    * qlx_openai_top_p (default: 1.0) An alternative to sampling with temperature, called nucleus sampling.
    * qlx_openai_frequency_penalty (default: 0.0) Number between -2.0 and 2.0. Positive values penalize new tokens
            based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same
            line verbatim.
    * qlx_openai_presence_penalty (default: 0.0) Number between -2.0 and 2.0. Positive values penalize new tokens
            based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.
    * qlx_openai_system_context A template string that provides the overall system context for the chat. You can use
            {bot_name} to dynamically fill in the name of the bot here.
            {game_state} to dynamically insert the current game state
            {current_timestamp} the current system timestamp in the format "dd/mm/yy HH:MM TZ"
            Defaults to: "You are {bot_name}, a spectator on a QuakeLive server."
    * qlx_openai_bot_role_* A template string injected directly before the conversation line according to the event.
            May provide the overall bot mood or instructions on how to react to different types of messages and
            questions. You can use
                * {bot_name} to dynamically fill in the name of the bot here.
                * {game_state} to dynamically insert the current game state
            The following role templates are currently recognized:
                * qlx_openai_bot_role_chat
                * qlx_openai_bot_role_gamestart
                * qlx_openai_bot_role_roundstart
                * qlx_openai_bot_role_roundend
                * qlx_openai_bot_role_gameend
                * qlx_openai_bot_role_weird_stats
            all are defaulting to: ""
    * qlx_openai_greet_joiners (default: 1 or True) greet joiners upon messages within the greeting_delay
    * qlx_openai_greeting_delay (default: 60) amount of seconds where newly connected players will be greeted upon
            their first message regardless of bot mentioning
    * qlx_openai_extended_logging (default 0 or False) enable or disable extended logging of chat contexts
    """

    database = Redis  # type: ignore

    def __init__(self):
        super().__init__()

        self.queue_lock = RLock()
        self.set_cvar_once("qlx_openai_botname", "Bob")
        self.set_cvar_once("qlx_openai_clanprefix", "")
        self.set_cvar_once("qlx_openai_bot_triggers", "")
        self.set_cvar_once("qlx_openai_model", "gpt-3.5-turbo")
        self.set_cvar_limit_once("qlx_openai_max_tokens", 1024, 0, 4096)
        self.set_cvar_limit_once("qlx_openai_max_chat_history_tokens", 512, 0, 4096)
        self.set_cvar_limit_once("qlx_openai_temperature", 1.0, 0.0, 2.0)
        self.set_cvar_limit_once("qlx_openai_top_p", 1.0, 0.0, 2.0)
        self.set_cvar_limit_once("qlx_openai_frequency_penalty", 0.0, -2.0, 2.0)
        self.set_cvar_limit_once("qlx_openai_presence_penalty", 0.0, -2.0, 2.0)
        self.set_cvar_once(
            "qlx_openai_system_context",
            "You are {bot_name}, a spectator on a QuakeLive server.",
        )
        self.set_cvar_once("qlx_openai_bot_mood", "")
        self.set_cvar_once("qlx_openai_bot_role_chat", "")
        self.set_cvar_once("qlx_openai_bot_role_gamestart", "")
        self.set_cvar_once("qlx_openai_bot_role_roundstart", "")
        self.set_cvar_once("qlx_openai_bot_role_roundend", "")
        self.set_cvar_once("qlx_openai_bot_role_gameend", "")
        self.set_cvar_once("qlx_openai_bot_role_weird_stats", "")
        self.set_cvar_once("qlx_openai_greet_joiners", "1")
        self.set_cvar_once("qlx_openai_greeting_delay", "60")
        self.set_cvar_once("qlx_openai_extended_logging", "0")

        self.bot_api_key = self.get_cvar("qlx_openai_apikey")
        self.bot_name = self.get_cvar("qlx_openai_botname") or "Bob"
        self.bot_triggers = self.get_cvar("qlx_openai_bot_triggers", list) or []
        self.bot_triggers = [
            trigger for trigger in self.bot_triggers if len(trigger) > 0
        ]
        self.bot_clanprefix = self.get_cvar("qlx_openai_clanprefix") or ""
        self.model = self.get_cvar("qlx_openai_model") or "gpt-3.5-turbo"
        self.max_tokens = self.get_cvar("qlx_openai_max_tokens", int) or 100
        self.max_chat_history_tokens = (
            self.get_cvar("qlx_openai_max_chat_history_tokens", int) or 512
        )
        self.temperature = self.get_cvar("qlx_openai_temperature", float) or 1.0
        if self.temperature < 0 or self.temperature > 2:
            self.temperature = 1.0
        self.top_p = self.get_cvar("qlx_openai_top_p", float) or 1.0
        if self.top_p < 0 or self.top_p > 2:
            self.top_p = 1.0
        self.frequency_penalty = (
            self.get_cvar("qlx_openai_frequency_penalty", float) or 0.0
        )
        if self.frequency_penalty < -2.0 or self.frequency_penalty > 2.0:
            self.frequency_penalty = 0.0
        self.presence_penalty = (
            self.get_cvar("qlx_openai_presence_penalty", float) or 0.0
        )
        if self.presence_penalty < -2.0 or self.presence_penalty > 2.0:
            self.presence_penalty = 0.0
        self.system_context = (
            self.get_cvar("qlx_openai_system_context")
            .encode("raw_unicode_escape")
            .decode("unicode_escape")
        )
        self.bot_role_chat = (
            self.get_cvar("qlx_openai_bot_role_chat")
            .encode("raw_unicode_escape")
            .decode("unicode_escape")
        )
        self.bot_role_gamestart = (
            self.get_cvar("qlx_openai_bot_role_gamestart")
            .encode("raw_unicode_escape")
            .decode("unicode_escape")
        )
        self.bot_role_roundstart = (
            self.get_cvar("qlx_openai_bot_role_roundstart")
            .encode("raw_unicode_escape")
            .decode("unicode_escape")
        )
        self.bot_role_roundend = (
            self.get_cvar("qlx_openai_bot_role_roundend")
            .encode("raw_unicode_escape")
            .decode("unicode_escape")
        )
        self.bot_role_gameend = (
            self.get_cvar("qlx_openai_bot_role_gameend")
            .encode("raw_unicode_escape")
            .decode("unicode_escape")
        )
        self.bot_role_weird_stats = (
            self.get_cvar("qlx_openai_bot_role_weird_stats")
            .encode("raw_unicode_escape")
            .decode("unicode_escape")
        )
        self.extended_logging = (
            self.get_cvar("qlx_openai_extended_logging", bool) or False
        )

        self.greet_joiners = self.get_cvar("qlx_openai_greet_joiners", bool)
        self.greeting_delay = self.get_cvar("qlx_openai_greeting_delay", int) or 60
        self.recently_connected_steam_ids = set()
        self.map_authors_cache = {}
        self.cache_map_authors_from_db()

        self.add_hook("chat", self.handle_chat)
        self.add_hook("player_connect", self.handle_player_connect)
        self.add_hook("game_countdown", self.handle_game_countdown)
        self.add_hook("round_start", self.handle_round_start)
        self.add_hook("round_end", self.handle_round_end)
        self.add_hook("game_end", self.handle_game_end)

        self.add_command("listmodels", self.cmd_list_models, permission=5)
        self.add_command(
            "switchmodel", self.cmd_switch_model, permission=5, usage="[modelname]"
        )

    @minqlx.thread
    def cache_map_authors_from_db(self):
        for key in self.db.keys("minqlx:maps:*:authors"):
            mapname = key.replace("minqlx:maps:", "").replace(":authors", "")
            self.map_authors_cache[mapname] = self.db[key]

    def summarize_game_end_stats(self, announcements):
        @minqlx.thread
        def threaded_summary(messages):
            response = self._gather_completion(messages)
            if response is None:
                return
            response = response.replace("%", " percent")
            self._send_message(minqlx.CHAT_CHANNEL, response)

        weird_stats_context = self.bot_role_weird_stats.format(
            bot_name=Plugin.clean_text(self.bot_name),
            game_state=self.current_game_state(),
        ).strip()

        contextualized_messages = [
            {"role": "user", "content": "You use sarcasm and slang."},
            {
                "role": "user",
                "content": f"{weird_stats_context}: {Plugin.clean_text(announcements)}.",
            },
        ]
        threaded_summary(contextualized_messages)

    def _gather_completion(self, messages):
        openai.api_key = self.bot_api_key
        try:
            completion = ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                n=1,
                top_p=self.top_p,
                stop=None,
                temperature=self.temperature,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
            )
        except OpenAIError as e:
            self.logger.debug(f"Exception from openai API: {e}")
            return None
        return self._cleanup_choice(self._pick_choice(completion))

    @staticmethod
    def _pick_choice(completion):
        return completion.choices[0]["message"]["content"].lstrip().rstrip()

    @staticmethod
    def _cleanup_choice(response):
        if len(response) == 0:
            return None
        matcher = re.compile(r"^(\w+: )?(.*)")
        match = matcher.match(response)
        while match is not None and match.groups()[0] is not None:
            match = matcher.match(match.groups()[1])
        if match is None:
            return response

        return match.groups()[1].lstrip('"').rstrip('"')

    @minqlx.thread
    def _record_chat_line(self, message, *, lock):
        with lock:
            self.db.zadd(
                CHAT_BOT_LOG,
                int(datetime.strftime(datetime.now(), DATETIMEFORMAT)),
                message,
            )

    def _send_message(self, communication_channel, message):
        communication_channel.reply(
            f"{self.bot_clanprefix}^7{self.bot_name}^7: ^2{self._ql_cleaned_up(message)}"
        )

        # noinspection PyProtectedMember
        if "mydiscordbot" in Plugin._loaded_plugins:
            # noinspection PyProtectedMember
            discord_plugin = Plugin._loaded_plugins["mydiscordbot"]
            # noinspection PyUnresolvedReferences
            discord_plugin.discord.relay_message(
                Plugin.clean_text(
                    f"**{self.bot_clanprefix}{self.bot_name}**: {message}"
                )
            )

    def _ql_cleaned_up(self, message):
        cleaned_up = emoji.demojize(message, delimiters=("#", " ")).replace("  ", " ")
        if self.db.exists("minqlx:openai_bot:message_replacements"):
            replacements = self.db.hgetall("minqlx:openai_bot:message_replacements")
            for original, replacement in replacements.items():
                if original in cleaned_up:
                    cleaned_up = cleaned_up.replace(f"{original} ", f"{replacement} ")
        return cleaned_up

    def handle_chat(self, player, msg, channel):
        @minqlx.thread
        def threaded_response(communication_channel, chatter, message):
            with self.queue_lock:
                request = f"{chatter.clean_name}: {message}"

                if not self.is_triggered_message(msg) and (
                    not self.greet_joiners
                    or chatter.steam_id not in self.recently_connected_steam_ids
                ):
                    self._record_chat_line(request, lock=self.queue_lock)
                    return

                if chatter.steam_id in self.recently_connected_steam_ids:
                    self.recently_connected_steam_ids.remove(chatter.steam_id)

                message_history = self.contextualized_chat_history(
                    request, trigger_template=self.get_role_template("chat")
                )
                self._record_chat_line(request, lock=self.queue_lock)

                response = self._gather_completion(message_history)
                if response is None:
                    return
                self._record_chat_line(
                    f"{Plugin.clean_text(self.bot_name)}: {response}",
                    lock=self.queue_lock,
                )
                self._send_message(communication_channel, response)

        if channel not in [CHAT_CHANNEL]:
            return

        if msg.startswith("!"):
            return

        matcher = re.compile(r"\w")
        if len(set(matcher.findall(Plugin.clean_text(msg)))) <= 3:
            return

        threaded_response(channel, player, msg)

    def is_triggered_message(self, message):
        matchers = [
            rf"^{trigger}\W|\W{trigger}\W|\W{trigger}$"
            for trigger in self.bot_triggers + [Plugin.clean_text(self.bot_name)]
        ]
        pattern = "|".join(matchers)
        return re.search(pattern, Plugin.clean_text(message), flags=re.IGNORECASE)

    def contextualized_chat_history(self, request, *, trigger_template=None):
        game_state = self.current_game_state()
        current_timestamp = datetime.now(
            datetime.now(timezone.utc).astimezone().tzinfo
        ).strftime("%m/%d/%y %H:%M %Z")
        chat_log = self.db.zrangebyscore(CHAT_BOT_LOG, "-INF", "+INF")
        formatted_system_context = self.system_context.format(
            bot_name=Plugin.clean_text(self.bot_name),
            game_state=game_state,
            current_timestamp=current_timestamp,
        )

        system_context = {
            "role": "system",
            "content": formatted_system_context,
        }

        chat_history_messages = [{"role": "user", "content": request}]
        if (
            trigger_template is not None
            and len(
                trigger_template.format(
                    bot_name=Plugin.clean_text(self.bot_name), game_state=game_state
                ).strip()
            )
            > 0
        ):
            chat_history_messages.append(
                {
                    "role": "user",
                    "content": trigger_template.format(
                        bot_name=Plugin.clean_text(self.bot_name), game_state=game_state
                    ),
                }
            )

        for message in reversed(chat_log):
            if (
                num_tokens_from_messages(
                    chat_history_messages + [system_context], model=self.model
                )
                > self.max_chat_history_tokens
            ):
                score = self.db.zscore(CHAT_BOT_LOG, message)
                self.db.zremrangebyscore(CHAT_BOT_LOG, "-INF", score)
                break
            role = (
                "assistant"
                if message.startswith(Plugin.clean_text(self.bot_name))
                else "user"
            )
            chat_history_messages.append({"role": role, "content": message})
        chat_history_messages.append(system_context)
        chat_history_messages.reverse()

        if self.extended_logging:
            self.logger.debug(f"chat_history_messages = {chat_history_messages}")

        return chat_history_messages

    def current_game_state(self):
        game = self.game
        if game is None:
            return ""

        teams = Plugin.teams()
        vs = min(len(teams["red"]), len(teams["blue"]))
        team_status = self.team_status()
        map_title = game.map_title if game.map_title else game.map
        author = self.map_authors_cache.get(game.map, None)

        if author is not None:
            return (
                f"Match state: {vs}v{vs} {game.state.replace('_', ' ').lower()}\n"
                f"{team_status}\nCurrent map(author): {map_title}({Plugin.clean_text(author)})\n"
                f"Game type: {game.factory_title}"
            )

        return (
            f"Match state: {vs}v{vs} {game.state.replace('_', ' ').lower()}\n"
            f"{team_status}\nCurrent map: {map_title}\nGame type: {game.factory_title}"
        )

    def team_status(self):
        game = self.game
        if game is None:
            return ""

        ratings = {}
        # noinspection PyProtectedMember
        if "balance" in Plugin._loaded_plugins:
            # noinspection PyUnresolvedReferences,PyProtectedMember
            ratings = Plugin._loaded_plugins["balance"].ratings

        # noinspection PyProtectedMember
        if "balancetwo" in Plugin._loaded_plugins:
            # noinspection PyProtectedMember
            balancetwo_plugin = Plugin._loaded_plugins["balancetwo"]
            balance_api = self.get_cvar("qlx_balanceApi")
            # noinspection PyUnresolvedReferences
            ratings = (
                balancetwo_plugin.ratings["Elo"]
                if balance_api == "elo"
                else balancetwo_plugin.ratings["B-Elo"]
            )

        player_speeds = {}
        # noinspection PyProtectedMember
        if "weird_stats" in Plugin._loaded_plugins:
            # noinspection PyUnresolvedReferences,PyProtectedMember
            player_speeds = Plugin._loaded_plugins[
                "weird_stats"
            ].determine_player_speeds()

        teams = Plugin.teams()
        team_status = (
            "nick|team|dmg|playtime(s)|frags|km/h|elo|matches|bday\n"
            if self.game.state == "in_progress"
            else "nick|team|elo|matches|bday\n"
        )
        for team in ["red", "blue", "spectator"]:
            if len(teams[team]) == 0:
                continue
            for player in teams[team]:
                player_speed = player_speeds.get(player.steam_id, "n/a")

                player_elo = "n/a"
                if (
                    player.steam_id in ratings
                    and game.type_short in ratings[player.steam_id]
                ):
                    player_elo = ratings[player.steam_id][game.type_short]["elo"]

                player_matches = 0
                if self.db.exists(f"minqlx:players:{player.steam_id}:games_completed"):
                    player_matches = int(
                        self.db.get(f"minqlx:players:{player.steam_id}:games_completed")
                    )

                player_bday = ""
                if self.db.exists(f"minqlx:players:{player.steam_id}:bday"):
                    birthdate = datetime.strptime(
                        self.db[f"minqlx:players:{player.steam_id}:bday"], "%d.%m."
                    )
                    player_bday = birthdate.strftime("%m%d")

                if self.game.state == "in_progress":
                    team_status += (
                        f"{player.clean_name}|{player.team}|"
                        f"{player.stats.damage_dealt}|{player.stats.time}|{player.stats.kills}|"
                        f"{player_speed}|{player_elo}|"
                        f"{player_matches}|{player_bday}\n"
                    )
                else:
                    team_status += f"{player.clean_name}|{player.team}|{player_elo}|{player_matches}|{player_bday}\n"

        team_status += (
            f"{Plugin.clean_text(self.bot_name)}|spectator|0|0|0|n/a|69|0|0207"
            if self.game.state == "in_progress"
            else f"{Plugin.clean_text(self.bot_name)}|spectator|69|0|0207"
        )
        return team_status

    def handle_player_connect(self, player):
        self.recently_connected_steam_ids.add(player.steam_id)
        self._remove_recently_connected(player.steam_id)

    @minqlx.thread
    def _remove_recently_connected(self, steam_id):
        time.sleep(self.greeting_delay)
        if steam_id in self.recently_connected_steam_ids:
            self.recently_connected_steam_ids.remove(steam_id)

    def get_role_template(self, trigger):
        return self.__getattribute__(f"bot_role_{trigger}")

    @minqlx.thread
    def threaded_response(self, trigger):
        attribute = self.get_role_template(trigger)
        with self.queue_lock:
            if len(attribute) == 0:
                return
            message_history = self.contextualized_chat_history(
                self.get_role_template(trigger)
            )

            response = self._gather_completion(message_history)
            if response is None:
                return
            self._send_message(minqlx.CHAT_CHANNEL, response)

    def handle_game_countdown(self):
        if not self.game:
            return
        self.threaded_response("gamestart")

    def handle_round_start(self, _roundnumber):
        if not self.game:
            return
        self.threaded_response("roundstart")

    def handle_round_end(self, _data):
        if not self.game:
            return
        self.threaded_response("roundend")

        self._record_chat_line(
            f"Red: {self.game.red_score}, Blue: {self.game.blue_score}",
            lock=self.queue_lock,
        )

    def handle_game_end(self, _data):
        self.cache_map_authors_from_db()

        if not self.game:
            return
        self.threaded_response("gameend")

        mapname = self.game.map_title if self.game.map_title else self.game.map
        self._record_chat_line(
            f"Match ended {self.game.red_score}(red) - {self.game.blue_score}(blue) on {mapname}",
            lock=self.queue_lock,
        )

    def cmd_list_models(self, player, _msg, _channel):
        self._list_models_in_thread(player)

    @minqlx.thread
    def _list_models_in_thread(self, player):
        openai.api_key = self.bot_api_key
        available_models = Model.list()
        formatted_models = ", ".join(
            [model["id"] for model in available_models["data"]]
        )
        player.tell(f"Available models: {formatted_models}")

    def cmd_switch_model(self, player, msg, _channel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        self._switch_model_in_thread(player, msg[1])
        return minqlx.RET_NONE

    @minqlx.thread
    def _switch_model_in_thread(self, player, model):
        openai.api_key = self.bot_api_key
        available_models = Model.list()
        available_model_names = [model["id"] for model in available_models["data"]]

        if model not in available_model_names:
            formatted_models = ", ".join(available_model_names)
            player.tell(f"Model {model} not available. Currently using {self.model}")
            player.tell(f"Available models are: {formatted_models}")
            return

        if model == self.model:
            player.tell(f"I'm already using {self.model}, no switch necessary.")
            return

        self.model = model
        player.tell(f"Switched to openai model {self.model}")
