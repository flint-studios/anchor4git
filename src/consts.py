from importlib.metadata import version

__title__ = "anchor4git"
__description__ = "A highly-minimal workflow tool for small teams using Git."
__version__ = version("anchor4git")
__author__ = "Abhirup Hajra"
__license__ = "MIT"
__url__ = "https://fx0.qzz.io"

CMDS = [ # Available commands
    "info",
    "i",
    "dashboard",
    "save",
    "s",
    "fetch",
    "f",
    "upload",
    "u",
    "goto",
    "g",
    "config",
    "c",
]

DEFAULT_NAME = "Anchor4Git Client"
DEFAULT_EMAIL = "anchor4git@local.dev"
CONFIG_FILE = ".git\\anchor4git.json"

__all__ = [
    "__title__",
    "__description__",
    "__version__",
    "__author__",
    "__license__",
    "__url__",
    "CMDS",
    "DEFAULT_NAME",
    "DEFAULT_EMAIL",
    "CONFIG_FILE"
]