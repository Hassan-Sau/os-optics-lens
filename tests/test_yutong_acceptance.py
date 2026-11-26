"""Check the Yutong query contract against the P2b record."""

import copy
import hashlib
import json
import math
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


def proportional_weights(actual, expected):
    if not isinstance(actual, list) or not actual or len(actual) != len(expected):
        return False
    if any(type(weight) not in (int, float) or not math.isfinite(weight) or weight < 0
           for weight in (*actual, *expected)):
        return False
    actual_scale, expected_scale = max(actual), max(expected)
    return bool(actual_scale and expected_scale) and all(
        math.isclose(a / actual_scale, b / expected_scale, rel_tol=1e-12)
        for a, b in zip(actual, expected)
    )


def matching_spectrum(actual, expected):
    return (
        isinstance(actual, dict)
        and actual.get("sampling_wavelengths_nm") == expected["sampling_wavelengths_nm"]
        and proportional_weights(actual.get("incident_weights"), expected["incident_weights"])
    )


def evidence_section(source):
    if not isinstance(source, dict):
        return None
    path, section, digest = (source.get(key) for key in ("path", "section", "sha256"))
    if not all(isinstance(value, str) and value for value in (path, section, digest)):
        return None
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        return None
    path = (ROOT / path).resolve()
    if not path.is_relative_to(ROOT):
        return None
    try:
        payload = path.read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(payload).hexdigest() == digest:
            return at(json.loads(payload), ["sections", section])
    except (OSError, UnicodeError, ValueError):
        return None
    return None


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
        if all(
            matching_spectrum(at(fact, ["conditions", key]), expected) if key == "spectrum"
            else at(fact, ["conditions", key]) == expected
            for key, expected in conditions.items()
        )
    ]
    if len(comparable) != 1:
        return UNCONFIRMED
    fact = comparable[0]

    required_samples = constraint.get("required_sampled_field_fractions")
    if required_samples is not None and fact.get("sampled_field_fractions") != required_samples:
        return UNCONFIRMED
    if constraint.get("requires_evidence_source") and evidence_section(fact.get("source")) is None:
        return UNCONFIRMED

    outcomes = []
    for predicate in constraint["predicates"]:
        value = at(fact, predicate["path"].split("."))
        op = predicate["op"]
        if value is None:
            outcomes.append(UNCONFIRMED)
        elif op == "proportional_weights":
            outcomes.append(MATCH if proportional_weights(value, predicate["value"]) else DOES_NOT_MATCH)
        elif op == "has_source":
            outcomes.append(MATCH if evidence_section(value) is not None else UNCONFIRMED)
        elif op == "has_sourced_method":
            sourced = any(evidence_section(method.get("source")) is not None for method in value)
            outcomes.append(MATCH if sourced else UNCONFIRMED)
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

    def test_spectral_weights_compare_by_ratio(self):
        record = copy.deepcopy(RECORD)
        constraints = {constraint["id"]: constraint for constraint in CASE["constraints"]}
        record["spectrum"]["incident_weights"] = [2, 2, 2]
        for metric in ("mtf_field_minimum", "relative_illumination"):
            fact = next(fact for fact in record["performance"] if fact["metric"] == metric)
            fact["conditions"]["spectrum"]["incident_weights"] = [2, 2, 2]
        for name in ("spectral_sampling", "mtf_0_to_0p8", "corner_relative_illumination"):
            with self.subTest(constraint=name):
                self.assertEqual(evaluate(record, constraints[name]), MATCH)
        record["spectrum"]["sampling_wavelengths_nm"].reverse()
        self.assertEqual(evaluate(record, constraints["spectral_sampling"]), DOES_NOT_MATCH)

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

    def test_p2b_review_extract_reproduces_search_values(self):
        facts = {fact["metric"]: fact for fact in RECORD["performance"]}
        mtf = facts["mtf_field_minimum"]
        field = evidence_section(mtf["source"])
        self.assertEqual(field, evidence_section(RECORD["field"]["verification"]["source"]))
        self.assertTrue(matching_spectrum(field["spectrum"], mtf["conditions"]["spectrum"]))
        self.assertEqual(field["mtf_frequency_lp_mm"], mtf["conditions"]["frequency_lp_mm"])
        rows = [dict(zip(field["columns"], row, strict=True)) for row in field["rows"]]
        samples = [row for row in rows if row["fraction"] <= mtf["conditions"]["field_end"]]
        self.assertEqual([row["fraction"] for row in samples], mtf["sampled_field_fractions"])
        minimum, fraction, direction = min(
            (row[direction + "_MTF40"], row["fraction"], direction)
            for row in samples for direction in mtf["conditions"]["directions"]
        )
        self.assertEqual(minimum, mtf["value"])
        self.assertEqual(mtf["limiting_sample"], {"field_fraction": fraction, "direction": direction})
        illumination = facts["relative_illumination"]
        self.assertEqual(field, evidence_section(illumination["source"]))
        self.assertEqual(field["relative_illumination_conditions"], illumination["conditions"])
        corner = next(row for row in rows if row["fraction"] == illumination["conditions"]["field_fraction"])
        self.assertEqual(corner["relative_illumination_pct"], illumination["value_percent"])
        back_focus = RECORD["first_order"]["final_powered_vertex_to_sensor_mm"]
        self.assertEqual(evidence_section(back_focus["source"])["value_mm"], back_focus["value"])

        tolerance = RECORD["analysis_evidence"]["tolerance"]
        for gate in (tolerance["mtf_gate"], tolerance["geometry_gate"]):
            section = evidence_section(gate["source"])
            self.assertEqual((section["passed"], section["samples"]), (gate["passed"], gate["samples"]))
        ghost = RECORD["analysis_evidence"]["ghost"]
        for method in ghost["methods"]:
            section = evidence_section(method["source"])
            for key, value in method.items():
                if key != "source":
                    self.assertEqual(section[key], value)

    def test_sonnar_review_extract_reproduces_search_values(self):
        _, sonnar = CAMERA_RECORDS
        field = sonnar["field"]["verification"]
        rows = evidence_section(field["source"])["rows"]
        self.assertEqual([target for target, _ in rows], sonnar["field"]["field_points_mm"])
        maximum_error = max(abs(target - actual) for target, actual in rows)
        self.assertEqual(maximum_error, field["maximum_image_height_difference_mm"])

        facts = [fact for fact in sonnar["performance"] if fact["metric"] == "mtf"]
        self.assertEqual(
            sorted(evidence_section(facts[0]["source"])["rows"]),
            sorted([fact["image_height_mm"], fact["frequency_lp_mm"], fact["direction"], fact["value"]]
                   for fact in facts),
        )
        self.assertTrue(all(fact["source"] == facts[0]["source"] for fact in facts))

    def test_contributed_licenses_and_review_extracts(self):
        for record in CAMERA_RECORDS:
            with self.subTest(record=record["record_id"]):
                collection = record["collection"]
                license = collection["license"]
                self.assertEqual(license["spdx"], "MIT")
                self.assertIn(license["copyright"], (ROOT / license["notice_path"]).read_text(encoding="utf-8"))
                source = collection["evidence_extract"]
                payload = (ROOT / source["path"]).read_bytes().replace(b"\r\n", b"\n")
                self.assertEqual(hashlib.sha256(payload).hexdigest(), source["sha256"])
                extract = json.loads(payload)
                self.assertEqual(extract["license"], license)
                self.assertEqual(extract["native_project_sha256"], record["native_project"]["sha256"])
                self.assertEqual(extract["study_project_sha256"], collection["source_input_sha256"])

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
