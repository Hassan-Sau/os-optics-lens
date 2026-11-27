"""Check Canon batch membership, Project identity and the retrieval projection."""

import json
import unittest
from pathlib import Path

from os_optics_lens.canonical import record_hash, sha256_hex
from os_optics_lens.corpus import load_corpus
from os_optics_lens.project_facts import _native_spectrum

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT / "records/canon-full-frame"
MANIFEST = COLLECTION / "batch-canon-full-frame-1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


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
        self.assertEqual(sorted(row["record_id"] for row in accepted), sorted(self.records))
        for row in rows:
            self.assertIn(row["outcome"], {"ACCEPTED", "DEFERRED", "CONVERSION_FAILED"})
            if row["outcome"] == "ACCEPTED":
                self.assertEqual(row["source_input"],
                                 self.records[row["record_id"]]["collection"]["source_input"])
            else:
                self.assertIsNone(row["record_id"])
                self.assertTrue(row["reason_code"])
                self.assertTrue(row["reason"])

    def test_record_and_native_project_identity(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                self.assertEqual(record["record_hash"], record_hash(record))
                self.assertEqual(record["record_id"], name)
                self.assertEqual(record["schema"], "opensci.lens.record")
                provenance = record["collection"]
                self.assertEqual(provenance["collection_id"], "canon-full-frame")
                self.assertTrue(provenance["original_publication"]["url"])
                self.assertEqual(provenance["license"]["notice_path"], "LICENSE")
                self.assertNotIn("evidence_extract", provenance)
                project_path = ROOT / record["native_project"]["path"]
                self.assertEqual(project_path, COLLECTION / name / "project.json")
                self.assertCountEqual((path.name for path in project_path.parent.iterdir()),
                                      ["record.json", "project.json"])
                project_bytes = project_path.read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(sha256_hex(project_bytes), record["native_project"]["sha256"])
                project = json.loads(project_bytes)
                unit = next(model for model in project["optical_models"] if model["model_id"] == "LENS")
                self.assertIn(record["conversion"]["source_sha256"], unit["display_name"])

    def test_first_order_matches_the_native_wavelength(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                project = load(ROOT / record["native_project"]["path"])
                wavelengths = _native_spectrum(project, None)["sampling_wavelengths_nm"]
                first_order = record["first_order"]
                for key in ("effective_focal_length_mm", "back_focal_length_mm"):
                    fact = first_order[key]
                    self.assertEqual(fact["basis"], "ENGINE_COMPUTED")
                    self.assertIn(fact["conditions"]["wavelength_nm"], wavelengths)
                    self.assertEqual(fact["value"], first_order["engine_check"][key])
                self.assertEqual(first_order["back_focal_length_mm"]["conditions"]["distance_kind"],
                                 "paraxial_focal_distance")

    def test_field_trace_is_available_without_image_coverage(self):
        corpus = load_corpus(ROOT)
        views = {record.record_id: record.views[0].view for record in corpus.records
                 if record.record_id in self.records}
        self.assertEqual(set(views), set(self.records))
        for name, record in self.records.items():
            with self.subTest(record=name):
                trace = record["field"]["traced_chief_rays"]
                self.assertEqual(trace["basis"], "PROJECT_DERIVED")
                self.assertEqual(trace["conditions"]["wavelength_nm"],
                                 record["first_order"]["effective_focal_length_mm"]["conditions"]["wavelength_nm"])
                self.assertEqual(len(trace["samples"]), 7)
                edge = trace["samples"][0]
                self.assertEqual(edge["field_fraction"], 1.0)
                self.assertEqual(edge["field_deg"], record["field"]["half_field_deg"])
                self.assertGreater(edge["image_height_mm"], 0.0)
                view = views[name]
                self.assertEqual(view["field"]["traced_chief_rays"], trace)
                self.assertNotIn("half_field_deg", view["field"])
                image_format = view["image_format"]
                self.assertEqual(image_format["format_facets"], ["full_frame"])
                for key in ("width_mm", "height_mm", "image_circle_diameter_mm"):
                    self.assertNotIn(key, image_format)

    def test_no_claim_beyond_the_project(self):
        for name, record in self.records.items():
            with self.subTest(record=name):
                self.assertEqual(record["design"]["design_scope"], "COMPLETE_SYSTEM")
                self.assertIn("imaging", record["design"]["function_tags"])
                self.assertIn("photography", record["design"]["application_tags"])
                self.assertEqual(record["validation"]["optical_solids"], "VALID")
                self.assertEqual(record["validation"]["conversion"], "PASSED")
                self.assertEqual(record["validation"]["project_check"], "ACCEPTED")
                self.assertEqual(record["spectrum"]["continuous_coverage_nm"]["state"], "UNCONFIRMED")
                self.assertFalse(record["design"]["aperture_validity"]["satisfies_stop_dependent_constraints"])
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
