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

"""Macro rendering diagnostics are read from generated page content."""

from pathlib import Path

from compatibility.checks import html, routes


def diagnostics(site: Path) -> dict:
    pages = {}
    for route in routes(site):
        article = html(site / route).select_one("article.md-content__inner")
        assert article is not None, f"page content is missing: {route}"
        heading = article.select_one("h1")
        assert heading is not None, f"diagnostic heading is missing: {route}"

        code = []
        for node in article.select("pre code"):
            source = node.get_text().strip()
            if source.startswith("Traceback (most recent call last):"):
                # The traceback and final exception are retained;
                # builder paths and stack frames are excluded.
                code.append({"traceback": True, "exception": source.splitlines()[-1]})
            else:
                code.append({"source": source})

        pages[route] = {
            "heading": heading.get_text(" ", strip=True).removesuffix(" ¶"),
            "paragraphs": [node.get_text().strip() for node in article.find_all("p", recursive=False)],
            "code": code,
        }
    return {"pages": pages}
