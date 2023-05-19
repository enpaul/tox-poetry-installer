# tox-poetry-installer

A plugin for [Tox](https://tox.readthedocs.io/en/latest/) that lets you install test
environment dependencies from the [Poetry](https://python-poetry.org/) lockfile.

[![CI Status](https://github.com/enpaul/tox-poetry-installer/workflows/CI/badge.svg?event=push)](https://github.com/enpaul/tox-poetry-installer/actions)
[![PyPI Version](https://img.shields.io/pypi/v/tox-poetry-installer)](https://pypi.org/project/tox-poetry-installer/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/tox-poetry-installer)](https://libraries.io/pypi/tox-poetry-installer)
[![License](https://img.shields.io/pypi/l/tox-poetry-installer)](https://opensource.org/licenses/MIT)
[![Python Supported Versions](https://img.shields.io/pypi/pyversions/tox-poetry-installer)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

⚠️ **This project is beta software and is under active development** ⚠️

## Documentation

- [Feature Overview](#feature-overview)
- [Using the Plugin](#user-documentation)
  - [Installing](#installing)
  - [Quick Start](#quick-start)
  - [References](#references)
    - [Config Options](#configuration-options)
    - [Runtime Options](#runtime-options)
    - [Errors](#errors)
  - [Other Notes](#other-notes)
    - [Unsupported Tox config options](#unsupported-tox-config-options)
    - [Updating locked dependencies in a testenv](#updating-locked-dependencies-in-a-testenv)
    - [Using with an unmanaged Poetry installation](#using-with-an-unmanaged-poetry-installation)
- [Developing the Plugin](#developer-documentation)
- [Road Map](#road-map)

See the
[Changelog](https://github.com/enpaul/tox-poetry-installer/blob/devel/CHANGELOG.md) for
release history.

*See also: [official Tox plugins](https://tox.readthedocs.io/en/latest/plugins.html) and
[the official Poetry documentation on using Tox](https://python-poetry.org/docs/faq/#is-tox-supported)*

## Feature Overview

- Manage package versions in exactly one place and with exactly one tool: Poetry.
- Ensure CI/CD and other automation tools are using the same package versions that you are
  in your local development environment.
- Add only the packages or custom groups you need to a Tox test environment, instead of
  everything in your lockfile.
- Directly integrate with Poetry, re-using your existing package indexes and credentials,
  with no additional configuration.
- Wherever possible, built-in Tox config options are always respected and their behavior
  kept consistent.
- Extremely configurable. Every feature can be disabled or enabled for any given Tox test
  environment.
- Friendly to other Tox plugins and supports a wide range of environments.

## User Documentation

*This section is for users looking to integrate the plugin with their project or CI
system. For information on contributing to the plugin please see the
[Developer Docs](#developer-documentation)*

### Installing

The recommended way to install the plugin is to add it to a project using Poetry:

```bash
poetry add -G dev tox-poetry-installer[poetry]
```

> ℹ️ **Note:** Always install the plugin with the `[poetry]` extra, unless you are
> [managing the Poetry installation yourself](#externally-managed-poetry-installation).

Alternatively, it can be installed directly to a virtual environment using Pip, though
this is not recommended:

```bash
source somevenv/bin/activate
pip install tox-poetry-installer
```

Alternatively alternatively, it can be installed using the Tox
[`requires`](https://tox.readthedocs.io/en/latest/config.html#conf-requires) option by
adding the below to `tox.ini`, though this is also not recommended:

```ini
requires =
    tox-poetry-installer[poetry] == 0.10.2
```

After installing, check that Tox recognizes the plugin by running
`poetry run tox --version`. The command should give output similar to below:

```
3.20.0 imported from .venv/lib64/python3.10/site-packages/tox/__init__.py
registered plugins:
    tox-poetry-installer-0.10.2 at .venv/lib64/python3.10/site-packages/tox_poetry_installer/__init__.py
```

### Quick Start

Congratulations! 🎉 Just by installing the plugin your Tox config is already using locked
dependencies: when Tox builds and installs your project package to a test environment,
your project package's dependencies will be installed from the lockfile.

Now lets update an example `tox.ini` to install the other test environment dependencies
from the lockfile.

A `testenv` from the example `tox.ini` we're starting with is below:

```ini
[testenv]
description = Some very cool tests
deps =
    black == 20.8b1
    pylint >=2.4.4,<2.7.0
    mypy <0.800
commands = ...
```

To update the config so that the testenv dependencies are installed from the lockfile, we
can replace the built-in
[`deps`](https://tox.readthedocs.io/en/latest/config.html#conf-deps) option with the
`locked_deps` option provided by the plugin, and then remove the inline version
specifiers. With these changes the three testenv dependencies (as well as all of their
dependencies) will be installed from the lockfile when the test environment is recreated:

```ini
[testenv]
description = Some very cool tests
locked_deps =
    black
    pylint
    mypy
commands = ...
```

We can also add the `require_locked_deps` option to the test environment. This will both
block any other install tools (another plugin or Tox itself) from installing dependencies
to the Tox environment and also cause Tox to fail if the test environment also uses the
built-in [`deps`](https://tox.readthedocs.io/en/latest/config.html#conf-deps) option:

```ini
[testenv]
description = Some very cool tests
require_locked_deps = true
locked_deps =
    black
    pylint
    mypy
commands = ...
```

> ℹ️ **Note:** Settings configured on the main `testenv` environment are inherited by
> child test environments (for example, `testenv:foo`). To override this, specify the
> setting in the child environment with a different value.

Alternatively, we can skip specifying all of our dependencies for a test environment in
the Tox config and install Poetry dependency groups directly:

```ini
[testenv]
description = Some very cool tests
require_locked_deps = true
poetry_dep_groups =
    dev
commands = ...
```

> ℹ️ **Note:** The `install_dev_deps` configuration option is deprecated. See
> [Configuration Options](#configuration-options) for more information.

Finally, we can also install an unlocked dependency (a dependency which doesn't take its
version from the Poetry lockfile) into the test environment alongside the locked ones. We
need to remove the `require_locked_deps = true` option, otherwise the environment will
error, and then we can add the unlocked dependency using the built-in
[`deps`](https://tox.readthedocs.io/en/latest/config.html#conf-deps) option:

```ini
[testenv]
description = Some very cool tests
deps =
    pytest >= 5.6.0,<6.0.0
locked_deps =
    black
    pylint
    mypy
commands = ...
```

## References

### Configuration Options

All options listed below are Tox environment options and can be applied to one or more
environment sections of the `tox.ini` file. They cannot be applied to the global Tox
configuration section.

> ℹ️ **Note:** Settings configured on the main `testenv` environment are inherited by
> child test environments (for example, `testenv:foo`). To override this, specify the
> setting in the child environment with a different value.

| Option                 |  Type   | Default | Description                                                                                                                                                                                                                                                                                                                                                          |
| :--------------------- | :-----: | :-----: | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `locked_deps`          |  List   |  `[]`   | Names of packages to install to the test environment from the Poetry lockfile. Transient dependencies (packages required by these dependencies) are automatically included.                                                                                                                                                                                          |
| `require_locked_deps`  | Boolean |  False  | Whether the plugin should block attempts to install unlocked dependencies to the test environment. If enabled, then the [`tox_testenv_install_deps`](https://tox.readthedocs.io/en/latest/plugins.html#tox.hookspecs.tox_testenv_install_deps) plugin hook will be intercepted and an error will be raised if the test environment has the `deps` option configured. |
| `install_project_deps` | Boolean |  True   | Whether all of the Poetry primary dependencies for the project package should be installed to the test environment.                                                                                                                                                                                                                                                  |
| `require_poetry`       | Boolean |  False  | Whether Tox should be forced to fail if the plugin cannot import Poetry locally. If `False` then the plugin will be skipped for the test environment if Poetry cannot be imported. If `True` then the plugin will force the environment to error and the Tox run to fail.                                                                                            |
| `poetry_dep_groups`    |  List   |  `[]`   | Names of Poetry dependency groups specified in `pyproject.toml` to install to the test environment.                                                                                                                                                                                                                                                                  |

> ℹ️ **Note:** The `install_dev_deps` configuration option is deprecated and will be
> removed in version 1.0.0. Please set `poetry_dep_groups = [dev]` in `tox.ini` for
> environments that install the development dependencies.

### Runtime Options

All arguments listed below can be passed to the `tox` command to modify runtime behavior
of the plugin.

| Argument                     |  Type   | Default | Description                                                                                                                                                                                                                                                                          |
| :--------------------------- | :-----: | :-----: | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--parallel-install-threads` | Integer |  `10`   | Number of worker threads to use to install dependencies in parallel. Installing in parallel with more threads can greatly speed up the install process, but can cause race conditions during install. Pass this option with the value `0` to entirely disable parallel installation. |

> ℹ️ **Note:** The `--require-poetry` runtime option is deprecated and will be removed in
> version 1.0.0. Please set `require_poetry = true` in `tox.ini` for environments that
> should fail if Poetry is not available.

> ℹ️ **Note:** The `--parallelize-locked-install` option is deprecated and will be removed
> in version 1.0.0. Please use the `--parallel-install-threads` option.

### Errors

There are several errors that the plugin can encounter for a test environment when Tox is
run. If an error is encountered then the status of the test environment that caused the
error will be set to one of the "Status" values below to indicate what the error was.

| Status/Name                     | Cause                                                                                                                                                                                                                           |
| :------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ExtraNotFoundError`            | Indicates that the [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras) config option specified an extra that is not configured by Poetry in `pyproject.toml`.                                              |
| `LockedDepVersionConflictError` | Indicates that an item in the `locked_deps` config option includes a [PEP-508 version specifier](https://www.python.org/dev/peps/pep-0508/#grammar) (ex: `pytest >=6.0, <6.1`).                                                 |
| `LockedDepNotFoundError`        | Indicates that an item specified in the `locked_deps` config option does not match the name of a package in the Poetry lockfile.                                                                                                |
| `LockedDepsRequiredError`       | Indicates that a test environment with the `require_locked_deps` config option set to `true` also specified unlocked dependencies using the [`deps`](https://tox.readthedocs.io/en/latest/config.html#conf-deps) config option. |
| `PoetryNotInstalledError`       | Indicates that the `poetry` module could not be imported under the current runtime environment, and `require_poetry = true` was specified.                                                                                      |
| `RequiresUnsafeDepError`        | Indicates that the package-under-test depends on a package that Poetry has classified as unsafe and cannot be installed.                                                                                                        |

> ℹ️ **Note:** One or more of these errors can be caused by the `pyproject.toml` being out
> of sync with the Poetry lockfile. If this is the case, than a warning will be logged
> when Tox is run.

### Other Notes

#### Unsupported Tox config options

Below are the built-in Tox config options that are not respected by this plugin. All of
these options are made obsolete by the Poetry lockfile: either they aren't needed or their
equivalent functionality is instead taken directly from the package details Poetry stores
in its lockfile.

> ℹ️ **Note:** The unsupported Tox config options will still apply to unlocked
> dependencies being installed with the default Tox installation backend.

- [`install_command`](https://tox.readthedocs.io/en/latest/config.html#conf-install_command)
- [`pip_pre`](https://tox.readthedocs.io/en/latest/config.html#conf-pip_pre)
- [`download`](https://tox.readthedocs.io/en/latest/config.html#conf-download)
- [`indexserver`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)
- [`usedevelop`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)

#### Updating locked dependencies in a testenv

When Poetry updates the version of a package in the lockfile (using either `poetry lock`
or `poetry update`) then the plugin will automatically use this new version to install the
package to a test environment; there is no need to manually update `tox.ini` after
updating the Poetry lockfile.

However, the plugin cannot determine when the lockfile is updated. If a Tox test
environment has already been created then it will need to be recreated (using Tox's
built-in
[`--recreate`](https://tox.readthedocs.io/en/latest/example/basic.html#forcing-re-creation-of-virtual-environments)
option) for the new version to be found and installed.

> ℹ️ **Note:** To force Tox to always recreate a test environment the
> [`recreate`](https://tox.readthedocs.io/en/latest/config.html#conf-recreate) config
> option can be set.

#### Using with an unmanaged Poetry installation

In CI/CD systems, automation environments, or other Python environments where the loaded
site packages are not managed by Poetry, it can be useful to manage the local installation
of Poetry externally. This also helps to avoid problems that can be caused by the
`--no-root`, `--without dev`, or `--sync` arguments to the `poetry install` command which,
in some situations, can cause Poetry to uninstall itself if Poetry is specified as a
dependency of one of the packages it is managing (like this plugin). To support these use
cases, this plugin specifies the `poetry` package as an optional dependency that can be
installed using a setuptools extra also named `poetry`.

> ⚠️ **Warning:** This plugin requires Poetry to function. If the plugin is installed
> without the `poetry` setuptools extra then Poetry must be installed independently for
> the plugin to function properly.

To skip installing the `poetry` package as a dependency of `tox-poetry-installer`, do not
specify the `poetry` extra when adding the plugin:

```bash
# Adding the package without the "[poetry]" extra specifier so that
# Poetry is not added as a transient dev-dependency:
poetry add -G dev tox-poetry-installer

# Adding the package with the "[poetry]" extra specifier, so the Poetry
# package will be added to the environment and tracked in the lockfile:
poetry add -G dev tox-poetry-installer[poetry]
```

Once the plugin is installed- either with or without the Poetry extra- you can validate
that the plugin will run correctly with the following command. This command checks that
all three required components (Tox, Poetry, and the plugin itself) are available in the
current Python environment:

```bash
python -c '\
  import tox;\
  import tox_poetry_installer;\
  from poetry.poetry import Poetry;\
'
```

> ℹ️ **Note:** To force Tox to fail if Poetry is not installed, add the
> `require_poetry = true` option to the tox `[testenv]` configuration. See the
> [Config Options](#configuration-options) for more information.

## Developer Documentation

All project contributors and participants are expected to adhere to the
[Contributor Covenant Code of Conduct, v2](CODE_OF_CONDUCT.md)
([external link](https://www.contributor-covenant.org/version/2/0/code_of_conduct/)).

The `devel` branch has the latest (and potentially unstable) changes. The stable releases
are tracked on [Github](https://github.com/enpaul/tox-poetry-installer/releases),
[PyPi](https://pypi.org/project/tox-poetry-installer/#history), and in the
[Changelog](CHANGELOG.md).

- To report a bug, request a feature, or ask for assistance, please
  [open an issue on the Github repository](https://github.com/enpaul/tox-poetry-installer/issues/new).
- To report a security concern or code of conduct violation, please contact the project
  author directly at **‌me \[at‌\] enp dot‎ ‌one**.
- To submit an update, please
  [fork the repository](https://docs.github.com/en/enterprise/2.20/user/github/getting-started-with-github/fork-a-repo)
  and [open a pull request](https://github.com/enpaul/tox-poetry-installer/compare).

Developing this project requires [Python 3.10+](https://www.python.org/downloads/) and
[Poetry 1.4](https://python-poetry.org/docs/#installation) or later. GNU Make can
optionally be used to quickly setup a local development environment, but this is not
required.

To setup a local development environment:

```bash
# Clone the repository...
# ...over HTTPS
git clone https://github.com/enpaul/tox-poetry-installer.git
# ...over SSH
git clone git@github.com:enpaul/tox-poetry-installer.git

cd tox-poetry-installer/

# Create and configure the local development environment
make dev

# Run tests and CI locally
make test

# See additional make targets
make help
```

> ℹ️ **Note:** The pre-commit hooks require dependencies in the Poetry environment to run.
> To make a commit with the pre-commit hooks, you will need to run `poetry run git commit`
> or, alternatively,
> [launch an environment shell](https://python-poetry.org/docs/cli/#shell).

## Road Map

This project is under active development and is classified as beta software, ready for
production environments on a provisional basis only.

- Beta classification was assigned with
  [v0.6.0](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.6.0)
- Stable classification will be assigned when the test suite covers an acceptable number
  of use cases

### Path to Beta

- [x] Verify that primary package dependencies (from the `.package` env) are installed
  correctly using the Poetry backend.
- [x] Support the [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras)
  Tox configuration option ([#4](https://github.com/enpaul/tox-poetry-installer/issues/4))
- [x] Add per-environment Tox configuration option to fall back to default installation
  backend.
- [ ] ~Add warnings when an unsupported Tox configuration option is detected while using
  the Poetry backend.~ ([#5](https://github.com/enpaul/tox-poetry-installer/issues/5))
- [x] Add trivial tests to ensure the project metadata is consistent between the
  pyproject.toml and the module constants.
- [x] Update to use [poetry-core](https://github.com/python-poetry/poetry-core) and
  improve robustness of the Tox and Poetry module imports to avoid potentially breaking
  API changes in upstream packages.
  ([#2](https://github.com/enpaul/tox-poetry-installer/issues/2))
- [ ] ~Find and implement a way to mitigate the
  [UNSAFE_DEPENDENCIES issue](https://github.com/python-poetry/poetry/issues/1584) in
  Poetry.~ ([#6](https://github.com/enpaul/tox-poetry-installer/issues/6))
- [x] Fix logging to make proper use of Tox's logging reporter infrastructure
  ([#3](https://github.com/enpaul/tox-poetry-installer/issues/3))
- [x] Add configuration option for installing all dev-dependencies to a testenv
  ([#14](https://github.com/enpaul/tox-poetry-installer/issues/14))

### Path to Stable

Everything in Beta plus...

- [ ] Fully replace dependency on `poetry` with dependency on `poetry-core`
  ([#2](https://github.com/enpaul/tox-poetry-installer/issues/2))
- [x] Add comprehensive unit tests
- [ ] ~Add tests for each feature version of Tox between 3.8 and 3.20~
- [x] Add tests for Python-3.6, 3.7, 3.8, and 3.9
- [x] Add Github Actions based CI
