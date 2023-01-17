# SPDX-FileCopyrightText: 2023 Artemis Changelog Contributors
#
# SPDX-License-Identifier: EUPL-1.2

PROJECT=artemis_changelog

.PHONY: generate-changelog
generate-changelog:
	poetry run python ./artemis_changelog/main.py --output-dir=changelog

.PHONY: format
format:
	poetry run isort .
	poetry run black .

.PHONY: mypy
mypy:
	poetry run mypy $(PROJECT) tests

.PHONY: ruff
ruff:
	poetry run ruff $(PROJECT) tests

.PHONY: reuse
reuse:
	poetry run reuse lint

.PHONY: check
check: format mypy ruff reuse
