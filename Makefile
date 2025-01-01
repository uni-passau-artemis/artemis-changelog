# SPDX-FileCopyrightText: 2023 Artemis Changelog Contributors
#
# SPDX-License-Identifier: EUPL-1.2

PROJECT=src

.PHONY: generate-changelog
generate-changelog:
	uv run python ./src/artemis_changelog/main.py --output-dir=changelog

.PHONY: format
format:
	uv run isort $(PROJECT) tests
	uv run ruff format $(PROJECT) tests

.PHONY: mypy
mypy:
	uv run mypy $(PROJECT) tests

.PHONY: pyre
pyre:
	uv run pyre

.PHONY: ruff
ruff:
	uv run ruff check $(PROJECT) tests

.PHONY: reuse
reuse:
	uv run reuse lint

.PHONY: check
check: format mypy pyre ruff reuse
