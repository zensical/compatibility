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

"""Diagnostic extraction is checked with generated HTML examples."""

import pytest

from compatibility.macros import diagnostics
from compatibility.runner import compare


def test_diagnostic_tracebacks_preserve_exception_and_page_details(tmp_path):
    # The same exception is displayed with different builder stack frames.
    for engine in ("mkdocs", "zensical"):
        site = tmp_path / engine
        site.mkdir()
        (site / "index.html").write_text(
            '<article class="md-content__inner">'
            '<h1><em>Macro Rendering Error</em><a>¶</a></h1>'
            '<p><em>File</em>: <code>index.md</code></p>'
            '<p><em>ZeroDivisionError</em>: division by zero</p>'
            '<pre><code>Traceback (most recent call last):\n'
            f'  File "/{engine}/renderer.py", line 42, in render\n'
            'ZeroDivisionError: division by zero\n</code></pre>'
            '</article>',
            encoding="utf-8",
        )

    first = diagnostics(tmp_path / "mkdocs")
    second = diagnostics(tmp_path / "zensical")

    # Page details and the final exception are retained in both manifests.
    assert first == second == {
        "pages": {
            "index.html": {
                "heading": "Macro Rendering Error",
                "paragraphs": ["File: index.md", "ZeroDivisionError: division by zero"],
                "code": [{"traceback": True, "exception": "ZeroDivisionError: division by zero"}],
            }
        }
    }

    # An unrelated diagnostic change must still be reported.
    second["pages"]["index.html"]["code"][0]["exception"] = "ValueError: changed"
    assert "ValueError: changed" in compare(first, second, [])


def test_syntax_diagnostic_retains_source_and_line_message(tmp_path):
    # Source code is retained instead of a traceback in syntax diagnostics.
    (tmp_path / "index.html").write_text(
        '<article class="md-content__inner">'
        '<h1>Macro Syntax Error</h1>'
        '<p>File: index.md</p>'
        '<p>Line 2: Expected an expression</p>'
        '<pre><code>{% if %}\n</code></pre>'
        '</article>',
        encoding="utf-8",
    )

    observed = diagnostics(tmp_path)

    assert observed["pages"]["index.html"] == {
        "heading": "Macro Syntax Error",
        "paragraphs": ["File: index.md", "Line 2: Expected an expression"],
        "code": [{"source": "{% if %}"}],
    }


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("<h1>Outside the article</h1>", "page content is missing"),
        ('<article class="md-content__inner"><p>Body</p></article>', "diagnostic heading is missing"),
    ],
)
def test_missing_diagnostic_content_is_rejected(tmp_path, content, message):
    # Missing diagnostic structure must be rejected.
    (tmp_path / "index.html").write_text(content, encoding="utf-8")

    with pytest.raises(AssertionError, match=message):
        diagnostics(tmp_path)
