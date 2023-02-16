import re
from datetime import datetime, timedelta
from threading import RLock

import openai

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
    database = Redis  # type: ignore

    def __init__(self):
        super().__init__()

        self.queue_lock = RLock()
        self.set_cvar_once("qlx_openai_botname", "Bob")
        self.set_cvar_once("qlx_openai_clanprefix", "")
        self.set_cvar_once("qlx_openai_model", "text-davinci-003")
        self.set_cvar_once("qlx_openai_temperature", "0.5")
        self.set_cvar_once("qlx_openai_max_tokens", "28")
        self.set_cvar_once("qlx_openai_top_p", "1.0")
        self.set_cvar_once("qlx_openai_frequency_penalty", "0")
        self.set_cvar_once("qlx_openai_presence_penalty", "0")
        self.set_cvar_once("qlx_openai_prompt_template", "{chat_history}\n{bot_name}:")
        self.set_cvar_once("qlx_openai_chat_history_minutes", "10")
        self.set_cvar_once("qlx_openai_chat_history_length", "8")

        self.bot_api_key = self.get_cvar("qlx_openai_apikey")
        self.bot_name = self.get_cvar("qlx_openai_botname") or "Bob"
        self.bot_clanprefix = self.get_cvar("qlx_openai_clanprefix") or ""
        self.model = self.get_cvar("qlx_openai_model") or "text-davinci-003"
        self.temperature = self.get_cvar("qlx_openai_temperature", float) or 0.5
        if self.temperature < 0 or self.temperature > 2:
            self.temperature = 0.5
        self.max_tokens = self.get_cvar("qlx_openai_max_tokens", int) or 28
        self.top_p = self.get_cvar("qlx_openai_top_p", float) or 1.0
        if self.top_p < 0 or self.top_p > 2:
            self.top_p = 1.0
        self.frequency_penalty = self.get_cvar("qlx_openai_frequency_penalty", float) or 0.0
        if self.frequency_penalty < -2.0 or self.frequency_penalty > 2.0:
            self.frequency_penalty = 0.0
        self.presence_penalty = self.get_cvar("qlx_openai_presence_penalty", float) or 0.0
        if self.presence_penalty < -2.0 or self.presence_penalty > 2.0:
            self.presence_penalty = 0.0
        self.prompt_template = self.get_cvar("qlx_openai_prompt_template")
        self.chat_history_minutes = self.get_cvar("qlx_openai_chat_history_minutes", int) or 10
        self.chat_history_length = self.get_cvar("qlx_openai_chat_history_length", int) or 8

        self.add_hook("chat", self.handle_chat)

        self.add_command("listmodels", self.cmd_list_models, permission=5)
        self.add_command("switchmodel", self.cmd_switch_model, permission=5, usage="[modelname]")

    def handle_chat(self, player, msg, channel):
        @minqlx.thread
        def send_threaded_response(communication_channel, request):
            openai.api_key = self.bot_api_key

            with self.queue_lock:
                contextualized_prompt = self.contextualized_query(request)
                try:
                    completion = openai.Completion.create(
                        engine=self.model,
                        prompt=contextualized_prompt,
                        max_tokens=self.max_tokens,
                        n=1,
                        top_p=self.top_p,
                        stop=None,
                        temperature=self.temperature,
                        frequency_penalty=self.frequency_penalty,
                        presence_penalty=self.presence_penalty,
                    )
                except (openai.error.Timeout, openai.error.APIConnectionError):
                    return

                response = (
                    completion.choices[0]
                    .text.lstrip()
                    .rstrip()
                    .replace("\n", " ")
                    .replace("  ", " ")
                    .lstrip('"')
                    .rstrip('"')
                )
                if len(response) == 0:
                    return
                if response.startswith(f"{self.bot_name}: "):
                    response = response.replace(f"{self.bot_name}: ", "")
                self.db.zadd(
                    CHAT_BOT_LOG,
                    {f"{self.bot_name}: {response}": int(datetime.strftime(datetime.now(), DATETIMEFORMAT))},
                )
                period_start = datetime.now() - timedelta(minutes=self.chat_history_minutes)
                self.db.zremrangebyscore(CHAT_BOT_LOG, "-INF", datetime.strftime(period_start, DATETIMEFORMAT))

            communication_channel.reply(f"{self.bot_clanprefix}^7{self.bot_name}^7: ^2{response}")

            # noinspection PyProtectedMember
            if "mydiscordbot" in Plugin._loaded_plugins:
                # noinspection PyProtectedMember
                discord_plugin = Plugin._loaded_plugins["mydiscordbot"]
                # noinspection PyUnresolvedReferences
                discord_plugin.discord.relay_message(
                    Plugin.clean_text(f"**{self.bot_clanprefix}{self.bot_name}**: {response}")
                )

        reply_channel = identify_reply_channel(channel)
        pattern = rf"^{self.bot_name}\W|\W{self.bot_name}\W|\W{self.bot_name}$"
        if not re.search(pattern, msg, flags=re.IGNORECASE):
            return

        send_threaded_response(reply_channel, f"Player {player.clean_name}: {msg}")

    def contextualized_query(self, request):
        self.db.zadd(CHAT_BOT_LOG, {request: int(datetime.strftime(datetime.now(), DATETIMEFORMAT))})
        period_start = datetime.now() - timedelta(minutes=self.chat_history_minutes)
        chat_log = self.db.zrangebyscore(CHAT_BOT_LOG, datetime.strftime(period_start, DATETIMEFORMAT), "+INF")
        chat_history = "\n".join(chat_log[-self.chat_history_length:])
        return self.prompt_template.format(bot_name=self.bot_name, chat_history=chat_history)

    def cmd_list_models(self, player, _msg, _channel):
        self.list_models_in_thread(player)

    @minqlx.thread
    def list_models_in_thread(self, player):
        openai.api_key = self.bot_api_key
        available_models = openai.Model.list()
        formatted_models = ", ".join([model["id"] for model in available_models["data"]])
        player.tell(f"Available models: {formatted_models}")

    def cmd_switch_model(self, player, msg, _channel):
        if len(msg) != 2:
            return minqlx.RET_USAGE

        self.switch_model_in_thread(player, msg[1])
        return minqlx.RET_NONE

    @minqlx.thread
    def switch_model_in_thread(self, player, model):
        openai.api_key = self.bot_api_key
        available_models = openai.Model.list()
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
