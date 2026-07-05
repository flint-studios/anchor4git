from typer import Argument, Option
from datetime import datetime
from typing import Optional

from ..consts import *
from ..utils import *

# Command for commit saving: `a4g save/s <MESSAGE>` #
def save_cmd(
    message: Optional[list[str]] = Argument(None, help="Message to describe changes."),
    preview: bool = Option(False, "--preview", help="Show what would be saved and exit."),
):
    """Save a snapshot of the entire repository."""

    # ───── SAFETY GATEWAY ────────────────────────────────────────────────── #
    if not is_repo(): die("Local repository does not exist. Get started by running 'a4g fetch <url>' first.")

    if detached(): die("This command is unavailable while actively using 'a4g goto'.")
    
    if not dirty(): return info("Nothing to save. Workspace is clean.")

    # ───── PREPARE DETAILS ────────────────────────────────────────────────── #
    timestmp = datetime.now().strftime("%y%m%d-%H%M%S")
    cfg = cfg_read()

    msg = " ".join(message or []) or f"anchor4git: Save {timestmp}"
    name = cfg.get("name") or DEFAULT_NAME
    email = cfg.get("email") or DEFAULT_EMAIL

    # ───── GIT COMMIT  ────────────────────────────────────────────────── #
    git("add", "."); git("reset", CONFIG_FILE)

    if preview:
        preview_block("General Details", [f"Message: {msg}", f"Author name: {name}", f"Author email: {email}"])
        preview_block("Changes", changes().splitlines())
        next_step("running the same command again without --preview to actually use it.")
        return

    git("commit", "-m", msg); ok(f'Saved: "{msg}"'); next_step("running 'a4g upload' when you are ready to publish.")