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

"""Check source guards and concurrent completion of patched Material layers."""

import ast
import json
import os
import posixpath
import subprocess
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest

from scripts.patch_material import patch_material, patch_optimize_source, patch_privacy_source, patch_source


@pytest.fixture(scope="module")
def material_source(pytestconfig):
    python = Path(pytestconfig.getoption("--mkdocs-python"))
    if not python.is_file():
        pytest.skip("the pinned MkDocs environment is required")
    command = "import importlib.util,json; print(json.dumps(importlib.util.find_spec('material.plugins.social.plugin').origin))"
    result = subprocess.run([str(python), "-c", command], check=True, capture_output=True, text=True, timeout=30)
    return Path(json.loads(result.stdout)).read_text(encoding="utf-8")


def dispatch_from_source(source):
    """Compile the actual dispatch loop without image-rendering dependencies."""
    plugin = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == "SocialPlugin")
    generate = next(node for node in plugin.body if isinstance(node, ast.FunctionDef) and node.name == "_generate")
    dispatch = next(node for node in generate.body if isinstance(node, ast.For) and any(isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr == "submit" for child in ast.walk(node)))
    module = ast.parse("def dispatch(self, layers, page, config): pass")
    module.body[0].body = [dispatch]
    namespace = {"Future": Future}
    exec(compile(ast.fix_missing_locations(module), "material-social-dispatch", "exec"), namespace)
    return namespace["dispatch"]


def test_material_patch_is_idempotent_and_rejects_unreviewed_source(material_source):
    patched = patch_source(material_source)

    assert patch_source(patched) == patched
    with pytest.raises(RuntimeError, match="differs from the reviewed"):
        patch_source(material_source + "\n# unexpected upstream change\n")


def test_material_patch_requires_review_for_a_new_oracle_version(monkeypatch):
    # An oracle update must not receive the old patch, even with unchanged code.
    response = subprocess.CompletedProcess([], 0, stdout=json.dumps({"version": "9.7.2"}))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: response)

    with pytest.raises(RuntimeError, match="review the Material concurrency patches"):
        patch_material(Path("unused-python"))


@pytest.fixture(scope="module")
def optimize_source(pytestconfig):
    python = Path(pytestconfig.getoption("--mkdocs-python"))
    if not python.is_file():
        pytest.skip("the pinned MkDocs environment is required")
    command = "import importlib.util,json; print(json.dumps(importlib.util.find_spec('material.plugins.optimize.plugin').origin))"
    result = subprocess.run([str(python), "-c", command], check=True, capture_output=True, text=True, timeout=30)
    return Path(json.loads(result.stdout)).read_text(encoding="utf-8")


def test_optimize_patch_is_idempotent_and_rejects_unreviewed_source(optimize_source):
    patched = patch_optimize_source(optimize_source)

    assert patch_optimize_source(patched) == patched

    with pytest.raises(RuntimeError, match="differs from the reviewed"):
        patch_optimize_source(optimize_source + "\n# unexpected upstream change\n")


@pytest.fixture(scope="module")
def privacy_source(pytestconfig):
    python = Path(pytestconfig.getoption("--mkdocs-python"))
    if not python.is_file():
        pytest.skip("the pinned MkDocs environment is required")
    command = "import importlib.util,json; print(json.dumps(importlib.util.find_spec('material.plugins.privacy.plugin').origin))"
    result = subprocess.run([str(python), "-c", command], check=True, capture_output=True, text=True, timeout=30)
    return Path(json.loads(result.stdout)).read_text(encoding="utf-8")


def test_privacy_patch_is_idempotent_and_rejects_unreviewed_source(privacy_source):
    patched = patch_privacy_source(privacy_source)

    assert patch_privacy_source(patched) == patched

    with pytest.raises(RuntimeError, match="differs from the reviewed"):
        patch_privacy_source(privacy_source + "\n# unexpected upstream change\n")


