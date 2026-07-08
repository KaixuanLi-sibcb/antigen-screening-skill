#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PATH_SUFFIXES = (".md", ".py", ".json", ".tsv", ".yaml", ".toml", ".sh", ".txt")


def parse_frontmatter(skill_path: Path) -> dict[str, str]:
    text = skill_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        raise ValueError("SKILL.md missing YAML frontmatter")
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def parse_manifest(manifest_path: Path) -> dict[str, Any]:
    text = manifest_path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise ValueError("manifest.yaml is not JSON-compatible and PyYAML is unavailable") from exc
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError("manifest.yaml did not parse to an object")
        return data


def collect_paths(obj: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(obj, dict):
        for value in obj.values():
            paths.extend(collect_paths(value))
    elif isinstance(obj, list):
        for value in obj:
            paths.extend(collect_paths(value))
    elif isinstance(obj, str):
        looks_like_path = obj == "Makefile" or obj.endswith(PATH_SUFFIXES) or ("/" in obj and " " not in obj)
        if looks_like_path:
            if not obj.startswith("http://") and not obj.startswith("https://"):
                paths.append(obj)
    return paths


def check_script_help(skill_dir: Path) -> list[dict[str, str]]:
    results = []
    for script in sorted((skill_dir / "scripts").glob("*.py")):
        proc = subprocess.run(
            [sys.executable, str(script), "--help"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
        results.append(
            {
                "script": str(script.relative_to(skill_dir)),
                "returncode": str(proc.returncode),
                "ok": str(proc.returncode == 0).lower(),
                "stderr": proc.stderr.strip()[:300],
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate antigen-screening skill package")
    parser.add_argument("--skill-dir", required=True, type=Path)
    args = parser.parse_args()

    skill_dir = args.skill_dir.resolve()
    errors: list[str] = []

    try:
        frontmatter = parse_frontmatter(skill_dir / "SKILL.md")
        for key in ("name", "description"):
            if not frontmatter.get(key):
                errors.append(f"SKILL.md frontmatter missing {key}")
    except Exception as exc:  # noqa: BLE001
        frontmatter = {}
        errors.append(str(exc))

    try:
        manifest = parse_manifest(skill_dir / "manifest.yaml")
    except Exception as exc:  # noqa: BLE001
        manifest = {}
        errors.append(str(exc))

    manifest_paths = sorted(set(collect_paths(manifest)))
    missing_paths = []
    for rel in manifest_paths:
        if not (skill_dir / rel).exists():
            missing_paths.append(rel)
    errors.extend([f"manifest path missing: {rel}" for rel in missing_paths])

    for rel in ("README.md", "CHANGELOG.md", "examples/input_candidates.tsv"):
        if not (skill_dir / rel).exists():
            errors.append(f"required file missing: {rel}")

    script_help = check_script_help(skill_dir) if (skill_dir / "scripts").exists() else []
    for item in script_help:
        if item["ok"] != "true":
            errors.append(f"{item['script']} --help failed: {item['stderr']}")

    summary = {
        "status": "pass" if not errors else "fail",
        "skill_dir": str(skill_dir),
        "frontmatter": frontmatter,
        "manifest_path_count": len(manifest_paths),
        "missing_manifest_paths": missing_paths,
        "script_help": script_help,
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
