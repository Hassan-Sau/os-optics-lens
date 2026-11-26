"""Configuration semantics end to end (SPEC section 2.3, 6.4; amendments 10.5, section 9).

A synthetic record_schema_version 1.1 record carries two native configurations `Wide`/`Tele`.
Search must evaluate every hard constraint against one configuration view, report native ids, and
never MATCH a record because different configurations satisfy different constraints. Build-time
configuration findings (CONFIGURATION_UNMAPPED / UNKNOWN / PROJECT_CONFIGURATION_INVALID /
top-level inheritance) are covered in test_build_foundation.ConfigurationTests and re-checked here
through the public build API.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from os_optics_lens import query  # noqa: E402
from os_optics_lens.build import build_index  # noqa: E402
from os_optics_lens.errors import LensError  # noqa: E402
from os_optics_lens.store import open_index  # noqa: E402

_spec = importlib.util.spec_from_file_location("_build_foundation_helpers", ROOT / "tests/test_build_foundation.py")
helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpers)

ALL = ["MATCH", "UNCONFIRMED", "DOES_NOT_MATCH"]
EFL = "first_order.effective_focal_length_mm"
HALF_FIELD = "field.half_field_deg"


def two_configurations(record: dict) -> None:
    """Wide: EFL 50 mm, half field 23 deg. Tele: EFL 100 mm, half field 12 deg."""
    record["record_schema_version"] = "1.1"
    record["design"].pop("conjugate")
    record["design"]["configuration_count"] = 2
    first_order, aperture, field = record.pop("first_order"), record.pop("aperture"), record.pop("field")
    performance = record.pop("performance")
    wide = {"configuration_id": "Wide", "conjugate": "INFINITE_TO_FINITE", "first_order": first_order,
            "aperture": aperture, "field": field, "performance": performance}
    tele = copy.deepcopy(wide)
    tele.update(configuration_id="Tele", label="tele end")
    tele["first_order"]["effective_focal_length_mm"]["value"] = 100.0
    tele["field"]["half_field_deg"] = 12.0
    record["configurations"] = [wide, tele]


class ConfigurationSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name) / "corpus"
        corpus = helpers.SynthCorpus(root)
        project = helpers.minimal_project([{"configuration_id": "Wide", "label": "wide end"},
                                           {"configuration_id": "Tele"}])
        corpus.add("zoom", project=project, mutate=two_configurations)
        corpus.add("prime", project=helpers.minimal_project([{"configuration_id": "Only", "label": "the one"}]))
        corpus.add("plain")
        cls.index_path = Path(cls._tmp.name) / "index.sqlite"
        result = build_index(root, cls.index_path)
        assert (result.records, result.configurations) == (3, 4), result.to_dict()
        cls.index = open_index(cls.index_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.index.close()
        cls._tmp.cleanup()

    def search(self, constraints: list[dict], **extra) -> dict:
        request = {"mode": "specification", "filters": {"record_ids": ["zoom"]}, "constraints": constraints,
                   "include": ALL, **extra}
        [candidate] = query.search(self.index, request)["result"]["candidates"]
        return candidate

    def test_no_cross_configuration_match(self) -> None:
        constraints = [{"id": "short", "fact": EFL, "op": "lte", "value": 60},
                       {"id": "narrow", "fact": HALF_FIELD, "op": "lte", "value": 15}]
        candidate = self.search(constraints)
        self.assertEqual(candidate["outcome"], "DOES_NOT_MATCH")
        self.assertEqual(candidate["counts"], {"MATCH": 1, "UNCONFIRMED": 0, "DOES_NOT_MATCH": 1})
        self.assertIn(candidate["configuration_id"], ("Wide", "Tele"))
        others = candidate["other_configurations"]
        self.assertEqual(len(others), 1)
        self.assertEqual({candidate["configuration_id"], others[0]["configuration_id"]}, {"Wide", "Tele"})
        self.assertEqual(others[0]["outcome"], "DOES_NOT_MATCH")
        default = query.search(self.index, {"mode": "specification", "filters": {"record_ids": ["zoom"]},
                                            "constraints": constraints})
        self.assertEqual(default["result"]["candidates"], [])

    def test_best_configuration_carries_native_id(self) -> None:
        candidate = self.search([{"id": "long", "fact": EFL, "op": "gte", "value": 90}])
        self.assertEqual((candidate["outcome"], candidate["configuration_id"]), ("MATCH", "Tele"))
        self.assertEqual([(o["configuration_id"], o["outcome"]) for o in candidate["other_configurations"]],
                         [("Wide", "DOES_NOT_MATCH")])
        candidate = self.search([{"id": "both", "fact": EFL, "op": "between_inclusive", "value": [40, 110]}])
        self.assertEqual((candidate["outcome"], candidate["configuration_id"]), ("MATCH", "Wide"))

    def test_both_constraints_in_one_configuration(self) -> None:
        candidate = self.search([{"id": "long", "fact": EFL, "op": "gte", "value": 90},
                                 {"id": "narrow", "fact": HALF_FIELD, "op": "lte", "value": 15}])
        self.assertEqual((candidate["outcome"], candidate["configuration_id"]), ("MATCH", "Tele"))

    def test_outcome_tie_prefers_more_match_constraints(self) -> None:
        # §6.4: equal outcomes are broken by more MATCH, then fewer DOES_NOT_MATCH, before
        # preferences and the ordinal. Both configurations fail EFL >= 200; only Tele (12 deg)
        # meets the half field, so Tele is reported even though Wide comes first and the
        # ascending EFL preference favours Wide (50 mm).
        constraints = [{"id": "very_long", "fact": EFL, "op": "gte", "value": 200},
                       {"id": "narrow", "fact": HALF_FIELD, "op": "lte", "value": 15}]
        for extra in ({}, {"preferences": [{"fact": EFL, "direction": "ascending"}]}):
            with self.subTest(**extra):
                candidate = self.search(constraints, **extra)
                self.assertEqual((candidate["outcome"], candidate["configuration_id"]), ("DOES_NOT_MATCH", "Tele"))
                self.assertEqual(candidate["counts"], {"MATCH": 1, "UNCONFIRMED": 0, "DOES_NOT_MATCH": 1})
                self.assertEqual(candidate["constraints"]["narrow"], "MATCH")
                self.assertEqual([c["constraint"] for c in candidate["shortfalls"]], ["very_long"])
                self.assertEqual(candidate["other_configurations"],
                                 [{"configuration_id": "Wide", "outcome": "DOES_NOT_MATCH",
                                   "counts": {"MATCH": 0, "UNCONFIRMED": 0, "DOES_NOT_MATCH": 2}}])

    def test_starting_point_picks_nearest_configuration(self) -> None:
        response = query.search(self.index, {"mode": "starting_point", "filters": {"record_ids": ["zoom"]},
                                             "targets": [{"fact": EFL, "target": 95, "tolerance": 5}]})
        [candidate] = response["result"]["candidates"]
        self.assertEqual(candidate["configuration_id"], "Tele")
        self.assertAlmostEqual(candidate["shortfalls"][0]["deviation"], 5.0)

    def test_single_native_configuration_and_project_as_written(self) -> None:
        response = query.search(self.index, {"mode": "specification", "filters": {"record_ids": ["prime", "plain"]},
                                             "constraints": [{"fact": EFL, "op": "lte", "value": 60}]})
        ids = {c["record_id"]: c["configuration_id"] for c in response["result"]["candidates"]}
        self.assertEqual(ids, {"prime": "Only", "plain": None})
        inspected = query.inspect(self.index, "prime")["result"]
        self.assertEqual(inspected["configurations"][0]["configuration_id"], "Only")
        self.assertIs(inspected["configurations"][0]["native"], True)

    def test_compare_and_inspect_by_configuration(self) -> None:
        rows = query.compare(self.index, ["zoom@Wide", "zoom@Tele"], fields=[EFL])["result"]["rows"]
        self.assertEqual([v["value"] for v in rows[0]["values"]], [50.0, 100.0])
        inspected = query.inspect(self.index, "zoom", configuration="Tele", fields=[EFL])["result"]
        self.assertEqual(inspected["configuration"]["configuration_id"], "Tele")
        self.assertEqual(inspected["fields"][EFL]["value"]["value"], 100.0)
        with self.assertRaises(LensError) as caught:
            query.inspect(self.index, "zoom", configuration="Mid")
        self.assertEqual(caught.exception.code, "CONFIGURATION_NOT_FOUND")
        project = query.project_metadata(self.index, "zoom")
        self.assertEqual(project["native_configuration_ids"], ["Wide", "Tele"])


class ConfigurationBuildErrors(unittest.TestCase):
    def test_unmapped_and_unknown_fail_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "corpus"
            corpus = helpers.SynthCorpus(root)
            corpus.add("unmapped", project=helpers.minimal_project([{"configuration_id": "A"},
                                                                   {"configuration_id": "B"}]))

            def unknown(record: dict) -> None:
                two_configurations(record)
                record["configurations"][1]["configuration_id"] = "Ghost"

            corpus.add("unknown", project=helpers.minimal_project([{"configuration_id": "Wide"},
                                                                  {"configuration_id": "Tele"}]), mutate=unknown)
            corpus.add("invalid", project=helpers.minimal_project([{"configuration_id": "nul"}]))

            def inherits(record: dict) -> None:
                record["record_schema_version"] = "1.1"
                record["configurations"] = [{"configuration_id": "A"}]

            corpus.add("inherits", project=helpers.minimal_project([{"configuration_id": "A"}]), mutate=inherits)
            with self.assertRaises(LensError) as caught:
                build_index(root, Path(tmp) / "index.sqlite")
            self.assertEqual(caught.exception.code, "BUILD_FAILED")
            found = {(f["code"], f["record_id"]) for f in caught.exception.details["findings"]}
            for expected in (("CONFIGURATION_UNMAPPED", "unmapped"), ("CONFIGURATION_UNKNOWN", "unknown"),
                             ("PROJECT_CONFIGURATION_INVALID", "invalid"), ("INVALID_FIELD", "inherits")):
                self.assertIn(expected, found)
            self.assertFalse((Path(tmp) / "index.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
