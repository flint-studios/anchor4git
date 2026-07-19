# Architecture

Anchor4Git is a Python CLI tool that wraps Git into a simplified **Download → Edit → Upload** workflow for small, trusted teams (2-4 people). Users never need to know Git commands.

## Core Design Principles

| Principle                     | Explanation                                                                 |
| ----------------------------- | --------------------------------------------------------------------------- |
| **No Git knowledge required** | Users interact with `ag fetch`, `ag save`, `ag upload`. That's it.       |
| **Workspace-first**           | Users edit files normally in their editor. Anchor4Git handles versioning.   |
| **Auto-save before risk**     | Dirty workspaces are committed automatically before destructive operations. |
| **Force-push model**          | Always `git push --force`. No push-rejection errors for small trusted teams.|
| **Conflicts in editor**       | Merge conflicts are surfaced as file markers; users resolve in their editor.|
| **Typo-tolerant CLI**         | Unknown commands are corrected via fuzzy matching (`difflib`).              |

---

## Project Structure

```
anchor4git/
├── src/                           # Main Python package
│   ├── __init__.py                # Package exports: main(), consts
│   ├── __main__.py                # CLI entry point — Typer app + command registration
│   ├── consts.py                  # Constants: version, command list, defaults
│   ├── utils.py                   # Git gateway, config I/O, safety gates, UI helpers
│   └── cmds/                      # CLI command implementations (one file per command)
│       ├── init.py                # ag init / i
│       ├── info.py                # ag info / d / dashboard
│       ├── save.py                # ag save / s
│       ├── fetch.py               # ag fetch / f
│       ├── upload.py              # ag upload / u
│       ├── goto.py                # ag goto / g
│       └── config.py              # ag config / c
├── tests/
│   ├── conftest.py                # pytest session hook — cleans temp dir on success
│   └── test_cmds.py               # Integration tests for all commands
├── .github/workflows/
│   └── upload.yml                 # CI/CD: manual-trigger build + PyPI + GitHub Release
├── pyproject.toml                 # Build system, dependencies, entry points
└── uv.lock                        # Dependency lock file (uv)
```

---

## CLI Architecture (Entry Point Chain)

```
Terminal: ag <command> [args]
    │
    ▼
pyproject.toml [project.scripts]
    "ag = src:main"
    "anchor4git = src:main"
    │
    ▼
src/__init__.py
    └── from .__main__ import main
    │
    ▼
src/__main__.py :: main()
    │
    ├── 1. Parse sys.argv[1:] before Typer runs
    ├── 2. If first arg is NOT a known command and doesn't start with "-":
    │       └── suggest_command(raw)     ← difflib.get_close_matches()
    │            └── die() if no close match found
    └── 3. app()   (Typer instance handles routing)
               │
               ├── "init"     → init_cmd()
               ├── "i"        → init_cmd()     (hidden alias)
               ├── "info"     → info_cmd()
               ├── "d"        → info_cmd()     (hidden)
               ├── "dashboard"→ info_cmd()     (hidden)
               ├── "save"     → save_cmd()
               ├── "s"        → save_cmd()     (hidden)
               ├── "fetch"    → fetch_cmd()
               ├── "f"        → fetch_cmd()    (hidden)
               ├── "upload"   → upload_cmd()
               ├── "u"        → upload_cmd()   (hidden)
               ├── "goto"     → goto_cmd()
               ├── "g"        → goto_cmd()    (hidden)
               ├── "config"   → config_cmd()
               └── "c"        → config_cmd()  (hidden)
```

### How commands are registered

In `src/__main__.py`, each command function is registered **twice**: once by its full name (visible in `--help`), once by a short alias (hidden from help). Both point to the same function object.

```python
app.command("fetch")(fetch_cmd)     # visible
app.command("f", hidden=True)(fetch_cmd)  # hidden shortcut
```

The `CMDS` list in `consts.py` contains ALL 14 names (7 full + 7 aliases) so that the typo-suggestion engine knows about them.

---

## Module Deep-Dive

### 1. `src/consts.py` — Constants & Static Data

| Symbol           | Value                                     | Purpose                                |
| ---------------- | ----------------------------------------- | -------------------------------------- |
| `__title__`      | `"anchor4git"`                            | Human-readable project name            |
| `__version__`    | `version("anchor4git")`                   | Dynamic version from installed package |
| `__description__`| Brief description string                  | Shown in Typer `--help`                |
| `CMDS`           | `["init","i","info","d","dashboard",...]` | All 14 command names for typo checking |
| `DEFAULT_NAME`   | `"Anchor4Git Client"`                     | Fallback Git author name               |
| `DEFAULT_EMAIL`  | `"anchor4git@local.dev"`                  | Fallback Git author email              |
| `CONFIG_FILE`    | `".git\\anchor4git.json"`                 | Path to runtime config (relative to workspace root) |

