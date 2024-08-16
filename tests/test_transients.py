# pylint: disable=missing-module-docstring,redefined-outer-name,unused-argument,unused-import,protected-access
import poetry.factory
import poetry.utils.env
import pytest

import tox_poetry_installer.hooks._tox_on_install_helpers
from tox_poetry_installer import exceptions

from .fixtures import mock_poetry_factory
from .fixtures import mock_venv


def test_allow_missing():
    """Test that the ``allow_missing`` parameter works as expected"""
    with pytest.raises(exceptions.LockedDepNotFoundError):
        tox_poetry_installer.hooks._tox_on_install_helpers.identify_transients(
            "luke-skywalker", {}, None
        )

    assert not tox_poetry_installer.hooks._tox_on_install_helpers.identify_transients(
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
            tox_poetry_installer.hooks._tox_on_install_helpers.identify_transients(
                version, {}, None
            )


def test_functional(mock_poetry_factory, mock_venv):
    """Integration tests for the :func:`identify_transients` function

    Trivially test that it resolves dependencies properly and that the parent package
    is always the last in the returned list.
    """
    pypoetry = poetry.factory.Factory().create_poetry(None)
    packages = tox_poetry_installer.hooks._tox_on_install_helpers.build_package_map(
        pypoetry
    )
    venv = poetry.utils.env.VirtualEnv()  # pylint: disable=no-value-for-parameter

    requests_requires = [
        packages["certifi"][0],
        packages["chardet"][0],
        packages["idna"][0],
        packages["urllib3"][0],
        packages["requests"][0],
    ]

    transients = tox_poetry_installer.hooks._tox_on_install_helpers.identify_transients(
        "requests", packages, venv
    )

    assert all((item in requests_requires) for item in transients)
    assert all((item in transients) for item in requests_requires)

    for package in [packages["requests"][0], packages["tox"][0], packages["flask"][0]]:
        transients = (
            tox_poetry_installer.hooks._tox_on_install_helpers.identify_transients(
                package.name, packages, venv
            )
        )
        assert transients[-1] == package
        assert len(transients) == len(set(transients))
