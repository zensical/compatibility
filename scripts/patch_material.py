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

"""Patch the pinned Material oracle's shared social layer futures."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "9.7.1"
ORIGINAL_SHA256 = "44be7988a79b43d0015148ed7ded36775622d651574877e3533061a6d4914bbd"
RECEIPT = "compatibility-material-patch.json"

ORIGINAL_INIT = "        self.card_layer_pool_jobs: dict[str, Future] = {}\n"
PATCHED_INIT = ORIGINAL_INIT + "        self.card_layer_pool_jobs_lock = Lock()\n"
ORIGINAL_DISPATCH = """        for h, layer in layers.items():
            sentinel = Future()

            # We need to use a hack here to avoid locking the thread pool while
            # we check if the layer was already dispatched. If we don't do this,
            # layers might be dispatched multiple times. The trick is to use a
            # sentinel value to check if the layer was already dispatched.
            if sentinel == self.card_layer_pool_jobs.setdefault(h, sentinel):
                self.card_layer_pool_jobs[h] = self.card_layer_pool.submit(
                    self._render, layer, page, config
                )
"""
PATCHED_DISPATCH = """        for h, layer in layers.items():
            # Only a submitted future is published to concurrent card workers.
            # An unfinished placeholder must never be retained by a waiter.
            with self.card_layer_pool_jobs_lock:
                if h not in self.card_layer_pool_jobs:
                    self.card_layer_pool_jobs[h] = self.card_layer_pool.submit(
                        self._render, layer, page, config
                    )
"""


def patch_source(source: str) -> str:
    """Patch reviewed source bytes and accept an identical existing patch."""
    restored = source.replace(PATCHED_INIT, ORIGINAL_INIT).replace(PATCHED_DISPATCH, ORIGINAL_DISPATCH)
    if hashlib.sha256(restored.encode()).hexdigest() != ORIGINAL_SHA256:
        raise RuntimeError("Material social source differs from the reviewed 9.7.1 file; review or remove the patch before updating the oracle")
    return restored.replace(ORIGINAL_INIT, PATCHED_INIT).replace(ORIGINAL_DISPATCH, PATCHED_DISPATCH)


def patch_material(python: Path) -> dict:
    """Patch one oracle environment and record the source change."""
    command = """
import importlib.metadata, importlib.util, json, sys
print(json.dumps({
    'version': importlib.metadata.version('mkdocs-material'),
    'path': importlib.util.find_spec('material.plugins.social.plugin').origin,
    'prefix': sys.prefix,
}))
"""
    result = subprocess.run([str(python), "-c", command], check=True, capture_output=True, text=True, timeout=30)
    info = json.loads(result.stdout)
    if info["version"] != VERSION:
        raise RuntimeError(f"Material {info['version']} is installed; review the social futures patch for the new oracle version")
    path = Path(info["path"])
    source = path.read_text(encoding="utf-8")
    patched = patch_source(source)
    if source != patched:
        path.write_text(patched, encoding="utf-8")
    receipt = {
        "name": "material-social-layer-futures",
        "version": VERSION,
        "path": str(path),
        "original_sha256": ORIGINAL_SHA256,
        "patched_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    (Path(info["prefix"]) / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, default=ROOT / ".environments/mkdocs" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
    print(json.dumps(patch_material(parser.parse_args().python), indent=2))
