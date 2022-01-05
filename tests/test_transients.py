# pylint: disable=missing-module-docstring, redefined-outer-name, unused-argument, wrong-import-order, unused-import
import poetry.factory
import poetry.utils.env
import pytest
from poetry.puzzle.provider import Provider

from .fixtures import mock_poetry_factory
from .fixtures import mock_venv
from tox_poetry_installer import constants
from tox_poetry_installer import datatypes
from tox_poetry_installer import exceptions
from tox_poetry_installer import utilities


def test_exclude_unsafe():
    """Test that the unsafe packages are properly excluded

    Also ensure that the internal constant matches the value from Poetry
    """
    assert Provider.UNSAFE_PACKAGES == constants.UNSAFE_PACKAGES

    for dep in constants.UNSAFE_PACKAGES:
        assert not utilities.identify_transients(dep, {}, None)


def test_allow_missing():
    """Test that the ``allow_missing`` parameter works as expected"""
    with pytest.raises(exceptions.LockedDepNotFoundError):
        utilities.identify_transients("luke-skywalker", {}, None)

    assert not utilities.identify_transients(
        "darth-vader", {}, None, allow_missing=["darth-vader"]
    )


def test_exclude_pep508():
    """Test that dependencies specified in PEP508 format are properly excluded"""
    for version in [
        "foo==1.0",
        "foo==1",
        "foo>2.0.0",
        "foo<=9.3.4.7.8",
        "foo>999,<=4.6",
        "foo>1234 || foo<2021.01.01",
        "foo!=7",
        "foo~=0.8",
        "foo!=9,==7",
        "=>foo",
    ]:
        with pytest.raises(exceptions.LockedDepVersionConflictError):
            utilities.identify_transients(version, {}, None)


def test_functional(mock_poetry_factory, mock_venv):
    """Integration tests for the :func:`identify_transients` function

    Trivially test that it resolves dependencies properly and that the parent package
    is always the last in the returned list.
    """
    pypoetry = poetry.factory.Factory().create_poetry(None)
    packages: datatypes.PackageMap = {
        item.name: item for item in pypoetry.locker.locked_repository(False).packages
    }
    venv = poetry.utils.env.VirtualEnv()  # pylint: disable=no-value-for-parameter

    requests_requires = [
        packages["certifi"],
        packages["chardet"],
        packages["idna"],
        packages["urllib3"],
        packages["requests"],
    ]

    transients = utilities.identify_transients("requests", packages, venv)

    assert all((item in requests_requires) for item in transients)
    assert all((item in transients) for item in requests_requires)

    for package in [packages["requests"], packages["tox"], packages["flask"]]:
        transients = utilities.identify_transients(package, packages, venv)
        assert transients[-1] == package
        assert len(transients) == len(set(transients))
