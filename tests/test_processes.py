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

"""Check bounded process cleanup and useful diagnostics on every platform."""

import os
import sys
import time
from pathlib import Path

import pytest

from compatibility.runner import build, check_build


def test_build_timeout_stops_descendants(tmp_path):
    heartbeat = tmp_path / "heartbeat.txt"
    (tmp_path / "child.py").write_text(
        "import time\n"
        "from pathlib import Path\n"
        "deadline = time.monotonic() + 10\n"
        "with Path('heartbeat.txt').open('a') as output:\n"
        "    while time.monotonic() < deadline:\n"
        "        output.write('alive\\n')\n"
        "        output.flush()\n"
        "        time.sleep(0.05)\n",
        encoding="utf-8",
    )
    (tmp_path / "probe.py").write_text(
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, 'child.py'])\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )
    outcome = build(
        Path(sys.executable),
        "probe",
        tmp_path,
        tmp_path,
        clean=True,
        strict=True,
        timeout=2,
    )
    assert outcome["timed_out"]
    assert outcome["seconds"] < 5, "cleanup must finish before the child expires"
    assert heartbeat.is_file(), "the descendant must actually start"
    size = heartbeat.stat().st_size
    assert size > 0
    time.sleep(0.3)
    assert heartbeat.stat().st_size == size, "timed-out descendant is still running"


def test_failed_build_reports_unicode_diagnostic(tmp_path):
    diagnostic = "COMPAT_FAILURE: café Ω"
    (tmp_path / "probe.py").write_text(
        f"import sys\nprint({diagnostic!r})\nsys.exit(2)\n", encoding="utf-8"
    )
    outcome = build(
        Path(sys.executable),
        "probe",
        tmp_path,
        tmp_path,
        clean=True,
        strict=True,
        timeout=5,
    )
    with pytest.raises(AssertionError) as failure:
        check_build(outcome, "probe", tmp_path, {})
    assert "exit 2" in str(failure.value)
    assert diagnostic in str(failure.value)


def test_version_environment_is_explicit_and_recorded(tmp_path, monkeypatch):
    # Unrelated cases must not be altered by an inherited Mike version.
    monkeypatch.setenv("MIKE_DOCS_VERSION", "inherited")
    (tmp_path / "probe.py").write_text("import os\nprint(os.environ.get('MIKE_DOCS_VERSION', 'unset'))\n")

    ordinary = build(Path(sys.executable), "probe", tmp_path, tmp_path, clean=True, strict=True, timeout=5)

    assert ordinary["exit_code"] == 0
    assert (tmp_path / "probe.log").read_text().startswith("unset\n")

    versioned = build(Path(sys.executable), "probe", tmp_path, tmp_path, clean=True, strict=True, timeout=5, environment={"MIKE_DOCS_VERSION": "2.1"})

    assert versioned["exit_code"] == 0
    assert versioned["environment"] == {"MIKE_DOCS_VERSION": "2.1"}
    assert (tmp_path / "probe.log").read_text().startswith("2.1\n")
    assert os.environ["MIKE_DOCS_VERSION"] == "inherited"
