from stat import S_IWRITE
from shutil import rmtree
from pathlib import Path
from os import chmod

import pytest

def pytest_sessionfinish(session, exitstatus):
    # exitstatus 1 means there were test failures
    if exitstatus == 1:
        print("\n\nSession finished: There were test failures.")
    elif exitstatus == 0:
        try:
            temp_folder = Path("temp")
            def remove_readonly(func, path, excinfo): chmod(path, S_IWRITE); func(path)
            if temp_folder.exists() and temp_folder.is_dir(): rmtree(temp_folder, onerror=remove_readonly)

        except: pass
        finally: print("\n\nSession finished: All tests passed!")