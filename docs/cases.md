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

# Case format

Each case contains an immutable `case.json` and a complete `project/` with
`mkdocs.yml`, `docs/`, and any local assets or template overrides. Both engines
receive separate copies. The runner preserves virtual environment interpreter
paths, strips inherited Python import paths, and records the package versions
actually used. Plugins are enabled only through public configuration.

```text
cases/plugins/redirects/directory-urls/
├── case.json
└── project/
    ├── mkdocs.yml
    └── docs/
```

Example:

```json
{
  "plugins": ["redirects"],
  "check": "redirects",
  "warm": true,
  "assertions": [
    {"path": "/redirects/old~1index.html/canonical", "value": "../new/"}
  ]
}
```

Paths are JSON pointers: `/` in a property name is written as `~1`, and `~`
as `~0`. Array elements use their numeric index. Assertions apply to both
engines at every successful checkpoint. They prevent equal but empty output
from passing. A homepage must also exist in every successful build.

| Field | Meaning |
| --- | --- |
| `plugins` | Distinct plugins under test; exactly one in an isolated case |
| `check` | Extractor name, or a list of unique extractor names checked together |
| `source` | Optional provenance relative to the preserved reproduction tree |
| `strict` | Abort on warnings; defaults to true |
| `timeout` | Seconds allowed per CLI build; defaults to 120 |
| `warm` | Repeat the build with the same project and cache |
| `assertions` | Exact `value` or collection `count`; optional `engine` selector |
| `steps` | Ordered replacements, copies or deletions in both copied projects |
| `differences` | Exact intentional differences at individual manifest fields |
| `failure` | Engine-specific diagnostic patterns for an expected rejection |
| `reason` | Required explanation for an asymmetric expected failure |
| `known_gap` | Reason for verified output differences, declared on a case or affected step |
| `purpose` | Behavior or interaction the fixture exercises |
| `environment` | Optional `MIKE_DOCS_VERSION` for versioned builds; the inherited value is cleared |
| `seed` | Repository-owned inputs copied to each project's cache |
| `pixel_budgets` | Social per-card mean RGB allowance and reason; default 1 |
| `pixel_differences` | Social exact decoded RGBA hash pair and reason |

Mutation example:

```json
{
  "name": "edit-title",
  "path": "docs/news/release.md",
  "before": "# Release announcement",
  "after": "# Revised release announcement",
  "changed": true
}
```

Each replacement must match once. A deletion uses `"delete": true`. Mutations
default to builds without `--clean`, retain each engine's own cache, and must
stay inside that engine's copied project. Use `"clean": true` explicitly for
a full rebuild. Unchanged warm output is enforced; it does not prove that an
internal cache hit occurred. Plugin-specific cache probes belong in extractors.

A step may declare `changed` as engine booleans, for example
`{"mkdocs": true, "zensical": false}`, to verify a specific stale-cache gap.
With multiple checks, manifests are keyed by extractor name; prepend that
name to assertion/difference pointers, e.g. `/publication/search/` observes
the empty-string homepage search location. Social pixel/lifecycle checks still
run when social is one of several extractors.

A step may instead specify `copy` as source/destination paths and `remove`
as a list of paths. Step `assertions`, `differences` and `pixel_differences`
override those declarations for that checkpoint. Social step `changes` maps
each engine to `pages`/`cards` booleans, so a known stale upstream cache can
require unchanged pixels while native must change. Warm social builds also
require unchanged decoded card pixels.

Expected difference example:

```json
{
  "path": "/navigation/0/title",
  "mkdocs": "Heading",
  "zensical": "Configured label",
  "reason": "Zensical preserves an explicit navigation label."
}
```

The exact pair must still occur at every affected checkpoint. Keep exceptions
small: do not exempt a whole page, whole case, routes, or all output HTML.

