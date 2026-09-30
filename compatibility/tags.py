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

"""Observe hierarchical listings, tag targets, TOC and search inclusion."""

import json
import posixpath
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from compatibility.checks import html, routes


def extract(site: Path) -> dict:
    pages = {}
    for route in routes(site):
        soup = html(site / route)
        canonical = soup.select_one('link[rel="canonical"]')
        base = canonical["href"]

        def link(node, base=base):
            return {
                "title": node.get_text(" ", strip=True),
                "url": urljoin(base, node["href"]),
            }

        listings = {}
        listing_order = []
        for heading in soup.select(
            "article h1, article h2, article h3, article h4, article h5, article h6"
        ):
            tag = heading.select_one(".md-tag")
            if tag is None:
                continue
            listing = heading.find_next_sibling("ul")
            identifier = heading.get("id", "")
            key = f"{identifier}:{sum(name.startswith(identifier + ':') for name in listing_order)}"
            listing_order.append(key)
            listings[key] = {
                "level": int(heading.name[1]),
                "id": heading.get("id"),
                "tag": tag.get_text(" ", strip=True),
                "shadow": "md-tag-shadow" in tag.get("class", []),
                "layout": tag.get("data-layout"),
                "links": [link(node) for node in listing.select("a[href]")]
                if listing
                else [],
            }
        diagnostics = {}
        for name in soup.select(".tags-diagnostics dt"):
            body = name.find_next_sibling("dd")
            links = [link(node) for node in body.select("a[href]")]

            def rank(target, base=base):
                common = posixpath.commonpath(
                    [urlparse(base).path, urlparse(target["url"]).path]
                )
                return len(common)

            ranks = [rank(target) for target in links]
            assert ranks == sorted(ranks, reverse=True), (
                f"farther tag target takes precedence: {route}"
            )
            # Upstream iterates a set; equally close targets have no stable order.
            diagnostics[name.get_text(" ", strip=True)] = [
                {
                    "rank": score,
                    "links": sorted(
                        [target for target in links if rank(target) == score],
                        key=lambda target: (target["url"], target["title"]),
                    ),
                }
                for score in sorted(set(ranks), reverse=True)
            ]
        references = []
        for node in soup.select("nav.md-tags a[href]"):
            reference = link(node)
            groups = diagnostics.get(
                reference["title"],
                diagnostics.get(reference["title"] + " (shadow)", []),
            )
            nearest = (
                sorted({target["url"] for target in groups[0]["links"]})
                if groups
                else []
            )
            assert reference["url"] in nearest, (
                f"tag does not point to a nearest listing: {route}"
            )
            references.append({"title": reference["title"], "nearest_targets": nearest})
        pages[route] = {
            "listings": listings,
            "listing_order": listing_order,
            "references": references,
            "toc": [
                link(node) for node in soup.select("nav.md-nav--secondary a[href]")
            ],
            "diagnostics": diagnostics,
        }
    index = site / "search/search_index.json"
    if not index.is_file():
        index = site / "search.json"
    data = json.loads(index.read_text())
    catalog = " ".join(
        BeautifulSoup(item.get("text", ""), "html.parser").get_text(" ", strip=True)
        for item in data.get("docs", data.get("items", []))
        if not item["location"].split("#", 1)[0]
    )
    return {
        "pages": pages,
        "export": (site / "legacy-tags.json").exists(),
        "catalog_search_contains_guide": "Python language guide" in catalog,
    }
