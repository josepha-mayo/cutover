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
                for field in ("contract", "plan"):
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


if __name__ == "__main__":
    unittest.main()
