# pylint: disable=missing-module-docstring, missing-function-docstring, unused-argument, too-few-public-methods
import time
from pathlib import Path
from typing import List

import poetry.factory
import poetry.installation.executor
import poetry.utils.env
import pytest
import tox.tox_env.python.virtual_env.runner
from poetry.installation.operations.operation import Operation

from tox_poetry_installer import utilities


TEST_PROJECT_PATH = Path(__file__).parent.resolve() / "test-project"

FAKE_VENV_PATH = Path("nowhere")


class MockVirtualEnv:
    """Mock class for the :class:`poetry.utils.env.VirtualEnv` and :class:`tox.venv.VirtualEnv`"""

    def __init__(self, *args, **kwargs):
        self.env_dir = FAKE_VENV_PATH
        self.installed = []

    @staticmethod
    def is_valid_for_marker(*args, **kwargs):
        return True

    @staticmethod
    def get_version_info():
        return (1, 2, 3)


class MockExecutor:
    """Mock class for the :class:`poetry.installation.executor.Executor`"""

    def __init__(self, env: MockVirtualEnv, **kwargs):
        self.env = env

    def execute(self, operations: List[Operation]):
        self.env.installed.extend([operation.package for operation in operations])
        time.sleep(1)


@pytest.fixture
def mock_venv(monkeypatch):
    monkeypatch.setattr(utilities, "convert_virtualenv", lambda venv: venv)
    monkeypatch.setattr(poetry.installation.executor, "Executor", MockExecutor)
    monkeypatch.setattr(
        tox.tox_env.python.virtual_env.runner, "VirtualEnvRunner", MockVirtualEnv
    )
    monkeypatch.setattr(poetry.utils.env, "VirtualEnv", MockVirtualEnv)


@pytest.fixture(scope="function")
def mock_poetry_factory(monkeypatch):
    pypoetry = poetry.factory.Factory().create_poetry(cwd=TEST_PROJECT_PATH)

    def mock_factory(*args, **kwargs):
        return pypoetry

    monkeypatch.setattr(poetry.factory.Factory, "create_poetry", mock_factory)
