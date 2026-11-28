"""Axial paraxial f-numbers of centered sequential imaging Projects.

Only contribution checking calls the Engine. Search reads the checked, per-configuration
facts from the record, so an installed retriever needs no Engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .canonical import is_number
from .project_facts import (
    AXIAL_PARAXIAL_METHOD, ENTRANCE_PUPIL_F_NUMBER, PARAXIAL_F_NUMBER_CONVENTIONS, PARAXIAL_WORKING_F_NUMBER,
    _axis, _dot, _observation_pose, _position, _same_axis,
)

CONJUGATE_FACT = {"infinite_to_finite": ENTRANCE_PUPIL_F_NUMBER, "finite_to_finite": PARAXIAL_WORKING_F_NUMBER}
AXIS_TOLERANCE_MM = 1e-6


def is_checked_paraxial_fact(key: str, fact: Any) -> bool:
    """Recognize the contribution checker’s convention, distinct from historical aperture facts."""
    name = key.removeprefix("aperture.")
    if key != f"aperture.{name}" or name not in CONVENTIONS or not isinstance(fact, dict):
        return False
    conditions = fact.get("conditions")
    return (fact.get("basis") == BASIS and isinstance(conditions, dict)
            and conditions.get("method") == METHOD and conditions.get("convention") == CONVENTIONS[name]
            and is_number(fact.get("value")) and fact["value"] > 0)


class Unconfirmed(ValueError):
    """The Project does not establish a supported paraxial f-number."""


@dataclass(frozen=True)
class Plane:
    z: float
    label: str
    radius: float
    curvature: float = 0
    before: str | None = None
    after: str | None = None


def axial_position(pose: dict, origin: tuple[float, ...], direction: tuple[float, ...]) -> float:
    position = _position(pose)
    if position is None or not _same_axis(direction, _axis(pose)):
        raise Unconfirmed("Expected forward, coaxial lenses, sources and image plane.")
    offset = [value - start for value, start in zip(position, origin)]
    z = _dot(offset, direction)
    if math.dist(offset, [z * value for value in direction]) > AXIS_TOLERANCE_MM:
        raise Unconfirmed("Expected forward, coaxial lenses, sources and image plane.")
    return z


def axial_sources(payload: dict, origin: tuple, direction: tuple, first_z: float) -> list[tuple[float, dict]]:
    sources = []
    for component in payload["components"]:
        model = component.get("source_model")
        if model is None:
            continue
        try:
            z = axial_position(component["nominal_pose"], origin, direction)
        except Unconfirmed:
            # Other sources may sample off-axis fields in the same configuration.
            continue
        if z < first_z:
            sources.append((z, model))
    if not sources:
        raise Unconfirmed("Expected an axial source before the first optical surface.")
    return sources


def sequence_planes(lowered: Any, payload: dict) -> tuple[list[Plane], tuple, tuple]:
    """Use the Engine's resolved element and material models, in its local +Z convention."""
    if not lowered.elements:
        raise Unconfirmed("No optical elements in the Project.")
    poses = {c["instance_id"]: c["nominal_pose"] for c in payload["components"]}
    start = poses[lowered.elements[0].instance_id]
    origin, direction = tuple(start["position_mm"]), _axis(start)
    if direction is None:
        raise Unconfirmed("The optical axis could not be resolved.")

    planes = []
    for element in lowered.elements:
        z = axial_position(poses[element.instance_id], origin, direction)
        for member in element.members or (element,):
            member_z = z
            if member.member_pose is not None:
                member_z += axial_position(member.member_pose.model_dump(mode="json"), (0, 0, 0), (0, 0, 1))
            planes.extend(element_planes(member, member_z))
    planes.sort(key=lambda plane: plane.z)
    return planes, origin, direction


