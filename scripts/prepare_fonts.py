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

"""Download and unpack the locked social-card fonts into the local cache."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def prepare_fonts(root: Path = ROOT) -> Path:
    lock = json.loads((root / "requirements/fonts.json").read_text("utf-8"))
    cache = root / ".cache"
    destination = cache / "fonts"
    files = lock["files"]
    if destination.is_dir() and all(
        (destination / name).is_file()
        and hashlib.sha256((destination / name).read_bytes()).hexdigest()
        == spec["sha256"]
        for name, spec in files.items()
    ):
        return destination

    archive = cache / "downloads" / lock["archive"]
    if not archive.is_file() or (
        hashlib.sha256(archive.read_bytes()).hexdigest() != lock["sha256"]
    ):
        with urlopen(lock["url"], timeout=30) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != lock["sha256"]:
            raise RuntimeError("font archive does not match the locked SHA-256")
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(data)

    with tempfile.TemporaryDirectory(dir=cache, prefix="fonts-") as temporary:
        unpacked = Path(temporary) / "fonts"
        with zipfile.ZipFile(archive) as source:
            for name, spec in files.items():
                target = unpacked / name
                if not target.resolve().is_relative_to(unpacked.resolve()):
                    raise RuntimeError("font destination escapes cache")
                data = source.read(spec["member"])
                if hashlib.sha256(data).hexdigest() != spec["sha256"]:
                    raise RuntimeError(f"font {name} does not match the locked SHA-256")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(unpacked), destination)
    return destination


if __name__ == "__main__":
    print(f"Fonts ready: {prepare_fonts().relative_to(ROOT)} (SHA-256 verified)")
