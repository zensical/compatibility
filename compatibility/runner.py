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

"""Build copied projects through public CLIs and retain comparison evidence."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

import yaml

from compatibility import blog, macros, media, search, social, tags
from compatibility.checks import CHECKS
from compatibility.publication import publication, references, tag_content
from scripts.prepare_fonts import prepare_fonts

EXTRACTORS = {
    **CHECKS,
    "blog": blog.extract,
    "media": media.extract,
    "social": social.extract,
    "search": search.extract,
    "search-config": search.configuration,
    "tags": tags.extract,
    "publication": publication,
    "references": references,
    "tag-content": tag_content,
    "macros-diagnostics": macros.diagnostics,
}


def check_names(spec: dict) -> list[str]:
    names = spec["check"]
    return [names] if isinstance(names, str) else names


def observe(site: Path, spec: dict) -> dict:
    names = check_names(spec)
    values = {name: EXTRACTORS[name](site) for name in names}
    return values[names[0]] if isinstance(spec["check"], str) else values


def render(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(path: Path, value: object) -> None:
    path.write_text(render(value), encoding="utf-8")


def pointer(value: object, path: str) -> object:
    # RFC 6901 preserves empty keys, including the homepage search location.
    for part in path[1:].split("/") if path else []:
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def replace(value: dict, path: str, expected: object) -> None:
    parent, _, key = path.rpartition("/")
    target = pointer(value, parent)
    key = key.replace("~1", "/").replace("~0", "~")
    target[int(key) if isinstance(target, list) else key] = expected


def compare(left: dict, right: dict, differences: list[dict]) -> str:
    """Accept only exact, documented pairs at individual JSON pointers."""
    left = json.loads(render(left))
    right = json.loads(render(right))
    for rule in differences:
        assert rule["reason"].strip(), "expected difference needs a reason"
        if "member" in rule:
            first = pointer(left, rule["path"])
            second = pointer(right, rule["path"])
            assert isinstance(first, list) and isinstance(second, list)
            value = rule["member"]
            counts = (rule["mkdocs"], rule["zensical"])
            assert (
                counts[0] != counts[1]
                and (first.count(value), second.count(value)) == counts
            ), f"expected member counts changed at {rule['path']}"
            values = first if counts[0] > counts[1] else second
            for _ in range(abs(counts[0] - counts[1])):
                values.remove(value)
            continue
        membership = [
            engine for engine in ("mkdocs", "zensical") if f"{engine}_only" in rule
        ]
        if membership:
            assert len(membership) == 1, "membership difference needs one engine"
            engine = membership[0]
            expected = rule[f"{engine}_only"]
            selected, other = (left, right) if engine == "mkdocs" else (right, left)
            values = pointer(selected, rule["path"])
            opposite = pointer(other, rule["path"])
            assert isinstance(values, list) and isinstance(opposite, list), (
                "membership differences require lists"
            )
            assert values.count(expected) == 1 and expected not in opposite, (
                f"expected membership difference changed at {rule['path']}: {expected!r}"
            )
            values.remove(expected)
            continue
        missing = object()
        actual = []
        expected = []
        for engine, manifest in (("mkdocs", left), ("zensical", right)):
            absent = rule.get(f"{engine}_missing", False)
            try:
                value = pointer(manifest, rule["path"])
            except KeyError:
                if not absent:
                    raise
                value = missing
            actual.append(value)
            expected.append(missing if absent else rule[engine])
        assert expected[0] != expected[1], "difference must describe unequal values"
        assert actual == expected, (
            f"expected difference changed at {rule['path']}: {actual!r}; "
            f"expected {expected!r}. {rule['reason']}"
        )
        if expected[0] is missing:
            parent, _, key = rule["path"].rpartition("/")
            del pointer(right, parent)[key.replace("~1", "/").replace("~0", "~")]
        else:
            replace(right, rule["path"], rule["mkdocs"])
    return "".join(
        difflib.unified_diff(
            render(left).splitlines(keepends=True),
            render(right).splitlines(keepends=True),
            fromfile="mkdocs.json",
            tofile="zensical.json",
        )
    )


def environment(python: Path, module: str) -> dict:
    """Record installed distributions and the actual native extension bytes."""
    command = """
