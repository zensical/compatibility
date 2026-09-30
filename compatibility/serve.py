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

"""Observe retained development servers through HTTP, without private APIs."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

import yaml
from PIL import Image

from compatibility.checks import html
from compatibility.runner import observe, process_environment, stop_process, write_json
from compatibility.social import pixels


@contextmanager
def server(python: Path, engine: str, project: Path, output: Path):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    base = f"http://127.0.0.1:{port}/docs/"
    config = project / "mkdocs.yml"
    value = yaml.safe_load(config.read_text())
    value["site_url"] = base
    config.write_text(yaml.safe_dump(value, sort_keys=False))
    command = [
        str(python),
        "-m",
        engine,
        "serve",
        "--config-file",
        "mkdocs.yml",
        "--dev-addr",
        f"127.0.0.1:{port}",
    ]
    with (output / "server.log").open("w") as log:
        process = subprocess.Popen(
            command,
            cwd=project,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=process_environment(),
            start_new_session=os.name == "posix",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        write_json(
            output / "server.json",
            {"command": command, "base": base, "cwd": str(project), "pid": process.pid},
        )
        try:
            yield base, process
        finally:
            stop_process(process, interrupt=True)
            write_json(output / "server-exit.json", {"exit_code": process.returncode})


def fetch(base: str, path: str) -> tuple[int, bytes]:
    try:
        with urlopen(base + path, timeout=2) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def download(base: str, engine: str, output: Path) -> dict:
    """Download published pages and plugin artifacts from the actual server."""
    site = output / "site"
    if site.exists():
        shutil.rmtree(site)
    site.mkdir()
    requests = {}

    def save(path: str, destination: str | None = None, binary: bool = False):
        status, body = fetch(base, path)
        requests[path] = status
        assert status == 200, f"HTTP {status}: {path}"
        target = site / (destination or path)
        assert target.resolve().is_relative_to(site.resolve()), "HTTP path escaped site"
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = output / "responses" / target.relative_to(site)
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(body)
        if not binary:
            # Binding ports are environment identity; preserve mount paths and
            # every other URL component while restoring the fixture site_url.
            body = body.replace(base.encode(), b"https://example.test/docs/")
        target.write_bytes(body)
        return body

    sitemap = save("sitemap.xml")
    cards = set()
    for node in ET.fromstring(sitemap).iter():
        if node.tag.rsplit("}", 1)[-1] != "loc":
            continue
        canonical = "https://example.test/docs/"
        assert node.text.startswith(canonical), f"unexpected published URL: {node.text}"
        route = node.text[len(canonical) :]
        destination = (
            route + "index.html" if route.endswith("/") or not route else route
        )
        save(route, destination)
        for image in html(site / destination).select('meta[property="og:image"]'):
            path = urlsplit(image["content"]).path.removeprefix("/docs/")
            cards.add(path)
    for path in sorted(cards):
        save(path, binary=True)
    search = "search/search_index.json" if engine == "mkdocs" else "search.json"
    save(search)
    for name in (
        "feed_json_created.json",
        "feed_json_updated.json",
        "feed_rss_created.xml",
        "feed_rss_updated.xml",
    ):
        save(name)
    write_json(output / "http.json", requests)
    return observe(site, {"check": ["publication", "social", "rss"]})


def checkpoint(base, engine, process, output, *, added, revised, deleted=False):
    """Wait for observable convergence, never for a fixed rebuild delay."""
    output.mkdir()
    deadline = time.monotonic() + 30
    last = "server has not responded"
    while time.monotonic() < deadline:
        assert process.poll() is None, f"{engine} server exited; see {output.parent}"
        try:
            value = download(base, engine, output)
            routes = ["index.html", "news/index.html"]
            if added:
                routes.append("news/second/index.html")
            assert value["publication"]["routes"] == routes, "stale page membership"
            assert fetch(base, "news/draft/")[0] == 404, "excluded page is served"
            assert fetch(base, "assets/images/social/news/draft.png")[0] == 404, (
                "excluded page card is served"
            )
            if not added:
                assert fetch(base, "news/second/")[0] == 404, "deleted page is served"
                assert fetch(base, "assets/images/social/news/second.png")[0] == 404, (
                    "deleted page card is served"
                )
            search = {"": ["COMPAT_HOME"], "news/": ["COMPAT_NEWS"]}
            if added:
                search["news/second/"] = ["COMPAT_ADDED"]
            assert value["publication"]["search"] == search, "stale search membership"
            feed = value["rss"]["feeds"]["feed_json_created.json"]
            items = feed["items"]
            title = "Revised headline" if revised else "Inherited headline"
            assert ["og:title", title] in value["social"]["pages"]["news/index.html"], (
                "stale inherited social title"
            )
            date = "2024-01-03" if revised else "2024-01-02"
            expected = [("https://example.test/docs/news/", title, date)]
            if engine == "mkdocs" and revised:
                expected *= 3 if deleted else 2 if added else 1
            if added or (deleted and engine == "mkdocs"):
                expected.append(
                    ("https://example.test/docs/news/second/", title, "2024-01-04")
                )
            if revised and engine == "mkdocs":
                expected.append(
                    (
                        "https://example.test/docs/news/",
                        "Inherited headline",
                        "2024-01-02",
                    )
                )
            actual = [
                (item["url"], item["title"], item["date_published"][:10])
                for item in items
            ]
            assert sorted(actual) == sorted(expected), "unexpected feed state"
            card = output / "site/assets/images/social/news/index.png"
            with Image.open(card) as image:
                assert image.convert("RGB").getpixel((0, 0)) == (
                    (101, 67, 33) if revised else (18, 52, 86)
                ), "stale inherited card color"
            assert len(value["social"]["cards"]) == (3 if added else 2)
            write_json(output / "manifest.json", value)
            write_json(
                output / "card-pixels.json",
                {
                    name: pixels(output / "site" / name)
                    for name in value["social"]["cards"]
                },
            )
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
        time.sleep(0.2)
    raise AssertionError(f"{engine} HTTP state did not converge: {last}; see {output}")
