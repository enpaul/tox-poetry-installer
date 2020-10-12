"""Tox plugin for installing environments using Poetry

This plugin makes use of the ``tox_testenv_install_deps`` Tox plugin hook to replace the default
installation functionality to install dependencies from the Poetry lockfile for the project. It
does this by using ``poetry`` to read in the lockfile, identify necessary dependencies, and then
use Poetry's ``PipInstaller`` class to install those packages into the Tox environment.
"""
from pathlib import Path
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Sequence
from typing import Set
from typing import Tuple

from poetry.core.packages import Package as PoetryPackage
from poetry.factory import Factory as PoetryFactory
from poetry.installation.pip_installer import PipInstaller as PoetryPipInstaller
from poetry.io.null_io import NullIO as PoetryNullIO
from poetry.poetry import Poetry
from poetry.puzzle.provider import Provider as PoetryProvider
from poetry.utils.env import VirtualEnv as PoetryVirtualEnv
from tox import hookimpl
from tox import reporter
from tox.action import Action as ToxAction
from tox.config import DepConfig as ToxDepConfig
from tox.config import Parser as ToxParser
from tox.venv import VirtualEnv as ToxVirtualEnv


__title__ = "tox-poetry-installer"
__summary__ = "Tox plugin to install Tox environment dependencies using the Poetry backend and lockfile"
__version__ = "0.2.4"
__url__ = "https://github.com/enpaul/tox-poetry-installer/"
__license__ = "MIT"
__authors__ = ["Ethan Paul <24588726+enpaul@users.noreply.github.com>"]


# Valid PEP508 version delimiters. These are used to test whether a given string (specifically a
# dependency name) is just a package name or also includes a version identifier.
_PEP508_VERSION_DELIMITERS: Tuple[str, ...] = ("~=", "==", "!=", ">", "<")

# Prefix all reporter messages should include to indicate that they came from this module in the
# console output.
_REPORTER_PREFIX = f"[{__title__}]:"

# Suffix that indicates an env dependency should be treated as a locked dependency and thus be
# installed from the lockfile. Will be automatically stripped off of a dependency name during
# sorting so that the resulting string is just the valid package name. This becomes optional when
# the "require_locked_deps" option is true for an environment; in that case a bare dependency like
# 'foo' is treated the same as an explicitly locked dependency like 'foo@poetry'
_MAGIC_SUFFIX_MARKER = "@poetry"


class _SortedEnvDeps(NamedTuple):
    unlocked_deps: List[ToxDepConfig]
    locked_deps: List[ToxDepConfig]


class ToxPoetryInstallerException(Exception):
    """Error while installing locked dependencies to the test environment"""


class LockedDepVersionConflictError(ToxPoetryInstallerException):
    """Locked dependencies cannot specify an alternate version for installation"""


class LockedDepNotFoundError(ToxPoetryInstallerException):
    """Locked dependency was not found in the lockfile"""


def _sort_env_deps(venv: ToxVirtualEnv) -> _SortedEnvDeps:
    """Sorts the environment dependencies by lock status

    Lock status determines whether a given environment dependency will be installed from the
    lockfile using the Poetry backend, or whether this plugin will skip it and allow it to be
    installed using the default pip-based backend (an unlocked dependency).

    .. note:: A locked dependency must follow a required format. To avoid reinventing the wheel
              (no pun intended) this module does not have any infrastructure for parsing PEP-508
              version specifiers, and so requires locked dependencies to be specified with no
              version (the installed version being taken from the lockfile). If a dependency is
              specified as locked and its name is also a PEP-508 string then an error will be
              raised.
    """

    reporter.verbosity1(
        f"{_REPORTER_PREFIX} sorting {len(venv.envconfig.deps)} env dependencies by lock requirement"
    )
    unlocked_deps = []
    locked_deps = []

    for dep in venv.envconfig.deps:
        if venv.envconfig.require_locked_deps:
            reporter.verbosity1(
                f"{_REPORTER_PREFIX} lock required for env, treating '{dep.name}' as locked env dependency"
            )
            dep.name = dep.name.replace(_MAGIC_SUFFIX_MARKER, "")
            locked_deps.append(dep)
        else:
            if dep.name.endswith(_MAGIC_SUFFIX_MARKER):
                reporter.verbosity1(
                    f"{_REPORTER_PREFIX} specification includes marker '{_MAGIC_SUFFIX_MARKER}', treating '{dep.name}' as locked env dependency"
                )
                dep.name = dep.name.replace(_MAGIC_SUFFIX_MARKER, "")
                locked_deps.append(dep)
            else:
                reporter.verbosity1(
                    f"{_REPORTER_PREFIX} specification does not include marker '{_MAGIC_SUFFIX_MARKER}', treating '{dep.name}' as unlocked env dependency"
                )
                unlocked_deps.append(dep)

    reporter.verbosity1(
        f"{_REPORTER_PREFIX} identified {len(locked_deps)} locked env dependencies for installation from poetry lockfile: {[item.name for item in locked_deps]}"
    )
    reporter.verbosity1(
        f"{_REPORTER_PREFIX} identified {len(unlocked_deps)} unlocked env dependencies for installation using default backend: {[item.name for item in unlocked_deps]}"
    )

    return _SortedEnvDeps(locked_deps=locked_deps, unlocked_deps=unlocked_deps)


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


