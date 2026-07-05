from subprocess import CalledProcessError
from rich.console import Console
from sys import exit, stdout
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from ..utils import *
from ..consts import *


console = Console()

# Command for information dashboard: `a4g info/i/dashboard` #
def info_cmd():
    """Show rich information about the repository."""

    if not is_repo(): die("Not a repository. Start with 'a4g fetch <url>'.")

    # ───── INFORMATION COLLECTION  ────────────────────────────────────────────────── #
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description} {task.percentage:>3.0f}%"),
        transient=True,
    ) as progress:

        task = progress.add_task("[green]Fetching data...", total=100)

        if not get_if_remote_empty(): git("fetch", resolve_origin())
        git("add", "."); git("reset", CONFIG_FILE)

        progress.update(task, advance=10)

        try:
            ahead = int(git("rev-list", "--count", f"FETCH_HEAD..HEAD", check=True).stdout or "0")
            behind = int(git("rev-list", "--count", f"HEAD..FETCH_HEAD", check=True).stdout or "0")
            sync_text = human_sync(ahead, behind)
        except: ahead, behind, sync_text = 0, 0, "Can't get."

        progress.update(task, advance=10)

        cfg = cfg_read()

        progress.update(task, advance=10)

        branch = git("branch", "--show-current").stdout.strip()

        dirty_ = dirty(); status_text = "[green]CLEAN[/green]" if not dirty_ else "[red]DIRTY[/red]"

        progress.update(task, advance=10)

        try: last = git("log", "-1", "--pretty=format:%s (%ar)").stdout.strip()
        except: last = "No saves yet."

        progress.update(task, advance=10)

        # Get changes
        status = git("status", "--short").stdout.strip()

        progress.update(task, advance=10)

        # Get contributors
        try: authors = git("shortlog", "-sne", "HEAD", check=True).stdout.splitlines()
        except CalledProcessError: authors = []

        progress.update(task, advance=10)

        # Get full repo size
        size = "Unknown"
        for line in git("count-objects", "-vH").stdout.splitlines():
            if line.strip().startswith("size:"):
                size = line.split(":", 1)[1].strip(); break

        progress.update(task, advance=10)

        # Get commit history
        try: log = list(reversed( git("log", "--all", "--pretty=format:%h\t | %ar\t | %an\t | %ae\t | %s").stdout.splitlines() ))
        except: log = []

        progress.update(task, advance=10)

        try: head_short = git("rev-parse", "--short", "HEAD", check=True).stdout.strip() # Get current short commit id
        except: head_short = ""

        progress.update(task, advance=10)

    # ───── SHOW INFORMATION  ────────────────────────────────────────────────── #

    # HEADER PANEL
    print(Panel.fit(
        f"[bold]ANCHOR4GIT DASHBOARD[/bold]\n"
        f"[dim]Workspace:[/dim] {status_text}        "
        f"[dim]Sync:[/dim] {sync_text}        "
        f"[dim]Size:[/dim] {size}",
        border_style="cyan"
    ))


    # GENERAL INFORMATION TABLE
    table = Table(show_header=False, box=None)
    table.add_row("Remote Repository:", cfg.get("origin_url", "N/A"))
    table.add_row("Your Username:", cfg.get("name", "No name"))
    table.add_row("Your Email:", cfg.get("email", "no email"))
    table.add_row("Last Save:", last)

    print(table)

    # CONTRIBUTORS TABLE
    if authors:
        section_header("Contributors")
        for a in authors: print(f" • {a.replace(chr(9), ' ').strip()}")


    # CHANGES
    section_header("Changes in the workspace")
    if status: print(status)
    else: print("[dim]No changes[/dim]")


    # SAVE HISTORY /w SCROLL
    section_header("Saves History")

    if not log: print("[dim]No saves yet.[/dim]"); return

    log_count = len(log) # Count no. of logs
    FIRST_DISP_MAX = 5 # Number of entries to display at first (and then scroll)

    # Print first few entries
    for i in range(min(FIRST_DISP_MAX, log_count)):
        entry = log.pop()
        marker = ">>> " if head_short in entry else "" # Show if the current commit is the one you are on.
        print(f"{marker}{log_count:>3}. {entry}")
        log_count -= 1

    try:
        while log:
            print("\n[dim]Press Enter to continue, Ctrl+C to exit[/dim]", end="")
            input()

            entry = log.pop()
            marker = ">>> " if head_short in entry else ""

            # overwrite previous previous line
            stdout.write("\033[F\033[K\033[F\033[K")

            print(f"{marker}{log_count:>3}. {entry}")
            log_count -= 1

    except KeyboardInterrupt:
        stdout.write("\r\033[K")
        print("[dim]Cancelled.[/dim]")
        exit(0)

    print("\n[green]Done.[/green]")