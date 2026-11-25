# Importing the LensLibrary seed collection

This note records how the first collection was prepared, so a reviewer can repeat it and check
every claim. It covers the source inventory, the conversion method, the material and surface
decisions, the verification actually run, and what remains open.

- **Source:** [Nathan Hagen's LensLibrary](https://github.com/nzhagen/LensLibrary) at revision
  [`86b2c0cac5a67e2112d58518230c4d8728154f4e`](https://github.com/nzhagen/LensLibrary/tree/86b2c0cac5a67e2112d58518230c4d8728154f4e)
- **Engine:** public `os-optics` **0.14.0**, catalog release **none used** (every glass is defined
  in the Project, so a record does not change when a catalog release moves)
- **Format:** `csv-surface-table/1`, the only prescription format `0.14.0` reads
- **Batch:** `records/lenslibrary/batch-lenslibrary-seed-1.json`

## Inventory

The pinned revision holds **77 ZMX files** under `zemax_files/`. They are counted
case-insensitively because one file is named `1975678.ZMX`. The manifest has one row per file, so
the inventory, the accepted records and the deferrals reconcile.

| Outcome | Count |
|---|---|
| Accepted records | 40 |
| Deferred (deliberately not converted) | 31 |
| Conversion failed (engine refused the table) | 6 |

`prescription_files/` holds 81 Zemax prescription dumps. They are **evidence**, not corpus: each
record cites the dump it used and its SHA-256. A dump is the source of the per-surface index
table and of the source-stated EFL, BFL and total track.

`lens_properties_list.txt` is a hand-maintained summary of the collection. It is **not** a second
source: its field convention is not consistent across rows (some rows give a full field, others a
half field, and two angle-typed rows carry an object height), so field and aperture values come
from the design file and the property list is recorded as a comparison only.

## Conversion method

The conversion is source-specific preparation and lives in a scratch workspace outside this
checkout: a ZMX reader, a reader for the upstream prescription dump, and a builder that emits a
`csv-surface-table/1` file. Only the resulting native Projects and their metadata are committed.

Per input:

1. **Read the ZMX** (UTF-16LE). Take `SURF` rows, `TYPE`, `CURV`, `DISZ`, `GLAS`, `DIAM`, `CONI`,
   `PARM`, the stop flag, `WAVM`/`PWAV`, `FTYP`, the field lines and `CONF`.
2. **Read the prescription dump** for the same design: the field table and its type, the
   wavelength table, the surface summary (radius, thickness, glass, diameter, conic), the
   per-surface index table, the source-stated EFL / BFL / total track and the edge-thickness table.
3. **Classify.** A construct the format cannot represent is a deferral with a reason code, not a
   partial conversion.
4. **Translate** geometry into the surface table: `CURV` → `radius` (`1/CURV`, `0` → plane),
   `DISZ` → `thickness`, `GLAS` → a material id, `DIAM` → `semi_diameter`, `CONI` → `conic`,
   `PARM n` → `a{2n}`.
5. **Import** with the engine's own importer (`import_prescription`). The importer does the
   element/stop decomposition, the edge checks and the solids checks; the builder never
   second-guesses them.
6. **Assemble the Project** from the import result: the `COMPOUND` unit, its members, the
   materials, one source at the primary wavelength and one observation plane at the reported image
   plane.
7. **Check** with `project check` and `project solids`, and **verify** optically with the engine's
   thick-lens paraxial matrix.

### Reproducibility

The same input produces the same surface table and the same Project. A second full run of all 77
inputs produced 93 byte-identical output files and identical record IDs; that repeat check is part
of the preparation run, not a one-off.

## What the source contains, and what happened to it

| Construct | Files | Outcome |
|---|---|---|
| Sequential refracting systems, representable | 40 | Accepted |
| Reflecting surfaces (`MIRROR`, `GLAS MIRROR`) | 16 | Deferred: `REFLECTOR`. The format refuses reflecting rows in a sequence; [os-optics#57](https://github.com/JunLin615/os-optics/issues/57) covers importing them |
| Coordinate breaks (decentre/tilt) | 12 | Deferred: `UNSUPPORTED_COORDBRK` |
| Diffraction gratings (plane, spherical, toroidal) | 8 | Deferred: `UNSUPPORTED_DGRATING`, and `UNSUPPORTED_TOROGRAT` for the toroidal one |
| Ideal paraxial surfaces | 8 | Deferred: `UNSUPPORTED_PARAXIAL` |
| Multi-configuration (`CONF`) | 7 | Deferred: `MULTI_CONFIGURATION`; the record layout keeps configurations together, so one variant is not split out |
| A zero or negative spacing between surfaces | 6 | Deferred: `NON_POSITIVE_SPACING`; a zero air gap or a negative "virtual" thickness is not a spacing the format can carry |
| A nonzero `a2` (r²) aspheric term | 2 | Deferred: `A2_TERM`; the format has no `a2` column |
| No upstream prescription dump | 2 | Deferred: `NO_PRESCRIPTION_DUMP`; without it the per-surface index table and the stated first-order values are unavailable |
| A tilted surface | 1 | Deferred: `UNSUPPORTED_TILTSURF` |
| Off-axis field points (nonzero x) | 1 | Deferred: `OFF_AXIS_FIELDS`; a coaxial sequence cannot carry them |
| A toroidal surface | 1 | Deferred: `TOROIDAL_PENDING`; the row is in a grating system that is deferred anyway |
| An immersed final space (the sequence ends in glass or water) | 2 | Failed: `UNSUPPORTED_FEATURE`, the format requires the image space to be air |
| Surfaces that intersect inside the clear aperture | 2 | Failed: `SURFACES_INTERSECT`, the source's own clear apertures make the glass impossible |
| Elements whose outlines overlap at the stated apertures | 2 | Failed: `BODIES_INTERSECT`, the source's apertures put two bodies in one volume |

Counts overlap: one file can carry several constructs, and the manifest lists them all in
`constructs`. The six failed inputs are the two immersed-space designs, the two designs whose own
apertures make a surface intersect, and the two whose outlines overlap.

## Material decisions

`GLAS ___BLANK` is Zemax's model glass: the file states only `nd` and `Vd`, which do not define a
dispersion curve. The upstream prescription dump, however, prints the **actual index of every
surface at every enabled wavelength**. Those samples are the source data, so every glass in this
batch is defined from them:

- three or more samples → a 3-term Sellmeier with fixed poles `(0.0035, 0.0125, 90) µm²` solved to
  the samples (residual at machine precision, recorded per material);
- one sample → a constant index over a 1 nm band, recorded as such.

`___BLANK` entries are keyed by their `(nd, Vd)` pair, so two model glasses in one design stay two
materials. This mattered: treating them as one material moved the EFL of a reference design by
3 %.

Named catalog glasses (N-BK7, SF6, CAF2, …) are **not substituted**. Where a published catalog
glass of the same name exists, the record keeps the source's own indices and adds the largest index
difference as a comparison, so a reviewer can see whether the names mean the same glass.

Air wavelengths: the source states wavelengths in air at 20 °C and 101325 Pa. They are converted
once to vacuum with the Edlén 1953 model — the model the engine names — and the surface table is
written in vacuum wavelengths. Declaring them as air would have made the engine apply the
conversion a second time.

## Surface and stop decisions

- **Radii** are copied with their sign (positive: centre of curvature after the surface). No
  re-signing, no mirroring.
- **Clear apertures** come from `DIAM`. The source states no mechanical semi-diameter, so each
  surface is edged at its own clear semi-diameter and the record says so.
- **The stop** keeps its own row and its own opening. The source states no stop-plate outer radius;
  the plate is placed at the largest clear semi-diameter beside the stop so the stop actually
  blocks light. Where a neighbouring element would meet that plate (one design), the plate falls
  back to the opening, and the record states that the stop then blocks no light.
- **Dummy surfaces** (air on both sides, not the stop) are reported by the importer and add no
  geometry.
- **Image plane:** the last surface's thickness gives it; the Project puts an observation plane
  there.

## Source disagreements, and what can settle them

One rule decided every case: **a value comes from the design file**, and a summary is not a source.

The design file (`zemax_files/*.zmx`) states the field type and field points itself (`FTYP`,
`YFLN`) and the system aperture itself (`FNUM` or `ENPD`). The upstream dump prints the same field
table, so it serves as a cross-check: across all 40 accepted records the two agree
(`prescription_dump_check: MATCHES`). Where the ZMX states no aperture (`5000548a` is one), the
dump's stated f-number is used and the record names that basis.

The collection's `lens_properties_list.txt` disagrees with the design file on some rows. That is a
property of the summary, not a conflict in the optics, so it is recorded as
`property_list_comparison` and never as a value.

**The engine does evaluate a field angle** — a field point is the source pose turned about the axis
across the beam, and the field point at the plane is the chief-ray hit point. Verified on
`lenslibrary-528155` (EFL 239.8934 mm, half field 26.6°): a source turned 5° puts the chief ray at
20.8661 mm, against `f·tan θ` = 20.9880 mm, a 0.58 % difference (distortion). So the engine can
settle a field question in principle.

It does not settle *this* one, for a narrower reason: the batch did not build per-field
configurations, so the committed Projects carry one on-axis source and one observation plane. A
field value is therefore not a quantity the records assert from the engine — it stays
`SOURCE_STATED`, and the records do not claim a field verification.

Turning a source into a field point has traps that cost me two wrong attempts (a laterally shifted
source, and a plane aperture that clips the off-axis beam); the method is not documented in the
engine's user docs. That gap is filed as
[os-optics#87](https://github.com/JunLin615/os-optics/issues/87).

## Verification

Three outcomes are tracked separately, and a record is accepted only when all three hold.

### 1. Conversion

The engine's importer accepted the surface table. Counts, the image-plane position and the
importer's own warnings are recorded in each record.

### 2. Native Project check

`project check` on the committed `project.json` returns `ACCEPTED`, and `project solids` returns
`VALID` with no error-severity finding. Re-run over the committed corpus in a clean environment:
40 of 40 pass.

Reviewer commands, from the repository root:

```
os-optics project check records/lenslibrary/lenslibrary-528155/project.json
os-optics project solids records/lenslibrary/lenslibrary-528155/project.json
```

### 3. Optical verification

For every accepted record the engine's thick-lens paraxial matrix, evaluated on the committed
Project at the source's primary wavelength, reproduces the source-stated EFL and BFL. The
comparison is a **paraxial** one: it establishes first-order agreement, not image quality.

| Quantity | Condition | Result |
|---|---|---|
| Signed EFL | primary vacuum wavelength, image space | 40/40 within 6 × 10⁻⁵ relative |
| BFL | same | 40/40 within 1 × 10⁻⁴ relative |

The largest EFL difference is `lenslibrary-5852515b` at 6 × 10⁻⁵ relative. That residual is
expected: the source's own EFL comes from its ray-traced paraxial solve with its glass catalogs,
while the record uses the source's printed index samples.

`os-optics project paraxial` is the reviewer command:

```
os-optics project paraxial records/lenslibrary/lenslibrary-528155/project.json \
    --components LENS --wavelength-nm 587.72485
```

## Path checks

Run in the scratch workspace, because they need the source files:

| Check | Result |
|---|---|
| A supported conversion is deterministic and yields the expected element/stop counts | PASS |
| A reflecting system is refused with its own code, not silently dropped | PASS |
| Two model glasses with different `(nd, Vd)` stay two materials | PASS |
| Air wavelengths are converted to vacuum once, and the band is written as vacuum | PASS |
| An angular field and an object-space height never share a field | PASS |
| A zero spacing is refused rather than silently re-spaced | PASS |

## Known limits

- **First-order only.** The optical verification is paraxial. No MTF, chief-ray angle or distortion
  is recorded: the source states none with interpretable conditions, and this batch built no
  per-field configurations, so no field-dependent quantity is asserted. The engine can evaluate a
  field point (see above); the records simply do not claim one.
- **No operating range claimed.** `spectrum.operating_range_nm` is the span of the enabled sampling
  wavelengths (or a 1 nm numerical band for a single-wavelength design), labelled as such. A set of
  enabled wavelengths is sampling evidence, not a specified range.
- **Single configuration.** Every accepted record is one configuration. The seven
  multi-configuration inputs are deferred rather than split.
- **No mechanical data.** The source gives clear apertures only, so no edge thickness, flange or
  mounting geometry is claimed.
- **Image circle not recorded.** The source states field angles or field heights, not a sensor
  format; an image circle would have to be derived from a field definition the source does not fix.
- **Deferred constructs** belong to the engine, not to this repository: reflecting rows, coordinate
  breaks, gratings, paraxial surfaces, the `a2` term and immersed spaces are the import gaps tracked
  in [os-optics#57](https://github.com/JunLin615/os-optics/issues/57); model-glass records that name
  their dispersion model and parameters are [os-optics#35](https://github.com/JunLin615/os-optics/issues/35).
- **No licensing blocker.** The upstream collection is MIT; the full notice is in
  `licenses/LensLibrary-MIT.txt` and stays with the records. No input was deferred for unclear
  redistribution terms.