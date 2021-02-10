"""Funcationality for performing virtualenv installation"""
# Silence this one globally to support the internal function imports for the proxied poetry module.
# See the docstring in 'tox_poetry_installer._poetry' for more context.
# pylint: disable=import-outside-toplevel
import typing
from pathlib import Path
from typing import Sequence
from typing import Set

import tox
from poetry.core.packages import Package as PoetryPackage
from tox.venv import VirtualEnv as ToxVirtualEnv

from tox_poetry_installer import constants

if typing.TYPE_CHECKING:
    from tox_poetry_installer import _poetry


def install(
    poetry: "_poetry.Poetry", venv: ToxVirtualEnv, packages: Sequence[PoetryPackage]
):
    """Install a bunch of packages to a virtualenv

    :param poetry: Poetry object the packages were sourced from
    :param venv: Tox virtual environment to install the packages to
    :param packages: List of packages to install to the virtual environment
    """
    from tox_poetry_installer import _poetry

    tox.reporter.verbosity1(
        f"{constants.REPORTER_PREFIX} Installing {len(packages)} packages to environment at {venv.envconfig.envdir}"
    )

    pip = _poetry.PipInstaller(
        env=_poetry.VirtualEnv(path=Path(venv.envconfig.envdir)),
        io=_poetry.NullIO(),
        pool=poetry.pool,
    )

    installed: Set[PoetryPackage] = set()

    for dependency in packages:
        if dependency not in installed:
            tox.reporter.verbosity2(
                f"{constants.REPORTER_PREFIX} Installing {dependency}"
            )
            pip.install(dependency)
            installed.add(dependency)
        else:
            tox.reporter.verbosity2(
                f"{constants.REPORTER_PREFIX} Already installed {dependency}, skipping"
            )
