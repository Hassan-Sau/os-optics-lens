"""Regression tests for the contribution gate's record selection and metric checks."""

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

from test_build_foundation import SynthCorpus

from os_optics_lens import query
from os_optics_lens.build import build_index
from os_optics_lens.corpus import load_corpus
from os_optics_lens.store import open_index
from scripts import check_intake


WAVELENGTH_NM = 587.6


class ContributionCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = tempfile.TemporaryDirectory()
        cls.addClassCleanup(scratch.cleanup)
        root = Path(scratch.name)
        corpus = SynthCorpus(root)

        def prepare(record):
            record["collection"].update(source="Example Lab", attribution="Example Lab", redistribution="MIT")
            record["first_order"]["back_focal_length_mm"] = {
                "value": 8.0, "basis": "ENGINE_COMPUTED", "conditions": {"wavelength_nm": WAVELENGTH_NM},
            }

        corpus.add("intake-sample", with_evidence=False, mutate=prepare)
        corpus.add("unrelated", with_evidence=False)
        cls.records = load_corpus(root).records
        cls.seed = next(record for record in cls.records if record.record_id == "intake-sample")

    def test_change_selects_record_and_detection_changes_select_all(self):
        self.assertEqual(check_intake.selected_records(self.records, {self.seed.project_path}), [self.seed])
        self.assertEqual(check_intake.selected_records(self.records, {self.seed.file}), [self.seed])
        self.assertEqual(check_intake.selected_records(self.records, {"CONTRIBUTING.md"}), [])
        self.assertEqual(check_intake.selected_records(self.records, {"src/os_optics_lens/build.py"}), self.records)

    def test_tampered_numeric_value_and_air_wavelength_are_rejected(self):
        record = copy.deepcopy(self.seed)
        entries = {fact["fact_key"]: fact for fact in record.facts[""]}
        efl = entries["first_order.effective_focal_length_mm"]
        bfl = entries["first_order.back_focal_length_mm"]
        native = [{"wavelength_nm": WAVELENGTH_NM, "effective_focal_length_mm": efl["value_num"],
                   "back_focal_length_mm": bfl["value_num"]}]
        self.assertEqual(check_intake.compare_first_order(record, None, native), [])

        efl.update(value_num=999.0, basis="ENGINE_COMPUTED at the primary wavelength", json_path=efl["fact_key"])
        bfl["conditions_json"] = '{"wavelength_nm":587.56}'
        diagnostics = check_intake.compare_first_order(record, None, native)
        self.assertEqual({item.code for item in diagnostics}, {"FIRST_ORDER_MISMATCH", "FIRST_ORDER_UNCONFIRMED"})
        mismatch = next(item for item in diagnostics if item.code == "FIRST_ORDER_MISMATCH")
        self.assertEqual(mismatch.actual, 999.0)
        self.assertEqual(mismatch.expected, native[0]["effective_focal_length_mm"])

    def test_missing_optional_fact_and_source_value_do_not_gate(self):
        record = copy.deepcopy(self.seed)
        native = [{"wavelength_nm": WAVELENGTH_NM}]
        self.assertEqual(check_intake.compare_first_order(record, None, []), [])
        record.facts[""] = [fact for fact in record.facts[""]
                             if fact["fact_key"] == "first_order.effective_focal_length_mm"]
        record.facts[""][0].update(value_num=999.0, basis_class="SOURCE_STATED")
        self.assertEqual(check_intake.compare_first_order(record, None, native), [])

    def test_duplicate_detection_includes_unchanged_records(self):
        record = copy.deepcopy(self.seed)
        record.record_id = "copied-design"
        findings = check_intake.duplicate_projects([self.seed, record], {record.record_id})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "DUPLICATE_PROJECT")
        self.assertIn(self.seed.record_id, findings[0].message)

    def test_projects_outside_the_record_layout_are_detected(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            folder = root / "records" / "collection"
            folder.mkdir(parents=True)
            (folder / "record.json").write_text("{}", encoding="utf-8")
            (folder / "project.json").write_text("{}", encoding="utf-8")
            orphans = folder / "orphan"
            orphans.mkdir()
            (orphans / "project.json").write_text("{}", encoding="utf-8")
            codes = [item.code for item in check_intake.check_layout(root)]
            self.assertCountEqual(codes, ["INVALID_RECORD_LAYOUT", "INVALID_RECORD_LAYOUT", "ORPHAN_PROJECT"])

    def test_provenance_and_redistribution_required(self):
        record = copy.deepcopy(self.seed)
        self.assertEqual(check_intake.intake_metadata(record), [])
        record.record["collection"] = {"collection_id": "lenslibrary"}
        codes = [item.code for item in check_intake.intake_metadata(record)]
        self.assertCountEqual(codes, ["PROVENANCE_REQUIRED", "PROVENANCE_REQUIRED", "REDISTRIBUTION_REQUIRED"])


def axial_project(clear_radius: str = "10") -> dict:
    def pose(z):
        return {"position_mm": [0, 0, z], "quaternion_wxyz": [1, 0, 0, 0]}

    def component(key, role, z, **extra):
        return {"instance_id": key, "optical_role": role, "nominal_pose": pose(z),
                "custom_part": {"custom_part_key": key, "description": key}, **extra}

    band = {"min_nm": "400", "max_nm": "700", "status": "SPECIFIED"}
    source = {"model_kind": "GAUSSIAN_BEAM", "wavelength_nm": WAVELENGTH_NM, "power_w": 0.001,
              "waist_radius_mm": 2.0, "waist_position_mm": 0.0, "m2": 1.0,
              "polarization": {"kind": "LINEAR", "angle_deg": 0}}
    return {
        "schema": "opensci.project", "project_schema_version": "2.0", "design_intent": "OPTICAL_SYSTEM",
        "environment": {"pressure_pa": "0"},
        "components": [
            component("SRC", "source", -200, source_model=source),
            component("LENS", "lens", 0, optical_model_id="LENS"),
            component("STOP", "aperture", 25, optical_model_id="STOP"),
        ],
        "observations": [{"observation_id": "image", "pose": pose(90),
                          "aperture": {"shape": "circle", "radius_mm": 20}, "absorbing": True, "medium": "air"}],
        "targets": [], "materials": [],
        "model_materials": [{"material_id": "GLASS", "display_name": "Example glass", "valid_band_nm": band,
                             "dispersion": {"kind": "CONSTANT_INDEX", "refractive_index": "1.5"}}],
        "optical_models": [
            {"model_id": "LENS", "display_name": "Plano-convex", "model": {
                "model_kind": "SURFACE_SEQUENCE", "model_version": "2", "fidelity": "SURFACE_PRESCRIPTION",
                "surfaces": [
                    {"surface_id": "S1", "vertex_z_mm": "0", "radius_mm": "25", "clear_radius_mm": clear_radius,
                     "traced": "TRANSMITTED", "status": "SPECIFIED"},
                    {"surface_id": "S2", "vertex_z_mm": "5", "clear_radius_mm": "10",
                     "traced": "TRANSMITTED", "status": "SPECIFIED"},
                ],
                "media": ["GLASS"], "edge_radius_mm": "10", "status": "SPECIFIED",
                "approximations": ["NOMINAL_PRESCRIPTION"], "valid_band_nm": band}},
            {"model_id": "STOP", "display_name": "Stop", "model": {
                "model_kind": "APERTURE_STOP", "model_version": "1", "opening_radius_mm": "2",
                "edge_radius_mm": "12", "plane_z_mm": "0", "status": "SPECIFIED"}},
        ],
    }


@unittest.skipUnless(importlib.util.find_spec("os_optics"), "native contribution tests require os-optics")
class ParaxialApertureCheck(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.corpus = SynthCorpus(self.root)

    def add(self, project, mutate=None):
        def prepare(record):
            record["collection"].update(source="Example Lab", attribution="Example Lab", redistribution="MIT")
            record["aperture"] = {"nominal_f_number": {"value": 4, "basis": "SOURCE_STATED"}}
            record["design"].pop("aperture_validity")
            if mutate is not None:
                mutate(record)

        return self.corpus.add("axial", project=project, with_evidence=False, mutate=prepare)

    def search(self, fact, value, **conditions):
        index_path = self.root / "search.sqlite"
        build_index(self.root, index_path)
        with open_index(index_path) as index:
            response = query.search(index, {
                "mode": "specification", "include": ["MATCH", "UNCONFIRMED", "DOES_NOT_MATCH"],
                "constraints": [{"id": "fno", "fact": f"aperture.{fact}", "op": "lte", "value": value, **conditions}],
            })
        return response["result"]["candidates"][0]

    def test_intake_requires_reproducible_f_number_and_search_uses_it(self):
        record = self.add(axial_project())
        project_path = record["native_project"]["path"]
        # The stop at z=25 reads a marginal height of 8/15 at unit incident height.
        audit = check_intake.run(self.root, None)
        self.assertTrue(audit["ok"], audit["findings"])
        report = audit["projects"][0]["configurations"][0]["paraxial_aperture"]
        [sample] = report["samples"]
        self.assertEqual((sample["fact"], sample["limiting_aperture"]), ("entrance_pupil_f_number", "STOP"))
        self.assertAlmostEqual(sample["data"]["value"], 50 / 7.5)
        self.assertEqual(self.search(sample["fact"], 7)["outcome"], "UNCONFIRMED")
        added = check_intake.run(self.root, {project_path})
        self.assertIn("PARAXIAL_F_NUMBER_REQUIRED", {f["code"] for f in added["findings"]})

        record["aperture"][sample["fact"]] = sample["data"]
        record["aperture"]["nominal_f_number"]["conditions"] = {
            key: value for key, value in sample["data"]["conditions"].items() if key != "method"
        }
        self.corpus.rewrite("synth", "axial", record)
        checked = check_intake.run(self.root, {project_path})
        self.assertTrue(checked["ok"], checked["findings"])
        [comparison] = checked["projects"][0]["configurations"][0]["paraxial_aperture"]["nominal_comparisons"]
        self.assertEqual((comparison["nominal"], comparison["computed"]), (4, sample["data"]["value"]))
        self.assertEqual(self.search(sample["fact"], 7)["outcome"], "MATCH")
        self.assertEqual(self.search(sample["fact"], 6)["outcome"], "DOES_NOT_MATCH")

        record["aperture"][sample["fact"]]["value"] = 4
        self.corpus.rewrite("synth", "axial", record)
        findings = check_intake.run(self.root, {project_path})["findings"]
        self.assertIn("PARAXIAL_F_NUMBER_MISMATCH", {f["code"] for f in findings})

    def test_refractive_clear_aperture_can_be_the_limiting_opening(self):
        project = axial_project(clear_radius="2")
        project["components"].pop()
        project["optical_models"].pop()
        record = self.add(project)
        result = check_intake.run(self.root, None)
        self.assertTrue(result["ok"], result["findings"])
        [sample] = result["projects"][0]["configurations"][0]["paraxial_aperture"]["samples"]
        self.assertEqual(sample["limiting_aperture"], "LENS/S1")
        self.assertAlmostEqual(sample["data"]["value"], 50 / 4)
        record["aperture"][sample["fact"]] = sample["data"]
        self.corpus.rewrite("synth", "axial", record)
        self.assertEqual(self.search(sample["fact"], 13)["outcome"], "MATCH")
        self.assertEqual(self.search(sample["fact"], 13, requires_blocking_stop=True)["outcome"], "UNCONFIRMED")

    def test_working_f_number_tracks_configured_object_and_leaves_unknown_open(self):
        project = axial_project()
        source = project["components"][0]["source_model"]
        project["configurations"] = [
            {"configuration_id": cid, "source_models": [
                {"instance_id": "SRC", "source_model": dict(source, waist_position_mm=offset)},
            ]}
            for cid, offset in (("Far", 0), ("Near", 100), ("Unknown", 200))
        ]

        def configure(record):
            record["record_schema_version"] = "1.1"
            record["design"].pop("conjugate")
            record["design"]["configuration_count"] = 3
            record.pop("field")
            aperture, first_order = record.pop("aperture"), record.pop("first_order")
            record["configurations"] = [
                {"configuration_id": cid, "conjugate": "FINITE_TO_FINITE",
                 "aperture": copy.deepcopy(aperture), "first_order": copy.deepcopy(first_order)}
                for cid in ("Far", "Near", "Unknown")
            ]

        record = self.add(project, configure)
        audit = check_intake.run(self.root, None)
        self.assertTrue(audit["ok"], audit["findings"])
        configurations = {row["configuration_id"]: row["paraxial_aperture"]
                          for row in audit["projects"][0]["configurations"]}
        name = "paraxial_working_f_number"
        for entry, expected, distance in zip(record["configurations"], (65 / 6, 115 / 6), (200, 100)):
            [sample] = configurations[entry["configuration_id"]]["samples"]
            self.assertEqual(sample["fact"], name)
            self.assertAlmostEqual(sample["data"]["value"], expected)
            self.assertEqual(sample["data"]["conditions"]["object_distance_mm"], distance)
            entry["aperture"][name] = sample["data"]
        self.assertEqual(configurations["Unknown"]["state"], "UNCONFIRMED")
        self.corpus.rewrite("synth", "axial", record)
        self.assertTrue(check_intake.run(self.root, {record["native_project"]["path"]})["ok"])
        result = self.search(name, 15)
        self.assertEqual((result["configuration_id"], result["outcome"]), ("Far", "MATCH"))
        self.assertEqual({row["configuration_id"]: row["outcome"] for row in result["other_configurations"]},
                         {"Near": "DOES_NOT_MATCH", "Unknown": "UNCONFIRMED"})

        record["configurations"][0]["aperture"][name]["conditions"]["object_distance_mm"] = 100
        self.corpus.rewrite("synth", "axial", record)
        findings = check_intake.run(self.root, None)["findings"]
        self.assertIn("PARAXIAL_F_NUMBER_UNCONFIRMED", {f["code"] for f in findings})


if __name__ == "__main__":
    unittest.main()
