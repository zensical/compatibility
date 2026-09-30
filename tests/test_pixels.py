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

"""Visual allowances remain specific to the named card and exact pixel pair."""

import pytest
from PIL import Image

from compatibility import runner
from compatibility.social import compare_cards, pixels


def cards(tmp_path):
    left = tmp_path / "mkdocs"
    right = tmp_path / "zensical"
    for directory in (left, right):
        directory.mkdir()
    for name in ("edited.png", "other.png"):
        Image.new("RGB", (8, 8), "red").save(left / name)
        Image.new("RGB", (8, 8), "blue").save(right / name)
    return left, right


def test_pixel_exception_does_not_accept_a_different_card(tmp_path):
    left, right = cards(tmp_path)
    rule = {
        "path": "edited.png",
        "mkdocs": pixels(left / "edited.png"),
        "zensical": pixels(right / "edited.png"),
        "reason": "Known stale SVG.",
    }
    result = compare_cards(
        left, right, {"edited.png": [8, 8], "other.png": [8, 8]}, {}, [rule]
    )
    assert result["edited.png"]["accepted"]
    assert not result["other.png"]["accepted"]


def test_changed_pixel_exception_fails(tmp_path):
    left, right = cards(tmp_path)
    rule = {
        "path": "edited.png",
        "mkdocs": pixels(left / "edited.png"),
        "zensical": "incorrect",
        "reason": "Known stale SVG.",
    }
    with pytest.raises(AssertionError, match="pixel difference changed"):
        compare_cards(left, right, {"edited.png": [8, 8]}, {}, [rule])


def test_pixel_budget_applies_only_to_its_named_card(tmp_path):
    left, right = cards(tmp_path)
    budgets = {
        "edited.png": {"mean_rgb": 200, "reason": "Reviewed rasterization allowance."}
    }
    result = compare_cards(
        left, right, {"edited.png": [8, 8], "other.png": [8, 8]}, budgets, []
    )
    assert result["edited.png"]["accepted"]
    assert not result["other.png"]["accepted"]


def test_known_output_gap_in_multiple_checks_cannot_hide_bad_card_pixels(
    tmp_path, monkeypatch
):
    case = tmp_path / "case"
    (case / "project").mkdir(parents=True)
    output = tmp_path / "artifacts"
    output.mkdir()

    def fake_build(python, engine, project, phase, **options):
        site = project / "site"
        site.mkdir()
        (site / "index.html").write_text("<html><head></head><body>Test</body></html>")
        card = site / "assets/images/social/card.png"
        card.parent.mkdir(parents=True)
        Image.new("RGB", (8, 8), "red" if engine == "mkdocs" else "blue").save(card)
        return {"timed_out": False, "exit_code": 0}

    monkeypatch.setattr(runner, "build", fake_build)
    monkeypatch.setitem(
        runner.EXTRACTORS, "probe", lambda site: {"engine": site.parent.name}
    )
    spec = {
        "check": ["probe", "social"],
        "assertions": [{"path": "/social/cards", "count": 1}],
        "known_gap": "Known probe difference.",
        "differences": [
            {
                "path": "/probe/engine",
                "mkdocs": "mkdocs",
                "zensical": "zensical",
                "reason": "Known probe difference.",
            }
        ],
    }
    with pytest.raises(AssertionError, match="card pixels differ"):
        runner.run_case(
            case,
            spec,
            {"mkdocs": tmp_path / "python", "zensical": tmp_path / "python"},
            output,
        )
