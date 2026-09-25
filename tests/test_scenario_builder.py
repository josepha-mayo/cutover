"""End-to-end evidence for the browser's generated custom migration path."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from cutover.service import run_rehearsal, validate_imported_contract


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "Node.js is needed to execute the browser module")
class ScenarioBuilderTests(unittest.TestCase):
    def build(self, data):
        script = (
            "import {buildScenario} from './public/scenario.js'; "
            "const input=JSON.parse(process.argv[1]); "
            "try { console.log(JSON.stringify({ok:true,value:buildScenario(input)})); } "
            "catch(error) { console.log(JSON.stringify({ok:false,error:error.message})); }"
        )
        process = subprocess.run(
            ["node", "--input-type=module", "-e", script, json.dumps(data, ensure_ascii=False)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True,
        )
        return json.loads(process.stdout)

    def test_custom_scenario_exposes_lost_write_then_verified_bridge(self):
        for table, old_column, new_column in (
            ("items", "location", "destination"),
            ("parcel_jobs", "delivery_address", "shipping_address"),
        ):
            with self.subTest(table=table):
                built = self.build(dict(project="My release", table=table,
                                        oldColumn=old_column, newColumn=new_column,
                                        firstValue="O'Connell", secondValue="東京-棚"))
                self.assertTrue(built["ok"], built)
                scenario = built["value"]
                contract = scenario["contract"]
                meta = validate_imported_contract(contract)
                self.assertEqual(meta["seed_count"], 2)
                before = run_rehearsal("custom", scenario["unsafe"], contract)
                after = run_rehearsal("custom", scenario["safe"], contract)
                self.assertEqual(before["status"], "blocked")
                self.assertEqual(after["status"], "pass")
                self.assertEqual(after["passed"], after["total"])
                self.assertEqual((before["contract_hash"], before["suite_hash"]),
                                 (after["contract_hash"], after["suite_hash"]))
                self.assertIsNotNone(before["witness"])

    def test_invalid_identifiers_are_rejected_before_sql(self):
        base = dict(project="My release", table="items", oldColumn="location",
                    newColumn="destination", firstValue="A-01", secondValue="B-02")
        for change in (dict(table="items; DROP TABLE items"),
                       dict(newColumn="LOCATION"), dict(oldColumn="id")):
            with self.subTest(change=change):
                self.assertFalse(self.build({**base, **change})["ok"])


if __name__ == "__main__":
    unittest.main()
