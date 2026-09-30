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

"""Ensure section comparisons cannot hide missing or changed result targets."""

import json

import pytest

from compatibility.search import extract, records


def write_index(site, location):
    (site / "search.json").write_text(
        json.dumps(
            {
                "items": [
                    {"location": location, "title": "Section", "text": "COMPAT_SECTION"}
                ]
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize("location", ["missing/", "#missing"])
def test_search_rejects_missing_pages_and_fragments(tmp_path, location):
    (tmp_path / "index.html").write_text('<h1 id="present">Home</h1>', encoding="utf-8")
    write_index(tmp_path, location)
    with pytest.raises(AssertionError, match="search (target|fragment) missing"):
        records(tmp_path)


def test_search_resolves_encoded_paths_and_fragments(tmp_path):
    (tmp_path / "space café.html").write_text(
        '<h2 id="café">Section</h2>', encoding="utf-8"
    )
    write_index(tmp_path, "space%20caf%C3%A9.html#caf%C3%A9")
    assert extract(tmp_path)["sections"][0]["tokens"] == ["COMPAT_SECTION"]


def test_search_detects_retargeting_even_when_page_tokens_match(tmp_path):
    (tmp_path / "index.html").write_text(
        '<h2 id="first">First</h2><h2 id="second">Second</h2>', encoding="utf-8"
    )
    write_index(tmp_path, "#first")
    before = extract(tmp_path)
    write_index(tmp_path, "#second")
    assert extract(tmp_path) != before
