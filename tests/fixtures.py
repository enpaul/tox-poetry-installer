# pylint: disable=missing-module-docstring, missing-function-docstring, unused-argument, too-few-public-methods
import time
from pathlib import Path

import poetry.factory
import poetry.installation.pip_installer
import poetry.utils.env
import pytest
import tox
from poetry.core.packages import Package as PoetryPackage

from tox_poetry_installer import utilities


TEST_PROJECT_PATH = Path(__file__).parent.resolve() / "test-project"

FAKE_VENV_PATH = Path("nowhere")


class MockVirtualEnv:
    """Mock class for the :class:`poetry.utils.env.VirtualEnv` and :class:`tox.venv.VirtualEnv`"""

    class MockTestenvConfig:  # pylint: disable=missing-class-docstring
        envdir = FAKE_VENV_PATH

    def __init__(self, *args, **kwargs):
        self.envconfig = self.MockTestenvConfig()
        self.installed = []

    @staticmethod
    def is_valid_for_marker(*args, **kwargs):
        return True


class MockPipInstaller:
    """Mock class for the :class:`poetry.installation.pip_installer.PipInstaller`"""

    def __init__(self, env: MockVirtualEnv, **kwargs):
        self.env = env

    def install(self, package: PoetryPackage):
        self.env.installed.append(package)
        time.sleep(1)


@pytest.fixture
def mock_venv(monkeypatch):
    monkeypatch.setattr(utilities, "convert_virtualenv", lambda venv: venv)
    monkeypatch.setattr(
        poetry.installation.pip_installer, "PipInstaller", MockPipInstaller
    )
    monkeypatch.setattr(tox.venv, "VirtualEnv", MockVirtualEnv)
    monkeypatch.setattr(poetry.utils.env, "VirtualEnv", MockVirtualEnv)


@pytest.fixture(scope="function")
def mock_poetry_factory(monkeypatch):
    pypoetry = poetry.factory.Factory().create_poetry(cwd=TEST_PROJECT_PATH)

    def mock_factory(*args, **kwargs):
        return pypoetry

    monkeypatch.setattr(poetry.factory.Factory, "create_poetry", mock_factory)
