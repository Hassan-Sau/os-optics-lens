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
| `record_hash` | SHA-256 over the record with `record_hash` removed, so a consumer can detect an edited record. |
| `collection.source_revision` | The pinned upstream commit. A record is only comparable with another record of the same revision. |
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
  Edlén 1953 air model, the model the engine names. `sampling_wavelengths_air_nm` keeps the
  source's own numbers so the conversion stays checkable.
- `primary_wavelength_nm` — the source's primary wavelength (Zemax `PWAV`), vacuum.
- `operating_range_nm` — a **numeric interval for filtering only**. Its `basis` says what it is:
  `SPAN_OF_STATED_SAMPLING_WAVELENGTHS` when the source enables several wavelengths and states no
  separate range, or `SINGLE_WAVELENGTH_BAND` when it enables one and the interval is a 1 nm
  numerical band. A set of enabled wavelengths is sampling evidence, not a claimed operating range.
- `band_facets` — `visible`, `near_infrared`, `ultraviolet`, `extreme_ultraviolet`,
  `mid_wave_infrared`, `long_wave_infrared`, from the documented boundaries in
  `band_boundaries` of the collection README. A facet is discovery; the numeric interval decides
  coverage.

## First-order properties

- `effective_focal_length_mm` — signed, in air, at `conditions.wavelength_nm`.
- `back_focal_length_mm` — from the last surface vertex to the paraxial image point, positive
  downstream.
- `total_track_mm` — first surface vertex to the image plane along the axis.
- `engine_check` — the same two quantities recomputed from the committed Project by the engine's
  thick-lens paraxial matrix, with `efl_relative_difference`. This is the optical verification of
  the record, separate from conversion and from opening the Project.

## Aperture

`f_number` and `numerical_aperture` are different quantities and never share a field. An
image-space design records `f_number` (image-space f-number as the source states it); an
object-space design records `numerical_aperture`. A record with neither leaves both out.

## Field

`field.kind` decides the meaning:

| `kind` | Fields | Meaning |
|---|---|---|
| `ANGULAR` | `full_field_deg`, `half_field_deg`, `field_points_deg` | Field angles. The full field is twice the largest half field. |
| `OBJECT_HEIGHT` | `max_object_height_mm`, `field_points_mm` | Object-space field size in millimetres, not an angle. |

The two are not interchangeable and are never converted into each other by the import.

## Materials

`materials.model_glasses` holds every glass defined from the source's own per-surface index table
in the upstream prescription dump: a 3-term Sellmeier with fixed poles solved to those samples
(`basis` records the poles, the samples and the residual), or a constant index when the source
states a single wavelength. A model glass always names its dispersion model and parameters;
`nd`/`Vd` alone do not define a curve.

`materials.catalog_comparisons` records where a published catalog glass of the same name exists,
with the largest index difference. The catalog glass is **compared, never substituted**: the
record keeps the source's own indices.

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