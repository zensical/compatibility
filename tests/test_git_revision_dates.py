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

"""Check deterministic Git fixtures and observable revision date contracts."""

import shutil
from datetime import datetime

import pytest

from compatibility import git_history, rendering
from compatibility.runner import compare, mutate


def project(root):
    """Create a small source tree for a real local Git repository."""
    (root / "docs").mkdir(parents=True)
    (root / "docs/index.md").write_text("# Home\n\nOriginal content.\n", encoding="utf-8")
    return root


def history():
    """Describe two commits with fixed identities, messages, and dates."""
    return {"commits": [
        {"name": "created", "date": "2024-01-01T00:00:00+00:00"},
        {"name": "updated", "date": "2024-02-01T00:00:00+00:00", "path": "docs/index.md", "before": "Original content.", "after": "Updated content.", "tag": "v1"},
    ]}


def test_independent_copies_have_equal_commits_and_ignored_revision_files(tmp_path):
    left = project(tmp_path / "left")
    right = tmp_path / "right"
    shutil.copytree(left, right)
    settings = {**history(), "ignored_commits_file": ".git-blame-ignore-revs", "ignored_commits": ["updated"]}

    left_state = git_history.prepare(left, settings, mutate)
    right_state = git_history.prepare(right, settings, mutate)

    assert left_state == right_state
    assert datetime.fromisoformat(git_history.git(left, "log", "-1", "--format=%aI")) == datetime.fromisoformat("2024-02-01T00:00:00+00:00")
    assert left_state["commits"]["updated"][:12] in (left / ".git-blame-ignore-revs").read_text()
    assert git_history.git(left, "tag", "--points-at", "HEAD") == "v1"

    # A later build's site and cache files must not become committed inputs.
    (left / "site").mkdir()
    (left / "site/index.html").write_text("Generated output")
    (left / "docs/index.md").write_text("# A later source edit\n")
    git_history.advance(left, left_state, {"name": "later", "date": "2024-03-01T00:00:00+00:00"})

    assert "site/index.html" not in git_history.git(left, "ls-files").splitlines()


def test_shallow_history_deepens_without_moving_head(tmp_path):
    root = project(tmp_path / "project")
    state = git_history.prepare(root, {**history(), "shallow": 1}, mutate)
    head = git_history.git(root, "rev-parse", "HEAD")

    assert git_history.git(root, "rev-parse", "--is-shallow-repository") == "true"
    assert len(git_history.git(root, "log", "--format=%H", "--", "docs/index.md").splitlines()) == 1

    git_history.advance(root, state, {"deepen": True})

    assert git_history.git(root, "rev-parse", "HEAD") == head
    assert git_history.git(root, "rev-parse", "--is-shallow-repository") == "false"
    assert len(git_history.git(root, "log", "--format=%H", "--", "docs/index.md").splitlines()) == 2


def test_worktree_amend_and_checkout_are_real_git_operations(tmp_path):
    root = project(tmp_path / "project")
    state = git_history.prepare(root, {**history(), "worktree": True}, mutate)

    assert (root / ".git").is_file()
    assert git_history.git(root, "tag", "--points-at", "HEAD") == "v1"

    git_history.advance(root, state, {"name": "amended", "date": "2024-04-01T00:00:00+00:00", "amend": True})

    assert datetime.fromisoformat(git_history.git(root, "log", "-1", "--format=%aI")) == datetime.fromisoformat("2024-04-01T00:00:00+00:00")
    assert state["commits"]["amended"] != state["commits"]["updated"]

    git_history.advance(root, state, {"checkout": "created"})

    assert "Original content." in (root / "docs/index.md").read_text()


def test_git_fixture_validation_rejects_escaping_paths_and_ambiguous_dates(tmp_path):
    case = tmp_path / "case"
    project(case / "project")

    with pytest.raises(AssertionError, match="escapes project"):
        git_history.validate(case, {"git": {"commits": [{"name": "bad", "date": "2024-01-01T00:00:00+00:00", "files": ["../../outside"]}]}})

    with pytest.raises(AssertionError, match="explicit UTC offset"):
        git_history.validate(case, {"git": {"commits": [{"name": "bad", "date": "2024-01-01"}]}})


def test_date_extractor_retains_relative_attributes_and_requires_local_assets(tmp_path):
    (tmp_path / "js").mkdir()
    (tmp_path / "css").mkdir()
    (tmp_path / "js/timeago.min.js").write_text("/* Fixture script */")
    (tmp_path / "css/timeago.css").write_text("@media print { .timeago { display: none } .iso_date { display: inline } }")
    page = tmp_path / "index.html"
    page.write_text('''<link rel="stylesheet" href="css/timeago.css">
<span class="git-revision-date-localized-plugin git-revision-date-localized-plugin-timeago" title="February 2, 2024 12:34:56 UTC"><span class="timeago" datetime="2024-02-02T12:34:56+00:00" locale="en"></span></span>
<script src="js/timeago.min.js"></script>''')

    before = rendering.git_revision_dates(tmp_path)

    assert before["scripts"] == ["js/timeago.min.js"]
    assert before["pages"]["index.html"][0]["relative"] == [{"datetime": "2024-02-02T12:34:56+00:00", "locale": "en"}]

    # A wrong timestamp remains observable even with identical empty span text.
    page.write_text(page.read_text().replace("2024-02-02T", "2024-02-03T"))

    assert "datetime" in compare(before, rendering.git_revision_dates(tmp_path), [])

    (tmp_path / "js/timeago.min.js").unlink()

    with pytest.raises(AssertionError, match="revision asset missing"):
        rendering.git_revision_dates(tmp_path)
