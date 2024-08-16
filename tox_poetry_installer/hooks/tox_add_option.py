"""Add additional command line arguments to tox to configure plugin behavior"""

from tox.config.cli.parser import ToxParser
from tox.plugin import impl

from tox_poetry_installer import constants


# pylint: disable=missing-function-docstring
@impl
def tox_add_option(parser: ToxParser):
    parser.add_argument(
        "--parallel-install-threads",
        type=int,
        dest="parallel_install_threads",
        default=constants.DEFAULT_INSTALL_THREADS,
        help="Number of locked dependencies to install simultaneously; set to 0 to disable parallel installation",
    )
