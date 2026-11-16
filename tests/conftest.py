import os
from pathlib import Path

import pytest

from faro_foundation.cli import load_env
from faro_foundation.common import Settings


@pytest.fixture(scope="session")
def home():
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def settings(home):
    os.environ["FARO_HOME"] = str(home)
    load_env(home)
    if not os.getenv("FARO_DB_PASSWORD"):
        pytest.fail("Integration needs FARO_DB_PASSWORD or a local .env; do not silently skip")
    return Settings.from_env()
