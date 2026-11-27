# The Nikon FX expansion series

This note records how the Nikon FX records were prepared, so a reviewer can repeat the work and
check every claim. It covers the scope the series took from
[issue #11](https://github.com/JunLin615/os-optics-lens/issues/11), the two sources it uses, the
conversion method, the acceptance rule actually applied, and the limits a consumer should read
before using a record.

- **Engine:** public `os-optics` **0.14.0**, catalog release **2026-11-25.1**
- **Format:** `csv-surface-table/1`, the only prescription format `0.14.0` reads
- **Batches:** `records/nikon-fx/batch-nikon-fx-1.json` (patent transcription) and
  `records/nikon-fx/batch-nikon-fx-2.json` (corpus prescriptions)

## Scope

The series targets Nikon-branded **FX photography lenses** across F and Z mounts and across
product generations. It includes primes and individual positions of zoom lenses. Each native
Project represents one optical position. Afocal attachments and reflecting designs are outside
the batch scope.

## Two sources, two kinds of claim

| Batch | Direct source | Model and check |
|---|---|---|
| `nikon-fx-1` | A numerical example printed in a United States patent publication | The surface table is transcribed from the example, scaled to 28 mm and modeled with catalog glass approximations. The Engine agrees with the scaled source EFL and back focal distance within the recorded tolerance. |
| `nikon-fx-2` | The FlareSim lens corpus at revision `0e28ead9` | Each source surface table supplies a prescription for the model. The Engine agrees with the focal length the corpus file states within the recorded tolerance. [Pinned corpus](https://github.com/LocalStarlight/flaresim_nuke/tree/0e28ead9a3ec4898c7568f27b1ce8c0de6df7a08) |

The FlareSim corpus carries an MIT license. The records keep the source file's patent citation
in `collection.original_publication` when available. The patent transcription record
`nikon-fx-us4099850a-ex1` cites the publication as its direct source. [FlareSim MIT notice](../licenses/FlareSim-MIT.txt)

## Inventory

The pinned corpus revision holds **1370 `.lens` files**. **246** are Nikon-branded. Selection is by
the corpus file's own name, with these exclusions:

| Excluded | Why |
|---|---|
| `DX`, `IX`, 1-series | not FX, and a DX design does not cover the format the series models |
| cinema, TV, `Cine` | different mount, different coverage, and the corpus names them separately |
| `Reflex`, `mirror` | a reflecting surface the sequential import cannot carry |
| `TC`, `teleconverter`, FCL attachments | afocal: no focal length and no f-number of their own |
| repro, industrial, medical, measuring, stereoscopic | not photography |

The batch 2 manifest accounts for **202 distinct source paths**. The prior 205 rows included three
repeated paths. Two repeated paths had duplicate Projects under alternate IDs and one had a repeated
deferral. The two distinct 85 mm source paths produced byte-identical Projects, so the alias stays
in the manifest with a reference to the retained record.

| Outcome | Count |
|---|---|
| Accepted records | 101 |
| Deferred, with a reason code | 100 |
| Conversion failed (the Engine refused the table) | 1 |

With the patent example, the series contains **102 Projects**.

## Conversion method

The conversion is source-specific preparation and lives in a scratch workspace outside this
checkout: a `.lens` reader, a glass matcher, an aperture synthesiser and a Project builder. Only
the native Projects and their metadata are committed.

Per file:

1. **Read the file.** The corpus prints, per surface, the radius, the axial thickness, the
   refractive index, the Abbe number, the element outline diameter and a coating column, plus one
   stop plane. A row with no index is air. A zero-radius row is a plane.
2. **Approximate the glass.** The corpus gives `nd` and `vd`. The Project uses the named glass
   from the published catalog that minimizes `|Δnd| / 0.001 + |Δvd| / 0.5` and uses its catalog
   dispersion curve as a substitute for the source glass. The record keeps both sets of values
   and their differences.
3. **Derive the apertures.** The corpus states one outline per element and no clear aperture. The
   stop is sized so the entrance pupil gives the product's f-number; each element's clear aperture
   is the smaller of the unvignetted envelope for the axial marginal ray plus the chief ray of the
   modelled field, and the radius at which the steepest surface of that element has a sag of half
   the adjacent glass thickness. Two neighbouring outlines that overlap where the air gap is narrow
   are edged down in 10 per cent steps until the bodies clear, and every reduction is recorded in
   `approximations`.
4. **Choose modeled field samples.** The angle subtended by the nominal FX diagonal (43.27 mm) at
   the design focal length supplies the modeled field. The calculation uses `atan(h/f)` for
   rectilinear designs or `h/f` in radians for an equidistant projection. The format provides an
   input to the estimate. Actual geometric coverage remains unconfirmed.
5. **Place the image plane at the paraxial focus.** The corpus prints a finite-conjugate spacing,
   and a collimated beam focuses elsewhere: for `AI Nikkor 180mm f/2.8 ED` the file's last
   thickness lands the image 30 mm short of the focus. The plane is therefore the exit vertex plus
   the Engine's paraxial back focal distance.
6. **Aim each field's chief ray at the stop.** A field angle is defined by the ray that crosses the
   stop's centre. A collimated beam aimed at the *paraxial* entrance pupil does not do that in a
   retrofocus wide angle, where pupil aberration is large: the beam crosses the stop off centre and
   the image height reads as tens of per cent of distortion the lens does not have. So each beam is
   traced, its crossing offset at the stop is measured, a 1 mm probe shift gives the response gain
   for that field, and the beam is shifted by `-offset / gain`. The committed Project carries the
   aim, so a reviewer traces the same rays.
7. **Import and check.** The surface table is imported as `csv-surface-table/1`, the Project is
   checked, the optical solids are inspected, and the paraxial focal length is computed from the
   committed Project.
8. **Verify the field.** Every declared field is traced at F, d and C; each field's image height is
   the mean of its chief-ray arrivals, and the difference from `EFL · tan θ` is the distortion the
   record reports.

## The acceptance rule

A candidate becomes a record only when all four hold:

| Gate | Rule |
|---|---|
| Paraxial | the engine's focal length is within `atol + rtol · f` of the focal length the file states, with `atol = 1e-5 mm` and `rtol` the larger of half a unit in the last digit the file printed and 0.5 per cent, which covers the shift the catalog-glass substitution itself introduces |
| Project | the engine accepts the surface table |
| Optical solids | every element body closes as a solid at the stated outlines |
| Field | the chief ray of every declared field reaches the image plane at some sampling wavelength |

The batch also screened for absolute distortion within **12 per cent** at the modeled samples.
The chief-ray and distortion gates describe these modeled samples. Actual geometric coverage and
image quality remain unconfirmed.

| Deferral reason | Count |
|---|---|
| `DUPLICATE_PROJECT` | 1 |
| `ENGINE_UNSUPPORTED_CONSTRUCT` | 1 |
| `FIELD_BEYOND_DESIGN` | 16 |
| `FIELD_NOT_DELIVERED` | 33 |
| `NO_STATED_APERTURE` | 4 |
| `PARAXIAL_DIFFERS` | 45 |
| **Total deferred** | **100** |

One candidate is a `CONVERSION_FAILED` row (`GEOMETRY_HAS_NO_EDGE`): the engine refuses the glass
between two surfaces of `AF-S Nikkor 24mm f/1.4G ED` at the outline the file states.

The batch 2 counts below use the focal length stated for each accepted source position.

| Source focal length | Accepted |
|---|---|
| Under 24 mm | 1 |
| 24 to under 36 mm | 19 |
| 36 to under 86 mm | 46 |
| 86 to under 201 mm | 16 |
| At least 201 mm | 19 |

## What the model supports

- The records contain first-order values, the material and aperture assumptions, and the original
  sampled chief-ray distortion results. MTF, relative illumination, color reproduction and CRA
  remain unconfirmed.
- The stored image-circle estimate is twice the paraxial image height at the outer modeled angle.
  The patent example takes the angle from the publication, and batch 2 takes it from the nominal
  FX diagonal and source focal length. The estimate is excluded from the search index. The full-frame
  label is available for discovery.
- `design.product_identification` records the source association. Independent product identification
  remains unconfirmed.

## Known limits

- **The corpus is a third party's reading.** Most of its file headers state that the data was
  converted from an upstream optical dataset. A file can be mislabelled: the corpus file named
  `Nikon_100mm_F3.5.lens` cites `US 4,099,850 Example 1` but carries radii about 9.2× the
  publication's, and its focal length is 28.6 mm against the publication's 28.0 mm. That is why a
  corpus record never claims a transcription.
- **Format screening uses file names.** A DX-only design can pass the name filter when the file
  omits `DX`. The chief-ray gate checks the modeled samples and does not validate the format label.
- **Derived apertures.** The `APERTURES_DERIVED` approximation describes the stop and clear-aperture
  assumptions. The two 60 mm f/2.8 Micro-Nikkor inputs cite `US005751485` and share a source SHA-256.
  Their Projects differ in stop opening and three surface clear radii. Both remain pending source
  and aperture reconciliation.
- **Sampled distortion.** `performance[].value_percent` describes the modeled chief-ray distortion
  at its stated sample. Product distortion and full-field behavior remain unconfirmed.
- **Single-position zoom models.** Each zoom Project holds the one position represented by its source
  file, with `configuration_count` set to 1. A zoom range in a title identifies the design family.

## Reproducing a record

```
os-optics project check   records/nikon-fx/nikon-fx-ai-nikkor-180mm-f2p8-ed/project.json
os-optics project solids  records/nikon-fx/nikon-fx-ai-nikkor-180mm-f2p8-ed/project.json
os-optics project paraxial records/nikon-fx/nikon-fx-ai-nikkor-180mm-f2p8-ed/project.json \
    --components LENS --wavelength-nm 587.5618
```

The record's `first_order.engine_check` states the values this run returns, and
`validation.evidence_notes` states the comparison in prose. `record_hash` recomputes from the
record's own JSON with `record_hash` and `record_hash_method` removed;
`tests/test_nikon_fx_batch.py` checks that, the Project hash, and the four validation states for
every committed record.

## Deferral reason codes

| Code | Meaning |
|---|---|
| `DUPLICATE_PROJECT` | A Project with identical committed bytes is retained under `duplicate_of_record_id`. |
| `NO_STATED_APERTURE` | The source supplies neither a focal length nor an f-number for an afocal attachment. |
| `ENGINE_UNSUPPORTED_CONSTRUCT` | the engine refuses the table's construct, with its own message |
| `GEOMETRY_*` | the engine refuses the geometry; the code names which check failed |
| `PARAXIAL_DIFFERS` | the engine's focal length is outside the tolerance the file's digits support |
| `OPTICAL_SOLIDS_INVALID` | the element bodies do not close as solids |
| `FIELD_NOT_DELIVERED` | a declared field reaches the image plane at no sampling wavelength |
| `FIELD_BEYOND_DESIGN` | the traced distortion at the modelled field exceeds the acceptance limit |
| `FIELD_NOT_TRACED` | the field check did not run |
