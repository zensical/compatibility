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

"""Font downloads preserve locked bytes and support offline cache reuse."""

import hashlib
import io
import json
import zipfile

import pytest

from scripts import prepare_fonts


@pytest.fixture
def font_download(tmp_path):
    content = io.BytesIO()
    font = b"locked font bytes"
    license_text = b"font license\n"
    with zipfile.ZipFile(content, "w") as archive:
        archive.writestr("Roboto-Regular.ttf", font)
        archive.writestr("LICENSE", license_text)
        archive.writestr("Unused.ttf", b"not requested")
    data = content.getvalue()
    lock = {
        "url": "https://example.com/fonts.zip",
        "archive": "fonts.zip",
        "sha256": hashlib.sha256(data).hexdigest(),
        "files": {
            "Roboto/Regular.ttf": {
                "member": "Roboto-Regular.ttf",
                "sha256": hashlib.sha256(font).hexdigest(),
            },
            "Roboto/LICENSE.txt": {
                "member": "LICENSE",
                "sha256": hashlib.sha256(license_text).hexdigest(),
            },
        },
    }
    (tmp_path / "requirements").mkdir()
    (tmp_path / "requirements/fonts.json").write_text(json.dumps(lock))
    return tmp_path, data, font


def test_verified_font_cache_is_reused_and_repaired_offline(font_download, monkeypatch):
    root, data, font = font_download
    monkeypatch.setattr(
        prepare_fonts, "urlopen", lambda *args, **kwargs: io.BytesIO(data)
    )
    cache = prepare_fonts.prepare_fonts(root)
    assert (cache / "Roboto/Regular.ttf").read_bytes() == font
    assert (cache / "Roboto/LICENSE.txt").is_file()
    assert not (cache / "Unused.ttf").exists()

    def offline(*args, **kwargs):
        pytest.fail("verified cache should not download fonts again")

    monkeypatch.setattr(prepare_fonts, "urlopen", offline)
    assert prepare_fonts.prepare_fonts(root) == cache
    (cache / "Roboto/Regular.ttf").write_bytes(b"corrupted cache")
    prepare_fonts.prepare_fonts(root)
    assert (cache / "Roboto/Regular.ttf").read_bytes() == font


def test_font_download_rejects_an_unlocked_archive(font_download, monkeypatch):
    root, data, _ = font_download
    monkeypatch.setattr(
        prepare_fonts, "urlopen", lambda *args, **kwargs: io.BytesIO(data + b"changed")
    )
    with pytest.raises(RuntimeError, match="locked SHA-256"):
        prepare_fonts.prepare_fonts(root)
    assert not (root / ".cache/fonts").exists()
    assert not (root / ".cache/downloads/fonts.zip").exists()
