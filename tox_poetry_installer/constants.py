"""Static constants for reference

Rule of thumb: if it's an arbitrary value that will never be changed at runtime, it should go
in this module.

All constants should be type hinted.
"""
import sys
from typing import Tuple

from poetry.core.semver.version import Version

from tox_poetry_installer import __about__


# Valid PEP508 version delimiters. These are used to test whether a given string (specifically a
# dependency name) is just a package name or also includes a version identifier.
PEP508_VERSION_DELIMITERS: Tuple[str, ...] = ("~=", "==", "!=", ">", "<")

# Prefix all reporter messages should include to indicate that they came from this module in the
# console output.
REPORTER_PREFIX: str = f"[{__about__.__title__}]:"


# Semver compatible version of the current python platform version. Used for checking
# whether a package is compatible with the current python system version
PLATFORM_VERSION: Version = Version(
    major=sys.version_info.major,
    minor=sys.version_info.minor,
    patch=sys.version_info.micro,
)
