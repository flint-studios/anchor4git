from subprocess import CalledProcessError
from typer import Argument, Option
from typing import Optional
from pathlib import Path
from rich import print

from ..consts import *
from ..utils import *


# Command for fetching changes: `a4g fetch/f <URL>` #
def fetch_cmd(
    url: Optional[str] = Argument(None, help="Remote Repository URL or local path."),
    force: bool = Option(False, "--force", help="Replace local workspace with origin."),
    preview: bool = Option(False, "--preview", help="Show what would happen and exit."),
):
    """Fetch content from another repository."""

    # ───── SAFETY GATEWAY & SETUP ────────────────────────────────────────────────── #
    if is_repo():
        if detached(): die(f"This command is unavailable while actively using '{__title__} goto'.")

    cfg = cfg_read()
    
    origin = resolve_origin(url)

    is_remote_empty = get_if_remote_empty(origin)

    repo_missing = not is_repo()

    # init repo if missing
    if repo_missing:
        git("init", "-b", "main")
        cfg.update(name=run(["git", "config", "user.name"], text=True, capture_output=True).stdout.strip() or DEFAULT_NAME)
        cfg.update(email=run(["git", "config", "user.email"], text=True, capture_output=True).stdout.strip() or DEFAULT_EMAIL)
        ok("Initialised new repository.")

    # ───── USER ASKED FOR PREVIEW ────────────────────────────────────────────────── #
    if preview:
        if not is_remote_empty:
            git("fetch", origin)
            diff = git("diff", "--name-only", "FETCH_HEAD").stdout.strip().splitlines()

        preview_block(
            "General Details",
            [
                f"Remote Repository URL: {origin}",
                f"Force replace? {'Yes' if force else 'No'}",
                f"A repository exists locally? {'Yes' if not repo_missing else 'No (will be created)'}",
                f"Remote repository is empty? {'Yes' if is_remote_empty else 'No'}",
                f"Dirty workspace? {'Yes (will be saved)' if dirty() else 'No'}",
            ],
        )
        if is_remote_empty: print("\nThe remote repository is empty.\n")
        else:
            preview_block(
                "Differences",
                diff
            )
            print()

        if repo_missing: delete_repo(); ok("Deleted Repository.")

        next_step("running the same command again without --preview to actually use it.")
        return

    # store config
    cfg.update(origin_url = origin)
    cfg.setdefault("default_branch", "main")

    cfg_write(cfg)

    # ───── REMOTE IS EMPTY ────────────────────────────────────────────────── #
    if is_remote_empty:
        ok("Remote repository is empty. Nothing to download. Start working.")
        next_step("running 'a4g save' when you have changes, and 'a4g upload' to publish them.")
        return

    # ───── REMOTE NOT EMPTY ────────────────────────────────────────────────── #
    if dirty(): autosave("anchor4git: Auto-save before fetch")

    # Fetch
    info(f"Fetching from {origin}"); git("fetch", origin)

    # force = overwrite everything
    if force:
        confirm_or_cancel(f"Replace the current workspace with '{origin}'?")
        git("reset", "--hard", f"FETCH_HEAD")
        git("clean", "-fd")
        ok("Workspace replaced with the remote repository.")
        next_step("running 'a4g save' after making local changes or 'a4g upload' if you want to publish.")
        return

    # merge normally
    try:
        cfg = cfg_read()
        name = cfg.get("name") or DEFAULT_NAME
        email = cfg.get("email") or DEFAULT_EMAIL

        git("merge", f"FETCH_HEAD", "--allow-unrelated-histories", "-m", "Merge remote repository.")
        last_commit_message = git("log", "-1", "--pretty=format:%s").stdout.strip()
        if not conflicts() and last_commit_message == "Merge remote repository.": git("commit", "--amend", "--no-edit", "--reset-author")
        ok("Workspace updated.")
        next_step("running 'a4g upload' to publish your work after you have made changes.")

    except CalledProcessError:
        c = conflicts()
        if not c:
            die("Merge failed. Check 'git status'.")
        warn("Conflicts detected:")
        for f in c:
            print(f"\t• {f}")
        print()
        warn("Resolve the conflicts, then run: 'a4g save' [HIGHLY IMPORTANT]")