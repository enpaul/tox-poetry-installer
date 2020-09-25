"""Tox plugin for installing environments using Poetry

This plugin makes use of the ``tox_testenv_install_deps`` Tox plugin hook to replace the default
installation functionality to install dependencies from the Poetry lockfile for the project. It
does this by using ``poetry`` to read in the lockfile, identify necessary dependencies, and then
use Poetry's ``PipInstaller`` class to install those packages into the Tox environment.
"""
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

from poetry.factory import Factory as PoetryFactory
from poetry.factory import Poetry
from poetry.installation.pip_installer import PipInstaller as PoetryPipInstaller
from poetry.io.null_io import NullIO as PoetryNullIO
from poetry.packages import Package as PoetryPackage
from poetry.puzzle.provider import Provider as PoetryProvider
from poetry.utils.env import VirtualEnv as PoetryVirtualEnv
from tox import hookimpl
from tox import reporter
from tox.action import Action as ToxAction
from tox.venv import VirtualEnv as ToxVirtualEnv


__title__ = "tox-poetry-installer"
__summary__ = "Tox plugin to install Tox environment dependencies using the Poetry backend and lockfile"
__version__ = "0.1.3"
__url__ = "https://github.com/enpaul/tox-poetry-installer/"
__license__ = "MIT"
__authors__ = ["Ethan Paul <24588726+enpaul@users.noreply.github.com>"]


_PEP508_VERSION_DELIMITERS: Tuple[str, ...] = ("~=", "==", "!=", ">", "<")

_REPORTER_PREFIX = f"[{__title__}]:"


class ToxPoetryInstallerException(Exception):
    """Error while installing locked dependencies to the test environment"""


class NoLockedDependencyError(ToxPoetryInstallerException):
    """Cannot install a package that is not in the lockfile"""


def _install_to_venv(
    poetry: Poetry, venv: ToxVirtualEnv, packages: Sequence[PoetryPackage]
):
    """Install a bunch of packages to a virtualenv

    :param poetry: Poetry object the packages were sourced from
    :param venv: Tox virtual environment to install the packages to
    :param packages: List of packages to install to the virtual environment
    """
    installer = PoetryPipInstaller(
        env=PoetryVirtualEnv(path=Path(venv.envconfig.envdir)),
        io=PoetryNullIO(),
        pool=poetry.pool,
    )

    for dependency in packages:
        reporter.verbosity1(f"{_REPORTER_PREFIX} installing {dependency}")
        installer.install(dependency)


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
                reporter.warning(
                    f"{_REPORTER_PREFIX} installing '{name}' using Poetry is not supported; skipping"
                )
                return []
            transients = [packages[name]]
            for dep in packages[name].requires:
                transients += find_transients(dep.name)
            return transients

        return find_transients(top_level.name)

    except KeyError:
        if any(
            delimiter in dependency_name for delimiter in _PEP508_VERSION_DELIMITERS
        ):
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

    if action.name == venv.envconfig.config.isolated_build_env:
        reporter.verbosity1(
            f"{_REPORTER_PREFIX} skipping isolated build env '{action.name}'"
        )
        return None

    poetry = PoetryFactory().create_poetry(venv.envconfig.config.toxinidir)

    reporter.verbosity1(
        f"{_REPORTER_PREFIX} loaded project pyproject.toml from {poetry.file}"
    )

    dependencies: List[PoetryPackage] = []
    for env_dependency in venv.envconfig.deps:
        dependencies += _find_locked_dependencies(poetry, env_dependency.name)

    reporter.verbosity1(
        f"{_REPORTER_PREFIX} identified {len(dependencies)} actual dependencies from {len(venv.envconfig.deps)} specified env dependencies"
    )

    reporter.verbosity0(
        f"{_REPORTER_PREFIX} ({venv.name}) installing {len(dependencies)} env dependencies from lockfile"
    )
    _install_to_venv(poetry, venv, dependencies)

    if not venv.envconfig.skip_install:
        reporter.verbosity1(
            f"{_REPORTER_PREFIX} env specifies 'skip_install = false', performing installation of dev-package dependencies"
        )

        primary_dependencies = poetry.locker.locked_repository(False).packages
        reporter.verbosity1(
            f"{_REPORTER_PREFIX} identified {len(primary_dependencies)} dependencies of dev-package"
        )

        reporter.verbosity0(
            f"{_REPORTER_PREFIX} ({venv.name}) installing {len(primary_dependencies)} dev-package dependencies from lockfile"
        )
        _install_to_venv(poetry, venv, primary_dependencies)
    else:
        reporter.verbosity1(
            f"{_REPORTER_PREFIX} env specifies 'skip_install = true', skipping installation of dev-package package"
        )

    return dependencies
