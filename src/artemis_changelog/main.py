# SPDX-FileCopyrightText: 2023 Artemis Changelog Contributors
#
# SPDX-License-Identifier: EUPL-1.2

import argparse
import dataclasses
import logging
import re
from collections.abc import Generator, Iterable
from enum import Enum
from pathlib import Path

import git
import more_itertools
import semver
from git.objects.commit import Commit
from git.cmd import Git
from jinja2 import Environment, PackageLoader, Template, select_autoescape


class Sections(Enum):
    CONFIG = "Config"
    DATABASE = "Database"
    DOCKER = "Docker"
    TEMPLATE = "Template"

    def path_pattern(self) -> str:
        match self:
            case Sections.CONFIG:
                return r"src/main/resources/config/.*\.yml$"
            case Sections.DATABASE:
                return r"src/main/resources/config/liquibase/.*"
            case Sections.DOCKER:
                return r"docker/.*"
            case Sections.TEMPLATE:
                return r"src/main/resources/templates/.*"

    def __str__(self) -> str:
        return self.value


def fetch_repo(url: str, target_path: Path) -> git.Repo:
    if target_path.exists():
        repo = git.Repo(target_path)
        repo.remote().pull()
        return repo

    return git.Repo.clone_from(url, target_path)


def get_release_tags(repo: git.Repo) -> list[tuple[semver.VersionInfo, git.Tag]]:
    return [
        (semver.VersionInfo.parse(tag.name), tag)
        for tag in repo.tags
        if re.match(r"^\d+\.\d+\.\d+$", tag.name)
    ]


def commits_between(a: git.Tag, b: git.Tag) -> set[str]:
    git_cmd = Git("artemis")
    output = str(git_cmd.execute(["git", "log", "--oneline", f"{a.name}..{b.name}"]))
    return {line.split()[0] for line in output.splitlines()}


def get_commits(
    latest_release: git.Tag, previous_release: git.Tag
) -> Generator[Commit, None, None]:
    yield latest_release.commit

    commits = commits_between(previous_release, latest_release)

    for commit_hash in commits:
        commit = latest_release.repo.commit(commit_hash)
        if commit == previous_release.commit:
            break

        yield commit


def get_changed_paths(commit: Commit) -> Generator[str, None, None]:
    for diff in commit.diff(commit.parents):
        yield diff.a_path
        yield diff.b_path


def collect_changed_paths(
    latest_release: git.Tag, previous_release: git.Tag
) -> dict[Sections, set[Commit]]:
    changed_paths: dict[Sections, set[Commit]] = {
        Sections.CONFIG: set(),
        Sections.DATABASE: set(),
        Sections.DOCKER: set(),
        Sections.TEMPLATE: set(),
    }

    logging.info("Comparing versions %s and %s...", previous_release, latest_release)

    for commit in get_commits(latest_release, previous_release):
        for changed_path in get_changed_paths(commit):
            for section in [
                Sections.CONFIG,
                Sections.DATABASE,
                Sections.DOCKER,
                Sections.TEMPLATE,
            ]:
                if re.match(section.path_pattern(), changed_path):
                    changed_paths[section].add(commit)

    return changed_paths


def path_from_version(version: semver.VersionInfo) -> Path:
    def format_number(n: int) -> str:
        return f"{n:02}"

    return Path(
        format_number(version.major),
        format_number(version.minor),
        f"{format_number(version.patch)}.adoc",
    )


@dataclasses.dataclass
class Release:
    version: semver.VersionInfo
    changes: dict[Sections, set[Commit]]


def create_changelogs(
    template: Template,
    output_dir: Path,
    tags: Iterable[tuple[semver.VersionInfo, git.Tag]],
) -> None:
    for after, before in more_itertools.sliding_window(tags, 2):
        output_path = output_dir / path_from_version(after[0])
        if not output_path.exists():
            output_path.parent.mkdir(exist_ok=True, parents=True)
            changed_paths = collect_changed_paths(after[1], before[1])
            release = Release(after[0], changed_paths)

            with output_path.open("w") as f:
                f.write(template.render(release=release))


def create_index(
    template: Template, output_dir: Path, tags: list[tuple[semver.VersionInfo, git.Tag]]
) -> None:
    output_path = output_dir / "index.adoc"
    versions = [t[0] for t in tags[:-1]]

    with output_path.open("w") as f:
        f.write(template.render(releases=versions))


def main(output_dir: Path) -> None:
    env = Environment(
        loader=PackageLoader("artemis_changelog"),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    target_path = Path("artemis")
    repo = fetch_repo("https://www.github.com/ls1intum/artemis.git", target_path)
    tags = get_release_tags(repo)
    tags.sort(key=lambda t: t[0], reverse=True)

    tags = tags[:20]

    changelog_template = env.get_template("release_notes.adoc.jinja2")
    create_changelogs(changelog_template, output_dir, tags)

    index_template = env.get_template("index.adoc.jinja2")
    create_index(index_template, output_dir, tags)


def _arg_parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--output-dir", type=Path, required=True)
    return arg_parser


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s|%(name)s|%(levelname)s|%(message)s"
    )
    args = _arg_parser().parse_args()
    main(args.output_dir)
