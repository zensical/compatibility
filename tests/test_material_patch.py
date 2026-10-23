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
import subprocess
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.patch_material import patch_material, patch_source


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

    with pytest.raises(RuntimeError, match="review the social futures patch"):
        patch_material(Path("unused-python"))


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
