"""Helper utility functions, usually bridging Tox and Poetry functionality"""
import sys
from pathlib import Path
from typing import Sequence
from typing import Set

from poetry.core.packages import Package as PoetryPackage
from poetry.core.semver.version import Version
from poetry.factory import Factory as PoetryFactory
from poetry.installation.pip_installer import PipInstaller as PoetryPipInstaller
from poetry.io.null_io import NullIO as PoetryNullIO
from poetry.poetry import Poetry
from poetry.puzzle.provider import Provider as PoetryProvider
from poetry.utils.env import VirtualEnv as PoetryVirtualEnv
from tox import reporter
from tox.action import Action as ToxAction
from tox.venv import VirtualEnv as ToxVirtualEnv

from tox_poetry_installer import constants
from tox_poetry_installer import exceptions
from tox_poetry_installer.datatypes import PackageMap


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
        reporter.verbosity1(f"{constants.REPORTER_PREFIX} Installing {dependency}")
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

        def find_deps_of_deps(name: str, searched: Set[str]) -> PackageMap:
            package = packages[name]
            local_version = Version(
                major=sys.version_info.major,
                minor=sys.version_info.minor,
                patch=sys.version_info.micro,
            )
            transients: PackageMap = {}
            searched.update([name])

            if name in PoetryProvider.UNSAFE_PACKAGES:
                reporter.warning(
                    f"{constants.REPORTER_PREFIX} Installing package '{name}' using Poetry is not supported; skipping installation of package '{name}'"
                )
                reporter.verbosity2(
                    f"{constants.REPORTER_PREFIX} Skip {package}: designated unsafe by Poetry"
                )
            elif not package.python_constraint.allows(local_version):
                reporter.verbosity2(
                    f"{constants.REPORTER_PREFIX} Skip {package}: incompatible Python requirement '{package.python_constraint}' for current version '{local_version}'"
                )
            elif package.platform is not None and package.platform != sys.platform:
                reporter.verbosity2(
                    f"{constants.REPORTER_PREFIX} Skip {package}: incompatible platform requirement '{package.platform}' for current platform '{sys.platform}'"
                )
            else:
                reporter.verbosity2(f"{constants.REPORTER_PREFIX} Include {package}")
                transients[name] = package
                for dep in package.requires:
                    if dep.name not in searched:
                        transients.update(find_deps_of_deps(dep.name, searched))

            return transients

        searched: Set[str] = set()
        transients: PackageMap = find_deps_of_deps(
            packages[dependency_name].name, searched
        )

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


def check_preconditions(venv: ToxVirtualEnv, action: ToxAction) -> Poetry:
    """Check that the local project environment meets expectations"""
    # Skip running the plugin for the packaging environment. PEP-517 front ends can handle
    # that better than we can, so let them do their thing. More to the point: if you're having
    # problems in the packaging env that this plugin would solve, god help you.
    if action.name == venv.envconfig.config.isolated_build_env:
        raise exceptions.SkipEnvironment(
            f"Skipping isolated packaging build env '{action.name}'"
        )

    try:
        return PoetryFactory().create_poetry(venv.envconfig.config.toxinidir)
    # Support running the plugin when the current tox project does not use Poetry for its
    # environment/dependency management.
    #
    # ``RuntimeError`` is dangerous to blindly catch because it can be (and in Poetry's case,
    # is) raised in many different places for different purposes.
    except RuntimeError:
        raise exceptions.SkipEnvironment(
            "Project does not use Poetry for env management, skipping installation of locked dependencies"
        ) from None
