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

"""Compare rendered media, surrounding content, and published local assets."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urljoin

from compatibility.checks import html, routes

FLAGS = ("controls", "autoplay", "loop", "muted", "allowfullscreen")


def _attributes(node, base: str) -> dict:
    values = {}
    for name, value in sorted(node.attrs.items()):
        if name in FLAGS:
            continue
        if name == "style":
            # Whitespace and declaration order do not change these fixture styles.
            values[name] = {
                key.strip(): content.strip()
                for declaration in value.split(";")
                if ":" in declaration
                for key, content in [declaration.split(":", 1)]
            }
        elif name in {"src", "poster"}:
            values[name] = urljoin(base, value) if value else value
        else:
            values[name] = sorted(value) if isinstance(value, list) else value
    return values


def extract(site: Path) -> dict:
    pages = {}
    for route in routes(site):
        soup = html(site / route)
        article = soup.select_one("article.md-content__inner")
        assert article is not None, f"page content missing: {route}"
        canonical = soup.select_one('link[rel="canonical"]')
        assert canonical is not None, f"canonical URL missing: {route}"
        base = canonical["href"]
        embeds = []
        for wrapper in article.select(".video-container, .audio-container"):
            node = wrapper.find(["iframe", "video", "audio"], recursive=False)
            assert node is not None, f"media element missing: {route}"
            embeds.append(
                {
                    "kind": node.name,
                    "container": _attributes(wrapper, base),
                    "attributes": _attributes(node, base),
                    "flags": {name: node.has_attr(name) for name in FLAGS},
                    "sources": [
                        _attributes(source, base) for source in node.find_all("source")
                    ],
                }
            )
        pages[route] = {
            "embeds": embeds,
            "images": [
                {
                    "alt": node.get("alt", ""),
                    "src": urljoin(base, node["src"])
                    if node.get("src")
                    else node.get("src"),
                }
                for node in article.select("img")
            ],
            "tokens": re.findall(r"\bCOMPAT_[A-Z_0-9]+\b", article.get_text(" ")),
        }
    assets = {
        path.relative_to(site).as_posix(): {
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted((site / "assets/media").rglob("*"))
        if path.is_file()
    }
    return {"pages": pages, "assets": assets}
