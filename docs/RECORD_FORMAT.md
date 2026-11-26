# Record layout and field semantics

This document defines the record contract and describes the existing seed layout.
[ARCHITECTURE.md](../ARCHITECTURE.md) defines retrieval behavior. Field names, units and bases are
part of the record contract. Use a new `record_schema_version` when changing their meaning.

## What retrieval uses

The index uses facts about the committed `os-optics` Project. These include facts declared in the
Project, quantities derived from it, and results calculated for it under identifiable conditions.
For each numerical search fact, retain the configuration, unit and conditions needed to compare it.
Contributor-supplied facets such as intended application or design family can aid discovery.

Keep upstream optical values, source comparisons, conversion notes and intake verdicts out of
field discovery, filters, matching, rankings and routine responses. Apply this rule when returning
whole sections as well as individual facts. A source check may be retained for contributors or
made available through explicit inspection. A missing Project value leaves only the requested
constraint unconfirmed. Existing records can retain their layout and richer review metadata. Read
only the eligible Project facts into the search index.

## One directory per record

```
records/lenslibrary/
├── batch-lenslibrary-seed-1.json          batch outcome manifest (one row per source input)
└── lenslibrary-528155/
    ├── project.json                       the native os-optics Project (authoritative)
    └── record.json                        compact search facts and provenance
```

`project.json` is the prescription. `record.json` carries the compact search facts and direct
provenance. An optional supporting extract can accompany a fact when it is needed to interpret a
result for the Project. Generate the index from the independently maintained records.

The batch outcome manifest shown above is part of the existing seed intake history. For new
batches, keep routine intake reports, transcription comparisons, raw exports and preparation
artifacts upstream or with the contribution. Keep required license notices with the collection.

The [camera evidence extension](CAMERA_SEARCH_EVIDENCE.md) uses this shared
format for native camera designs and provides an executable acceptance case.
Camera records may carry verified real image heights, geometric back-focus
endpoints, field-interval MTF, radiometry and sourced analysis evidence.

## Record identity

| Field | Meaning |
|---|---|
| `record_id` | Stable design ID. The seed uses `lenslibrary-<source stem>` in lower case. A re-import of the same input keeps the identity. |
| `record_revision` | Integer, starts at 1. Increase it when the Project or a record fact changes. |
| `record_hash` | SHA-256 over the parsed record with `record_hash` and `record_hash_method` removed. Serialize with `json.dumps(body, sort_keys=True, ensure_ascii=False)` as UTF-8 with no trailing newline. |
| `record_hash_method` | The serialization above in prose. |
| `native_project.sha256` | SHA-256 of the committed native Project bytes. Normalize checkout line endings to the repository's LF form when recomputing from a Windows worktree. |

## Direct provenance

Use the contributor's account of the input used to make the Project. A library conversion needs
that library, the input identifier, its revision or edition when available, and applicable
attribution and redistribution terms. For a direct patent transcription, identify the publication
and example. For an original submission, name the contributor and the terms of the contribution.
These details are available on explicit request. The source's own references can stay upstream.

Existing fields such as `collection.source_revision`, `collection.source_input_sha256`,
`collection.source_links`, `collection.original_publication` and `design.source_reference` can be
read for provenance or maintenance. They are outside the search facts. A source identifier or
checksum identifies an input and does not determine optical comparability.

`design.design_family_id` groups meaningful variants: `1998704a`/`b` and `7301707`/`7301707-spherical`
are one family, and separate records. Family membership is a facet, not a merge.

## Value bases

Record the basis needed to interpret the value. Use the native value and convention for a
Project declaration such as a geometric aperture. The existing record labels identify other
common bases.

| Basis | Meaning |
|---|---|
| `DERIVED` | Computed from other values. The derivation must use the committed Project or results for it for the output to be a search fact. |
| `ENGINE_COMPUTED` | Produced by `os-optics` for the committed Project. |
| `SOURCE_STATED` | Written in the direct source and retained as provenance or transcription evidence. A source label may inform a discovery facet. |

