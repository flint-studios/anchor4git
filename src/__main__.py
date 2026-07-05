from typer import Typer
from rich import print
from sys import argv

from .utils import *
from .consts import *

# Import commands
from .cmds.info import info_cmd
from .cmds.save import save_cmd
from .cmds.fetch import fetch_cmd
from .cmds.upload import upload_cmd
from .cmds.goto import goto_cmd
from .cmds.config import config_cmd


# ───── TYPER INSTANCE ────────────────────────────────────────────────── #
app = Typer(
    help=f"Anchor4Git - {__description__}",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


# ───── COMMAND REGISTRATION ────────────────────────────────────────────────── #
app.command("info")(info_cmd)
app.command("i", hidden=True)(info_cmd)
app.command("dashboard", hidden=True)(info_cmd)

app.command("save")(save_cmd)
app.command("s", hidden=True)(save_cmd)

app.command("fetch")(fetch_cmd)
app.command("f", hidden=True)(fetch_cmd)

app.command("upload")(upload_cmd)
app.command("u", hidden=True)(upload_cmd)

app.command("goto")(goto_cmd)
app.command("g", hidden=True)(goto_cmd)

app.command("config")(config_cmd)
app.command("c", hidden=True)(config_cmd)


# ───── RUN CLI ────────────────────────────────────────────────── #
def main():
    args = argv[1:]

    if args and not args[0].startswith("-"):
        known = CMDS
        if args[0] not in known: suggest_command(args[0])

    app()