For a single additional list item use `mkdocs_only` or `zensical_only` with
its exact value. The item must occur exactly once in the named engine and
be absent from the other. A `member` rule uses `mkdocs` and `zensical` as exact
occurrence counts for one exact list member. Every other list member and
its order remain compared. These declarations allow a known additional
control page or duplicated feed item without exempting the route/feed list.

A missing object key can be declared with `mkdocs_missing: true` or
`zensical_missing: true` instead of that engine's value. An undeclared missing
field still fails, and a resolved absence requires reviewing the exception.

Declare both engines in `failure` for an ordinary negative case. Declaring
one engine requires a successful output contract and `reason`. A MkDocs-only
rejection passes after the specific diagnostic and successful native output
have been checked. A native-only rejection reports xfail after validating its
diagnostic and the oracle output. An unrelated error, timeout or resolved
rejection remains a failure.

`known_gap` requires successful builds and nonempty exact differences at each
affected checkpoint. Pytest reports xfail after all phases and checks succeed.
A gap on a mutation step does not excuse a cold/warm mismatch or a failure
to recover on a later clean rebuild. Removing or changing a known difference
fails until its declaration is reviewed.

Font seeds use `source: .cache/fonts` and a destination such as
`social-cache/fonts`. The runner downloads missing fonts using
`scripts/prepare_fonts.py` and `requirements/fonts.json`, records seed hashes
and copies fonts into independent caches. The repository's `.cache/fonts`
directory is ignored by Git. Keep the copied destination outside the builder's
`.cache` if its clean build removes that directory.

Extractors currently observe redirect targets and fragment-forwarding code;
navigation routes, labels, URLs and hierarchy; RSS/JSON Feed fields and item
order and stylesheet references; and inherited page metadata. RSS channel
build dates and generator labels are excluded, while item dates are compared.
RSS field order is canonicalized while item and category order is preserved.
Private Material metadata
bookkeeping is observed separately with exact documented differences.

Blog observes ordered view memberships, dates, authors, categories, excerpt
HTML, full visible text, headings, links, images, routes and navigation.
Social observes page metadata, card paths/dimensions, decoded pixels and
cached edits. Tags observes listing hierarchy/membership, filtered targets,
custom fragments, TOC, nearest tag links, search inclusion and export presence.
See [observed differences](differences.md) for normalization boundaries.

`search` observes index presence, per-page search UI, section titles, complete
result locations, tags and explicit fixture tokens. It checks every result's
page and fragment against the generated HTML, including percent-encoded paths
and anchors. `search-config` checks the emitted separator expression in cases
that configure it explicitly. Search scores, tokenization and browser query
execution are outside these CLI contracts.

`publication` checks canonical URLs, HTML route membership, all sitemap URLs,
search page membership and explicit fixture tokens, plus exact HTML probes
and selected comments. `references` checks actual rendered autorefs links,
object anchors, content tokens, unresolved references and decoded Sphinx
inventory entries. `tag-content` observes catalog headings, ordered listing
links, page tag labels/references and TOC links. Multiple extractors let a
combination check all its outputs together. `publication` validates search
targets before aggregating page membership and fixture tokens.

Future plugin extractors should read generated output or deterministic fixture
probes. Do not call private generator APIs. Use real local data files, fixed
dates, and local image/font assets. A browser check is required to establish
browser execution, widget behavior, redirect execution, or live navigation;
the generated HTML checks alone cannot establish those behaviors.

Macros output is checked with `publication` probes and paired cold/warm builds. Template edits are applied without a clean build. Diagnostic headings, source files, exception messages, and syntax-error source lines are checked by `macros-diagnostics`. Traceback presence and the final exception are retained; builder paths and stack frames are excluded.

Markdown transformations are observed by `content`, including callouts, tables, code, headings, and visible text. Image links and lightbox attributes are observed by `lightbox`. Generated Markdown and text files are compared by `llmstxt`. Worker shims and inline search consistency are checked by `offline`. Their observation boundaries and plugin settings are described in [plugin coverage](plugin-coverage.md).
