# Architecture

anchor4git is a CLI tool that wraps Git into a simplified **Download → Edit → Upload** workflow for small teams.

## Core Principles

| Rule                              | Description                       |
| --------------------------------- | --------------------------------- |
| No Git knowledge required         | Users never run Git commands      |
| Workspace first                   | Users edit files normally         |
| Auto-save before risky operations | Dirty workspace saved as commit   |
| Forced upload                     | Simpler model, avoids push errors |
| Conflicts handled in editor       | Best UX for non-Git users         |

## Project Structure

```
anchor/                          # Main Python package
├── __init__.py                  # Exports main() and __version__
├── __main__.py                  # CLI entry point (Typer app & command registration)
├── data.py                      # Dynamic data store (commands list, defaults, version)
├── utils.py                     # Git helpers, UI helpers, config I/O
└── cmds/                        # CLI command implementations
    ├── info.py                  # anchor info / i / dashboard
    ├── save.py                  # anchor save / s
    ├── fetch.py                 # anchor fetch / f
    ├── upload.py                # anchor upload / u
    ├── goto.py                  # anchor goto / g
    └── config.py                # anchor config / c
```

## CLI Architecture

The CLI is built with [Typer](https://typer.tiangolo.com/). Commands are registered in `anchor/__main__.py` with short aliases and hidden aliases (e.g., `dashboard` for `info`). Before invoking Typer, the module checks for unknown commands and suggests corrections via `difflib.get_close_matches`.

### Entry Point

```
pyproject.toml  ──>  anchor:main()
                         └── anchor.__main__.main()
                               ├── Unknown command check
                               └── app()  (Typer)
```

## Commands

### `anchor info` (`i`, `dashboard`)

Shows a rich dashboard with repository state:
- Current branch, dirty/clean status, sync status
- Contributors, recent changes
- Save history with scrollable log (paginated commit history)
- Uses Rich tables and panels for terminal rendering

### `anchor save` (`s`)

Saves a snapshot (commit) of the entire workspace:
- `--preview` mode to inspect changes before saving
- Auto-generates commit message from timestamp if none provided
- Respects configured name/email from `.git/anchor.json`
- Ignores the anchor config file in commits

### `anchor fetch` (`f`)

Downloads latest work from remote:
- Initializes Git repo if none exists
- Auto-saves dirty workspace before fetching
- `--force` flag to replace local state with remote
- Merges with `--allow-unrelated-histories`
- Detects and reports merge conflicts
- Config stores `origin_url` and `default_branch` in `.git/anchor.json`

### `anchor upload` (`u`)

Uploads work to remote:
- Always force pushes (simplified for small teams)
- `--force` flag bypasses safety checks
- Blocks if conflicts exist or behind remote
- Auto-saves dirty workspace before upload

### `anchor goto` (`g`)

Navigates to any previous save:
- `--reset` for permanent workspace reset
- `--stay` to remain on a commit (otherwise auto-returns on Enter)
- Shows target commit info before switching

### `anchor config` (`c`)

Opens `.git/anchor.json` in the user's default editor.

## Configuration

Stored at `.git/anchor.json`:

```json
{
  "name": "User Name",
  "email": "user@example.com",
  "origin_url": "https://github.com/org/repo.git",
  "default_branch": "main"
}
```

Authentication is handled via the `ANCHOR_AUTH` environment variable, injected into the remote URL.

## Internal Modules

| Module  | Purpose                              |
| ------- | ------------------------------------ |
| `cmds/` | CLI command implementations          |
| `utils` | Git helpers (`git()`, `dirty()`, etc.) and UI helpers (`ok()`, `warn()`, `die()`, etc.) |
| `data`  | Static data store (commands, defaults, version) |

## Build System

- **Package:** setuptools + wheel, configured in `pyproject.toml`
- **Version:** Dynamic, pulled from `anchor.__version__`
- **Compiled build:** Nuitka compiles to a standalone `anchor.exe` (~29MB with embedded Python 3.13)
- **Dependencies:** typer, rich (runtime); setuptools, wheel, nuitka, scons (build)

## User Workflow

Daily usage:
```
anchor fetch
(edit files)
anchor upload
```

Conflict workflow:
```
anchor fetch
(resolve conflicts in editor)
anchor save
```

Mental model:
```
Download → Edit → Upload
```

## Conflict Detection

Uses `git diff --name-only --diff-filter=U` to list conflicted files. Users resolve conflicts in their editor and then run `anchor save` to complete the merge commit.

## Future Plans

- [ ] API key in `.env` instead of config
- [ ] Better `main`/`master` branch handling