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
        counts = self.manifest["counts"]
        self.assertEqual(counts["inputs"], len(rows))
        self.assertEqual(self.manifest["input_inventory"]["count"], len(rows))
        accepted = [row for row in rows if row["outcome"] == "ACCEPTED"]
        deferred = [row for row in rows if row["outcome"] == "DEFERRED"]
        failed = [row for row in rows if row["outcome"] == "CONVERSION_FAILED"]
        self.assertEqual(counts["accepted"], len(accepted))
        self.assertEqual(counts["deferred"], len(deferred))
        self.assertEqual(counts["conversion_failed"], len(failed))
        self.assertEqual(sorted(self.manifest["accepted_record_ids"]), sorted(self.records))
        for row in rows:
            self.assertIn(row["outcome"], {"ACCEPTED", "DEFERRED", "CONVERSION_FAILED"})
            if row["outcome"] == "ACCEPTED":
                self.assertIn(row["record_id"], self.records)
                self.assertEqual(row["source_input"], self.records[row["record_id"]]["collection"]["source_input"])
            if row["outcome"] == "DEFERRED":
                self.assertTrue(row["reason_code"])
                self.assertTrue(row["reason"])
                self.assertIsNone(row["record_id"])

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
                sections = json.loads(evidence_bytes)["sections"]
                self.assertEqual(record["collection"]["source_input_sha256"], sections["prescription"]["sha256"])
                self.assertEqual(sha256(sections["prescription"]["text"].encode("utf-8")),
                                 sections["prescription"]["sha256"])
                self.assertEqual(record["conversion"]["source_sha256"], sections["engine"]["surface_table_sha256"])
                project = json.loads(project_bytes)
                unit = next(model for model in project["optical_models"] if model["model_id"] == "LENS")
                self.assertIn(record["conversion"]["source_sha256"], unit["display_name"])

    def test_evidence_extract_follows_the_shared_contract(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                extract = load(ROOT / record["collection"]["evidence_extract"]["path"])
                sections = extract.get("sections")
                self.assertTrue(
                    extract.get("schema") == "opensci.lens.evidence_extract"
                    and extract.get("record_id") == name
                    and isinstance(sections, dict) and bool(sections)
                    and all(value is not None for value in sections.values()),
                    "not the shared evidence-extract layout")

    def test_evidence_matches_the_record(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                sections = load(ROOT / record["collection"]["evidence_extract"]["path"])["sections"]
                stated = sections["stated"]
                self.assertEqual(stated["effective_focal_length_mm"],
                                 record["first_order"]["engine_check"]["comparison"]
                                 ["effective_focal_length"]["source_mm"])
                self.assertEqual(stated["f_number"], record["aperture"]["f_number"]["value"])
                self.assertEqual(stated["half_field_deg"], record["field"]["half_field_deg"])
                self.assertEqual(sections["engine"]["effective_focal_length_mm"],
                                 record["first_order"]["engine_check"]["effective_focal_length_mm"])
                self.assertEqual(sections["field_trace"]["samples"], record["field"]["traced_chief_rays"])
                self.assertEqual(record["image_format"]["image_circle_diameter_mm"],
                                 round(2 * sections["field_trace"]["samples"][0]["image_height_mm"], 4))
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
                self.assertEqual(comparison["back_focal_length"]["state"], "UNCONFIRMED")
                self.assertIn("no back focal length", record["validation"]["paraxial_scope"])
                bfl = record["first_order"]["back_focal_length_mm"]
                self.assertEqual(bfl["basis"], "ENGINE_COMPUTED")
                self.assertGreater(bfl["value"], 0)

    def test_derived_quantities_are_consistent(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                aperture = record["aperture"]
                self.assertNotIn("entrance_pupil_diameter_mm", aperture)
                self.assertEqual(aperture["stop_opening_diameter_mm"]["basis"], "DERIVED")
                self.assertEqual(aperture["f_number"]["system_aperture"], True)
                swept = record["field"]["traced_chief_rays"]
                self.assertTrue(swept)
                fraction = record["image_format"]["field_fraction_of_stated_half_field"]
                self.assertEqual(swept[0]["field_fraction"], fraction)
                self.assertAlmostEqual(record["image_format"]["image_circle_diameter_mm"],
                                       2 * swept[0]["image_height_mm"], places=4)
                self.assertEqual(record["spectrum"]["continuous_coverage_nm"]["state"], "UNCONFIRMED")
                self.assertEqual(record["spectrum"]["sampling_wavelengths_air_nm"], [587.56])
                self.assertGreater(record["spectrum"]["sampling_wavelengths_nm"][0], 587.56)
                self.assertIn("air model", record["spectrum"]["sampling_wavelengths_basis"])
                self.assertEqual(record["field"]["verification"]["state"], "TRACED")
                self.assertIsNone(record["field"]["field_points_deg"])
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
