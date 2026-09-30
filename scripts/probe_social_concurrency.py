# Copyright (c) 2026 Zensical and contributors

# SPDX-License-Identifier: MIT
# All contributions are certified under the DCO

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""Run the shared-layer social rebuild with upstream concurrency restored."""

import argparse
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import yaml

from compatibility.runner import environment, run_case, write_json
from scripts.prepare_candidate import prepare_candidate


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument(
        "--mkdocs-python", type=Path, default=root / ".environments/mkdocs/bin/python"
    )
    parser.add_argument(
        "--zensical-python",
        type=Path,
        default=None,
    )
    parser.add_argument("--zensical-version", default=None)
    args = parser.parse_args()
    if args.timeout < 1 or (args.concurrency is not None and args.concurrency < 1):
        parser.error("timeout and concurrency must be positive")
    if args.zensical_python and args.zensical_version:
        parser.error("choose --zensical-python or --zensical-version")
    candidate = args.zensical_python or prepare_candidate(args.zensical_version)
    source = root / "cases/combinations/publishing/blog-meta-tags-social-rss"
    spec = json.loads((source / "case.json").read_text())
    spec["steps"] = spec["steps"][:1]
    spec["timeout"] = args.timeout
    interpreters = {
        "mkdocs": args.mkdocs_python.absolute(),
        "zensical": candidate.absolute(),
    }
    output = root / "artifacts" / ("concurrency-" + uuid4().hex)
    output.mkdir(parents=True)
    write_json(
        output / "environments.json",
        {
            engine: environment(python, engine)
            for engine, python in interpreters.items()
        },
    )
    print(f"Concurrency probe artifacts: {output}", flush=True)
    with TemporaryDirectory(prefix="compatibility-concurrency-") as temporary:
        case = Path(temporary)
        shutil.copytree(source / "project", case / "project")
        config = case / "project/mkdocs.yml"
        value = yaml.safe_load(config.read_text())
        social = next(
            plugin["social"]
            for plugin in value["plugins"]
            if isinstance(plugin, dict) and "social" in plugin
        )
        social.pop("concurrency", None)
        if args.concurrency is not None:
            social["concurrency"] = args.concurrency
        config.write_text(yaml.safe_dump(value, sort_keys=False))
        # Timeouts and unrelated output changes remain failures. No retries or
        # expected-failure marker obscure intermittent concurrency behavior.
        run_case(case, spec, interpreters, output)


if __name__ == "__main__":
    main()