An existing fact's label alone may not establish its basis. For example, a legacy `DERIVED` value
can come from the source's printed numbers. Establish the underlying Project basis before mapping
a legacy fact into search. Leave out unavailable facts or use `null` where the layout calls for it.

For a Project analysis, retain the required conditions and any compact supporting result needed to
interpret it. Source targets and side-by-side numerical comparisons belong to contribution review.

## Spectrum

- `sampling_wavelengths_nm` — wavelengths configured or evaluated for the Project, in vacuum
  nanometres. The seed uses the engine's air model to convert its original air wavelengths.
  Its `sampling_wavelengths_air_nm` entries are retained for intake review.
- `primary_wavelength_nm` — the primary wavelength used by the Project, in vacuum nanometres.
- `wavelength_precision` — states that these are computational values at full precision, so a
  reviewer may pass them to the engine unchanged; rounding in this document or in prose is for
  display only.
- `sampling_span_nm` — the numeric span of the sampling wavelengths, **eligible for discovery only**.
  It is not a coverage claim and not an operating range. Two `basis` values occur:
  - `SPAN_OF_STATED_SAMPLING_WAVELENGTHS` — the min and max of several enabled wavelengths. The span
    is a summary of the samples; the samples themselves are `sampling_wavelengths_nm`.
  - `SINGLE_WAVELENGTH_BAND` — **ten records** enable exactly one wavelength. A zero-width interval
    cannot be filtered or evaluated, so the span is a **±0.5 nm window around that one sample**
    (1 nm wide). It is a numerical convenience, not a second wavelength: `sampling_wavelengths_nm`
    still holds exactly one value, and the window must never be read as two observed samples or as
    a measured band. Only `sampling_wavelengths_nm` is observed.
- `continuous_coverage_nm` — **the only interval that can satisfy a hard band constraint.** Its
  `state` is `UNCONFIRMED` with null bounds until there is evidence for the range on the Project.
  A hard coverage constraint remains unconfirmed when the record supplies only discrete samples or
  a sampling span.
- `band_facets` — `visible`, `near_infrared`, `ultraviolet`, `extreme_ultraviolet`,
  `mid_wave_infrared`, `long_wave_infrared`, from the documented boundaries in the collection
  README. A facet is a discovery label derived from the sampling span; it decides nothing about
  coverage.

## First-order properties

- `effective_focal_length_mm` — signed, computed for the Project at the stated wavelength and
  ambient medium.
- `back_focal_length_mm` — the Project's paraxial distance from the last optical surface vertex to
  the rear focal point, positive downstream. A geometric vertex-to-sensor distance is a separate
  fact with its own endpoints.
- `total_track_mm` — geometric distance from the first surface vertex to the Project's image plane
  along the stated axis or path.

For the existing LensLibrary records, take the Project's EFL and BFL from the engine values in
`first_order.engine_check` and expose them under the regular search keys with the stored wavelength.
If there is no Project-derived track, compute it from the Project or omit it. Keep the source
values and `engine_check.comparison` available only as intake details.

### LensLibrary transcription check

The seed intake compared the Project to upstream first-order values using the rule below. This
is the historical check for that batch. Search uses the Project values regardless of the check.

```
per quantity:  |engine − source| ≤ atol + rtol · scale
atol = 1e-5 mm,  rtol = 1e-4
scale = |EFL|               for the effective focal length
scale = max(|BFL|, |EFL|)   for the back focal length
```

Each quantity carries its own `scale_mm` and `scale_basis` in `comparison`, so the rule stated here
is the rule that was applied.

`comparison` records the rule, both values, the absolute difference, the tolerance and
`fraction_of_tolerance` for each quantity, so a reviewer recomputes the verdict instead of trusting
it. The tightest record in the seed batch uses 0.43 % of its allowance (`1792917`, EFL), so the rule
is not tuned to pass.

