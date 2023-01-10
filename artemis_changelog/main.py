# SPDX-FileCopyrightText: 2023 Artemis Changelog Contributors
#
# SPDX-License-Identifier: EUPL-1.2

import argparse
import datetime
import logging
import os.path
import re
import typing
from enum import Enum
from pathlib import Path
from typing import Iterable

import git
import more_itertools
import semver

if typing.TYPE_CHECKING:
    from git.objects.commit import Commit


class Sections(Enum):
    CONFIG = "Config"
    DATABASE = "Database"
    TEMPLATE = "Template"

    def path_pattern(self) -> str:
        match self:
            case Sections.CONFIG:
                return r"src/main/resources/config/.*\.yml$"
            case Sections.DATABASE:
                return r"src/main/resources/config/liquibase/.*"
            case Sections.TEMPLATE:
                return r"src/main/resources/templates/.*"


def fetch_repo(url: str, target_path: Path) -> git.Repo:
    if os.path.exists(target_path):
        repo = git.Repo(target_path)
        repo.remote().pull()
        return repo
    else:
        repo = git.Repo.clone_from(url, target_path)
        return repo


def get_release_tags(repo: git.Repo) -> list[tuple[semver.VersionInfo, git.Tag]]:
    return list(
        (semver.VersionInfo.parse(tag.name), tag)
        for tag in repo.tags
        if re.match(r"^\d+\.\d+\.\d+$", tag.name)
    )


def commits_between(a: git.Tag, b: git.Tag) -> set[str]:
    git_cmd = git.cmd.Git("artemis")
    output = str(git_cmd.execute(["git", "log", "--oneline", f"{a.name}..{b.name}"]))
    return set(line.split()[0] for line in output.splitlines())


def get_commits(latest_release: git.Tag, previous_release: git.Tag) -> Iterable[Commit]:
    yield latest_release.commit

    commits = commits_between(previous_release, latest_release)

    for commit_hash in commits:
        commit = latest_release.repo.commit(commit_hash)
        if commit == previous_release.commit:
            break

        yield commit


def get_changed_paths(commit: Commit) -> Iterable[str]:
    for diff in commit.diff(commit.parents):
        yield diff.a_path
        yield diff.b_path


def collect_changed_paths(
    latest_release: git.Tag, previous_release: git.Tag
) -> dict[Sections, set[Commit]]:
    changed_paths: dict[Sections, set[Commit]] = {
        Sections.CONFIG: set(),
        Sections.DATABASE: set(),
        Sections.TEMPLATE: set(),
    }

    logging.info("Comparing versions %s and %s...", previous_release, latest_release)

    for commit in get_commits(latest_release, previous_release):
        for changed_path in get_changed_paths(commit):
            for section in [Sections.CONFIG, Sections.DATABASE, Sections.TEMPLATE]:
                if re.match(section.path_pattern(), changed_path):
                    changed_paths[section].add(commit)

    return changed_paths


def format_commit_message(commit: Commit) -> str:
    return str(commit.message).splitlines()[0].strip().replace("]", "\\]")


def _licence_header() -> str:
    # avoid reuse being overly eager to parse the strings as licence headers
    prefix1 = "SPDX-FileCopyrightText"
    prefix2 = "SPDX-License-Identifier"

    year = datetime.date.today().year

    return (
        f"// {prefix1}: {year} Artemis Changelog Contributors\n"
        "//\n"
        f"// {prefix2}: CC-BY-SA-4.0"
    )


def format_result(
    latest_release: git.Tag,
    previous_release: git.Tag,
    result: dict[Sections, set[Commit]],
) -> str:
    formatted = _licence_header()
    formatted += f"\n\n= {previous_release.name} -- {latest_release.name}\n\n"

    formatted += f"link:https://github.com/ls1intum/Artemis/releases/tag/{latest_release.name}[Full Release Notes]\n\n"

    for section, commits in result.items():
        if len(commits) == 0:
            continue

        formatted += f"== {section.value}\n\n"
        for commit in commits:
            formatted += f"* link:https://www.github.com/ls1intum/Artemis/commit/{commit}[{format_commit_message(commit)}]\n"
        formatted += "\n\n"

    if sum(map(len, result.values())) == 0:
        formatted += "No relevant changes.\n"

    return formatted


def path_from_version(version: semver.VersionInfo) -> Path:
    def format_number(n: int) -> str:
        return f"{n:02}"

    return Path(
        format_number(version.major),
        format_number(version.minor),
        f"{format_number(version.patch)}.adoc",
    )


def create_changelogs(
    output_dir: Path, tags: Iterable[tuple[semver.VersionInfo, git.Tag]]
) -> None:
    for after, before in more_itertools.sliding_window(tags, 2):
        output_path = output_dir / path_from_version(after[0])
        if not os.path.exists(output_path):
            os.makedirs(output_path.parent, exist_ok=True)
            changed_paths = collect_changed_paths(after[1], before[1])
            result = format_result(after[1], before[1], changed_paths)
            with open(output_path, "w") as f:
                f.write(result)


def create_index(
    output_dir: Path, tags: list[tuple[semver.VersionInfo, git.Tag]]
) -> None:
    output_path = output_dir / "index.adoc"

    with open(output_path, "w") as f:
        f.write(_licence_header())
        f.write("\n\n= Artemis Changelog\n")
        f.write(":toc: left\n\n")
        f.write(":leveloffset: +1\n\n")

        for version, _ in tags[:-1]:
            version_path = path_from_version(version)
            f.write(f"include::{version_path}[]\n\n")


def main(output_dir: Path) -> None:
    target_path = Path("artemis")
    repo = fetch_repo("https://www.github.com/ls1intum/artemis.git", target_path)
    tags = get_release_tags(repo)
    tags.sort(key=lambda t: t[0], reverse=True)

    tags = tags[:20]

    create_changelogs(output_dir, tags)
    create_index(output_dir, tags)


def argparser() -> argparse.ArgumentParser:
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--output-dir", type=Path, required=True)
    return argparser


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s|%(name)s|%(levelname)s|%(message)s"
    )
    args = argparser().parse_args()
    main(args.output_dir)
