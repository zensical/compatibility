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

"""Check that documented differences cannot mask unrelated regressions."""

import pytest

from compatibility.runner import check_build, compare, pointer


def test_json_pointer_preserves_empty_keys_and_escaped_routes():
    value = {"search": {"": ["COMPAT_HOME"], "guide/": ["COMPAT_GUIDE"]}}
    assert pointer(value, "/search/") == ["COMPAT_HOME"]
    assert pointer(value, "/search/guide~1/0") == "COMPAT_GUIDE"
    assert pointer(value, "") is value


RULE = {
    "path": "/page/title",
    "mkdocs": "Heading",
    "zensical": "Navigation label",
    "reason": "Zensical preserves an explicit navigation label.",
}


def test_documented_difference_preserves_other_regressions():
    left = {"page": {"title": "Heading", "url": "/guide/"}}
    right = {"page": {"title": "Navigation label", "url": "/missing/"}}
    difference = compare(left, right, [RULE])
    assert "/missing/" in difference
    assert left["page"]["title"] == "Heading"
    assert right["page"]["title"] == "Navigation label"


def test_only_the_exact_documented_pair_is_accepted():
    with pytest.raises(AssertionError, match="expected difference changed"):
        compare({"page": {"title": "Heading"}}, {"page": {"title": "Broken"}}, [RULE])


def test_resolved_difference_requires_removing_the_exception():
    with pytest.raises(AssertionError, match="expected difference changed"):
        compare({"page": {"title": "Heading"}}, {"page": {"title": "Heading"}}, [RULE])


def test_a_missing_field_cannot_pass_as_an_expected_difference():
    with pytest.raises(KeyError):
        compare({"page": {"title": "Heading"}}, {"page": {}}, [RULE])


def test_documented_missing_file_preserves_other_file_regressions():
    rule = {
        "path": "/files/internal.yml",
        "mkdocs": True,
        "zensical_missing": True,
        "reason": "Native does not publish internal YAML.",
    }
    difference = compare(
        {"files": {"internal.yml": True, "image.svg": True}}, {"files": {}}, [rule]
    )
    assert "image.svg" in difference


def test_a_resolved_missing_file_exception_fails():
    rule = {
        "path": "/files/internal.yml",
        "mkdocs": True,
        "zensical_missing": True,
        "reason": "Native does not publish internal YAML.",
    }
    with pytest.raises(AssertionError, match="expected difference changed"):
        compare(
            {"files": {"internal.yml": True}}, {"files": {"internal.yml": True}}, [rule]
        )


def test_one_known_extra_route_does_not_hide_another_missing_route():
    rule = {
        "path": "/routes",
        "mkdocs_only": "summary/index.html",
        "reason": "Oracle publishes a generated control file.",
    }
    difference = compare(
        {"routes": ["index.html", "guide/index.html", "summary/index.html"]},
        {"routes": ["index.html"]},
        [rule],
    )
    assert "guide/index.html" in difference


def test_resolved_extra_route_requires_reviewing_the_gap():
    rule = {
        "path": "/routes",
        "mkdocs_only": "summary/index.html",
        "reason": "Oracle publishes a generated control file.",
    }
    with pytest.raises(AssertionError, match="membership difference changed"):
        compare({"routes": ["index.html"]}, {"routes": ["index.html"]}, [rule])


def test_known_duplicate_count_preserves_unrelated_items_and_requires_review():
    rule = {
        "path": "/items",
        "member": "current",
        "mkdocs": 2,
        "zensical": 1,
        "reason": "Retained upstream feed duplicates a current item.",
    }
    difference = compare(
        {"items": ["current", "current", "other"]}, {"items": ["current"]}, [rule]
    )
    assert "other" in difference
    with pytest.raises(AssertionError, match="member counts changed"):
        compare({"items": ["current"]}, {"items": ["current"]}, [rule])


def test_known_native_failure_requires_the_specific_diagnostic(tmp_path):
    (tmp_path / "zensical.log").write_text("RuntimeError: unknown plugin\n")
    with pytest.raises(AssertionError, match="wrong reason"):
        check_build(
            {"exit_code": 1, "timed_out": False},
            "zensical",
            tmp_path,
            {"zensical": "failed to render social layout expression: undefined value"},
        )


def test_known_native_failure_requires_a_successful_oracle(tmp_path):
    with pytest.raises(AssertionError, match="mkdocs build failed"):
        check_build(
            {"exit_code": 1, "timed_out": False},
            "mkdocs",
            tmp_path,
            {"zensical": "undefined value"},
        )


def test_timeout_is_never_an_expected_rejection(tmp_path):
    with pytest.raises(AssertionError, match="timed out"):
        check_build(
            {"exit_code": None, "timed_out": True},
            "zensical",
            tmp_path,
            {"zensical": "undefined value"},
        )


def test_resolved_native_gap_fails_until_reviewed(tmp_path):
    with pytest.raises(AssertionError, match="did not reject"):
        check_build(
            {"exit_code": 0, "timed_out": False},
            "zensical",
            tmp_path,
            {"zensical": "undefined value"},
        )