`validation.paraxial` is `MATCHED` only when both quantities are within tolerance.

## Aperture

Keep each aperture convention distinct. Examples include image-space f-number, entrance pupil
diameter, object-side numerical aperture and paraxial working f-number. Use aperture values the
current Project declares or supports under the recorded conditions. Mark the declared system
aperture where applicable. The mappings below describe how the existing seed records preserve
source aperture information for intake. Use a legacy source aperture as a search value only when
the corresponding value and convention are established for the Project.

### The `FNUM` type mapping

A ZMX `FNUM` line carries a type flag in its second field, and the flag — not a numerical
coincidence with another convention — decides which f-number the value is:

| `FNUM` flag | Convention | Field stored | Records |
|---|---|---|---|
| `0` | Image Space F/# | `f_number` | 19 |
| `1` | Paraxial Working F/# | `paraxial_working_f_number` | `6744570a/b/c` |

The mapping is verified against the upstream dump's declared `System Aperture`, which agrees with
the flag on every record.

### System-aperture fields

| Field | Meaning |
|---|---|
| `f_number` | Image-space f-number, from `FNUM` with flag 0. |
| `paraxial_working_f_number` | Paraxial working f-number, from `FNUM` with flag 1. |
| `entrance_pupil_diameter_mm` | From the design file's `ENPD`. |
| `object_numerical_aperture` | From the design file's `OBNA`. An NA is not an f-number. |

`why_not_design_file` is the marker for a system-aperture value that comes from the dump because the
design file states no aperture at all (`FNUM`, `ENPD` and `OBNA` all absent). **No record in the seed
batch takes that route**: every one of the 39 states its aperture in the design file, so the field is
documented here for the contract's sake and does not occur in the data. The property list is kept as
`property_list_comparison` only. A record with no stated aperture leaves every system-aperture field
out rather than inferring one.

### Dump-derived f-number facts

The dump prints several f-number conventions side by side. Each is kept as its own fact with
`system_aperture: false` and a `source_locator` naming where it came from, and is **never** merged
into the system-aperture value:

| Field | Meaning |
|---|---|
| `image_space_f_number` | The dump's stated image-space F/#. |
| `paraxial_working_f_number_from_dump` | The dump's stated paraxial working F/#. |
| `working_f_number` | The dump's stated working F/#, computed by tracing rays. |

### Stop validity: `design.aperture_validity`

A record's eligibility for stop-dependent evaluation is machine-readable, not prose:

| Field | Meaning |
|---|---|
| `state` | `STOP_BLOCKING`, `STOP_NOT_BLOCKING` or `NO_STOP`. |
| `stop_blocks_light` | Whether the Project's stop plate actually blocks light outside its opening. |
| `basis` | Why the state holds. |
| `consequence` | What the state means for the record, in prose. |
| `eligible_for_stop_dependent_evaluation` | Whether the record may be evaluated at all against a stop-dependent constraint. |
| `satisfies_stop_dependent_constraints` | Existing intake summary of whether the record carries evidence for stop-dependent matches. |
| `satisfaction_basis` | Explanation of that intake summary. |

A blocking plate makes a Project eligible for analyses that require a physical stop. A match
requires the result appropriate to the requested metric, such as a pupil sample or an illumination
calculation. Evaluate each supported fact on its own conditions. An unmeasured field result does
not affect a query for the Project's stop opening or focal length. The seed reports zero confirmed
stop-dependent matches in its intake metadata. Its `7821720c` Project has a nonblocking stop and
is useful as a first-order geometry reference.

## Field

Index the field conditions configured or evaluated for the native Project. Preserve the distinct
meanings below. The seed records also retain the original field type and points for intake review.
They come from the ZMX `FTYP` and `YFLN` fields, where `0` means angle, `1` object height, `2`
paraxial image height and `3` real image height.

