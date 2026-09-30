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

# Reproduction migration

Migrated on 2026-09-30 from `~/Desktop/Reproductions`. The originals remain
untouched. [inventory.json](inventory.json) records sources and destinations.
Each active case also names its source in `case.json`.

## Active projects

| Source | Destination | Coverage |
| --- | --- | --- |
| `zensical-blog-parity/cases` | 21 isolated blog cases and one combination | Routing, dates, drafts, authors, views, pagination, excerpts, full text, links, images, navigation, three invalid configurations and edit/delete scenarios |
| `zensical-social-parity/regression/cases` | 20 isolated social cases and two combinations | Metadata, paths, dimensions, decoded pixels, layouts, filtering, instances, cached SVG/title/layout edits and unsupported custom context |
| `plugin-blog` | `plugins/blog/showcase` | Connected authors, categories, archives and pagination |
| `plugin-social` | `plugins/social/showcase` | Bundled layouts, images, opt-out, exclusions and warm builds |
| `plugin-tags` | `plugins/tags/hierarchical-listings` | Hierarchy, shadow tags, fragments, filters, scope, targets, TOC, search and export boundary |
| `plugin-meta` | `plugins/meta/deep-inheritance` and smaller `inheritance` case | Inheritance, sequences, aliases, nulls, prefix boundaries and private bookkeeping |
| `plugin-rss` | `combinations/rss/blog-showcase` and two isolated cases | Three instances with blog authors; RSS, JSON Feed, stylesheets and a date edit |
| `plugin-redirects` | Three isolated cases | Directory/flat URLs, five redirect forms and missing targets |
| `plugin-awesome-nav` | `plugins/awesome-nav/nested-navigation` | Nested controls, sorting, globbing and exclusions |
| `plugin-literate-nav` | `plugins/literate-nav/nested-navigation` | Nested summaries, implicit indexes, wildcards and hierarchy |

The initial migration supplied **57 projects: 53 isolated and four combinations**.
The [expansion](expansion.md) adds 17 projects, bringing the current suite to
**74 projects: 57 isolated and 17 combinations**.
Multiple instances of one plugin remain isolated tests. Search can be enabled
as infrastructure; the tags showcase checks its search integration explicitly.
Select combinations with `--combinations`.

## Portability changes

- The old blog runner imported a removed `scripts/blog_oracle.py` from the
  candidate. The licensed extractor now lives in `compatibility/blog.py`.
  Both builders use their public installed CLIs.
- Three blanket blog case exceptions were replaced with exact field/value
  pairs. Empty pagers, continuation ancestors and copied configuration files
  previously normalized away are also recorded as exact differences.
- Category ordering uses a local callable with upstream's post-count behavior
  and canonical identity. Both engines receive the same module and YAML;
  Material is not required in the candidate merely to deserialize the config.
- The blog demo's broken related-link path was corrected to `index.md`:
  this metadata field resolves from `docs_dir` in both engines.
- Roboto fonts and their upstream license are downloaded from a pinned release
  into ignored `.cache/fonts/`; `requirements/fonts.json` locks their hashes.
  Font binaries are not included in the repository. Both builder caches are
  seeded independently. The social demo cache moved to `social-cache`, outside
  the candidate's `.cache` cleanup.
- The meta demo's TOML became shared MkDocs YAML. Display-only macros became
  a JSON template probe. A nav entry for an absent source file was removed.
  Macros behavior is not claimed by this case.
- RSS pins upstream commit `1b5e630ed5121ef6f5f8261275dbaa77d10000ae` and its
  archive hash. Published 1.17.9 lacks the preserved stylesheet option;
  the source wheel omits integration modules. `prepare_oracle.py` verifies
  and installs unmodified source. Explicit channel images avoid its invalid
  default image URL of `None`.
- Generated sites, Python caches and absolute executable paths were excluded
  from fixture inputs. Adaptations are recorded in the affected case JSON.

See [differences.md](differences.md) for measured boundaries. Recorded
baseline differences do not establish universal plugin parity.

## Follow-ups

The suite covers CLI builds and output. Blog scenarios retain the original
clean rebuild behavior; social scenarios retain each plugin's external cache.
Those builds alone do not prove invalidation inside a retained `serve` process.
The optional `--serve` publishing check now verifies HTTP metadata edits,
page insertion/deletion and exclusion. Browser checks for actual redirects,
media controls, widgets and instant navigation remain follow-up work.

Local runs and CI default to the latest stable Zensical release from PyPI,
installed in an isolated environment. Hosted CI is prepared but has not run.
A later Zensical gate for unreleased changes should pass its
exact candidate interpreter or wheel and pin the compatibility repository
revision. Keep oracle upgrades separate from candidate regressions.
