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

# Image optimization coverage

Image optimization is covered by 15 isolated cases and one privacy combination. Independent copies are built through both public CLIs. Cold and unchanged warm output are compared.

`pngquant` must be available on `PATH` for PNG cases. Pillow is included in the pinned runner and oracle environments. A candidate containing native optimize support is required.

```sh
.venv/bin/python scripts/patch_material.py
.venv/bin/python -m pytest tests/test_optimize.py tests/test_plugins.py --combinations -k optimize --zensical-python=../zensical-zensical/.venv/bin/python
```

## Cases

| Case | Contract |
| --- | --- |
| `defaults` | Default JPEG quality, progressive scans, grayscale, PNG metadata removal, transparency, unreferenced files, nested URLs, and unsupported resources are checked. |
| `configured` | Baseline JPEG scans, quality 85, PNG speed 10, retained metadata, concurrency 1, reporting controls, and a custom cache directory are configured. |
| `disabled`, `optimization-disabled`, `formats-disabled` | Invalid image bytes must be copied unchanged when processing is disabled. |
| `png-disabled`, `jpg-disabled` | One image format is optimized while the other is copied unchanged. |
| `include-precedence` | Include patterns are given precedence over exclusions. Unmatched images are copied unchanged. |
| `exclude-patterns` | Wildcards, character classes, nested paths, and Unicode exclusions are checked. |
| `cache-disabled` | Warm output and quality changes are checked with persistent cache reuse disabled. |
| `source-edits` | Cached output must be replaced after a source image with different dimensions is copied over the original. |
| `quality-zero` | Minimum JPEG quality is checked through the emitted quantization table. |
| `png-no-gain` | Original bytes must be retained when PNG quantization would increase file size. |
| `corrupt-jpeg` | A selected corrupt JPEG must be rejected with an image diagnostic by both CLIs. |
| `multiple-instances` | Overlapping selections must be claimed by the first matching instance, as in the existing RSS multiple-instance fixture. |
| `privacy-optimize` | Local and downloaded JPEGs are optimized. Rewritten URLs and zero warm HTTP requests are checked together. |

Theme PNGs are excluded with `assets/images/*` so image processing is confined to fixture inputs. The reviewed Material 9.7.1 oracle patch removes file ownership before workers are submitted. An intermittent file-collection error is prevented when a warm-cache worker changes the source path immediately. Image encoding and selection settings are preserved. Source hashes guard the patch, its receipt is validated in environment reports, and completed-worker dispatch is covered by a deterministic test. The patch must be reviewed or removed when Material is updated.

## Observation boundaries

Image observations are configured in each project's `optimize-probes.json`. Published paths are mapped to source paths, including remote fixture sources. Optional `cache_dirs` entries are checked for cached files beyond `manifest.json`.

Asset membership, source hashes, byte preservation, size reduction, dimensions, image format, color mode, progressive scans, JPEG luminance quantization tables, PNG text metadata, EXIF presence, ICC profile presence, and alpha extrema are compared. Marked image URLs are retained, and local targets must exist.

JPEG bytes and exact decoded pixels are excluded from cross-engine comparison because different encoders are used. Decoded RGB content is checked against each source with a maximum per-channel mean error of 40. A bound of 90 is declared for quality zero. Dimensions and decoded alpha values must be preserved exactly. Resizing, recoloring, transparency loss, corrupt output, broken URLs, and ignored encoder settings are covered by extractor tests.

Unchanged warm manifests establish stable semantics. Cache population is observed, but internal cache hits and byte stability across builds are not established. Reporting options and concurrency are configured without assertions about log formatting or worker counts. Serve mode, uppercase extension differences, CMYK conversion, and invalid PNG backend diagnostics are outside these cases.

## Validation

The 16 paired cases and 30 supporting checks were run on Linux on 2026-10-28 with Python 3.14.9, MkDocs 1.6.1, Material 9.7.1, and a development Zensical 0.0.72 candidate. All **46 checks passed**. Full collection with combinations produced **389 tests**. Windows and macOS execution were not checked locally.
