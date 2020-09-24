"""Tox plugin for installing environments using Poetry

This plugin makes use of the ``tox_testenv_install_deps`` Tox plugin hook to replace the default
installation functionality to install dependencies from the Poetry lockfile for the project. It
does this by using ``poetry`` to read in the lockfile, identify necessary dependencies, and then
use Poetry's ``PipInstaller`` class to install those packages into the Tox environment.
"""
import logging
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from poetry.factory import Factory as PoetryFactory
from poetry.factory import Poetry
from poetry.installation.pip_installer import PipInstaller as PoetryPipInstaller
from poetry.io.null_io import NullIO as PoetryNullIO
from poetry.packages import Package as PoetryPackage
from poetry.puzzle.provider import Provider as PoetryProvider
from poetry.utils.env import VirtualEnv as PoetryVirtualEnv
from tox import hookimpl
from tox.action import Action as ToxAction
from tox.venv import VirtualEnv as ToxVirtualEnv


__title__ = "tox-poetry-installer"
__summary__ = "Tox plugin to install Tox environment dependencies using the Poetry backend and lockfile"
__version__ = "0.1.0"
__url__ = "https://github.com/enpaul/tox-poetry-installer/"
__license__ = "MIT"
__authors__ = ["Ethan Paul <e@enp.one>"]


PEP440_VERSION_DELIMITERS: Tuple[str, ...] = ("~=", "==", "!=", ">", "<")


class ToxPoetryInstallerException(Exception):
    """Error while installing locked dependencies to the test environment"""


class NoLockedDependencyError(ToxPoetryInstallerException):
    """Cannot install a package that is not in the lockfile"""


def _make_poetry(venv: ToxVirtualEnv) -> Poetry:
    """Helper to make a poetry object from a toxenv"""
    return PoetryFactory().create_poetry(venv.envconfig.config.toxinidir)


def _find_locked_dependencies(
    poetry: Poetry, dependency_name: str
) -> List[PoetryPackage]:
    """Using a poetry object identify all dependencies of a specific dependency

    :param poetry: Populated poetry object which can be used to build a populated locked
                   repository object.
    :param dependency_name: Bare name (without version) of the dependency to fetch the transient
                            dependencies of.
    :returns: List of packages that need to be installed for the requested dependency.

    .. note:: The package corresponding to the dependency named by ``dependency_name`` is included
              in the list of returned packages.
    """
    packages: Dict[str, PoetryPackage] = {
        package.name: package
        for package in poetry.locker.locked_repository(True).packages
    }

    try:
        top_level = packages[dependency_name]

        def find_transients(name: str) -> List[PoetryPackage]:
            if name in PoetryProvider.UNSAFE_PACKAGES:
                return []
            transients = [packages[name]]
            for dep in packages[name].requires:
                transients += find_transients(dep.name)
            return transients

        return find_transients(top_level.name)

    except KeyError:
        if any(delimiter in dependency_name for delimiter in PEP440_VERSION_DELIMITERS):
            message = "specifying a version in the tox environment definition is incompatible with installing from a lockfile"
        else:
            message = (
                "no version of the package was found in the current project's lockfile"
            )

        raise NoLockedDependencyError(
            f"Cannot install requirement '{dependency_name}': {message}"
        ) from None


@hookimpl
def tox_testenv_install_deps(
    venv: ToxVirtualEnv, action: ToxAction
) -> Optional[List[PoetryPackage]]:
    """Install the dependencies for the current environment

    Loads the local Poetry environment and the corresponding lockfile then pulls the dependencies
    specified by the Tox environment. Finally these dependencies are installed into the Tox
    environment using the Poetry ``PipInstaller`` backend.

    :param venv: Tox virtual environment object with configuration for the local Tox environment.
    :param action: Tox action object
    """

    logger = logging.getLogger(__name__)

    if action.name == venv.envconfig.config.isolated_build_env:
        logger.debug(
            f"Environment {action.name} is isolated build environment; skipping Poetry-based dependency installation"
        )
        return None

    poetry = _make_poetry(venv)

    logger.debug(f"Loaded project pyproject.toml from {poetry.file}")

    dependencies: List[PoetryPackage] = []
    for env_dependency in venv.envconfig.deps:
        dependencies += _find_locked_dependencies(poetry, env_dependency.name)

    logger.debug(
        f"Identified {len(dependencies)} dependencies for environment {action.name}"
    )

    installer = PoetryPipInstaller(
        env=PoetryVirtualEnv(path=Path(venv.envconfig.envdir)),
        io=PoetryNullIO(),
        pool=poetry.pool,
    )

    for dependency in dependencies:
        logger.info(f"Installing environment dependency: {dependency}")
        installer.install(dependency)

    return dependencies
