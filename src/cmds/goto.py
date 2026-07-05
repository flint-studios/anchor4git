from subprocess import CalledProcessError
from typer import Argument, Option

from sys import exit
from ..utils import *


# Command for going to a previous save: `a4g goto/g` #
def goto_cmd(
    commit: str = Argument(None, help="Commit hash or HEAD."),
    reset: bool = Option(False, "--reset", help="Reset workspace to the commit."),
    stay: bool = Option(False, "--stay", help="Stay on the chosen commit."),
    preview: bool = Option(False, "--preview", help="Show what would happen and exit."),
):
    """Goto any previous save temporarily or permanently."""

    # ───── SAFETY GATEWAY ────────────────────────────────────────────────── #
    if not is_repo(): die("Not a git repository.")
    if not commit: die("Usage: a4g goto <commit> [--reset] [--stay]")

    # ───── RETURN TO HEAD ────────────────────────────────────────────────── #
    if commit == "HEAD":
        git("checkout", git("rev-parse", "--abbrev-ref", "@{-1}").stdout.strip())
        head_branch = git("branch", "--show-current").stdout.strip()
        ok(f"Returned to '{head_branch}'")
        try:
            if "stash@" in git("stash", "list").stdout:
                git("stash", "pop")
                ok("Restored previous changes.")
            else:
                info("No previous changes to restore.")

            exit(0)
        except CalledProcessError:
            exit(1)

        exit(1)

    if detached():
        die("This command is unavailable with a save ID while you are not on HEAD. First use `a4g goto HEAD`.")

    # ───── RESOLVE FULL COMMIT ID AND PRINT INFO ────────────────────────────────────────────────── #
    try: full = git("rev-parse", "--verify", commit).stdout.strip()
    except CalledProcessError: die(f"Invalid commit '{commit}'")

    head_branch = git("branch", "--show-current").stdout.strip()

    msg = git("log", "-1", "--pretty=format:%s (%h) by %an %ar", full).stdout
    info(f"Target commit: {msg}")

    # ───── SHOW PREVIEW ────────────────────────────────────────────────── #
    if preview:
        preview_block(
            "goto",
            [
                f"Commit: {commit}",
                f"Reset mode: {'yes' if reset else 'no'}",
                f"Stay mode: {'yes' if stay else 'no'}",
            ],
        )
        next_step("run the same command again without --preview")
        return

    # ───── RESET MODE ────────────────────────────────────────────────── #
    if reset:
        if dirty(): autosave(f"anchor4git: Auto Save before goto {commit}")

        confirm_or_cancel(f"Reset the workspace to {commit}? This is destructive.")
        warn(f"Resetting workspace to {commit}.")

        git("checkout", full, ".")
        git("clean", "-fd")
        final_commit_name = git("log", "-1", "--pretty=format:%s", full).stdout
        autosave(f"RESET of: {final_commit_name}")
        ok(f"Workspace reset to {commit}")
        next_step("run 'anchor4git save' to record new changes")
        return

    # ───── TEMPORARY/STAY MODE ────────────────────────────────────────────────── #
    stashed = False

    try:
        if dirty():
            git("stash", "push", "-u", "-m", "anchor-goto-temp")
            stashed = True
            info("Saved current changes somewhere safe. They will be restored when you return to HEAD.")

        git("checkout", full)
        ok(f"Now at {commit}.")

        if stay:
            info("Staying on this commit. Use 'a4g goto HEAD' to return.")
            return

        input("Press `Enter` to return to HEAD... ")

    finally:
        if not stay:
            git("checkout", head_branch)

            if stashed:
                try:
                    git("stash", "pop")
                    ok("Restored previous changes.")
                except CalledProcessError:
                    warn("Could not auto-apply stash. Run 'git stash list'.")

            ok(f"Returned to '{head_branch}'")