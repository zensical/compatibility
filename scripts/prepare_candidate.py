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

"""Prepare an isolated candidate from the latest stable Zensical PyPI release."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare_candidate(version: str | None = None) -> Path:
    candidate = ROOT / ".environments/zensical"
    python = candidate / "bin/python"
    if not python.is_file():
        subprocess.run(
            ["uv", "venv", "--clear", "--python", sys.executable, str(candidate)],
            check=True,
        )
    runtime = ROOT / "requirements/candidate.txt"
    # Sync first to remove the previous candidate and preserve the reviewed API
    # runtime dependencies before resolving the published Zensical package.
    subprocess.run(
        [
            "uv",
            "pip",
            "sync",
            "--python",
            str(python),
            "--require-hashes",
            str(runtime),
        ],
        check=True,
    )
    requirement = f"zensical=={version}" if version else "zensical"
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--default-index",
            "https://pypi.org/simple",
            "--constraint",
            str(runtime),
            "--prerelease",
            "disallow",
            "--upgrade-package",
            "zensical",
            requirement,
        ],
        check=True,
    )
    subprocess.run(["uv", "pip", "check", "--python", str(python)], check=True)
    (candidate / "compatibility-candidate.json").write_text(
        json.dumps(
            {
                "source": "pypi",
                "requirement": requirement,
                "index": "https://pypi.org/simple",
                "runtime_lock_sha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return python


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", help="Install an exact release instead of latest stable"
    )
    args = parser.parse_args()
    print(f"Candidate ready: {prepare_candidate(args.version).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
