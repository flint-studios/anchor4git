from pathlib import Path

from ..consts import *
from ..utils import *

# Command for commit saving: `a4g save/s <MESSAGE>` #
def config_cmd():
    """Open the defaut text editor app with the project config open."""

    # ───── SAFETY GATEWAY ────────────────────────────────────────────────── #
    if not is_repo(): die("Local repository does not exist. Get started by running 'a4g fetch <url>' first.")

    open_editor(Path(CONFIG_FILE))