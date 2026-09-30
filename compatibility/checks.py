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

"""Observe generated files without importing either generator."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def html(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def routes(site: Path) -> list[str]:
    return sorted(
        path.relative_to(site).as_posix()
        for path in site.rglob("*.html")
        if path.name != "404.html"
    )


def redirects(site: Path) -> dict:
    pages = {}
    for route in routes(site):
        soup = html(site / route)
        refresh = soup.find(
            "meta", attrs={"http-equiv": re.compile("refresh", re.IGNORECASE)}
        )
        if refresh is None:
            continue
        canonical = soup.select_one('link[rel="canonical"]')
        assert canonical is not None, f"redirect lacks canonical URL: {route}"
        scripts = "\n".join(script.get_text() for script in soup.find_all("script"))
        pages[route] = {
            "canonical": canonical.get("href"),
            "refresh": refresh.get("content"),
            "forwards_fragment": "location.hash" in scripts,
        }
    return {"routes": routes(site), "redirects": pages}


def navigation(site: Path) -> dict:
    soup = html(site / "index.html")
    nav = soup.select_one("nav.md-nav--primary")
    assert nav is not None, "primary navigation is missing"
    canonical = soup.select_one('link[rel="canonical"]')
    base = canonical["href"] if canonical else "https://example.com/"

    def items(container) -> list[dict]:
        listing = container.find("ul", recursive=False)
        if listing is None:
            return []
        result = []
        for entry in listing.find_all("li", recursive=False):
            link = entry.find("a", recursive=False)
            wrapper = entry.find("div", recursive=False)
            if link is None and wrapper is not None:
                link = wrapper.find("a", recursive=False)
            label = link or entry.find("label", recursive=False)
            assert label is not None, "navigation entry lacks a label"
            item = {"title": label.get_text(" ", strip=True)}
            if link is not None:
                item["url"] = urljoin(base, link.get("href", ""))
            child = entry.find("nav", recursive=False)
            if child is not None:
                children = items(child)
                if children:
                    item["children"] = children
            result.append(item)
        return result

    return {"routes": routes(site), "navigation": items(nav)}


def _xml(element: ET.Element) -> dict:
    # Only channel-level build dates and generator identify the build itself.
    # Item publication dates, content, order, and attributes remain observable.
    children = [
        _xml(child)
        for child in element
        if not (
            element.tag == "channel"
            and child.tag in {"lastBuildDate", "pubDate", "generator"}
        )
        and not (element.tag == "item" and child.tag == "enclosure")
    ]
    if element.tag in {"channel", "item"}:
        # RSS field order is irrelevant. Stable sorting keeps repeated items
        # and categories in their original semantic order.
        children.sort(key=lambda child: child["tag"])
    value = {
        "tag": element.tag,
        "attributes": dict(sorted(element.attrib.items())),
        "text": (element.text or "").strip(),
        "children": children,
    }
    if element.tag == "item":
        # Keep media fields separate so their absence cannot shift pointers to
        # descriptions, dates or links. Repeated enclosures retain their order.
        value["enclosures"] = [
            _xml(child) for child in element if child.tag == "enclosure"
        ]
    return value


def rss(site: Path) -> dict:
    feeds = {}
    for path in sorted(site.glob("*.xml")):
        if path.name == "sitemap.xml":
            continue
        stylesheet = re.search(
            r'<\?xml-stylesheet\s+[^?]*href="([^"]*)"', path.read_text("utf-8")
        )
        feeds[path.name] = {
            "stylesheet": stylesheet.group(1) if stylesheet else None,
            "document": _xml(ET.parse(path).getroot()),
        }
    for path in sorted(site.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and str(value.get("version", "")).startswith(
            "https://jsonfeed.org/version/"
        ):
            feeds[path.name] = value
    for path in sorted(site.glob("*.xsl")):
        feeds[path.name] = _xml(ET.parse(path).getroot())
    return {"files": sorted(feeds), "feeds": feeds}


def meta(site: Path) -> dict:
    pages = {}
    extends = {}
    for route in routes(site):
        marker = html(site / route).select_one("#compatibility-meta")
        assert marker is not None, f"metadata probe missing: {route}"
        value = json.loads(marker.get_text())
        # Observe the private marker separately so its exact intentional omission
        # cannot hide a difference in public page metadata.
        extends[route] = value.pop("__extends", [])
        pages[route] = value
    return {"pages": pages, "extends": extends}


CHECKS = {"redirects": redirects, "navigation": navigation, "rss": rss, "meta": meta}
