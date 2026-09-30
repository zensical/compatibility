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

# Expansion analysis

## Selection

Prioritize plugins that share routing, metadata, generated source files or
final HTML. A failure there can affect links, search, feeds, cards and the
sitemap together. Use isolated controls, focused pairs and a few realistic
larger projects; an exhaustive power set would mostly duplicate coverage.

This pass adds **17 projects: four isolated controls and 13 combinations**,
plus one opt-in retained HTTP server lifecycle check. The full suite now has
74 projects: 57 isolated and 17 combinations, across 14 plugin names.
All original migration projects remain included.

New cases use multiple output extractors together. Publication checks include
the complete sitemap and search page membership, including pages omitted from
navigation. API checks include actual rendered content tokens, resolved links,
anchors and the Sphinx inventory. Social still compares decoded card pixels.

## Combinations exercised

| Area | Added projects | Risk exercised |
| --- | --- | --- |
| Routed blog links | Blog + autorefs; blog + redirects | References to source posts must resolve to final dated/slug routes, then change after a slug edit. |
| Navigation and publication | Blog + awesome-nav; blog + literate-nav | Hidden posts must remain published, searchable and present in the sitemap. A root SUMMARY page is published by both engines in this configuration. |
| Metadata, cards and feeds | Meta + social + RSS | Inherited titles/dates/colors must reach feeds and cards. |
| Publishing pipeline | Blog + meta + tags + social + RSS | Shared metadata edits, tag changes, slug changes and post deletion must agree across publication, tag catalog, feeds and cards. |
| Exclusion | Exclude + meta + social + RSS | A private draft must be absent from HTML, search, sitemap, feeds and cards. |
| API generation | api-autonav + mkdocstrings; mkdocs-autoapi + mkdocstrings | Generated pages must publish real handler output, object inventory and references; Python source edits/additions/deletions must update artifacts. |
| Generated API exclusion | api-autonav + mkdocstrings + awesome-nav + exclude, in both orders | Excluding a generated page must remove publication, search and inventory entries; hiding its navigation is a separate operation. |
| API summary resolution | mkdocs-autoapi + mkdocstrings + literate-nav + exclude | Generated summaries and exclusions can leave dangling links or fail strict mode. |
| Final HTML | Mkdocstrings + autorefs + minify + social | Minification must preserve API anchors, reference links, exact code whitespace and injected social metadata. |
| Retained server | Exclude + meta + social + RSS over HTTP | Inherited title/date/color edits, page insertion and deletion must update actual responses without restarting either server. Excluded/deleted pages must return 404. |

The four isolated controls cover autorefs aliases/closest targets, direct
mkdocstrings objects, exclude membership and minify protected code/comments.
API generators require the real mkdocstrings renderer, so those projects are
explicitly classified as combinations.

## Findings

Here, upstream means MkDocs, Material and their plugins. Verified improvements
in Zensical pass their contracts with exact expected differences.

Generated social-card attachments in RSS are deliberately outside the test
scope. Direct mkdocstrings Python-only cache invalidation is an existing known
issue; its mutation checks have been removed. The isolated renderer and
minify/social cases check cold and unchanged warm output.

| Priority | Observed behavior | Test status |
| --- | --- | --- |
| High | **Plugin order changes upstream API exclusion.** Exclude before api-autonav publishes the excluded secret module, including sitemap, search and inventory entries. Native excludes it in either order. Hidden navigation does not establish exclusion. | Ordered case passes; reversed case passes with the exact MkDocs-only artifact recorded as an expected difference. |
| High | **Retained upstream RSS accumulates items.** Metadata edits keep the previous version, subsequent rebuilds duplicate current items, and deletion keeps the deleted item. Native feeds contain only current published pages. | Passes with exact MkDocs item contents/counts, publication checks and pixels across all four checkpoints. |
| Medium | **AutoAPI default navigation/publication differs.** Upstream drops Home, flattens package children and publishes the generated summary; native preserves Home/children and treats generated summaries as controls. | Passes with exact navigation fields and one additional control-page membership recorded. |
| Medium | **AutoAPI exclusion can fail upstream strict mode.** The generated summary still links to the excluded module. Native builds successfully without the module. | Passes when MkDocs rejects with the specific missing-target warning and native output satisfies its contract on both builds. |
| Investigate | **Default upstream social concurrency hung twice** at the shared inherited-color rebuild, reaching the 120-second limit. Serial card rendering completed the pipeline. The cause and frequency are not established. | Saved failures remain failures; deterministic new composition fixtures explicitly set `social.concurrency: 1`. A separate bounded probe restores concurrency. |

