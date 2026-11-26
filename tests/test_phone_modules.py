"""Check the phone-module batch against its own evidence.

The tests are engine-free: they re-derive every hash, the paraxial verdict and the derived
quantities from the committed files, so a reviewer can run them before installing anything.
"""

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT / "records/phone-modules"
MANIFEST = COLLECTION / "batch-phone-modules-1.json"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def record_hash(record):
    body = {key: value for key, value in record.items() if key not in ("record_hash", "record_hash_method")}
    return sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8"))


class PhoneModuleBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load(MANIFEST)
        cls.dirs = sorted(path for path in COLLECTION.iterdir() if path.is_dir())
        cls.records = {path.name: load(path / "record.json") for path in cls.dirs}

    def test_every_manifest_row_has_an_outcome(self):
        rows = self.manifest["outcomes"]
        self.assertEqual(self.manifest["counts"]["inputs"], len(rows))
        accepted = [row for row in rows if row["outcome"] == "ACCEPTED"]
        self.assertEqual(self.manifest["counts"]["accepted"], len(accepted))
        self.assertEqual(sorted(self.manifest["accepted_record_ids"]), sorted(self.records))
        for row in rows:
            self.assertIn(row["outcome"], {"ACCEPTED", "DEFERRED", "CONVERSION_FAILED"})
            if row["outcome"] == "DEFERRED":
                self.assertTrue(row["reason_code"])
                self.assertTrue(row["reason"])

    def test_record_hash_and_evidence(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                self.assertEqual(record["record_hash"], record_hash(record))
                self.assertEqual(record["record_id"], name)
                self.assertEqual(record["schema"], "opensci.lens.record")
                evidence_path = ROOT / record["collection"]["evidence_extract"]["path"]
                evidence_bytes = evidence_path.read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(sha256(evidence_bytes), record["collection"]["evidence_extract"]["sha256"])
                project_path = ROOT / record["native_project"]["path"]
                project_bytes = project_path.read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(sha256(project_bytes), record["native_project"]["sha256"])
                self.assertEqual(record["collection"]["source_input_sha256"],
                                 json.loads(evidence_bytes)["prescription"]["sha256"])

    def test_evidence_matches_the_record(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                evidence = load(ROOT / record["collection"]["evidence_extract"]["path"])
                stated = evidence["stated"]
                self.assertEqual(stated["effective_focal_length_mm"],
                                 record["first_order"]["engine_check"]["comparison"]
                                 ["effective_focal_length"]["source_mm"])
                self.assertEqual(stated["f_number"], record["aperture"]["f_number"]["value"])
                self.assertEqual(stated["half_field_deg"], record["field"]["half_field_deg"])
                project = load(ROOT / record["native_project"]["path"])
                self.assertEqual(project["schema"], "opensci.project")
                self.assertTrue(any(component.get("optical_role") == "source" for component in project["components"]))
                self.assertTrue(project["observations"][0]["observation_id"] == "image_plane")

    def test_paraxial_verdict_is_recomputable(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                comparison = record["first_order"]["engine_check"]["comparison"]
                quantity = comparison["effective_focal_length"]
                difference = abs(quantity["engine_mm"] - quantity["source_mm"])
                tolerance = comparison["atol_mm"] + comparison["rtol"] * quantity["scale_mm"]
                self.assertAlmostEqual(difference, quantity["absolute_difference_mm"], places=12)
                self.assertAlmostEqual(tolerance, quantity["tolerance_mm"], places=12)
                self.assertEqual(difference <= tolerance, quantity["within_tolerance"])
                self.assertEqual(record["validation"]["paraxial"], "MATCHED" if difference <= tolerance else "DIFFERS")
                self.assertLessEqual(quantity["fraction_of_tolerance"], 0.75)

    def test_derived_quantities_are_consistent(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                aperture = record["aperture"]
                efl = record["first_order"]["effective_focal_length_mm"]["value"]
                fno = aperture["f_number"]["value"]
                self.assertAlmostEqual(aperture["entrance_pupil_diameter_mm"]["value"], efl / fno, places=9)
                swept = record["field"]["traced_chief_rays"]
                self.assertTrue(swept)
                fraction = record["image_format"]["field_fraction_of_stated_half_field"]
                self.assertEqual(swept[0]["field_fraction"], fraction)
                self.assertAlmostEqual(record["image_format"]["image_circle_diameter_mm"],
                                       2 * swept[0]["image_height_mm"], places=4)
                self.assertEqual(record["spectrum"]["continuous_coverage_nm"]["state"], "UNCONFIRMED")
                self.assertEqual(record["design"]["aperture_validity"]["satisfies_stop_dependent_constraints"], False)
                codes = {entry["code"] for entry in record["approximations"]}
                self.assertIn("ND_VD_DISPERSION_MODEL", codes)
                self.assertIn("CLEAR_APERTURES_DERIVED", codes)

    def test_batch_spans_both_module_roles(self):
        roles = {record["design"]["module_role"] for record in self.records.values()}
        self.assertEqual(roles, {"main_camera", "ultrawide"})
        for record in self.records.values():
            self.assertEqual(record["design"]["design_scope"], "COMPLETE_SYSTEM")
            self.assertIn("mobile_imaging", record["design"]["application_tags"])
            self.assertGreaterEqual(record["design"]["aspheric_element_count"], 5)


if __name__ == "__main__":
    unittest.main()
