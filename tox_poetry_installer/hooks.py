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


def _postprocess_install_project_deps(
    testenv_config, value: Optional[str]  # pylint: disable=unused-argument
) -> Optional[bool]:
    """An awful hack to patch on three-state boolean logic to a config parameter

    .. warning: This logic should 100% be removed in the next feature release. It's here to work
                around a bad design for now but should not persist.

    The bug filed in `#61`_ is caused by a combination of poor design and attempted cleverness. The
    name of the ``install_project_deps`` config option implies that it has ultimate control over
    whether the project dependencies are installed to the testenv, but this is not actually correct.
    What it actually allows the user to do is force the project dependencies to not be installed to
    an environment that would otherwise install them. This was intended behavior, however the
    intention was wrong.

    .. _`#61`: https://github.com/enpaul/tox-poetry-installer/issues/61

    In an effort to be clever the plugin automatically skips installing project dependencies when
    the project package is not installed to the testenv (``skip_install = true``) or if packaging
    as a whole is disabled (``skipsdist = true``). The intention of this behavior is to install only
    the expected dependencies to a testenv and no more. However, this conflicts with the
    ``install_project_deps`` config option, which cannot override this behavior because it defaults
    to ``True``. In effect, ``install_project_deps = true`` in fact means "automatically
    determine whether to install project dependencies" and ``install_project_deps = false`` means
    "never install the project dependencies". This is not ideal and unintuitive.

    To avoid having to make a breaking change this workaround has been added to support three-state
    logic between ``True``, ``False``, and ``None``. The ``install_project_deps`` option is now
    parsed by Tox as a string with a default value of ``None``. If the value is not ``None`` then
    this post processing function will try to convert it to a boolean the same way that Tox's
    `SectionReader.getbool()`_ method does, raising an error to mimic the default behavior if it
    can't.

    .. _`SectionReader.getbool()`: https://github.com/tox-dev/tox/blob/f8459218ee5ab5753321b3eb989b7beee5b391ad/src/tox/config/__init__.py#L1724

    The three states for the ``install_project_deps`` setting are:
    * ``None`` - User did not configure the setting, package dependency installation is
      determined automatically
    * ``True`` - User configured the setting to ``True``, package dependencies will be installed
    * ``False`` - User configured the setting to ``False``, package dependencies will not be
      installed

    This config option should be deprecated with the 1.0.0 release and instead an option like
    ``always_install_project_deps`` should be added which overrides the default determination and
    just installs the project dependencies. The counterpart (``never_install_project_deps``)
    shouldn't be needed, since I don't think there's a real use case for that.
    """
    if value is None:
        return value

    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False

    raise tox.exception.ConfigError(
        f"install_project_deps: boolean value '{value}' needs to be 'True' or 'False'"
    )


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
        type="string",
        default=None,
        help="Automatically install all Poetry primary dependencies to the environment",
        postprocess=_postprocess_install_project_deps,
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

        install_project_deps = (
            venv.envconfig.install_project_deps
            if venv.envconfig.install_project_deps is not None
            else (
                not venv.envconfig.skip_install and not venv.envconfig.config.skipsdist
            )
        )

        if install_project_deps:
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
