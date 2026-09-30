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

"""Observe search sections and validate their published link targets."""

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from compatibility.checks import html, routes


def index(site: Path) -> dict | None:
    for name in ("search/search_index.json", "search.json"):
        path = site / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def records(site: Path) -> list[dict]:
    data = index(site)
    if data is None:
        return []
    result = data.get("docs", data.get("items", []))
    pages = {}
    for record in result:
        location = record["location"]
        url = urlsplit(location)
        assert not url.scheme and not url.netloc and not url.query, (
            f"unexpected search location: {location}"
        )
        route = unquote(url.path)
        if not route or route.endswith("/"):
            route += "index.html"
        path = site / route
        assert path.resolve().is_relative_to(site.resolve()), (
            f"search target escapes site: {location}"
        )
        assert path.is_file(), f"search target missing: {location}"
        if url.fragment:
            soup = pages.setdefault(route, None)
            if soup is None:
                pages[route] = soup = html(path)
            fragment = unquote(url.fragment)
            assert soup.find(id=fragment) or soup.find("a", attrs={"name": fragment}), (
                f"search fragment missing: {location}"
            )
    return result


def configuration(site: Path) -> dict:
    data = index(site)
    assert data is not None, "search index missing"
    return {"separator": data["config"]["separator"]}


def extract(site: Path) -> dict:
    data = index(site)
    sections = []
    for record in records(site):
        text = BeautifulSoup(record.get("text", ""), "html.parser").get_text(" ")
        title = BeautifulSoup(record["title"], "html.parser").get_text(" ", strip=True)
        sections.append(
            {
                "location": record["location"],
                "title": title,
                "tokens": sorted(set(re.findall(r"\bCOMPAT_[A-Z_0-9]+\b", text))),
                "tags": sorted(str(tag) for tag in record.get("tags", [])),
            }
        )
    return {
        "index_present": data is not None,
        "ui": {
            route: bool(html(site / route).select_one('[data-md-component="search"]'))
            for route in routes(site)
        },
        "sections": sorted(
            sections, key=lambda value: (value["location"], value["title"])
        ),
    }
