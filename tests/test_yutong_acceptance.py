"""Check the Yutong query contract against the P2b record."""

import copy
import hashlib
import json
import operator
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = json.loads((ROOT / "acceptance/yutong-2025-mirrorless-problem-2.json").read_text(encoding="utf-8"))
RECORD_PATH = ROOT / CASE["record"]["path"]
RECORD = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
SONNAR_PATH = ROOT / "records/opensci-design-studies/portrait-85-sonnar-eight/record.json"
CAMERA_RECORDS = (RECORD, json.loads(SONNAR_PATH.read_text(encoding="utf-8")))

MATCH = "MATCH"
UNCONFIRMED = "UNCONFIRMED"
DOES_NOT_MATCH = "DOES_NOT_MATCH"
OPERATORS = {
    "eq": operator.eq,
    "gt": operator.gt,
    "gte": operator.ge,
    "lte": operator.le,
    "in": lambda value, choices: value in choices,
    "between_inclusive": lambda value, limits: limits[0] <= value <= limits[1],
}


def at(data, path):
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def has_source(data):
    return (
        isinstance(data, dict)
        and bool(data.get("archive_member") or data.get("url"))
        and re.fullmatch(r"[0-9a-f]{64}", data.get("sha256", "")) is not None
    )


def evaluate(record, constraint):
    if constraint.get("requires_blocking_stop"):
        aperture_validity = at(record, ["design", "aperture_validity"]) or {}
        if not (aperture_validity.get("stop_blocks_light") is True
                and aperture_validity.get("eligible_for_stop_dependent_evaluation") is True):
            return UNCONFIRMED
    scope = at(record, constraint["scope"])
    if "metric" in constraint:
        candidates = [entry for entry in scope or [] if entry.get("metric") == constraint["metric"]]
    else:
        candidates = [scope] if scope is not None else []

    conditions = constraint.get("conditions", {})
    comparable = [
        fact for fact in candidates
        if all(at(fact, ["conditions", key]) == expected for key, expected in conditions.items())
    ]
    if len(comparable) != 1:
        return UNCONFIRMED
    fact = comparable[0]

    if constraint.get("metric") == "mtf_field_minimum":
        samples = fact.get("sampled_field_fractions", [])
        if (
            len(samples) < 3
            or sorted(set(samples)) != samples
            or (samples[0], samples[-1]) != (conditions["field_start"], conditions["field_end"])
        ):
            return UNCONFIRMED

    outcomes = []
    for predicate in constraint["predicates"]:
        value = at(fact, predicate["path"].split("."))
        op = predicate["op"]
        if value is None:
            outcomes.append(UNCONFIRMED)
        elif op == "has_source":
            outcomes.append(MATCH if has_source(value) else UNCONFIRMED)
        elif op == "has_sourced_method":
            outcomes.append(MATCH if any(has_source(item.get("source")) for item in value) else UNCONFIRMED)
        else:
            outcomes.append(MATCH if OPERATORS[op](value, predicate["value"]) else DOES_NOT_MATCH)

    if DOES_NOT_MATCH in outcomes:
        return DOES_NOT_MATCH
    if UNCONFIRMED in outcomes:
        return UNCONFIRMED
    return MATCH


