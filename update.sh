#! /usr/bin/env bash

# SPDX-FileCopyrightText: 2023 Artemis Changelog Contributors
#
# SPDX-License-Identifier: EUPL-1.2

set -e

version=$1

if [[ -z "$version" ]]; then
    echo "Please provide the Artemis version for which the update is run as argument."
    exit 1
fi

poetry install
poetry run python ./artemis_changelog/main.py --output-dir=changelog

git add changelog/
git commit -m "update for version $version"

git push
git push github main
