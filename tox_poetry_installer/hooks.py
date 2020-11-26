"""Main hook definition module

All implementations of tox hooks are defined here, as well as any single-use helper functions
specifically related to implementing the hooks (to keep the size/readability of the hook functions
themselves manageable).
"""
from typing import List
from typing import Optional

from poetry.core.packages import Package as PoetryPackage
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

    try:
        poetry = utilities.check_preconditions(venv, action)
    except exceptions.SkipEnvironment as err:
        reporter.verbosity1(str(err))
        return None

    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} Loaded project pyproject.toml from {poetry.file}"
    )

    if venv.envconfig.require_locked_deps and venv.envconfig.deps:
        raise exceptions.LockedDepsRequiredError(
            f"Unlocked dependencies '{venv.envconfig.deps}' specified for environment '{venv.name}' which requires locked dependencies"
        )

    package_map: PackageMap = {
        package.name: package
        for package in poetry.locker.locked_repository(True).packages
    }

    if venv.envconfig.install_dev_deps:
        dev_deps: List[PoetryPackage] = [
            dep
            for dep in package_map.values()
            if dep not in poetry.locker.locked_repository(False).packages
        ]
    else:
        dev_deps = []

    reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} Identified {len(dev_deps)} development dependencies to install to env"
    )

    try:
        env_deps: List[PoetryPackage] = []
        for dep in venv.envconfig.locked_deps:
            env_deps += utilities.find_transients(package_map, dep.lower())
        reporter.verbosity1(
            f"{constants.REPORTER_PREFIX} Identified {len(env_deps)} environment dependencies to install to env"
        )

        if not venv.envconfig.skip_install and not venv.envconfig.config.skipsdist:
            project_deps: List[PoetryPackage] = _find_project_dependencies(
                venv, poetry, package_map
            )
        else:
            project_deps = []
            reporter.verbosity1(
                f"{constants.REPORTER_PREFIX} Skipping installation of project dependencies, env does not install project package"
            )
        reporter.verbosity1(
            f"{constants.REPORTER_PREFIX} Identified {len(project_deps)} project dependencies to install to env"
        )
    except exceptions.ToxPoetryInstallerException as err:
        venv.status = "lockfile installation failed"
        reporter.error(f"{constants.REPORTER_PREFIX} {err}")
        raise err

    dependencies = list(set(dev_deps + env_deps + project_deps))
    reporter.verbosity0(
        f"{constants.REPORTER_PREFIX} Installing {len(dependencies)} dependencies to env '{action.name}'"
    )
    utilities.install_to_venv(poetry, venv, dependencies)

    return venv.envconfig.require_locked_deps or None


def _find_project_dependencies(
    venv: ToxVirtualEnv, poetry: Poetry, packages: PackageMap
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
        dependencies += utilities.find_transients(packages, dep.name.lower())

    return dependencies
