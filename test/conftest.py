import os
import shutil
from pathlib import Path

import pytest


_TEST_RENV_DIR = Path("/tmp/renv")


@pytest.fixture(scope="session", autouse=True)
def configure_renv_dir():
    """Force tests to use an isolated renv directory under /tmp."""

    previous = os.environ.get("RENV_DIR")

    if _TEST_RENV_DIR.exists():
        shutil.rmtree(_TEST_RENV_DIR)
    _TEST_RENV_DIR.mkdir(parents=True, exist_ok=True)

    os.environ["RENV_DIR"] = str(_TEST_RENV_DIR)

    try:
        yield _TEST_RENV_DIR
    finally:
        if previous is None:
            os.environ.pop("RENV_DIR", None)
        else:
            os.environ["RENV_DIR"] = previous
        shutil.rmtree(_TEST_RENV_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def ensure_renv_dir_exists():
    """Make sure the renv directory exists before each test."""

    _TEST_RENV_DIR.mkdir(parents=True, exist_ok=True)
    yield
