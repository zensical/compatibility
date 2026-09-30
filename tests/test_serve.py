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

"""Metadata, exclusion, feeds and social cards update in retained servers."""

import shutil
from pathlib import Path

import pytest

from compatibility.runner import compare, pointer, write_json
from compatibility.serve import checkpoint, server
from compatibility.social import compare_cards


def test_publishing_server_lifecycle(pytestconfig, request):
    if not pytestconfig.getoption("--serve"):
        pytest.skip("enable --serve for retained HTTP server checks")
    builders, _ = request.getfixturevalue("builders")
    output = request.getfixturevalue("artifacts") / "serve/publishing"
    output.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1] / (
        "cases/combinations/publishing/exclude-meta-social-rss/project"
    )
    observations = {}
    for engine, python in builders.items():
        root = output / engine
        root.mkdir()
        project = root / "project"
        shutil.copytree(source, project)
        observations[engine] = {}
        with server(python, engine, project, root) as (base, process):

            def record(
                name,
                *,
                added=False,
                revised=False,
                deleted=False,
                engine=engine,
                root=root,
            ):
                observations[engine][name] = checkpoint(
                    base,
                    engine,
                    process,
                    root / name,
                    added=added,
                    revised=revised,
                    deleted=deleted,
                )

            record("00-cold")
            metadata = project / "docs/news/.meta.yml"
            metadata.write_text(
                metadata.read_text()
                .replace("Inherited headline", "Revised headline")
                .replace("2024-01-02", "2024-01-03")
                .replace("#123456", "#654321")
            )
            record("01-inherited-metadata", revised=True)
            page = project / "docs/news/second.md"
            page.write_text(
                "---\ndate: 2024-01-04\nupdated: 2024-01-04\n---\n# Another item\n\nCOMPAT_ADDED\n"
            )
            record("02-add-page", added=True, revised=True)
            page.unlink()
            record("03-delete-page", revised=True, deleted=True)
    reason = "Upstream RSS retains the old item after inherited metadata edits and retains a deleted page's item; native feeds contain only current published pages."
    for phase, expected in observations["mkdocs"].items():
        rules = []
        if phase != "00-cold":
            for name in expected["rss"]["files"]:
                collection = (
                    "/items"
                    if name.endswith(".json")
                    else "/document/children/0/children"
                )
                path = f"/rss/feeds/{name}" + collection
                cold = pointer(observations["mkdocs"]["00-cold"], path)
                revised = pointer(
                    observations["zensical"]["01-inherited-metadata"], path
                )
                added = pointer(observations["zensical"]["02-add-page"], path)
                if name.endswith(".xml"):
                    cold = [item for item in cold if item["tag"] == "item"]
                    revised = [item for item in revised if item["tag"] == "item"]
                    added = [
                        item
                        for item in added
                        if item["tag"] == "item"
                        and any(
                            field["tag"] == "link"
                            and field["text"].endswith("/second/")
                            for field in item["children"]
                        )
                    ]
                else:
                    added = [item for item in added if item["url"].endswith("/second/")]
                members = [(item, 1, 0) for item in cold]
                if phase in {"02-add-page", "03-delete-page"}:
                    members += [
                        (item, 3 if phase == "03-delete-page" else 2, 1)
                        for item in revised
                    ]
                if phase == "03-delete-page":
                    members += [(item, 1, 0) for item in added]
                rules += [
                    {
                        "path": path,
                        "member": item,
                        "mkdocs": first,
                        "zensical": second,
                        "reason": reason,
                    }
                    for item, first, second in members
                ]
        difference = compare(expected, observations["zensical"][phase], rules)
        (output / f"{phase}.diff").write_text(difference)
        assert not difference, f"serve compatibility regression; see {output / phase}"
        cards = expected["social"]["cards"]
        metrics = compare_cards(
            output / "mkdocs" / phase / "site",
            output / "zensical" / phase / "site",
            cards,
            {},
            [],
        )
        write_json(output / f"{phase}-pixels.json", metrics)
        assert all(card["accepted"] for card in metrics.values()), (
            "serve card pixels differ"
        )
        if rules:
            write_json(
                output / f"{phase}-accepted-differences.json",
                {"reason": reason, "differences": rules},
            )
