# tox-poetry-installer makefile

# You can set these variables from the command line
PROJECT = tox_poetry_installer

.PHONY: help
# Put it first so that "make" without argument is like "make help"
# Adapted from:
# https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## List Makefile targets
	$(info Makefile documentation)
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}'

tox: clean
	tox

clean-tox:
	rm -rf ./.mypy_cache
	rm -rf ./.tox
	rm -f .coverage

clean-py:
	rm -rf ./dist
	rm -rf ./build
	rm -rf ./*.egg-info
	rm -rf __pycache__/

clean: clean-tox clean-py clean-docs; ## Clean temp build/cache files and directories

wheel: ## Build Python binary distribution wheel package
	poetry build --format wheel

source: ## Build Python source distribution package
	poetry build --format sdist

test: ## Run the project testsuite(s)
	poetry run tox -r

docs: ## Build the documentation using Sphinx
	poetry run tox -e docs
