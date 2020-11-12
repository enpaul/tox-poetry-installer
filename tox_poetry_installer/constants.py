"""Static constants for reference

Rule of thumb: if it's an arbitrary value that will never be changed at runtime, it should go
in this module.

All constants should be type hinted.
"""
from typing import Tuple

from tox_poetry_installer import __about__


# Valid PEP508 version delimiters. These are used to test whether a given string (specifically a
# dependency name) is just a package name or also includes a version identifier.
PEP508_VERSION_DELIMITERS: Tuple[str, ...] = ("~=", "==", "!=", ">", "<")

# Prefix all reporter messages should include to indicate that they came from this module in the
# console output.
REPORTER_PREFIX = f"[{__about__.__title__}]:"
