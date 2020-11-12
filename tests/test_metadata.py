"""Ensure that the pyproject and module metadata never drift out of sync

The next best thing to having one source of truth is having a way to ensure all of your
sources of truth agree with each other.
"""
from pathlib import Path

import toml

from tox_poetry_installer import __about__


def test_metadata():
    """Test that module metadata matches pyproject poetry metadata"""

    with (Path(__file__).resolve().parent / ".." / "pyproject.toml").open() as infile:
        pyproject = toml.load(infile, _dict=dict)

    assert pyproject["tool"]["poetry"]["name"] == __about__.__title__
    assert pyproject["tool"]["poetry"]["version"] == __about__.__version__
    assert pyproject["tool"]["poetry"]["license"] == __about__.__license__
    assert pyproject["tool"]["poetry"]["description"] == __about__.__summary__
    assert pyproject["tool"]["poetry"]["repository"] == __about__.__url__
    assert (
        all(
            item in __about__.__authors__
            for item in pyproject["tool"]["poetry"]["authors"]
        )
        is True
    )
    assert (
        all(
            item in pyproject["tool"]["poetry"]["authors"]
            for item in __about__.__authors__
        )
        is True
    )
