"""Definitions for typehints/containers used by the plugin"""
from typing import Dict

from poetry.core.packages import Package as PoetryPackage


# Map of package names to the package object
PackageMap = Dict[str, PoetryPackage]
