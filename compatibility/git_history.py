# Copyright (c) 2026 Zensical and contributors

# SPDX-License-Identifier: MIT
# All contributions are certified under the DCO

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""Prepare deterministic Git history for independent public CLI builds."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def local(project: Path, name: str) -> Path:
    """Resolve one fixture path without escaping its copied project."""
    path = project / name
    assert path.resolve().is_relative_to(project.resolve()), "Git fixture path escapes project"
    return path


def git(project: Path, *args: str, date: str | None = None) -> str:
    """Run fixed Git operations independently of the user's Git configuration."""
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0", GIT_AUTHOR_NAME="Compatibility Writer", GIT_AUTHOR_EMAIL="writer@example.test", GIT_COMMITTER_NAME="Compatibility Builder", GIT_COMMITTER_EMAIL="builder@example.test")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    command = ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", f"core.hooksPath={os.devnull}", "-c", "core.autocrlf=false", "-C", str(project), *args]
    result = subprocess.run(command, env=env, text=True, encoding="utf-8", capture_output=True, timeout=30, check=False)
    assert result.returncode == 0, f"Git fixture failed: {args}\n{result.stdout}\n{result.stderr}"
    return result.stdout.strip()


def validate(case: Path, spec: dict) -> None:
    """Validate declarative history and mutations before running either builder."""
    settings = spec.get("git")
    if settings is None:
        assert not any("git" in step for step in spec.get("steps", [])), "Git steps require initial Git settings"
        return
    assert isinstance(settings, dict), "git must be a mapping"
    _validate_repository(case / "project", settings)
    for step in spec.get("steps", []):
        action = step.get("git", {})
        if "date" in action:
            _validate_commit(case / "project", action)
        assert set(action) <= {"name", "date", "message", "files", "move", "tag", "amend", "checkout", "deepen"}, "unknown Git step option"


def _validate_repository(project: Path, settings: dict) -> None:
    assert set(settings) <= {"commits", "ignored_commits_file", "ignored_commits", "shallow", "worktree", "repositories", "missing"}, "unknown Git fixture option"
    names = [commit["name"] for commit in settings.get("commits", [])]
    assert len(names) == len(set(names)), "Git commit names must be unique"
    for commit in settings.get("commits", []):
        _validate_commit(project, commit)
    for name in settings.get("ignored_commits", []):
        assert name in names, f"unknown ignored commit: {name}"
    if settings.get("ignored_commits"):
        local(project, settings["ignored_commits_file"])
    if "shallow" in settings:
        assert isinstance(settings["shallow"], int) and settings["shallow"] > 0, "shallow depth must be positive"
        assert not settings.get("worktree"), "worktree and shallow setup must be separate cases"
    for name, nested in settings.get("repositories", {}).items():
        _validate_repository(local(project, name), nested)


def _validate_commit(project: Path, commit: dict) -> None:
    stamp = datetime.fromisoformat(commit["date"])
    assert stamp.utcoffset() is not None, "Git dates need an explicit UTC offset"
    assert commit.get("name"), "Git commits need stable names"
    for name in commit.get("files", ["."]):
        local(project, name)
    for source, destination in commit.get("move", {}).items():
        local(project, source)
        local(project, destination)


def prepare(project: Path, settings: dict | None, mutate) -> dict:
    """Create equal commit objects in the two independently copied projects."""
    if settings is None:
        return {}
    if settings.get("missing"):
        # Discovery of the suite's own checkout is prevented by a broken Git
        # boundary when artifacts are written below that checkout.
        (project / ".git").write_text("gitdir: .compat-missing-git\n", encoding="utf-8")
        return {}
    git(project, "init", "--quiet", "--initial-branch=main", "--object-format=sha1", "--template=")
    git(project, "config", "core.autocrlf", "false")
    git(project, "config", "core.filemode", "false")
    state = {"commits": {}}
    for commit in settings.get("commits", []):
        mutate(project, commit)
        advance(project, state, commit)
    if settings.get("shallow") or settings.get("worktree"):
        origin = project.with_name(project.name + "-git-origin")
        git(project.parent, "clone", "--quiet", "--bare", str(project), str(origin))
        backup = project.with_name(project.name + "-git-inputs")
        project.rename(backup)
        if settings.get("worktree"):
            git(origin, "worktree", "add", "--quiet", "--detach", str(project), "HEAD")
        else:
            git(project.parent, "clone", "--quiet", f"--depth={settings['shallow']}", origin.as_uri(), str(project))
        shutil.copytree(backup, project, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
        shutil.rmtree(backup)
    exclude = Path(git(project, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"))
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("/site/\n/.cache/\n", encoding="utf-8")
    if settings.get("ignored_commits_file"):
        path = local(project, settings["ignored_commits_file"])
        path.write_text("# Fixture formatting commits\n\n" + "".join(f"{state['commits'][name][:12]} # {name}\n" for name in settings.get("ignored_commits", [])), encoding="utf-8")
    for name, nested in settings.get("repositories", {}).items():
        prepare(local(project, name), nested, mutate)
    return state


def advance(project: Path, state: dict, action: dict) -> None:
    """Apply one bounded history mutation to a copied fixture repository."""
    if action.get("deepen"):
        git(project, "fetch", "--quiet", "--unshallow")
    if "checkout" in action:
        target = state["commits"][action["checkout"]]
        git(project, "checkout", "--quiet", "--detach", target)
    for source, destination in action.get("move", {}).items():
        local(project, destination).parent.mkdir(parents=True, exist_ok=True)
        git(project, "mv", "--", str(local(project, source)), str(local(project, destination)))
    if "date" in action:
        git(project, "add", "--all", "--", *action.get("files", ["."]))
        args = ["commit", "--quiet", "--message", action.get("message", action["name"])]
        if action.get("amend"):
            args.extend(["--amend", "--reset-author"])
        git(project, *args, date=action["date"])
        state["commits"][action["name"]] = git(project, "rev-parse", "HEAD")
    if "tag" in action:
        git(project, "tag", "--", action["tag"])
