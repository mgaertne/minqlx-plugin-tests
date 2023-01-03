import time

import minqlx

from minqlx import Plugin


# noinspection PyPep8Naming
class cmdlist(Plugin):
    def __init__(self):
        super().__init__()

        self.add_command("cmdlist", self.cmd_cmdlist)

    def cmd_cmdlist(self, player, _msg, _channel):
        self.thread_reply(player)

    @minqlx.thread
    def thread_reply(self, player):
        available_commands = {  # type: ignore
            0: [],
            1: [],
            2: [],
            3: [],
            4: [],
            5: [],
        }

        for command in minqlx.COMMANDS.commands:
            if not command.is_eligible_player(player, False):
                continue
            if isinstance(command.name, str):
                if command.usage is not None:
                    available_commands[command.permission].append(f"{command.name} {command.usage}".strip())
                else:
                    available_commands[command.permission].append(command.name.strip())
            else:
                for name in command.name:
                    if command.usage is not None:
                        available_commands[command.permission].append(f"{name} {command.usage}".strip())
                    else:
                        available_commands[command.permission].append(name.strip())

        for level in range(0, 6):
            if len(available_commands[level]) == 0:
                continue

            level_colorcode = level % 6 + 1
            player.tell(f"^{level_colorcode}Permission level {level}^7 commands:")
            formatted_commands = f"^7, ^{level_colorcode}".join(available_commands[level])
            for line in minqlx.CHAT_CHANNEL.split_long_lines(formatted_commands, delimiter=","):
                player.tell(f"^{level_colorcode}  {line}")
                time.sleep(0.005)
