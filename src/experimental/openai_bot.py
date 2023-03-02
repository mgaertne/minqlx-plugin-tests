"""
This is a plugin created by ShiN0
Copyright (c) 2023 ShiN0
<https://www.github.com/mgaertne/minqlx-plugin-tests>

You are free to modify this plugin to your own one.

You need to install openai in your python installation, i.e. python3 -m pip install -U openai
"""
import re
from datetime import datetime, timedelta
from threading import RLock

import openai
from openai import OpenAIError, Model, ChatCompletion

import minqlx
from minqlx import (
    Plugin,
    CHAT_CHANNEL,
    FREE_CHAT_CHANNEL,
    SPECTATOR_CHAT_CHANNEL,
    BLUE_TEAM_CHAT_CHANNEL,
    RED_TEAM_CHAT_CHANNEL,
)
from minqlx.database import Redis

DATETIMEFORMAT = "%Y%m%d%H%M%S"

CHAT_BOT_LOG = "minqlx:openai_bot:log"


def identify_reply_channel(channel):
    if channel in [
        RED_TEAM_CHAT_CHANNEL,
        BLUE_TEAM_CHAT_CHANNEL,
        SPECTATOR_CHAT_CHANNEL,
        FREE_CHAT_CHANNEL,
    ]:
        return CHAT_CHANNEL

    return channel


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
    * qlx_openai_model (default: "gpt-3.5-turbo") The AI model used for creating chat interactions.
    * qlx_openai_temperature (default: 1.0) What sampling temperature to use, between 0 and 2.
    * qlx_openai_max_tokens (default: 100, max: 4096) The maximum amount of tokens a completion may consume. Note that
            tokens are consumed for the prompt and completion combined.
    * qlx_openai_top_p (default: 1.0) An alternative to sampling with temperature, called nucleus sampling.
    * qlx_openai_frequency_penalty (default: 0.0) Number between -2.0 and 2.0. Positive values penalize new tokens
            based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same
            line verbatim.
    * qlx_openai_presence_penalty (default: 0.0) Number between -2.0 and 2.0. Positive values penalize new tokens
            based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.
    * qlx_openai_system_context A template string that provides the overall system context for the chat. You can use
            {bot_name} to dynamically fill in the name of the bot here
            Defaults to: "You are {bot_name}, a spectator on a QuakeLive server."
    * qlx_openai_chat_history_minutes (default: 10) Conversations with the bot from the past x minutes will be included
            in the chat_history.
    * qlx_openai_chat_history_length (default: 8) Maximum number of previous conversations to include in the
            chat_history.

    Previously used cvars that have become obsolete and are no longer used/supported:
    * qlx_openai_prompt_template feed the relevant parts into qlx_openai_system_context. The chat history is
            automatically provided per the ChatCompletion API request. You no longer need to provide this on your own.
    """

    database = Redis  # type: ignore

    def __init__(self):
        super().__init__()

        self.queue_lock = RLock()
        self.set_cvar_once("qlx_openai_botname", "Bob")
        self.set_cvar_once("qlx_openai_clanprefix", "")
        self.set_cvar_once("qlx_openai_model", "gpt-3.5-turbo")
        self.set_cvar_limit_once("qlx_openai_temperature", 1.0, 0.0, 2.0)
        self.set_cvar_limit_once("qlx_openai_max_tokens", 100, 0, 4096)
        self.set_cvar_limit_once("qlx_openai_top_p", 1.0, 0.0, 2.0)
        self.set_cvar_limit_once("qlx_openai_frequency_penalty", 0.0, -2.0, 2.0)
        self.set_cvar_limit_once("qlx_openai_presence_penalty", 0.0, -2.0, 2.0)
        self.set_cvar_once("qlx_openai_system_context", "You are {bot_name}, a spectator on a QuakeLive server.")
        self.set_cvar_once("qlx_openai_chat_history_minutes", "10")
        self.set_cvar_once("qlx_openai_chat_history_length", "8")

        self.bot_api_key = self.get_cvar("qlx_openai_apikey")
        self.bot_name = self.get_cvar("qlx_openai_botname") or "Bob"
        self.bot_clanprefix = self.get_cvar("qlx_openai_clanprefix") or ""
        self.model = self.get_cvar("qlx_openai_model") or "gpt-3.5-turbo"
        self.temperature = self.get_cvar("qlx_openai_temperature", float) or 1.0
        if self.temperature < 0 or self.temperature > 2:
            self.temperature = 1.0
        self.max_tokens = self.get_cvar("qlx_openai_max_tokens", int) or 100
        self.top_p = self.get_cvar("qlx_openai_top_p", float) or 1.0
        if self.top_p < 0 or self.top_p > 2:
            self.top_p = 1.0
        self.frequency_penalty = self.get_cvar("qlx_openai_frequency_penalty", float) or 0.0
        if self.frequency_penalty < -2.0 or self.frequency_penalty > 2.0:
            self.frequency_penalty = 0.0
        self.presence_penalty = self.get_cvar("qlx_openai_presence_penalty", float) or 0.0
        if self.presence_penalty < -2.0 or self.presence_penalty > 2.0:
            self.presence_penalty = 0.0
        self.system_context = (
            self.get_cvar("qlx_openai_system_context").encode("raw_unicode_escape").decode("unicode_escape")
        )
        self.chat_history_minutes = self.get_cvar("qlx_openai_chat_history_minutes", int) or 10
        self.chat_history_length = self.get_cvar("qlx_openai_chat_history_length", int) or 8

        self.add_hook("chat", self.handle_chat)

        self.add_command("listmodels", self.cmd_list_models, permission=5)
        self.add_command("switchmodel", self.cmd_switch_model, permission=5, usage="[modelname]")

    def summarize_game_end_stats(self, announcements):
        @minqlx.thread
        def threaded_summary(messages):
            response = self._gather_completion(messages)
            if response is None:
                return
            response = response.replace("%", " percent")
            self._send_message(minqlx.CHAT_CHANNEL, response)

        contextualized_messages = [
            {"role": "system", "content": self.system_context},
            {"role": "user", "content": f"Summarize in short using slang and sarcasm:\n{announcements}."}
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
        return self._pick_choice_and_cleanup(completion)

    def _pick_choice_and_cleanup(self, completion):
        response = completion.choices[0]["message"]["content"]
        if len(response) == 0:
            return None
        if response.startswith(f"{self.bot_name}: "):
            response = response.replace(f"{self.bot_name}: ", "")
        return response

    def _record_chat_line(self, message, *, lock):
        with lock:
            self.db.zadd(CHAT_BOT_LOG, int(datetime.strftime(datetime.now(), DATETIMEFORMAT)), message)

    def _send_message(self, communication_channel, message):
        communication_channel.reply(f"{self.bot_clanprefix}^7{self.bot_name}^7: ^2{message}")

        # noinspection PyProtectedMember
        if "mydiscordbot" in Plugin._loaded_plugins:
            # noinspection PyProtectedMember
            discord_plugin = Plugin._loaded_plugins["mydiscordbot"]
            # noinspection PyUnresolvedReferences
            discord_plugin.discord.relay_message(
                Plugin.clean_text(f"**{self.bot_clanprefix}{self.bot_name}**: {message}")
            )

    def handle_chat(self, player, msg, channel):
        @minqlx.thread
        def threaded_response(communication_channel, chatter, message):
            request = f"{chatter.clean_name}: {message}"
            with self.queue_lock:
                message_history = self.contextualized_chat_history(request)
                response = self._gather_completion(message_history)
                self._record_chat_line(request, lock=self.queue_lock)
                if response is None:
                    return
                self._record_chat_line(f"{self.bot_name}: {response}", lock=self.queue_lock)
                self._send_message(communication_channel, response)

        reply_channel = identify_reply_channel(channel)
        pattern = rf"^{self.bot_name}\W|\W{self.bot_name}\W|\W{self.bot_name}$"
        if not re.search(pattern, msg, flags=re.IGNORECASE):
            return

        threaded_response(reply_channel, player, msg)

    def contextualized_chat_history(self, request):
        period_start = datetime.now() - timedelta(minutes=self.chat_history_minutes)
        chat_log = self.db.zrangebyscore(CHAT_BOT_LOG, datetime.strftime(period_start, DATETIMEFORMAT), "+INF")
        chat_history_messages = [{"role": "system", "content": self.system_context.format(bot_name=self.bot_name)}]
        for message in chat_log[-self.chat_history_length:]:
            role = "assistant" if message.startswith(self.bot_name) else "user"
            chat_history_messages.append({"role": role, "content": message})
        chat_history_messages.append({"role": "user", "content": request})
        return chat_history_messages

    def cmd_list_models(self, player, _msg, _channel):
        self._list_models_in_thread(player)

    @minqlx.thread
    def _list_models_in_thread(self, player):
        openai.api_key = self.bot_api_key
        available_models = Model.list()
        formatted_models = ", ".join([model["id"] for model in available_models["data"]])
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
