"""Check the Nikon FX records against the contract their manifest states.

Every accepted record must be self-consistent: its hash recomputes from its own JSON, the Project
it names is the Project beside it, the first-order values in the record are the ones the engine
returns for that Project, and the manifest lists the record exactly once.
"""

import hashlib
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT / "records/nikon-fx"
MANIFESTS = sorted(COLLECTION.glob("batch-*.json"))


def record_hash(body):
    stripped = {k: v for k, v in body.items()
                if k not in ("record_hash", "record_hash_method")}
    payload = json.dumps(stripped, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def records():
    for path in sorted(COLLECTION.glob("*/record.json")):
        yield path.parent, json.loads(path.read_text(encoding="utf-8"))


class NikonFxBatchTest(unittest.TestCase):
    def test_manifests_are_present_and_complete(self):
        self.assertTrue(MANIFESTS, "no batch manifest in records/nikon-fx")
        for path in MANIFESTS:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], "opensci.lens.batch")
            rows = manifest["outcomes"]
            self.assertEqual(manifest["counts"]["candidates"], len(rows))
            accepted = [r["record_id"] for r in rows if r["outcome"] == "ACCEPTED"]
            self.assertEqual(sorted(accepted), sorted(manifest["accepted_record_ids"]))
            self.assertEqual(manifest["counts"]["accepted"], len(accepted))
            for row in rows:
                self.assertIn(row["outcome"],
                              {"ACCEPTED", "DEFERRED", "CONVERSION_FAILED"})
                if row["outcome"] != "ACCEPTED":
                    self.assertTrue(row.get("reason_code"), row.get("source_input"))
                else:
                    self.assertTrue((COLLECTION / row["record_id"] / "record.json").exists(),
                                    row["record_id"])

    def test_every_record_is_listed_once(self):
        listed = []
        for path in MANIFESTS:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            listed.extend(r["record_id"] for r in manifest["outcomes"]
                          if r["outcome"] == "ACCEPTED")
        self.assertEqual(len(listed), len(set(listed)))
        on_disk = {folder.name for folder, _ in records()}
        self.assertEqual(on_disk, set(listed))

    def test_record_hash_recomputes(self):
        for folder, body in records():
            with self.subTest(record=folder.name):
                self.assertEqual(body["record_hash"], record_hash(body))

    def test_project_is_the_project_the_record_names(self):
        for folder, body in records():
            with self.subTest(record=folder.name):
                project = folder / "project.json"
                self.assertTrue(project.exists())
                digest = hashlib.sha256(project.read_bytes()).hexdigest()
                self.assertEqual(body["native_project"]["sha256"], digest)
                self.assertEqual(body["native_project"]["path"],
                                 f"records/nikon-fx/{folder.name}/project.json")

    def test_validation_states_are_accepted(self):
        for folder, body in records():
            with self.subTest(record=folder.name):
                validation = body["validation"]
                self.assertEqual(validation["conversion"], "PASSED")
                self.assertEqual(validation["project_check"], "ACCEPTED")
                self.assertEqual(validation["optical_solids"], "VALID")
                self.assertEqual(validation["paraxial"], "MATCHED")

    def test_paraxial_comparison_is_within_its_own_tolerance(self):
        for folder, body in records():
            with self.subTest(record=folder.name):
                comparison = body["first_order"]["engine_check"]["comparison"][
                    "effective_focal_length"]
                difference = abs(comparison["engine_mm"] - comparison["source_mm"])
                self.assertLessEqual(difference, comparison["tolerance_mm"])
                self.assertAlmostEqual(
                    comparison["absolute_difference_mm"], difference, places=9)
                self.assertTrue(comparison["within_tolerance"])

    def test_engine_values_are_the_projects_values(self):
        for folder, body in records():
            with self.subTest(record=folder.name):
                first_order = body["first_order"]
                efl = first_order["effective_focal_length_mm"]["value"]
                self.assertEqual(efl, first_order["engine_check"]["effective_focal_length_mm"])
                # the record rounds the circle to four decimals
                self.assertAlmostEqual(
                    body["image_format"]["image_circle_diameter_mm"],
                    self._image_circle(body), delta=1e-3)

    @staticmethod
    def _image_circle(body):
        efl = abs(body["first_order"]["effective_focal_length_mm"]["value"])
        half = body["field"]["half_field_deg"]
        if body["field"]["projection"] == "EQUIDISTANT":
            return 2.0 * efl * math.radians(half)
        return 2.0 * efl * math.tan(math.radians(half))

    def test_every_basis_is_in_the_vocabulary(self):
        vocabulary = {"SOURCE_STATED", "DERIVED", "ENGINE_COMPUTED"}
        for folder, body in records():
            with self.subTest(record=folder.name):
                self.assertIn(body["first_order"]["effective_focal_length_mm"]["basis"],
                              vocabulary)
                self.assertIn(body["first_order"]["back_focal_length_mm"]["basis"], vocabulary)
                for glass in body["materials"]["model_glasses"]:
                    self.assertTrue(glass["basis"].startswith("SOURCE_STATED"))
                for approximation in body["approximations"]:
                    self.assertTrue(approximation["code"])
                    self.assertTrue(approximation["description"])

    def test_corpus_records_cite_a_pinned_revision(self):
        for folder, body in records():
            with self.subTest(record=folder.name):
                collection = body["collection"]
                self.assertEqual(collection["collection_id"], "nikon-fx")
                if not collection["source_input"].startswith("lenses/"):
                    # a transcription of a patent publication: no upstream revision to pin
                    self.assertIn("source_input_sha256", collection)
                    continue
                self.assertRegex(collection["source_revision"], r"^[0-9a-f]{40}$")
                self.assertIn(collection["source_revision"], collection["source_links"]
                              ["source_file_url"])


if __name__ == "__main__":
    unittest.main()
