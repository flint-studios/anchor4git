# Anchor4Git

![version](https://img.shields.io/badge/version-0.1.1-orange)
[![License](https://img.shields.io/badge/license-I0SL-blue.svg)](LICENSE)
![Static Badge](https://img.shields.io/badge/build-passing-darkcyan)

A highly-minimal workflow tool for small teams (2–4 people) using Git. Anchor4Git wraps Git into a simple **Download → Edit → Upload** mental model so users never need to know Git commands.

> [!WARNING]
> Anchor4Git requires `git`. Please install it on your device.

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Documentation](https://docs.invoke0.indevs.in/anchor4git)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)


## Features

- **No Git knowledge required** — users never run Git commands directly.
- **Workspace-first** — users edit files normally, anchor4git handles versioning.
- **Auto-save before risky operations** — dirty workspaces are saved automatically.
- **Force push model** — simplified for small, trusted teams.
- **Conflicts handled in editor** — visual merge UX instead of CLI confusion.

## Installation
### For non-contributors:
```bash
pipx anchor4git
```

### For contributors:
   ```bash
   git clone https://github.com/invoke-zero/anchor4git.git
   cd anchor4git
   pip install -r requirements.txt
   python -m build
   ```

## Usage

```
ag fetch       -  Download latest work from the remote
ag save        -  Save a snapshot of your workspace
ag upload      -  Publish your work to the remote
ag info        -  View project dashboard and history
ag goto        -  Navigate to a previous save
ag config      -  Open project configuration
```

All commands have short aliases (`f`, `s`, `u`, `i`, `g`, `c`).

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add new feature"
   ```
4. Push your branch:
   ```bash
   git push origin feature-name
   ```
5. Submit a pull request.

Please read the [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

This project is licensed under the Invoke0 Standard License 1.0 **(I0SL-1.0)** License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Typer](https://typer.tiangolo.com/) - build great CLIs. Easy to code. Based on Python type hints.
- [Rich](https://github.com/textualize/rich) - for rich text and beautiful formatting in the terminal.
