#!/usr/bin/env bash
#
# Environment setup script for the local project. Intended to be used with automation
# to create a repeatable local environment for tests to be run in. The python env
# this script creates can be accessed at the location defined by the CI_VENV variable
# below.

set -e;

CI_CACHE=$HOME/.cache;
POETRY_VERSION=1.1.12;

mkdir --parents "$CI_CACHE";

command -v python;
python --version;

curl --location https://install.python-poetry.org \
  --output "$CI_CACHE/install-poetry.py" \
  --silent \
  --show-error;
python "$CI_CACHE/install-poetry.py" \
  --version "$POETRY_VERSION" \
  --yes;
poetry --version --no-ansi;
poetry run pip --version;

poetry install \
  --extras poetry \
  --quiet \
  --remove-untracked \
  --no-ansi;

poetry env info;
poetry run tox --version;
