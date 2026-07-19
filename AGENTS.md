# For AI Agents

## Project Identity
- **Name:** `anchor4git` — a Python CLI that wraps Git for non-technical users
- **Entry points:** `anchor4git` / `ag` → `src:main()` → `src/__main__.main()`
- **Python:** `>=3.9`, dependencies: `typer>=0.16`, `rich>=10.0.0`
- **Build:** `uv_build` (PEP 517), **not** setuptools. Run `uv build` to build.
- **Tests:** `pytest>=8.4.2`, run with `uv run pytest tests/ -v`
- **Version:** `0.1.1` in `pyproject.toml`, dynamically at runtime via `importlib.metadata.version("anchor4git")`

## Key Conventions
- **No docstrings on command functions** — Typer uses the function's docstring as `--help` text, so keep the one-liner docstring on each command function
- **All output uses Rich's `print()`** — not standard `print()`. Import: `from rich import print`
- **Config file:** `.git/anchor4git.json` — always use the `CONFIG_FILE` constant from `consts.py`
- **Every command ends with `next_step()`** suggesting what the user should do next
- **Safety gates go first** in every command function: `git_existance_safety()`, `repo_existance_safety()`, `detached_safety()`
- **Author precedence:** config file > `git config` global > `DEFAULT_NAME`/`DEFAULT_EMAIL` presets
- **Lambda style:** simple one-liner helpers use `lambda` (see `utils.py`)

## Module Map
| File | Purpose |
|------|---------|
| `src/consts.py` | All constants: `CMDS` (command names list), `DEFAULT_NAME`, `DEFAULT_EMAIL`, `CONFIG_FILE`, version info |
| `src/utils.py` | Git gateway (`git()`), config I/O (`cfg_read`/`cfg_write`), safety gates, UI helpers, `open_editor()` |
| `src/__main__.py` | Typer app setup, command registration, unknown-command suggestion |
| `src/cmds/*.py` | One file per command, each exports a single `*_cmd()` function |

## Common Pitfalls
1. **`src` is the package name.** The package is installed as `src`, so imports are `from .utils import *` not `from anchor.utils import *`.
2. **`git()` returns `CompletedProcess`** — access `.stdout`, `.stderr`, `.returncode`. Default `check=True` raises `CalledProcessError`.
3. **`message` param in `save` is `Optional[list[str]]`** — Typer splits multi-word args into a list, rejoined with `" ".join(message or [])`.
4. **Config file is excluded from every commit** — `git add .` then `git reset CONFIG_FILE` before every commit (see `autosave()`).
5. **Force-push is the only push mode** — no `--force-with-lease`, no fast-forward checks. Safety is in pre-checks only.
6. **`resolve_origin(url)` accepts local paths** — if no scheme/netloc, it resolves as a local absolute path.
7. **`detached_safety()` blocks fetch, upload, save, init** — because those commands can't run while in a `goto` session.
8. **Tests create real Git repos** in `tests/temp/` — conftest cleans up on success but leaves artifacts on failure.
9. **Version is dynamic** — `consts.py` uses `importlib.metadata.version()`, which only works if the package is installed.
10. **`goto HEAD` uses `@{-1}`** — it checks out the previous branch (not literally `HEAD`).

## Adding a New Command
1. Create `src/cmds/newfeature.py` with a Typer function `newfeature_cmd(...)` + docstring (becomes `--help` text)
2. Register in `src/__main__.py`: `app.command("newfeature")(newfeature_cmd)` + optional hidden alias
3. Add all names to `CMDS` list in `consts.py`
4. Add safety gates first, UI helpers (`ok()`/`info()`/`warn()`/`die()`), end with `next_step()`
5. Write integration test in `tests/test_cmds.py` — tests call the CLI via `subprocess.run()`

## Test Patterns
Tests live in `tests/test_cmds.py`. The test setup:
1. Creates `temp/repo/` as workspace and `temp/origin/` as bare remote
2. Runs `anchor4git <args>` via `subprocess.run()` (helper: `ag(args, cwd)`)
3. Asserts `returncode == 0` or `== 1`
4. Asserts file contents, `git log` output, or config state

## CI/CD
- `.github/workflows/upload.yml` — manually triggered (`workflow_dispatch`), builds with `uv build`, publishes to PyPI/TestPyPI, optionally creates GitHub Release
- **Not automated on push** — only on manual trigger
