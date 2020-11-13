"""Main hook definition module

All implementations of tox hooks are defined here, as well as any single-use helper functions
specifically related to implementing the hooks (to keep the size/readability of the hook functions
themselves manageable).
"""
from typing import List
from typing import Optional

from poetry.core.packages import Package as PoetryPackage
from poetry.factory import Factory as PoetryFactory
from poetry.poetry import Poetry
from tox import hookimpl
from tox import reporter
from tox.action import Action as ToxAction
from tox.config import Parser as ToxParser
from tox.venv import VirtualEnv as ToxVirtualEnv

from tox_poetry_installer import constants
from tox_poetry_installer import exceptions
from tox_poetry_installer import utilities
from tox_poetry_installer.datatypes import PackageMap


@hookimpl
def tox_addoption(parser: ToxParser):
    """Add required configuration options to the tox INI file

    Adds the ``require_locked_deps`` configuration option to the venv to check whether all
    dependencies should be treated as locked or not.
    """

    parser.add_testenv_attribute(
        name="install_dev_deps",
        type="bool",
        default=False,
        help="Automatically install all Poetry development dependencies to the environment",
    )

    parser.add_testenv_attribute(
        name="require_locked_deps",
        type="bool",
        default=False,
        help="Require all dependencies in the environment be installed using the Poetry lockfile",
    )

    parser.add_testenv_attribute(
        name="locked_deps",
        type="line-list",
        help="List of locked dependencies to install to the environment using the Poetry lockfile",
    )


@hookimpl
def tox_testenv_install_deps(venv: ToxVirtualEnv, action: ToxAction) -> Optional[bool]:
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
            f"{constants.REPORTER_PREFIX} skipping isolated build env '{action.name}'"
        )
        return None

    try:
        poetry = PoetryFactory().create_poetry(venv.envconfig.config.toxinidir)
    except RuntimeError:
        # Support running the plugin when the current tox project does not use Poetry for its
        # environment/dependency management.
        #
        # ``RuntimeError`` is dangerous to blindly catch because it can be (and in Poetry's case,
        # is) raised in many different places for different purposes.
        reporter.verbosity1(
            f"{constants.REPORTER_PREFIX} project does not use Poetry for env management, skipping installation of locked dependencies"
        )
        return None

    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} loaded project pyproject.toml from {poetry.file}"
    )

    package_map: PackageMap = {
        package.name: package
        for package in poetry.locker.locked_repository(True).packages
    }

    if venv.envconfig.require_locked_deps and venv.envconfig.deps:
        raise exceptions.LockedDepsRequiredError(
            f"Unlocked dependencies '{venv.envconfig.deps}' specified for environment '{venv.name}' which requires locked dependencies"
        )

    # Handle the installation of any locked env dependencies from the lockfile
    _install_env_dependencies(venv, poetry, package_map)

    # Handle the installation of the package dependencies from the lockfile if the package is
    # being installed to this venv; otherwise skip installing the package dependencies
    if venv.envconfig.skip_install:
        reporter.verbosity1(
            f"{constants.REPORTER_PREFIX} env specifies 'skip_install = true', skipping installation of project package"
        )
        return venv.envconfig.require_locked_deps or None

    if venv.envconfig.config.skipsdist:
        reporter.verbosity1(
            f"{constants.REPORTER_PREFIX} config specifies 'skipsdist = true', skipping installation of project package"
        )
        return venv.envconfig.require_locked_deps or None

    _install_project_dependencies(venv, poetry, package_map)

    return venv.envconfig.require_locked_deps or None


def _install_env_dependencies(
    venv: ToxVirtualEnv, poetry: Poetry, packages: PackageMap
):
    """Install the packages for a specified testenv

    Processes the tox environment config, identifies any locked environment dependencies, pulls
    them from the lockfile, and installs them to the virtual environment.

    :param venv: Tox virtual environment to install the packages to
    :param poetry: Poetry object the packages were sourced from
    :param packages: Mapping of package names to the corresponding package object
    """

    dependencies: List[PoetryPackage] = []
    for dep in venv.envconfig.locked_deps:
        try:
            dependencies += utilities.find_transients(packages, dep.lower())
        except exceptions.ToxPoetryInstallerException as err:
            venv.status = "lockfile installation failed"
            reporter.error(f"{constants.REPORTER_PREFIX} {err}")
            raise err

    if venv.envconfig.install_dev_deps:
        reporter.verbosity1(
            f"{constants.REPORTER_PREFIX} env specifies 'install_env_deps = true', including Poetry dev dependencies"
        )

        dev_dependencies = [
            dep
            for dep in poetry.locker.locked_repository(True).packages
            if dep not in poetry.locker.locked_repository(False).packages
        ]

        reporter.verbosity1(
            f"{constants.REPORTER_PREFIX} identified {len(dev_dependencies)} Poetry dev dependencies"
        )

        dependencies = list(set(dev_dependencies + dependencies))

    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} identified {len(dependencies)} total dependencies from {len(venv.envconfig.locked_deps)} locked env dependencies"
    )

    reporter.verbosity0(
        f"{constants.REPORTER_PREFIX} ({venv.name}) installing {len(dependencies)} env dependencies from lockfile"
    )
    utilities.install_to_venv(poetry, venv, dependencies)


def _install_project_dependencies(
    venv: ToxVirtualEnv, poetry: Poetry, packages: PackageMap
):
    """Install the dependencies of the project package

    Install all primary dependencies of the project package.

    :param venv: Tox virtual environment to install the packages to
    :param poetry: Poetry object the packages were sourced from
    :param packages: Mapping of package names to the corresponding package object
    """
    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} performing installation of project dependencies"
    )

    base_dependencies: List[PoetryPackage] = [
        packages[item.name]
        for item in poetry.package.requires
        if not item.is_optional()
    ]

    extra_dependencies: List[PoetryPackage] = []
    for extra in venv.envconfig.extras:
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
        try:
            dependencies += utilities.find_transients(packages, dep.name.lower())
        except exceptions.ToxPoetryInstallerException as err:
            venv.status = "lockfile installation failed"
            reporter.error(f"{constants.REPORTER_PREFIX} {err}")
            raise err

    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} identified {len(dependencies)} total dependencies from {len(poetry.package.requires)} project dependencies"
    )

    reporter.verbosity0(
        f"{constants.REPORTER_PREFIX} ({venv.name}) installing {len(dependencies)} project dependencies from lockfile"
    )
    utilities.install_to_venv(poetry, venv, dependencies)
