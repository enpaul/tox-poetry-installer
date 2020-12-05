"""You've heard of vendoirization, now get ready for internal namespace shadowing

Poetry is an optional dependency of this package explicitly to support the use case of having the
plugin and the `poetry` package installed to the same python environment; this is most common in
containers and/or CI. In this case there are two potential problems that can arise in this case:

* The installation of the plugin overwrites the installed version of Poetry resulting in
  compatibility issues.
* Running `poetry install --no-dev`, when this plugin is in the dev-deps, results in poetry being
  uninstalled from the environment.

To support these edge cases, and more broadly to support not messing with a system package manager,
the `poetry` package dependency is listed as optional dependency. This allows the plugin to be
installed to the same environment as Poetry and import that same Poetry installation here.

However, simply importing Poetry on the assumption that it is installed breaks another valid use
case: having this plugin installed alongside Tox when not using a Poetry-based project. To account
for this the imports in this module are isolated and the resultant import error that would result
is converted to an internal error that can be caught by callers. Rather than importing this module
at the module scope it is imported into function scope wherever Poetry components are needed. This
moves import errors from load time to runtime which allows the plugin to be skipped if Poetry isn't
installed and/or a more helpful error be raised within the Tox framework.
"""
# pylint: disable=unused-import
import sys

from tox_poetry_installer import exceptions


try:
    from poetry.factory import Factory
    from poetry.installation.pip_installer import PipInstaller
    from poetry.io.null_io import NullIO
    from poetry.poetry import Poetry
    from poetry.puzzle.provider import Provider
    from poetry.utils.env import VirtualEnv
except ImportError:
    raise exceptions.PoetryNotInstalledError(
        f"No version of Poetry could be imported under the current environment for '{sys.executable}'"
    ) from None
