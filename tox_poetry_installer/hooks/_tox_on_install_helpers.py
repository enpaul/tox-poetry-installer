"""Helper functions for the :func:`tox_on_install` hook"""

import collections
import concurrent.futures
import contextlib
import datetime
import pathlib
from typing import Collection
from typing import Dict
from typing import List
from typing import Sequence
from typing import Set

import cleo.io.null_io
import packaging.utils
import poetry.config.config
import poetry.core.packages.dependency
import poetry.core.packages.package
import poetry.factory
import poetry.installation.executor
import poetry.installation.operations.install
import poetry.poetry
import poetry.utils.env
import tox.tox_env.api
import tox.tox_env.package

from tox_poetry_installer import constants
from tox_poetry_installer import exceptions
from tox_poetry_installer import logger


PackageMap = Dict[str, List[poetry.core.packages.package.Package]]


def check_preconditions(venv: tox.tox_env.api.ToxEnv) -> poetry.poetry.Poetry:
    """Check that the local project environment meets expectations"""

    # Skip running the plugin for the provisioning environment. The provisioned environment,
    # for alternative Tox versions and/or the ``requires`` meta dependencies is specially
    # handled by Tox and is out of scope for this plugin. Since one of the ways to install this
    # plugin in the first place is via the Tox provisioning environment, it quickly becomes a
    # chicken-and-egg problem.
    if isinstance(venv, tox.tox_env.package.PackageToxEnv):
        raise exceptions.SkipEnvironment(f"Skipping Tox provisioning env '{venv.name}'")

    try:
        return poetry.factory.Factory().create_poetry(venv.core["tox_root"])
    # Support running the plugin when the current tox project does not use Poetry for its
    # environment/dependency management.
    #
    # ``RuntimeError`` is dangerous to blindly catch because it can be (and in Poetry's case,
    # is) raised in many different places for different purposes.
    except RuntimeError as err:
        raise exceptions.SkipEnvironment(
            f"Skipping installation of locked dependencies due to a Poetry error: {err}"
        ) from None


def identify_transients(
    dep_name: str,
    packages: PackageMap,
    venv: poetry.utils.env.VirtualEnv,
    allow_missing: Sequence[str] = (),
) -> List[poetry.core.packages.package.Package]:
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

    def _transients(
        transient: poetry.core.packages.dependency.Dependency,
    ) -> List[poetry.core.packages.package.Package]:
        searched.add(transient.name)

        results: List[poetry.core.packages.package.Package] = []
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
    venv: poetry.utils.env.VirtualEnv,
    project: poetry.poetry.Poetry,
    extras: Sequence[str] = (),
) -> List[poetry.core.packages.package.Package]:
    """Find the root project dependencies

    Recursively identify the dependencies of the root project package

    :param packages: Mapping of all locked package names to their corresponding package object
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param project: Poetry object for the current project
    :param extras: Sequence of extra names to include the dependencies of
    """

    required_dep_names = [
        item.name for item in project.package.requires if not item.is_optional()
    ]

    extra_dep_names: List[str] = []
    for extra in extras:
        logger.info(f"Processing project extra '{extra}'")
        try:
            extra_dep_names += [
                item.name
                for item in project.package.extras[
                    packaging.utils.NormalizedName(extra)
                ]
            ]
        except KeyError:
            raise exceptions.ExtraNotFoundError(
                f"Environment specifies project extra '{extra}' which was not found in the lockfile"
            ) from None

    dependencies: List[poetry.core.packages.package.Package] = []
    for dep_name in required_dep_names + extra_dep_names:
        dependencies += identify_transients(
            dep_name.lower(), packages, venv, allow_missing=[project.package.name]
        )

    return dedupe_packages(dependencies)


def find_additional_deps(
    packages: PackageMap,
    venv: poetry.utils.env.VirtualEnv,
    project: poetry.poetry.Poetry,
    dep_names: Sequence[str],
) -> List[poetry.core.packages.package.Package]:
    """Find additional dependencies

    Recursively identify the dependencies of an arbitrary list of package names

    :param packages: Mapping of all locked package names to their corresponding package object
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param project: Poetry object for the current project
    :param dep_names: Sequence of additional dependency names to recursively find the transient
                      dependencies for
    """
    dependencies: List[poetry.core.packages.package.Package] = []
    for dep_name in dep_names:
        dependencies += identify_transients(
            dep_name.lower(), packages, venv, allow_missing=[project.package.name]
        )

    return dedupe_packages(dependencies)


def find_group_deps(
    group: str,
    packages: PackageMap,
    venv: poetry.utils.env.VirtualEnv,
    project: poetry.poetry.Poetry,
) -> List[poetry.core.packages.package.Package]:
    """Find the dependencies belonging to a dependency group

    Recursively identify the Poetry dev dependencies

    :param group: Name of the dependency group from the project's ``pyproject.toml``
    :param packages: Mapping of all locked package names to their corresponding package object
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param project: Poetry object for the current project
    """
    return find_additional_deps(
        packages,
        venv,
        project,
        # the type ignore here is due to the difficulties around getting nested data
        # from the inherrently unstructured toml structure (which necessarily is flexibly
        # typed) but in a situation where there is a meta-structure applied to it (i.e. a
        # pyproject.toml structure).
        project.pyproject.data["tool"]["poetry"]  # type: ignore
        .get("group", {})
        .get(group, {})
        .get("dependencies", {})
        .keys(),
    )


