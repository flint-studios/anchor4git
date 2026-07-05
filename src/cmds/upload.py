from typer import Argument, Option

from ..utils import *
from ..consts import *

# Command for uploading: `a4g upload/u` #
def upload_cmd(
    branch: str = Argument("main", help="Branch to upload to."),
    force: bool = Option(False, "--force", help="Force upload without any safety checks."),
    preview: bool = Option(False, "--preview", help="Show what would happen and exit."),
):
    """Upload the repository to the remote repository."""

    # ───── SAFETY GATEWAY & INFORMATION GATHERING ────────────────────────────────────────────────── #
    if not is_repo(): die("Local repository does not exist. Get started by running 'a4g fetch <url>' first.")
    if detached(): die("This command is unavailable while actively using 'a4g goto'.")

    cfg = cfg_read()
    origin = cfg.get("origin_url") or die("Run 'a4g fetch <url>' first.")

    if not get_if_remote_empty(): git("fetch", origin, check=False)
    try: behind = int(git("rev-list", "--count", f"HEAD..FETCH_HEAD", check=False).stdout or "0")
    except Exception: behind = 0


    # ───── USER ASKED FOR PREVIEW ────────────────────────────────────────────────── #
    if preview:
        preview_block(
            "General Details",
            [
                f"Branch to upload to: {branch}" if branch != "main" else "",
                f"Force upload? {'Yes' if force else 'No'}",
                f"Remote has changes you don't? {'Yes' + (' (will be blocked)' if not force else ' (WON\'T be blocked)') if behind else 'No'}",
                f"Dirty workspace? {'Yes' + (' (will be saved)' if not force else ' (WON\'T be saved)') if dirty() else 'No'}",
                f"Conflicts: {', '.join(conflicts()) + (' (will be ignored)' if not force else '') if conflicts() else 'Nil'}",
            ],
        )
        next_step("running the same command again without --preview")
        return


    # ───── FORCED UPLOAD (NO BLOCKS) ────────────────────────────────────────────────── #
    if force:
        confirm_or_cancel(f"Force upload to {'remote' if 'main' else branch}? This will overwrite the remote history.")
        if dirty(): autosave("anchor4git: Auto-save before upload")
        git("push", "--force", origin, f"HEAD:refs/heads/{branch}")
        ok(f"Force-uploaded to {'remote' if 'main' else branch}.")
        next_step("running 'a4g info' to verify the repository state.")
        return


    # ───── BLOCKS ────────────────────────────────────────────────── #
    # Blocks if conflicts not resolved.
    if (c := conflicts()):
        warn("Resolve conflicts before uploading:")
        for f in c: print(f"     • {f}")
        return next_step("resolving all conflicts, running 'a4g save' and then try again.")

    # Block if behind remote.
    if behind: die(f"You're behind by {behind} save(s). Run 'a4g fetch' and try again.")


    # ───── PUSH SAFELY ────────────────────────────────────────────────── #
    if dirty(): autosave("anchor4git: Auto-save before upload")
    git("push", "--force", origin, f"HEAD:refs/heads/{branch}")
    ok(f"Uploaded to {'remote' if 'main' else branch}.")
    next_step("running 'a4g info' to verify the repository state.")