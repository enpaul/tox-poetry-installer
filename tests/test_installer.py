# pylint: disable=missing-module-docstring, redefined-outer-name, unused-argument, wrong-import-order, unused-import
import time

import tox.venv
from poetry.factory import Factory

from .fixtures import mock_poetry_factory
from .fixtures import mock_venv
from tox_poetry_installer import datatypes
from tox_poetry_installer import installer


def test_deduplication(mock_venv, mock_poetry_factory):
    """Test that the installer does not install duplicate dependencies"""
    poetry = Factory().create_poetry(None)
    packages: datatypes.PackageMap = {
        item.name: item for item in poetry.locker.locked_repository(False).packages
    }

    venv = tox.venv.VirtualEnv()
    to_install = [packages["toml"], packages["toml"]]

    installer.install(poetry, venv, to_install)

    assert len(set(to_install)) == len(venv.installed)  # pylint: disable=no-member


def test_parallelization(mock_venv, mock_poetry_factory):
    """Test that behavior is consistent between parallel and non-parallel usage"""
    poetry = Factory().create_poetry(None)
    packages: datatypes.PackageMap = {
        item.name: item for item in poetry.locker.locked_repository(False).packages
    }

    to_install = [
        packages["toml"],
        packages["toml"],
        packages["tox"],
        packages["requests"],
        packages["python-dateutil"],
        packages["attrs"],
    ]

    venv_sequential = tox.venv.VirtualEnv()
    start_sequential = time.time()
    installer.install(poetry, venv_sequential, to_install, 0)
    sequential = time.time() - start_sequential

    venv_parallel = tox.venv.VirtualEnv()
    start_parallel = time.time()
    installer.install(poetry, venv_parallel, to_install, 5)
    parallel = time.time() - start_parallel

    # The mock delay during package install is static (one second) so these values should all
    # be within microseconds of each other
    assert parallel < sequential
    assert round(parallel * 5) == round(sequential)
    assert round(sequential) == len(set(to_install))
    assert round(parallel * 5) == len(set(to_install))