class YutongAcceptance(unittest.TestCase):
    def test_optical_requirements_and_evidence(self):
        self.assertEqual(RECORD["record_id"], CASE["record"]["id"])
        self.assertEqual(RECORD["record_revision"], CASE["record"]["revision"])
        self.assertEqual(RECORD["design"]["configuration_count"], 1)
        expected = CASE["expected"]
        self.assertEqual(len(CASE["constraints"]), expected["confirmed_constraints"])
        for constraint in CASE["constraints"]:
            with self.subTest(constraint=constraint["id"]):
                self.assertEqual(evaluate(RECORD, constraint), expected["outcome"])

    def test_cost_is_a_ranking_preference(self):
        preference = CASE["ranking_preference"]
        cost = at(RECORD, preference["scope"])
        self.assertEqual(cost["scope"], preference["scope_of_cost"])
        self.assertEqual(cost["spherical_element_weight"], preference["spherical_element_weight"])
        self.assertEqual(cost["aspheric_element_weight"], preference["aspheric_element_weight"])
        aspheres = RECORD["design"]["aspheric_element_count"]
        spheres = RECORD["design"]["powered_element_count"] - aspheres
        weighted_count = spheres * cost["spherical_element_weight"] + aspheres * cost["aspheric_element_weight"]
        self.assertEqual(cost[preference["metric"]], weighted_count)
        self.assertEqual(weighted_count, CASE["expected"]["cost_proxy"])
        self.assertEqual(preference["direction"], "ascending")

    def test_counterexamples(self):
        constraints = {item["id"]: item for item in CASE["constraints"]}
        for case in CASE["counterexamples"]:
            with self.subTest(case=case["id"]):
                record = copy.deepcopy(RECORD)
                constraint = constraints[case["constraint"]]
                scope_path = constraint["scope"]
                if "record_path" in case:
                    *parent_path, key = case["record_path"]
                    at(record, parent_path)[key] = case["value"]
                elif case["path"]:
                    scope = at(record, scope_path)
                    if "metric" in constraint:
                        scope = next(entry for entry in scope if entry["metric"] == constraint["metric"])
                    *parent_path, key = case["path"].split(".")
                    parent = at(scope, parent_path)
                    if case.get("remove"):
                        del parent[key]
                    else:
                        parent[key] = case["value"]
                else:
                    parent = at(record, scope_path[:-1])
                    parent[scope_path[-1]] = at(record, case["copy_from"])
                self.assertEqual(evaluate(record, constraint), case["expected"])

    def test_record_and_native_project_hashes(self):
        for source in CAMERA_RECORDS:
            with self.subTest(record=source["record_id"]):
                record = copy.deepcopy(source)
                recorded_hash = record.pop("record_hash")
                record.pop("record_hash_method")
                payload = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
                self.assertEqual(hashlib.sha256(payload).hexdigest(), recorded_hash)
                project = ROOT / record["native_project"]["path"]
                project_bytes = project.read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(hashlib.sha256(project_bytes).hexdigest(), record["native_project"]["sha256"])

    def test_seed_format_aperture_and_paraxial_evidence(self):
        for record in CAMERA_RECORDS:
            with self.subTest(record=record["record_id"]):
                spectrum = record["spectrum"]
                self.assertEqual(spectrum["sampling_span_nm"]["eligible_for"], "DISCOVERY_ONLY")
                self.assertEqual(spectrum["continuous_coverage_nm"]["state"], "UNCONFIRMED")
                aperture = record["aperture"]
                declared_apertures = [key for key, fact in aperture.items() if fact.get("system_aperture")]
                self.assertEqual(declared_apertures, ["stop_opening_diameter_mm"])
                project = json.loads((ROOT / record["native_project"]["path"]).read_text(encoding="utf-8"))
                stop_fact = aperture["stop_opening_diameter_mm"]
                stop = next(item["model"] for item in project["optical_models"]
                            if item["model_id"] == stop_fact["source_model_id"])
                self.assertEqual(stop_fact["value"], 2 * float(stop["opening_radius_mm"]))
                self.assertGreater(float(stop["edge_radius_mm"]), float(stop["opening_radius_mm"]))
                engine = record["first_order"]["engine_check"]
                self.assertEqual(engine["wavelength_nm"], spectrum["primary_wavelength_nm"])
                comparison = engine["comparison"]
                efl = comparison["effective_focal_length"]
                bfl = comparison["back_focal_length"]
                self.assertEqual(efl["scale_mm"], abs(efl["source_mm"]))
                self.assertEqual(bfl["scale_mm"], max(abs(bfl["source_mm"]), abs(efl["source_mm"])))
                for quantity in (efl, bfl):
                    tolerance = comparison["atol_mm"] + comparison["rtol"] * quantity["scale_mm"]
                    self.assertEqual(quantity["tolerance_mm"], tolerance)
                    difference = abs(quantity["engine_mm"] - quantity["source_mm"])
                    self.assertEqual(quantity["absolute_difference_mm"], difference)
                    self.assertEqual(quantity["within_tolerance"], difference <= tolerance)
                    self.assertTrue(quantity["within_tolerance"])


if __name__ == "__main__":
    unittest.main()
