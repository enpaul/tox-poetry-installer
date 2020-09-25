"""Ensure that the pyproject and module metadata never drift out of sync

The next best thing to having one source of truth is having a way to ensure all of your
sources of truth agree with each other.
"""
from pathlib import Path

import toml

import tox_poetry_installer


def test_metadata():
    """Test that module metadata matches pyproject poetry metadata"""

    with (Path(__file__).resolve().parent / ".." / "pyproject.toml").open() as infile:
        pyproject = toml.load(infile, _dict=dict)

    assert pyproject["tool"]["poetry"]["name"] == tox_poetry_installer.__title__
    assert pyproject["tool"]["poetry"]["version"] == tox_poetry_installer.__version__
    assert pyproject["tool"]["poetry"]["license"] == tox_poetry_installer.__license__
    assert (
        pyproject["tool"]["poetry"]["description"] == tox_poetry_installer.__summary__
    )
    assert pyproject["tool"]["poetry"]["repository"] == tox_poetry_installer.__url__
    assert (
        all(
            item in tox_poetry_installer.__authors__
            for item in pyproject["tool"]["poetry"]["authors"]
        )
        is True
    )
    assert (
        all(
            item in pyproject["tool"]["poetry"]["authors"]
            for item in tox_poetry_installer.__authors__
        )
        is True
    )
