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

"""Observe social metadata and compare decoded card pixels."""

import hashlib
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from compatibility.checks import html, routes


def extract(site: Path) -> dict:
    pages = {}
    for route in routes(site):
        pages[route] = [
            [node["property"], node.get("content", "")]
            for node in html(site / route).select("head meta[property]")
            if node["property"].startswith(("og:", "twitter:", "x:"))
        ]
    cards = {}
    for path in sorted(site.rglob("*.png")):
        relative = path.relative_to(site).as_posix()
        if relative.startswith(("assets/images/social/", "assets/cards/")):
            with Image.open(path) as image:
                cards[relative] = list(image.size)
    return {"pages": pages, "cards": cards}


def pixels(path: Path) -> str:
    with Image.open(path) as image:
        return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def snapshot(site: Path, manifest: dict) -> dict:
    return {
        "pages": manifest["pages"],
        "cards": {name: pixels(site / name) for name in manifest["cards"]},
    }


def compare_cards(
    left: Path, right: Path, cards: dict, budgets: dict, differences: list[dict]
) -> dict:
    """A visual exception accepts one exact pair; all other cards keep their budget."""
    rules = {rule["path"]: rule for rule in differences}
    assert len(rules) == len(differences), "duplicate pixel exception"
    assert set(rules) <= cards.keys(), "expected pixel difference lost its card"
    assert set(budgets) <= cards.keys(), "pixel budget lost its card"
    results = {}
    for name in cards:
        with Image.open(left / name) as first, Image.open(right / name) as second:
            assert first.size == second.size, f"card dimensions differ: {name}"
            delta = ImageChops.difference(first.convert("RGB"), second.convert("RGB"))
            mean = sum(ImageStat.Stat(delta).mean) / 3
        budget = budgets.get(name, {"mean_rgb": 1})
        if name in budgets:
            assert budget.get("reason", "").strip(), "pixel budget needs a reason"
        accepted = mean <= budget["mean_rgb"]
        if name in rules:
            rule = rules[name]
            assert rule["reason"].strip(), "pixel exception needs a reason"
            actual = (pixels(left / name), pixels(right / name))
            expected = (rule["mkdocs"], rule["zensical"])
            assert actual == expected and expected[0] != expected[1], (
                f"expected pixel difference changed: {name}"
            )
            assert not accepted, f"resolved pixel exception must be removed: {name}"
            accepted = True
        results[name] = {
            "mean_rgb": round(mean, 6),
            "budget": budget["mean_rgb"],
            "accepted": accepted,
            "known_difference": name in rules,
        }
    return results
