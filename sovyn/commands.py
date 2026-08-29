from enum import StrEnum, unique


@unique
class SlashCommand(StrEnum):
    HELP = "help"
    MODEL = "model"
    STATUS = "status"
    TOOLS = "tools"
    PERMISSIONS = "permissions"
    HISTORY = "history"
    UNDO = "undo"
    WORKFLOWS = "workflows"
    DEBUG = "debug"
    CLEAR = "clear"
    STATS = "stats"
    EXIT = "exit"


def parse_slash_command(value: str) -> SlashCommand | None:
    stripped = value.strip()
    if not stripped.startswith("/"):
        return None
    name = stripped[1:].split(maxsplit=1)[0].lower()
    if name == "quit":
        return SlashCommand.EXIT
    try:
        return SlashCommand(name)
    except ValueError:
        return None
