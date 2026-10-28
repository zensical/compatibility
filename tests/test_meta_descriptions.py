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

"""Check that description and CSV regressions remain observable."""

import csv
import json

import pytest

from compatibility.meta_descriptions import extract
from compatibility.runner import compare


def page(site, *, description="Generated metadata", head="Final &amp; rendered"):
    """Write distinct metadata, head, and body description probes."""
    metadata = json.dumps({"description": description})
    (site / "index.html").write_text(
        f'<html><head><meta name="description" content="{head}"></head><body>'
        f'<script id="compatibility-meta-descriptions">{metadata}</script>'
        '<meta name="description" content="Body description">'
        '</body></html>',
        encoding="utf-8",
    )


def exported(site, rows):
    """Write exported rows with the standard CSV dialect."""
    with (site / "meta-descriptions.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Page", "Meta description"])
        writer.writerows(rows)


def test_metadata_and_final_head_descriptions_are_observed_separately(tmp_path):
    # Body tags must be excluded from head and metadata observations.
    page(tmp_path)

    before = extract(tmp_path)

    assert before == {
        "pages": {"index.html": {"metadata": "Generated metadata", "head": ["Final & rendered"]}},
        "csv": None,
    }

    page(tmp_path, description="Changed metadata")
    changed_metadata = extract(tmp_path)
    page(tmp_path, head="Changed head")
    changed_head = extract(tmp_path)

    assert "Changed metadata" in compare(before, changed_metadata, [])
    assert "Changed head" in compare(before, changed_head, [])


def test_csv_preserves_quotes_newlines_urls_and_duplicate_rows(tmp_path):
    page(tmp_path)
    first = ["https://example.test/docs/", 'Quoted, "exact"\nsecond line']
    second = ["https://example.test/docs/caf%C3%A9/", "Café 🦀"]
    exported(tmp_path, [second, first, first])

    before = extract(tmp_path)

    assert before["csv"] == {
        "header": ["Page", "Meta description"],
        "rows": [first, first, second],
    }

    # Only traversal order is excluded from semantic comparison.
    exported(tmp_path, [first, second, first])
    assert extract(tmp_path) == before

    # Duplicate removal and changed exported text must remain observable.
    exported(tmp_path, [first, second])
    assert compare(before, extract(tmp_path), [])

    exported(tmp_path, [[first[0], "Changed"], first, second])
    assert "Changed" in compare(before, extract(tmp_path), [])

    exported(tmp_path, [["https://example.test/docs/wrong/", first[1]], first, second])
    assert "wrong" in compare(before, extract(tmp_path), [])


def test_export_absence_and_missing_head_tags_are_observed(tmp_path):
    page(tmp_path)
    path = tmp_path / "index.html"
    path.write_text(path.read_text().replace('<meta name="description" content="Final &amp; rendered">', ""), encoding="utf-8")

    without_export = extract(tmp_path)
    exported(tmp_path, [["https://example.test/docs/", ""]])
    with_export = extract(tmp_path)

    assert without_export["pages"]["index.html"]["head"] == []
    assert without_export["csv"] is None
    assert with_export["csv"]["rows"] == [["https://example.test/docs/", ""]]
    assert compare(without_export, with_export, [])

    (tmp_path / "index.html").unlink()
    assert "index.html" in compare(with_export, extract(tmp_path), [])


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "description CSV is empty"),
        ("Wrong,Header\n", "invalid description CSV header"),
        ("Page,Meta description\nonly-one-field\n", "invalid description CSV row"),
    ],
)
def test_malformed_csv_is_rejected(tmp_path, content, message):
    page(tmp_path)
    (tmp_path / "meta-descriptions.csv").write_text(content, encoding="utf-8")

    with pytest.raises(AssertionError, match=message):
        extract(tmp_path)


def test_missing_metadata_probe_is_rejected(tmp_path):
    (tmp_path / "index.html").write_text(
        '<head><meta name="description" content="Description"></head>',
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="description metadata probe missing"):
        extract(tmp_path)
