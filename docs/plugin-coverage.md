<!--
Copyright (c) 2026 Zensical and contributors

SPDX-License-Identifier: MIT
All contributions are certified under the DCO

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
-->

# Plugin coverage

All 27 plugins from the [published compatibility list](https://zensical.org/docs/compatibility/mkdocs/plugins/index.md) are covered. The list was checked on 2026-10-07. Coverage is also provided for development support of `mkdocs-nav-weight`, `markdownextradata`, `include-markdown`, and `privacy`.

Each project is built through both public CLIs in separate environments. Observable contracts are checked before the complete semantic manifests are compared. Cold and unchanged warm builds are checked in the new cases. Focused input changes are applied without a clean build where mutation steps are declared.

API generators are tested with their required `mkdocstrings` renderer under `cases/combinations/`. These cases are enabled with `--combinations`. Coverage of every listed plugin is enforced by `test_supported_plugins_have_successful_output_contracts`.

| Plugin configuration name | Isolated cases | Combination cases | Observed behavior and settings |
| --- | ---: | ---: | --- |
| `api-autonav` | 0 | 3 | Generated module pages, custom roots, exclusions, navigation, and source changes. |
| `autorefs` | 3 | 2 | Aliases, nearest targets, routed targets, and enabled or external-only tooltips. |
| `awesome-nav` | 5 | 5 | Nested navigation, control files, sorting, hidden pages, core inclusion patterns, and exclude-plugin interactions. |
| `blog` | 23 | 8 | Routes, dates, authors, categories, archives, excerpts, pagination, mutations, and core versus metadata drafts. |
| `callouts` | 3 | 1 | Alert types, explicit titles, lists, folded blocks, literal fenced examples, and included callouts. |
| `exclude` | 4 | 8 | Globs, regular expressions, recursive paths, publication, core inclusion patterns, navigation plugins, generated API exclusions, and included unpublished sources. |
| `gh-admonitions` | 2 | 0 | GitHub alert types, custom titles, formatted bodies, and literal fenced examples. |
| `glightbox` | 4 | 0 | Automatic and manual wrapping, skipped classes, captions, dimensions, and page opt-out. |
| `include-markdown` | 15 | 6 | Directives, paths, nested sources, custom syntax, indentation, encoding, disabled output, fenced code, Snippets settings, URL modes, options, plugin order, and edits. |
| `literate-nav` | 4 | 4 | Nested summaries, control files, indexes, labels, core inclusion patterns, directory inference, and exclude-plugin interactions. |
| `llmstxt` | 4 | 0 | Sections, globs, export hosts, URL modes, descriptions, aggregate output, and edits. |
| `macros` | 27 | 2 | Variables, modules, includes, precedence, page selection, titles, diagnostic modes, and include-markdown with default or custom Jinja syntax. |
| `markdown-exec` | 5 | 0 | Python execution, Markdown results, ANSI configuration, and selected languages. |
| `markdownextradata` | 7 | 1 | Configuration context, data directories, precedence, scalar types, delimiters, titles, data edits, and included expressions. |
| `meta` | 8 | 8 | Inheritance, merge behavior, aliases, disabled output, invalid inputs, metadata edits, and core inclusion patterns. |
| `mike` | 3 | 0 | Unversioned and versioned builds, canonical aliases, and version-selector settings. |
| `minify` | 2 | 3 | Preserved code whitespace, comment settings, search, and API/social combinations. |
| `mkdocs-audio` | 4 | 3 | Default and custom markers, MIME types, playback attributes, disabled output, and media combinations. |
| `mkdocs-autoapi` | 0 | 2 | Source discovery, ignored files, generated references, inventories, and source changes. |
| `mkdocs-nav-weight` | 12 | 2 | Weights, section indexes, hidden pages, reverse sorting, labels, strict warnings, metadata edits, and core inclusion patterns. |
| `mkdocs-video` | 4 | 3 | Iframes, native video, custom markers, playback attributes, disabled output, and media combinations. |
| `mkdocstrings` | 2 | 6 | Handler output, object references, inventories, member order, source display, and API generators. |
| `offline` | 3 | 0 | Flat URLs, worker shims, inline search consistency, search absence, and disabled output. |
| `privacy` | 31 | 13 | Asset fetching, cache/request controls, filters, Python expressions, fragments, template resources, URL modes, error templates, and plugin combinations. |
| `redirects` | 4 | 1 | Directory and flat URLs, external and routed targets, missing targets, and unlisted targets. |
| `rss` | 3 | 4 | Multiple feeds, filtering, dates, stylesheets, disabled output, core inclusion patterns, and publishing combinations. |
| `search` | 34 | 0 | Sections, titles, exclusions, separators, encoded paths, disabled output, mutations, and core inclusion patterns. |
| `section-index` | 3 | 0 | Linked section landing pages, nested sections, directory or flat URLs, and core inclusion patterns. |
| `social` | 21 | 6 | Layouts, typography, metadata, filtering, pixels, disabled output, and mutations. |
| `table-reader` | 5 | 1 | CSV, JSON, YAML, reader selection, path lookup, arguments, missing files, edits, and included reader expressions. |
| `tags` | 14 | 6 | Scalars, ordering, hierarchy, filters, listings, disabled output, invalid inputs, mutations, and core inclusion patterns. |

## File inclusion settings

`exclude_docs`, `draft_docs`, and `not_in_nav` are covered by 42 fixtures: 38 isolated cases and four plugin combinations. Existing extractors and the paired CLI runner are used.

Patterns are checked with directory and flat URLs, anchored paths, recursive directories, character classes, escaped prefixes, Unicode paths, and ordered negations. Default exclusions and restorations are checked for pages and resources. Null, empty, and invalid configuration values are also checked.

Publication routes, sitemap URLs, search tokens, navigation hierarchy, and `nav.pages` membership are checked together. Explicit navigation, pairwise overlaps, and precedence across all three settings are covered. Unchanged warm builds, configuration edits, additions, deletions, and edits to unpublished sources are checked.

The settings are combined with `exclude`, `awesome-nav`, `literate-nav`, `mkdocs-nav-weight`, `section-index`, tags, metadata, RSS, redirects, blog drafts, and `include-markdown`. Resource membership is checked with `llmstxt`; extra-template evaluation is checked through the public CLI diagnostic.

Preview inclusion and draft markers are outside these build contracts. Expected plugin and URL differences are recorded in [Observed differences](differences.md).

The inclusion cases can be selected against a development candidate:

```sh
.venv/bin/python -m pytest tests/test_plugins.py --combinations -k inclusion --zensical-python=../zensical-zensical/.venv/bin/python
```

## Include-markdown settings

The baseline is pinned to `mkdocs-include-markdown-plugin==7.3.0`. Both directives are checked with quoted spaces, multiline tags, docs-relative paths, source-relative paths, repeated includes, nested sources, and sources outside `docs/`.

Global dedenting, includer indentation, Latin-1 source encoding, disabled output, custom delimiters, renamed directives, and fenced code are checked. Native Snippets settings are combined with the plugin: `base_path`, `restrict_base_path`, `check_paths`, `auto_append`, and `dedent_subsections`.

Included links and images are checked with directory and flat URLs, including `rewrite-relative-urls=false`. Global heading offsets and per-inclusion section boundaries and heading offsets are checked against the exact native output.

Combinations are provided for macros, custom Jinja delimiters, Jinja includes, Markdown extra data, table-reader, callouts, tables, search, and exclusion settings. Included expressions and excluded sources are edited without clean builds. Search tokens, publication routes, and navigation are checked for included sources excluded by `exclude_docs`, `draft_docs`, or the exclude plugin.

Remote downloads, HTTP watch behavior, glob includes, and untested options are outside these contracts. The exact observed gaps are recorded in [Observed differences](differences.md).

The include cases can be selected against a development candidate:

```sh
.venv/bin/python -m pytest tests/test_plugins.py --combinations -k include-markdown --zensical-python=../zensical-zensical/.venv/bin/python
```

## Privacy settings

Privacy is covered by 44 fixtures: 31 isolated cases and 13 combinations. Cold and unchanged warm output are compared through both public CLIs. Actual HTTP requests, custom cache-directory population, and emitted asset bytes are checked against local fixture data.

The settings are combined with minification and content hashes, search, Glightbox, include-markdown, macros, offline search, exclusion, blog metadata, and social cards. Theme logo/favicon configuration, extra CSS/scripts, extra templates, nested routes, site URL subpaths, and HTTP error templates are covered.

The local server protocol, extraction boundaries, known differences, and selection command are described in [privacy coverage](privacy.md). A development candidate containing privacy support is required.

## Observation boundaries

Callout element types, classes, titles, bodies, and expansion states are retained by `content`. Exact fenced-code whitespace, table cell values and order, headings, and visible text are also compared. Theme heading controls are excluded.

Image wrapping and all anchor attributes are compared by `lightbox`, including captions, dimensions, and skipped images. JavaScript execution, animation, and browser interaction are not established by these HTML checks.

All generated `.md` and `.txt` files are parsed and compared by `llmstxt`. Equivalent Markdown escaping, link delimiters, and block spacing are normalized. File membership, element structure, inline spacing, link targets, and exact code whitespace are retained. Offline search data is decoded and checked against each builder's JSON index before script presence and worker-shim references are compared.

Mike's build-time behavior is tested with an explicit `MIKE_DOCS_VERSION`. The variable is cleared from inherited environments and recorded for cases that set it. Remote deployment, alias publishing, and browser version switching are outside these build contracts.

The known differences discovered by the cases are described in [Observed differences](differences.md). Exact field pairs are required; whole pages and cases are not excluded from comparison.

The new branch cases require a candidate containing both `edbaf55` (nav-weight) and master commit `8e96dd1` (markdownextradata), or later equivalents. A temporary combined candidate was built from copies of those branches for local validation.

## Validation

The 21 include-markdown fixtures and the plugin coverage guard were run against `../zensical-zensical` on 2026-10-13 with Python 3.14.8. The result was **11 passed and 11 xfailed**, with no failures. Artifacts were retained in `artifacts/9ade05ad58ce4b42ae0994fe1e2acc39/`. Full-suite collection with combinations also passed: **305 tests collected**.

The expected failures cover preprocessing order, URL rewriting, ignored heading and section options, discarded indentation, and explicit Snippets settings. Exact output pairs or the specific rejection diagnostic are required before xfail is reported. Cold and unchanged warm builds are checked for every case; source and data changes are checked where declared.

The 41 file inclusion fixtures were run against `../zensical-zensical` on 2026-10-09 with Python 3.14.8. The result was **36 passed and 5 xfailed**. Artifacts were retained in `artifacts/50effdfd5d9245e894b993f9c4f7e5c3/`. Final fixture cleanup was rechecked with **12 passed and 1 xfailed**, retained in `artifacts/a1dfb8a0b2a440d1ab52ed726e372ad3/`. Full-suite collection and the plugin coverage guard also passed.

The five expected failures cover awesome-nav glob membership in two fixtures, literate-nav unpublished links, and leading-exclamation URL encoding in both URL modes. Exact differences and unchanged warm output are required before xfail is reported. The three asymmetric rejection cases passed after their MkDocs diagnostics and successful native outputs were checked.

The 58 added projects and the coverage guard were run against the combined candidate with Python 3.14.8. The result was **55 passed and 4 xfailed**. Artifacts were retained in `artifacts/a4917568269a4a83960822ac1ea9071d/`.

The four expected failures cover three differences: page-level lightbox opt-out, previous-page links in hidden weighted sections, and cached CSV edits. Exact differences and clean CSV recovery are required before xfail is reported.

The full suite was also run with `--combinations`: **230 passed, 8 xfailed, 2 skipped, and 3 failed**. Retained HTTP checks were skipped because `--serve` was not enabled. The failures were 120-second MkDocs timeouts in the existing `social/basic`, `social/filters`, and `social/paths` cases. Similar upstream concurrency timeouts are documented in [the expansion analysis](expansion.md). These failures were retained in `artifacts/e03d5231f11a467a9231c49401f5f28e/`; no timeout was reclassified as an expected failure.
