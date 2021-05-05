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
from tox_poetry_installer import logger
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
        help="(deprecated) Trigger a failure if Poetry is not available to Tox",
    )

    parser.add_argument(
        "--parallelize-locked-install",
        type=int,
        dest="parallelize_locked_install",
        default=None,
        help="(deprecated) Number of worker threads to use for installing dependencies from the Poetry lockfile in parallel",
    )

    parser.add_argument(
        "--parallel-install-threads",
        type=int,
        dest="parallel_install_threads",
        default=constants.DEFAULT_INSTALL_THREADS,
        help="Number of locked dependencies to install simultaneously; set to 0 to disable parallel installation",
    )

    parser.add_testenv_attribute(
        name="install_dev_deps",
        type="bool",
        default=False,
        help="Automatically install all Poetry development dependencies to the environment",
    )

    parser.add_testenv_attribute(
        name="install_project_deps",
        type="bool",
        default=True,
        help="Automatically install all Poetry primary dependencies to the environment",
    )

    parser.add_testenv_attribute(
        name="require_locked_deps",
        type="bool",
        default=False,
        help="Require all dependencies in the environment be installed using the Poetry lockfile",
    )

    parser.add_testenv_attribute(
        name="require_poetry",
        type="bool",
        default=False,
        help="Trigger a failure if Poetry is not available to Tox",
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
        if isinstance(err, exceptions.PoetryNotInstalledError) and (
            venv.envconfig.config.option.require_poetry or venv.envconfig.require_poetry
        ):
            venv.status = err.__class__.__name__
            logger.error(str(err))
            return False
        logger.info(str(err))
        return None

    logger.info(f"Loaded project pyproject.toml from {poetry.file}")

    virtualenv = utilities.convert_virtualenv(venv)

    if not poetry.locker.is_fresh():
        logger.warning(
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
            dev_deps = utilities.find_dev_deps(packages, virtualenv, poetry)
            logger.info(
                f"Identified {len(dev_deps)} development dependencies to install to env"
            )
        else:
            dev_deps = []
            logger.info("Env does not install development dependencies, skipping")

        env_deps = utilities.find_additional_deps(
            packages, virtualenv, poetry, venv.envconfig.locked_deps
        )

        logger.info(
            f"Identified {len(env_deps)} environment dependencies to install to env"
        )

        if (
            not venv.envconfig.skip_install
            and not venv.envconfig.config.skipsdist
            and venv.envconfig.install_project_deps
        ):
            project_deps = utilities.find_project_deps(
                packages, virtualenv, poetry, venv.envconfig.extras
            )
            logger.info(
                f"Identified {len(project_deps)} project dependencies to install to env"
            )
        else:
            project_deps = []
            logger.info("Env does not install project package dependencies, skipping")
    except exceptions.ToxPoetryInstallerException as err:
        venv.status = err.__class__.__name__
        logger.error(str(err))
        return False
    except Exception as err:
        venv.status = "InternalError"
        logger.error(f"Internal plugin error: {err}")
        raise err

    dependencies = dev_deps + env_deps + project_deps
    if (
        venv.envconfig.config.option.parallel_install_threads
        != constants.DEFAULT_INSTALL_THREADS
    ):
        parallel_threads = venv.envconfig.config.option.parallel_install_threads
    else:
        parallel_threads = (
            venv.envconfig.config.option.parallelize_locked_install
            if venv.envconfig.config.option.parallelize_locked_install is not None
            else constants.DEFAULT_INSTALL_THREADS
        )
    log_parallel = f" (using {parallel_threads} threads)" if parallel_threads else ""

    action.setactivity(
        __about__.__title__,
        f"Installing {len(dependencies)} dependencies from Poetry lock file{log_parallel}",
    )
    installer.install(
        poetry,
        venv,
        dependencies,
        parallel_threads,
    )

    return venv.envconfig.require_locked_deps or None
