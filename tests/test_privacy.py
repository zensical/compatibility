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

"""Ensure privacy manifests and local HTTP observations detect regressions."""

import hashlib
from http.client import HTTPConnection
import json
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

import pytest

from compatibility.privacy import ORIGIN, extract, fixture, validate
from compatibility.runner import compare


def _site(project, authority="127.0.0.1:18001", *, target="image.png", attributes=""):
    site = project / "site"
    assets = site / "assets/external/privacy.test"
    assets.mkdir(parents=True)
    (assets / "image.png").write_bytes(b"COMPAT_IMAGE")
    (project / "privacy-http.json").write_text(json.dumps({
        "origin": f"http://{authority}", "asset_roots": ["assets/external"],
    }))
    (site / "index.html").write_text(
        '<img data-privacy="image" '
        f'src="assets/external/privacy.test/{target}" {attributes}>'
        f'<a data-privacy="external" href="http://{authority}/page" '
        'target="_blank" rel="noopener nofollow">COMPAT_LINK</a>'
    )
    return site


def test_ports_are_normalized_while_attributes_and_image_bytes_are_observed(tmp_path):
    left = _site(tmp_path / "left", attributes='loading="lazy"')
    right = _site(tmp_path / "right", "127.0.0.1:18002", attributes='loading="lazy"')

    expected = extract(left)
    actual = extract(right)

    assert actual == expected
    assert actual["pages"]["index.html"]["external"]["attributes"]["rel"] == ["nofollow", "noopener"]
    image = actual["assets"]["assets/external/privacy.test/image.png"]
    assert image["sha256"] == hashlib.sha256(b"COMPAT_IMAGE").hexdigest()

    # A changed browser attribute must remain visible after port normalization.
    page = right / "index.html"
    page.write_text(page.read_text().replace('loading="lazy"', 'loading="eager"'))
    assert compare(expected, extract(right), [])

    # Equal filenames must not hide corrupted or stale downloaded bytes.
    (right / "assets/external/privacy.test/image.png").write_bytes(b"CHANGED")
    assert compare(expected, extract(right), [])


def test_missing_download_targets_are_rejected(tmp_path):
    site = _site(tmp_path, target="missing.png#only-light")

    with pytest.raises(AssertionError, match="rewritten asset is missing"):
        extract(site)


def test_css_dependencies_and_javascript_strings_are_retained(tmp_path):
    site = _site(tmp_path)
    assets = site / "assets/external/privacy.test"
    (assets / "theme.css").write_text('body { background: url("image.png#only-dark"); }')
    (assets / "loader.js").write_text('const image = "image.png";')

    manifest = extract(site)

    assert manifest["assets"]["assets/external/privacy.test/theme.css"] == {"urls": ["image.png#only-dark"]}
    assert manifest["assets"]["assets/external/privacy.test/loader.js"] == {"strings": ["image.png"]}

    # Equivalent URL semantics are retained for static and quoted strings.
    (assets / "loader.js").write_text('const image = `image.png`;')
    assert extract(site) == manifest


def test_hash_normalization_keeps_emitted_byte_validity_observable(tmp_path):
    site = _site(tmp_path)
    assets = site / "assets/external/privacy.test"
    source = b'const marker="COMPAT_SCRIPT";'
    digest = hashlib.sha384(source).hexdigest()[:6]
    correct = assets / f"loader.{digest}.min.js"
    correct.write_bytes(source)

    expected = extract(site)

    key = "assets/external/privacy.test/loader.HASH.min.js"
    assert expected["assets"][key]["fingerprint_valid"] is True

    correct.write_bytes(b'const marker="CHANGED";')
    actual = extract(site)
    assert actual["assets"][key]["fingerprint_valid"] is False
    assert compare(expected, actual, [])


