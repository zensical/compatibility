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

"""Observe published image settings and content without importing either builder."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from PIL import Image, ImageChops, ImageStat, UnidentifiedImageError

from compatibility.checks import html, routes


def extract(site: Path) -> dict:
    """Compare image URLs, decoded content, encoder settings, and cache presence."""
    project = site.parent
    probes = json.loads((project / "optimize-probes.json").read_text("utf-8"))
    sources = probes["sources"]
    assets = {}

    # Unexpected files and missing outputs are retained in the membership check.
    published = {
        path.relative_to(site).as_posix()
        for path in (site / "assets/optimize").rglob("*")
        if path.is_file()
    } | set(sources)
    for name in sorted(published):
        assert name in sources, f"unexpected optimization output: {name}"
        output = site / name
        source = project / sources[name]
        assert output.is_file(), f"optimized asset is missing: {name}"
        original = source.read_bytes()
        emitted = output.read_bytes()
        value = {
            "source_sha256": hashlib.sha256(original).hexdigest(),
            "unchanged": emitted == original,
            "smaller": len(emitted) < len(original),
        }
        try:
            image = Image.open(output)
        except UnidentifiedImageError:
            # Opaque fixtures must be copied byte for byte, including invalid images.
            assert emitted == original, f"opaque asset was modified: {name}"
            value["format"] = None
        else:
            with image, Image.open(source) as before:
                image.load()
                before.load()
                assert image.size == before.size, f"image dimensions changed: {name}"
                error = ImageStat.Stat(ImageChops.difference(image.convert("RGBA").convert("RGB"), before.convert("RGBA").convert("RGB"))).mean
                assert max(error) <= probes.get("max_mean_error", 40), f"image content changed: {name}: {error}"
                assert image.convert("RGBA").getchannel("A").tobytes() == before.convert("RGBA").getchannel("A").tobytes(), f"image transparency changed: {name}"
                value.update({
                    "format": image.format,
                    "dimensions": list(image.size),
                    "mode": image.mode,
                    "progressive": bool(image.info.get("progressive")),
                    "text": getattr(image, "text", {}),
                    "exif": bool(image.getexif()),
                    "icc_profile": bool(image.info.get("icc_profile")),
                    "alpha_extrema": list(image.convert("RGBA").getchannel("A").getextrema()),
                })
                if image.format == "JPEG":
                    value["luma_quantization"] = image.quantization[0]
        assets[name] = value

    pages = {}
    for route in routes(site):
        images = {}
        for node in html(site / route).select('img[alt^="COMPAT_"]'):
            marker = node["alt"]
            assert marker not in images, f"duplicate image probe: {marker}"
            src = node["src"]
            target = urlsplit(urljoin("/" + route, src))
            if not target.netloc:
                assert (site / unquote(target.path.lstrip("/"))).is_file(), f"image URL target is missing: {route}: {src}"
            images[marker] = src
        pages[route] = images

    caches = {
        name: any(path.is_file() and path.name != "manifest.json" for path in (project / name).rglob("*"))
        for name in probes.get("cache_dirs", [])
    }
    return {"pages": pages, "assets": assets, "caches": caches}
