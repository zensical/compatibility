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

"""Check that plugin output differences remain observable."""

import json

import pytest

from compatibility import rendering
from compatibility.runner import compare


def test_content_preserves_callout_state_code_whitespace_and_table_order(tmp_path):
    # Text shared by different callout types must remain distinguishable.
    (tmp_path / "index.html").write_text('''<article class="md-content__inner">
<h1 id="home">Home<a class="headerlink">¶</a></h1>
<details class="tip" open><summary>Advice</summary><p>Read this.</p></details>
<pre><code>first  second\n  third</code></pre>
<table><tr><th>Name</th></tr><tr><td>Beta</td></tr><tr><td>Alpha</td></tr></table>
</article>''')

    manifest = rendering.content(tmp_path)

    assert manifest["index.html"]["headings"] == [{"level": "h1", "id": "home", "text": "Home"}]
    assert manifest["index.html"]["code"] == ["first  second\n  third"]
    assert manifest["index.html"]["tables"] == [[["Name"], ["Beta"], ["Alpha"]]]
    assert manifest["index.html"]["alerts"] == [{"kind": "details", "classes": ["tip"], "title": "Advice", "text": "Advice Read this.", "open": True}]

    # A changed expansion state is detected even when the visible text agrees.
    changed = json.loads(json.dumps(manifest))
    changed["index.html"]["alerts"][0]["open"] = False

    assert '"open"' in compare(manifest, changed, [])


def test_lightbox_observes_wrapping_captions_and_skipped_images(tmp_path):
    (tmp_path / "index.html").write_text('''<article>
<a class="glightbox" href="full.svg" data-title="Caption" data-width="80%"><img src="small.svg" alt="Preview"></a>
<img class="off-glb" src="plain.svg" alt="Plain">
</article>''')

    images = rendering.lightbox(tmp_path)["index.html"]

    assert images[0]["link"] == {"class": ["glightbox"], "href": "full.svg", "data-title": "Caption", "data-width": "80%"}
    assert images[1]["link"] is None


def test_llmstxt_preserves_exports_text_order_and_missing_files(tmp_path):
    (tmp_path / "guide").mkdir()
    (tmp_path / "llms.txt").write_text("# Site\n\n- Beta\n- Alpha\n")
    (tmp_path / "guide/index.md").write_text("# Guide\n\n    spaced  code\n")

    before = rendering.llmstxt(tmp_path)
    (tmp_path / "guide/index.md").unlink()
    after = rendering.llmstxt(tmp_path)

    assert before["llms.txt"]["text"] == "Site Beta Alpha"
    assert before["guide/index.md"]["structure"][1]["children"][0]["children"] == ["spaced  code\n"]
    assert "guide/index.md" in compare(before, after, [])


def test_llmstxt_normalizes_markdown_spelling_but_preserves_targets(tmp_path):
    path = tmp_path / "llms.txt"
    path.write_text("# Site\n\n- [Guide](https://example.com/guide.md): A_B\n\n")
    before = rendering.llmstxt(tmp_path)

    path.write_text("# Site\n\n- [Guide](<https://example.com/guide.md>): A\\_B\n")

    assert rendering.llmstxt(tmp_path) == before

    # A changed link target is retained despite equivalent Markdown syntax.
    path.write_text("# Site\n\n- [Guide](<https://example.com/wrong.md>): A\\_B\n")

    assert "wrong.md" in compare(before, rendering.llmstxt(tmp_path), [])

    # Spaces between inline elements remain meaningful after normalization.
    path.write_text("**First** **Second**\n")
    spaced = rendering.llmstxt(tmp_path)
    path.write_text("**First****Second**\n")

    assert rendering.llmstxt(tmp_path) != spaced


def test_offline_rejects_stale_inline_search_data(tmp_path):
    (tmp_path / "search").mkdir()
    (tmp_path / "index.html").write_text('<script src="https://unpkg.com/iframe-worker/shim"></script>')
    (tmp_path / "search/search_index.json").write_text('{"docs": [{"text": "Current"}]}')
    script = tmp_path / "search/search_index.js"
    script.write_text('var __index = {"docs": [{"text": "Current"}]}')

    manifest = rendering.offline(tmp_path)

    assert manifest == {"inline_search": True, "shims": {"index.html": ["https://unpkg.com/iframe-worker/shim"]}}

    # Stale inline output must fail even when both builders emit a script.
    script.write_text('var __index = {"docs": [{"text": "Stale"}]}')

    with pytest.raises(AssertionError, match="differs from the JSON index"):
        rendering.offline(tmp_path)
