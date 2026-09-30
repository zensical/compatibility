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

# Local validation

Validated on 2026-09-30 in `../compatibility`.

## Current scope

The suite contains **105 projects: 84 isolated and 21 opt-in combinations**,
plus 18 comparator/pixel guards, four search guards, two subprocess guards,
two font cache guards and two retained HTTP lifecycle tests.
All 44 original blog/social matrix projects remain included.

The RSS generated social-card attachment case has been removed. The known
direct mkdocstrings Python-only edit and recovery steps have been removed;
its isolated and minify/social rendering projects retain cold/warm checks.

Verified improvements over MkDocs and its plugins now count as passing tests
with exact expected differences. This includes API exclusion order, AutoAPI
navigation/control-file handling, successful native builds where an excluded
summary link causes MkDocs strict mode to reject, and current RSS feed items
under a retained server. The unsupported native social `page.file.src_uri`
context and visible metadata tags when the tags plugin is disabled are the
two declared xfails.

## Latest Material coverage verification

The complete run passed **131 tests with two expected xfails** in
**193.56 seconds** against Zensical 0.0.67 and MkDocs/Material 1.6.1/9.7.1.
This includes all 105 projects, combinations, both retained HTTP lifecycle
tests and all comparison/cache/process guards.

- **468 CLI builds across 234 checkpoints**: 437 successful exits, 31 required
  negative exits and no timeouts.
- Four retained development servers completed **20 HTTP snapshots** in total
  and shut down with exit code zero. The new metadata/tags/search test checks
  six snapshots per engine without restarting: inherited tag changes, search
  exclusion/restoration and page addition/deletion.
- The additional 12 projects cover Unicode tag/search routes, tag sorting and
  deduplication, filter changes, empty-catalog recovery, search title fallbacks
  and rich content, empty metadata values, BOM/alias handling, type conflicts,
  reversed plugin order and search with HTML minification.
- The headingless search title difference is accepted with exact engine-specific
  values; all remaining search fields are compared. The same two known xfails
  remain: custom social `page.file.src_uri` context and disabled tag labels.
- All 105 case contracts validate. Ruff, formatting, whitespace, full 2026
  license headers on new comment-capable files and local documentation links
  were checked. Generated output remains ignored.

Command:

```sh
.venv/bin/python -m pytest --combinations --serve -q --tb=short
```

Complete evidence: **`artifacts/a095957d11fd4c799500217d53b1ffd1/`**.
The focused retained HTTP run passed in 5.33 seconds in
`artifacts/561c657bd7934c969560cbe38929f46a/`.
This verification ran on macOS ARM64; Linux and Windows await hosted CI.

## First Material coverage verification

The expanded full run passed **118 tests with two expected xfails** in
**165.22 seconds** against Zensical 0.0.67 and MkDocs/Material 1.6.1/9.7.1.
This includes all 93 projects, combinations, the retained HTTP lifecycle test
and all comparison/cache/process guards.

- **400 CLI builds across 200 checkpoints**: 373 successful exits, 27 required
  negative exits and no timeouts. Both retained development servers completed
  their four HTTP checkpoints and shut down with exit code zero.
- The 19 new projects add nine tags controls/lifecycle/diagnostic cases, five
  search cases, three meta cases and two publishing combinations. The focused
  run passed 30 tests with one checked xfail before the full run.
- Search results now require an existing generated page and fragment. Four
  guards cover missing pages/anchors, percent-encoded targets and retargeting
  that the earlier page-level token aggregation could miss. Existing blog,
  RSS, API and publishing projects passed with this additional validation.
- The disabled-tags xfail checks the exact native label difference on cold and
  unchanged warm builds. The existing social template-context xfail remains.
  Native's removal of broken links with disabled tag listings passes with an
  exact expected difference; disabled search checks UI absence, empty content
  and the native empty-index output difference separately.
- Ruff, formatting and whitespace checks passed. All new comment-capable
  files carry the full 2026 MIT/SPDX/DCO header. Generated sites, fonts,
  environments and exploration scripts remain ignored.

Command:

```sh
.venv/bin/python -m pytest --combinations --serve -q --tb=short
```

