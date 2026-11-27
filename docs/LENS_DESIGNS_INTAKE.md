# Importing the lens-designs.com collection

This note records how the collection is prepared, so a reviewer can repeat it and check every claim.
It covers the source, the conversion method, the material and aperture decisions, the verification
actually run, and what remains open.

- **Source:** [lens-designs.com](https://www.lens-designs.com/), Dan Reiley's collection of optical
  designs in Zemax format. Files are published in Google Drive folders linked from the collection's
  six section pages; the site states no version of its own, so the snapshot date is recorded per
  record as `collection.source_revision`.
- **Engine:** public `os-optics` **0.14.0**, catalog release **2026-11-25.1** (glasses the file names
  are resolved through it and copied into the Project, so a record does not change when the catalog
  moves).
- **Format:** `csv-surface-table/1`, the only prescription format `0.14.0` reads.
- **Licence:** the site states MIT for every file unless the file's own Notes section says otherwise
  (`https://www.lens-designs.com/note-on-ip`); the notice is committed at
  `licenses/LensDesigns-MIT.txt`. The optical designs themselves are transcriptions of patent or
  journal publications, which the site states are public domain.

## What the source is

The collection publishes `.zmx` (Zemax), `.len` (OSLO), `.zar` (Zemax archive) and `.zda` files.
This collection imports **`.zmx` only**; the other formats are listed in each batch manifest as
deferred with the reason `FORMAT_NOT_IMPORTED`, because the conversion path reads the Zemax surface
block.

| Section | Inputs | What it is |
|---|---|---|
| `photographic-primes` | 1010 | Photographic objectives, mostly patent transcriptions |
| `photographic-zooms` | 374 | Zoom systems, including folded zooms |
| `microscopes` | 151 | Microscope objectives |
| `eyepieces` | 81 | Eyepieces |
| `telescopes` | 93 | Telescope objectives and catadioptric systems |
| `projectors` | 37 | Projection and photolithography systems |

The site also publishes a summary sheet per section listing, for most inputs, the design basis, the
program, the half image size, the f-number and the effective focal length. That sheet is the
**independent witness** for the first-order check: it is not the file, so it can catch a
transcription error the engine cannot.

## Conversion method

The conversion is source-specific preparation and lives in a scratch workspace outside this
checkout: a ZMX reader and a builder that emits a `csv-surface-table/1` file. Only the resulting
native Projects and their metadata are committed.

Per input:

1. **Read the ZMX** (UTF-16LE). Take the `SURF` rows (`TYPE`, `CURV`, `DISZ`, `GLAS`, `DIAM`,
   `CONI`, `PARM`, the stop flag), and the header (`UNIT`, `FNUM`, `ENPD`, `OBNA`, `FTYP`,
   `YFLN`/`XFLN`, `WAVM`, `PWAV`, `GCAT`).
2. **Classify.** A construct the format cannot represent is a deferral with a reason code, not a
   partial conversion.
3. **Translate** geometry: `CURV` → `radius` (`1/CURV`, `0` → plane), `DISZ` → `thickness`,
   `DIAM` → `semi_diameter`, `CONI` → `conic`, `PARM n` → `a2n` (so `PARM 2` → `a4`).
4. **Import** with the engine's own importer (`import_prescription`). The importer does the
   element/stop decomposition, the edge checks and the solids checks; the builder never
   second-guesses them.
5. **Assemble the Project** from the import result: the `COMPOUND` unit, its members, the materials,
   one source per sampling wavelength and one observation plane at the summed thicknesses.
6. **Check** with `project check` and the optical-solids check, and **verify** with the engine's
   paraxial analysis at every sampling wavelength.

### Wavelengths

The file's `WAVM` lines are air wavelengths at the reference environment. Each is converted **once**
to vacuum with the engine's own air model (`material_physics.air_index_exact`), and the Project
carries vacuum nanometres. A file that states no `WAVM` line is given OpticStudio's own default set
(C, d, F with d primary) and the record says so.

### Glasses

The file names a glass on every surface and states its `nd` and `vd`. Three cases:

| Case | Decision |
|---|---|
| the name resolves in the catalog **and** the file's `nd`/`vd` are that glass | the catalog glass is used, and its dispersion curve with it |
| the name resolves but the file's `nd`/`vd` differ by more than 0.002 / 1.0 | the design used the file's own numbers, so they are modelled and the catalog difference is recorded |
| the name does not resolve, or is `___BLANK` | modelled from the file's `nd` and `vd` |

A modelled glass is a three-term Sellmeier with fixed poles solved through the vacuum C, d and F
lines, with the stated Abbe number and a normal-glass partial dispersion of 0.60. Its d-line index is
the file's own, so a paraxial value at the primary wavelength is unaffected by that assumption; the
chromatic behaviour is an approximation and is recorded as one.

`materials.catalog_comparisons` records, for every glass, the catalog value where one exists and the
difference, so a reviewer sees whether the name means the same glass.

### Apertures

`DIAM` is the only outline the file states, and on some inputs it is the mechanical edge of the
barrel rather than the optical clear aperture. The import therefore runs as stated first, and where
the engine reports that two elements' outlines overlap, the stated outline of the named surfaces and
their partners is trimmed to just under the radius the engine reports, and the import is retried.
The trim is recorded in `approximations` with the final values, so no aperture is silently invented.

### The stop

The file marks one surface `STOP`. The import places an aperture stop there with the file's own
clear semi-diameter. A record states `STOP_BLOCKING` when that opening is the smallest in the
system, and `STOP_NOT_BLOCKING` otherwise, with the basis. No record claims a stop-dependent result.

## Verification

Three outcomes are tracked separately, and a record is accepted only when all three hold.

### 1. Conversion

The engine's importer accepted the surface table. Counts, the image-plane position and the importer's
own warnings are recorded in each record.

### 2. Native Project check

`project check` on the committed `project.json` returns `ACCEPTED`, and the optical-solids check
returns `VALID`. `scripts/check_intake.py` re-runs both over every committed record in CI.

### 3. Optical verification against the collection's summary sheet

For every input the summary sheet lists, the engine's paraxial EFL at the primary wavelength is
compared to the printed value. The rule is the seed rule, raised to the precision the sheet can
actually state:

```
|engine − source| ≤ max(atol + rtol · |EFL|, half a printed unit)
atol = 1e-5 mm,  rtol = 1e-4
```

The second term matters: the sheet prints EFL to two or three significant figures, so a rule of
1e-4 relative would demand agreement six times finer than the number it is comparing against can be
stated. `first_order.engine_check.comparison` records both tolerances and which one applied, so a
reviewer recomputes the verdict instead of trusting it.

`validation.paraxial` is `MATCHED` when the comparison holds, `DIFFERS` when the sheet and the file
disagree beyond it, and `NOT_CHECKED` when the sheet lists no value for that input, or states a unit
focal length for a normalised design.

**A `DIFFERS` verdict is not hidden and not re-tuned.** The record keeps the Project it transcribed
and states the difference; the intake note below says what it means.

## What a `DIFFERS` verdict means

The search facts come from the Project, so a `DIFFERS` record still describes a real, self-consistent
lens. What it does not do is reproduce the sheet's number. In the batches seen so far the causes are
in the source, not in the transcription:

- the file's `GLAS` lines name a glass whose stated `nd`/`vd` are not that glass (`B270` at 1.5/40),
  so the design was made with the file's own numbers, not the catalog's;
- a surface carries a solve (a marginal-ray-height or thickness solve) whose stored value is the
  solved one, and re-solving under a different glass model moves the focal length;
- the sheet's row belongs to a different example of the same publication, which is why the lookup
  uses the f-number to tell candidates apart.

A reviewer who wants to resolve one should open the input in OpticStudio and compare; the record
already carries the file's bytes (`collection.source_input_sha256`) and every value it used.

## Known limits

- **First-order only.** The verification is paraxial. No MTF, chief-ray angle or distortion is
  recorded.
- **No field verification.** The Project carries one on-axis source per wavelength, not one per field
  point, so no field-dependent quantity is asserted. `field` states what the file states, with its
  provenance.
- **No operating range claimed.** `spectrum.sampling_span_nm` is the span of the stated sampling
  wavelengths and is `DISCOVERY_ONLY`; `continuous_coverage_nm` is `UNCONFIRMED`.
- **One configuration per record.** A file with several Zemax configurations (a zoom's positions) is
  deferred as `MULTI_CONFIGURATION` rather than split, because the prescription format carries one
  configuration.
- **No mechanical data.** The file gives one outline per surface, so no edge thickness, flange or
  mounting geometry is claimed.
- **`.len`, `.zar` and `.zda` inputs are not imported**, for the reason given above.
