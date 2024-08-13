"""Custom plugin exceptions

All exceptions should inherit from the common base exception :exc:`ToxPoetryInstallerException`.

::

  ToxPoetryInstallerException
   +-- SkipEnvironment
   |    +-- PoetryNotInstalledError
   +-- LockedDepVersionConflictError
   +-- LockedDepNotFoundError
   +-- ExtraNotFoundError
   +-- LockedDepsRequiredError

"""


class ToxPoetryInstallerException(Exception):
    """Error while installing locked dependencies to the test environment"""


class SkipEnvironment(ToxPoetryInstallerException):
    """Current environment does not meet preconditions and should be skipped by the plugin"""


class PoetryNotInstalledError(SkipEnvironment):
    """No version of Poetry could be imported from the current Python environment"""


class LockedDepVersionConflictError(ToxPoetryInstallerException):
    """Locked dependencies cannot specify an alternate version for installation"""


class LockedDepNotFoundError(ToxPoetryInstallerException):
    """Locked dependency was not found in the lockfile"""


class ExtraNotFoundError(ToxPoetryInstallerException):
    """Project package extra not defined in project's pyproject.toml"""


class LockedDepsRequiredError(ToxPoetryInstallerException):
    """Environment cannot specify unlocked dependencies when locked dependencies are required"""
