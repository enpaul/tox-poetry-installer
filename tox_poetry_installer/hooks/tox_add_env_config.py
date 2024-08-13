"""Add required env configuration options to the tox INI file"""
from typing import List

from tox.config.sets import EnvConfigSet
from tox.plugin import impl


@impl
def tox_add_env_config(env_conf: EnvConfigSet):
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