def element_planes(element: Any, z: float) -> list[Plane]:
    from os_optics.contracts.materials import AxialGradientIndexMaterial, GradientIndexMaterial, UniaxialMaterial
    from os_optics.local.compile import _media

    name = element.member_id or element.instance_id
    model = element.model
    if model.model_kind == "APERTURE_STOP":
        if (model.opening_radius_mm is None or model.edge_radius_mm is None
                or model.opening_shape not in (None, "CIRCLE", "circle")
                or any(float(v) != 0 for v in model.opening_center_mm or ())
                or float(model.obstruction_radius_mm or 0) != 0 or model.sample is not None):
            raise Unconfirmed(f"{name}: expected a centered circular stop with a clear opening.")
        opening = float(model.opening_radius_mm)
        return ([Plane(z + float(model.plane_z_mm), name, opening)]
                if float(model.edge_radius_mm) > opening else [])
    if model.model_kind != "SURFACE_SEQUENCE":
        raise Unconfirmed(f"{name}: unsupported optical model {model.model_kind}.")
    if any(isinstance(m, (AxialGradientIndexMaterial, GradientIndexMaterial, UniaxialMaterial))
           for m in element.materials):
        raise Unconfirmed(f"{name}: gradient-index and birefringent elements are outside this calculation.")

    planes = []
    for i, surface in enumerate(model.surfaces):
        label = f"{name}/{surface.surface_id}"
        if (surface.traced != "TRANSMITTED" or surface.is_freeform or surface.is_axicon
                or surface.is_cylindrical or surface.has_section_powers):
            raise Unconfirmed(f"{label}: expected a rotationally symmetric transmitting surface.")
        if (surface.clear_radius_mm is None or surface.clear_shape not in (None, "CIRCLE", "circle")
                or any(float(v) != 0 for v in surface.aperture_center_mm or ()) or surface.holes):
            raise Unconfirmed(f"{label}: expected a centered circular clear aperture without holes.")
        before, after = _media(model, i)
        planes.append(Plane(
            z + float(surface.vertex_z_mm), label, float(surface.clear_radius_mm),
            0.0 if surface.radius_mm is None else 1.0 / float(surface.radius_mm),
            element.engine_material_id(before), element.engine_material_id(after),
        ))
    return planes


def image_position(payload: dict, origin: tuple, direction: tuple) -> float:
    observations = payload.get("observations", [])
    if len(observations) != 1:
        raise Unconfirmed("Expected one native image observation.")
    observation = observations[0]
    if (observation.get("medium") or "air").lower() != "air":
        raise Unconfirmed("Expected an image observation in the surrounding medium.")
    pose = _observation_pose(payload, observation)
    if pose is None:
        raise Unconfirmed("The native image observation pose could not be resolved.")
    return axial_position(pose, origin, direction)


def object_position(sources: list[tuple[float, dict]], wavelength: float) -> float:
    """For a finite object, the configured Gaussian waist supplies the native object plane."""
    positions = []
    for z, model in sources:
        wavelengths = [line["wavelength_nm"] for line in (model.get("spectral_lines") or ())]
        if not wavelengths:
            wavelengths = [model.get("wavelength_nm")]
        if wavelength not in wavelengths:
            continue
        if model.get("model_kind") != "GAUSSIAN_BEAM" or not is_number(model.get("waist_position_mm")):
            raise Unconfirmed("Expected a native Gaussian source waist for the finite object plane.")
        positions.append(z + model["waist_position_mm"])
    if not positions or max(positions) - min(positions) > AXIS_TOLERANCE_MM:
        raise Unconfirmed("Expected one object plane at the requested wavelength.")
    return positions[0]


def trace_aperture(planes: list[Plane], indices: dict[str, float], object_z: float | None) -> tuple[float, Plane, float]:
    """Propagate the normalized paraxial ray (height, n·angle) through every aperture."""
    medium = "air"
    z = planes[0].z if object_z is None else object_z
    height, angle = (1.0, 0.0) if object_z is None else (0.0, 1.0)
    radius, limiting = math.inf, planes[0]
    for plane in planes:
        height += (plane.z - z) * angle / indices[medium]
        z = plane.z
        if abs(height) > 1e-12:
            admitted = plane.radius / abs(height)
            if admitted < radius:
                radius, limiting = admitted, plane
        if plane.after is not None:
            if plane.before != medium:
                raise Unconfirmed(f"{plane.label}: the optical media do not form one sequential path.")
            angle -= height * (indices[plane.after] - indices[medium]) * plane.curvature
            medium = plane.after
    if (medium != "air" or not math.isfinite(radius) or radius <= 0 or not math.isfinite(angle)
            or abs(angle) < 1e-15 or not math.isfinite(height) or height * angle > 0):
        raise Unconfirmed("The path does not establish a finite admitted cone with a downstream paraxial image.")
    return radius, limiting, angle


