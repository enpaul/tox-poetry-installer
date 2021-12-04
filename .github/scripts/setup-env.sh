#!/usr/bin/env bash
#
# Environment setup script for the local project. Intended to be used with automation
# to create a repeatable local environment for tests to be run in. The python env
# this script creates can be accessed at the location defined by the CI_VENV variable
# below.

set -e;

# ##### Prereqs #####
#
# Set global vars for usage in the script, create the cache directory so we can rely
# on that existing, then dump some diagnostic info for later reference.
#
PATH="$PATH:$HOME/.local/bin"
CI_VENV=$HOME/ci;
CI_CACHE=$HOME/.cache;
CI_CACHE_GET_POETRY="$CI_CACHE/get-poetry.py";
CI_VENV_PIP="$CI_VENV/bin/pip";
CI_VENV_PIP_VERSION=19.3.1;
CI_VENV_TOX="$CI_VENV/bin/tox";

mkdir --parents "$CI_CACHE";

command -v python;
python --version;

# ##### Install Poetry #####
#
# Download the poetry install script to the cache directory and then install poetry.
# After dump the poetry version for later reference.
#
curl https://install.python-poetry.org \
  --output "$CI_CACHE_GET_POETRY" \
  --silent \
  --show-error \
  --location;
python "$CI_CACHE_GET_POETRY" --yes 1>/dev/null;

poetry --version --no-ansi;

# ##### Setup Runtime Venv #####
#
# Create a virtual environment for poetry to use, upgrade pip in that venv to a pinned
# version, then install the current project to the venv.
#
# Note 1: Poetry, Tox, and this project plugin all use pip under the hood for package
#         installation. This means that even though we are creating up to eight venvs
#         during a given CI run they all share the same download cache.
# Note 2: The "VIRTUAL_ENV=$CI_VENV" prefix on the poetry commands below sets the venv
#         that poetry will use for operations. There is no CLI flag for poetry that
#         directs it to use a given environment, but if it finds itself in an existing
#         environment it will use it and skip environment creation.
#
python -m venv "$CI_VENV";

$CI_VENV_PIP install "pip==$CI_VENV_PIP_VERSION" \
  --upgrade \
  --quiet;

VIRTUAL_ENV=$CI_VENV poetry install \
  --extras poetry \
  --quiet \
  --no-ansi \
  &>/dev/null;

# ##### Print Debug Info #####
#
# Print the pip and tox versions (which will include registered plugins)
#
$CI_VENV_PIP --version;
echo "tox $($CI_VENV_TOX --version)";
