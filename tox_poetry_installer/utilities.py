"""Helper utility functions, usually bridging Tox and Poetry functionality"""
# Silence this one globally to support the internal function imports for the proxied poetry module.
# See the docstring in 'tox_poetry_installer._poetry' for more context.
# pylint: disable=import-outside-toplevel
import collections
import typing
from pathlib import Path
from typing import Dict
from typing import List
from typing import Sequence
from typing import Set

from poetry.core.packages.dependency import Dependency as PoetryDependency
from poetry.core.packages.package import Package as PoetryPackage
from tox.tox_env.api import ToxEnv as ToxVirtualEnv
from tox.tox_env.package import PackageToxEnv

from tox_poetry_installer import constants
from tox_poetry_installer import exceptions
from tox_poetry_installer import logger

if typing.TYPE_CHECKING:
    from tox_poetry_installer import _poetry


PackageMap = Dict[str, List[PoetryPackage]]


def check_preconditions(venv: ToxVirtualEnv) -> "_poetry.Poetry":
    """Check that the local project environment meets expectations"""

    # Skip running the plugin for the provisioning environment. The provisioned environment,
    # for alternative Tox versions and/or the ``requires`` meta dependencies is specially
    # handled by Tox and is out of scope for this plugin. Since one of the ways to install this
    # plugin in the first place is via the Tox provisioning environment, it quickly becomes a
    # chicken-and-egg problem.
    if isinstance(venv, PackageToxEnv):
        raise exceptions.SkipEnvironment(f"Skipping Tox provisioning env '{venv.name}'")

    if venv.options.require_poetry:
        logger.warning(
            "DEPRECATION: The '--require-poetry' runtime option is deprecated and will be "
            "removed in version 1.0.0. Please update test environments that require Poetry to "
            "set the 'require_poetry = true' option in tox.ini"
        )

    from tox_poetry_installer import _poetry

    try:
        return _poetry.Factory().create_poetry(venv.core["tox_root"])
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

    return _poetry.VirtualEnv(path=Path(venv.env_dir))


def build_package_map(poetry: "_poetry.Poetry") -> PackageMap:
    """Build the mapping of package names to objects

    :param poetry: Populated poetry object to load locked packages from
    :returns: Mapping of package names to Poetry package objects
    """
    packages = collections.defaultdict(list)
    for package in poetry.locker.locked_repository().packages:
        packages[package.name].append(package)

    return packages


def identify_transients(
    dep_name: str,
    packages: PackageMap,
    venv: "_poetry.VirtualEnv",
    allow_missing: Sequence[str] = (),
) -> List[PoetryPackage]:
    """Using a pool of packages, identify all transient dependencies of a given package name

    :param dep_name: Either the Poetry dependency or the dependency's bare package name to recursively
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
    searched: Set[str] = set()

    def _transients(transient: PoetryDependency) -> List[PoetryPackage]:
        searched.add(transient.name)

        results: List[PoetryPackage] = []
        for option in packages[transient.name]:
            if venv.is_valid_for_marker(option.to_dependency().marker):
                for requirement in option.requires:
                    if requirement.name not in searched:
                        results += _transients(requirement)
                logger.debug(f"Including {option} for installation")
                results.append(option)
                break
        else:
            logger.debug(
                f"Skipping {transient.name}: target python version is {'.'.join([str(item) for item in venv.get_version_info()])} but package requires {transient.marker}"
            )

        return results

    try:
        for option in packages[dep_name]:
            if venv.is_valid_for_marker(option.to_dependency().marker):
                dep = option.to_dependency()
                break
        else:
            logger.warning(
                f"Skipping {dep_name}: no locked version found compatible with target python version {'.'.join([str(item) for item in venv.get_version_info()])}"
            )
            return []

        return _transients(dep)
    except KeyError as err:
        missing = err.args[0]

        if missing in constants.UNSAFE_PACKAGES:
            logger.warning(
                f"Installing package '{missing}' using Poetry is not supported and will be skipped"
            )
            logger.debug(f"Skipping {missing}: designated unsafe by Poetry")
            return []

        if missing in allow_missing:
            logger.debug(f"Skipping {missing}: package is allowed to be unlocked")
            return []

        if any(
            delimiter in missing for delimiter in constants.PEP508_VERSION_DELIMITERS
        ):
            raise exceptions.LockedDepVersionConflictError(
                f"Locked dependency '{missing}' cannot include version specifier"
            ) from None

        raise exceptions.LockedDepNotFoundError(
            f"No version of locked dependency '{missing}' found in the project lockfile"
        ) from None


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

    required_dep_names = [
        item.name for item in poetry.package.requires if not item.is_optional()
    ]

    extra_dep_names: List[str] = []
    for extra in extras:
        logger.info(f"Processing project extra '{extra}'")
        try:
            extra_dep_names += [item.name for item in poetry.package.extras[extra]]
        except KeyError:
            raise exceptions.ExtraNotFoundError(
                f"Environment specifies project extra '{extra}' which was not found in the lockfile"
            ) from None

    dependencies: List[PoetryPackage] = []
    for dep_name in required_dep_names + extra_dep_names:
        dependencies += identify_transients(
            dep_name.lower(), packages, venv, allow_missing=[poetry.package.name]
        )

    return dedupe_packages(dependencies)


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
    dependencies: List[PoetryPackage] = []
    for dep_name in dep_names:
        dependencies += identify_transients(
            dep_name.lower(), packages, venv, allow_missing=[poetry.package.name]
        )

    return dedupe_packages(dependencies)


def find_group_deps(
    group: str,
    packages: PackageMap,
    venv: "_poetry.VirtualEnv",
    poetry: "_poetry.Poetry",
) -> List[PoetryPackage]:
    """Find the dependencies belonging to a dependency group

    Recursively identify the Poetry dev dependencies

    :param group: Name of the dependency group from the project's ``pyproject.toml``
    :param packages: Mapping of all locked package names to their corresponding package object
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param poetry: Poetry object for the current project
    """
    return find_additional_deps(
        packages,
        venv,
        poetry,
        poetry.pyproject.data["tool"]["poetry"]
        .get("group", {})
        .get(group, {})
        .get("dependencies", {})
        .keys(),
    )


def find_dev_deps(
    packages: PackageMap, venv: "_poetry.VirtualEnv", poetry: "_poetry.Poetry"
) -> List[PoetryPackage]:
    """Find the dev dependencies

    Recursively identify the Poetry dev dependencies

    :param packages: Mapping of all locked package names to their corresponding package object
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param poetry: Poetry object for the current project
    """
    dev_group_deps = find_group_deps("dev", packages, venv, poetry)

    # Legacy pyproject.toml poetry format:
    legacy_dev_group_deps = find_additional_deps(
        packages,
        venv,
        poetry,
        poetry.pyproject.data["tool"]["poetry"].get("dev-dependencies", {}).keys(),
    )

    # Poetry 1.2 unions these two toml sections.
    return dedupe_packages(dev_group_deps + legacy_dev_group_deps)


def dedupe_packages(packages: Sequence[PoetryPackage]) -> List[PoetryPackage]:
    """Deduplicates a sequence of PoetryPackages while preserving ordering

    Adapted from StackOverflow: https://stackoverflow.com/a/480227
    """
    seen: Set[PoetryPackage] = set()
    # Make this faster, avoid method lookup below
    seen_add = seen.add
    return [p for p in packages if not (p in seen or seen_add(p))]
