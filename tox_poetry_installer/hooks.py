"""Main hook definition module

All implementations of tox hooks are defined here, as well as any single-use helper functions
specifically related to implementing the hooks (to keep the size/readability of the hook functions
themselves manageable).
"""
from typing import Optional

import tox
from tox.action import Action as ToxAction
from tox.config import Parser as ToxParser
from tox.venv import VirtualEnv as ToxVirtualEnv

from tox_poetry_installer import __about__
from tox_poetry_installer import constants
from tox_poetry_installer import exceptions
from tox_poetry_installer import installer
from tox_poetry_installer import utilities
from tox_poetry_installer.datatypes import PackageMap


@tox.hookimpl
def tox_addoption(parser: ToxParser):
    """Add required configuration options to the tox INI file

    Adds the ``require_locked_deps`` configuration option to the venv to check whether all
    dependencies should be treated as locked or not.
    """

    parser.add_argument(
        "--require-poetry",
        action="store_true",
        dest="require_poetry",
        help="Trigger a failure if Poetry is not available to Tox",
    )

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


@tox.hookimpl
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
        if (
            isinstance(err, exceptions.PoetryNotInstalledError)
            and venv.envconfig.config.option.require_poetry
        ):
            venv.status = err.__class__.__name__
            tox.reporter.error(str(err))
            return False
        tox.reporter.verbosity1(str(err))
        return None

    tox.reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} Loaded project pyproject.toml from {poetry.file}"
    )

    if not poetry.locker.is_fresh():
        tox.reporter.warning(
            f"The Poetry lock file is not up to date with the latest changes in {poetry.file}"
        )

    try:
        if venv.envconfig.require_locked_deps and venv.envconfig.deps:
            raise exceptions.LockedDepsRequiredError(
                f"Unlocked dependencies '{venv.envconfig.deps}' specified for environment '{venv.name}' which requires locked dependencies"
            )

        packages: PackageMap = {
            package.name: package
            for package in poetry.locker.locked_repository(True).packages
        }

        if venv.envconfig.install_dev_deps:
            dev_deps = utilities.find_dev_deps(packages, poetry)
            tox.reporter.verbosity1(
                f"{constants.REPORTER_PREFIX} Identified {len(dev_deps)} development dependencies to install to env"
            )
        else:
            dev_deps = []
            tox.reporter.verbosity1(
                f"{constants.REPORTER_PREFIX} Env does not install development dependencies, skipping"
            )

        env_deps = utilities.find_additional_deps(
            packages, poetry, venv.envconfig.locked_deps
        )

        tox.reporter.verbosity1(
            f"{constants.REPORTER_PREFIX} Identified {len(env_deps)} environment dependencies to install to env"
        )

        if not venv.envconfig.skip_install and not venv.envconfig.config.skipsdist:
            project_deps = utilities.find_project_deps(
                packages, poetry, venv.envconfig.extras
            )
            tox.reporter.verbosity1(
                f"{constants.REPORTER_PREFIX} Identified {len(project_deps)} project dependencies to install to env"
            )
        else:
            project_deps = []
            tox.reporter.verbosity1(
                f"{constants.REPORTER_PREFIX} Env does not install project package, skipping"
            )
    except exceptions.ToxPoetryInstallerException as err:
        venv.status = err.__class__.__name__
        tox.reporter.error(f"{constants.REPORTER_PREFIX} {err}")
        return False
    except Exception as err:
        venv.status = "InternalError"
        tox.reporter.error(f"{constants.REPORTER_PREFIX} Internal plugin error: {err}")
        raise err

    dependencies = dev_deps + env_deps + project_deps
    action.setactivity(
        __about__.__title__,
        f"Installing {len(dependencies)} dependencies from Poetry lock file",
    )
    installer.install(poetry, venv, dependencies)

    return venv.envconfig.require_locked_deps or None
