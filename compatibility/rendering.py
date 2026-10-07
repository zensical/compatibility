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

"""Observe Markdown transformations and plugin-generated artifacts."""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString
from markdown import markdown

from compatibility.checks import html, routes


def content(site: Path) -> dict:
    """Read rendered text, code, tables, and callout semantics from each page."""
    pages = {}
    for route in routes(site):
        article = html(site / route).select_one("article.md-content__inner")
        assert article is not None, f"missing article: {route}"

        # Theme heading controls are excluded from the authored content.
        for control in article.select(".headerlink, .md-content__button"):
            control.decompose()
        alerts = []
        for node in article.select(".admonition, details"):
            title = node.select_one(".admonition-title, summary")
            alerts.append({
                "kind": node.name,
                "classes": sorted(node.get("class", [])),
                "title": title.get_text(" ", strip=True) if title else None,
                "text": node.get_text(" ", strip=True),
                "open": node.has_attr("open"),
            })

        pages[route] = {
            "text": article.get_text(" ", strip=True),
            "headings": [{"level": node.name, "id": node.get("id"), "text": node.get_text(" ", strip=True)} for node in article.select("h1, h2, h3, h4, h5, h6")],
            "code": [node.get_text() for node in article.select("pre code")],
            "tables": [[[cell.get_text(" ", strip=True) for cell in row.select("th, td")] for row in table.select("tr")] for table in article.select("table")],
            "alerts": alerts,
            "quotes": [node.get_text(" ", strip=True) for node in article.select("blockquote")],
        }
    return pages


def lightbox(site: Path) -> dict:
    """Read image links and lightbox attributes without running JavaScript."""
    pages = {}
    for route in routes(site):
        soup = html(site / route)
        images = []
        for node in soup.select("article img"):
            anchor = node.find_parent("a")
            images.append({
                "src": node.get("src"),
                "alt": node.get("alt"),
                "title": node.get("title"),
                "classes": sorted(node.get("class", [])),
                "link": dict(sorted(anchor.attrs.items())) if anchor else None,
            })
        pages[route] = images
    return pages


def llmstxt(site: Path) -> dict:
    """Compare Markdown meaning while preserving structure, links, and code."""
    files = sorted({*site.rglob("*.md"), *site.rglob("*.txt")})
    outputs = {}

    def tree(node, preformatted=False):
        if isinstance(node, NavigableString):
            return str(node) if preformatted else re.sub(r"\s+", " ", str(node))
        return {
            "tag": node.name,
            "attributes": dict(sorted(node.attrs.items())),
            "children": [tree(child, preformatted or node.name == "pre") for child in node.children if node.name not in {"ul", "ol", "table", "thead", "tbody", "tfoot", "tr", "blockquote", "div"} or not isinstance(child, NavigableString) or child.strip()],
        }

    for path in files:
        soup = BeautifulSoup(markdown(path.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"]), "html.parser")
        outputs[path.relative_to(site).as_posix()] = {
            "text": soup.get_text(" ", strip=True),
            "structure": [tree(node) for node in soup.children if not isinstance(node, NavigableString) or node.strip()],
        }
    return outputs


def offline(site: Path) -> dict:
    """Check offline search data and worker-shim references in generated pages."""
    script = site / "search/search_index.js"
    index_path = site / "search/search_index.json"
    if (site / "search.js").is_file():
        assert not script.is_file(), "multiple offline search indexes were emitted"
        script = site / "search.js"
        index_path = site / "search.json"
    if script.is_file():
        source = script.read_text(encoding="utf-8")
        prefix = "var __index = "
        assert source.startswith(prefix), "offline search index lacks its assignment"
        inline = json.loads(source[len(prefix):].rstrip(";\n "))
        index = json.loads(index_path.read_text(encoding="utf-8"))
        assert inline == index, "offline search data differs from the JSON index"
    return {
        "inline_search": script.is_file(),
        "shims": {route: [node["src"] for node in html(site / route).select("script[src]") if "iframe-worker" in node["src"]] for route in routes(site)},
    }
