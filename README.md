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
* [Usage Examples](#usage-examples)
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
* [Tox plugins](https://tox.readthedocs.io/en/latest/plugins.html)


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
    tox-poetry-installer-0.2.2 at .venv/lib64/python3.8/site-packages/tox_poetry_installer.py
```

If using Pip, ensure that the plugin is installed to the same environment as Tox:

```
# Calling the virtualenv's 'pip' binary directly will cause pip to install to that virtualenv
~ $: /path/to/my/automation/virtualenv/bin/pip install tox
~ $: /path/to/my/automation/virtualenv/bin/pip install tox-poetry-installer
```


## Quick Start

To require a Tox environment install all it's dependencies from the Poetry lockfile, add the
`require_locked_deps = true` option to the environment configuration and remove all version
specifiers from the dependency list. The versions to install will be taken from the lockfile
directly:

```ini
[testenv]
description = Run the tests
require_locked_deps = true
deps =
    pytest
    pytest-cov
    black
    pylint
    mypy
commands = ...
```

To require specific dependencies be installed from the Poetry lockfile, and let the rest be
installed using the default Tox installation backend, add the suffix `@poetry` to the dependencies.
In the example below the `pytest`, `pytest-cov`, and `black` dependencies will be installed from
the lockfile while `pylint` and `mypy` will be installed using the versions specified here:

```ini
[testenv]
description = Run the tests
require_locked_deps = true
deps =
    pytest@poetry
    pytest-cov@poetry
    black@poetry
    pylint >=2.5.0
    mypy == 0.770
commands = ...
```

**Note:** Regardless of the settings outlined above, all dependencies of the project package (the
one Tox is testing) will always be installed from the lockfile.


## Usage Examples

After installing the plugin to a project your Tox automation is already benefiting from the
lockfile: when Tox installs your project package to one of your environments, all the dependencies
of your project package will be installed using the versions specified in the lockfile. This
happens automatically and requires no configuration changes.

But what about the rest of your Tox environment dependencies?

Let's use an example `tox.ini` file, below, that defines two environments: the main `testenv` for
running the project tests and `testenv:check` for running some other helpful tools:

```ini
[tox]
envlist = py37, static
isolated_build = true

[testenv]
description = Run the tests
deps =
    pytest == 5.3.0
commands = ...

[testenv:check]
description = Static formatting and quality enforcement
deps =
    pylint >=2.4.4,<2.6.0
    mypy == 0.770
    black --pre
commands = ...
```

Let's focus on the `testenv:check` environment first. In this project there's no reason that any
of these tools should be a different version than what a human developer is using when installing
from the lockfile. We can require that these dependencies be installed from the lockfile by adding
the option `require_locked_deps = true` to the environment config, but this will cause an error:

```ini
[testenv:check]
description = Static formatting and quality enforcement
require_locked_deps = true
deps =
    pylint >=2.4.4,<2.6.0
    mypy == 0.770
    black --pre
commands = ...
```

Running Tox using this config gives us this error:

```
tox_poetry_installer.LockedDepVersionConflictError: Locked dependency 'pylint >=2.4.4,<2.6.0' cannot include version specifier
```

This is because we told the Tox environment to require all dependencies be locked, but then also
specified a specific version constraint for Pylint. With the `require_locked_deps = true` setting
Tox expects all dependencies to take their version from the lockfile, so when it gets conflicting
information it errors. We can fix this by simply removing all version specifiers from the
environment dependency list:

```ini
[testenv:check]
description = Static formatting and quality enforcement
require_locked_deps = true
deps =
    pylint
    mypy
    black
commands = ...
```

Now all the dependencies will be installed from the lockfile. If Poetry updates the lockfile with
a new version then that updated version will be automatically installed when the Tox environment is
recreated.

Now let's look at the `testenv` environment. Let's make the same changes to the `testenv`
environment that we made to `testenv:check` above; remove the PyTest version and add
`require_locked_deps = true`. Then imagine that we want to add the
[Requests](https://requests.readthedocs.io/en/master/) library to the test environment: we
can add `requests` as a dependency of the test environment, but this will cause an error:

```ini
[testenv]
description = Run the tests
require_locked_deps = true
deps =
    pytest
    requests
commands = ...
```

Running Tox with this config gives us this error:

```
tox_poetry_installer.LockedDepNotFoundError: No version of locked dependency 'requests' found in the project lockfile
```

This is because `requests` is not in our lockfile yet. Tox will refuse to install a dependency
that isn't in the lockfile to an an environment that specifies `require_locked_deps = true`. We
can fix this by running `poetry add requests --dev` to add it to the lockfile.

Now let's combine dependencies from the lockfile with dependencies that are
specified in-line in the Tox environment configuration.
[This isn't generally recommended](#why-would-i-use-this), but it is a valid use case and
fully supported by this plugin. Let's modify the `testenv` configuration to install PyTest
from the lockfile but then install an older version of the Requests library.

The first thing to do is remove the `require_locked_deps = true` setting so that we can install
Requests as an unlocked dependency. Then we can add our version specifier to the `requests`
entry in the dependency list:

```ini
[testenv]
description = Run the tests
deps =
    pytest
    requests >=2.2.0,<2.10.0
commands = ...
```

However we still want `pytest` to be installed from the lockfile, so the final step is to tell Tox
to install it from the lockfile by adding the suffix `@poetry` to the `pytest` entry in the
dependency list:

```ini
[testenv]
description = Run the tests
deps =
    pytest@poetry
    requests >=2.2.0,<2.10.0
commands = ...
```

Now when the `testenv` environment is created it will install PyTest (and all of its dependencies)
from the lockfile while it will install Requests (and all of its dependencies) using the default
Tox installation backend.


## Known Drawbacks and Problems

* The following `tox.ini` configuration options have no effect on the dependencies installed from
  the Poetry lockfile (note that they will still affect unlocked dependencies):
  * [`install_command`](https://tox.readthedocs.io/en/latest/config.html#conf-install_command)
  * [`pip_pre`](https://tox.readthedocs.io/en/latest/config.html#conf-pip_pre)
  * [`downloadcache`](https://tox.readthedocs.io/en/latest/config.html#conf-downloadcache) (deprecated)
  * [`download`](https://tox.readthedocs.io/en/latest/config.html#conf-download)
  * [`indexserver`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)
  * [`usedevelop`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)

* The [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras) setting in `tox.ini`
  does not work. Optional dependencies of the project package will not be installed to Tox
  environments. (See the [road map](#roadmap))

* The plugin currently depends on `poetry<1.1.0`. This can be a different version than Poetry being
  used for actual project development. (See the [road map](#roadmap))

* Tox environments automatically inherit their settings from the main `testenv` environment. This
  means that if the `require_locked_deps = true` is specified for the `testenv` environment then
  all environments will also require locked dependencies. This can be overwritten by explicitly
  specifying `require_locked_deps = false` on child environments where unlocked dependencies are
  needed.

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
deps =
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

This project requires Poetry version 1.0+, see the [installation instructions here](https://python-poetry.org/docs/#installation).

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
- [ ] Support the [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras)
      Tox configuration option ([#4](https://github.com/enpaul/tox-poetry-installer/issues/4))
- [X] Add per-environment Tox configuration option to fall back to default installation
      backend.
- [ ] Add warnings when an unsupported Tox configuration option is detected while using the
      Poetry backend. ([#5](https://github.com/enpaul/tox-poetry-installer/issues/5))
- [X] Add trivial tests to ensure the project metadata is consistent between the pyproject.toml
      and the module constants.
- [ ] Update to use [poetry-core](https://github.com/python-poetry/poetry-core) and
      improve robustness of the Tox and Poetry module imports
      to avoid potentially breaking API changes in upstream packages. ([#2](https://github.com/enpaul/tox-poetry-installer/issues/2))
- [ ] Find and implement a way to mitigate the [UNSAFE_DEPENDENCIES issue](https://github.com/python-poetry/poetry/issues/1584) in Poetry.
      ([#6](https://github.com/enpaul/tox-poetry-installer/issues/6))
- [ ] Fix logging to make proper use of Tox's logging reporter infrastructure

### Path to Stable

Everything in Beta plus...

- [ ] Add tests for each feature version of Tox between 2.3 and 3.20
- [ ] Add tests for Python-3.6, 3.7, and 3.8
- [ ] Add Github Actions based CI
- [ ] Add CI for CPython, PyPy, and Conda
- [ ] Add CI for Linux and Windows
