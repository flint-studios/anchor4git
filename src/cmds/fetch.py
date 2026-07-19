from subprocess import CalledProcessError
from typer import Argument, Option
from typing import Optional
from pathlib import Path
from rich import print

from ..consts import *
from ..utils import *


def fetch_cmd(
    url: Optional[str] = Argument(None, help="Origin repository URL or local path."),
    force: bool = Option(False, "--force", help="Replace local workspace with origin."),
    preview: bool = Option(False, "--preview", help="Show what would happen and exit."),
):
    """Fetch content from a origin repository."""

    # ───── SAFETY GATEWAY & SETUP ────────────────────────────────────────────────── #
    git_existance_safety()
    detached_safety()

    cfg = cfg_read()
        
    origin = resolve_origin(url)

    origin_empty = get_if_origin_empty(origin)

    repo_missing = not is_repo() # Is local rrepository missing RIGHT NOW?

    # Create repo if missing
    if repo_missing:
        create_repo()
    
    generate_config(origin=origin, refresh=True)


    # ───── USER ASKED FOR PREVIEW ────────────────────────────────────────────────── #
    if preview:
        # If origin has files.
        if not origin_empty: 
            git("fetch", origin)

            # Get changes
            diff = git("diff", "--name-only", "FETCH_HEAD").stdout.strip().splitlines()

        # Display preview block
        preview_block(
            "General Details",
            [
                f"Origin Repository URL: {origin}",
                f"Force replace? {'Yes' if force else 'No'}",
                f"A repository exists locally? {'Yes' if not repo_missing else 'No (will be created)'}",
                f"Origin repository is empty? {'Yes' if origin_empty else 'No'}",
                f"Dirty workspace? {'Yes (will be saved)' if dirty() else 'No'}",
            ],
        )

        if origin_empty: print("\nThe origin repository is empty.\n")
        
        else:
            preview_block(
                "Differences",
                diff
            )
            print()

        if repo_missing: delete_repo() # If repo WAS missing before, delete it
        
        next_step("running the same command again without --preview to actually use it.")

        return # to exit the command


    # ───── ORIGIN IS EMPTY ────────────────────────────────────────────────── #
    if origin_empty:
        ok("Origin repository is empty. Nothing to download. Start working.")
        next_step(f"running '{__title__} save' when you have changes, and '{__title__} upload' to publish them.")
        
        return # to exit the command


    # ───── ORIGIN NOT EMPTY ────────────────────────────────────────────────── #
    autosave("anchor4git: Auto-save before fetch")

    # Fetch
    info(f"Fetching from {origin}")
    git("fetch", origin)

    # force = overwrite everything
    if force:
        confirm_or_cancel(f"Replace the current workspace with '{origin}'?")

        git("reset", "--hard", f"FETCH_HEAD")
        git("clean", "-fd")
        
        ok("Workspace replaced with the origin repository.")
        next_step(f"running '{__title__} save' after making local changes or '{__title__} upload' if you want to publish.")
        
        return


    # Try to merge normally
    try:
        commit_msg = "Merge origin repository."

        git("merge", f"FETCH_HEAD", "--allow-unrelated-histories", "-m", commit_msg)

        # Rewrite the author details in the commit to maintain consistency
        last_commit_message = git("log", "-1", "--pretty=format:%s").stdout.strip()

        if not conflicts() and last_commit_message == commit_msg:
            git("commit", "--amend", "--no-edit", "--reset-author")

        ok("Workspace updated.")
        next_step(f"running '{__title__} upload' to publish your work after you have made changes.")


    except CalledProcessError:
        c = conflicts()

        if not c: die("Merge failed. Check 'git status'.")

        warn("Conflicts detected:")
        
        for f in c:
            print(f"\t• {f}")
        
        print()
        
        warn(f"Resolve the conflicts, then run: '{__title__} save' [HIGHLY IMPORTANT]")        
    