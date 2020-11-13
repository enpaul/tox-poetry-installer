# tox-poetry-installer

A plugin for [Tox](https://tox.readthedocs.io/en/latest/) that allows test environment
dependencies to be installed using [Poetry](https://python-poetry.org/) from its lockfile.

⚠️ **This project is alpha software and should not be used in production environments** ⚠️

[![ci-status](https://github.com/enpaul/tox-poetry-installer/workflows/CI/badge.svg?event=push)](https://github.com/enpaul/tox-poetry-installer/actions)
[![license](https://img.shields.io/pypi/l/tox-poetry-installer)](https://opensource.org/licenses/MIT)
[![pypi-version](https://img.shields.io/pypi/v/tox-poetry-installer)](https://pypi.org/project/tox-poetry-installer/)
[![python-versions](https://img.shields.io/pypi/pyversions/tox-poetry-installer)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Documentation**

* [Installation](#installation)
* [Quick Start](#quick-start)
* [Reference and Usage](#reference-and-usage)
  * [Config Option Reference](#config-option-reference)
  * [Error Reference](#error-reference)
  * [Example Config](#example-config)
* [Known Drawbacks and Problems](#known-drawbacks-and-problems)
* [Why would I use this?](#why-would-i-use-this) (What problems does this solve?)
* [Developing](#developing)
* [Contributing](#contributing)
* [Roadmap](#roadmap)
  * [Path to Beta](#path-to-beta)
  * [Path to Stable](#path-to-stable)

Related resources:
* [Poetry Python Project Manager](https://python-poetry.org/)
* [Tox Automation Project](https://tox.readthedocs.io/en/latest/)
* [Poetry Dev-Dependencies Tox Plugin](https://github.com/sinoroc/tox-poetry-dev-dependencies)
* [Poetry Tox Plugin](https://github.com/tkukushkin/tox-poetry)
* [Other Tox plugins](https://tox.readthedocs.io/en/latest/plugins.html)


## Installation

Add the plugin as a development dependency of a Poetry project:

```
~ $: poetry add tox-poetry-installer --dev
```

Confirm that the plugin is installed, and Tox recognizes it, by checking the Tox version:

```
~ $: poetry run tox --version
3.20.0 imported from .venv/lib64/python3.8/site-packages/tox/__init__.py
registered plugins:
    tox-poetry-installer-0.5.0 at .venv/lib64/python3.8/site-packages/tox_poetry_installer.py
```

If using Pip, ensure that the plugin is installed to the same environment as Tox:

```
# Calling the virtualenv's 'pip' binary directly will cause pip to install to that virtualenv
~ $: /path/to/my/automation/virtualenv/bin/pip install tox
~ $: /path/to/my/automation/virtualenv/bin/pip install tox-poetry-installer
```

**Note:** While it is possible to install this plugin using Tox's
[`requires`](https://tox.readthedocs.io/en/latest/config.html#conf-requires)
configuration option, it is not recommended. Dependencies from the `requires` option are
installed using the default Tox installation backend which opens up the
[possibility of transient dependency problems](#why-would-i-use-this) in your automation
environment.


## Quick Start

To add dependencies from the lockfile to a Tox environment, add the option `locked_deps`
to the environment configuration and list names of dependencies (with no version
specifier) under it:

```ini
[testenv]
description = Some very cool tests
locked_deps =
    black
    pylint
    mypy
commands = ...
```

The standard `deps` option can be used in parallel with the `locked_deps` option to
install unlocked dependencies (dependencies not in the lockfile) alongside locked
dependencies:

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
`install_dev_deps =  true` option to the environment configuration.

**Note:** Regardless of the settings outlined above, all dependencies of the project package (the
one Tox is testing) will always be installed from the lockfile.


## Reference and Usage

### Config Option Reference

All options listed below are Tox environment options and can be applied to one or more
environment sections of the `tox.ini` file. They cannot be applied to the global Tox
configuration section.

**NOTE:** Environment settings applied to the main `testenv` environment will be
inherited by child environments (i.e. `testenv:foo`) unless they are explicitly
overridden by the child environment's configuration.

| Option                | Type            | Default | Usage                                          |
|:----------------------|:----------------|:--------|:-----------------------------------------------|
| `locked_deps`         | Multi-line list | `[]`    | Names of packages in the Poetry lockfile to install to the Tox environment. All dependencies specified here (and their dependencies) will be installed to the Tox environment using the version the Poetry lockfile specifies for them. |
| `require_locked_deps` | Bool            | `false` | Indicates whether the environment should allow unlocked dependencies (dependencies not in the Poetry lockfile) to be installed alongside locked dependencies. If `true` then installation of unlocked dependencies will be blocked and an error will be raised if the `deps` option specifies any values. |
| `install_dev_deps`    | Bool            | `false` | Indicates whether all Poetry development dependencies should be installed to the environment. Provides a quick and easy way to install all dev-dependencies without needing to specify them individually. |

### Error Reference

* `LockedDepVersionConflictError` - Indicates that a locked dependency included a PEP-508 version
  specifier (i.e. `pytest >=6.0, <6.1`). Locked dependencies always take their version from the
  Poetry lockfile so specifying a specific version for a locked dependency is not supported.
* `LockedDepNotFoundError` - Indicates that a locked dependency could not be found in the Poetry
  lockfile. This can be solved by [adding the dependency using Poetry](https://python-poetry.org/docs/cli/#add).
* `ExtraNotFoundError` - Indicates that the Tox `extras` option specified a project extra that
  Poetry does not know about. This may be due to a misconfigured `pyproject.toml` or out of date
  lockfile.
* `LockedDepsRequiredError` - Indicates that an environment with `require_locked_deps = true` also
  specified unlocked dependencies using Tox's `deps` option. This can be solved by either setting
  `require_locked_deps = false` (the default) or removing the `deps` option from the environment
  configuration.

### Example Config

```ini
[tox]
envlist = py, foo, bar, baz
isolated_build = true

# The base testenv will always use locked dependencies and only ever installs the project package
# (and its dependencies) and the two pytest dependencies listed below
[testenv]
description = Some very cool tests
require_locked_deps = true
locked_deps =
    pytest
    pytest-cov
commands = ...

# This environment also requires locked dependencies, but the "skip_install" setting means that
# the project dependencies will not be installed to the environment from the lockfile
[testenv:foo]
description = FOObarbaz
skip_install = true
require_locked_deps = true
locked_deps =
    requests
    toml
    ruamel.yaml
commands = ...

# This environment allows unlocked dependencies to be installed ad-hoc. Below, the "mypy" and
# "pylint" dependencies (and their dependencies) will be installed from the Poetry lockfile but the
# "black" dependency will be installed using the default Tox backend. Note, this environment does
# not specify "require_locked_deps = true" to allow the unlocked "black" dependency without raising
# an error.
[testenv:bar]
description = fooBARbaz
locked_deps =
    mypy
    pylint
deps =
    black
commands = ...

# This environment requires locked dependencies but does not specify any. Instead it specifies the
# "install_dev_deps = true" option which will cause all of the Poetry dev-dependencies to be
# installed from the lockfile.
[testenv:baz]
description = foobarBAZ
install_dev_deps = true
require_locked_deps = true
commands = ...
```


## Known Drawbacks and Problems

* The following `tox.ini` configuration options have no effect on the dependencies installed from
  the Poetry lockfile (note that they will still affect unlocked dependencies):
  * [`install_command`](https://tox.readthedocs.io/en/latest/config.html#conf-install_command)
  * [`pip_pre`](https://tox.readthedocs.io/en/latest/config.html#conf-pip_pre)
  * [`downloadcache`](https://tox.readthedocs.io/en/latest/config.html#conf-downloadcache) (deprecated)
  * [`download`](https://tox.readthedocs.io/en/latest/config.html#conf-download)
  * [`indexserver`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)
  * [`usedevelop`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)

* Tox will not automatically detect changes to the locked dependencies and so
  environments will not be automatically rebuilt when locked dependencies are changed.
  When changing the locked dependencies (or their versions) the environments will need to
  be manually rebuilt using either the `-r`/`--recreate` CLI option or the
  `recreate = true` option in `tox.ini`.

* There are a handful of packages that cannot be installed from the lockfile, whether as specific
  dependencies or as transient dependencies (dependencies of dependencies). This is due to
  [an ongoing discussion in the Poetry project](https://github.com/python-poetry/poetry/issues/1584);
  the list of dependencies that cannot be installed from the lockfile can be found
  [here](https://github.com/python-poetry/poetry/blob/cc8f59a31567f806be868aba880ae0642d49b74e/poetry/puzzle/provider.py#L55).
  This plugin will skip these dependencies entirely, but log a warning when they are encountered.


## Why would I use this?

**Introduction**

The lockfile is a file generated by a package manager for a project that records what
dependencies are installed, the versions of those dependencies, and any additional metadata that
the package manager needs to recreate the local project environment. This allows developers
to have confidence that a bug they are encountering that may be caused by one of their
dependencies will be reproducible on another device. In addition, installing a project
environment from a lockfile gives confidence that automated systems running tests or performing
builds are using the same environment as a developer.

[Poetry](https://python-poetry.org/) is a project dependency manager for Python projects, and
so it creates and manages a lockfile so that its users can benefit from all the features
described above. [Tox](https://tox.readthedocs.io/en/latest/#what-is-tox) is an automation tool
that allows Python developers to run tests suites, perform builds, and automate tasks within
self-contained [Python virtual environments](https://docs.python.org/3/tutorial/venv.html).
To make these environments useful Tox supports installing dependencies in each environment.
However, since these environments are created on the fly and Tox does not maintain a lockfile,
there can be subtle differences between the dependencies a developer is using and the
dependencies Tox uses.

This is where this plugin comes into play.

By default Tox uses [Pip](https://docs.python.org/3/tutorial/venv.html) to install the
PEP-508 compliant dependencies to a test environment. This plugin extends the default
Tox dependency installation behavior to support installing dependencies using a Poetry-based
installation method that makes use of the dependency metadata from Poetry's lockfile.

**The Problem**

Environment dependencies for a Tox environment are usually specified in PEP-508 format, like
the below example:

```ini
# from tox.ini
...

[testenv]
description = Some very cool tests
deps =
    foo == 1.2.3
    bar >=1.3,<2.0
    baz

...
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
# from tox.ini
...

[testenv]
description = Some very cool tests
require_locked_deps = true
locked_deps =
    foo
    bar
    baz

...
```

However with the `tox-poetry-installer` plugin installed the `require_locked_deps = true`
setting means that Tox will install these dependencies from the Poetry lockfile so that the
version installed to the Tox environment exactly matches the version Poetry is managing. When
`poetry update` updates the lockfile with new versions of these dependencies, Tox will
automatically install these new versions without needing any changes to the configuration.


## Developing

This project requires a developer to have Poetry version 1.0+ installed on their workstation, see
the [installation instructions here](https://python-poetry.org/docs/#installation).

```bash
# Clone the repository...
# ...over HTTPS
git clone https://github.com/enpaul/tox-poetry-installer.git
# ...over SSH
git clone git@github.com:enpaul/tox-poetry-installer.git

# Create a the local project virtual environment and install dependencies
cd tox-poetry-installer
poetry install

# Install pre-commit hooks
poetry run pre-commit install

# Run tests and static analysis
poetry run tox
```


## Contributing

All project contributors and participants are expected to adhere to the
[Contributor Covenant Code of Conduct, Version 2](CODE_OF_CONDUCT.md).

The `devel` branch has the latest (potentially unstable) changes. The
[tagged versions](https://github.com/enpaul/tox-poetry-installer/releases) correspond to the
releases on PyPI.

* To report a bug, request a feature, or ask for assistance, please
  [open an issue on the Github repository](https://github.com/enpaul/tox-poetry-installer/issues/new).
* To report a security concern or code of conduct violation, please contact the project author
  directly at **ethan dot paul at enp dot one**.
* To submit an update, please
  [fork the repository](https://docs.github.com/en/enterprise/2.20/user/github/getting-started-with-github/fork-a-repo)
  and
  [open a pull request](https://github.com/enpaul/tox-poetry-installer/compare).


## Roadmap

This project is under active development and is classified as alpha software, not yet ready
for usage in production environments.

* Beta classification will be assigned when the initial feature set is finalized
* Stable classification will be assigned when the test suite covers an acceptable number of
  use cases

### Path to Beta

- [X] Verify that primary package dependencies (from the `.package` env) are installed
      correctly using the Poetry backend.
- [X] Support the [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras)
      Tox configuration option ([#4](https://github.com/enpaul/tox-poetry-installer/issues/4))
- [X] Add per-environment Tox configuration option to fall back to default installation
      backend.
- [ ] Add warnings when an unsupported Tox configuration option is detected while using the
      Poetry backend. ([#5](https://github.com/enpaul/tox-poetry-installer/issues/5))
- [X] Add trivial tests to ensure the project metadata is consistent between the pyproject.toml
      and the module constants.
- [X] Update to use [poetry-core](https://github.com/python-poetry/poetry-core) and
      improve robustness of the Tox and Poetry module imports
      to avoid potentially breaking API changes in upstream packages. ([#2](https://github.com/enpaul/tox-poetry-installer/issues/2))
- [ ] Find and implement a way to mitigate the [UNSAFE_DEPENDENCIES issue](https://github.com/python-poetry/poetry/issues/1584) in Poetry.
      ([#6](https://github.com/enpaul/tox-poetry-installer/issues/6))
- [ ] Fix logging to make proper use of Tox's logging reporter infrastructure ([#3](https://github.com/enpaul/tox-poetry-installer/issues/3))
- [X] Add configuration option for installing all dev-dependencies to a testenv ([#14](https://github.com/enpaul/tox-poetry-installer/issues/14))

### Path to Stable

Everything in Beta plus...

- [ ] Add tests for each feature version of Tox between 2.3 and 3.20
- [ ] Add tests for Python-3.6, 3.7, and 3.8
- [X] Add Github Actions based CI
- [ ] Add CI for CPython, PyPy, and Conda
- [ ] Add CI for Linux and Windows
