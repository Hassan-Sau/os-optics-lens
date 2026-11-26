# Intake: Canon full-frame photography lenses

This note records how the `records/canon-full-frame/` collection was prepared, so a reviewer can
repeat it and check every claim. It covers the source inventory, the selection, the conversion
method, the material and aperture decisions, the field evidence, the verification actually run, and
what the records do not claim.

- **Source:** US patent publications assigned to Canon, read as Google Patents articles
- **Engine:** public `os-optics` **0.14.0**, catalog release **none used** (every glass is defined
  in the Project, so a record does not change when a catalog release moves)
- **Format:** `csv-surface-table/1`, the only prescription format `0.14.0` reads
- **Batch:** `records/canon-full-frame/batch-canon-full-frame-1.json`
- **Series:** [issue #9](https://github.com/JunLin615/os-optics-lens/issues/9), the first batch of
  a series that extends the library from Zemax exchange files to published patent prescriptions

## Inventory and selection

Fifty-four US patent publications from the Canon assignee search were read, listing **629 numerical
examples**. An example is counted
as full frame when the image height it prints is 20.9 to 21.8 mm, the 35 mm frame half diagonal
being 21.63 mm. That screen leaves **227 full-frame examples in 37 publications**, 119 of them zoom
positions and 108 single-focal-length designs. The candidate inventory in the batch manifest lists
all 227 with the focal length, f-number, half field and image height the publication prints.

The batch takes **31 inputs** from that inventory, chosen to cover the focal-length range and the
structural families rather than to maximise the count: 18 became records, 5 are deferred and 8
failed conversion.

| Outcome | Count |
|---|---|
| Accepted records | 18 |
| Deferred (deliberately not committed) | 5 |
| Conversion failed (a construct the format cannot represent, or the importer refused) | 8 |

The 18 records come from 10 publications and 10 design families. Together they hold 552 surfaces
and 301 lens elements, 21 of them aspheric.

| Record | Publication | EFL (mm) | F/# | Half field | Elements / groups | Image circle (mm) | EFL check |
|---|---|---|---|---|---|---|---|
| `patent-us20250231376a1-ex04` | US20250231376A1 | 24.74 | 1.24 | 41.17° | 18 / 12 | 42.54 | 0.03 |
| `patent-us20250110319a1-ex01` | US20250110319A1 | 26.79 | 1.44 | 38.93° | 11 / 8 | 41.53 | 0.03 |
| `patent-us20250110319a1-ex03` | US20250110319A1 | 33.73 | 1.44 | 32.68° | 11 / 9 | 42.75 | 0.01 |
| `patent-us20250231376a1-ex01` | US20250231376A1 | 34.00 | 1.24 | 32.47° | 17 / 11 | 42.67 | 0.04 |
| `patent-us20260287867a1-ex01-tele` | US20260287867A1 | 67.90 | 2.92 | 17.67° | 15 / 13 | 45.76 | 0.00 |
| `patent-us12259534b2-ex03` | US12259534B2 | 72.10 | 2.89 | 16.70° | 18 / 12 | 42.46 | 0.01 |
| `patent-us11822064b2-ex01` | US11822064B2 | 73.00 | 2.88 | 16.51° | 16 / 13 | 42.44 | 0.02 |
| `patent-us11822064b2-ex02` | US11822064B2 | 73.00 | 2.88 | 16.51° | 16 / 13 | 42.43 | 0.01 |
| `patent-us20260153708a1-ex10` | US20260153708A1 | 71.96 | 1.49 | 16.73° | 14 / 10 | 42.64 | 0.01 |
| `patent-us20260186266a1-ex04` | US20260186266A1 | 82.47 | 1.45 | 14.70° | 17 / 11 | 44.01 | 0.00 |
| `patent-us20260153708a1-ex01` | US20260153708A1 | 82.60 | 1.44 | 14.68° | 13 / 10 | 43.43 | 0.01 |
| `patent-us20260140424a1-ex05` | US20260140424A1 | 89.85 | 3.50 | 13.54° | 20 / 15 | 43.81 | 0.06 |
| `patent-us12259534b2-ex02` | US12259534B2 | 103.04 | 4.60 | 11.86° | 21 / 14 | 43.23 | 0.00 |
| `patent-us20260259392a1-ex04` | US20260259392A1 | 174.62 | 3.60 | 7.06° | 17 / 13 | 45.69 | 0.07 |
| `patent-us20260140424a1-ex01` | US20260140424A1 | 179.88 | 3.60 | 6.86° | 18 / 14 | 43.80 | 0.12 |
| `patent-us11822064b2-ex05` | US11822064B2 | 195.00 | 2.88 | 6.33° | 16 / 13 | 44.19 | 0.01 |
| `patent-us20250224598a1-ex01` | US20250224598A1 | 389.00 | 2.91 | 3.18° | 17 / 15 | 43.39 | 0.02 |
| `patent-us20250224598a1-ex02` | US20250224598A1 | 814.80 | 5.88 | 1.52° | 26 / 20 | 43.81 | 0.25 |

The last column is the engine's paraxial focal length against the printed one, as a fraction of the
tolerance: `|engine - source| <= 0.02 mm + 0.005 |source|`. Fourteen records land under 0.05; the
worst is the 814.8 mm design at 0.25, where 0.01 mm of a surface spacing moves the focal length by
0.1 per cent and the printed table is rounded to 0.01 mm.

Six records describe one end of a zoom (the publication prints one surface table per zoom position);
twelve are single-focal-length designs. `evidence.json` states which configuration was transcribed in
`stated.configuration`, and the title names the end.

## Conversion method

The conversion is source-specific preparation and lives in a scratch workspace outside this
checkout: a reader for the cached Google Patents article, a transcriber per example, and a builder
that emits a `csv-surface-table/1` file and assembles the Project. Only the native Projects and
their metadata are committed.

Per input:

1. **Read the article.** The surface table, the "Various Data" table, any "Aspheric Surface Data"
   table and any "Lens Unit Data" table. Every published example is a sequence of those tables.
2. **Transcribe** one example: surface number, radius, thickness, `nd`, `νd`, the stop row, and the
   conic and aspheric coefficients. Plane surfaces are `inf`, not a guessed radius. A plane-parallel
   plate the publication prints (a glass block, a filter) is transcribed as printed.
3. **Classify.** A construct the format cannot represent is a deferral with a reason code, not a
   partial conversion: a reflecting surface, a non-positive spacing, an odd-order asphere.
4. **Import** with the engine's own importer (`import_prescription`). The importer does the
   element/stop decomposition, the edge checks and the solids checks; the builder never
   second-guesses them.
5. **Assemble the Project** from the import result: the `COMPOUND` unit as `LENS`, one source at the
   primary wavelength and one observation plane at the image plane.
6. **Check** with `project check` and `project solids`, and **verify** optically with the engine's
   thick-lens paraxial matrix and a real meridional chief-ray trace.

## The glass model

The publications state `nd` and `νd` only. Each glass is modelled from those two values: a two-term
Cauchy curve through (`nd`, `νd`), then a three-term Sellmeier with fixed poles fitted to that curve
over the band the publication states. The record carries the coefficients, so a record does not
depend on a catalog release.

The band is the span of the wavelengths the publication states — `435.8–656.3 nm` for the five
records whose publication names the g line as well as d, F and C, and `400–700 nm` for the thirteen
whose publication names no design band, recorded as a modelling convention rather than a claim.
`spectrum.continuous_coverage_nm` is `UNCONFIRMED` in every record: no publication states a
continuous band.

One correction is needed to fit the engine's convention. The engine treats a model glass as an
**absolute** refractive index and a gap as air at 20 °C and 101325 Pa, so the ratio it applies at a
glass-air surface is `nd / 1.0002772`. The model glasses are therefore fitted to `nd × 1.0002772`,
which makes that ratio the printed `nd`. Without the factor the same surface table gives a focal
length 0.03 to 0.4 per cent long — 0.4 per cent on a 100 mm design, 1.2 per cent on the 814.8 mm
one — which is a property of the model and not of the transcription. The records state the
correction as the `ABSOLUTE_INDEX_CONVENTION` approximation.

## The stop and the clear apertures

The publications state the f-number but not the stop diameter, and none states a clear aperture
except the two that print an effective-diameter column. Both are therefore derived, and both are
declared as approximations:

- **Stop.** The modelled stop opening is solved so that the paraxial marginal ray reproduces the
  printed f-number (`STOP_FROM_PRINTED_F_NUMBER`).
- **Clear apertures.** Each semi-diameter is the larger of the paraxial marginal and chief-ray
  heights at the stated f-number and half field, times a mechanical allowance of 6 per cent. Where
  neighbouring surfaces would meet inside that envelope, the allowance is reduced until the
  importer accepts the table; the value used is recorded per record. No clear-aperture value is
  transcribed from the publication (`CLEAR_APERTURES_DERIVED`).

The envelope is paraxial and meridional. On a design whose front group is strongly negative it
overstates the real ray height, which is why the two ultra-wide examples of US20260202717A1 could
not be imported (see the deferrals).

## Field evidence

Every record traces seven real meridional chief rays, at 1.0, 0.95, 0.9, 0.85, 0.7, 0.5 and 0.3 of
the stated half field, through the committed prescription at the reference wavelength, with vector
Snell refraction at spherical, conic and even-asphere surfaces. All seven land on the image plane in
every record. The trace is evidence, not a claim: the record states `field.verification.state =
TRACED`, never `MATCHED`.

The traced height at the full field is the image circle the record reports. It differs from the
printed image height by the prescription's own distortion, and the record keeps both numbers:

| Behaviour | Records |
|---|---|
| Within 2 % of the printed image height | 15 |
| 2 to 6 % outside it | 3 (`us20250110319a1-ex01` −4.0 %, `us20260259392a1-ex04` +5.6 %, `us20260287867a1-ex01-tele` +5.8 %) |
| More than 6 % outside it | 3, not committed (see the deferrals) |

A derived circle wider than 43.27 mm is not a coverage claim. It means the model delivers that
height at the field the publication prints, which is what a lens with pincushion does.

## Verification

What a reviewer can re-run:

1. `python -m unittest discover -s tests` — the collection tests are engine-free: they recompute
   every record hash from the committed JSON, re-derive the evidence and Project hashes from the
   committed bytes, recompute the paraxial verdict and its tolerance from the recorded numbers,
   check the full-frame format fields, check that no record carries an MTF, distortion or
   relative-illumination section, and check that the batch covers distinct designs.
2. `os_optics_lens.corpus.load_corpus('.')` — returns no findings for this collection: no unknown
   vocabulary term, no manifest mismatch, no unresolved evidence reference.
3. Per record, `os-optics project check` and `os-optics project solids` on the committed Project,
   and `os-optics project paraxial` at the recorded wavelength.
4. The transcriber's own confirmation, recorded in `evidence.json`: the printed lens-unit focal
   lengths, the total track and, where printed, the back focal length. Several records reproduce
   every printed unit focal length to 0.01 mm and the total length to 0.01 mm, which is a much
   stronger check on a transcription than the focal length alone. Five records also compare a
   printed back focal length (`first_order.engine_check.comparison.back_focal_length`), the engine
   landing within 0.5 to 3 per cent of the printed value; the other thirteen state
   `UNCONFIRMED` because no back focal length was transcribed for them.

Every record passed `project check`, returned `VALID` from `inspect_optical_solids`, matched its
printed focal length inside the tolerance above, and traced all seven chief rays.

## What the records do not claim

- **No performance claim.** There is no MTF, distortion curve, relative illumination, spot size or
  wavefront error in a record, and no field of view beyond the printed half field. The test suite
  fails if such a section appears.
- **No coverage claim.** `spectrum.continuous_coverage_nm` is `UNCONFIRMED`; `band_facets` is a
  discovery label.
- **No stop-dependent claim.** `design.aperture_validity.satisfies_stop_dependent_constraints` is
  `false` in every record: a stop-dependent constraint needs pupil or field evidence that these
  records do not carry.
- **No focusing claim.** A prescription is transcribed in the state the publication prints its
  numbers for — infinite conjugate, and for a design with a floating focus group the infinite
  spacings. Nothing is claimed about the focusing travel or about performance at a finite distance.
- **No claim that the prescription is manufacturable.** Clear apertures are derived, not printed;
  a real lens has tolerances, and these records carry none.

## Deferred and failed inputs

| Input | Outcome | Reason code | Why |
|---|---|---|---|
| US20260186266A1 ex. 1, wide end | Deferred | `FIELD_IMAGE_HEIGHT_INCONSISTENT` | Verified at all three zoom positions, but the printed 37.12° wide field traces to 16.77 mm, a 33.55 mm circle against the printed 43.28 mm. The publication's middle and telephoto half angles are exactly `atan(21.64/f)`; its wide one is not. |
| US20260287867A1 ex. 1, wide end | Deferred | `FIELD_IMAGE_HEIGHT_INCONSISTENT` | The printed 34.93° traces to 18.77 mm (37.54 mm circle). At the frame-corner angle `atan(21.64/28.80) = 36.92°` the same prescription returns exactly 20.10 mm, so the printed field is computed from the design's own corner height while the table prints the nominal 21.64 mm. The telephoto end of the same example is committed. |
| US20260259392A1 ex. 1 | Deferred | `FIELD_IMAGE_HEIGHT_INCONSISTENT` | Verified (unit focal lengths to 0.01 mm, total length and back focus agree), but the corner traces to 25.17 mm, a 50.34 mm circle: 16 per cent pincushion in the prescription. Committing it would overstate the format by 16 per cent. |
| US20260140424A1 ex. 4 | Conversion failed | `NON_POSITIVE_SPACING` | The printed table carries `d7 = -0.03 mm` and `d33 = -0.06 mm`. The importer refuses a non-positive thickness and the numbers may not be altered; with them the thicknesses sum to the printed overall length of 176.52 mm exactly. |
| US20260194764A1 ex. 4, ex. 5 | Conversion failed | `REFLECTIVE_SURFACE` | A folded transmissive-reflective prism: the sequential surface table describes one forward pass along +Z. |
| US20260259398A1 ex. 1, ex. 7, ex. 15 | Conversion failed | `REFLECTIVE_SURFACE` | A catadioptric family; the whole publication is folded out rather than transcribed as a refractive chain. |
| US20260202717A1 ex. 1 | Conversion failed | `CLEAR_APERTURE_UNRESOLVABLE` | Verified six ways, but the paraxial envelope overstates the chief height by 25 to 50 per cent in the negative front group (26.45 mm derived against a 22.391 mm vertex radius at surface 2). The publication prints an effective diameter for every surface; with those the import succeeds at an EFL fraction of 0.013, but the toolchain cannot yet take transcribed semi-diameters. |
| US20260202717A1 ex. 11 | Conversion failed | `UNSUPPORTED_ASPHERE_TERM` | The asphere formula carries odd orders (`A3`, `A5`, `A7`); `csv-surface-table/1` admits `a4` to `a18` only. The odd terms move surface 4 by 11.13 mm of sag at the clear aperture, so they cannot be dropped. |
| US20250231376A1 ex. 2 | Deferred | `VARIANT_OUTSIDE_BATCH` | The same 34.00 mm prescription at F/1.45; the F/1.24 state is committed as ex. 1. |
| US20250231376A1 ex. 3 | Deferred | `VARIANT_OUTSIDE_BATCH` | A third f/1.24 design of the same publication; the batch takes two examples per publication. |

## Open work

- **Odd-order aspheres.** Nineteen of the 21 examples of US20260202717A1 print `A3`/`A5`/`A7`.
  Until the prescription format carries odd orders, that publication is out of reach.
- **Transcribed clear apertures.** Two publications print an effective diameter for every surface.
  Taking them would both improve those records and unblock the ultra-wides that the paraxial
  envelope currently overstates.
- **Reflecting and folded systems.** Five publications in this series are catadioptric or use a
  folded prism. They need a Project with two axes, not a longer surface table.
- **Nominal fields.** Three wide-angle ends print a half field that does not reproduce the printed
  image height. A future revision could record the field the prescription actually delivers and mark
  the printed one as nominal, instead of dropping the record.
- **The rest of the inventory.** 227 full-frame examples are inventoried and 31 considered; 196 are
  still open, including the 12.43 mm, 14.42 mm and 20.48 mm wide-angles above and every zoom
  position the batch did not take.
