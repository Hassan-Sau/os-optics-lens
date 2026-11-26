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

The series covers Nikon-branded **FX photography lenses** across mounts and product generations:
F, AI, AI-S, AF, AF-D, AF-S, AF-P, and the Z line, primes and zooms, including designs a DX body
can also use. A shared optical design appears once. Two classes are out of scope: afocal
attachments (teleconverters, close-up lenses), which have no focal length of their own, and
reflecting designs, which a sequential surface table cannot carry.

## Two sources, two kinds of claim

The series uses two sources, and a record says which one it came from. The distinction matters:
one is a transcription of numbers a publication prints, the other is a reproduction of a
prescription a corpus distributes.

| Batch | Source | Claim |
|---|---|---|
| `nikon-fx-1` | A numerical example printed in a United States patent publication | The surface table is **transcribed** from the publication, and the engine reproduces the focal length and back focal distance the publication states |
| `nikon-fx-2` | The [FlareSim lens corpus](https://github.com/LocalStarlight/flaresim_nuke) at revision [`0e28ead9`](https://github.com/LocalStarlight/flaresim_nuke/tree/0e28ead9a3ec4898c7568f27b1ce8c0de6df7a08) | The surface table is **reproduced** from the corpus file, and the engine reproduces the design focal length the file states in its own header |

The corpus is MIT licensed; its notice is committed at `licenses/FlareSim-MIT.txt`. Most corpus
files cite a patent number in their header, and those numbers are kept in
`collection.original_publication` as the design's own reference. They are **not** a transcription
claim: a corpus file is a third party's reading of a publication, and this series does not vouch
for it. The one record that does claim a transcription is `nikon-fx-us4099850a-ex1`, whose surface
table was read from the publication itself and checked number by number against the rendered text.

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

That leaves **205 candidates**, one per corpus file, each with an `entry.json` recording the file's
own facts: its header, its patent citation, its stated focal length and every surface.

| Outcome | Count |
|---|---|
| Accepted records | 104 |
| Deferred, with a reason code | 100 |
| Conversion failed (the engine refused the table) | 1 |

Every candidate appears in the manifest with its own row, so the inventory, the accepted records
and the deferrals reconcile.

## Conversion method

The conversion is source-specific preparation and lives in a scratch workspace outside this
checkout: a `.lens` reader, a glass matcher, an aperture synthesiser and a Project builder. Only
the native Projects and their metadata are committed.

Per file:

1. **Read the file.** The corpus prints, per surface, the radius, the axial thickness, the
   refractive index, the Abbe number, the element outline diameter and a coating column, plus one
   stop plane. A row with no index is air. A zero-radius row is a plane.
2. **Match the glass.** The corpus states `nd` and `vd` and no glass name. Each pair is matched to
   the closest published catalog glass by `|Δnd| / 0.001 + |Δvd| / 0.5`, and the Project carries
   that glass's own dispersion curve. The catalog glass is **compared, never substituted**: the
   record keeps the stated `nd` and `vd` beside the catalog values and their differences.
3. **Derive the apertures.** The corpus states one outline per element and no clear aperture. The
   stop is sized so the entrance pupil gives the product's f-number; each element's clear aperture
   is the smaller of the unvignetted envelope for the axial marginal ray plus the chief ray of the
   modelled field, and the radius at which the steepest surface of that element has a sag of half
   the adjacent glass thickness. Two neighbouring outlines that overlap where the air gap is narrow
   are edged down in 10 per cent steps until the bodies clear, and every reduction is recorded in
   `approximations`.
4. **Derive the field.** The prescription covers the FX format, so the modelled field is the angle
   the FX diagonal (43.27 mm) subtends at the design focal length — `atan(h/f)` for a rectilinear
   design, `h/f` in radians for a fish eye, whose projection maps angle to height directly. A file
   that states its own field angle in its name (the 220° fish eyes) uses that instead.
5. **Place the image plane at the paraxial focus.** The corpus prints a finite-conjugate spacing,
   and a collimated beam focuses elsewhere: for `AI Nikkor 180mm f/2.8 ED` the file's last
   thickness lands the image 30 mm short of the focus. The plane is therefore the exit vertex plus
   the engine's paraxial back focal distance, and `facts.json` records which basis was used.
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

and the traced distortion at the modelled field stays inside **12 per cent**. That
last gate is a statement about the model, not about the lens: a design whose traced distortion is
far above what its type can have is a design whose modelled field is wider than the prescription is
corrected over, and the record would claim a field it does not deliver. Such a candidate is
deferred, not published with a field claim it cannot support.

| Deferral reason | Count |
|---|---|
| `ENGINE_UNSUPPORTED_CONSTRUCT` | 1 |
| `FIELD_BEYOND_DESIGN` | 16 |
| `FIELD_NOT_DELIVERED` | 34 |
| `GEOMETRY_HAS_NO_EDGE` | 1 |
| `NO_STATED_APERTURE` | 4 |
| `PARAXIAL_DIFFERS` | 45 |
| **Total deferred** | **100** |

One candidate is a `CONVERSION_FAILED` row (`GEOMETRY_HAS_NO_EDGE`): the engine refuses the glass
between two surfaces of `AF-S Nikkor 24mm f/1.4G ED` at the outline the file states.

The accepted set is not evenly spread over the range. By design focal length:

| Range | Accepted |
|---|---|
| under 24 mm | 2 |
| 24 – 35 mm | 14 |
| 36 – 85 mm | 48 |
| 86 – 200 mm | 20 |
| over 200 mm | 20 |

The wide end is thin because that is where the modelled FX field is widest, and a wide design is
the first to fail the field gates: either its chief ray does not survive to the image plane at the
corner, or the traced distortion says the modelled field is wider than the prescription is
corrected over. Those designs are deferred rather than published with a field claim that does not
hold.

## What a record does not claim

- **No modulation transfer function.** The corpus states none, and this series measures none. A
  record carries first-order values, the glass list, the aperture, the field and its traced
  distortion. It is a starting point for a design study, not a specification sheet.
- **No relative illumination, no colour reproduction, no CRA.** None is measured here.
- **No tested image circle.** `image_format.image_circle_diameter_mm` is the field the record is
  evaluated over, derived from the format; it is not a coverage measurement.
- **No claim about the product.** The corpus pairs a design with a product name. The record repeats
  that pairing in `design.product_identification` and does not independently establish it.

## Known limits

- **The corpus is a third party's reading.** Its files are converted from photonstophotos.net
  Optical Bench data, as most headers state. A file can be mislabelled: the corpus file named
  `Nikon_100mm_F3.5.lens` cites `US 4,099,850 Example 1` but carries radii about 9.2× the
  publication's, and its focal length is 28.6 mm against the publication's 28.0 mm. That is why a
  corpus record never claims a transcription.
- **DX leakage.** Selection is by file name. A DX-only design whose corpus name omits `DX` can pass
  the filter; the field gate is what removes it, because such a design does not deliver the FX
  corner.
- **Apertures are derived, not stated.** Every record says so in `approximations`
  (`APERTURES_DERIVED`), and a reviewer who has the real clear apertures should prefer them.
- **Distortion is reported, not corrected.** Wide designs show larger values than the products do,
  which is a property of the derived apertures and the modelled field. Read
  `performance[].value_percent` as an upper bound on what the prescription delivers at that field,
  not as the product's published distortion.
- **One configuration per zoom.** A corpus file is one zoom position. A zoom record is that
  position, named by the design's focal length, and its `configuration_count` is 1.

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
| `NO_STATED_APERTURE` | an afocal attachment: no focal length, no f-number |
| `ENGINE_UNSUPPORTED_CONSTRUCT` | the engine refuses the table's construct, with its own message |
| `GEOMETRY_*` | the engine refuses the geometry; the code names which check failed |
| `PARAXIAL_DIFFERS` | the engine's focal length is outside the tolerance the file's digits support |
| `OPTICAL_SOLIDS_INVALID` | the element bodies do not close as solids |
| `FIELD_NOT_DELIVERED` | a declared field reaches the image plane at no sampling wavelength |
| `FIELD_BEYOND_DESIGN` | the traced distortion at the modelled field exceeds the acceptance limit |
| `FIELD_NOT_TRACED` | the field check did not run |
