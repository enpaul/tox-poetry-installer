# tox-poetry-installer

A plugin for [Tox](https://tox.readthedocs.io/en/latest/) that allows test environment
dependencies to be installed using [Poetry](https://python-poetry.org/) from its lockfile.

⚠️ **This project is beta software and is under active development** ⚠️

[![ci-status](https://github.com/enpaul/tox-poetry-installer/workflows/CI/badge.svg?event=push)](https://github.com/enpaul/tox-poetry-installer/actions)
[![pypi-version](https://img.shields.io/pypi/v/tox-poetry-installer)](https://pypi.org/project/tox-poetry-installer/)
[![pypi-downloads](https://img.shields.io/pypi/dm/tox-poetry-installer)](https://libraries.io/pypi/tox-poetry-installer)
[![license](https://img.shields.io/pypi/l/tox-poetry-installer)](https://opensource.org/licenses/MIT)
[![python-versions](https://img.shields.io/pypi/pyversions/tox-poetry-installer)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Documentation**

* [Introduction](#introduction)
  * [Install](#install)
  * [Quick Start](#quick-start)
  * [Why would I use this?](#why-would-i-use-this) (What problems does this solve?)
* [Reference](#reference)
  * [Configuration Options](#configuration-options)
  * [Command-line Arguments](#command-line-arguments)
  * [Errors](#errors)
  * [Advanced Usage](#advanced-usage)
* [Developing](#developing)
* [Contributing](#contributing)
* [Roadmap](#roadmap)
  * [Path to Beta](#path-to-beta)
  * [Path to Stable](#path-to-stable)

Related resources:
* [Poetry Python Project Manager](https://python-poetry.org/)
* [Tox Automation Project](https://tox.readthedocs.io/en/latest/)
* [Other Tox plugins](https://tox.readthedocs.io/en/latest/plugins.html)

Similar projects:
* [Poetry Dev-Dependencies Tox Plugin](https://github.com/sinoroc/tox-poetry-dev-dependencies)
* [Poetry Tox Plugin](https://github.com/tkukushkin/tox-poetry)


## Introduction

This is a plugin to unify two great projects in the Python ecosystem: the
[Tox](https://tox.readthedocs.io/en/latest/) automation project and the
[Poetry](https://python-poetry.org) project/dependency manager. Specifically it allows
the repeatable dependency resolution and installation tools that Poetry uses to benefit
the isolated environments that Tox uses to run automated tests. The motivation to write
this plugin came from a need for a single source of truth for the versions of all
packages that should be installed to an environment.

When in use this plugin will allow a Tox environment to install its required
dependencies using the versions specified in the Poetry lockfile. This eliminates
needing to specify package versions in multiple places as well as ensures that the Tox
environment has the exact same versions of a given package as the Poetry environment.
This reduces (or hopefully eliminates) hard to debug problems caused by subtle
differences in the dependency graph of the active development environment (the one managed
by Poetry) and the automated test environment(s) created by Tox.

To learn more about the problems this plugin aims to solve jump ahead to
[What problems does this solve?](#why-would-i-use-this).
Otherwise keep reading to get started.

### Install

The recommended way to install the plugin is to add it to a project's `pyproject.toml`
and lockfile using Poetry:

```bash
poetry add tox-poetry-installer[poetry] --dev
```

**WARNING:** The below installation methods are vulnerable to the
[transient dependency issues this plugin aims to avoid](#why-would-i-use-this). It is
always recommended to install dependencies using Poetry whenever possible.

The plugin can also be installed with pip directly, though it is recommended to always
install to a virtual environment and pin to a specific version:

```bash
source my-venv/bi/activate
pip install tox-poetry-installer[poetry] == 0.6.0
```

The plugin can also be installed using the Tox
[`requires`]((https://tox.readthedocs.io/en/latest/config.html#conf-requires))
configuration option. Note however that dependencies installed via the `requires` option
are not handled by the plugin and will be installed the same way as a `pip install ...`
above. For this reason it is also recommended to always pin to a specific version when
using this installation method:

```ini
# tox.ini
[tox]
requires
    tox-poetry-installer[poetry] == 0.6.0
```

Check that the plugin is registered by checking the Tox version:

```
~ $: poetry run tox --version
3.20.0 imported from .venv/lib64/python3.8/site-packages/tox/__init__.py
registered plugins:
    tox-poetry-installer-0.6.0 at .venv/lib64/python3.8/site-packages/tox_poetry_installer.py
```

**NOTE:** Installing the `tox-poetry-installer[poetry]` extra will add the `poetry`
package as a managed environment dependency which can cause problems when the Poetry
installation is externally managed (such as in a CI or container environment). See
[Advanced Usage](#installing-alongside-an-existing-poetry-installation) for more
information on this use case.

### Quick Start

Before making any changes to `tox.ini` the project is already benefiting from having
the plugin installed: all dependencies of the root project package are installed using
the Poetry backend to all Tox environments that install the root package without any
configuration changes.

To add dependencies from the lockfile to a Tox environment, add the option
[`locked_deps`](#locked_deps) to the environment configuration and list names of
dependencies (with no version specifier) under it:

```ini
[testenv]
description = Some very cool tests
locked_deps =
    black
    pylint
    mypy
commands = ...
```

The standard [`deps`](https://tox.readthedocs.io/en/latest/config.html#conf-deps) option
can be used in parallel with the `locked_deps` option to install unlocked dependencies
(dependencies not in the lockfile) alongside locked dependencies:

```ini
[testenv]
description = Some very cool tests
locked_deps =
    black
    pylint
    mypy
deps =
    pytest == 6.1.1
    pytest-cov >= 2.10, <2.11
commands = ...
```

Alternatively, to quickly install all Poetry dev-dependencies to a Tox environment, add the
[`install_dev_deps`](#install_dev_deps) option to the environment configuration:

```ini
[testenv]
description = Some very cool tests
install_dev_deps = true
```

See the [Reference](#reference) section for more details on available
configuration options and the [Advanced Usage](#advanced-usage) section for some
unusual use cases.

### Why would I use this?

**The Problem**

By default Tox uses Pip to install the [PEP-508](https://www.python.org/dev/peps/pep-0508/)
compliant dependencies to a test environment. This plugin extends the default Tox
dependency installation behavior to support installing dependencies using a Poetry-based
installation method that makes use of the dependency metadata from Poetry's lockfile.

Environment dependencies for a Tox environment are usually specified in PEP-508 format, like
the below example:

```ini
[testenv]
description = Some very cool tests
deps =
    foo == 1.2.3
    bar >=1.3,<2.0
    baz
```

Let's assume these dependencies are also useful during development, so they can be added to the
Poetry environment using this command:

 ```
 poetry add --dev \
    foo==1.2.3 \
    bar>=1.3,<2.0 \
    baz
 ```

 However there is a potential problem that could arise from each of these environment
 dependencies that would _only_ appear in the Tox environment and not in the Poetry
 environment in use by a developer:

 * **The `foo` dependency is pinned to a specific version:** let's imagine a security
   vulnerability is discovered in `foo` and the maintainers release version `1.2.4` to fix
   it. A developer can run `poetry remove foo` and then `poetry add foo^1.2` to get the new
   version, but the Tox environment is left unchanged. The development environment, as defined by
   the lockfile, is now patched against the vulnerability but the Tox environment is not.

* **The `bar` dependency specifies a dynamic range:** a dynamic range allows a range of
  versions to be installed, but the lockfile will have an exact version specified so that
  the Poetry environment is reproducible; this allows versions to be updated with
  `poetry update` rather than with the `remove` and `add` commands used above. If the
  maintainers of `bar` release version `1.6.0` then the Tox environment will install it
  because it is valid for the specified version range. Meanwhile the Poetry environment will
  continue to install the version from the lockfile until `poetry update bar` explicitly
  updates it. The development environment is now has a different version of `bar` than the Tox
  environment.

* **The `baz` dependency is unpinned:** unpinned dependencies are
  [generally a bad idea](https://python-poetry.org/docs/faq/#why-are-unbound-version-constraints-a-bad-idea),
  but here it can cause real problems. Poetry will interpret an unbound dependency using
  [the carrot requirement](https://python-poetry.org/docs/dependency-specification/#caret-requirements)
  but Pip (via Tox) will interpret it as a wildcard. If the latest version of `baz` is `1.0.0`
  then `poetry add baz` will result in a constraint of `baz>=1.0.0,<2.0.0` while the Tox
  environment will have a constraint of `baz==*`. The Tox environment can now install an
  incompatible version of `baz` and any errors that causes cannot be replicated using `poetry update`.

All of these problems can apply not only to the dependencies specified for a Tox environment,
but also to the dependencies of those dependencies, those dependencies' dependencies, and so on.

**The Solution**

This plugin allows dependencies specified in Tox environment take their version directly from
the Poetry lockfile without needing an independent version to be specified in the Tox
environment configuration. The modified version of the example environment given below appears
less stable than the one presented above because it does not specify any versions for its
dependencies:

```ini
[testenv]
description = Some very cool tests
require_locked_deps = true
locked_deps =
    foo
    bar
    baz
```

However with the `tox-poetry-installer` plugin installed Tox will install these
dependencies from the Poetry lockfile so that the version installed to the Tox
environment exactly matches the version Poetry is managing. When `poetry update` updates
the lockfile with new versions of these dependencies, Tox will automatically install
these new versions without needing any changes to the configuration.


## Reference

### Configuration Options

All options listed below are Tox environment options and can be applied to one or more
environment sections of the `tox.ini` file. They cannot be applied to the global Tox
configuration section.

**NOTE:** Environment settings applied to the main `testenv` environment will be
inherited by child environments (i.e. `testenv:foo`) unless they are explicitly
overridden by the child environment's configuration.

#### `locked_deps`

* **Type:** multi-line list
* **Default:** `[]`

Names of packages in the Poetry lockfile to install to the Tox environment. All
dependencies specified here will be installed to the Tox environment using the details
given by the Poetry lockfile.

#### `require_locked_deps`


* **Type:** boolean
* **Default:** `false`

Whether the environment should allow unlocked dependencies (dependencies not in the
Poetry lockfile) to be installed alongside locked dependencies. If `true` then an error
will be raised if the environment specifies unlocked dependencies to install and the
plugin will block any other plugins from using the
[`tox_testenv_install_deps`](https://tox.readthedocs.io/en/latest/plugins.html#tox.hookspecs.tox_testenv_install_deps)
hook.

#### `install_dev_deps`

* **Type:** boolean
* **Default:** `false`

Whether all Poetry dev-dependencies should be installed to the environment. If `true`
then all dependencies specified in the
[`dev-dependencies`](https://python-poetry.org/docs/pyproject/#dependencies-and-dev-dependencies)
section of `pyproject.toml` will be installed automatically.

### Command-line Arguments

All arguments listed below can be passed to the `tox` command to modify runtime behavior
of the plugin.

#### `--require-poetry`

Indicates that Poetry is expected to be available to Tox and, if it is not, then the Tox
run should fail. If provided and the `poetry` package is not installed to the same
environment as the `tox` package then Tox will fail.

**NOTE:** See [Advanced Usage](#installing-alongside-an-existing-poetry-installation)
for more information.

### Errors

If the plugin encounters an error while processing a Tox environment then it will mark
the environment as failed and set the environment status to one of the values below:

**NOTE:** In addition to the reasons noted below, the plugin can encounter errors if the
Poetry lockfile is not up-to-date with `pyproject.toml`. To resynchronize the
lockfile with the `pyproject.toml` run one of
[`poetry update`](https://python-poetry.org/docs/cli/#update) or
[`poetry lock`](https://python-poetry.org/docs/cli/#lock)

#### Poetry Not Installed Error

* **Status value:** `PoetryNotInstalledError`
* **Cause:** Indicates that the `poetry` module could not be imported from the same
  environment as the running `tox` module and the runtime flags specified
  [`--require-poetry`](#--require-poetry).
* **Resolution options:**
  * Install Poetry: ensure that `poetry` is installed to the same environment as `tox`.
  * Skip running the plugin: remove the `--require-poetry` flag from the runtime options.

**NOTE:** See [Advanced Usage](#installing-alongside-an-existing-poetry-installation)
for more information.

#### Locked Dependency Version Conflict Error

* **Status value:** `LockedDepVersionConflictError`
* **Cause:** Indicates that a dependency specified in the [`locked_deps`](#locked_deps)
  configuration option in `tox.ini` includes a
  [PEP-508 version specifier](https://www.python.org/dev/peps/pep-0508/#grammar)
  (i.e. `pytest >=6.0, <6.1`).
* **Resolution options:**
  * Use the dependency version from the lockfile: remove any/all version specifiers
    from the item in the `locked_deps` list in `tox.ini`.
  * Do not install the dependency: remove the item from the `locked_deps` list in
    `tox.ini`.

#### Locked Dependency Not Found Error

* **Status value:** `LockedDepNotFoundError`
* **Cause:** Indicates that a dependency specified in the [`locked_deps`](#locked_deps)
  configuration option in `tox.ini` could not be found in the Poetry lockfile.
* **Resolution options:**
  * Add the dependency to the lockfile: run
    [`poetry add <dependency>`](https://python-poetry.org/docs/cli/#add).
  * Do not install the dependency: remove the item from the `locked_deps` list in
    `tox.ini`.

#### Extra Not Found Error

* **Status value:** `ExtraNotFoundError`
* **Cause:** Indicates that the [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras)
  configuration option specified a setuptools extra that is not configured by Poetry in
  `pyproject.toml`
* **Resolution options:**
  * Configure the extra: add a section for the named extra to the
    [`extras`](https://python-poetry.org/docs/pyproject/#extras) section of
    `pyproject.toml` and optionally assign dependencies to the named extra using the
    [`--optional`](https://python-poetry.org/docs/cli/#options_3) dependency setting.
  * Remove the extra: remove the item from the `extras` list in `tox.ini`.

#### Locked Dependencies Required Error

* **Status value:** `LockedDepsRequiredError`
* **Cause:** Indicates that an environment with the [`require_locked_deps`](#require_locked_deps)
  configuration option also specified unlocked dependencies using
  [`deps`](https://tox.readthedocs.io/en/latest/config.html#conf-deps) option in
  `tox.ini`.
* **Resolution options:**
  * Remove all unlocked dependencies: remove the `deps` configuration option in
    `tox.ini`.
  * Allow unlocked dependencies: remove the `require_locked_deps` configuration option
    in `tox.ini` or explicitly set `require_locked_deps = false`.

### Advanced Usage

#### Unsupported Tox configuration options

The `tox.ini` configuration options listed below have no effect on the dependencies
installed by this plugin the Poetry lockfile. Note that these settings will still be
applied by the default Tox installation backend when installing unlocked dependencies
using the built-in `deps` option.

  * [`install_command`](https://tox.readthedocs.io/en/latest/config.html#conf-install_command)
  * [`pip_pre`](https://tox.readthedocs.io/en/latest/config.html#conf-pip_pre)
  * [`download`](https://tox.readthedocs.io/en/latest/config.html#conf-download)
  * [`indexserver`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)
  * [`usedevelop`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)

All of these options are obsoleted by using the Poetry backend. If a given package
installs successfully using Poetry (using either `poetry add <package>` or
`poetry install`) then the required configuration options are already properly set in
the Poetry configuration and the plugin will automatically use the same settings when
installing the package.

#### Reinstalling locked dependencies to a Tox environment

Updating the `poetry.lock` file will not automatically cause Tox to install the updated
lockfile specifications to the Tox environments that specify them.

The Tox environment(s) with updated locked dependencies must be deleted and recreated
using the [`--recreate`](https://tox.readthedocs.io/en/latest/config.html#cmdoption-tox-r)
runtime flag. Alternatively Tox can be configured to always recreate an environment by
setting the [`recreate`](https://tox.readthedocs.io/en/latest/config.html#conf-recreate)
option in `tox.ini`.

#### Installing Poetry's unsafe dependencies

There are several packages that cannot be installed from the lockfile because they are
excluded by Poetry itself. As a result these packages cannot be installed by this plugin
either as environment dependencies (passed directly to [`locked_deps`](#locked_deps)) or
as transient dependencies (a dependency of a locked dependency).

As of [Poetry-1.1.4](https://github.com/python-poetry/poetry/releases/tag/1.1.4) there
are four packages classified as "unsafe" by Poetry and excluded from the lockfile:

* `setuptools`
* `distribute`
* `pip`
* `wheel`

When one of these packages is encountered by the plugin a warning will be logged and
_**the package will not be installed to the environment**_. If the unsafe package
is required for the environment then it will need to be specified as an unlocked
dependency using the [`deps`](https://tox.readthedocs.io/en/latest/config.html#conf-deps)
configuration option in `tox.ini`, ideally with an exact pinned version.

* The set of packages excluded from the Poetry lockfile can be found in
  [`poetry.puzzle.provider.Provider.UNSAFE_DEPENDENCIES`](https://github.com/python-poetry/poetry/blob/master/poetry/puzzle/provider.py)
* There is an ongoing discussion of Poetry's handling of these packages at
  [python-poetry/poetry#1584](https://github.com/python-poetry/poetry/issues/1584)

#### Installing alongside an existing Poetry installation

The plugin specifies the `poetry` package as an optional dependency to support an
externally managed Poetry installation such as in a container or CI environment. This
gives greater flexibility when using Poetry arguments like `--no-root`, `--no-dev`, or
`--remove-untracked` which can cause Poetry to uninstall itself if Poetry is specified
as a dependency of one of the packages it is managing (like this plugin).

To have the plugin use the externally-managed Poetry package simply do not install the
`poetry` extra when installing this plugin:

```bash
# Installing Poetry as a dependency with the plugin
poetry add tox-poetry-installer[poetry]

# Relying on an externally managed Poetry installation
poetry add tox-poetry-installer
```

Note that Poetry is an optional dependency to support this use case _only_: Poetry must
be installed to the same environment as Tox for the plugin to function. To check that
the local environment has all of the required modules in scope run the below command:

```bash
python -c '\
  import tox;\
  import tox_poetry_installer;\
  from poetry.poetry import Poetry;\
'
```

**NOTE:** To force Tox to fail if Poetry is not installed, run the `tox` command with
the [`--require-poetry`](#--require-poetry) option.


## Developing

This project requires Poetry version 1.0+ on the development workstation, see
the [installation instructions here](https://python-poetry.org/docs/#installation).

Local environment setup instructions:

```bash
# Clone the repository...
# ...over HTTPS
git clone https://github.com/enpaul/tox-poetry-installer.git
# ...over SSH
git clone git@github.com:enpaul/tox-poetry-installer.git

# Create a the local project virtual environment and install dependencies
cd tox-poetry-installer
poetry install -E poetry

# Install pre-commit hooks
poetry run pre-commit install

# Run tests and static analysis
poetry run tox
```

**NOTE:** Because the pre-commit hooks require dependencies in the Poetry environment it
is recommend to [launch an environment shell](https://python-poetry.org/docs/cli/#shell)
when developing the project. Alternatively, many `git` commands will need to be run from
outside of the environment shell by prefacing the command with
[`poetry run`](https://python-poetry.org/docs/cli/#run).


## Contributing

All project contributors and participants are expected to adhere to the
[Contributor Covenant Code of Conduct, v2](CODE_OF_CONDUCT.md)
([external link](https://www.contributor-covenant.org/version/2/0/code_of_conduct/)).

The `devel` branch has the latest (potentially unstable) changes. The
[tagged versions](https://github.com/enpaul/tox-poetry-installer/releases) correspond to the
releases on PyPI.

* To report a bug, request a feature, or ask for assistance, please
  [open an issue on the Github repository](https://github.com/enpaul/tox-poetry-installer/issues/new).
* To report a security concern or code of conduct violation, please contact the project author
  directly at **‌me [at‌] enp dot‎ ‌one**.
* To submit an update, please
  [fork the repository](https://docs.github.com/en/enterprise/2.20/user/github/getting-started-with-github/fork-a-repo)
  and
  [open a pull request](https://github.com/enpaul/tox-poetry-installer/compare).


## Roadmap

This project is under active development and is classified as beta software, ready for
production environments on a provisional basis only.

* Beta classification was assigned with [v0.6.0](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.6.0)
* Stable classification will be assigned when the test suite covers an acceptable number of
  use cases

### Path to Beta

- [X] Verify that primary package dependencies (from the `.package` env) are installed
      correctly using the Poetry backend.
- [X] Support the [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras)
      Tox configuration option ([#4](https://github.com/enpaul/tox-poetry-installer/issues/4))
- [X] Add per-environment Tox configuration option to fall back to default installation
      backend.
- [ ] ~Add warnings when an unsupported Tox configuration option is detected while using the
      Poetry backend. ([#5](https://github.com/enpaul/tox-poetry-installer/issues/5))~
- [X] Add trivial tests to ensure the project metadata is consistent between the pyproject.toml
      and the module constants.
- [X] Update to use [poetry-core](https://github.com/python-poetry/poetry-core) and
      improve robustness of the Tox and Poetry module imports
      to avoid potentially breaking API changes in upstream packages. ([#2](https://github.com/enpaul/tox-poetry-installer/issues/2))
- [ ] ~Find and implement a way to mitigate the [UNSAFE_DEPENDENCIES issue](https://github.com/python-poetry/poetry/issues/1584) in Poetry.
      ([#6](https://github.com/enpaul/tox-poetry-installer/issues/6))~
- [X] Fix logging to make proper use of Tox's logging reporter infrastructure ([#3](https://github.com/enpaul/tox-poetry-installer/issues/3))
- [X] Add configuration option for installing all dev-dependencies to a testenv ([#14](https://github.com/enpaul/tox-poetry-installer/issues/14))

### Path to Stable

Everything in Beta plus...

- [ ] Add comprehensive unit tests
- [ ] Add tests for each feature version of Tox between 3.0 and 3.20
- [ ] Add tests for Python-3.6, 3.7, 3.8, and 3.9
- [X] Add Github Actions based CI
- [ ] Add CI for CPython, PyPy, and Conda
- [ ] Add CI for Linux and Windows
