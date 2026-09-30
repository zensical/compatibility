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

"""Install the pinned RSS source tree whose wheel omits integration modules."""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    lock = (ROOT / "requirements/mkdocs.txt").read_text(encoding="utf-8")
    match = re.search(
        r"^mkdocs-rss-plugin @ (https://[^\s]+) \\\n"
        r"\s+--hash=sha256:([0-9a-f]{64})",
        lock,
        re.MULTILINE,
    )
    if match is None:
        raise RuntimeError("pinned RSS archive and hash are missing from the lock")
    url, expected = match.groups()
    with urlopen(url, timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise RuntimeError("RSS archive does not match the locked hash")
    destination = ROOT / ".environments/sources" / expected
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as raw:
        unpacked = Path(raw)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            archive.extractall(unpacked, filter="data")
        directories = list(unpacked.iterdir())
        if len(directories) != 1 or not directories[0].is_dir():
            raise RuntimeError("unexpected RSS archive structure")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(directories[0]), destination)
    # Editable installation exposes the unmodified pinned source tree, including
    # integrations/ that this upstream revision omits from its built wheel.
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(
                ROOT
                / ".environments/mkdocs"
                / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            ),
            "--no-deps",
            "--editable",
            str(destination),
        ],
        check=True,
    )
    (ROOT / ".environments/oracle-source.json").write_text(
        json.dumps(
            {"url": url, "sha256": expected, "source": str(destination)}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
