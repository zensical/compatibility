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

"""Check inherited tags and search changes through retained public servers."""

import json
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import URLError
from urllib.parse import unquote

import pytest

from compatibility.runner import compare, mutate, observe, pointer, write_json
from compatibility.serve import fetch, server

CANONICAL = "https://example.test/docs/"


def download(base, engine, output):
    site = output / "site"
    if site.exists():
        shutil.rmtree(site)
    site.mkdir()
    responses = {}

    def save(route, destination=None):
        status, body = fetch(base, route)
        responses[route] = status
        assert status == 200, f"HTTP {status}: {route}"
        path = site / unquote(destination or route)
        assert path.resolve().is_relative_to(site.resolve()), "HTTP target escaped site"
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = output / "responses" / path.relative_to(site)
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(body)
        body = body.replace(base.encode(), CANONICAL.encode())
        path.write_bytes(body)
        return body

    sitemap = save("sitemap.xml")
    for node in ET.fromstring(sitemap).iter():
        if node.tag.rsplit("}", 1)[-1] != "loc":
            continue
        assert node.text.startswith(CANONICAL), f"unexpected canonical: {node.text}"
        route = node.text.removeprefix(CANONICAL)
        save(route, route + "index.html" if not route or route.endswith("/") else route)
    save("search/search_index.json" if engine == "mkdocs" else "search.json")
    write_json(output / "http.json", responses)
    return observe(site, {"check": ["meta", "tag-content", "search", "publication"]})


def checkpoint(base, engine, process, output, spec, step, previous):
    output.mkdir()
    deadline = time.monotonic() + 30
    last = "server has not responded"
    while time.monotonic() < deadline:
        try:
            assert process.poll() is None, f"{engine} server exited"
            value = download(base, engine, output)
            for assertion in step.get("assertions", spec["assertions"]):
                if assertion.get("engine", engine) != engine:
                    continue
                actual = pointer(value, assertion["path"])
                assert (
                    len(actual) == assertion["count"]
                    if "count" in assertion
                    else actual == assertion["value"]
                ), f"{assertion['path']}: expected {assertion}; observed {actual}"
            if step.get("changed"):
                assert value != previous, "HTTP output did not change"
            if step["name"] == "delete-page":
                assert fetch(base, "guides/new/")[0] == 404, (
                    "deleted page is still served"
                )
            write_json(output / "manifest.json", value)
            return value
        except (
            AssertionError,
            OSError,
            URLError,
            ValueError,
            KeyError,
            ET.ParseError,
        ) as error:
            last = str(error)
        if process.poll() is not None:
            break
        time.sleep(0.2)
    log = (output.parent / "server.log").read_text(encoding="utf-8", errors="replace")
    tail = "\n".join(log.splitlines()[-80:])
    raise AssertionError(f"{engine} HTTP state did not converge: {last}\n{tail}")


def test_metadata_tags_search_server_lifecycle(pytestconfig, request):
    if not pytestconfig.getoption("--serve"):
        pytest.skip("enable --serve for retained HTTP server checks")
    builders, _ = request.getfixturevalue("builders")
    root = Path(__file__).resolve().parents[1]
    case = root / "cases/combinations/publishing/meta-tags-search"
    spec = json.loads((case / "case.json").read_text(encoding="utf-8"))
    steps = [{"name": "cold"}, *spec["steps"]]
    output = request.getfixturevalue("artifacts") / "serve/meta-tags-search"
    output.mkdir(parents=True)
    observations = {}
    for engine, python in builders.items():
        engine_output = output / engine
        engine_output.mkdir()
        project = engine_output / "project"
        shutil.copytree(case / "project", project)
        observations[engine] = {}
        previous = None
        with server(python, engine, project, engine_output) as (base, process):
            for step in steps:
                mutate(project, step)
                value = checkpoint(
                    base,
                    engine,
                    process,
                    engine_output / step["name"],
                    spec,
                    step,
                    previous,
                )
                observations[engine][step["name"]] = value
                previous = value
    for step in steps:
        difference = compare(
            observations["mkdocs"][step["name"]],
            observations["zensical"][step["name"]],
            step.get("differences", spec["differences"]),
        )
        (output / f"{step['name']}.diff").write_text(difference, encoding="utf-8")
        assert not difference, (
            f"retained meta/tags/search compatibility regression:\n{difference}"
        )
