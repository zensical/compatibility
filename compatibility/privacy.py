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

"""Observe privacy output and serve deterministic external fixture assets."""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import threading
from urllib.parse import unquote, urlsplit

from compatibility.checks import html

ORIGIN = "http://privacy.test"


def validate(case: Path, spec: dict) -> None:
    """Validate a fixture server's repository-owned inputs and contracts."""
    if "http" not in spec:
        return
    options = spec["http"]
    assert isinstance(options, dict), "http must be a mapping"
    assert set(options) <= {"directory", "routes", "requests", "asset_roots", "local_assets", "cache_dirs"}, "unknown HTTP fixture setting"
    assert isinstance(options.get("directory"), str), "HTTP fixtures need a source directory"
    for field in ("asset_roots", "local_assets", "cache_dirs"):
        for path in options.get(field, []):
            assert isinstance(path, str) and not Path(path).is_absolute() and ".." not in Path(path).parts, "HTTP output probes must stay inside the generated site"
    project = (case / "project").resolve()
    directory = (project / options["directory"]).resolve()
    assert directory.is_relative_to(project) and directory.is_dir(), "HTTP fixtures must stay inside the source project"
    for route, response in options.get("routes", {}).items():
        assert route.startswith("/"), "HTTP fixture routes must start with /"
        assert set(response) <= {"file", "content_type", "status", "location"}, "unknown HTTP response setting"
        if "file" in response:
            source = (directory / response["file"]).resolve()
            assert source.is_relative_to(directory) and source.is_file(), "HTTP response source is missing or escapes its directory"


class Fixture:
    """Serve one case's assets and retain per-builder network observations."""

    def __init__(self, directory: Path, options: dict):
        self.directory = directory.resolve()
        self.options = options
        self.requests = Counter()
        self.lock = threading.Lock()
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_CONNECT(self):
                # CONNECT is used for HTTP URLs by ureq. Requests inside this
                # restricted tunnel are served locally without another socket.
                if self.path != "privacy.test:80":
                    self.send_error(502, "The fixture proxy only serves privacy.test:80")
                    return
                self.send_response(200, "Connection established")
                self.end_headers()
                self.close_connection = False

            def do_GET(self):
                parsed = urlsplit(self.path)
                request = parsed.path + ("?" + parsed.query if parsed.query else "")
                allowed = not parsed.netloc or parsed.hostname == "privacy.test"
                with fixture.lock:
                    fixture.requests[request if allowed else self.path] += 1
                if not allowed:
                    self.send_error(502, "The fixture proxy only serves privacy.test")
                    return
                response = options.get("routes", {}).get(
                    request, options.get("routes", {}).get(parsed.path, {})
                )
                location = response.get("location")
                if location is not None:
                    self.send_response(response.get("status", 302))
                    self.send_header("Location", fixture.substitute(location.encode()).decode())
                    self.end_headers()
                    return
                source = (
                    fixture.directory
                    / response.get("file", unquote(parsed.path).lstrip("/"))
                ).resolve()
                if not source.is_relative_to(fixture.directory) or not source.is_file():
                    self.send_error(404)
                    return
                content = fixture.substitute(source.read_bytes())
                mime = response.get("content_type") or mimetypes.guess_type(source.name)[0] or "application/octet-stream"
                self.send_response(response.get("status", 200))
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def log_message(self, format, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.origin = ORIGIN
        self.bind_url = f"http://127.0.0.1:{self.server.server_port}"
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)

    def prepare(self, project: Path) -> None:
        """Prepare identical virtual origins and probe metadata for both builders."""
        for source in project.rglob("*"):
            if source.is_file():
                contents = source.read_bytes()
                substituted = self.substitute(contents)
                if substituted != contents:
                    source.write_bytes(substituted)
        (project / "privacy-http.json").write_text(json.dumps({
            "origin": self.origin,
            "asset_roots": self.options.get("asset_roots", ["assets/external"]),
            "local_assets": self.options.get("local_assets", []),
            "cache_dirs": self.options.get("cache_dirs", []),
        }), encoding="utf-8")

    def substitute(self, contents: bytes) -> bytes:
        """Replace host-pattern tokens without placing ports in asset filenames."""
        authority = urlsplit(self.origin).netloc.encode()
        return contents.replace(ORIGIN.encode(), self.origin.encode()).replace(b"//privacy.test", b"//" + authority).replace(b"PRIVACY_FIXTURE_HOST", authority)

    def normalize(self, value):
        """Normalize only the actual fixture binding authority in all checks."""
        if isinstance(value, str):
            return value.replace(urlsplit(self.bind_url).netloc, "privacy.test")
        if isinstance(value, list):
            return [self.normalize(item) for item in value]
        if isinstance(value, dict):
            return {self.normalize(key): self.normalize(item) for key, item in value.items()}
        return value

    def environment(self) -> dict[str, str]:
        """Route fixture requests through the local proxy in each builder process."""
        # Material uses URL authorities as filesystem components. A stable
        # virtual host is required because host:port names are invalid on Windows.
        proxies = {name: self.bind_url for name in (
            "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy",
        )}
        return proxies | {"NO_PROXY": "", "no_proxy": ""}

    def snapshot(self) -> Counter:
        with self.lock:
            return self.requests.copy()

    def record(self, before: Counter, phase: Path, engine: str, name: str, *, successful: bool = True) -> None:
        """Retain actual requests and enforce optional cold/warm contracts."""
        observed = dict(sorted((self.snapshot() - before).items()))
        (phase / f"{engine}-http.json").write_text(json.dumps({
            "origin": self.origin, "binding": self.bind_url, "requests": observed,
        }, indent=2) + "\n", encoding="utf-8")
        expected = self.options.get("requests", {}).get(name)
        if expected is not None and successful:
            if set(expected) == {"mkdocs", "zensical"}:
                expected = expected[engine]
            assert observed == expected, f"{engine} HTTP requests differ in {name}: expected {expected}, observed {observed}; see {phase}"


