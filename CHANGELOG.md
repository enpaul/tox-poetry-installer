# changelog

See also: [Github Release Page](https://github.com/enpaul/tox-poetry-installer/releases).

## Version 0.10.3

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.10.3),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.10.3/)

- Update Poetry requirement to exclude usage with incompatible 1.5 release

## Version 0.10.2

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.10.2),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.10.2/)

- Update documentation with best practices and Poetry 1.2+ command syntax
- Fix failed install of sdist package not raising an exception in multi-threaded mode.
  Contributed by [chriskuehl](https://github.com/chriskuehl) (#86)

## Version 0.10.1

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.10.1),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.10.1/)

- Add PyPI classifier for Python-3.11 compatibility
- Add CI support for Python-3.11
- Add support for Poetry-1.3.x (#83)

## Version 0.10.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.10.0),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.10.0/)

- Add `poetry_dep_groups` option to support installing groups of Poetry dependencies.
  Contributed by [Oshmoun](https://github.com/oshmoun) (#76)
- Deprecate `install_dev_deps` option

## Version 0.9.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.9.0),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.9.0/)

- Add support for Poetry-1.2.x. Contributed by [Justin Wood](https://github.com/Callek)
  (#73)
- Update Black formatting to stable release version
- Remove support for Python-3.6
- Remove support for Poetry-1.1.x
- Fix installing dependencies multiple times when transient dependencies are duplicated in
  the dependency tree

## Version 0.8.5

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.8.5),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.8.5/)

- Fix Poetry version specification supporting the incompatible Poetry-1.2.0 release

## Version 0.8.4

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.8.4),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.8.4/)

- Fix issue where incompatible package versions were selected for installation when
  multiple package versions were in the lockfile

## Version 0.8.3

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.8.3),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.8.3/)

- Add PyPI classifier for Python 3.10 compatibility

## Version 0.8.2

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.8.2),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.8.2/)

- Improve debug-level logging for package installation, and time how long installing each
  package takes. Contributed by [Rebecca Turner](https://github.com/9999years) (#63).
- Fix crash caused by the package-under-test depending on Poetry's unsafe dependencies
  ([#65](https://github.com/enpaul/tox-poetry-installer/issues/65))

## Version 0.8.1

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.8.1),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.8.1/)

- Fix unintuitive behavior of the `install_project_deps` option by ensuring the specified
  value always causes the implied action

## Version 0.8.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.8.0),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.8.0/)

- Add default installation of locked dependencies using thread workers, decreasing
  environment provisioning times by ~90%
- Add runtime option `--parallel-install-threads` to support configuring the number of
  worker threads for parallel dependency installation
- Add configuration option `install_project_deps` to support disabling the install of
  project dependencies to an environment
- Deprecate runtime option `--parallelize-locked-install`

## Version 0.7.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.7.0),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.7.0/)

- Add runtime option `--parallelize-locked-install` to support installing locked
  dependencies in parallel to speed up test environment creation
- Add config option `require_poetry` to allow per-environment control over whether the
  plugin should force an error
- Add unit tests for custom dependency processing and installation
- Update internal logging system to reduce code duplication
- Update documentation to improve readability
- Deprecate runtime option `--require-poetry`

## Version 0.6.4

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.6.4),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.6.4/)

- Remove custom package compatibility checking logic from transient dependency resolution
  process
- Add integration with Poetry's compatibility
  [`Marker`](https://github.com/python-poetry/poetry-core/blob/master/poetry/core/version/markers.py)
  object system for determining package compatibility with the current platform
  ([#43](https://github.com/enpaul/tox-poetry-installer/issues/43))
- Add missing PyPI classifier for Python 3

## Version 0.6.3

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.6.3),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.6.3/)

- Update required `tox` version from `^3.0` to `^3.8` to avoid compatibility issues
- Update logging messages to improve UX
- Fix transient dependency packages being installed in a pseudo-random order due to Python
  sets being unordered ([#41](https://github.com/enpaul/tox-poetry-installer/issues/41))
- Fix outdated docstrings

## Version 0.6.2

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.6.2),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.6.2/)

- Update locked version of `py` to `1.10.0` to address
  [CVE-2020-29651](https://nvd.nist.gov/vuln/detail/CVE-2020-29651)
- Fix dependency identification failing when the package under test is a transient
  dependency of a locked dependency specified for installation
- Fix `AttributeError` being raised while creating the Tox self-provisioned environment
  when using either the
  [`minversion`](https://tox.readthedocs.io/en/latest/config.html#conf-minversion) or
  [`requires`](https://tox.readthedocs.io/en/latest/config.html#conf-requires) Tox config
  options

## Version 0.6.1

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.6.1),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.6.1/)

- Update logging around transient dependency processing to improve debugging of dependency
  installation problems
- Fix regression around handling of Poetry's unsafe packages when the unsafe package is a
  transient dependency ([#33](https://github.com/enpaul/tox-poetry-installer/issues/33))
- Fix handling of Poetry's unsafe packages when the unsafe package is a primary
  (environment or package) dependency

## Version 0.6.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.6.0),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.6.0/)

- Add `poetry` extra to support installing Poetry as a direct dependency of the plugin
- Add `--require-poetry` runtime option to force Tox failure if Poetry is not installed
- Update logging messages to improve UX around non-verbose messaging
- Update error logging to avoid dumping stack traces
- Update integration with Tox's `action` object to better manage internal state at runtime
- Update documentation to more clearly cover more use cases
- Remove `poetry` as a required dependency to support external Poetry installations

First beta release :tada:

## Version 0.5.2

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.5.2),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.5.2/)

- Fix always attempting to install dependencies with incompatible python version
  constraints
- Fix always attempting to install dependencies with incompatible python platforms

## Version 0.5.1

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.5.1),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.5.1/)

