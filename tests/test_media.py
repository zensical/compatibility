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

"""Ensure the media manifest detects regressions in generated output."""

from compatibility.media import extract
from compatibility.runner import compare


def _site(path, *, controls, source="clip.webm", style="width: 50%; height: 20px"):
    path.mkdir()
    flag = "controls" if controls else ""
    (path / "index.html").write_text(
        '<link rel="canonical" href="https://example.test/docs/guide/">'
        '<article class="md-content__inner">COMPAT_BEFORE '
        '<div class="video-container"><video '
        f'{flag} style="{style}" title="title &amp; value">'
        f'<source src="../{source}?q=1&amp;part=2" type="video/webm">'
        "</video></div> COMPAT_AFTER</article>"
    )
    return path


def test_media_observes_flags_sources_attributes_and_surrounding_text(tmp_path):
    manifest = extract(_site(tmp_path / "site", controls=False))
    page = manifest["pages"]["index.html"]
    element = page["embeds"][0]
    assert element["flags"]["controls"] is False
    assert element["sources"] == [
        {"src": "https://example.test/docs/clip.webm?q=1&part=2", "type": "video/webm"}
    ]
    assert element["attributes"]["title"] == "title & value"
    assert element["attributes"]["style"] == {"width": "50%", "height": "20px"}
    assert page["tokens"] == ["COMPAT_BEFORE", "COMPAT_AFTER"]
    equivalent = extract(
        _site(tmp_path / "equivalent", controls=False, style="height:20px;width:50%")
    )
    assert not compare(manifest, equivalent, [])


def test_expected_controls_difference_does_not_hide_a_broken_source(tmp_path):
    left = extract(_site(tmp_path / "mkdocs", controls=True))
    right = extract(_site(tmp_path / "zensical", controls=False, source="wrong.webm"))
    rule = {
        "path": "/pages/index.html/embeds/0/flags/controls",
        "mkdocs": True,
        "zensical": False,
        "reason": "Native honors disabled controls.",
    }
    difference = compare(left, right, [rule])
    assert "wrong.webm" in difference


def test_media_asset_corruption_and_omission_remain_visible(tmp_path):
    left = _site(tmp_path / "mkdocs", controls=True)
    right = _site(tmp_path / "zensical", controls=True)
    for site, content in ((left, b"original"), (right, b"corrupted")):
        folder = site / "assets/media"
        folder.mkdir(parents=True)
        (folder / "clip.webm").write_bytes(content)
    assert compare(extract(left), extract(right), [])
    (right / "assets/media/clip.webm").unlink()
    assert "assets/media/clip.webm" in compare(extract(left), extract(right), [])