def calculate(project: Any, payload: dict, conjugate: str, wavelengths: list[float]) -> dict:
    """Report verified fact candidates or why this configuration remains unconfirmed."""
    from os_optics.config import DEFAULT_NUMERICAL_CONFIG
    from os_optics.local.errors import LocalRunError
    from os_optics.local.lowering import lower_project
    from os_optics.optics.materials.index import build_evaluator

    name = CONJUGATE_FACT.get(conjugate)
    if name is None or not wavelengths:
        return {"state": "UNCONFIRMED", "reason": "Specify a supported imaging conjugate and native wavelength."}
    try:
        lowered = lower_project(project, check_solids=False, inspect_solids=False)
        planes, origin, direction = sequence_planes(lowered, payload)
        if not planes or image_position(payload, origin, direction) < planes[-1].z - AXIS_TOLERANCE_MM:
            raise Unconfirmed("The native image observation must follow the optical train.")
        sources = axial_sources(payload, origin, direction, planes[0].z)
        materials = {m.material_id: m for m in lowered.request.project.materials}
        needed = {"air"} | {p.after for p in planes if p.after is not None}
        if needed - materials.keys() - {"vacuum"}:
            raise Unconfirmed("The optical path contains an unresolved material.")
        evaluators = {key: build_evaluator(materials[key], DEFAULT_NUMERICAL_CONFIG) for key in needed - {"vacuum"}}
    except (Unconfirmed, LocalRunError) as exc:
        return {"state": "UNCONFIRMED", "reason": str(exc)}

    samples, unconfirmed = [], []
    for wavelength in wavelengths:
        try:
            indices = {"vacuum": 1.0}
            for key, evaluator in evaluators.items():
                value, issue = evaluator.index(wavelength)
                if value is None or not math.isfinite(value) or value <= 0:
                    raise Unconfirmed(issue.message if issue else f"No material index for {key}.")
                indices[key] = value
            object_z = object_position(sources, wavelength) if name == PARAXIAL_WORKING_F_NUMBER else None
            if object_z is not None and object_z >= planes[0].z:
                raise Unconfirmed("The finite object plane must be before the optical train.")
            radius, limiting, angle = trace_aperture(planes, indices, object_z)
            cone = 2.0 * radius * abs(angle)
            if not math.isfinite(cone) or cone <= 0:
                raise Unconfirmed("The admitted cone has no finite positive f-number.")
            conditions = {"method": AXIAL_PARAXIAL_METHOD, "convention": PARAXIAL_F_NUMBER_CONVENTIONS[name],
                          "conjugate": conjugate, "field": "on_axis", "wavelength_nm": wavelength}
            if object_z is None:
                # The infinite-conjugate ray starts with unit height and zero angle.
                # Its effective focal length is -n_image / reduced_angle.
                value = indices["air"] / cone
                definition = "Magnitude of effective focal length divided by the admitted axial entrance pupil diameter."
                diameter = 2.0 * radius
                if not math.isfinite(diameter):
                    raise Unconfirmed("The admitted entrance pupil diameter is not finite.")
                extra = {"entrance_pupil_diameter_mm": diameter}
            else:
                # The ray starts at the native object plane. Scaling its reduced angle to
                # the admitted marginal ray gives n_image times the paraxial image angle.
                value = 1.0 / cone
                conditions["object_distance_mm"] = next(p.z for p in planes if p.after is not None) - object_z
                definition = "Reciprocal of twice the admitted axial marginal ray's reduced image angle."
                extra = {}
            if not math.isfinite(value) or value <= 0:
                raise Unconfirmed("The admitted cone has no finite positive f-number.")
            samples.append({"fact": name, "data": {"value": value, "basis": "PROJECT_DERIVED", "conditions": conditions,
                                                  "definition": definition},
                            "limiting_aperture": limiting.label, **extra})
        except Unconfirmed as exc:
            unconfirmed.append({"wavelength_nm": wavelength, "reason": str(exc)})
    return {"state": "CONFIRMED" if samples else "UNCONFIRMED", "samples": samples, "unconfirmed": unconfirmed}