def find_dev_deps(
    packages: PackageMap,
    venv: poetry.utils.env.VirtualEnv,
    project: poetry.poetry.Poetry,
) -> List[poetry.core.packages.package.Package]:
    """Find the dev dependencies

    Recursively identify the Poetry dev dependencies

    :param packages: Mapping of all locked package names to their corresponding package object
    :param venv: Poetry virtual environment to use for package compatibility checks
    :param project: Poetry object for the current project
    """
    dev_group_deps = find_group_deps("dev", packages, venv, project)

    # Legacy pyproject.toml poetry format:
    legacy_dev_group_deps = find_additional_deps(
        packages,
        venv,
        project,
        # the type ignore here is due to the difficulties around getting nested data
        # from the inherrently unstructured toml structure (which necessarily is flexibly
        # typed) but in a situation where there is a meta-structure applied to it (i.e. a
        # pyproject.toml structure).
        project.pyproject.data["tool"]["poetry"].get("dev-dependencies", {}).keys(),  # type: ignore
    )

    # Poetry 1.2 unions these two toml sections.
    return dedupe_packages(dev_group_deps + legacy_dev_group_deps)


@contextlib.contextmanager
def _optional_parallelize(parallels: int):
    """A bit of cheat, really

    A context manager that exposes a common interface for the caller that optionally
    enables/disables the usage of the parallel thread pooler depending on the value of
    the ``parallels`` parameter.
    """
    if parallels > 0:
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallels) as executor:
            yield executor.submit
    else:
        yield lambda func, arg: func(arg)


def install_package(
    project: poetry.poetry.Poetry,
    venv: tox.tox_env.api.ToxEnv,
    packages: Collection[poetry.core.packages.package.Package],
    parallels: int = 0,
):
    """Install a bunch of packages to a virtualenv

    :param project: Poetry object the packages were sourced from
    :param venv: Tox virtual environment to install the packages to
    :param packages: List of packages to install to the virtual environment
    :param parallels: Number of parallel processes to use for installing dependency packages, or
                      ``None`` to disable parallelization.
    """

    logger.info(f"Installing {len(packages)} packages to environment at {venv.env_dir}")

    install_executor = poetry.installation.executor.Executor(
        env=convert_virtualenv(venv),
        io=cleo.io.null_io.NullIO(),
        pool=project.pool,
        config=poetry.config.config.Config(),
    )

    installed: Set[poetry.core.packages.package.Package] = set()

    def logged_install(dependency: poetry.core.packages.package.Package) -> None:
        start = datetime.datetime.now()
        logger.debug(f"Installing {dependency}")
        install_executor.execute(
            [poetry.installation.operations.install.Install(package=dependency)]
        )
        end = datetime.datetime.now()
        logger.debug(f"Finished installing {dependency} in {end - start}")

    with _optional_parallelize(parallels) as executor:
        futures = []
        for dependency in packages:
            if dependency not in installed:
                installed.add(dependency)
                logger.debug(f"Queuing {dependency}")
                future = executor(logged_install, dependency)
                if future is not None:
                    futures.append(future)
            else:
                logger.debug(f"Skipping {dependency}, already installed")
        logger.debug("Waiting for installs to finish...")

        for future in concurrent.futures.as_completed(futures):
            # Don't actually care about the return value, just waiting on the
            # future to ensure any exceptions that were raised in the called
            # function are propagated.
            future.result()


def dedupe_packages(
    packages: Sequence[poetry.core.packages.package.Package],
) -> List[poetry.core.packages.package.Package]:
    """Deduplicates a sequence of Packages while preserving ordering

    Adapted from StackOverflow: https://stackoverflow.com/a/480227
    """
    seen: Set[poetry.core.packages.package.Package] = set()
    # Make this faster, avoid method lookup below
    seen_add = seen.add
    return [p for p in packages if not (p in seen or seen_add(p))]


def convert_virtualenv(venv: tox.tox_env.api.ToxEnv) -> poetry.utils.env.VirtualEnv:
    """Convert a Tox venv to a Poetry venv

    :param venv: Tox ``VirtualEnv`` object representing a tox virtual environment
    :returns: Poetry ``VirtualEnv`` object representing a poetry virtual environment
    """
    return poetry.utils.env.VirtualEnv(path=pathlib.Path(venv.env_dir))


def build_package_map(project: poetry.poetry.Poetry) -> PackageMap:
    """Build the mapping of package names to objects

    :param project: Populated poetry object to load locked packages from
    :returns: Mapping of package names to Poetry package objects
    """
    packages = collections.defaultdict(list)
    for package in project.locker.locked_repository().packages:
        packages[str(package.name)].append(package)

    return packages
