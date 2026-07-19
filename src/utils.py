from os import path, chmod, getenv, environ, startfile
from difflib import get_close_matches
from urllib.parse import urlparse
from subprocess import run, Popen
from shutil import rmtree, which
from typer import confirm, Exit
from sys import exit, platform
from json import loads, dumps
from stat import S_IWRITE
from pathlib import Path
from rich import print

from .consts import *


# ───── CONFIG FILE OPS HANDLER ────────────────────────────────────────────────── #

cfg_read = lambda: loads(Path(CONFIG_FILE).read_text()) if Path(CONFIG_FILE).exists() else {}
cfg_write = lambda d: Path(CONFIG_FILE).write_text(dumps(d, indent=2))


# ───── GIT EXECUTABLE GATEWAY ────────────────────────────────────────────────── #

def git(*a, check: bool = True):
    """Run any git command with auto author details injection."""

    cfg = cfg_read()

    # Get author name and email
    # Precedence: CONFIG > GIT DEFAULTS > PRESET DEFAULT
    name = cfg.get("name") or run(["git", "config", "user.name"], text=True, capture_output=True, check=False).stdout.strip() or DEFAULT_NAME
    email = cfg.get("email") or run(["git", "config", "user.email"], text=True, capture_output=True, check=False).stdout.strip() or DEFAULT_EMAIL

    return run([
        "git",
        "-c", f'user.name="{name}"',
        "-c", f'user.email="{email}"',
        *a
        ], text=True, capture_output=True, check=check)


# Git repo management helper functions
is_repo = lambda: path.isdir(".git")
dirty = lambda: bool(git("status", "--porcelain").stdout.strip()) # True if changes returns nothing
changes = lambda: git("status", "--porcelain").stdout.strip() # List changes
conflicts = lambda: git("diff", "--name-only", "--diff-filter=U").stdout.split() # List conflicts if any
detached = lambda: not bool(git("branch", "--show-current").stdout.strip()) # Bool for if on HEAD or not
get_if_origin_empty = lambda origin = "": not git("ls-remote", resolve_origin(origin), check=True).stdout.strip()


def resolve_origin(url: str = "") -> str:
    """
    Get/Resolve origin URL from various sources and fallbacks
    Precedence: USER PROVIDED > CONFIG > FAIL
                NETWORK URL > LOCAL FILEPATH
    """

    # Get URL
    origin = url or cfg_read().get("origin_url") or die("Origin repository not initalised. Run `{__title__} fetch <url>`.")

    u = urlparse(origin.strip()) # Is remote URL?
    
    if not (u.scheme and u.netloc): # NO
        origin = str(Path(origin).resolve(False))  # local path fallback

    # YES
    return origin


def create_repo(default_branch: str = "main") -> None:
    git("init", "-b", default_branch)
    ok("Initialised new repository.")


def generate_config(origin:str = "", default_branch: str = "main", refresh: bool = False) -> None:
    cfg = cfg_read()

    # name & email: GIT DEFAULTS > PPRESET DEFAULT
    if refresh:
        cfg.update(
                name = cfg.get("name", None) or run(["git", "config", "user.name"], text=True, capture_output=True).stdout.strip() or DEFAULT_NAME,
                email = cfg.get("email", None) or run(["git", "config", "user.email"], text=True, capture_output=True).stdout.strip() or DEFAULT_EMAIL,
                origin_url = origin,
                default_branch= default_branch
                )
    else:
        cfg.update(
                name = run(["git", "config", "user.name"], text=True, capture_output=True).stdout.strip() or DEFAULT_NAME,
                email = run(["git", "config", "user.email"], text=True, capture_output=True).stdout.strip() or DEFAULT_EMAIL,
                origin_url = origin,
                default_branch= default_branch
                )

    cfg_write(cfg)


def delete_repo() -> None:
    def remove_readonly(func, path, excinfo):
        """Make read-only files writable by editing perms"""
        chmod(path, S_IWRITE); func(path)

    if path.exists('.git'): rmtree('.git', onerror=remove_readonly)
    else: die("Unable to delete the Git repository. Please try to delete it manually.")


def autosave(msg: str = "anchor4git: Auto-save workspace.") -> None:
    """Auto create a commit only if there are changes."""
    if dirty():
        git("add", "."); git("reset", CONFIG_FILE); git("commit", "-m", msg); ok("Auto-saved workspace.")


# ───── SAFETY GATEWAY ────────────────────────────────────────────────── #

def git_existance_safety() -> None:
    if which("git") is None: die("Git executable not found. Please install git by visiting 'https://git-scm.com/'.")


def repo_existance_safety() -> None:
    if not is_repo(): die(f"Local repository does not exist. Get started by running '{__title__} fetch <url>' first.")


def detached_safety() -> None:
    if is_repo():
        if detached(): die(f"This command is unavailable while actively using '{__title__} goto'.")


# ───── UI HELPERS ────────────────────────────────────────────────── #

# Print formatted log: [TEXT] Message...
def log(message: str, type: str = "MSG", color: str = "blue") -> None:
    print(f"[bold white on bright_{color}] {type} [/] {message}")


# Styles of logs
ok = lambda s: log(s, "SUCESS", "green")
info = lambda s: log(s, "INFO", "cyan")
warn = lambda s: log(s, "WARN", "yellow")
die = lambda s: (log(s, "ERROR", "red"), exit(1))

def section_header(title: str) -> None: print(f"\n===== {title} =====") # Section header

def kv(key: str, value) -> None: print(f"- {key:<20} {value}") # KV printer

def next_step(text: str) -> None: print(); info(f"Next, try {text}") # Next step format

def confirm_or_cancel(prompt: str) -> None:
    """Confirmation prompt"""
    if not confirm(prompt, default=False): info("Cancelled."); raise Exit(code=0)

def preview_block(title: str, lines: list[str]) -> None:
    """Format for preview blocks"""
    section_header(f"Preview: {title}")
    if not lines: print("- Nothing to show."); return
    for line in lines: print(line)


def human_sync(ahead: int, behind: int) -> str:
    """Convert ahead/behind numbers to easily understandable language"""

    if ahead == 0 and behind == 0: return "In sync."
    if ahead > 0 and behind == 0: return f"You have {ahead} unsynced save(s) on your end."
    if behind > 0 and ahead == 0: return f"You're behind by {behind} save(s). Run '{__title__} fetch'"
    return f"{ahead} unsynced save(s) / behind by {behind} save(s)"


def suggest_command(raw: str) -> None:
    """Suggest command if a faulty command has been entered."""

    commands = CMDS
    matches = get_close_matches(raw, commands, n=1)
    if matches: die(f"Unknown command '{raw}'. Did you mean '{matches[0]}'?")
    die(f"Unknown command '{raw}'")


# ───── FILESYSTEM OPS ────────────────────────────────────────────────── #

def open_editor(filepath: str, blocking: bool = True) -> None:
    """Open a file in the user's default text editor."""

    if not path.exists(filepath): raise FileNotFoundError(f"File not found: {filepath}")

    if platform.startswith('win'):
        if blocking: run(['start', '', filepath], shell=True)
        else: startfile(filepath)
    
    elif sys.platform == 'darwin':
        if blocking: run(['open', filepath])
        else: Popen(['open', filepath])
    
    else:
        editor = environ.get('EDITOR') or environ.get('VISUAL')
        if editor:
            try:
                if blocking: run([editor, filepath])
                else: Popen([editor, filepath])
                return
            except FileNotFoundError: pass

        if blocking: run(['xdg-open', filepath])
        else: Popen(['xdg-open', filepath])

