"""Validate configured release pairs before creating the GitHub Actions matrix."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from cutover.engine import validate_contract, validate_plan


ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z][a-z0-9-]{0,40}\Z")
LABEL = re.compile(r"[A-Za-z][A-Za-z0-9 _-]{0,49}\Z")
SAFE_PATH = re.compile(r"[A-Za-z0-9_./-]+\.json\Z")
FIELDS = {"case", "slug", "contract", "plan"}


def _checked_file(root: Path, path: str) -> Path:
    if (not isinstance(path, str) or not SAFE_PATH.fullmatch(path) or
            path.startswith("/") or any(part in ("", ".", "..") for part in path.split("/"))):
        raise ValueError(f"Unsafe case input path: {path!r}")
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError(f"Case input is missing or outside the repository: {path}")
    return target


def discover(root: Path = ROOT, manifest: str = "ci/cases.json") -> dict:
    root = root.resolve()
    source = _checked_file(root, manifest)
    cases = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not 1 <= len(cases) <= 8:
        raise ValueError("Case manifest must contain 1 to 8 contract/plan pairs")
    seen = set()
    registered_plans = set()
    for entry in cases:
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise ValueError("Each case requires exactly case, slug, contract and plan")
        if not isinstance(entry["case"], str) or not LABEL.fullmatch(entry["case"]):
            raise ValueError("Case label must be short and contain only letters, digits, spaces, _ or -")
        slug = entry["slug"]
        if not isinstance(slug, str) or not SLUG.fullmatch(slug) or slug in seen:
            raise ValueError("Case slugs must be unique lowercase names")
        seen.add(slug)
        contract_path = _checked_file(root, entry["contract"])
        plan_path = _checked_file(root, entry["plan"])
        if plan_path in registered_plans:
            raise ValueError(f"Candidate plan is registered more than once: {entry['plan']}")
        registered_plans.add(plan_path)
        validate_contract(json.loads(contract_path.read_text(encoding="utf-8")))
        validate_plan(json.loads(plan_path.read_text(encoding="utf-8")))
    # The kit installer writes ci/<slug>-candidate.json. A PR must not be able
    # to add one of those inputs without getting its own review job. Keep the
    # original ci/candidate.json under the same rule.
    candidate_dir = root / "ci"
    candidates = {path.resolve() for path in candidate_dir.glob("*-candidate.json")}
    legacy_candidate = candidate_dir / "candidate.json"
    if legacy_candidate.exists():
        candidates.add(legacy_candidate.resolve())
    unregistered = sorted(path.relative_to(root).as_posix()
                          for path in candidates - registered_plans)
    if unregistered:
        raise ValueError(f"Unregistered candidate plan(s): {', '.join(unregistered)}")
    return {"include": cases}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="ci/cases.json")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    value = json.dumps(discover(ROOT, args.manifest), separators=(",", ":"))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(f"matrix={value}\n")
    print(value)


if __name__ == "__main__":
    main()
