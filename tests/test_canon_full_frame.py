"""Check the Canon full-frame batch against its own evidence.

The tests are engine-free: they re-derive every hash, the paraxial verdict and the derived
quantities from the committed files, so a reviewer can run them before installing anything.
"""

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT / "records/canon-full-frame"
MANIFEST = COLLECTION / "batch-canon-full-frame-1.json"
FULL_FRAME_HALF_DIAGONAL_MM = 21.6333


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def record_hash(record):
    body = {key: value for key, value in record.items()
            if key not in ("record_hash", "record_hash_method")}
    return sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8"))


class CanonFullFrameBatch(unittest.TestCase):
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
                self.assertEqual(row["source_input"],
                                 self.records[row["record_id"]]["collection"]["source_input"])
            else:
                self.assertIsNone(row["record_id"])
                self.assertTrue(row["reason_code"])
                self.assertTrue(row["reason"])

    def test_record_hash_and_evidence(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                self.assertEqual(record["record_hash"], record_hash(record))
                self.assertEqual(record["record_id"], name)
                self.assertEqual(record["schema"], "opensci.lens.record")
                self.assertEqual(record["collection"]["collection_id"], "canon-full-frame")
                evidence_path = ROOT / record["collection"]["evidence_extract"]["path"]
                evidence_bytes = evidence_path.read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(sha256(evidence_bytes),
                                 record["collection"]["evidence_extract"]["sha256"])
                project_path = ROOT / record["native_project"]["path"]
                project_bytes = project_path.read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(sha256(project_bytes), record["native_project"]["sha256"])
                evidence = json.loads(evidence_bytes)
                self.assertEqual(record["collection"]["source_input_sha256"],
                                 evidence["prescription"]["sha256"])
                self.assertEqual(sha256(evidence["prescription"]["text"].encode("utf-8")),
                                 evidence["prescription"]["sha256"])
                self.assertEqual(record["conversion"]["source_sha256"],
                                 evidence["engine"]["surface_table_sha256"])
                project = json.loads(project_bytes)
                unit = next(model for model in project["optical_models"]
                            if model["model_id"] == "LENS")
                self.assertIn(record["conversion"]["source_sha256"], unit["display_name"])

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
                self.assertEqual(evidence["engine"]["effective_focal_length_mm"],
                                 record["first_order"]["engine_check"]["effective_focal_length_mm"])
                self.assertEqual(evidence["field_trace"]["samples"],
                                 record["field"]["traced_chief_rays"])
                self.assertEqual(record["image_format"]["image_circle_diameter_mm"],
                                 round(2 * evidence["field_trace"]["samples"][0]["image_height_mm"], 4))

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
                self.assertEqual(record["validation"]["paraxial"],
                                 "MATCHED" if difference <= tolerance else "DIFFERS")
                self.assertLessEqual(quantity["fraction_of_tolerance"], 0.8)
                back_focus = comparison["back_focal_length"]
                if back_focus.get("state") == "UNCONFIRMED":
                    # No printed back focal length was transcribed, so there is nothing to compare.
                    self.assertIsNone(back_focus.get("source_mm"))
                    self.assertIn("no back focal length", record["validation"]["paraxial_scope"])
                else:
                    difference = abs(back_focus["engine_mm"] - back_focus["source_mm"])
                    self.assertAlmostEqual(difference, back_focus["absolute_difference_mm"],
                                           places=12)
                    self.assertEqual(difference <= back_focus["tolerance_mm"],
                                     back_focus["within_tolerance"])
                    self.assertLessEqual(back_focus["fraction_of_tolerance"], 0.8)
                    self.assertIn("back focal length", record["validation"]["paraxial_scope"])

    def test_records_are_full_frame_and_complete_systems(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                self.assertEqual(record["design"]["design_scope"], "COMPLETE_SYSTEM")
                self.assertIn("imaging", record["design"]["function_tags"])
                self.assertIn("photography", record["design"]["application_tags"])
                self.assertIn("full_frame", record["image_format"]["format_facets"])
                self.assertEqual(record["image_format"]["width_mm"], 36.0)
                self.assertEqual(record["image_format"]["height_mm"], 24.0)
                circle = record["image_format"]["image_circle_diameter_mm"]
                self.assertGreater(circle, 39.0)
                self.assertLess(circle, 46.0)
                self.assertEqual(record["validation"]["optical_solids"], "VALID")
                self.assertEqual(record["validation"]["conversion"], "PASSED")
                self.assertEqual(record["validation"]["project_check"], "ACCEPTED")

    def test_no_claim_beyond_the_evidence(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                self.assertEqual(record["spectrum"]["continuous_coverage_nm"]["state"],
                                 "UNCONFIRMED")
                self.assertEqual(record["design"]["aperture_validity"]
                                 ["satisfies_stop_dependent_constraints"], False)
                self.assertEqual(record["field"]["verification"]["state"], "TRACED")
                self.assertTrue(record["field"]["traced_chief_rays"])
                codes = {entry["code"] for entry in record["approximations"]}
                self.assertIn("ND_VD_DISPERSION_MODEL", codes)
                self.assertIn("CLEAR_APERTURES_DERIVED", codes)
                self.assertIn("STOP_FROM_PRINTED_F_NUMBER", codes)
                for key in ("mtf", "distortion", "relative_illumination"):
                    self.assertNotIn(key, record)
                self.assertEqual(record["unsupported_constructs"], [])

    def test_the_batch_covers_distinct_designs(self):
        focal = sorted(record["first_order"]["effective_focal_length_mm"]["value"]
                       for record in self.records.values())
        self.assertGreater(len(self.records), 5)
        # The batch spans an ultra-wide prime to a super-telephoto: 24.74 mm to 814.8 mm.
        self.assertLess(min(focal), 30.0)
        self.assertGreater(max(focal), 500.0)
        self.assertGreater(max(focal) / min(focal), 20.0)
        families = {record["design"]["design_family_id"] for record in self.records.values()}
        self.assertGreater(len(families), 3)
        types = {tuple(sorted(record["design"]["structure_tags"])) for record in self.records.values()}
        self.assertTrue(any("zoom" in tags for tags in types))
        self.assertTrue(any("zoom" not in tags for tags in types))


if __name__ == "__main__":
    unittest.main()