Accepted improvements remain regression tests: native exclusions, current
feed items and corrected navigation are required. Changed/resolved differences,
timeouts, unrelated errors and other output regressions fail normally.
A specifically verified unsupported native behavior is reported as xfail.
No production Zensical files were changed in this pass.

The two default-concurrency timeout runs are retained under
`artifacts/fa86b9089eb44fa8919dd9f8368e7c2a/` and
`artifacts/3ff7988e0d304e478f13551f238c81be/`, at
`combinations/publishing/blog-meta-tags-social-rss/02-inherited-color/`.
Probe with:

```sh
.venv/bin/python -m scripts.probe_social_concurrency --timeout=20
.venv/bin/python -m scripts.probe_social_concurrency --concurrency=4 --timeout=20
```

The probe copies the project, retains provenance/logs/sites under a unique
artifact directory and propagates timeouts as failures. It is outside the
default gate because the observed hang is intermittent. The saved failures
used Material's default concurrency; a successful probe does not establish
that concurrent rendering is safe.

## Next priorities

| Priority | Expansion | Concrete checks |
| --- | --- | --- |
| 1 | Retained API servers | Module addition/removal/rename, new objects and backlinks; verify HTTP docstrings, inventory and search together. Include generated API sources outside docs and explicit watch paths. |
| 1 | Blog drafts and exclusions | Published-to-draft changes, future dates, navigation-hidden posts, excluded posts and inherited tags/dates; ensure feed, sitemap, search and cards lose the right pages. Fix the clock rather than testing relative to today. |
| 1 | URL modes across combinations | Repeat routed blog references/redirects and API inventory with flat URLs, nested roots, Unicode slugs, encoded spaces, query strings and fragments. Test publication below a site URL subpath. |
| 2 | Browser execution | Real redirect fragment forwarding; search clicks to generated/routed pages; autorefs preview after finalization; instant navigation between API/blog/tag pages. Inspect behavior in a browser, including console/network errors. |
| 2 | HTML and asset minification | JS/CSS file rewriting and cache-safe names with social/template output, inline script/data attributes, code tabs and math. Assert exact referenced asset existence and run scripts in a browser. |
| 2 | Social concurrency and cache dependencies | Concurrent cards sharing layer hashes, cached SVG/font/layout changes and deletion under serve. Preserve upstream/cache differences explicitly. |
| 2 | API feature boundaries | Cross-page backlinks, imported/re-exported objects, external inventories, multiple packages and namespace packages, selective members and custom templates. Start with a small representative Python package. |
| 3 | Configuration/platform coverage | Equivalent YAML/TOML settings on the native side; Linux/Python versions; disabled and multiple plugin instances; malformed settings and deterministic diagnostics. |

Priorities 1 and 2 can materially affect already published URLs or rendered
content. Browser checks and Linux coverage have not been established by this
local macOS run.

## Running and dependencies

```sh
.venv/bin/python -m pytest --combinations --serve
.venv/bin/python -m pytest --combinations --case=combinations/api/autonav-basic
.venv/bin/python -m pytest --combinations --case=combinations/rendering/api-minify-social
.venv/bin/python -m pytest tests/test_serve.py --serve
```

Upstream additions are pinned to [api-autonav 0.4.0](https://pypi.org/project/mkdocs-api-autonav/),
[AutoAPI 0.4.1](https://pypi.org/project/mkdocs-autoapi/),
[exclude 1.0.2](https://pypi.org/project/mkdocs-exclude/) and
[minify 0.8.0](https://pypi.org/project/mkdocs-minify-plugin/).
The candidate requires mkdocstrings/Python-handler/autorefs runtime dependencies,
locked separately in `requirements/candidate.txt` and installed automatically
with the default PyPI candidate. It uses its native API
generators, navigation, exclusion and minification implementations.

See [validation](validation.md) for the complete run, versions, counts and
artifact directory. Keep oracle upgrades separate from candidate regression
changes so a moving upstream baseline cannot silently alter the gate.
