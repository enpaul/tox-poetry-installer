"""Main hook definition module

All implementations of tox hooks are defined here, as well as any single-use helper functions
specifically related to implementing the hooks (to keep the size/readability of the hook functions
themselves manageable).
"""
from itertools import chain
from typing import List

from tox.config.cli.parser import ToxParser
from tox.config.sets import EnvConfigSet
from tox.plugin import impl
from tox.tox_env.api import ToxEnv as ToxVirtualEnv

from tox_poetry_installer import constants
from tox_poetry_installer import exceptions
from tox_poetry_installer import installer
from tox_poetry_installer import logger
from tox_poetry_installer import utilities


@impl
def tox_add_option(parser: ToxParser):
    """Add additional command line arguments to tox to configure plugin behavior"""
    parser.add_argument(
        "--require-poetry",
        action="store_true",
        dest="require_poetry",
        help="(deprecated) Trigger a failure if Poetry is not available to Tox",
    )

    parser.add_argument(
        "--parallel-install-threads",
        type=int,
        dest="parallel_install_threads",
        default=constants.DEFAULT_INSTALL_THREADS,
        help="Number of locked dependencies to install simultaneously; set to 0 to disable parallel installation",
    )


@impl
def tox_add_env_config(env_conf: EnvConfigSet):
    """Add required env configuration options to the tox INI file"""
    env_conf.add_config(
        "poetry_dep_groups",
        of_type=List[str],
        default=[],
        desc="List of Poetry dependency groups to install to the environment",
    )

    env_conf.add_config(
        "install_project_deps",
        of_type=bool,
        default=True,
        desc="Automatically install all Poetry primary dependencies to the environment",
    )

    env_conf.add_config(
        "require_locked_deps",
        of_type=bool,
        default=False,
        desc="Require all dependencies in the environment be installed using the Poetry lockfile",
    )

    env_conf.add_config(
        "require_poetry",
        of_type=bool,
        default=False,
        desc="Trigger a failure if Poetry is not available to Tox",
    )

    env_conf.add_config(
        "locked_deps",
        of_type=List[str],
        default=[],
        desc="List of locked dependencies to install to the environment using the Poetry lockfile",
    )


@impl
def tox_on_install(
    tox_env: ToxVirtualEnv, section: str  # pylint: disable=unused-argument
) -> None:
    """Install the dependencies for the current environment

    Loads the local Poetry environment and the corresponding lockfile then pulls the dependencies
    specified by the Tox environment. Finally these dependencies are installed into the Tox
    environment using the Poetry ``PipInstaller`` backend.

    :param venv: Tox virtual environment object with configuration for the local Tox environment.
    :param action: Tox action object
    """
    try:
        poetry = utilities.check_preconditions(tox_env)
    except exceptions.SkipEnvironment as err:
        if (
            isinstance(err, exceptions.PoetryNotInstalledError)
            and tox_env.conf["require_poetry"]
        ):
            logger.error(str(err))
            raise err
        logger.info(str(err))
        return

    logger.info(f"Loaded project pyproject.toml from {poetry.file}")

    virtualenv = utilities.convert_virtualenv(tox_env)

    if not poetry.locker.is_fresh():
        logger.warning(
            f"The Poetry lock file is not up to date with the latest changes in {poetry.file}"
        )

    try:
        if tox_env.conf["require_locked_deps"] and tox_env.conf["deps"].lines():
            raise exceptions.LockedDepsRequiredError(
                f"Unlocked dependencies '{tox_env.conf['deps']}' specified for environment '{tox_env.name}' which requires locked dependencies"
            )

        packages = utilities.build_package_map(poetry)

        group_deps = utilities.dedupe_packages(
            list(
                chain(
                    *[
                        utilities.find_group_deps(group, packages, virtualenv, poetry)
                        for group in tox_env.conf["poetry_dep_groups"]
                    ]
                )
            )
        )
        logger.info(
            f"Identified {len(group_deps)} group dependencies to install to env"
        )

        env_deps = utilities.find_additional_deps(
            packages, virtualenv, poetry, tox_env.conf["locked_deps"]
        )

        logger.info(
            f"Identified {len(env_deps)} environment dependencies to install to env"
        )

        # extras are not set in a testenv if skip_install=true
        try:
            extras = tox_env.conf["extras"]
        except KeyError:
            extras = []

        if tox_env.conf["install_project_deps"]:
            project_deps = utilities.find_project_deps(
                packages, virtualenv, poetry, extras
            )
            logger.info(
                f"Identified {len(project_deps)} project dependencies to install to env"
            )
        else:
            project_deps = []
            logger.info("Env does not install project package dependencies, skipping")
    except exceptions.ToxPoetryInstallerException as err:
        logger.error(str(err))
        raise err
    except Exception as err:
        logger.error(f"Internal plugin error: {err}")
        raise err

    dependencies = utilities.dedupe_packages(group_deps + env_deps + project_deps)

    logger.info(f"Installing {len(dependencies)} dependencies from Poetry lock file")
    installer.install(
        poetry,
        tox_env,
        dependencies,
        tox_env.options.parallel_install_threads,
    )
