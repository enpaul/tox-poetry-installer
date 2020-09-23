from pathlib import Path
import logging
from typing import Dict, List

from poetry.factory import Factory
from poetry.factory import Poetry
from poetry.packages import Package
from poetry.installation.pip_installer import PipInstaller
from poetry.io.null_io import NullIO
from poetry.utils.env import VirtualEnv

from tox.action import Action as ToxAction
from tox.venv import VirtualEnv as ToxVirtualEnv
from tox import hookimpl


__title__ = "tox-poetry-installer"
__summary__ = "Tox plugin to install Tox environment dependencies using the Poetry backend and lockfile"
__version__ = "0.1.0"
__url__ = "https://github.com/enpaul/tox-poetry-installer/"
__license__ = "MIT"
__authors__ = ["Ethan Paul <e@enp.one>"]


def _make_poetry(venv: ToxVirtualEnv) -> Poetry:
    return Factory().create_poetry(venv.envconfig.config.toxinidir)


def _find_locked_dependencies(poetry: Poetry, dependency_name: str) -> List[Package]:
    packages: Dict[str, Package] = {
        package.name: package
        for package in poetry.locker.locked_repository(True).packages
    }

    try:
        top_level = packages[dependency_name]
    except KeyError:
        raise

    def find_transients(name: str) -> List[Package]:
        transients = [packages[name]]
        for dep in packages[name].requires:
            transients += find_transients(dep.name)
        return transients

    return find_transients(top_level.name)


@hookimpl
def tox_testenv_install_deps(venv: ToxVirtualEnv, action: ToxAction):

    logger = logging.getLogger(__name__)

    if action.name == venv.envconfig.config.isolated_build_env:
        logger.debug(f"Environment {action.name} is isolated build environment; skipping Poetry-based dependency installation")
        return None

    poetry = _make_poetry(venv)

    logger.debug(f"Loaded project pyproject.toml from {poetry.file}")

    dependencies = []
    for env_dependency in venv.envconfig.deps:
        dependencies += _find_locked_dependencies(poetry, env_dependency.name)

    logger.debug(f"Identified {len(dependencies)} dependencies for environment {action.name}")

    installer = PipInstaller(
        env=VirtualEnv(path=Path(venv.envconfig.envdir)),
        io=NullIO(),
        pool=poetry.pool
    )

    for dependency in dependencies:
        logger.info(f"Installing environment dependency: {dependency}")
        installer.install(dependency)

    return dependencies