- Add CI/Tox tests for Python-3.9
- Update dependency processing to reduce duplication during installation
- Update minimum python requirement to `3.6.1`
- Fix `UnboundLocal` exception when not installing project dependencies

## Version 0.5.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.5.0),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.5.0/)

- Add option `locked_deps` to better support both locked and unlocked dependencies in a
  single environment
- Add blocking functionality when using `require_locked_deps = true` to prevent other
  hooks from running after this one
- Update documentation to include new configuration options and errors
- Update documentation to improve future maintainability
- Update module structure to move from single-file module to multi-file directory module
- Fix `RecursionError` when installing locked dependencies that specify recursive
  dependencies
- Fix always reinstalling all locked dependencies on every run regardless of update status

## Version 0.4.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.4.0),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.4.0/)

- Add `install_dev_deps` configuration option for automatically installing all Poetry
  dev-dependencies into a Tox testenv

## Version 0.3.1

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.3.1),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.3.1/)

- Fix error when installing an environment with no extras specified in the configuration
- Fix problem where only the dependencies of the sequentially last extra would be
  installed
- Fix regression causing no project dependencies to be installed

## Version 0.3.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.3.0),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.3.0/)

- Add support for the Tox
  [`extras`](https://tox.readthedocs.io/en/latest/config.html#conf-extras) configuration
  parameter
- Update runtime-skip-conditional checks to improve clarity and ease of future maintenance
- Update lockfile parsing to avoid parsing it multiple times for a single testenv
- Fix missing `poetry-core` dependency when using Poetry\<1.1.0

## Version 0.2.4

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.2.4),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.2.4/)

- Fix support for Poetry-1.1
  ([#2](https://github.com/enpaul/tox-poetry-installer/issues/2))
- Include tests in sdist ([#8](https://github.com/enpaul/tox-poetry-installer/issues/8))

## Version 0.2.3

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.2.3),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.2.3/)

- Fix usage of the plugin in non-Poetry based projects
  ([#1](https://github.com/enpaul/tox-poetry-installer/issues/1))
- Fix treating dependency names as case sensitive when they shouldn't be
  ([#7](https://github.com/enpaul/tox-poetry-installer/issues/7))

## Version 0.2.2

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.2.2),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.2.2/)

- Fix breaking when running Tox in projects that do not use Poetry for their
  environment/dependency management
  ([#1](https://github.com/enpaul/tox-poetry-installer/issues/1))

## Version 0.2.1

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.2.1),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.2.1/)

- Fix duplicate installation of transient environment dependencies
- Fix logging error indicating all environments always have zero dependencies
- Fix installing main dependencies when `skip_install` is false but `skipdist` is true

## Version 0.2.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.2.0),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.2.0/)

- Add support for per-environment configuration setting `require_locked_deps`
- Add support for per-dependency lock requirement setting using `@poetry` suffix
- Add support for coexisting locked and unlocked dependencies in a single test environment
- Update documentation to include more usage examples
- Update documentation to improve clarity around problems and drawbacks
- Fix logging messages being inconsistently formatted
- Fix raising the same exception for "locked dependency not found" and "locked dependency
  specifies alternate version" errors
- Fix plugin errors not reporting to Tox that they happened
- Fix plugin errors not causing Tox to mark the env as failed

## Version 0.1.3

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.1.3),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.1.3/)

- Fix core functionality of installing dependencies from lockfile for the
  package-under-development ("dev-package") built by Tox
- Fix log messages not being displayed with Tox output
- Add additional logging output for diagnostics
- Update Poetry requirement to exclude upcoming Poetry-1.1.0 release which will break
  compatibility

This is the first release where the core functionality actually works as expected :tada:

## Version 0.1.2

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.1.2),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.1.2/)

- Test trivial functionality on Python-3.6 and Python-3.7
- Fix disagreement between `pyproject.toml` and module metadata on what the current
  version is
- Fix constant named for PEP-440 that should have been named for PEP-508

## Version 0.1.1

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.1.1),
[PyPI](https://pypi.org/project/tox-poetry-installer/0.1.1/)

- Add/update project documentation
- Add static analysis and formatting enforcement automation to toxfile
- Add security analysis to toxfile
- Fix raising `KeyError` for unlocked dependencies
- Fix mishandling of Poetry's "unsafe dependencies"
- Lint, blacken, and generally improve code quality

## Version 0.1.0

View this release on:
[Github](https://github.com/enpaul/tox-poetry-installer/releases/tag/0.1.0),

- Add support for installing Tox environment dependencies using Poetry from the Poetry
  lockfile
