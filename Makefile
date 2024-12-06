# SPDX-FileCopyrightText: 2023 Artemis Changelog Contributors
#
# SPDX-License-Identifier: EUPL-1.2

PROJECT=src

.PHONY: generate-changelog
generate-changelog:
	poetry run python ./src/artemis_changelog/main.py --output-dir=changelog

.PHONY: format
format:
	poetry run isort $(PROJECT) tests
	poetry run ruff format $(PROJECT) tests

.PHONY: mypy
mypy:
	poetry run mypy $(PROJECT) tests

.PHONY: pyre
pyre:
	poetry run pyre

.PHONY: ruff
ruff:
	poetry run ruff check $(PROJECT) tests

.PHONY: reuse
reuse:
	poetry run reuse lint

.PHONY: check
check: format mypy pyre ruff reuse