def privacy_queue_from_source(source, pool):
    """Compile the real queue and initialization methods with a small asset store."""
    plugin_class = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == "PrivacyPlugin")
    methods = [node for node in plugin_class.body if isinstance(node, ast.FunctionDef) and node.name in {"on_config", "_queue", "_queue_locked"}]
    module = ast.parse("from __future__ import annotations\nclass QueuedPrivacy: pass")
    module.body[1].body = methods
    assets = {}
    namespace = {
        "posixpath": posixpath,
        "urlparse": urlparse,
        "RLock": threading.RLock,
        "ThreadPoolExecutor": lambda concurrency: pool,
        "Files": lambda files: SimpleNamespace(get_file_from_path=assets.get, append=lambda file: assets.setdefault(file.src_uri, file)),
        "log": SimpleNamespace(disabled=False),
    }
    exec(compile(ast.fix_missing_locations(module), "material-privacy-queue", "exec"), namespace)
    plugin = namespace["QueuedPrivacy"]()
    plugin.config = SimpleNamespace(enabled=True, concurrency=2, assets_expr_map={}, log=False, assets_fetch_dir="assets/external")
    plugin.on_config(SimpleNamespace(site_url="https://example.test/docs/"))
    plugin._path_from_url = lambda url: url.netloc + url.path
    plugin._path_to_file = lambda path, config: SimpleNamespace(src_uri=posixpath.join(plugin.config.assets_fetch_dir, path))
    return plugin


@pytest.mark.parametrize("concurrent", [False, True], ids=["synchronous", "background"])
def test_concurrent_privacy_discovery_downloads_a_shared_asset_once(privacy_source, concurrent):
    # Eight callers are released together while registration is delayed.
    ready = threading.Barrier(8)
    fetched = []

    def fetch(file, config):
        fetched.append(file.url)
        if not concurrent:
            time.sleep(0.05)
        return True

    with ThreadPoolExecutor(max_workers=2) as downloads:
        def submit(worker, file, config):
            future = downloads.submit(worker, file, config)
            time.sleep(0.05)
            return future

        plugin = privacy_queue_from_source(patch_privacy_source(privacy_source), SimpleNamespace(submit=submit))
        plugin._fetch = fetch
        url = urlparse("http://privacy.test/image.png")

        def discover():
            ready.wait(timeout=5)
            return plugin._queue(url, None, concurrent=concurrent)

        with ThreadPoolExecutor(max_workers=8) as callers:
            discoveries = [callers.submit(discover) for _ in range(8)]
            files = [discovery.result(timeout=5) for discovery in discoveries]

        for download in plugin.pool_jobs:
            download.result(timeout=5)

    # The same asset must be returned to every caller after exactly one download.
    assert fetched == ["http://privacy.test/image.png"]
    assert all(file is files[0] for file in files)


def test_privacy_downloads_of_distinct_assets_remain_concurrent(privacy_source):
    # Download completion is blocked until both workers have started.
    downloading = threading.Barrier(2)
    fetched = []

    def fetch(file, config):
        downloading.wait(timeout=5)
        fetched.append(file.url)
        return True

    with ThreadPoolExecutor(max_workers=2) as downloads:
        plugin = privacy_queue_from_source(patch_privacy_source(privacy_source), downloads)
        plugin._fetch = fetch

        plugin._queue(urlparse("http://privacy.test/first.png"), None, concurrent=True)
        plugin._queue(urlparse("http://privacy.test/second.png"), None, concurrent=True)
        for download in plugin.pool_jobs:
            download.result(timeout=5)

    assert sorted(fetched) == ["http://privacy.test/first.png", "http://privacy.test/second.png"]


def test_synchronous_privacy_downloads_can_queue_dependencies(privacy_source):
    # A synchronous stylesheet download is allowed to discover a background font.
    fetched = []
    completed = Future()

    with ThreadPoolExecutor(max_workers=2) as downloads:
        plugin = privacy_queue_from_source(patch_privacy_source(privacy_source), downloads)

        def fetch(file, config):
            fetched.append(file.url)
            if file.url.endswith("style.css"):
                plugin._queue(urlparse("http://privacy.test/font.woff2"), config, concurrent=True)
            return True

        plugin._fetch = fetch

        def discover():
            try:
                completed.set_result(plugin._queue(urlparse("http://privacy.test/style.css"), None))
            except Exception as error:
                completed.set_exception(error)

        # A non-reentrant lock regression must be detected within the test timeout.
        caller = threading.Thread(target=discover, daemon=True)
        caller.start()
        completed.result(timeout=5)
        caller.join(timeout=5)
        for download in plugin.pool_jobs:
            download.result(timeout=5)

    assert not caller.is_alive()
    assert sorted(fetched) == ["http://privacy.test/font.woff2", "http://privacy.test/style.css"]