import hashlib, importlib.metadata as md, importlib.util, json, platform, subprocess, sys
from pathlib import Path
module = sys.argv[1]
spec = importlib.util.find_spec(module)
info = {'python': sys.executable, 'prefix': sys.prefix,
        'python_version': sys.version, 'platform': platform.platform(),
        'module': spec.origin if spec else None,
        'packages': {d.metadata['Name']: d.version for d in md.distributions()},
        'direct_sources': {d.metadata['Name']: json.loads(value)
                           for d in md.distributions()
                           if (value := d.read_text('direct_url.json'))}}
receipt = Path(sys.prefix).parent / 'oracle-source.json'
if module == 'mkdocs' and receipt.is_file():
    info['oracle_source'] = json.loads(receipt.read_text())
candidate_receipt = Path(sys.prefix) / 'compatibility-candidate.json'
if module == 'zensical' and candidate_receipt.is_file():
    info['candidate_source'] = json.loads(candidate_receipt.read_text())
if module == 'zensical' and spec and spec.submodule_search_locations:
    info['native_extensions'] = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for root in spec.submodule_search_locations for p in Path(root).glob('*')
        if p.suffix in {'.so', '.pyd'}
    }
    parents = () if Path(spec.origin).is_relative_to(Path(sys.prefix)) else Path(spec.origin).parents
    for parent in parents:
        if (parent / '.git').exists():
            info['checkout'] = {
                'path': str(parent),
                'commit': subprocess.check_output(['git', '-C', str(parent),
                           'rev-parse', 'HEAD'], text=True).strip(),
                'status': subprocess.check_output(['git', '-C', str(parent),
                           'status', '--porcelain'], text=True),
            }
            break
