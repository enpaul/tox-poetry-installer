"""Add additional command line arguments to tox to configure plugin behavior"""

import tox.config.cli.parser
import tox.plugin

from tox_poetry_installer import constants


# pylint: disable=missing-function-docstring
@tox.plugin.impl
def tox_add_option(parser: tox.config.cli.parser.ToxParser):
    parser.add_argument(
        "--parallel-install-threads",
        type=int,
        dest="parallel_install_threads",
        default=constants.DEFAULT_INSTALL_THREADS,
        help="Number of locked dependencies to install simultaneously; set to 0 to disable parallel installation",
    )
