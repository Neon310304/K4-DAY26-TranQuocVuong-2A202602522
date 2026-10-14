import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "04-lab/mcp-client"))


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def weather():
    return load_module("weather_lab_server", "04-lab/mcp-server/weather.py")


@pytest.fixture(scope="session")
def verify():
    return load_module("weather_lab_verify", "04-lab/mcp-client/verify_setup.py")


@pytest.fixture(scope="session")
def server_url():
    from lab_support import local_server
    with local_server(env={"WEATHERAPI_KEY": ""}) as url:
        yield url
