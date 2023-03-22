# noinspection PyPackageRequirements
from discord.ext.commands import Cog


from minqlx import Plugin


def int_set(string_set):
    returned = set()  # type: ignore

    if string_set is None:
        return returned

    for item in string_set:
        if item == "":
            continue
        value = int(item)
        returned.add(value)

    return returned


class OpenAIBridge(Cog):
    def __init__(self, bot):
        self.bot = bot

        Plugin.set_cvar_once("qlx_openai_botname", "Bob")
        Plugin.set_cvar_once("qlx_openai_clanprefix", "")
        Plugin.set_cvar_once("qlx_openai_bot_triggers", "")
        Plugin.set_cvar_once("qlx_openai_bot_role_chat", "")

        self.bot_name = Plugin.get_cvar("qlx_openai_botname") or "Bob"
        self.bot_clanprefix = Plugin.get_cvar("qlx_openai_clanprefix") or ""
        self.bot_triggers = Plugin.get_cvar("qlx_openai_bot_triggers", list) or []
        self.bot_triggers = [
            trigger for trigger in self.bot_triggers if len(trigger) > 0
        ]
        self.bot_role_chat = (
            Plugin.get_cvar("qlx_openai_bot_role_chat")
            .encode("raw_unicode_escape")
            .decode("unicode_escape")
        )

    @Cog.listener(name="on_message")
    async def on_message(self, message):
        discord_relay_channel_ids = int_set(
            Plugin.get_cvar("qlx_discordRelayChannelIds", set)
        )

        if message.channel.id not in discord_relay_channel_ids:
            return

        if self.bot.user is None or message.author.id == self.bot.user.id:
            return

        # noinspection PyProtectedMember
        if "openai_bot" not in Plugin._loaded_plugins:
            return

        # noinspection PyProtectedMember
        openai_bot_plugin = Plugin._loaded_plugins["openai_bot"]

        # noinspection PyUnresolvedReferences
        with openai_bot_plugin.queue_lock:
            author_name = (
                message.author.display_name
                if message.author.display_name
                else message.author.name
            )
            request = f"{author_name}: {message.content}"

            # noinspection PyUnresolvedReferences
            if not openai_bot_plugin.is_triggered_message(message.content):
                # noinspection PyProtectedMember,PyUnresolvedReferences
                openai_bot_plugin._record_chat_line(
                    request, lock=openai_bot_plugin.queue_lock
                )
                return

            # noinspection PyUnresolvedReferences
            message_history = openai_bot_plugin.contextualized_chat_history(
                request, trigger_template=self.bot_role_chat
            )
            # noinspection PyProtectedMember,PyUnresolvedReferences
            openai_bot_plugin._record_chat_line(
                request, lock=openai_bot_plugin.queue_lock
            )

            # noinspection PyProtectedMember,PyUnresolvedReferences
            response = openai_bot_plugin._gather_completion(message_history)
            if response is None:
                return
            # noinspection PyProtectedMember,PyUnresolvedReferences
            openai_bot_plugin._record_chat_line(
                f"{Plugin.clean_text(self.bot_name)}: {response}",
                lock=openai_bot_plugin.queue_lock,
            )
            # noinspection PyProtectedMember,PyUnresolvedReferences
            Plugin.msg(
                f"{self.bot_clanprefix}^7{self.bot_name}^7: "
                f"^2{openai_bot_plugin._ql_cleaned_up(response)}"
            )
            await message.channel.send(
                content=Plugin.clean_text(
                    f"{self.bot_clanprefix}{self.bot_name}: {response}"
                )
            )


async def setup(bot):
    # noinspection PyTypeChecker
    await bot.add_cog(OpenAIBridge(bot))
