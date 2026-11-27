"""Regression tests for the contribution gate's record selection and metric checks."""

import copy
import tempfile
import unittest
from pathlib import Path

from test_build_foundation import SynthCorpus

from os_optics_lens.corpus import load_corpus
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


if __name__ == "__main__":
    unittest.main()
