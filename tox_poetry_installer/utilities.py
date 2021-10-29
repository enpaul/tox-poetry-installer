"""Helper utility functions, usually bridging Tox and Poetry functionality"""
# Silence this one globally to support the internal function imports for the proxied poetry module.
# See the docstring in 'tox_poetry_installer._poetry' for more context.
# pylint: disable=import-outside-toplevel
import typing
from pathlib import Path
from typing import List
from typing import Sequence
from typing import Set
from typing import Union

from poetry.core.packages import Dependency as PoetryDependency
from poetry.core.packages import Package as PoetryPackage
from tox.action import Action as ToxAction
from tox.venv import VirtualEnv as ToxVirtualEnv

from tox_poetry_installer import constants
from tox_poetry_installer import exceptions
from tox_poetry_installer import logger
from tox_poetry_installer.datatypes import PackageMap

if typing.TYPE_CHECKING:
    from tox_poetry_installer import _poetry


def check_preconditions(venv: ToxVirtualEnv, action: ToxAction) -> "_poetry.Poetry":
    """Check that the local project environment meets expectations"""
    # Skip running the plugin for the provisioning environment. The provisioned environment,
    # for alternative Tox versions and/or the ``requires`` meta dependencies is specially
    # handled by Tox and is out of scope for this plugin. Since one of the ways to install this
    # plugin in the first place is via the Tox provisioning environment, it quickly becomes a
    # chicken-and-egg problem.
    if action.name == venv.envconfig.config.provision_tox_env:
        raise exceptions.SkipEnvironment(
            f"Skipping Tox provisioning env '{action.name}'"
        )

    # Skip running the plugin for the packaging environment. PEP-517 front ends can handle
    # that better than we can, so let them do their thing. More to the point: if you're having
    # problems in the packaging env that this plugin would solve, god help you.
    if action.name == venv.envconfig.config.isolated_build_env:
        raise exceptions.SkipEnvironment(
            f"Skipping isolated packaging build env '{action.name}'"
        )

    if venv.envconfig.config.option.require_poetry:
        logger.warning(
            "DEPRECATION: The '--require-poetry' runtime option is deprecated and will be "
            "removed in version 1.0.0. Please update test environments that require Poetry to "
            "set the 'require_poetry = true' option in tox.ini"
        )

    if venv.envconfig.config.option.parallelize_locked_install is not None:
        logger.warning(
            "DEPRECATION: The '--parallelize-locked-install' option is deprecated and will "
            "be removed in version 1.0.0. Please use the '--parallel-install-threads' option."
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


def convert_virtualenv(venv: ToxVirtualEnv) -> "_poetry.VirtualEnv":
    """Convert a Tox venv to a Poetry venv

    :param venv: Tox ``VirtualEnv`` object representing a tox virtual environment
    :returns: Poetry ``VirtualEnv`` object representing a poetry virtual environment
    """
    from tox_poetry_installer import _poetry

    return _poetry.VirtualEnv(path=Path(venv.envconfig.envdir))


def identify_transients(
    dep: Union[PoetryDependency, str],
    packages: PackageMap,
    venv: "_poetry.VirtualEnv",
    allow_missing: Sequence[str] = (),
) -> List[PoetryPackage]:
    """Using a pool of packages, identify all transient dependencies of a given package name

    :param dep: Either the Poetry dependency or the dependency's bare package name to recursively
                identify the transient dependencies of
    :param packages: All packages from the lockfile to use for identifying dependency relationships.
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param allow_missing: Sequence of package names to allow to be missing from the lockfile. Any
                          packages that are not found in the lockfile but their name appears in this
                          list will be silently skipped from installation.
    :returns: List of packages that need to be installed for the requested dependency.

    .. note:: The package corresponding to the dependency specified by the ``dep`` parameter will
              be included in the returned list of packages.
    """
    transients: List[PoetryPackage] = []
    searched: Set[str] = set()

    def _deps_of_dep(transient: PoetryDependency):
        searched.add(transient.name)

        if venv.is_valid_for_marker(transient.marker):
            for requirement in packages[transient.name].requires:
                if requirement.name not in searched:
                    _deps_of_dep(requirement)
            logger.debug(f"Including {transient} for installation")
            transients.append(packages[transient.name])
        else:
            logger.debug(f"Skipping {transient}: package requires {transient.marker}")

    try:
        if isinstance(dep, str):
            dep = packages[dep].to_dependency()

        _deps_of_dep(dep)
    except KeyError as err:
        dep_name = err.args[0]

        if dep_name in constants.UNSAFE_PACKAGES:
            logger.warning(
                f"Installing package '{dep_name}' using Poetry is not supported and will be skipped"
            )
            logger.debug(f"Skipping {dep_name}: designated unsafe by Poetry")
            return []

        if dep_name in allow_missing:
            logger.debug(f"Skipping {dep_name}: package is allowed to be unlocked")
            return []

        if any(
            delimiter in dep_name for delimiter in constants.PEP508_VERSION_DELIMITERS
        ):
            raise exceptions.LockedDepVersionConflictError(
                f"Locked dependency '{dep_name}' cannot include version specifier"
            ) from None

        raise exceptions.LockedDepNotFoundError(
            f"No version of locked dependency '{dep_name}' found in the project lockfile"
        ) from None

    return transients


def find_project_deps(
    packages: PackageMap,
    venv: "_poetry.VirtualEnv",
    poetry: "_poetry.Poetry",
    extras: Sequence[str] = (),
) -> List[PoetryPackage]:
    """Find the root project dependencies

    Recursively identify the dependencies of the root project package

    :param packages: Mapping of all locked package names to their corresponding package object
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param poetry: Poetry object for the current project
    :param extras: Sequence of extra names to include the dependencies of
    """

    if any(dep.name in constants.UNSAFE_PACKAGES for dep in poetry.package.requires):
        raise exceptions.RequiresUnsafeDepError(
            f"Project package requires one or more unsafe dependencies ({', '.join(constants.UNSAFE_PACKAGES)}) which cannot be installed with Poetry"
        )

    base_deps: List[PoetryPackage] = [
        packages[item.name]
        for item in poetry.package.requires
        if not item.is_optional()
    ]

    extra_deps: List[PoetryPackage] = []
    for extra in extras:
        logger.info(f"Processing project extra '{extra}'")
        try:
            extra_deps += [packages[item.name] for item in poetry.package.extras[extra]]
        except KeyError:
            raise exceptions.ExtraNotFoundError(
                f"Environment specifies project extra '{extra}' which was not found in the lockfile"
            ) from None

    dependencies: List[PoetryPackage] = []
    for dep in base_deps + extra_deps:
        dependencies += identify_transients(
            dep.name.lower(), packages, venv, allow_missing=[poetry.package.name]
        )

    return dependencies


def find_additional_deps(
    packages: PackageMap,
    venv: "_poetry.VirtualEnv",
    poetry: "_poetry.Poetry",
    dep_names: Sequence[str],
) -> List[PoetryPackage]:
    """Find additional dependencies

    Recursively identify the dependencies of an arbitrary list of package names

    :param packages: Mapping of all locked package names to their corresponding package object
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param poetry: Poetry object for the current project
    :param dep_names: Sequence of additional dependency names to recursively find the transient
                      dependencies for
    """
    deps: List[PoetryPackage] = []
    for dep_name in dep_names:
        deps += identify_transients(
            dep_name.lower(), packages, venv, allow_missing=[poetry.package.name]
        )

    return deps


def find_dev_deps(
    packages: PackageMap, venv: "_poetry.VirtualEnv", poetry: "_poetry.Poetry"
) -> List[PoetryPackage]:
    """Find the dev dependencies

    Recursively identify the Poetry dev dependencies

    :param packages: Mapping of all locked package names to their corresponding package object
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param poetry: Poetry object for the current project
    """
    return find_additional_deps(
        packages,
        venv,
        poetry,
        poetry.pyproject.data["tool"]["poetry"].get("dev-dependencies", {}).keys(),
    )
