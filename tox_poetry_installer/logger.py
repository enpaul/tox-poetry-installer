"""Logging wrappers to reduce duplication elsewhere

Calling ``tox.reporter.something()`` and having to format a string with the prefix
gets really old fast, but more importantly it also makes the flow of the main code
more difficult to follow because of the added complexity.
"""
import tox

from tox_poetry_installer import constants


def error(message: str):
    """Wrapper around :func:`tox.reporter.error`"""
    tox.reporter.error(f"{constants.REPORTER_PREFIX} {message}")


def warning(message: str):
    """Wrapper around :func:`tox.reporter.warning`"""
    tox.reporter.warning(f"{constants.REPORTER_PREFIX} {message}")


def info(message: str):
    """Wrapper around :func:`tox.reporter.verbosity1`"""
    tox.reporter.verbosity1(f"{constants.REPORTER_PREFIX} {message}")


def debug(message: str):
    """Wrapper around :func:`tox.reporter.verbosity2`"""
    tox.reporter.verbosity2(f"{constants.REPORTER_PREFIX} {message}")
