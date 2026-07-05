from os import path, chmod, getenv, environ, startfile
from difflib import get_close_matches
from urllib.parse import urlparse
from subprocess import run, Popen
from typer import confirm, Exit
from sys import exit, platform
from json import loads, dumps
from stat import S_IWRITE
from shutil import rmtree
from pathlib import Path
from rich import print
import base64

from .consts import *

# ───── GIT HELPERS ────────────────────────────────────────────────── #

cfg_read = lambda: loads(Path(CONFIG_FILE).read_text()) if Path(CONFIG_FILE).exists() else {}
cfg_write = lambda d: Path(CONFIG_FILE).write_text(dumps(d, indent=2))

# Run any git command.
def git(*a, check=True):
    cfg = cfg_read()
    name = cfg.get("name") or run(["git", "config", "user.name"], text=True, capture_output=True, check=False).stdout.strip() or DEFAULT_NAME
    email = cfg.get("email") or run(["git", "config", "user.email"], text=True, capture_output=True, check=False).stdout.strip() or DEFAULT_EMAIL

    return run([
        "git",
        "-c", f'user.name="{name}"',
        "-c", f'user.email="{email}"',
        *a
        ], text=True, capture_output=True, check=check)

is_repo = lambda: path.isdir(".git")
dirty = lambda: bool(git("status", "--porcelain").stdout.strip())
changes = lambda: git("status", "--porcelain").stdout.strip()
conflicts = lambda: git("diff", "--name-only", "--diff-filter=U").stdout.split()
detached = lambda: not bool(git("branch", "--show-current").stdout.strip())
def delete_repo():
    def remove_readonly(func, path, excinfo): chmod(path, S_IWRITE); func(path) # Make read-only files writable
    if path.exists('.git'): rmtree('.git', onerror=remove_readonly)
    else: die("Unable to delete the Git repository. Please try to delete it manually.")

# Get origin URL (arg > saved > fail)
def resolve_origin(url = ""):
    origin = url or cfg_read().get("origin_url") or die("Anchor4Git not initalised. Run `a4g fetch <url>`.")

    u = urlparse(origin.strip()) # Is remote URL?
    
    if not (u.scheme and u.netloc): origin = str(Path(origin).resolve(False))  # local path fallback
    return origin

get_if_remote_empty = lambda origin = "": not git("ls-remote", resolve_origin(origin), check=True).stdout.strip()

# auto commit if there are changes
def autosave(msg="anchor4git: Auto-save workspace."):
    if dirty():
        git("add", "."); git("reset", CONFIG_FILE); git("commit", "-m", msg); ok("Auto-saved workspace.")

# ───── UI HELPERS ────────────────────────────────────────────────── #

# Print formatted log: [TEXT] Message...
def out(type, message, color="blue"): print(f"[bold white on bright_{color}] {type} [/] {message}")

# Styles of logs
ok = lambda s: out("SUCESS", s, "green")
info = lambda s: out("INFO", s, "cyan")
warn = lambda s: out("WARN", s, "yellow")
die = lambda s: (out("ERROR", s, "red"), exit(1))

def section_header(title: str): print(f"\n===== {title} =====") # Section header

def kv(key: str, value): print(f"- {key:<20} {value}") # KV printer

def next_step(text: str): print(); info(f"Next, try {text}") # Next step format

def confirm_or_cancel(prompt: str) -> None:
    if not confirm(prompt, default=False): info("Cancelled."); raise Exit(code=0)

def preview_block(title: str, lines: list[str]) -> None: # Format for preview blocks
    section_header(f"Preview: {title}")
    if not lines: print("- Nothing to show."); return
    for line in lines: print(line)

def human_sync(ahead: int, behind: int) -> str: # Convert ahead/behind numbers to easily understandable language
    if ahead == 0 and behind == 0: return "In sync."
    if ahead > 0 and behind == 0: return f"You have {ahead} unsynced save(s) on your end."
    if behind > 0 and ahead == 0: return f"You're behind by {behind} save(s). Run 'a4g fetch'"
    return f"{ahead} unsynced save(s) / behind by {behind} save(s)"

def suggest_command(raw: str) -> None: # Suggest command if a faulty command has been entered.
    commands = CMDS
    matches = get_close_matches(raw, commands, n=1)
    if matches: die(f"Unknown command '{raw}'. Did you mean '{matches[0]}'?")
    die(f"Unknown command '{raw}'")


def open_editor(filepath: str, blocking: bool = True) -> None: # Open a file in the user's default text editor.
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