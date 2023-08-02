"""Logging wrappers to reduce duplication elsewhere

Calling ``tox.reporter.something()`` and having to format a string with the prefix
gets really old fast, but more importantly it also makes the flow of the main code
more difficult to follow because of the added complexity.
"""
import logging

from tox_poetry_installer import constants


def error(message: str):
    """Wrapper around :func:`logging.error` that prefixes the reporter prefix onto the message"""
    logging.error(f"{constants.REPORTER_PREFIX} {message}")


def warning(message: str):
    """Wrapper around :func:`logging.warning`"""
    logging.warning(f"{constants.REPORTER_PREFIX} {message}")


def info(message: str):
    """Wrapper around :func:`logging.info`"""
    logging.info(f"{constants.REPORTER_PREFIX} {message}")


def debug(message: str):
    """Wrapper around :func:`logging.debug`"""
    logging.debug(f"{constants.REPORTER_PREFIX} {message}")