| `kind` | Fields | Meaning |
|---|---|---|
| `ANGULAR` | `full_field_deg`, `half_field_deg`, `field_points_deg` | Field angles. The full field is twice the largest stated half field. |
| `OBJECT_HEIGHT` | `max_object_height_mm`, `field_points_mm` | Object-space field size in millimetres, not an angle. |
| `IMAGE_HEIGHT` | `max_image_height_mm`, `image_height_kind`, `field_points_mm` | Image-space field size. An image quantity: neither an object-space field nor an angle. |

The three are not interchangeable and the import never converts one into another.

Two checks sit beside the value and are **not** values:

- `prescription_dump_check` — the upstream dump prints the same field table. `MATCHES` when it
  agrees, otherwise `FIELD_TABLE_DIFFERS` with both numbers. Across this batch it is `MATCHES` for
  all 39 accepted records.
- `property_list_comparison` — the collection's `lens_properties_list.txt` is a hand-maintained
  summary whose field convention is **not consistent across rows**: an angle-typed row may give the
  full field (`528155`: 53.2) or a half field (`5852515a`: 4.0), and two angle-typed rows carry an
  object height instead (`6016226`: 1.673, `Kidger2004`: 0.315). It is therefore never used as a
  field value and never described as a source disagreement.

A missing value is left out. An unknown field leaves the field constraint unconfirmed.

## Materials

`materials.model_glasses` holds every glass defined from the source's own per-surface index table
in the upstream prescription dump: a 3-term Sellmeier with fixed poles solved to those samples
(`basis` records the poles, the samples and the residual), or a constant index when the source
states a single wavelength. A model glass always names its dispersion model and parameters;
`nd`/`Vd` alone do not define a curve.

`materials.catalog_comparisons` records where a published catalog glass of the same name exists,
with the largest index difference. The catalog glass is **compared, never substituted**: the
record keeps the source's own indices.

A continuous law is only fitted to samples that can come from one glass. A solid glass in the
visible/near-infrared has normal dispersion — its index falls as the wavelength rises — so samples
that rise or are not monotonic cannot support a fit: interpolating between them would invent a
material. Such an input is deferred (`MATERIAL_MODEL_FAILED`) instead of being modelled.
`lenslibrary-895045b` is that case: its surface 1 states 1.7517, 1.6042, 1.7338 at 486, 588 and
656 nm.

## Approximations and unsupported constructs

`approximations` lists every modelling decision that changes the optics or its interpretation,
with a stable `code`. `unsupported_constructs` lists what the source contains and this record does
not represent. An accepted record has no construct in that list that affects the design.

## Validation states

`validation` tracks four independent outcomes:

| Key | Values |
|---|---|
| `conversion` | `PASSED` / `REFUSED` |
| `project_check` | `ACCEPTED` / `REFUSED` |
| `optical_solids` | `VALID` / `INVALID` |
| `paraxial` | `MATCHED` / `DIFFERS` / `NOT_CHECKED` |

`validation.paraxial` describes the optional source comparison in the seed layout. `MATCHED`
means the Project reproduces the comparable source quantities under the stated intake rule.
Keep the comparison verdict separate from successful opening, applicable geometry checks and
support for each searchable Project fact. A source comparison is useful for spotting transcription
errors. Resolve any issue it reveals with the Project or its advertised facts during intake.

Keep detailed checks and source discrepancies with the contribution. Routine retrieval reports
confidence in the requested Project facts through their conditions and match states.

## Batch manifest

`batch-lenslibrary-seed-1.json` reports an outcome for **every** input:

| `outcome` | Meaning |
|---|---|
| `ACCEPTED` | A committed record exists; `record_id` names it. |
| `DEFERRED` | Deliberately not converted, with `reason_code` naming the construct or the missing source data. |
| `CONVERSION_FAILED` | The engine refused the surface table, with the engine's own problems attached. |

`counts` and `accepted_record_ids` are generated from the rows, so the manifest cannot drift from
the records.