"""Static constants for reference

Rule of thumb: if it's an arbitrary value that will never be changed at runtime, it should go
in this module.

All constants should be type hinted.
"""
from typing import Set
from typing import Tuple

from tox_poetry_installer import __about__


# Valid PEP508 version delimiters. These are used to test whether a given string (specifically a
# dependency name) is just a package name or also includes a version identifier.
PEP508_VERSION_DELIMITERS: Tuple[str, ...] = ("~=", "==", "!=", ">", "<")

# Prefix all reporter messages should include to indicate that they came from this module in the
# console output.
REPORTER_PREFIX: str = f"{__about__.__title__}:"

# Internal list of packages that poetry has deemed unsafe and are excluded from the lockfile
UNSAFE_PACKAGES: Set[str] = {"distribute", "pip", "setuptools", "wheel"}

# Number of threads to use for installing dependencies by default
DEFAULT_INSTALL_THREADS: int = 10
