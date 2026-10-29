# Privacy coverage

Privacy is covered by 45 complete projects: 31 isolated cases and 14 opt-in combinations. The added image optimization combination is described in [image optimization coverage](optimize.md). The pinned Material 9.7.1 plugin and a Zensical candidate containing privacy support are exercised through their public CLIs. Source projects are copied independently for both builders.

## Settings and combinations

| Area | Coverage |
| --- | --- |
| Activation and links | Default activation, disabled instances, `assets`, `links`, `links_attr_map`, and `links_noopener`. Absolute same-host anchors and fragment-only links are distinguished. |
| Fetching and diagnostics | Default downloading, report-only mode, strict rejection, disabled logging, error-level filtering, and followed redirects. |
| Filtering | Include-before-exclude behavior, the upstream report-only early return, excluded URLs, and repeated instances with separate output roots. |
| Cache and concurrency | Cold/warm requests, `cache: false`, custom cache and output directories, populated custom caches, repeated image references, and concurrency values 1, 2, and 4. |
| Dependency discovery | Local and remote CSS/JavaScript, recursively referenced fonts and JSON, extensionless stylesheet responses, query digests, protocol-relative URLs, and shared image fragments. |
| Python expressions | Custom extension mappings, lookbehind, backreferences, and UTF-8 capture offsets. Invalid expressions are rejected. |
| Templates and routes | Configured CSS/module scripts, SVG image references, icon/preload/preconnect elements, theme logos/favicons, extra templates, raw HTML boundaries, flat/directory URLs, nested routes, `site_url` subpaths, and 404/500 templates. |
| Generated and unpublished content | Macros, both include-markdown orders, blog views/posts with metadata inheritance, core exclusion, plugin exclusion, and excluded CSS. |
| Other output stages | Both Glightbox orders, HTML minification with search, external minification with and without content hashes, offline search, and social metadata/card pixels. |

## Local HTTP fixtures

A local origin is declared by `http.directory`, relative to the immutable source `project/`. Files are served from that directory. The directory and explicit response sources must remain inside the source project. The virtual origin `http://privacy.test` is served through a shared loopback HTTP proxy. Its socket is assigned an ephemeral port. The server is stopped when the case completes, including on failure.

`http://privacy.test` and protocol-relative `//privacy.test` URLs are retained in both project copies. `PRIVACY_FIXTURE_HOST` is replaced with `privacy.test` for host/path filters. The stable authority is required because authorities are used as asset filenames by Material, and colons in host:port names are invalid on Windows.

Proxy variables and empty proxy-bypass variables are supplied only to the builder subprocesses. Their values are recorded in the existing build artifacts. HTTP requests for other origins are rejected by the fixture proxy instead of forwarded. No public asset service is required by these cases.

Optional `http.routes` entries are selected by exact request target or path. Each entry may specify `file`, `content_type`, `status`, or `location`. Extensionless font stylesheets and redirects are provided through these entries. The font payloads are deterministic fixture bytes; browser font decoding is outside these checks.

Asset GET requests are recorded in `<engine>-http.json` at each phase. Absolute-form HTTP proxy requests and restricted CONNECT tunnels are served locally; proxy handshakes are not counted as asset downloads. The virtual origin, actual binding, request paths, and query strings are retained. Request contracts are declared by phase name under `http.requests`:

```json
{
  "http": {
    "directory": "remote",
    "requests": {
      "cold": {"/image.png": 1},
      "warm": {}
    }
  }
}
```

The same contract is applied to both engines. Separate `mkdocs` and `zensical` request maps may be supplied when an engine-specific contract is required. Build failures are reported through the existing diagnostic checks before request-count mismatches are considered.

## Output contracts

Marked elements are selected with `data-privacy`. Their element names, attributes, and text are retained. Related script, image, SVG image, and link references are also observed outside marked content, including theme templates.

Downloaded files under `http.asset_roots` are observed; `assets/external` is used by default. Additional local assets are selected with `http.local_assets` globs. CSS dependency URLs, static JavaScript string values, custom text, and binary SHA-256 hashes/sizes are compared. Rewritten asset references must resolve to files inside the generated site.

Populated cache directories may be required with `http.cache_dirs`. Cache reuse is checked through actual zero-request warm contracts, rather than inferred from unchanged output. Network observations are recorded separately from semantic manifests so both conditions can be enforced. The extensionless font stylesheet case is run without strict mode to permit the upstream Windows symlink fallback. Its warm request count is retained, but no assumption about symlink permissions is imposed.

Only the actual fixture binding authority is normalized across selected extractors; the stable virtual origin is retained. Redundant leading `./` prefixes and six-character fingerprint spellings are normalized in privacy URLs. Each fingerprint is checked against emitted bytes, and validity is retained in the manifest. Static backtick and quoted JavaScript strings are treated equally. CSS/JavaScript execution is outside these contracts.

Cold/warm output is required to remain unchanged. An image URL is also replaced without a clean build in `source-mutation`, where a new request and changed output are required. Dynamically assembled JavaScript URLs are deliberately retained without requests, matching the upstream observation boundary.

## Exact observed differences

Five fixtures are reported as xfail only after their output contracts, warm builds, requests, and all undeclared fields have passed:

- Shared upstream image fragments are accumulated; each native image fragment is retained independently.
- Custom extension dependencies are discovered upstream, but only CSS/JavaScript are patched. Custom media are also patched natively.
- A remote CSS dependency is retained by upstream cached minification; it is localized before native hashing/minification.
- Default Glightbox wrapper attributes and href presence differ. Both plugin orders are covered by separate fixtures.

Exact field pairs are declared in each `case.json`. Downloaded bytes, local target validity, and unrelated output are still compared. These pairs are also listed in [observed differences](differences.md).

## Run the cases

The isolated cases are included in the normal suite. All privacy combinations can be selected with a privacy-capable candidate:

```sh
.venv/bin/python -m pytest tests/test_plugins.py --combinations -k privacy --zensical-python=/path/to/privacy-candidate/bin/python
.venv/bin/python -m pytest tests/test_privacy.py
```

Comparator guards cover port normalization, changed attributes and binary bytes, missing targets, CSS/JS references, content-hash validity, fixture substitution, MIME overrides, request recording, path containment, rejected foreign origins, and server shutdown.

## Validation

Validation was completed on 2026-10-19 with Python 3.14.8, MkDocs 1.6.1, Material 9.7.1, and a candidate built from the `feature/support-privacy-plugin` worktree. The 44 paired cases and plugin coverage guard produced **40 passed and 5 xfailed**, with no failures. The extractor, HTTP fixture, comparator, and process guards produced **26 passed**.

Paired build artifacts were retained in `artifacts/3daf40dc59ed43da88a3511e39cb6444/`. Three existing non-HTTP cases were also checked during staging: minification, offline search, and include-markdown source edits. Full collection with combinations produced **358 tests**. The stable-host proxy transport was exercised with absolute-form HTTP requests and CONNECT tunnels. No Windows execution is claimed by this local Linux run. Ruff checks passed for all changed Python modules.