print(json.dumps(info))
"""
    result = subprocess.run(
        [str(python), "-c", command, module],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        env=process_environment(),
    )
    info = json.loads(result.stdout)
    assert info["module"], f"{module} is not installed in {python}"
    return info


def process_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    for name in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(name, None)
    env.update(PYTHONNOUSERSITE="1", NO_COLOR="1", TZ="UTC")
    return env


def discover(root: Path, combinations: bool = False) -> list[Path]:
    groups = [root / "plugins"]
    if combinations:
        groups.append(root / "combinations")
    return sorted(path.parent for group in groups for path in group.rglob("case.json"))


def validate_case(case: Path, root: Path) -> dict:
    spec = json.loads((case / "case.json").read_text(encoding="utf-8"))
    assert spec.get("assertions") or spec.get("failure"), (
        "case needs an output contract"
    )
    failures = spec.get("failure", {})
    assert set(failures) <= {"mkdocs", "zensical"}, "unknown failure engine"
    if len(failures) == 1:
        assert spec.get("assertions") and spec.get("reason", "").strip(), (
            "an asymmetric rejection needs a successful output contract and reason"
        )
    for step in [{}, *spec.get("steps", [])]:
        gap = step.get("known_gap", spec.get("known_gap"))
        if gap is not None:
            assert gap.strip(), "known output gap needs a reason"
            assert not failures, "output gaps require successful builds"
            assert step.get("differences", spec.get("differences")), (
                "known output gaps require exact differences at every checkpoint"
            )
    names = check_names(spec)
    assert isinstance(names, list) and names and len(names) == len(set(names)), (
        "checks must be a nonempty unique list"
    )
    assert set(names) <= EXTRACTORS.keys(), f"unknown check in {case}"
    config = yaml.load(
        (case / "project" / "mkdocs.yml").read_text("utf-8"), Loader=yaml.BaseLoader
    )
    # Plugins are explicit: MkDocs must not add its default search plugin.
    assert isinstance(config.get("plugins"), list), "declare plugins explicitly"
    plugins = [next(iter(p)) if isinstance(p, dict) else p for p in config["plugins"]]
    subjects = set(plugins)
    if spec["plugins"] != ["search"]:
        subjects.discard("search")
    assert subjects == set(spec["plugins"]), f"plugin declaration mismatch: {case}"
    if case.relative_to(root).parts[0] == "plugins":
        assert len(subjects) == 1, f"isolated case enables several plugins: {case}"
    assert config.get("docs_dir", "docs") == "docs", "fixture docs_dir must be docs"
    assert config.get("site_dir", "site") == "site", "fixture site_dir must be site"
    for name in (".cache", "site"):
        assert not (case / "project" / name).exists(), (
            f"generated fixture input: {name}"
        )
    return spec


def check_build(outcome: dict, engine: str, phase: Path, failures: dict) -> None:
    path = phase / f"{engine}.log"
    log = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    tail = "\n".join(log.splitlines()[-80:])
    diagnostic = f"see {phase}\n{tail}"
    assert not outcome["timed_out"], f"{engine} timed out; {diagnostic}"
    if engine in failures:
        assert outcome["exit_code"] > 0, f"{engine} did not reject; {diagnostic}"
        assert re.search(failures[engine], log, re.IGNORECASE), (
            f"{engine} rejected for the wrong reason; {diagnostic}"
        )
    else:
        assert outcome["exit_code"] == 0, (
            f"{engine} build failed (exit {outcome['exit_code']}); {diagnostic}"
        )


def stop_process(process: subprocess.Popen, *, interrupt: bool = False) -> None:
    """Stop a builder and its descendants, allowing servers to close first."""
    if process.poll() is not None:
        return
    if interrupt:
        try:
            process.send_signal(
                signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT
            )
            process.wait(timeout=5)
            return
        except (OSError, subprocess.TimeoutExpired):
            pass
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=5)


def build(
    python: Path,
    engine: str,
    project: Path,
    phase: Path,
    *,
    clean: bool,
    strict: bool,
    timeout: int,
) -> dict:
    command = [str(python), "-m", engine, "build", "--config-file", "mkdocs.yml"]
    if clean:
        command.append("--clean")
    if strict:
        command.append("--strict")
    started = time.monotonic()
    with (phase / f"{engine}.log").open("w", encoding="utf-8") as log:
        with subprocess.Popen(
            command,
            cwd=project,
            stdout=log,
            stderr=log,
            env=process_environment(),
            start_new_session=os.name == "posix",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        ) as process:
            try:
                code = process.wait(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                stop_process(process)
                code, timed_out = None, True
        log.write(f"\nexit: {code}; timeout: {timed_out}\n")
    outcome = {
        "command": command,
        "cwd": str(project),
        "exit_code": code,
        "timed_out": timed_out,
        "seconds": round(time.monotonic() - started, 3),
    }
    write_json(phase / f"{engine}-build.json", outcome)
    return outcome


def mutate(project: Path, step: dict) -> None:
    def local(name: str) -> Path:
        result = project / name
        assert result.resolve().is_relative_to(project.resolve()), (
            "mutation escapes project"
        )
        return result

    for source, destination in step.get("copy", {}).items():
        target = local(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local(source), target)
    for name in step.get("remove", []):
        local(name).unlink()
    if "path" not in step:
        return
    path = local(step["path"])
    if step.get("delete"):
        path.unlink()
    else:
        before = path.read_text(encoding="utf-8")
        assert before.count(step["before"]) == 1, "mutation must match once"
        path.write_text(before.replace(step["before"], step["after"]), encoding="utf-8")


def run_case(
    case: Path, spec: dict, interpreters: dict[str, Path], output: Path
) -> None:
    projects = {}
    for engine in interpreters:
        project = output / engine
        shutil.copytree(case / "project", project)
        projects[engine] = project
    sources = {
        p.relative_to(case / "project").as_posix(): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in sorted((case / "project").rglob("*"))
        if p.is_file()
    }
    write_json(output / "inputs.json", sources)
    write_json(output / "case.json", spec)
    for seed in spec.get("seed", []):
        if seed["source"] == ".cache/fonts":
            prepare_fonts()
        source = Path(__file__).resolve().parents[1] / seed["source"]
        assert source.resolve().is_relative_to(Path(__file__).resolve().parents[1]), (
            "seed escapes repository"
        )
        hashes = {
            p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(source.rglob("*"))
            if p.is_file()
        }
        write_json(output / "seed-inputs.json", hashes)
        for project in projects.values():
            destination = project / seed["destination"]
            assert destination.resolve().is_relative_to(project.resolve()), (
                "seed escapes project"
            )
            shutil.copytree(source, destination)
    steps = [{"name": "cold", "clean": True}]
    if spec.get("warm"):
        steps.append({"name": "warm", "clean": False})
    steps.extend(spec.get("steps", []))
    previous = {}
    snapshots = {}
    for index, step in enumerate(steps):
        phase = output / f"{index:02}-{step['name']}"
        phase.mkdir()
        if any(key in step for key in ("path", "copy", "remove")):
            for project in projects.values():
                mutate(project, step)
        outcomes = {
            engine: build(
                python,
                engine,
                projects[engine],
                phase,
                clean=step.get("clean", False),
                strict=spec.get("strict", True),
                timeout=spec.get("timeout", 120),
            )
            for engine, python in interpreters.items()
        }
        for engine, outcome in outcomes.items():
            check_build(outcome, engine, phase, spec.get("failure", {}))
        if set(spec.get("failure", {})) == set(interpreters):
            continue
        manifests = {}
        for engine, project in projects.items():
            if engine in spec.get("failure", {}):
                continue
            assert (project / "site" / "index.html").is_file(), (
                f"{engine} homepage missing"
            )
            manifest = observe(project / "site", spec)
            assert manifest, f"empty manifest: {engine}"
            write_json(phase / f"{engine}.json", manifest)
            manifests[engine] = manifest
        # Write the unmodified diff even when an expected difference is accepted.
        raw_diff = (
            compare(manifests["mkdocs"], manifests["zensical"], [])
            if len(manifests) == 2
            else ""
        )
        (phase / "raw.diff").write_text(raw_diff, encoding="utf-8")
        for engine, manifest in manifests.items():
            for assertion in step.get("assertions", spec.get("assertions", [])):
                if assertion.get("engine", engine) != engine:
                    continue
                value = pointer(manifest, assertion["path"])
                assert (
                    len(value) == assertion["count"]
                    if "count" in assertion
                    else value == assertion["value"]
                ), (
                    f"{engine} contract failed at {assertion['path']}; see {phase}\n"
                    f"Expected: {render(assertion)}\nObserved: {render(value)}"
                )
            changed = step.get("changed")
            if isinstance(changed, dict):
                assert (manifest != previous[engine]) == changed[engine], (
                    f"{engine} output change contract failed"
                )
            elif changed:
                assert manifest != previous[engine], f"{engine} output did not change"
            if step["name"] == "warm":
                assert manifest == previous[engine], (
                    f"{engine} changed on unchanged build"
                )
        if len(manifests) != 2:
            write_json(
                phase
                / (
                    "known-gap.json"
                    if "zensical" in spec["failure"]
                    else "accepted-difference.json"
                ),
                {"failure": spec["failure"], "reason": spec["reason"]},
            )
            previous = manifests
            continue
        difference = compare(
            manifests["mkdocs"],
            manifests["zensical"],
            step.get("differences", spec.get("differences", [])),
        )
        (phase / "unexpected.diff").write_text(difference, encoding="utf-8")
        assert not difference, (
            f"compatibility regression; see {phase / 'unexpected.diff'}\n{difference}"
        )
        gap = step.get("known_gap", spec.get("known_gap"))
        if gap is not None:
            assert raw_diff, "known output gap resolved; review its declaration"
            write_json(phase / "known-gap.json", {"reason": gap})
        if "social" in check_names(spec):
            social_manifests = (
                manifests
                if isinstance(spec["check"], str)
                else {
                    engine: manifest["social"] for engine, manifest in manifests.items()
                }
            )
            visuals = social.compare_cards(
                projects["mkdocs"] / "site",
                projects["zensical"] / "site",
                social_manifests["mkdocs"]["cards"],
                spec.get("pixel_budgets", {}),
                step.get("pixel_differences", spec.get("pixel_differences", [])),
            )
            write_json(phase / "pixels.json", visuals)
            current = {
                engine: social.snapshot(project / "site", social_manifests[engine])
                for engine, project in projects.items()
            }
            write_json(phase / "snapshots.json", current)
            for engine, kinds in step.get("changes", {}).items():
                for kind, changed in kinds.items():
                    assert (
                        current[engine][kind] != snapshots[engine][kind]
                    ) == changed, (
                        f"{engine} {kind} lifecycle contract failed; see {phase}"
                    )
            if step["name"] == "warm":
                assert current == snapshots, "card pixels changed on unchanged build"
            assert all(value["accepted"] for value in visuals.values()), (
                f"card pixels differ; see {phase / 'pixels.json'}\n{render(visuals)}"
            )
            snapshots = current
        previous = manifests
