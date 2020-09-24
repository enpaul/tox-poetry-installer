# tox-poetry-installer

A plugin for [Tox](https://tox.readthedocs.io/en/latest/) that allows test environment
dependencies to be installed using [Poetry](https://python-poetry.org/) using its lockfile.

⚠️ **This project is alpha software and should not be used in a production capacity** ⚠️

![image](https://img.shields.io/pypi/l/tox-poetry-installer)
![image](https://img.shields.io/pypi/v/tox-poetry-installer)
![image](https://img.shields.io/pypi/pyversions/tox-poetry-installer)

**Documentation**

* [Installation and Usage](#installation-and-usage)
* [Limitations](#limitations)
* [What problem does this solve?](#what-problems-does-this-solve) (Why would I use this?)
* [Developing](#developing)
* [Contributing](#contributing)
* [Roadmap](#roadmap)
  * [Path to Beta](#path-to-beta)
  * [Path to Stable](#path-to-stable)

Related resources:
* [Poetry Python Project Manager](https://python-poetry.org/)
* [Tox Automation Project](https://tox.readthedocs.io/en/latest/)
* [Tox plugins](https://tox.readthedocs.io/en/latest/plugins.html)


## Installation and Usage

1. Install the plugin from PyPI:

```
poetry add tox-poetry-installer --dev
```

2. Remove all version specifications from the environment dependencies in `tox.ini`:

```ini
# This...
[testenv]
description = My cool test environment
deps =
    requests >=2.19,<3.0
    toml == 0.10.0
    pytest >=5.4

# ...becomes this:
[testenv]
description = My cool test environment
deps =
    requests
    toml
    pytest
```

3. Run Tox with the `--recreate` flag to rebuild the test environments:

```
poetry run tox --recreate
```

4. 💸 Profit 💸


## Limitations

* In general, any command line or INI settings that affect how Tox installs environment
  dependencies will be disabled by installing this plugin. A non-exhaustive and untested
  list of the INI options that are not expected to work with this plugin is below:
  * [`install_command`](https://tox.readthedocs.io/en/latest/config.html#conf-install_command)
  * [`pip_pre`](https://tox.readthedocs.io/en/latest/config.html#conf-pip_pre)
  * [`downloadcache`](https://tox.readthedocs.io/en/latest/config.html#conf-downloadcache) (deprecated)
  * [`download`](https://tox.readthedocs.io/en/latest/config.html#conf-download)
  * [`indexserver`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)
  * [`usedevelop`](https://tox.readthedocs.io/en/latest/config.html#conf-indexserver)
  * [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras)

* When the plugin is enabled all dependencies for all environments will use the Poetry backend
  provided by the plugin; this functionality cannot be disabled on a per-environment basis.

* Alternative versions cannot be specified alongside versions from the lockfile. All
  dependencies are installed from the lockfile and alternative versions cannot be specified
  in the Tox configuration.


## What problems does this solve?

[The point of using a lockfile is to create reproducable builds](https://docs.gradle.org/current/userguide/dependency_locking.html). One of the main points of Tox is to [allow a Python
package to be built and tested in multiple environments](https://tox.readthedocs.io/en/latest/#what-is-tox). However, in the Tox configuration file the dependencies are specified with
standard dynamic ranges and passed directly to Pip. This means that the reproducability
a lockfile brings to a project is circumvented when running the tests.

The obvious solution to this problem is to add the dependencies required for testing to the
lockfile as development dependencies so that they are locked along with the primary dependencies
of the project. The only remaining question however, is how to install the dev-dependencies from
the lockfile into the Tox environment when Tox sets it up. [For very good reason](https://dev.to/elabftw/stop-using-sudo-pip-install-52mn) Tox uses independent
[virtual environments](https://docs.python.org/3/tutorial/venv.html) for each environment a
project defines, so there needs to be a way to install a locked dependency into a Tox
environment.

This is where this plugin comes in.

Traditionally Tox environments specify dependencies and their corresponding versions inline in
[PEP-440](https://www.python.org/dev/peps/pep-0440/) format like below:

```ini
[testenv]
description = Run the tests
deps =
  foo == 1.2.3
  bar >=1.3,<2.0
  baz
```

This runs into the problem outlined above: many different versions of the `bar` dependency
could be installed depending on what the latest version is that matches the defined range. The
`baz` dependency is entirely unpinned making it a true wildcard, and even the seemingly static
`foo` dependency could result in subtly different files being downloaded depending on what's
available in the upstream mirrors.

However these same versions, specified in the [pyproject.toml](https://snarky.ca/what-the-heck-is-pyproject-toml/) file, result in reproducible
installations when using `poetry install` because they each have a specific version and file
hash specified in the lockfile. The versions specified in the lockfile are updated only when
`poetry update` is run.

This plugin allows environment dependencies to be specified in the [tox.ini](https://tox.readthedocs.io/en/latest/config.html) configuration file
just by name. The package is automatically retrieved from the lockfile and the Poetry backend
is used to install the singular locked package version to the Tox environment. When the
lockfile is updated, the Tox environment will automatically install the newly locked package
as well. All dependency requirements are specified in one place (pyproject.toml), all
dependencies have a locked version, and everything is installed from that source of truth.


## Developing

This project requires Poetry-1.0+, see the [installation instructions here](https://python-poetry.org/docs/#installation).

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
usage in production systems.

* Beta classification will be assigned when the initial feature set is finalized
* Stable classification will be assigned when the test suite covers an acceptable number of
  use cases

### Path to Beta

- [ ] Verify that primary package dependencies (from the `.package` env) are installed
      correctly using the Poetry backend.
- [ ] Support the [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras)
      Tox configuration option
- [ ] Add per-environment Tox configuration option to fall back to default installation
      backend.
- [ ] Add detection of a changed lockfile to automatically trigger a rebuild of Tox
      environments when necessary.
- [ ] Add warnings when an unsupported Tox configuration option is detected while using the
      Poetry backend.
- [ ] Add trivial tests to ensure the project metadata is consistent between the pyproject.toml
      and the module constants.
- [ ] Update to use [poetry-core](https://github.com/python-poetry/poetry-core)
      Tox configuration option) and improve robustness of the Tox and Poetry module imports
      to avoid potentially breaking API changes in upstream packages.

### Path to Stable

Everything in Beta plus...

- [ ] Add tests for each feature version of Tox between 2.3 and 3.20
- [ ] Add tests for Python-3.6, 3.7, and 3.8
- [ ] Add Github Actions based CI
- [ ] Add CI for CPython, PyPy, and Conda
- [ ] Add CI for Linux and Windows