Complete evidence: **`artifacts/3074c82804494bee9a36b80b15dd5b65/`**.
Focused evidence: `artifacts/6fe225e6855b4768984df5430d600b6e/`.
This verification ran on macOS ARM64; Linux and Windows await hosted CI.
See [expansion](expansion.md#material-expansion) for the new contracts and limits.

## CI portability verification

The workflow now runs independent Linux, macOS and Windows jobs. Each installs
Cairo for upstream SVG rendering and selects the platform's virtual environment
interpreter path. Windows configures Cairo DLL lookup through MSYS2. Builder
timeouts stop child processes, and server shutdown uses the platform's process
group signal with forced cleanup as a fallback. Text fixtures check out with LF
line endings on every platform.

CI no longer uploads generated sites or caches. Package versions, failing build
log tails, output contract values, unexpected diffs and pixel metrics appear in
the job output. Local runs continue to retain their full ignored artifacts.

The complete local macOS ARM64 run passed **96 tests with one expected xfail**
in **128.82 seconds**, including combinations, retained HTTP lifecycle checks
and two new subprocess guards. The guards verify that a timed-out builder's
descendant stops and that a failing build's Unicode diagnostic reaches the
failure report. Evidence is in
`artifacts/6bcdef82879a4cd78b4c283d0317f690/`.

Ruff, formatting, workflow YAML, embedded Bash syntax and actionlint 1.7.12
passed. Linux and Windows execution still require the first hosted matrix run.

## Initial verification against the published release

- **94 passed, 1 xfailed**, with no failures: all 74 CLI projects,
  18 comparator/pixel guards, two font cache guards and the retained HTTP
  lifecycle test.
- **284 CLI builds across 142 checkpoints**. Eleven nonzero exits were
  required by declared negative contracts; no build timed out.
- Two public development servers each completed four HTTP checkpoints for
  inherited metadata edits, page insertion and deletion. Excluded/deleted
  pages and cards returned 404. Search, feeds, sitemap, social metadata and
  decoded card pixels satisfied their contracts. Both servers shut down
  successfully.
- Final source cleanup organized imports, removed an obsolete script header
  and explicitly bound helper values inside loops.
- The default run installed the latest stable Zensical release from PyPI into
  `.environments/zensical`, with the reviewed API runtime lock enforced. The
  environment report confirms an installed package with no editable source
  or candidate checkout. Source receipts distinguish the oracle from the
  candidate.
- All 74 case contracts, migration destinations and downloaded font checksums
  validated. Ruff and formatting checks passed. Workflow YAML and embedded
  shell blocks validated.
- A fresh live download verified the pinned Roboto 2.138 archive and unpacked
  12 fonts plus their upstream license into ignored `.cache/fonts/`. Cache
  reuse and repair work offline; altered archives are rejected. Font binaries
  and the former root `assets/` directory are absent from commit contents.
- All 430 files with comment syntax carry the full MIT/SPDX/DCO header copied
  from `../zensical`, changing only the copyright year to 2026. Fixture
  Markdown keeps the header inside YAML front matter comments, with an
  explicit empty mapping where needed, to preserve titles and excerpts.
- All 514 files eligible for the initial commit were inspected. No generated
  environments, build artifacts, caches, removed examples or excluded cases
  are included. Text files have no trailing whitespace or missing newlines;
  local documentation links resolve. Inventory counts now match the matrix.

Command:

```sh
.venv/bin/python -m pytest --combinations --serve --junitxml=artifacts/junit.xml -q --tb=short
```

Complete evidence: **`artifacts/2c2e7e40160d43a1bf94c602a6e86509/`**.
The run completed in **127.74 seconds**, including candidate preparation.
Reports preserve environments, input hashes, copied projects, logs, exact
manifests/differences, pixel metrics and
actual HTTP responses. Artifacts are ignored by Git. HTTP tests require local
socket access and `--serve`.

The pinned-release option and refresh of an existing candidate environment
were also verified with `--zensical-version=0.0.67` and the directory-URL
redirect case: 21 passed (including comparator/font guards), with the HTTP
test skipped because `--serve` was omitted. Evidence is in
`artifacts/0e3d0e9ef58c433b916b9a69617f2670/`.

The final staged whitespace check removed extra terminal blank lines from
15 meta/tags fixtures. Both affected projects and the comparator/font guards
passed again (22 passed, HTTP test skipped) in
`artifacts/d2b3126bc1124555aef3c13953820727/`.

The earlier complete source-checkout validation is preserved in
`artifacts/c326a5eaa99b4c419d5d1a65b5b118eb/` (94 passed, 1 xfailed).
The earlier focused verification is preserved in
`artifacts/dea841211a254a9181b1e04cf564cd63/` (24 passed, 1 xfailed).
The historical expanded run in
`artifacts/5f8429b2f4754c07b4fa2fdfbaff5082/` included the subsequently removed
checks and previous xfail labels. It is superseded by the complete run above.

## Candidate and oracle

| Component | Tested version |
| --- | --- |
| Runner / oracle Python | 3.12.9 |
| Candidate Python | 3.12.9 |
| Zensical | 0.0.67 |
| Candidate source | Latest stable PyPI release, installed in `.environments/zensical` |
| MkDocs / Material oracle | 1.6.1 / 9.7.1 |
| Oracle / runner Pillow | 12.1.1 |
| Oracle CairoSVG | 2.8.2 |
| Downloaded font fixture | Roboto 2.138 unhinted release archive |
| mkdocstrings / Python handler | 1.0.6 / 2.0.9 |
| autorefs / griffelib | 1.4.4 / 2.3.0 |
| api-autonav / AutoAPI oracle | 0.4.0 / 0.4.1 |
| exclude / minify oracle | 1.0.2 / 0.8.0 |

RSS uses the unchanged pinned upstream source revision from the migration.
Full installed packages and direct-source provenance are in the environment
report. The candidate is the published macOS ARM64 package. Its loaded native
extension SHA-256 was:

```text
3df8183449e3b7896eab53bee07cd5405c609669d89ef8cc63b88e74ed57992d
```

## Earlier experiments and limits

The initial migrated baseline passed **69 tests with one verified xfail**
across 186 builds. Its evidence remains in
`artifacts/70fa6a498b214b04ad047a4bcf9a2ad4/`.

Default upstream social concurrency timed out twice at the shared inherited
color rebuild. Those failures remain recorded in the expansion analysis;
timeouts are never treated as expected failures. The new deterministic
publishing projects use `concurrency: 1`. The separate concurrency probe was
validated with `--concurrency=1 --timeout=20`, completing all six CLI builds in
`artifacts/concurrency-31d0296d671a47d99ab7ccffb4901e91/`. That validation does
not resolve the default-concurrency hang.

These are local macOS ARM64 runs. Browser execution, retained API generators
under serve, full search behavior, Linux, Windows and hosted CI remain
unverified. The initial validation ran before the initial commit; CI portability
was validated locally afterward.
