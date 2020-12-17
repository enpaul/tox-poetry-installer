"""Helper utility functions, usually bridging Tox and Poetry functionality"""
# Silence this one globally to support the internal function imports for the proxied poetry module.
# See the docstring in 'tox_poetry_installer._poetry' for more context.
# pylint: disable=import-outside-toplevel
import sys
import typing
from pathlib import Path
from typing import List
from typing import Sequence
from typing import Set

from poetry.core.packages import Package as PoetryPackage
from tox import reporter
from tox.action import Action as ToxAction
from tox.venv import VirtualEnv as ToxVirtualEnv

from tox_poetry_installer import constants
from tox_poetry_installer import exceptions
from tox_poetry_installer.datatypes import PackageMap

if typing.TYPE_CHECKING:
    from tox_poetry_installer import _poetry


def install_to_venv(
    poetry: "_poetry.Poetry", venv: ToxVirtualEnv, packages: Sequence[PoetryPackage]
):
    """Install a bunch of packages to a virtualenv

    :param poetry: Poetry object the packages were sourced from
    :param venv: Tox virtual environment to install the packages to
    :param packages: List of packages to install to the virtual environment
    """
    from tox_poetry_installer import _poetry

    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} Installing {len(packages)} packages to environment at {venv.envconfig.envdir}"
    )

    installer = _poetry.PipInstaller(
        env=_poetry.VirtualEnv(path=Path(venv.envconfig.envdir)),
        io=_poetry.NullIO(),
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
    from tox_poetry_installer import _poetry

    def find_deps_of_deps(name: str, searched: Set[str]) -> PackageMap:
        searched.add(name)

        if name in _poetry.Provider.UNSAFE_PACKAGES:
            reporter.warning(
                f"{constants.REPORTER_PREFIX} Installing package '{name}' using Poetry is not supported and will be skipped"
            )
            reporter.verbosity2(
                f"{constants.REPORTER_PREFIX} Skip {name}: designated unsafe by Poetry"
            )
            return dict()

        transients: PackageMap = {}
        package = packages[name]

        if not package.python_constraint.allows(constants.PLATFORM_VERSION):
            reporter.verbosity2(
                f"{constants.REPORTER_PREFIX} Skip {package}: incompatible Python requirement '{package.python_constraint}' for current version '{constants.PLATFORM_VERSION}'"
            )
        elif package.platform is not None and package.platform != sys.platform:
            reporter.verbosity2(
                f"{constants.REPORTER_PREFIX} Skip {package}: incompatible platform requirement '{package.platform}' for current platform '{sys.platform}'"
            )
        else:
            reporter.verbosity2(
                f"{constants.REPORTER_PREFIX} Including {package} for installation"
            )
            transients[name] = package
            for index, dep in enumerate(package.requires):
                reporter.verbosity2(
                    f"{constants.REPORTER_PREFIX} Processing dependency {index + 1}/{len(package.requires)} for {package}: {dep.name}"
                )
                if dep.name not in searched:
                    transients.update(find_deps_of_deps(dep.name, searched))
                else:
                    reporter.verbosity2(
                        f"{constants.REPORTER_PREFIX} Package with name '{dep.name}' has already been processed, skipping"
                    )

        return transients

    searched: Set[str] = set()

    try:
        transients: PackageMap = find_deps_of_deps(
            packages[dependency_name].name, searched
        )
    except KeyError:
        if dependency_name in _poetry.Provider.UNSAFE_PACKAGES:
            reporter.warning(
                f"{constants.REPORTER_PREFIX} Installing package '{dependency_name}' using Poetry is not supported and will be skipped"
            )
            return set()

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

    return set(transients.values())


def check_preconditions(venv: ToxVirtualEnv, action: ToxAction) -> "_poetry.Poetry":
    """Check that the local project environment meets expectations"""
    # Skip running the plugin for the packaging environment. PEP-517 front ends can handle
    # that better than we can, so let them do their thing. More to the point: if you're having
    # problems in the packaging env that this plugin would solve, god help you.
    if action.name == venv.envconfig.config.isolated_build_env:
        raise exceptions.SkipEnvironment(
            f"Skipping isolated packaging build env '{action.name}'"
        )

    from tox_poetry_installer import _poetry

    try:
        return _poetry.Factory().create_poetry(venv.envconfig.config.toxinidir)
    # Support running the plugin when the current tox project does not use Poetry for its
    # environment/dependency management.
    #
    # ``RuntimeError`` is dangerous to blindly catch because it can be (and in Poetry's case,
    # is) raised in many different places for different purposes.
    except RuntimeError:
        raise exceptions.SkipEnvironment(
            "Project does not use Poetry for env management, skipping installation of locked dependencies"
        ) from None


def find_project_dependencies(
    venv: ToxVirtualEnv, poetry: "_poetry.Poetry", packages: PackageMap
) -> List[PoetryPackage]:
    """Install the dependencies of the project package

    Install all primary dependencies of the project package.

    :param venv: Tox virtual environment to install the packages to
    :param poetry: Poetry object the packages were sourced from
    :param packages: Mapping of package names to the corresponding package object
    """

    base_dependencies: List[PoetryPackage] = [
        packages[item.name]
        for item in poetry.package.requires
        if not item.is_optional()
    ]

    extra_dependencies: List[PoetryPackage] = []
    for extra in venv.envconfig.extras:
        reporter.verbosity1(
            f"{constants.REPORTER_PREFIX} Processing project extra '{extra}'"
        )
        try:
            extra_dependencies += [
                packages[item.name] for item in poetry.package.extras[extra]
            ]
        except KeyError:
            raise exceptions.ExtraNotFoundError(
                f"Environment '{venv.name}' specifies project extra '{extra}' which was not found in the lockfile"
            ) from None

    dependencies: List[PoetryPackage] = []
    for dep in base_dependencies + extra_dependencies:
        dependencies += find_transients(packages, dep.name.lower())

    return dependencies