def _find_transients(poetry: Poetry, dependency_name: str) -> Set[PoetryPackage]:
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

        def find_deps_of_deps(name: str) -> List[PoetryPackage]:
            if name in PoetryProvider.UNSAFE_PACKAGES:
                reporter.warning(
                    f"{_REPORTER_PREFIX} installing '{name}' using Poetry is not supported; skipping"
                )
                return []
            transients = [packages[name]]
            for dep in packages[name].requires:
                transients += find_deps_of_deps(dep.name)
            return transients

        return set(find_deps_of_deps(top_level.name))

    except KeyError:
        if any(
            delimiter in dependency_name for delimiter in _PEP508_VERSION_DELIMITERS
        ):
            raise LockedDepVersionConflictError(
                f"Locked dependency '{dependency_name}' cannot include version specifier"
            ) from None
        raise LockedDepNotFoundError(
            f"No version of locked dependency '{dependency_name}' found in the project lockfile"
        ) from None


def _install_env_dependencies(venv: ToxVirtualEnv, poetry: Poetry):
    env_deps = _sort_env_deps(venv)

    dependencies: List[PoetryPackage] = []
    for dep in env_deps.locked_deps:
        try:
            dependencies += _find_transients(poetry, dep.name.lower())
        except ToxPoetryInstallerException as err:
            venv.status = "lockfile installation failed"
            reporter.error(f"{_REPORTER_PREFIX} {err}")
            raise err

    reporter.verbosity1(
        f"{_REPORTER_PREFIX} identified {len(dependencies)} actual dependencies from {len(venv.envconfig.deps)} specified env dependencies"
    )

    reporter.verbosity1(
        f"{_REPORTER_PREFIX} updating env config with {len(env_deps.unlocked_deps)} unlocked env dependencies for installation using the default backend"
    )
    venv.envconfig.deps = env_deps.unlocked_deps

    reporter.verbosity0(
        f"{_REPORTER_PREFIX} ({venv.name}) installing {len(dependencies)} env dependencies from lockfile"
    )
    _install_to_venv(poetry, venv, dependencies)


def _install_package_dependencies(venv: ToxVirtualEnv, poetry: Poetry):
    reporter.verbosity1(
        f"{_REPORTER_PREFIX} performing installation of project dependencies"
    )

    primary_dependencies = poetry.locker.locked_repository(False).packages

    reporter.verbosity1(
        f"{_REPORTER_PREFIX} identified {len(primary_dependencies)} dependencies of project '{poetry.package.name}'"
    )

    reporter.verbosity0(
        f"{_REPORTER_PREFIX} ({venv.name}) installing {len(primary_dependencies)} project dependencies from lockfile"
    )
    _install_to_venv(poetry, venv, primary_dependencies)


@hookimpl
def tox_addoption(parser: ToxParser):
    """Add required configuration options to the tox INI file

    Adds the ``require_locked_deps`` configuration option to the venv to check whether all
    dependencies should be treated as locked or not.
    """

    parser.add_testenv_attribute(
        name="require_locked_deps",
        type="bool",
        default=False,
        help="Require all dependencies in the environment be installed using the Poetry lockfile",
    )


@hookimpl
def tox_testenv_install_deps(venv: ToxVirtualEnv, action: ToxAction):
    """Install the dependencies for the current environment

    Loads the local Poetry environment and the corresponding lockfile then pulls the dependencies
    specified by the Tox environment. Finally these dependencies are installed into the Tox
    environment using the Poetry ``PipInstaller`` backend.

    :param venv: Tox virtual environment object with configuration for the local Tox environment.
    :param action: Tox action object
    """

    if action.name == venv.envconfig.config.isolated_build_env:
        # Skip running the plugin for the packaging environment. PEP-517 front ends can handle
        # that better than we can, so let them do their thing. More to the point: if you're having
        # problems in the packaging env that this plugin would solve, god help you.
        reporter.verbosity1(
            f"{_REPORTER_PREFIX} skipping isolated build env '{action.name}'"
        )
        return

    try:
        poetry = PoetryFactory().create_poetry(venv.envconfig.config.toxinidir)
    except RuntimeError:
        # Support running the plugin when the current tox project does not use Poetry for its
        # environment/dependency management.
        #
        # ``RuntimeError`` is dangerous to blindly catch because it can be (and in Poetry's case,
        # is) raised in many different places for different purposes.
        reporter.verbosity1(
            f"{_REPORTER_PREFIX} project does not use Poetry for env management, skipping installation of locked dependencies"
        )
        return

    reporter.verbosity1(
        f"{_REPORTER_PREFIX} loaded project pyproject.toml from {poetry.file}"
    )

    # Handle the installation of any locked env dependencies from the lockfile
    _install_env_dependencies(venv, poetry)

    # Handle the installation of the package dependencies from the lockfile if the package is
    # being installed to this venv; otherwise skip installing the package dependencies
    if not venv.envconfig.skip_install and not venv.envconfig.config.skipsdist:
        _install_package_dependencies(venv, poetry)
    else:
        if venv.envconfig.skip_install:
            reporter.verbosity1(
                f"{_REPORTER_PREFIX} env specifies 'skip_install = true', skipping installation of project package"
            )
        elif venv.envconfig.config.skipsdist:
            reporter.verbosity1(
                f"{_REPORTER_PREFIX} config specifies 'skipsdist = true', skipping installation of project package"
            )