@pytest.mark.parametrize("event", ["on_env", "on_post_build"])
def test_recursive_privacy_downloads_finish_before_files_are_published(privacy_source, event):
    # The actual event methods are compiled without importing either builder.
    tree = ast.parse(patch_privacy_source(privacy_source))
    plugin_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "PrivacyPlugin")
    method = next(node for node in plugin_class.body if isinstance(node, ast.FunctionDef) and node.name == event)
    method.decorator_list = []
    published = []
    stylesheet_download = Future()
    font_download = Future()

    # A font is discovered by the stylesheet worker during the initial wait.
    def complete_downloads(jobs):
        for download in list(jobs):
            download.set_result(None)

    def publish(file):
        assert font_download.done(), "the font was published before its download finished"
        published.append(file)

    font = SimpleNamespace(dest_uri="assets/external/privacy.test/font.woff2", abs_src_path="cached-font.woff2")
    font.copy_file = lambda: publish(font)
    plugin = SimpleNamespace(config=SimpleNamespace(enabled=True), pool_jobs=[stylesheet_download], assets=[font], assets_done=[], pool=SimpleNamespace(shutdown=lambda: None))
    # The queue may already be referenced by the stylesheet worker.
    queue_download = plugin.pool_jobs.append
    stylesheet_download.add_done_callback(lambda download: queue_download(font_download))
    namespace = {
        "wait": complete_downloads,
        "posixpath": posixpath,
        "os": SimpleNamespace(path=SimpleNamespace(exists=lambda path: font_download.done())),
    }
    exec(compile(ast.Module(body=[method], type_ignores=[]), "material-privacy-downloads", "exec"), namespace)

    if event == "on_env":
        namespace[event](plugin, None, config=None, files=SimpleNamespace(append=publish))
    else:
        namespace[event](plugin, config=None)

    # Both event boundaries must retain and finish recursively queued downloads.
    assert published == [font]
    assert font_download.done()


def test_completed_optimizer_cannot_change_file_collection_keys(optimize_source):
    # The actual dispatch method is compiled without importing either builder.
    tree = ast.parse(patch_optimize_source(optimize_source))
    plugin_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "OptimizePlugin")
    on_env = next(node for node in plugin_class.body if isinstance(node, ast.FunctionDef) and node.name == "on_env")
    namespace = {"os": os}
    exec(compile(ast.Module(body=[on_env], type_ignores=[]), "material-optimize-dispatch", "exec"), namespace)
    source_path = "docs/photo.jpg"
    file = SimpleNamespace(src_path="photo.jpg", abs_src_path=source_path)
    collection = {file.src_path: file}

    def remove(selected):
        del collection[selected.src_path]

    def submit(worker, selected, path, config):
        # A warm-cache worker is completed before submission returns.
        selected.src_path = path
        selected.abs_src_path = path
        future = Future()
        future.set_result(selected)
        return future

    plugin = SimpleNamespace(config=SimpleNamespace(enabled=True, optimize=True, cache_dir="image-cache"), _is_excluded=lambda file: False, _optimize_image=None, pool_jobs={}, pool=SimpleNamespace(submit=submit))
    files = SimpleNamespace(media_files=lambda: list(collection.values()), remove=remove)

    namespace["on_env"](plugin, None, config=None, files=files)

    # Ownership and the reporting source path are preserved despite completion.
    assert collection == {}
    assert list(plugin.pool_jobs) == [source_path]
    assert plugin.pool_jobs[source_path].result() is file


@pytest.mark.parametrize("render_fails", [False, True], ids=["shared-result", "shared-error"])
def test_concurrent_cards_receive_the_submitted_layer_future(material_source, render_fails):
    dispatch = dispatch_from_source(patch_source(material_source))
    rendered = object()
    calls = []
    ready = threading.Barrier(8)

    def submit(render, layer, page, config):
        future = Future()
        calls.append(layer)
        if render_fails:
            future.set_exception(ValueError("layer rendering failed"))
        else:
            future.set_result(rendered)

        # Publication is delayed so other cards can request the shared layer.
        # In upstream code, an unfinished placeholder is exposed in this window.
        time.sleep(0.05)
        return future

    plugin = SimpleNamespace(card_layer_pool=SimpleNamespace(submit=submit), card_layer_pool_jobs={}, card_layer_pool_jobs_lock=threading.Lock(), _render=None)

    def card():
        ready.wait(timeout=5)
        dispatch(plugin, {"shared": "background"}, None, None)
        return plugin.card_layer_pool_jobs["shared"].result(timeout=1)

    with ThreadPoolExecutor(max_workers=8) as workers:
        cards = [workers.submit(card) for _ in range(8)]

        # Every card must finish with the actual result or rendering error.
        for future in cards:
            if render_fails:
                with pytest.raises(ValueError, match="layer rendering failed"):
                    future.result(timeout=5)
            else:
                assert future.result(timeout=5) is rendered

    assert calls == ["background"], "the shared layer must be submitted only once"
