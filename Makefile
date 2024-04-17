# SPDX-License-Identifier: Apache-2.0
# Based on code from https://github.com/bachya/simplisafe-python/blob/dev/Makefile

check_vulns:
	poetry run safety check

clean:
	rm -rf dist/ build/ docs/build/

init: setup_env
	poetry install --with dev

lint:
	poetry run ruff check

format:
	poetry run ruff format --check --diff 

docu:
	poetry run sphinx-build -M html docs/source/ docs/build/

setup_env:
	pipx install poetry
