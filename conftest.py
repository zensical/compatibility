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

"""Configure independent builder interpreters and retained run artifacts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from compatibility.runner import discover, environment, validate_case, write_json
from scripts.prepare_candidate import prepare_candidate

ROOT = Path(__file__).resolve().parent


def pytest_addoption(parser):
    group = parser.getgroup("compatibility")
    group.addoption(
        "--mkdocs-python",
        default=str(
            ROOT
            / ".environments/mkdocs"
            / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        ),
    )
    group.addoption(
        "--zensical-python",
        default=None,
        help="Use an explicit candidate interpreter instead of a PyPI release",
    )
    group.addoption(
        "--zensical-version",
        default=None,
        help="Test an exact PyPI release; defaults to latest stable",
    )
    group.addoption("--artifacts", default=str(ROOT / "artifacts"))
    group.addoption("--case", action="append", default=[])
    group.addoption("--combinations", action="store_true", default=False)
    group.addoption("--serve", action="store_true", default=False)


def pytest_generate_tests(metafunc):
    if "case" not in metafunc.fixturenames:
        return
    paths = discover(ROOT / "cases", metafunc.config.getoption("--combinations"))
    available = {p.relative_to(ROOT / "cases").as_posix(): p for p in paths}
    selected = metafunc.config.getoption("--case")
    unknown = set(selected) - available.keys()
    if unknown:
        raise pytest.UsageError(f"unknown cases: {', '.join(sorted(unknown))}")
    if selected:
        available = {name: available[name] for name in selected}
    if not available:
        raise pytest.UsageError("no compatibility cases selected")
    for path in available.values():
        validate_case(path, ROOT / "cases")
    metafunc.parametrize("case", list(available.values()), ids=list(available))


@pytest.fixture(scope="session")
def builders(pytestconfig):
    candidate = pytestconfig.getoption("--zensical-python")
    version = pytestconfig.getoption("--zensical-version")
    if candidate and version:
        raise pytest.UsageError("choose --zensical-python or --zensical-version")
    if candidate is None:
        candidate = str(prepare_candidate(version))
    selected = {
        "mkdocs": pytestconfig.getoption("--mkdocs-python"),
        "zensical": candidate,
    }
    # Preserve venv symlinks: resolving bin/python can select the base interpreter.
    paths = {
        engine: Path(os.path.abspath(os.path.expanduser(selected[engine])))
        for engine in ("mkdocs", "zensical")
    }
    for engine, path in paths.items():
        if not path.is_file():
            raise pytest.UsageError(f"missing {engine} interpreter: {path}")
    info = {engine: environment(path, engine) for engine, path in paths.items()}
    if info["mkdocs"]["prefix"] == info["zensical"]["prefix"]:
        raise pytest.UsageError("MkDocs and Zensical must use separate environments")
    return paths, info


@pytest.fixture(scope="session")
def artifacts(pytestconfig, builders):
    root = Path(pytestconfig.getoption("--artifacts")).absolute() / uuid4().hex
    root.mkdir(parents=True)
    write_json(root / "environments.json", builders[1])
    pytestconfig._compatibility_artifacts = root
    return root


def pytest_terminal_summary(terminalreporter, config):
    root = getattr(config, "_compatibility_artifacts", None)
    if root is not None:
        write_json(root / "summary.json", getattr(config, "_compatibility_results", {}))
        terminalreporter.write_line(f"Compatibility artifacts: {root}")

        environments = json.loads((root / "environments.json").read_text("utf-8"))
        for engine, info in environments.items():
            packages = info["packages"]
            names = (
                ("mkdocs", "mkdocs-material") if engine == "mkdocs" else ("zensical",)
            )
            versions = ", ".join(f"{name} {packages[name]}" for name in names)
            terminalreporter.write_line(
                f"{versions}; Python {info['python_version'].split()[0]}"
            )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" or (report.when == "setup" and report.failed):
        if not hasattr(item.config, "_compatibility_results"):
            item.config._compatibility_results = {}
        item.config._compatibility_results[item.nodeid] = {
            "status": "xfailed" if hasattr(report, "wasxfail") else report.outcome,
            "seconds": round(report.duration, 3),
        }
        if hasattr(report, "wasxfail"):
            item.config._compatibility_results[item.nodeid]["reason"] = report.wasxfail
