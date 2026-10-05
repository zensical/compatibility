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

# Observed differences

These are specific baseline boundaries, not whole-case exemptions. Exact
pairs live in `case.json`; changed or resolved pairs fail until reviewed.

| Surface | Current contract |
| --- | --- |
| Blog home titles | Native retains the configured navigation label; upstream usually shows only the site title. Exact titles remain checked. |
| Blog navigation labels | `navigation-title` and `root-flat` preserve specific heading/configuration differences. |
| Empty blog / pagers | Exact empty archive and empty pager differences are recorded. Routes and contents remain compared. |
| Continuation ancestors | Native retains a view label upstream omits on some author/archive/category continuation pages. |
| Blog raw HTML assets | Native resolves assets from the post source directory; upstream uses the generated route or view. Exact URL and excerpt fields are recorded. |
| Authors YAML | Upstream publishes `blog/people.yml`; native treats it as internal configuration. Other output files remain compared. |
| Meta bookkeeping | Public metadata matches; native omits Material's private `__extends`. |
| Tags export | Native deliberately omits the configured legacy JSON export. |
| Tags hierarchy / shadow listings | The demo records exact child heading-depth and default shadow-membership differences. Named shadow listings stay observed. |
| Disabled tags | In Zensical 0.0.67, `tags.enabled: false` still renders metadata tag labels. The isolated control checks the exact visible label difference on cold/warm builds before reporting xfail. |
| Disabled search | Native emits an empty search index; MkDocs emits no index. Both remove the UI and all indexed sections. Exact index presence remains checked. |
| Headingless search titles | Native uses the explicit navigation label for the root search result; Material uses the front matter title. The exact title pair is checked; section content and targets remain compared. |
| Audio controls | Upstream adds controls even when disabled. Native honors `audio_controls: false`; only the exact controls flags are accepted differences. |
| Inline media text | Upstream replacement drops following text from Markdown and raw HTML, including the search index. Native preserves and indexes it; only the named trailing tokens may differ. |
| RSS blog summaries | Four description fields differ only in whitespace between heading and paragraph. |
| Social typography | Only two named cards allow mean RGB error 4 instead of 1; measured maximum is about 3.636. Metadata, paths and sizes must match. |
| Social cached SVG | Upstream retains red pixels after the SVG edit; native renders blue. SVG/title checkpoints require one exact decoded pixel pair plus separate lifecycle expectations. Layout editing returns to normal comparison. |
| Social custom context | Oracle must emit both cards and `page.file.src_uri` metadata; native must reject with its layout-expression undefined-value diagnostic. Only then is this case xfailed. Other diagnostics, timeouts, native success and oracle failures fail normally. |

## Expansion findings

These MkDocs/plugin differences describe verified improvements in Zensical.
Their tests pass after validating exact differences and all other contracts:

| Surface | Verified behavior |
| --- | --- |
| API generation and exclude order | Putting exclude before api-autonav publishes the excluded module upstream, including search and inventory. Native excludes it in either order. |
| AutoAPI defaults | Upstream omits Home, collapses package children and publishes generated summary Markdown as a page. Native retains the hierarchy and treats generated summaries as control files. |
| AutoAPI + literate-nav + exclude | Upstream generated summary retains the excluded link and fails strict mode with the specific missing-target warning. Native builds without that API page. |
| Retained HTTP RSS | Upstream retains old item versions, duplicates current items on rebuilds and keeps deleted-page items. Native emits only current published pages. Exact item contents and occurrence counts are checked at each checkpoint. |
| Disabled tag listings | Material links a tag label to a missing listing fragment. Native keeps the label unlinked. The exact MkDocs link and native absence remain checked. |

The new publishing compositions use `social.concurrency: 1`. Default upstream
concurrency timed out twice during the shared inherited-color rebuild; those
failures remain failures in the saved experiment runs. See [expansion](expansion.md)
for evidence and a bounded concurrency probe. No timeout is treated as xfail.

## Semantic normalization

- Internal links are resolved before comparing destinations; queries and
  fragments remain checked.
- Blog excerpt whitespace is collapsed. Permalink controls, page tag badges
  and the reserved `__skip` heading ID are excluded from visible text/IDs.
  Full post text, headings, links and images remain checked. View-level theme
  prev/next traversal and theme/search implementation files are outside this
  extractor; post relations remain observed.
- RSS channel build timestamps and generator strings are omitted. Item dates,
  content and order remain checked. Field order is canonicalized without
  reordering repeated items or categories.
- Material uses a set for equally close tag targets. Ties are sorted for
  comparison; membership, nearer-before-farther ranking and the primary
  rendered link's membership in the nearest group are enforced.
- Social compares decoded pixels, independent of PNG encoding. Full images
  remain in artifacts.

- Navigation ignores an empty child `<nav>` container, preserving every
  actual child, label, link and group. Links resolve from the real homepage
  canonical URL, including site URL subpaths.
- Search comparison aggregates records by page URL and checks explicit
  fixture tokens in `publication`, after validating every published page and
  fragment target. The focused `search` extractor retains section titles,
  full locations, tags and per-section fixture tokens. Segmentation, ranks and
  full search-engine equivalence are outside these contracts; complete original
  indexes remain in artifacts.
- Material's private metadata `__extends` paths use `/` in reports on every
  operating system. The full inheritance path sequence remains checked.
- RSS item enclosures are observed separately from other child fields so
  missing attachments cannot shift description/date/link pointers. Repeated
  enclosures keep their original order and attributes.
- HTTP server binding origins are restored to the shared fixture `site_url`
  before semantic comparison. Paths, queries and fragments stay intact;
  actual bind URLs and downloaded HTTP responses are recorded.
