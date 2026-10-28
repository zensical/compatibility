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

"""Observe page descriptions and the CSV exported from final HTML."""

import csv
import json
from pathlib import Path

from compatibility.checks import html, routes


def extract(site: Path) -> dict:
    """Read metadata probes, head descriptions, and decoded CSV fields."""
    pages = {}
    for route in routes(site):
        soup = html(site / route)
        marker = soup.select_one("#compatibility-meta-descriptions")
        assert marker is not None, f"description metadata probe missing: {route}"
        metadata = json.loads(marker.get_text())
        pages[route] = {
            "metadata": metadata.get("description"),
            "head": [node.get("content") for node in soup.select('head meta[name="description"]')],
        }

    exported = None
    path = site / "meta-descriptions.csv"
    if path.is_file():
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.reader(stream))
        assert rows, "description CSV is empty"
        assert rows[0] == ["Page", "Meta description"], "invalid description CSV header"
        assert all(len(row) == 2 for row in rows[1:]), "invalid description CSV row"
        # Traversal order is excluded; duplicate rows, URLs, and field text are retained.
        exported = {"header": rows[0], "rows": sorted(rows[1:])}
    return {"pages": pages, "csv": exported}