@contextmanager
def fixture(case: Path, spec: dict):
    """Start a local origin only for cases declaring HTTP fixture inputs."""
    if "http" not in spec:
        yield None
        return
    remote = Fixture(case / "project" / spec["http"]["directory"], spec["http"])
    remote.worker.start()
    try:
        yield remote
    finally:
        remote.server.shutdown()
        remote.server.server_close()
        remote.worker.join(timeout=5)
        assert not remote.worker.is_alive(), "HTTP fixture server did not stop"


def extract(site: Path) -> dict:
    """Compare marked HTML, emitted assets, and local reference validity."""
    options = json.loads((site.parent / "privacy-http.json").read_text("utf-8"))
    origin = options["origin"]
    authority = urlsplit(origin).netloc
    roots = options["asset_roots"]

    def normalize(value: str) -> str:
        return value.replace(origin, ORIGIN).replace(authority, "privacy.test")

    def asset_reference(value: str) -> str:
        # Digest validity is retained separately from its normalized spelling.
        # Different hashes may be produced by equivalent static string quoting.
        return re.sub(r"\.[0-9a-f]{6}(?=\.(?:min\.)?(?:js|css)(?:[?#]|$))", ".HASH", normalize(value).removeprefix("./"))

    def check_target(route: str, value: str) -> None:
        if "/" not in value and not re.search(r"\.[a-zA-Z0-9]{1,8}(?:[?#]|$)", value):
            return
        parsed = urlsplit(value)
        if parsed.netloc:
            if parsed.netloc != "example.test":
                return
            path = unquote(parsed.path).removeprefix("/docs/")
        elif parsed.path.startswith("/docs/"):
            path = unquote(parsed.path).removeprefix("/docs/")
        elif parsed.path.startswith("/"):
            path = unquote(parsed.path).lstrip("/")
        else:
            path = (Path(route).parent / unquote(parsed.path)).as_posix()
        if any(root in path for root in roots):
            target = (site / path).resolve()
            assert target.is_relative_to(site.resolve()) and target.is_file(), f"rewritten asset is missing: {route}: {value}"

    pages = {}
    resources = {}
    for source in sorted(site.rglob("*.html")):
        route = source.relative_to(site).as_posix()
        soup = html(source)
        marked = soup.select("[data-privacy]")
        selected = []
        for node in soup.select("script[src], img[src], image[href], link[href]"):
            attribute = "src" if node.has_attr("src") else "href"
            value = node[attribute]
            if authority not in value and not any(root in value for root in roots):
                continue
            check_target(route, value)
            selected.append({
                "tag": node.name, attribute: asset_reference(value),
                **{key: node[key] for key in ("type", "as", "rel", "async", "defer", "crossorigin") if node.has_attr(key)},
            })
        if selected:
            resources[route] = selected
        if not marked:
            continue
        nodes = {}
        for node in marked:
            name = node["data-privacy"]
            assert name not in nodes, f"duplicate privacy probe {name}: {route}"
            attributes = {}
            for key, value in sorted(node.attrs.items()):
                if key == "data-privacy":
                    continue
                if key in {"src", "href"}:
                    check_target(route, value)
                    value = asset_reference(value)
                elif isinstance(value, str):
                    value = normalize(value)
                attributes[key] = sorted(value) if key in {"class", "rel"} and isinstance(value, list) else value
            nodes[name] = {"tag": node.name, "attributes": attributes, "text": node.get_text(" ", strip=True)}
        pages[route] = nodes

    paths = {path for root in roots for path in (site / root).rglob("*") if path.is_file()}
    paths.update(path for pattern in options.get("local_assets", []) for path in site.glob(pattern) if path.is_file())
    assets = {}
    for path in sorted(paths):
        route = path.relative_to(site).as_posix()
        raw = path.read_bytes()
        fingerprint = re.search(r"\.([0-9a-f]{6})(?=\.(?:min\.)?(?:js|css)$)", path.name)
        fingerprint_valid = hashlib.sha384(raw).hexdigest().startswith(fingerprint[1]) if fingerprint else None
        key = asset_reference(route)
        assert key not in assets, f"normalized asset collision: {key}"
        if path.suffix in {".css", ".js", ".txt"}:
            source = raw.decode("utf-8-sig")
            if path.suffix == ".css":
                urls = re.findall(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", source)
                for value in urls:
                    check_target(route, value.strip())
                assets[key] = {"urls": [asset_reference(value.strip()) for value in urls]}
            elif path.suffix == ".js":
                urls = re.findall(r"['\"`]([^'\"`\r\n]+)['\"`]", source)
                for value in urls:
                    check_target(route, value)
                assets[key] = {"strings": [asset_reference(value) for value in urls]}
            else:
                assets[key] = {"text": normalize(source)}
        else:
            assets[key] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        if fingerprint is not None:
            assets[key]["fingerprint_valid"] = fingerprint_valid
    result = {"pages": pages, "assets": assets, "resources": resources}
    if options.get("cache_dirs"):
        result["cache"] = {
            directory: any(path.is_file() for path in (site.parent / directory).rglob("*"))
            for directory in options["cache_dirs"]
        }
    return result
