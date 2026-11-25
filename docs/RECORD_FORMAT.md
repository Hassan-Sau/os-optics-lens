# Record layout and field semantics

This document fixes the layout the first collection uses and states what every indexed value
means. [ARCHITECTURE.md](../ARCHITECTURE.md) sets the design; this file is the implementation of
it for the seed batch. Field names, units and bases are part of the record contract: change them
only with a new `record_schema_version`.

## One directory per record

```
records/lenslibrary/
├── batch-lenslibrary-seed-1.json          batch outcome manifest (one row per source input)
└── lenslibrary-528155/
    ├── project.json                       the native os-optics Project (authoritative)
    └── record.json                        compact search facts and provenance
```

`project.json` is the prescription. Everything else is discovery, comparison and evidence. A
record is independently maintainable: its directory holds no shared state, and the index is
generated from these files rather than stored beside them.

Raw ZMX files, intermediate CSV surface tables, patent PDFs and layout images stay upstream or in
a scratch workspace. They are cited by path and SHA-256, never committed.

## Record identity

| Field | Meaning |
|---|---|
| `record_id` | `lenslibrary-<source stem>`, lower-cased. Derived from the upstream file name, so a re-import of the same input keeps the identity. |
| `record_revision` | Integer, starts at 1. Bumped when the Project or a stated fact changes for the same source input. |
| `record_hash` | SHA-256 over the record with `record_hash` and `record_hash_method` removed, so a consumer can detect an edited record. Recompute it from the **parsed JSON**, not the file's bytes: `json.dumps(body, sort_keys=True, ensure_ascii=False)` encoded as UTF-8, no trailing newline. The method is stated in the record itself. |
| `record_hash_method` | The serialization above, in prose, so the hash is reproducible without reading this document. |
| `collection.source_revision` | The pinned upstream commit. A record is only comparable with another record of the same revision. |
| `collection.source_input_sha256` | SHA-256 of the file's bytes **as the pinned revision stores them**, taken from the git blob, so a Windows CRLF checkout does not change it. |
| `collection.source_links.source_file_url` | The upstream ZMX at the pinned revision, so a reviewer reads the exact input. |
| `collection.original_publication` | The patent publication the source bundles with the design, when it does. `null` when the source gives none. |
| `design.source_reference` | The upstream's own short reference (`Goerz1894`, `Kidney2004`, …), preserved verbatim. |

`design.design_family_id` groups meaningful variants: `1998704a`/`b` and `7301707`/`7301707-spherical`
are one family, and separate records. Family membership is a facet, not a merge.

## Value bases

Every quantity carries a `basis`. The vocabulary is fixed:

| Basis | Meaning |
|---|---|
| `SOURCE_STATED` | Written in the upstream source: the ZMX file, the upstream prescription dump, or the LensLibrary property list. |
| `DERIVED` | Computed from source values by the import (for example a band from sampling wavelengths, or a half field from a full field). |
| `ENGINE_COMPUTED` | Produced by `os-optics` from the committed Project. |

A missing value is `null` with the field left out, never a guess. An unknown value leaves the
corresponding constraint unconfirmed.

## Spectrum

- `sampling_wavelengths_nm` — the wavelengths the source enables, as **vacuum** nanometres. The
  upstream files state air wavelengths at 20 °C and 101325 Pa; each was converted once with the
  **engine's own** air model (`material_physics.air_index_exact`, the 6432.8 / 2949810 / 25540
  form), so a record's vacuum wavelength is the wavelength the engine evaluates.
  `sampling_wavelengths_air_nm` keeps the source's own numbers so the conversion stays checkable.
  Using a different air model (Edlén 1953, the 8342.13 form) shifts the value by about 0.003 nm and
  is wrong here.
- `primary_wavelength_nm` — the source's primary wavelength (Zemax `PWAV`), vacuum.
- `sampling_span_nm` — the **numeric span of the sampling wavelengths, eligible for discovery
  only**. A set of enabled wavelengths is evidence of what the source samples; it is not a claimed
  operating range.
- `continuous_coverage_nm` — `state: UNCONFIRMED` with null bounds unless the source states a range
  independently. Nothing in this collection does, so no record claims continuous coverage.
- `band_facets` — `visible`, `near_infrared`, `ultraviolet`, `extreme_ultraviolet`,
  `mid_wave_infrared`, `long_wave_infrared`, from the documented boundaries in the collection
  README. A facet is discovery; the numeric interval decides coverage.

## First-order properties

- `effective_focal_length_mm` — signed, in air, at `conditions.wavelength_nm`.
- `back_focal_length_mm` — from the last surface vertex to the paraxial image point, positive
  downstream.
- `total_track_mm` — first surface vertex to the image plane along the axis.
- `engine_check` — the same two quantities recomputed from the committed Project by the engine's
  thick-lens paraxial matrix, plus `comparison`. This is the optical verification of the record,
  separate from conversion and from opening the Project.

### The paraxial comparison rule

A back focal length can pass through zero, so a tolerance relative to BFL alone is meaningless
there: `lenslibrary-4037934a` has a BFL of −0.0059 mm, and a 1 × 10⁻⁴ relative rule would demand
6 × 10⁻⁷ mm agreement. The scale of a first-order comparison is the system's focal length, but a
long back focus behind a short focal length needs its own length too. The rule is therefore:

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

An f-number, an entrance pupil diameter, an object-side numerical aperture and a paraxial working
f-number are different quantities with different conditions. Each is recorded as its own field and
none is derived from another:

| Field | Meaning |
|---|---|
| `f_number` | Image-space f-number. From the design file's `FNUM`, else the dump's stated value. |
| `entrance_pupil_diameter_mm` | From the design file's `ENPD`. |
| `object_numerical_aperture` | From the design file's `OBNA`. An NA is not an f-number. |

`why_not_design_file` appears on a value that comes from the dump because the design file states no
aperture at all. The property list is kept as `property_list_comparison` only.

A record with no stated aperture leaves all three out rather than inferring one.

## Field

The **design file is authoritative**: the ZMX states the field type in `FTYP` and the field points
in `YFLN`. `FTYP`'s first code maps to the kind — `0` angle, `1` object height, `2` paraxial image
height, `3` real image height — and the record keeps that kind:

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

A record is accepted only when all four hold. `MATCHED` means the engine's paraxial EFL and BFL
reproduce the source-stated values within the tolerance stated in the import notes.

## Batch manifest

`batch-lenslibrary-seed-1.json` reports an outcome for **every** input:

| `outcome` | Meaning |
|---|---|
| `ACCEPTED` | A committed record exists; `record_id` names it. |
| `DEFERRED` | Deliberately not converted, with `reason_code` naming the construct or the missing source data. |
| `CONVERSION_FAILED` | The engine refused the surface table, with the engine's own problems attached. |

`counts` and `accepted_record_ids` are generated from the rows, so the manifest cannot drift from
the records.