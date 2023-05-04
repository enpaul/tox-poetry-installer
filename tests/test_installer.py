# pylint: disable=missing-module-docstring, redefined-outer-name, unused-argument, wrong-import-order, unused-import
import time
from unittest import mock

import pytest
import tox.tox_env.python.virtual_env.runner
from poetry.factory import Factory

from .fixtures import mock_poetry_factory
from .fixtures import mock_venv
from tox_poetry_installer import installer
from tox_poetry_installer import utilities


def test_deduplication(mock_venv, mock_poetry_factory):
    """Test that the installer does not install duplicate dependencies"""
    poetry = Factory().create_poetry(None)
    packages: utilities.PackageMap = {
        item.name: item for item in poetry.locker.locked_repository().packages
    }

    venv = tox.tox_env.python.virtual_env.runner.VirtualEnvRunner()
    to_install = [packages["toml"], packages["toml"]]

    installer.install(poetry, venv, to_install)

    assert len(set(to_install)) == len(venv.installed)  # pylint: disable=no-member


def test_parallelization(mock_venv, mock_poetry_factory):
    """Test that behavior is consistent between parallel and non-parallel usage"""
    poetry = Factory().create_poetry(None)
    packages: utilities.PackageMap = {
        item.name: item for item in poetry.locker.locked_repository().packages
    }

    to_install = [
        packages["toml"],
        packages["toml"],
        packages["tox"],
        packages["requests"],
        packages["python-dateutil"],
        packages["attrs"],
    ]

    venv_sequential = tox.tox_env.python.virtual_env.runner.VirtualEnvRunner()
    start_sequential = time.time()
    installer.install(poetry, venv_sequential, to_install, 0)
    sequential = time.time() - start_sequential

    venv_parallel = tox.tox_env.python.virtual_env.runner.VirtualEnvRunner()
    start_parallel = time.time()
    installer.install(poetry, venv_parallel, to_install, 5)
    parallel = time.time() - start_parallel

    # The mock delay during package install is static (one second) so these values should all
    # be within microseconds of each other
    assert parallel < sequential
    assert round(parallel * 5) == round(sequential)
    assert round(sequential) == len(set(to_install))
    assert round(parallel * 5) == len(set(to_install))


@pytest.mark.parametrize("num_threads", (0, 8))
def test_propagates_exceptions_during_installation(
    mock_venv, mock_poetry_factory, num_threads
):
    """Assert that an exception which occurs during installation is properly raised.

    Regression test for https://github.com/enpaul/tox-poetry-installer/issues/86
    """
    from tox_poetry_installer import _poetry  # pylint: disable=import-outside-toplevel

    poetry = Factory().create_poetry(None)
    packages: utilities.PackageMap = {
        item.name: item for item in poetry.locker.locked_repository().packages
    }
    to_install = [packages["toml"]]
    venv = tox.tox_env.python.virtual_env.runner.VirtualEnvRunner()
    fake_exception = ValueError("my testing exception")

    with mock.patch.object(
        _poetry,
        "Executor",
        **{"return_value.execute.side_effect": fake_exception},
    ):
        with pytest.raises(ValueError) as exc_info:
            installer.install(poetry, venv, to_install, num_threads)

    assert exc_info.value is fake_exception
