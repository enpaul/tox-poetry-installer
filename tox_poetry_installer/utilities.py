"""Helper utility functions, usually bridging Tox and Poetry functionality"""
from pathlib import Path
from typing import Sequence
from typing import Set

from poetry.core.packages import Package as PoetryPackage
from poetry.installation.pip_installer import PipInstaller as PoetryPipInstaller
from poetry.io.null_io import NullIO as PoetryNullIO
from poetry.poetry import Poetry
from poetry.puzzle.provider import Provider as PoetryProvider
from poetry.utils.env import VirtualEnv as PoetryVirtualEnv
from tox import reporter
from tox.venv import VirtualEnv as ToxVirtualEnv

from tox_poetry_installer import constants
from tox_poetry_installer import exceptions
from tox_poetry_installer.datatypes import PackageMap
from tox_poetry_installer.datatypes import SortedEnvDeps


def sort_env_deps(venv: ToxVirtualEnv) -> SortedEnvDeps:
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
        f"{constants.REPORTER_PREFIX} sorting {len(venv.envconfig.deps)} env dependencies by lock requirement"
    )
    unlocked_deps = []
    locked_deps = []

    for dep in venv.envconfig.deps:
        if venv.envconfig.require_locked_deps:
            reporter.verbosity1(
                f"{constants.REPORTER_PREFIX} lock required for env, treating '{dep.name}' as locked env dependency"
            )
            dep.name = dep.name.replace(constants.MAGIC_SUFFIX_MARKER, "")
            locked_deps.append(dep)
        else:
            if dep.name.endswith(constants.MAGIC_SUFFIX_MARKER):
                reporter.verbosity1(
                    f"{constants.REPORTER_PREFIX} specification includes marker '{constants.MAGIC_SUFFIX_MARKER}', treating '{dep.name}' as locked env dependency"
                )
                dep.name = dep.name.replace(constants.MAGIC_SUFFIX_MARKER, "")
                locked_deps.append(dep)
            else:
                reporter.verbosity1(
                    f"{constants.REPORTER_PREFIX} specification does not include marker '{constants.MAGIC_SUFFIX_MARKER}', treating '{dep.name}' as unlocked env dependency"
                )
                unlocked_deps.append(dep)

    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} identified {len(locked_deps)} locked env dependencies: {[item.name for item in locked_deps]}"
    )
    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} identified {len(unlocked_deps)} unlocked env dependencies: {[item.name for item in unlocked_deps]}"
    )

    return SortedEnvDeps(locked_deps=locked_deps, unlocked_deps=unlocked_deps)


def install_to_venv(
    poetry: Poetry, venv: ToxVirtualEnv, packages: Sequence[PoetryPackage]
):
    """Install a bunch of packages to a virtualenv

    :param poetry: Poetry object the packages were sourced from
    :param venv: Tox virtual environment to install the packages to
    :param packages: List of packages to install to the virtual environment
    """

    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} Installing {len(packages)} packages to environment at {venv.envconfig.envdir}"
    )

    installer = PoetryPipInstaller(
        env=PoetryVirtualEnv(path=Path(venv.envconfig.envdir)),
        io=PoetryNullIO(),
        pool=poetry.pool,
    )

    for dependency in packages:
        reporter.verbosity1(f"{constants.REPORTER_PREFIX} installing {dependency}")
        installer.install(dependency)


def find_transients(packages: PackageMap, dependency_name: str) -> Set[PoetryPackage]:
    """Using a poetry object identify all dependencies of a specific dependency

    :param poetry: Populated poetry object which can be used to build a populated locked
                   repository object.
    :param dependency_name: Bare name (without version) of the dependency to fetch the transient
                            dependencies of.
    :returns: List of packages that need to be installed for the requested dependency.

    .. note:: The package corresponding to the dependency named by ``dependency_name`` is included
              in the list of returned packages.
    """

    try:

        def find_deps_of_deps(name: str, transients: PackageMap):
            if name in PoetryProvider.UNSAFE_PACKAGES:
                reporter.warning(
                    f"{constants.REPORTER_PREFIX} installing package '{name}' using Poetry is not supported; skipping installation of package '{name}'"
                )
            else:
                transients[name] = packages[name]
                for dep in packages[name].requires:
                    if dep.name not in transients.keys():
                        find_deps_of_deps(dep.name, transients)

        transients: PackageMap = {}
        find_deps_of_deps(packages[dependency_name].name, transients)

        return set(transients.values())
    except KeyError:
        if any(
            delimiter in dependency_name
            for delimiter in constants.PEP508_VERSION_DELIMITERS
        ):
            raise exceptions.LockedDepVersionConflictError(
                f"Locked dependency '{dependency_name}' cannot include version specifier"
            ) from None
        raise exceptions.LockedDepNotFoundError(
            f"No version of locked dependency '{dependency_name}' found in the project lockfile"
        ) from None
