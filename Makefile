# SPDX-License-Identifier: Apache-2.0
# Based on code from https://github.com/bachya/simplisafe-python/blob/dev/Makefile

bump:
	poetry run semantic-release release
	poetry run semantic-release changelog

check_vulns:
	poetry run safety check
clean:
	rm -rf dist/ build/ .egg sengledwifipy.egg-info/
init: setup_env
	poetry install

docstyle:
	poetry run pydocstyle sengledwifipy

docs: docstyle
	poetry export --dev --without-hashes -f requirements.txt --output docs/requirements.txt
	echo "sengledwifipy" >> docs/requirements.txt
	poetry run sphinx-build -b html docs docs/html
setup_env:
	pip install poetry
