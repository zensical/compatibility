# Zensical compatibility

End to end comparisons of MkDocs plugins and Zensical's native replacements.
Each case builds the same small project through both public CLIs in separate
environments, then checks the generated website or artifacts. No Zensical
implementation modules are imported into the test runner.

The suite contains **57 isolated projects** and **17 opt-in combinations**,
covering publishing, navigation, API references, exclusion and minification.
An optional HTTP lifecycle check exercises retained development servers.
All 44 preserved blog and social matrix projects have been migrated, along
with their plugin demos. See [migration notes](docs/migration.md) and
[the latest local validation](docs/validation.md). New combinations, findings
and the next priorities are in [the expansion analysis](docs/expansion.md).

## Run locally

Requires uv and Python 3.12 or newer. Set up the runner, MkDocs oracle and
downloaded fonts once:

```sh
cd ../compatibility
uv venv --python 3.12 .venv
uv pip sync --python .venv/bin/python --require-hashes requirements/runner.txt
uv venv --python 3.12 .environments/mkdocs
uv pip sync --python .environments/mkdocs/bin/python --require-hashes requirements/mkdocs.txt
.venv/bin/python scripts/prepare_oracle.py
.venv/bin/python scripts/prepare_fonts.py
.venv/bin/python -m pytest
```

Each test run installs the **latest stable Zensical release from PyPI** in
ignored `.environments/zensical/`, together with the locked API handler runtime.
This requires network access to check the latest release. The runner records
the resolved version, package location and native extension hash in the
artifacts. Collection and comparator-only tests do not prepare a candidate.

Select cases, collect the matrix, or pin a published release:

```sh
.venv/bin/python -m pytest --collect-only -q
.venv/bin/python -m pytest -k redirects
.venv/bin/python -m pytest --case=plugins/rss/multiple-instances
.venv/bin/python -m pytest --combinations
.venv/bin/python -m pytest --combinations --serve
.venv/bin/python -m pytest --zensical-version=0.0.67
.venv/bin/python -m pytest --zensical-python=/path/to/candidate/bin/python --junitxml=artifacts/junit.xml
```

`--zensical-python` uses an explicitly prepared environment and skips the PyPI
installation. For this override, install Zensical and the API runtime yourself:
`uv pip install --python /path/to/candidate/bin/python --require-hashes -r requirements/candidate.txt`.
Use either `--zensical-version` or `--zensical-python`.

The oracle uses MkDocs 1.6.1 and Material 9.7.1. RSS is pinned to the exact
upstream commit used by the preserved reproduction; the published RSS 1.17.9
package does not support its stylesheet option. Navigation plugin versions
are pinned from their [PyPI release pages](https://pypi.org/project/mkdocs-awesome-nav/)
and [literate-nav release page](https://pypi.org/project/mkdocs-literate-nav/).

Social uses Pillow 12.1.1 and CairoSVG 2.8.2. Roboto fonts and their license
are downloaded from the [upstream 2.138 release](https://github.com/googlefonts/roboto-2/releases/tag/v2.138)
and unpacked into ignored `.cache/fonts/`. `requirements/fonts.json` pins the
archive URL and SHA-256 hashes for the archive and required files. The runner
prepares missing fonts automatically and seeds each builder's cache with the
same bytes. Subsequent runs reuse the verified cache without network access;
font binaries are not stored in Git. CairoSVG requires the system Cairo
library (for example, `libcairo2` on Linux).

`prepare_oracle.py` verifies the RSS archive against the lock and installs
its unmodified source as editable: that upstream revision's wheel omits its
integration modules. Dependencies remain locked. Run it again after syncing
the MkDocs environment. The source and its archive provenance live under
`.environments/`.

## Results

Every run gets a new `artifacts/<run-id>/` directory. It contains environment
and package versions, the loaded Zensical native extension hash, input hashes,
both copied projects and generated sites, per-build logs and exit codes,
semantic JSON manifests, raw and unexpected diffs, and `summary.json`.
Pass `--artifacts=/path` to keep runs elsewhere. Results are never overwritten.

A success case requires both builds to succeed, satisfy its explicit output
assertions, and match the plugin's semantic manifest. A negative case requires
both engines to reject it with the expected diagnostic. Warm builds must
preserve their semantic output; mutation steps can require a visible change.
Builds time out after 120 seconds unless the case sets another limit.

Expected differences name an exact field, both exact values, and a reason.
They cannot accept an unrelated difference in that case. A changed or resolved
exception fails until the declaration is reviewed. Both raw manifests remain
available. Specific list membership/count differences retain checks on every
other item. Verified native improvements pass with their exact differences
checked. Known native output gaps are xfailed only after exact differences, all
other outputs, pixels and lifecycle contracts pass. Full theme assets and
HTML bytes are preserved but do not form a universal equality check.

Social also compares decoded card pixels, with a mean RGB error budget of 1.
The custom typography fixture allows 4 only for its two named cards. Cached
SVG differences require exact pixel hashes at the two affected checkpoints.
The unsupported `page.file.src_uri` case is reported as **xfail only after**
the oracle output and specific native rejection have passed their checks.
See [the observed differences](docs/differences.md) for the current boundaries.

The `--serve` check starts both public development servers and downloads
pages, search, feeds and cards through HTTP. It verifies inherited metadata
edits, page insertion/deletion and excluded-page HTTP 404s. It requires local
socket access and is skipped by default. Browser execution, redirects in a
browser and instant navigation remain follow-up work.

## Add a case

See [the case format](docs/cases.md). Put one plugin under
`cases/plugins/<plugin>/<case>/`. Declare all plugins explicitly so MkDocs
cannot add the default search plugin. Search may be included as infrastructure
when needed; interactions with it still require focused checks.

Combination cases live under `cases/combinations/` and run only with
`--combinations`. They use the same runner and checks. Keeping a separate
case tree makes plugin interactions explicit without generating every possible
combination.

## CI and dependency updates

The included GitHub Actions workflow tests the latest stable PyPI release by
default and uploads reports, logs, and generated sites even when tests fail.
The optional `workflow_dispatch` input `ref` builds a commit, tag, or branch
from `zensical/zensical` in its own environment instead. This workflow has
been prepared locally; it has not run in a hosted repository.
Enable the `combinations` and `serve` inputs for the extended checks; pull
requests and pushes run isolated cases by default.

The `.in` files hold reviewed direct pins; the `.txt` files lock transitive
dependencies and archive hashes. Update the oracle in a dedicated change and
review its output differences separately from candidate changes. Regenerate
the files using [uv's documented compile workflow](https://docs.astral.sh/uv/pip/compile/):

```sh
uv pip compile requirements/runner.in --universal --python-version 3.12 --generate-hashes -o requirements/runner.txt
uv pip compile requirements/mkdocs.in --universal --python-version 3.12 --generate-hashes -o requirements/mkdocs.txt
uv pip compile requirements/candidate.in --universal --python-version 3.10 --generate-hashes -o requirements/candidate.txt
```
