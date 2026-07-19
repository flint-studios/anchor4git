from subprocess import run
from stat import S_IWRITE
from shutil import rmtree
from pathlib import Path
from os import chmod

from src.__main__ import app


# UTILITIES
def remove_readonly(func, path, excinfo): chmod(path, S_IWRITE); func(path)

def ag(args, cwd="."):
    return run(f"anchor4git {args}", cwd=cwd, text=True, capture_output=True)

def git(args, cwd="."):
    return run(f"git {args}", cwd=cwd, text=True, capture_output=True)


# TEMPORARY CWD SETUP
temp_folder = Path("temp")

if temp_folder.exists() and temp_folder.is_dir(): rmtree(temp_folder, onerror=remove_readonly)
temp_folder.mkdir(parents=True, exist_ok=True)


def test_help():
    assert ag("--help", temp_folder).returncode == 0


def test_missing_repo_error():
    assert ag("save", temp_folder).returncode == 1


def test_init():
    cwd = temp_folder / Path("repo")
    cwd.mkdir(parents=True, exist_ok=True)

    result = ag("init --no-template", cwd)
    
    assert result.returncode == 0
    assert (cwd / Path(".git")).is_dir()


def test_save():
    cwd = temp_folder / Path("repo")
    cwd.mkdir(parents=True, exist_ok=True)

    with open(f"{cwd}/test.md", "x") as f: f.write("create")

    assert ag('save "create test.md"', cwd).returncode == 0

    assert "create test.md" in git('log --oneline', cwd).stdout


def test_fetch():
    origin_cwd = temp_folder / Path("origin")
    origin_cwd.mkdir(parents=True, exist_ok=True)

    git("init --bare -b main", origin_cwd)

    control_cwd = temp_folder / Path("control")
    control_cwd.mkdir(parents=True, exist_ok=True)

    with open(f"{control_cwd}/test.md", "x") as f: f.write("conflict")

    git("--git-dir=../origin --work-tree=. add .", control_cwd)
    git('--git-dir=../origin --work-tree=. commit -m "origin: create conflict"', control_cwd)

    cwd = temp_folder / Path("repo")
    cwd.mkdir(parents=True, exist_ok=True)

    ag("fetch ../origin", cwd).returncode == 0

    assert "<<<<<<< HEAD\ncreate\n=======\nconflict\n>>>>>>>" in (cwd / Path("test.md")).read_text(encoding="utf-8")

    (cwd / Path("test.md")).write_text("resolved")


def test_upload():
    origin_cwd = temp_folder / Path("origin")
    origin_cwd.mkdir(parents=True, exist_ok=True)

    cwd = temp_folder / Path("repo")
    cwd.mkdir(parents=True, exist_ok=True)

    # Fail due to conflicts
    assert ag("upload", cwd).returncode == 1

    assert ag('save "resolution"', cwd).returncode == 0

    assert ag("upload", cwd).returncode == 0

    assert "resolution" in git(f"--git-dir=../origin log --oneline", cwd).stdout


def test_info():
    cwd = temp_folder / Path("repo")
    cwd.mkdir(parents=True, exist_ok=True)

    result = ag("info", cwd)

    returncode = result.returncode
    stdout = result.stdout

    assert returncode == 0

    assert "resolution" in stdout
    assert "origin: create conflict" in stdout
    assert "create test.md" in stdout

    assert "temp\\origin" in stdout

    assert git("rev-parse --short HEAD", cwd).stdout.replace("\n", "") in stdout
    
    assert "CLEAN" in stdout


def test_goto_stay():
    cwd = temp_folder / Path("repo")
    cwd.mkdir(parents=True, exist_ok=True)

    hash = git("rev-parse --short HEAD~1", cwd).stdout.replace("\n", "")

    assert ag(f"goto {hash} --stay", cwd).returncode == 0

    assert "create" in (cwd / Path("test.md")).read_text(encoding="utf-8")


def test_detached_fail():
    cwd = temp_folder / Path("repo")
    cwd.mkdir(parents=True, exist_ok=True)

    assert ag(f"fetch", cwd).returncode == 1


def test_return():
    cwd = temp_folder / Path("repo")
    cwd.mkdir(parents=True, exist_ok=True)

    assert ag(f"goto HEAD", cwd).returncode == 0

    assert "resolved" in (cwd / Path("test.md")).read_text(encoding="utf-8")
