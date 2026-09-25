"""The PR gate must reject missing or unsafe case registrations."""
import json
import tempfile
import unittest
from pathlib import Path

from ci.discover_cases import ROOT, discover


class CaseDiscoveryTests(unittest.TestCase):
    def test_checked_in_cases_expand_into_two_independent_review_jobs(self):
        matrix = discover()
        self.assertEqual({case["slug"] for case in matrix["include"]},
                         {"warehouse", "parcel"})
        self.assertEqual(len(matrix["include"]), 2)

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