The version is **not** hardcoded — it's pulled from installed package metadata via `importlib.metadata.version()`. This means `__version__` will fail if the package isn't installed (it's only used at runtime, not build time).

---

### 2. `src/utils.py` — Core Infrastructure (201 lines)

This is the guts of the project. It provides six categories of functionality:

#### A. Config I/O (`cfg_read`, `cfg_write`)

```python
cfg_read  = lambda: loads(Path(CONFIG_FILE).read_text()) if Path(CONFIG_FILE).exists() else {}
cfg_write = lambda d: Path(CONFIG_FILE).write_text(dumps(d, indent=2))
```

**What it does:**
- Reads/writes `.git/anchor4git.json` as a JSON dict
- `cfg_read` returns `{}` if the file doesn't exist (no crash)
- `cfg_write` overwrites the file with pretty-printed JSON

**Config file structure:**
```json
{
  "name": "User Name",
  "email": "user@example.com",
  "origin_url": "https://github.com/org/repo.git",
  "default_branch": "main"
}
```

**Why `.git/` subdirectory?** Because `.git/` is never tracked by Git itself, so the config file is automatically excluded from commits. The `save` command also explicitly `git reset`s it before committing as a safety net.

#### B. Git Execution Gateway (`git()`)

```python
def git(*a, check: bool = True):
    cfg = cfg_read()
    name = cfg.get("name") or run(["git", "config", "user.name"], ...).stdout.strip() or DEFAULT_NAME
    email = cfg.get("email") or run(["git", "config", "user.email"], ...).stdout.strip() or DEFAULT_EMAIL
    return run(["git", "-c", f'user.name="{name}"', "-c", f'user.email="{email}"', *a], ...)
```

**Key behaviors:**
- Every Git command is injected with `-c user.name=... -c user.email=...` to ensure the configured identity is always used, regardless of global/default Git config.
- Author name/email **precedence**: Config file (`anchor4git.json`) > Git global defaults > Preset defaults (`DEFAULT_NAME`/`DEFAULT_EMAIL`).
- Returns a `subprocess.CompletedProcess` with `.stdout`, `.stderr`, `.returncode`.
- Default `check=True` raises `CalledProcessError` on non-zero exit (like `subprocess.run(check=True)`).

#### C. Repository State Helpers (Lambdas)

| Helper | What it checks | Implementation |
|--------|---------------|----------------|
| `is_repo()` | Does `.git/` directory exist? | `path.isdir(".git")` |
| `dirty()` | Are there uncommitted changes? | `bool(git("status", "--porcelain").stdout.strip())` |
| `changes()` | List of changed file paths | `git("status", "--porcelain").stdout.strip()` |
| `conflicts()` | Files with merge conflicts | `git("diff", "--name-only", "--diff-filter=U").stdout.split()` |
| `detached()` | Is HEAD in detached state? | `not bool(git("branch", "--show-current").stdout.strip())` |
| `get_if_origin_empty(origin)` | Does remote have any refs? | `not git("ls-remote", resolve_origin(origin)).stdout.strip()` |

All six are simple one-liners that wrap `git()` calls.

#### D. Setup Helpers

**`resolve_origin(url)`** — Resolves the origin URL with precedence:
1. User-provided URL argument
2. `origin_url` from config file
3. Dies with error if neither exists

If the URL looks like a local path (no scheme + netloc), it's converted to an absolute path via `Path().resolve()`.

**`create_repo(default_branch)`** — Runs `git init -b <branch>` to create a new repository.

**`generate_config(origin, default_branch, refresh)`** — Creates or updates `.git/anchor4git.json`. When `refresh=True`, preserves existing `name`/`email` values; when `False`, always overwrites with Git defaults.

**`delete_repo()`** — Removes `.git/` directory. Uses a Windows-compatible `remove_readonly` callback because Git marks some internal files as read-only.

**`autosave(msg)`** — Stages all files (`git add .`), explicitly resets the config file (`git reset .git/anchor4git.json`), then commits. This is the safety net called before fetch, upload, and destructive goto operations.

#### E. Safety Gates

Three functions that enforce preconditions and `die()` (exit with error) if unmet:

```
git_existance_safety()   → Ensures `git` executable is on PATH (via shutil.which)
repo_existance_safety()  → Ensures `.git/` directory exists
detached_safety()        → Ensures HEAD is not detached (blocks operations during `goto`)
```

**When to call which:**
- `git_existance_safety()` — EVERY command
- `repo_existance_safety()` — info, config, save, upload (anything that needs a repo)
- `detached_safety()` — fetch, upload, save, init (anything that modifies state)

#### F. UI Helpers

| Function | Purpose | Visual |
|----------|---------|--------|
| `ok(msg)` | Success message | `[SUCESS] msg` (green) |
| `info(msg)` | Info message | `[INFO] msg` (cyan) |
| `warn(msg)` | Warning message | `[WARN] msg` (yellow) |
| `die(msg)` | Error + exit | `[ERROR] msg` (red) + `sys.exit(1)` |
| `section_header(title)` | Section break | `===== title =====` |
| `kv(key, value)` | Key-value line | `- key                 value` |
| `next_step(text)` | Suggested next action | `[INFO] Next, try ...` |
| `confirm_or_cancel(prompt)` | Yes/No confirmation | Typer `confirm()`; raises `Exit` if denied |
| `preview_block(title, lines)` | Preview section | Section header + bullet list |
| `human_sync(ahead, behind)` | Sync status in plain English | e.g. "You have 3 unsynced save(s) on your end." |
| `suggest_command(raw)` | Typo correction | `die()` with "Did you mean '...'?" |
| `open_editor(filepath, blocking)` | Open file in default editor | Cross-platform: `start`/`open`/`$EDITOR`/`xdg-open` |

**Console rendering:** Uses Rich's `print()` for styled output. All logs use a consistent `[bold white on bright_COLOR] TYPE [/]` format.

---

### 3. `src/cmds/init.py` — `ag init [name] [--no-template]`

**Purpose:** Set up a Git repository + starter template files.

**Flow:**
1. Safety: `git_existance_safety()`, `detached_safety()`
2. If `.git/` missing → `create_repo()` (which runs `git init -b main`)
3. If config file missing → `generate_config()` with Git defaults
4. Unless `--no-template`, create `README.md`, `.gitignore`, `LICENSE` (MIT boilerplate) — skips if files already exist

**Notes:**
- The template files are hardcoded multi-line strings in the source.
- `init` does NOT set up a remote; that happens during `fetch`.

---

### 4. `src/cmds/fetch.py` — `ag fetch [url] [--force] [--preview]`

**Purpose:** Download work from a remote repository. This is the "Download" step.

**Flow:**

```
fetch_cmd(url, force, preview)
│
├── 1. Safety: git_existance_safety(), detached_safety()
│
├── 2. Resolve origin URL (argument > config > die)
│
├── 3. Check if origin is empty (git ls-remote)
│
├── 4. If repo missing locally → create_repo()
│
├── 5. generate_config(refresh=True) — update config with origin
│
├── 6. If --preview:
│       ├── Fetch from origin
│       ├── Show preview block (URL, force flag, repo status, dirty status, file diffs)
│       └── If repo was just created → delete_repo() to clean up
│
├── 7. If origin is empty → info message + return
│
├── 8. autosave() — commit any dirty changes
│
├── 9. git fetch <origin>
│
├── 10. If --force:
│        ├── confirm_or_cancel()
│        ├── git reset --hard FETCH_HEAD
│        ├── git clean -fd
│        └── return
│
└── 11. Normal merge:
         ├── git merge FETCH_HEAD --allow-unrelated-histories
         ├── If no conflicts → amend merge commit to fix author
         └── If CalledProcessError → check conflicts():
              ├── If no conflicts → die("Merge failed")
              └── If conflicts → list files + prompt to resolve and `ag save`
```

**Key details:**
- `--allow-unrelated-histories` is always used, enabling merge of entirely independent repos.
- After a clean merge, the commit author is rewritten with `git commit --amend --no-edit --reset-author` to match the configured identity.
- Conflict detection uses `git diff --name-only --diff-filter=U`.
- Force mode completely replaces local state with remote (hard reset + clean).

---

### 5. `src/cmds/upload.py` — `ag upload [branch] [--force] [--preview]`

**Purpose:** Publish local work to the remote repository. This is the "Upload" step.

**Flow:**

```
upload_cmd(branch, force, preview)
│
├── 1. Safety: repo_existance_safety(), detached_safety()
│
├── 2. Resolve origin from config
│
├── 3. Fetch from origin (if not empty) to calculate sync state
│
├── 4. Calculate behind count: git rev-list --count HEAD..FETCH_HEAD
│
├── 5. If --preview:
│       └── Show branch, force flag, behind status, dirty status, conflicts
│
├── 6. If --force:
│       ├── confirm_or_cancel()
│       ├── autosave() if dirty
│       ├── git push --force origin HEAD:refs/heads/<branch>
│       └── return
│
├── 7. Blocks:
│       ├── If conflicts exist → die() with list of conflicting files
│       └── If behind remote → die() with behind count
│
└── 8. Safe upload:
        ├── autosave() if dirty
        └── git push --force origin HEAD:refs/heads/<branch>
```

**Key design decision:** Even the "safe" mode uses `git push --force`. There is no `--force-with-lease` or rejection on non-fast-forward. This is intentional — for small trusted teams, push rejection errors are confusing and unhelpful. The safety comes from the **before** checks (conflict check, behind check).

**Behind count edge case:** Wrapped in `try/except` because `FETCH_HEAD` may not exist if the remote is empty or unreachable. Falls back to `behind = 0`.

---

### 6. `src/cmds/save.py` — `ag save [message] [--preview]`

**Purpose:** Commit a snapshot of all workspace changes.

**Flow:**

```
save_cmd(message, preview)
│
├── 1. Safety: git_existance_safety(), repo_existance_safety(), detached_safety()
│
├── 2. If workspace is clean → info("Nothing to save") + return
│
├── 3. Generate commit message:
│       ├── User-provided > auto-generated "anchor4git: Save YYMMDD-HHMMSS"
│
├── 4. Resolve author name/email (config > Git defaults > presets)
│
├── 5. git add .  +  git reset CONFIG_FILE  (exclude config from commit)
│
├── 6. If --preview → show preview block + return
│
└── 7. git commit -m <msg>
```

**Notes:**
- The `message` argument uses `Optional[list[str]]` — Typer joins multiple words into a list, rebuilt with `" ".join(message or [])`.
- The config file is always excluded from commits via `git reset CONFIG_FILE` after staging everything.

---

### 7. `src/cmds/info.py` — `ag info` (aliases: `d`, `dashboard`)

**Purpose:** Display a rich dashboard of repository state using Rich rendering.

**Data collected (with Rich Progress spinner):**

| Data | How it's obtained |
|------|-------------------|
| Sync status (ahead/behind) | `git rev-list --count FETCH_HEAD..HEAD` and reverse |
| Config values | `cfg_read()` |
| Current branch | `git branch --show-current` |
| Dirty/clean status | `dirty()` |
| Last save | `git log -1 --pretty=format:"%s (%ar)"` |
| Changes list | `git status --short` |
| Contributors | `git shortlog -sne HEAD` |
| Repo size | `git count-objects -vH` (parses `size:` line) |
| Full commit log | `git log --all --pretty=format:"%h\t | %ar\t | %an\t | %ae\t | %s"` |

**Rendering:**
1. **Panel** (cyan border): workspace status, sync text, repo size
2. **Table** (no border): origin URL, username, email, last save
3. **Contributors** list (bullet points)
4. **Changes** section
5. **Save history** — paginated: first 5 entries, then Enter to scroll, Ctrl+C to exit. Each entry shows `>>>` marker next to the current HEAD commit.

---

### 8. `src/cmds/goto.py` — `ag goto <commit> [--reset] [--stay] [--preview]`

**Purpose:** Time-travel to any previous commit — either temporarily (default) or permanently.

**Flow:**

```
goto_cmd(commit, reset, stay, preview)
│
├── 1. Safety: git_existance_safety(), repo_existance_safety()
├── 2. If no commit → die with usage
│
├── 3. If commit == "HEAD":
│       ├── git checkout @{-1}  (previous branch)
│       ├── If stash has anchor-goto-temp → git stash pop
│       └── Return
│
├── 4. If detached → die("Must use goto HEAD first")
│
├── 5. Resolve full commit hash: git rev-parse --verify <commit>
├── 6. Show commit info: message, short hash, author, relative time
│
├── 7. If --preview → show preview + return
│
├── 8. If --reset (permanent):
│       ├── autosave() if dirty
│       ├── confirm_or_cancel() — destructive warning
│       ├── git checkout <full> .  (checkout files)
│       ├── git clean -fd
│       └── autosave("RESET of: <commit message>")
│
└── 9. Temporary mode (default) / --stay:
        ├── If dirty → git stash push -u -m "anchor-goto-temp"
        ├── git checkout <full>
        ├── If --stay → info + return (stay on commit)
        ├── Else → wait for Enter
        └── Finally:
             ├── git checkout <original_branch>
             ├── If stash was created → git stash pop
             └── ok("Returned to branch")
```

**Key behaviors:**
- Temporary mode uses `finally:` to guarantee branch restoration even on Ctrl+C.
- Stash messages are tagged `anchor-goto-temp` so `goto HEAD` can identify and restore them.
- The `--reset` mode creates a new commit with `RESET of: <original message>` so the history of "what happened" is preserved.

---

### 9. `src/cmds/config.py` — `ag config`

**Purpose:** Open the config file in the user's default text editor.

**Flow:**
1. Safety: `git_existance_safety()`, `repo_existance_safety()`
2. `open_editor(Path(CONFIG_FILE))`

That's it. It's intentionally minimal — the editor provides full CRUD for the JSON config.

---

## Configuration System

### Config File Location: `.git/anchor4git.json`

**Why `.git/` subdirectory?**
- Git never tracks anything inside `.git/`
- The config file is automatically excluded from version control
- Additionally, `save` explicitly runs `git reset .git/anchor4git.json` before committing

### Authentication System
Anchor4Git itself does not handle authentication directly — it relies on Git's credential mechanisms.

---

## The `autosave()` Pattern

This is a critical safety mechanism used across multiple commands:

```python
def autosave(msg):
    if dirty():
        git("add", ".")
        git("reset", CONFIG_FILE)
        git("commit", "-m", msg)
        ok("Auto-saved workspace.")
```

**When is it called?**
| Command | Condition |
|---------|-----------|
| `fetch` | Before merging remote changes (always) |
| `upload --force` | Before force-push (only if dirty) |
| `upload` (normal) | Before push (only if dirty) |
| `goto --reset` | Before destructive reset (only if dirty) |

**What it does:**
1. Checks if workspace is dirty (uncommitted changes exist)
2. Stages EVERYTHING (`git add .`)
3. Un-stages the config file (`git reset .git/anchor4git.json`) so it's never committed
4. Commits with a descriptive message

---

## Safety Gate System

Each command calls one or more safety gates before doing anything. They enforce preconditions and exit cleanly if unmet.

```
             ┌──────────────────────────────────────────────────┐
             │                  COMMAND                         │
             │                                                  │
             │  git_existance_safety()  — "Do you have Git?"    │
             │  repo_existance_safety() — "Is .git/ here?"      │
             │  detached_safety()       — "Are we on a branch?" │
             │                                                  │
             │  → If any fails → die() with clear message       │
             └──────────────────────────────────────────────────┘
```

**Safety requirements per command:**

| Command | Git exists | Repo exists | Not detached |
|---------|:----------:|:-----------:|:------------:|
| `init` | ✅ | — (creates it) | ✅ |
| `info` | ✅ | ✅ | — |
| `config` | ✅ | ✅ | — |
| `save` | ✅ | ✅ | ✅ |
| `fetch` | ✅ | — (creates it) | ✅ |
| `upload` | ✅ | ✅ | ✅ |
| `goto` | ✅ | ✅ | — (but blocks on specific ops) |

---

## UI System

All terminal output uses the Rich library via its `print()` function. The style system:

```
Output format:  [bold white on bright_COLOR] TYPE [/] message
                                               │
                    ┌──────────────────────────┴─────────────────────┐
               [SUCESS] green   [INFO] cyan   [WARN] yellow   [ERROR] red
```

**Command output conventions:**
- Every command ends with a `next_step()` suggestion (e.g., "Next, try `ag upload`")
- Preview blocks use `section_header()` + bullet list
- Confirmations use `confirm_or_cancel()` which wraps Typer's `confirm()` — `Exit` is raised if user says no

---

## Test System

**Framework:** pytest 8.4.2+
**File:** `tests/test_cmds.py` (143 lines, integration tests)
**Setup:** `tests/conftest.py` — cleans up `tests/temp/` directory after successful runs

### Test Architecture

Tests create a real Git filesystem inside `tests/temp/`:
1. **Bare origin repo** — simulates a remote repository
2. **Local clone/workspace** — simulates the user's working directory
3. **Control repo** — used to push initial commits to the bare origin

Each test runs `anchor4git <command>` via `subprocess.run()` and checks return codes + output + file state.

### Test Coverage

| Test | What it verifies |
|------|------------------|
| `test_help` | `--help` returns exit code 0 |
| `test_missing_repo_error` | `save` without repo returns exit code 1 |
| `test_init` | `init --no-template` creates `.git` directory |
| `test_save` | Saves a file, checks commit log contains the message |
| `test_fetch` | Creates conflict scenario, verifies conflict markers in file |
| `test_upload` | Upload fails during conflicts, succeeds after resolution |
| `test_info` | Dashboard output contains expected commits, status, origin |
| `test_goto_stay` | Goes to previous commit `--stay`, verifies file content reverted |
| `test_detached_fail` | Verifies fetch fails while HEAD is detached |
| `test_return` | `goto HEAD` returns to normal, restores content |

**To run tests:**
```bash
uv run pytest tests/ -v
```

---

## Build & Distribution System

### Build Backend: `uv_build`

`pyproject.toml` declares:
```toml
[build-system]
requires = ["uv_build>=0.11.26,<0.12"]
build-backend = "uv_build"
```

`uv_build` is the PEP 517 build backend from the Astral `uv` ecosystem. It reads metadata from `pyproject.toml`.

### Module Structure for Build

```toml
[tool.uv.build-backend]
module-name = "src"
module-root = ""
```

The `src/` directory is the Python package root. It's NOT a `src-layout` flattening — the package name IS `src`, so it's installed as `import src`.

### Entry Points

```toml
[project.scripts]
anchor4git = "src:main"
ag = "src:main"
```

Both `anchor4git` and `ag` invoke the same `src:main()` function.

### Dependencies

**Runtime:** `typer>=0.16`, `rich>=10.0.0`
**Dev:** `pytest>=8.4.2`

### CI/CD (`.github/workflows/upload.yml`)

Manually triggered via `workflow_dispatch` with options:
- **publish_target:** `build-only` | `testpypi` | `pypi`
- **Version:** required string input
- **GitHub Release:** optional, with configurable name, notes, draft/prerelease flags

Steps:
1. Checkout (full depth)
2. Setup uv (Python 3.13)
3. `uv build`
4. `twine check` (validation)
5. `uv publish` (to PyPI or TestPyPI)
6. Optionally create GitHub Release with `softprops/action-gh-release`

---

## User Workflow (Mental Model)

### Happy path:
```
ag fetch <url>       # Download project → start working
(edit files)
ag save "my change"  # Snapshot your work locally
ag upload            # Publish to the team
```

### Sync with team:
```
ag fetch             # Get latest from team
(edit files)
ag save              # Save your changes
ag upload            # Share your changes
```

### Conflict resolution:
```
ag fetch             # Get latest — conflicts may appear
(open conflicted files in editor)
(edit to resolve conflicts)
ag save              # Commit the resolved merge
ag upload            # Publish resolution
```

### Time travel:
```
ag goto <hash>       # Look at old version (temporary)
ag goto HEAD         # Return to latest

ag goto <hash> --reset   # Permanently roll back
ag goto <hash> --stay    # Look and stay on old version
```

---

## Future Plans

- [ ] Better `main`/`master` branch handling
- [ ] Merging all local commits into one merge commit before uploading to maintain minimalism
- [ ] More interactive methhod to edit anchor4git.json
- [ ] Resolving ahead & behind fails sometimes
- [ ] Info command does not work unless there is a origin repository configured.

---

## Development Guide

### Adding a new command

1. Create `src/cmds/newfeature.py` with a function like `newfeature_cmd(...)` using Typer arguments/options.
2. Import and register it in `src/__main__.py`:
   ```python
   from .cmds.newfeature import newfeature_cmd
   app.command("newfeature")(newfeature_cmd)
   app.command("nf", hidden=True)(newfeature_cmd)
   ```
3. Add `"newfeature"` and `"nf"` to the `CMDS` list in `consts.py`.
4. Add safety gates at the top of the function.
5. Follow UI conventions: use `ok()`/`info()`/`warn()`/`die()`, end with `next_step()`.
6. Write tests in `tests/test_cmds.py`.

### Code conventions

- Use lambda for simple one-liners when readable
- Typer commands return `None` (they print output, not return data)
- Always call `git_existance_safety()` first
- Config file is always at `.git/anchor4git.json` — referenced via `CONFIG_FILE` constant
- Use `Rich`'s `print()` for all output (not standard `print`)
- Always use `origin` instead of `remote` to maintain consistancy for new users