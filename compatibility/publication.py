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

"""Observe published URLs, search membership and cross-reference artifacts."""

import json
import re
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment

from compatibility.checks import html, routes


def publication(site: Path) -> dict:
    canonicals = {}
    probes = {}
    comments = {}
    for route in routes(site):
        soup = html(site / route)
        if soup.select_one('meta[http-equiv="refresh"]'):
            continue
        canonical = soup.select_one('link[rel="canonical"]')
        assert canonical is not None, f"missing canonical: {route}"
        canonicals[route] = canonical["href"]
        probes[route] = {
            node["data-compat-probe"]: node.get_text()
            for node in soup.select("[data-compat-probe]")
        }
        comments[route] = sorted(
            str(node).strip()
            for node in soup.find_all(string=lambda node: isinstance(node, Comment))
            if "COMPAT_" in str(node)
        )
    locations = sorted(
        node.text
        for node in ET.parse(site / "sitemap.xml").iter()
        if node.tag.rsplit("}", 1)[-1] == "loc"
    )
    search = site / "search/search_index.json"
    if not search.is_file():
        search = site / "search.json"
    records = []
    if search.is_file():
        data = json.loads(search.read_text())
        records = data.get("docs", data.get("items", []))
    # Search engines split documents differently; compare page membership and
    # explicit fixture tokens, retaining per-page content coverage.
    indexed = {}
    for record in records:
        location = record["location"].split("#", 1)[0]
        text = BeautifulSoup(record.get("text", ""), "html.parser").get_text(" ")
        indexed.setdefault(location, set()).update(
            re.findall(r"\bCOMPAT_[A-Z_0-9]+\b", text)
        )
    return {
        "routes": routes(site),
        "canonicals": canonicals,
        "sitemap": locations,
        "search": {name: sorted(tokens) for name, tokens in sorted(indexed.items())},
        "probes": probes,
        "probe_comments": comments,
    }


def references(site: Path) -> dict:
    pages = {}
    for route in routes(site):
        soup = html(site / route)
        canonical = soup.select_one('link[rel="canonical"]')
        base = canonical["href"] if canonical else "https://example.test/"
        main = soup.select_one("article.md-content__inner")
        links = []
        for node in main.select("a.autorefs, a.compat-link") if main else []:
            links.append(
                {
                    "text": node.get_text(" ", strip=True),
                    "url": urljoin(base, node.get("href", "")),
                    "title": node.get("title"),
                    "preview": node.has_attr("data-preview"),
                }
            )
        pages[route] = {
            "links": links,
            "objects": sorted({node["id"] for node in soup.select(".doc-heading[id]")}),
            "content_tokens": sorted(
                set(
                    re.findall(
                        r"\bCOMPAT_[A-Z_0-9]+\b", main.get_text(" ") if main else ""
                    )
                )
            ),
            "unresolved": len(soup.select("autoref, [data-autorefs-identifier]")),
        }
    inventory = {}
    path = site / "objects.inv"
    if path.is_file():
        header = path.read_bytes().split(b"\n", 4)
        assert len(header) == 5 and header[0] == b"# Sphinx inventory version 2", (
            "invalid inventory"
        )
        for line in zlib.decompress(header[4]).decode().splitlines():
            name, domain, _priority, uri, display = line.split(maxsplit=4)
            if uri.endswith("$"):
                uri = uri[:-1] + name
            inventory[name] = {"domain": domain, "uri": uri, "display": display}
    return {"pages": pages, "inventory": inventory}


def tag_content(site: Path) -> dict:
    pages = {}
    for route in routes(site):
        soup = html(site / route)
        canonical = soup.select_one('link[rel="canonical"]')
        base = canonical["href"] if canonical else "https://example.test/"
        pages[route] = {
            "headings": [
                {
                    "id": node.get("id"),
                    "tag": node.select_one(".md-tag").get_text(" ", strip=True),
                }
                for node in soup.select(
                    "article h1, article h2, article h3, article h4, article h5, article h6"
                )
                if node.select_one(".md-tag")
            ],
            "references": [
                {
                    "tag": node.get_text(" ", strip=True),
                    "url": urljoin(base, node.get("href", "")),
                }
                for node in soup.select("nav.md-tags a[href]")
            ],
        }
    return pages