def test_http_fixture_records_cache_contracts_and_stops_its_server(tmp_path):
    case = tmp_path / "case"
    remote = case / "project/remote"
    remote.mkdir(parents=True)
    (remote / "asset.css").write_text(f'body {{ background: url("{ORIGIN}/image.png"); }}')
    (case / "project/mkdocs.yml").write_text(f'site_url: {ORIGIN}\npattern: PRIVACY_FIXTURE_HOST/*\n')
    spec = {"http": {"directory": "remote", "requests": {"cold": {"/asset.css?v=1": 1}, "warm": {}}}}
    project = tmp_path / "build"
    project.mkdir()
    (project / "mkdocs.yml").write_text((case / "project/mkdocs.yml").read_text())
    validate(case, spec)

    with fixture(case, spec) as server:
        server.prepare(project)
        assert ORIGIN in (project / "mkdocs.yml").read_text()
        assert "PRIVACY_FIXTURE_HOST" not in (project / "mkdocs.yml").read_text()
        assert server.bind_url not in (project / "mkdocs.yml").read_text()
        opener = build_opener(ProxyHandler({"http": server.bind_url}))
        before = server.snapshot()
        with opener.open(server.origin + "/asset.css?v=1", timeout=5) as response:
            assert server.origin in response.read().decode()
        server.record(before, tmp_path, "mkdocs", "cold")
        server.record(server.snapshot(), tmp_path, "zensical", "warm")
        assert json.loads((tmp_path / "mkdocs-http.json").read_text())["requests"] == {"/asset.css?v=1": 1}

    assert not server.worker.is_alive()


def test_http_fixture_rejects_escape_paths_and_serves_explicit_mime_types(tmp_path):
    case = tmp_path / "case"
    remote = case / "project/remote"
    remote.mkdir(parents=True)
    (remote / "font.css").write_text("COMPAT_FONT")
    (remote.parent / "secret.txt").write_text("PRIVATE")
    spec = {"http": {"directory": "remote", "routes": {"/css": {"file": "font.css", "content_type": "text/css"}}}}

    with fixture(case, spec) as server:
        opener = build_opener(ProxyHandler({"http": server.bind_url}))
        with opener.open(server.origin + "/css?family=Fixture", timeout=5) as response:
            assert response.headers["Content-Type"] == "text/css"
            assert response.read() == b"COMPAT_FONT"
        with pytest.raises(HTTPError) as error:
            opener.open(server.origin + "/../secret.txt", timeout=5)
        assert error.value.code == 404


def test_http_fixture_rejects_other_origins_instead_of_forwarding_them(tmp_path):
    remote = tmp_path / "project/remote"
    remote.mkdir(parents=True)
    (remote / "image.png").write_bytes(b"LOCAL")

    with fixture(tmp_path, {"http": {"directory": "remote"}}) as server:
        opener = build_opener(ProxyHandler({"http": server.bind_url}))
        with pytest.raises(HTTPError) as error:
            opener.open("http://outside.invalid/image.png", timeout=5)

        assert error.value.code == 502
        assert server.snapshot() == {"http://outside.invalid/image.png": 1}


def test_http_fixture_serves_connect_tunnels_without_forwarding(tmp_path):
    remote = tmp_path / "project/remote"
    remote.mkdir(parents=True)
    (remote / "image.png").write_bytes(b"LOCAL")

    with fixture(tmp_path, {"http": {"directory": "remote"}}) as server:
        connection = HTTPConnection("127.0.0.1", server.server.server_port, timeout=5)
        connection.set_tunnel("privacy.test", 80)
        try:
            connection.request("GET", "/image.png")
            response = connection.getresponse()
            assert response.status == 200
            assert response.read() == b"LOCAL"
        finally:
            connection.close()

        assert server.snapshot() == {"/image.png": 1}


def test_http_fixture_validation_rejects_sources_outside_the_case(tmp_path):
    (tmp_path / "project").mkdir()

    with pytest.raises(AssertionError, match="inside the source project"):
        validate(tmp_path, {"http": {"directory": "../outside"}})
