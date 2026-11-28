"""Run the repository's contribution checks and report native first-order facts."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath
from typing import Any

CHECKOUT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHECKOUT / "src"))

from os_optics_lens.canonical import is_number  # noqa: E402
from os_optics_lens.corpus import NormalizedRecord, load_corpus  # noqa: E402
from os_optics_lens.errors import ERROR, Finding, finding  # noqa: E402
from os_optics_lens.normalize import configuration_views  # noqa: E402
from os_optics_lens.paraxial_aperture import calculate  # noqa: E402
from os_optics_lens.project_facts import (  # noqa: E402
    PARAXIAL_F_NUMBER_CONVENTIONS, PROJECT_BASES, _basis, _native_spectrum, is_checked_paraxial_fact,
)

ENGINE_VERSION = "0.14.0"
FIRST_ORDER = {"effective_focal_length_mm": "efl_mm", "back_focal_length_mm": "bfl_mm"}
WAVELENGTH_TOLERANCE_NM = 1e-6
RELATIVE_TOLERANCE = 1e-6
ABSOLUTE_TOLERANCE_MM = 1e-7
CHECKER_FILES = {"scripts/check_intake.py", ".github/workflows/intake.yml", "pyproject.toml"}
NOMINAL_F_NUMBER_FIELDS = {
    *PARAXIAL_F_NUMBER_CONVENTIONS, "nominal_f_number", "f_number", "image_space_f_number", "working_f_number",
}


def changed_paths(root: Path, base: str) -> set[str]:
    commit = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}"], text=True,
    ).strip()
    data = subprocess.check_output(["git", "-C", str(root), "diff", "--name-only", "--no-renames", "-z", commit, "--"])
    return set(data.decode("utf-8").split("\0")) - {""}


def selected_records(records: list[NormalizedRecord], paths: set[str] | None) -> list[NormalizedRecord]:
    if paths is None or paths & CHECKER_FILES or any(path.startswith("src/os_optics_lens/") for path in paths):
        return records
    changed_directories = {PurePosixPath(path).parent.as_posix() for path in paths}
    return [record for record in records if (
        PurePosixPath(record.file).parent.as_posix() in changed_directories
        or record.project_path in paths
        or any(ref.path in paths for ref in record.evidence_refs)
    )]


def text_present(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def intake_metadata(record: NormalizedRecord) -> list[Finding]:
    collection = record.record["collection"]
    problems = [
        finding(ERROR, "PROVENANCE_REQUIRED", record.record_id, record.file, f"collection.{key}", message)
        for key, message in {
            "source": "Name the direct source or the original contributor.",
            "attribution": "Provide attribution for the submitted design.",
        }.items()
        if not text_present(collection.get(key))
    ]
    expected_project = PurePosixPath(record.file).with_name("project.json").as_posix()
    if record.project_path != expected_project:
        problems.append(finding(ERROR, "PROJECT_PATH_MISMATCH", record.record_id, record.file, "native_project.path",
                                "Put project.json next to record.json.",
                                expected=expected_project, actual=record.project_path))
    license_info = collection.get("license")
    licensed = (isinstance(license_info, dict) and text_present(license_info.get("spdx"))
                and text_present(license_info.get("notice_path")))
    if not licensed and not text_present(collection.get("redistribution")):
        problems.append(finding(ERROR, "REDISTRIBUTION_REQUIRED", record.record_id, record.file,
                                "collection.redistribution", "Provide redistribution terms or a license and notice."))
    return problems


def duplicate_projects(records: list[NormalizedRecord], selected: set[str]) -> list[Finding]:
    by_digest: dict[str, list[NormalizedRecord]] = defaultdict(list)
    for record in records:
        by_digest[record.project_sha256].append(record)
    problems = []
    for copies in by_digest.values():
        if len(copies) < 2:
            continue
        for record in copies:
            if record.record_id in selected:
                other_ids = ", ".join(item.record_id for item in copies if item is not record)
                problems.append(finding(ERROR, "DUPLICATE_PROJECT", record.record_id, record.file,
                                        "native_project.sha256", f"Identical Project already appears in {other_ids}."))
    return problems


def compare_first_order(record: NormalizedRecord, configuration_id: str | None,
                        results: list[dict[str, Any]]) -> list[Finding]:
    view = next((view for view in record.views if view.configuration_id == configuration_id), None)
    if view is None or not results:
        return []
    primary = view.view.get("spectrum", {}).get("primary_wavelength_nm")
    if primary is None and configuration_id is None:
        primary = record.record.get("spectrum", {}).get("primary_wavelength_nm")
    fields = {f"first_order.{name}": name for name in FIRST_ORDER}
    problems = []
    for item in record.facts[view.configuration_key]:
        name = fields.get(item["fact_key"])
        value = item["value_num"]
        if name is None or item["basis_class"] != "ENGINE_COMPUTED" or not is_number(value):
            continue
        conditions = json.loads(item["conditions_json"] or "{}")
        wavelength = conditions.get("wavelength_nm")
        if wavelength is None:
            wavelength = results[0]["wavelength_nm"] if len(results) == 1 else primary
        field = item["json_path"]
        if configuration_id is not None:
            field = f"configuration {configuration_id}: {field}"
        sample = next((sample for sample in results if is_number(wavelength) and math.isclose(
            sample["wavelength_nm"], wavelength, rel_tol=0, abs_tol=WAVELENGTH_TOLERANCE_NM,
        )), None)
        if sample is None or name not in sample:
            problems.append(finding(ERROR, "FIRST_ORDER_UNCONFIRMED", record.record_id, record.file, field,
                                    f"No native result at the declared vacuum wavelength ({wavelength} nm). "
                                    "Correct the conditions or omit the claim."))
        elif not math.isclose(sample[name], value, rel_tol=RELATIVE_TOLERANCE, abs_tol=ABSOLUTE_TOLERANCE_MM):
            problems.append(finding(ERROR, "FIRST_ORDER_MISMATCH", record.record_id, record.file, field,
                                    f"Stored value differs from the Engine result at {sample['wavelength_nm']} nm.",
                                    expected=sample[name], actual=value))
    return problems


def native_first_order(project: Any, payload: dict[str, Any], configuration_id: str | None,
                       paraxial_analysis: Any) -> list[dict[str, Any]]:
    lenses = [component["instance_id"] for component in payload["components"] if component.get("optical_role") == "lens"]
    if len(lenses) != 1:
        return []
    wavelengths = _native_spectrum(payload, None).get("sampling_wavelengths_nm", [])
    results = []
    for wavelength in wavelengths:
        request = {"components": lenses, "wavelength_nm": wavelength}
        if configuration_id is not None:
            request["configuration_id"] = configuration_id
        analysis = paraxial_analysis(project, request)
        row = {"wavelength_nm": wavelength}
        if analysis["ok"]:
            row.update({name: analysis["system"][key] for name, key in FIRST_ORDER.items()
                        if is_number(analysis["system"].get(key))})
        else:
            row["unconfirmed"] = analysis["error"]
        results.append(row)
    return results


def check_aperture(record: NormalizedRecord, configuration_id: str | None, raw_view: dict,
                   report: dict, require_fact: bool) -> list[Finding]:
    aperture = raw_view.get("aperture") or {}
    prefix = f"configuration {configuration_id}: " if configuration_id is not None else ""
    nominal = {key: fact["value"] for key, fact in aperture.items() if key in NOMINAL_F_NUMBER_FIELDS
               and isinstance(fact, dict) and _basis(fact.get("basis")) == "SOURCE_STATED"
               and is_number(fact.get("value")) and fact["value"] > 0}
    if nominal:
        report["nominal_f_numbers"] = nominal
    samples = report.get("samples", [])
    comparisons = []
    for key, value in nominal.items():
        declared = aperture[key].get("conditions")
        if not isinstance(declared, dict):
            continue
        for sample in samples:
            data = sample["data"]
            comparable = {k: v for k, v in data["conditions"].items() if k != "method"}
            if comparable.keys() <= declared.keys() and same_aperture_conditions(
                comparable, {k: declared[k] for k in comparable},
            ):
                comparisons.append({"nominal_field": key, "fact": sample["fact"], "conditions": comparable,
                                    "nominal": value, "computed": data["value"]})
    if comparisons:
        report["nominal_comparisons"] = comparisons
    indexed = {item["fact_key"]: item for item in record.facts.get(configuration_id or "", ())
               if is_number(item["value_num"]) and item["eligible_for"] != "DISCOVERY_ONLY"}
    problems = []
    verified = set()
    for key in PARAXIAL_F_NUMBER_CONVENTIONS:
        fact = aperture.get(key)
        if not isinstance(fact, dict) or _basis(fact.get("basis")) not in PROJECT_BASES:
            continue
        field = f"{prefix}aperture.{key}"
        sample = None
        fact_key = f"aperture.{key}"
        if fact_key in indexed and is_checked_paraxial_fact(fact_key, fact):
            conditions = fact["conditions"]
            sample = next((s for s in samples if s["fact"] == key
                           and same_aperture_conditions(s["data"]["conditions"], conditions)), None)
        if sample is None:
            problems.append(finding(ERROR, "PARAXIAL_F_NUMBER_UNCONFIRMED", record.record_id, record.file, field,
                                    "No searchable native f-number under these conditions. "
                                    "Use a supported paraxial_aperture sample from the report or omit the value."))
        elif not math.isclose(sample["data"]["value"], fact["value"], rel_tol=RELATIVE_TOLERANCE, abs_tol=1e-8):
            problems.append(finding(ERROR, "PARAXIAL_F_NUMBER_MISMATCH", record.record_id, record.file, field,
                                    "The stored f-number differs from the admitted paraxial cone of the native Project.",
                                    expected=sample["data"]["value"], actual=fact["value"]))
        else:
            verified.add(key)
    if require_fact and nominal and samples and not verified and not problems:
        key = samples[0]["fact"]
        problems.append(finding(ERROR, "PARAXIAL_F_NUMBER_REQUIRED", record.record_id, record.file,
                                f"{prefix}aperture.{key}",
                                "The Project has a supported f-number calculation. Store its per-configuration "
                                "paraxial_aperture sample under the matching aperture field."))
    return problems


def same_aperture_conditions(expected: dict, actual: dict) -> bool:
    if expected.keys() != actual.keys():
        return False
    for key, value in expected.items():
        other = actual[key]
        if key in ("wavelength_nm", "object_distance_mm"):
            tolerance = WAVELENGTH_TOLERANCE_NM if key == "wavelength_nm" else ABSOLUTE_TOLERANCE_MM
            if not is_number(other) or not math.isclose(value, other, rel_tol=0, abs_tol=tolerance):
                return False
        elif value != other:
            return False
    return True


def check_native(record: NormalizedRecord, *, require_aperture_fact: bool = False) -> tuple[dict[str, Any], list[Finding]]:
    from os_optics.local import load_project
    from os_optics.local.json_api import check_project, paraxial_analysis

    result = check_project(record.project_bytes)
    report = {"record_id": record.record_id, "project_sha256": record.project_sha256, "configurations": []}
    if not result["ok"]:
        report["engine_error"] = result["error"]
        return report, [finding(ERROR, "PROJECT_REFUSED", record.record_id, record.project_path, "",
                                "Engine refused the native Project. See the engine error in the report.")]
    problems = []
    project = load_project(result["project"])
    raw_views = {view.configuration_id: view.view for view in configuration_views(record.record, project.payload())}
    for state in result.get("configurations", [result]):
        cid = state.get("configuration_id")
        solids = state.get("optical_solids")
        row = {"configuration_id": cid, "solids": None if solids is None else solids["status"]}
        report["configurations"].append(row)
        if not state["ok"] or (solids is not None and solids["status"] != "VALID"):
            row["engine_error"] = state.get("problems") or solids
            problems.append(finding(ERROR, "CONFIGURATION_REFUSED", record.record_id, record.project_path,
                                    cid or "", "Engine did not accept this configuration and its optical solids."))
            continue
        configured = project.configured(cid) if cid is not None else project
        payload = configured.payload()
        samples = native_first_order(project, payload, cid, paraxial_analysis)
        row["first_order"] = samples
        if not samples:
            row["first_order_unconfirmed"] = "Expected one lens component and at least one native source wavelength."
        problems.extend(compare_first_order(record, cid, samples))
        raw_view = raw_views.get(cid, {})
        conjugate = raw_view.get("design", {}).get("conjugate") or ""
        wavelengths = _native_spectrum(payload, None).get("sampling_wavelengths_nm", [])
        aperture = calculate(configured, payload, conjugate.lower(), wavelengths)
        row["paraxial_aperture"] = aperture
        problems.extend(check_aperture(record, cid, raw_view, aperture, require_aperture_fact))
    return report, problems


def check_layout(root: Path) -> list[Finding]:
    problems = []
    for path in sorted(p for name in ("record.json", "project.json") for p in (root / "records").rglob(name)):
        relative = path.relative_to(root)
        if len(relative.parts) != 4 or not path.is_file():
            problems.append(finding(ERROR, "INVALID_RECORD_LAYOUT", None, relative.as_posix(), "",
                                    "Use records/<collection>/<record>/ for each record and Project."))
        elif path.name == "project.json" and not path.with_name("record.json").is_file():
            problems.append(finding(ERROR, "ORPHAN_PROJECT", None, relative.as_posix(), "",
                                    "Add record.json next to this Project."))
    return problems


def run(root: Path, paths: set[str] | None) -> dict[str, Any]:
    corpus = load_corpus(root)
    selected = selected_records(corpus.records, paths)
    findings = [*corpus.findings, *check_layout(root)]
    findings.extend(duplicate_projects(corpus.records, {record.record_id for record in selected}))
    reports = []
    for record in selected:
        findings.extend(intake_metadata(record))
        report, problems = check_native(record, require_aperture_fact=paths is not None and record.project_path in paths)
        reports.append(report)
        findings.extend(problems)
    errors = sum(item.severity == ERROR for item in findings)
    return {
        "ok": errors == 0, "engine_version": ENGINE_VERSION,
        "corpus_records": len(corpus.records), "projects_checked": len(reports),
        "errors": errors, "warnings": len(findings) - errors,
        "findings": [f.to_dict() for f in sorted(findings, key=Finding.sort_key)],
        "projects": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CHECKOUT, help="directory containing records/")
    parser.add_argument("--base", help="limit Engine checks to records changed since this Git commit")
    parser.add_argument("--output", type=Path, help="write the full JSON report to this file")
    args = parser.parse_args()
    try:
        installed = version("os-optics")
    except PackageNotFoundError:
        installed = None
    if installed != ENGINE_VERSION:
        parser.error(f"Install os-optics=={ENGINE_VERSION} before running this check (found {installed or 'none'}).")
    if not (args.corpus / "records").is_dir():
        parser.error(f"no records/ directory in {args.corpus}")
    try:
        paths = changed_paths(args.corpus, args.base) if args.base is not None else None
    except subprocess.CalledProcessError:
        parser.error(f"could not compare the corpus against {args.base!r}")
    result = run(args.corpus, paths)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for item in result["findings"]:
        location = f"{item['file']} {item['field']}".rstrip()
        print(f"{item['severity']}: {location}: {item['code']}: {item['message']}")
    print(f"Lens intake: {result['projects_checked']} Projects checked, "
          f"{result['errors']} errors, {result['warnings']} warnings.")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
