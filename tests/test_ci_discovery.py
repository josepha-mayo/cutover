"""The PR gate must reject missing or unsafe case registrations."""
import json
import tempfile
import unittest
from pathlib import Path

from ci.discover_cases import ROOT, discover


class CaseDiscoveryTests(unittest.TestCase):
    def test_checked_in_baseline_cases_remain_registered_as_more_are_added(self):
        matrix = discover()
        by_slug = {case["slug"]: case for case in matrix["include"]}
        self.assertEqual(len(by_slug), len(matrix["include"]))
        self.assertEqual(by_slug["warehouse"]["plan"], "ci/candidate.json")
        self.assertEqual(by_slug["parcel"]["plan"], "ci/parcel-candidate.json")

    def test_bad_manifest_cannot_create_a_green_empty_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ci").mkdir()
            source = json.loads((ROOT / "ci/cases.json").read_text(encoding="utf-8"))
            for case in source:
                for field in (key for key in ("contract", "plan", "migration_file") if key in case):
                    path = root / case[field]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes((ROOT / case[field]).read_bytes())
            manifest = root / "ci/cases.json"
            for invalid in ([], [{**source[0], "slug": "../escape"}],
                            [source[0], {**source[1], "slug": source[0]["slug"]}],
                            [{**source[0], "contract": "../secret.json"}],
                            [{**source[0], "plan": "ci/does-not-exist.json"}]):
                with self.subTest(invalid=invalid):
                    manifest.write_text(json.dumps(invalid), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        discover(root)

    def test_new_candidate_cannot_be_silently_omitted_from_review_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = json.loads((ROOT / "ci/cases.json").read_text(encoding="utf-8"))
            for case in source:
                for field in (key for key in ("contract", "plan", "migration_file") if key in case):
                    path = root / case[field]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes((ROOT / case[field]).read_bytes())
            manifest = root / "ci/cases.json"
            manifest.write_text(json.dumps(source), encoding="utf-8")
            candidate = root / "ci/new-release-candidate.json"
            candidate.write_bytes((ROOT / source[0]["plan"]).read_bytes())
            with self.assertRaisesRegex(ValueError, "Unregistered candidate plan"):
                discover(root)
            source.append({**source[0], "case": "New release", "slug": "new-release",
                           "plan": "ci/new-release-candidate.json"})
            manifest.write_text(json.dumps(source), encoding="utf-8")
            self.assertEqual(len(discover(root)["include"]), len(source))

    def test_manifest_can_bind_adapters_to_a_checked_in_sql_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ci").mkdir()
            original = json.loads((ROOT / "ci/candidate.json").read_text(encoding="utf-8"))
            (root / "ci/adapters-candidate.json").write_text(
                json.dumps({key: value for key, value in original.items() if key != "migration"}),
                encoding="utf-8")
            (root / "ci/contract.json").write_bytes((ROOT / "examples/warehouse/contract.json").read_bytes())
            (root / "ci/release.sql").write_text(original["migration"], encoding="utf-8")
            entry = {"case": "SQL source", "slug": "sql-source", "contract": "ci/contract.json",
                     "plan": "ci/adapters-candidate.json", "migration_file": "ci/release.sql"}
            manifest = root / "ci/cases.json"
            manifest.write_text(json.dumps([entry]), encoding="utf-8")
            self.assertEqual(discover(root)["include"], [entry])
            for invalid in ("../release.sql", "ci/missing.sql", "ci/contract.json"):
                manifest.write_text(json.dumps([{**entry, "migration_file": invalid}]), encoding="utf-8")
                with self.subTest(path=invalid), self.assertRaises(ValueError):
                    discover(root)


if __name__ == "__main__":
    unittest.main()
