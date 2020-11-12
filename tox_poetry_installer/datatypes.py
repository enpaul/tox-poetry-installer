"""Definitions for typehints/containers used by the plugin"""
from typing import Dict
from typing import List
from typing import NamedTuple

from poetry.core.packages import Package as PoetryPackage
from tox.config import DepConfig as ToxDepConfig


# Map of package names to the package object
PackageMap = Dict[str, PoetryPackage]


class SortedEnvDeps(NamedTuple):
    """Container for the two types of environment dependencies"""

    unlocked_deps: List[ToxDepConfig]
    locked_deps: List[ToxDepConfig]
