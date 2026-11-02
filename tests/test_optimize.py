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

"""Image comparisons must expose damaged output and ignored encoder settings."""

import json

import pytest
from PIL import Image, PngImagePlugin

from compatibility.optimize import extract
from compatibility.runner import compare


def _site(project, *, name="photo.jpg", mode="RGB", color="red"):
    """Create an independent source image and its published copy."""
    source = project / "docs/assets/optimize" / name
    output = project / "site/assets/optimize" / name
    source.parent.mkdir(parents=True)
    output.parent.mkdir(parents=True)
    Image.new(mode, (16, 16), color).save(source)
    output.write_bytes(source.read_bytes())
    (project / "optimize-probes.json").write_text(json.dumps({
        "sources": {f"assets/optimize/{name}": f"docs/assets/optimize/{name}"},
    }))
    (project / "site/index.html").write_text(f'<img alt="COMPAT_PHOTO" src="assets/optimize/{name}">')
    return project / "site", source, output


def test_jpeg_quality_and_progressive_settings_remain_observable(tmp_path):
    site, source, output = _site(tmp_path)
    with Image.open(source) as image:
        image.save(output, quality=60, progressive=True)
    expected = extract(site)

    # The same image is emitted with different JPEG settings.
    with Image.open(source) as image:
        image.save(output, quality=25, progressive=False)
    actual = extract(site)

    assert expected["assets"]["assets/optimize/photo.jpg"]["progressive"] is True
    assert actual["assets"]["assets/optimize/photo.jpg"]["progressive"] is False
    assert actual["assets"]["assets/optimize/photo.jpg"]["luma_quantization"][0] == 32
    assert compare(expected, actual, [])


@pytest.mark.parametrize("damage", ["dimensions", "colors", "invalid"])
def test_damaged_images_are_rejected(tmp_path, damage):
    site, _source, output = _site(tmp_path)

    # Resized, recolored, or unreadable output must be rejected at the expected path.
    if damage == "dimensions":
        Image.new("RGB", (8, 8), "red").save(output)
    elif damage == "colors":
        Image.new("RGB", (16, 16), "blue").save(output)
    else:
        output.write_bytes(b"not an image")

    with pytest.raises(AssertionError, match="dimensions changed|content changed|opaque asset was modified"):
        extract(site)


def test_png_transparency_cannot_be_discarded(tmp_path):
    site, _source, output = _site(tmp_path, name="diagram.png", mode="RGBA", color=(255, 0, 0, 128))

    # The RGB values are retained, but alpha is removed from the published PNG.
    Image.new("RGB", (16, 16), "red").save(output)

    with pytest.raises(AssertionError, match="transparency changed"):
        extract(site)


def test_png_metadata_is_compared_separately_from_pixels(tmp_path):
    site, source, output = _site(tmp_path, name="diagram.png")
    text = PngImagePlugin.PngInfo()
    text.add_text("Description", "COMPAT_METADATA")
    with Image.open(source) as image:
        image.save(output, pnginfo=text)
    expected = extract(site)

    # Optional metadata is removed while decoded pixels are retained.
    output.write_bytes(source.read_bytes())
    actual = extract(site)

    assert expected["assets"]["assets/optimize/diagram.png"]["text"] == {"Description": "COMPAT_METADATA"}
    assert actual["assets"]["assets/optimize/diagram.png"]["text"] == {}
    assert compare(expected, actual, [])


def test_opaque_images_are_accepted_only_when_copied_unchanged(tmp_path):
    site, source, output = _site(tmp_path)
    source.write_bytes(b"invalid JPEG used by a disabled plugin")
    output.write_bytes(source.read_bytes())

    manifest = extract(site)

    assert manifest["assets"]["assets/optimize/photo.jpg"]["unchanged"] is True
    assert manifest["assets"]["assets/optimize/photo.jpg"]["format"] is None

    output.write_bytes(b"different invalid JPEG")

    with pytest.raises(AssertionError, match="opaque asset was modified"):
        extract(site)


def test_missing_assets_and_broken_page_urls_are_rejected(tmp_path):
    site, _source, output = _site(tmp_path)
    (site / "index.html").write_text('<img alt="COMPAT_PHOTO" src="missing.jpg">')

    with pytest.raises(AssertionError, match="image URL target is missing"):
        extract(site)

    output.unlink()

    with pytest.raises(AssertionError, match="optimized asset is missing"):
        extract(site)


def test_cache_manifest_alone_does_not_prove_cached_image_presence(tmp_path):
    site, _source, output = _site(tmp_path)
    probes = tmp_path / "optimize-probes.json"
    probes.write_text(json.dumps(json.loads(probes.read_text()) | {"cache_dirs": ["image-cache"]}))
    cache = tmp_path / "image-cache"
    cache.mkdir()
    (cache / "manifest.json").write_text("{}")

    assert extract(site)["caches"] == {"image-cache": False}

    # Actual cached image bytes are required in addition to bookkeeping.
    (cache / "photo.jpg").write_bytes(output.read_bytes())

    assert extract(site)["caches"] == {"image-cache": True}
