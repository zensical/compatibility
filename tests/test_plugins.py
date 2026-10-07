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

"""Every case is a complete pair of builds, followed by observable contracts."""

import json
from pathlib import Path

import pytest

from compatibility.runner import discover, run_case, validate_case

ROOT = Path(__file__).resolve().parents[1]

# The published list is supplemented by the two requested branch additions.
SUPPORTED_PLUGINS = {
    "api-autonav", "autorefs", "awesome-nav", "blog", "callouts", "exclude",
    "gh-admonitions", "glightbox", "literate-nav", "llmstxt", "macros",
    "markdown-exec", "markdownextradata", "meta", "mike", "minify",
    "mkdocs-audio", "mkdocs-autoapi", "mkdocs-nav-weight", "mkdocs-video",
    "mkdocstrings", "offline", "redirects", "rss", "search", "section-index",
    "social", "table-reader", "tags",
}


def test_supported_plugins_have_successful_output_contracts():
    # API generators are covered with their required mkdocstrings renderer.
    covered = set()
    for case in discover(ROOT / "cases", combinations=True):
        spec = json.loads((case / "case.json").read_text(encoding="utf-8"))
        if spec.get("assertions") and not spec.get("failure"):
            covered.update(plugin.removeprefix("material/") for plugin in spec["plugins"])

    assert SUPPORTED_PLUGINS <= covered, f"plugins without output contracts: {sorted(SUPPORTED_PLUGINS - covered)}"


def test_compatibility(case, builders, artifacts):
    spec = validate_case(case, ROOT / "cases")
    output = artifacts / case.relative_to(ROOT / "cases")
    output.mkdir(parents=True)
    run_case(case, spec, builders[0], output)
    if set(spec.get("failure", {})) == {"zensical"}:
        # Only mark the gap after the successful oracle output and exact native
        # rejection have been validated. An unrelated failure remains a failure.
        pytest.xfail(spec["reason"])
    gaps = [
        spec.get("known_gap"),
        *(step.get("known_gap") for step in spec.get("steps", [])),
    ]
    if any(gaps):
        # Exact field pairs and all other manifests, assertions, pixels and
        # mutation contracts must pass before reporting a known output gap.
        pytest.xfail(next(gap for gap in gaps if gap))
