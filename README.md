# Zensical compatibility

End to end tests comparing MkDocs plugins with Zensical's native implementations.
Each case builds the same project through both public CLIs in separate
environments and checks the generated output.

The suite covers publishing, navigation, API references, tags, metadata,
search, exclusion, minification and audio/video, with isolated plugin cases, opt-in
combinations and HTTP lifecycle checks.

## Run locally

Requires uv and Python 3.12 or newer. Social tests need Cairo and FriBiDi
(`sudo apt-get install libcairo2 libfribidi0` on Linux, `brew install cairo fribidi`
on macOS). FriBiDi enables Pillow's Raqm text layout; its basic fallback renders
different typography. On macOS, expose both libraries before running:

```sh
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix cairo)/lib:$(brew --prefix fribidi)/lib"
```

Set up the runner and MkDocs baseline:

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

On Windows, use `Scripts/python.exe` instead of `bin/python` in these paths.
Set `PYTHONUTF8=1` and point `CAIROCFFI_DLL_DIRECTORIES` to the folder containing
your Cairo DLLs. Install `mingw-w64-ucrt-x86_64-cairo` and
`mingw-w64-ucrt-x86_64-fribidi` through MSYS2, and add its `ucrt64/bin` directory
to `PATH`. CI installs these automatically and verifies Raqm is available.

Test runs install the **latest stable Zensical release from PyPI** into
`.environments/zensical/`, together with the locked API runtime and Windows
timezone data. Checking the latest release requires network access.
Collection and comparator-only tests
do not prepare a candidate.

Select cases or enable extended checks:

```sh
.venv/bin/python -m pytest --collect-only -q
.venv/bin/python -m pytest -k redirects
.venv/bin/python -m pytest --case=plugins/rss/multiple-instances
.venv/bin/python -m pytest --combinations --serve
```

Pin a release with `--zensical-version=VERSION`, or use an existing candidate
with `--zensical-python=/path/to/candidate/bin/python`. Existing candidates
need Zensical and the API runtime from `requirements/candidate.txt` installed.
Choose one of these options.

The MkDocs baseline, candidate runtime and fonts are pinned under `requirements/`.
Fonts are downloaded into ignored `.cache/fonts/`, verified and reused by both
builders. Run `prepare_oracle.py` again after syncing the MkDocs environment
to restore the pinned RSS source.

## Results

Each run creates `artifacts/<run-id>/` with package versions, native extension
and input hashes, copied projects, generated sites, logs, manifests, diffs and
a summary. Use `--artifacts=/path` to choose another location and
`--junitxml=artifacts/junit.xml` for a JUnit report.

Cases assert output contracts and compare semantic manifests. Social cards
also undergo decoded pixel comparisons. Expected differences must match
their declared values; unrelated changes and timeouts fail. Known gaps are
reported as xfail only after their contracts pass. See
[the documented differences](docs/differences.md) for details.

`--serve` checks pages, metadata, tags, search, feeds and cards over HTTP while
editing, adding and deleting content. It requires local socket access. Browser
execution and instant navigation are not covered.

## Add a case

See [the case format](docs/cases.md). Put one plugin under
`cases/plugins/<plugin>/<case>/`. Declare all plugins explicitly so MkDocs
cannot add the default search plugin. Search may be included as infrastructure
when needed; interactions with it still require focused checks.

Put plugin interactions under `cases/combinations/`; these run with
`--combinations` and use the same runner and checks. See
[the expansion analysis](docs/expansion.md) for coverage priorities.
See [media coverage](docs/media.md) for the audio/video cases and playback checks.

## CI and dependency updates

The GitHub Actions workflow tests the latest stable PyPI release on Linux,
macOS and Windows. Versions, failing build logs and unexpected diffs appear
in the job output. Generated sites and caches are not uploaded.
Pull requests and pushes run isolated cases. Manual runs can enable
`combinations` and `serve`, or set `ref` to build a commit, tag or branch from
`zensical/zensical` instead.

The `.in` files hold reviewed direct pins; the `.txt` files lock transitive
dependencies and archive hashes. Update the oracle in a dedicated change and
review its output differences separately from candidate changes. Regenerate
the files using [uv's documented compile workflow](https://docs.astral.sh/uv/pip/compile/):

```sh
uv pip compile requirements/runner.in --universal --python-version 3.12 --generate-hashes -o requirements/runner.txt
uv pip compile requirements/mkdocs.in --universal --python-version 3.12 --generate-hashes -o requirements/mkdocs.txt
uv pip compile requirements/candidate.in --universal --python-version 3.10 --generate-hashes -o requirements/candidate.txt
```
