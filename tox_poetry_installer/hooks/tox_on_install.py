"""Install the dependencies for the current environment

Loads the local Poetry environment and the corresponding lockfile then pulls the dependencies
specified by the Tox environment. Finally these dependencies are installed into the Tox
environment using the Poetry ``PipInstaller`` backend.
"""
from itertools import chain

from tox.plugin import impl
from tox.tox_env.api import ToxEnv as ToxVirtualEnv

from tox_poetry_installer import exceptions
from tox_poetry_installer import installer
from tox_poetry_installer import logger
from tox_poetry_installer import utilities


@impl
def tox_on_install(
    tox_env: ToxVirtualEnv, section: str  # pylint: disable=unused-argument
) -> None:
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
