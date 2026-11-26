# Phone main-camera and ultrawide modules, batch 1

This note records how the first phone-module batch was prepared so a reviewer can repeat the
conversion and check every claim. It covers the sources, the transcription rules, the material and
aperture decisions, the field evidence, the checks actually run and what the records leave
unconfirmed. The batch belongs to the series issue
[#24](https://github.com/JunLin615/os-optics-lens/issues/24), which coordinates main-camera and
ultrawide modules; dedicated telephoto modules are a separate series.

- **Collection:** `phone-modules`
- **Batch:** [`batch-phone-modules-1.json`](../records/phone-modules/batch-phone-modules-1.json)
- **Engine:** public `os-optics` **0.14.0**, no catalog release (every material is defined in the
  Project, so a record does not move when the catalog does)
- **Format:** `csv-surface-table/1`
- **Records:** 11 accepted, 11 deferred, 0 conversion failures

## What the batch contains

| Record | Module role | Elements | EFL (engine) | f-number | Full field | Total track | Image circle | CRA at edge |
|---|---|---|---|---|---|---|---|---|
| `patent-us9366845b2-ex01` | main camera | 7 | 3.896 | f/1.60 | 71.6° | 5.069 | 5.81 | 24.2° |
| `patent-us9366845b2-ex04` | main camera | 7 | 3.666 | f/2.00 | 75.2° | 4.495 | 5.79 | 26.5° |
| `patent-us9366845b2-ex05` | main camera | 7 | 5.600 | f/1.75 | 69.0° | 6.763 | 7.83 | 30.1° |
| `patent-us9366845b2-ex06` | main camera | 7 | 5.051 | f/1.85 | 74.8° | 6.601 | 7.80 | 33.0° |
| `patent-us9366845b2-ex08` | main camera | 7 | 3.933 | f/2.30 | 70.2° | 5.008 | 5.71 | 27.9° |
| `patent-us9366845b2-ex13` | main camera | 7 | 5.191 | f/2.05 | 72.4° | 6.529 | 7.82 | 33.7° |
| `patent-us10247911b2-ex01` | ultrawide | 5 | 1.733 | f/2.40 | 140.0° | 5.072 | 4.67 | 31.9° |
| `patent-us10247911b2-ex03` | ultrawide | 5 | 1.531 | f/2.30 | 124.0° | 5.018 | 4.17 | 33.0° |
| `patent-us10247911b2-ex05` | ultrawide | 5 | 1.545 | f/3.20 | 134.0° | 5.229 | 3.81 | 32.2° |
| `patent-us10247911b2-ex08` | ultrawide | 5 | 1.331 | f/2.70 | 120.0° | 5.005 | 3.76 | 33.8° |
| `patent-us10247911b2-ex09` | ultrawide | 5 | 2.461 | f/2.20 | 134.0° | 7.629 | 6.72 | 33.7° |

All lengths are millimetres. EFL, total track and image circle come from the committed Project; the
f-number and the field are the publication's printed values; CRA is the traced chief-ray angle at
the largest field the prescription traces.

The two families are complementary by design: the seven-element group covers the
`3.7 mm … 5.6 mm` focal-length and `f/1.6 … f/2.3` aperture range of a main camera, the five-element
group the `1.3 mm … 2.5 mm` and `f/2.2 … f/3.2` range of an ultrawide. Both are entirely plastic,
all-aspheric, with a plane-parallel IR-cut plate and a front or near-front stop.

## Sources

| Publication | Assignee | Examples | Used here |
|---|---|---|---|
| [US9366845B2](https://patents.google.com/patent/US9366845B2/en), *Photographing optical lens assembly, image capturing unit and electronic device* | Largan Precision Co., Ltd. | 13 | 6 |
| [US10247911B2](https://patents.google.com/patent/US10247911B2/en), *Imaging optical lens assembly, image capturing apparatus and electronic device* | Largan Precision Co., Ltd. | 9 | 5 |

Each record names the tables it came from (`Table 1` surface data, `Table 2` aspheric coefficients)
and the embodiment. The publications are granted US patents: the numerical examples are a public
record, and the patent document itself is not redistributed. The transcription, the native Project
and the evidence extract are MIT, like the rest of the repository.

A numerical example is a **published design**, not a measured product. Nothing in the batch claims
that a shipped module uses it.

## Conversion method

The conversion is source-specific preparation and lives in a preparation workspace outside this
checkout; only the native Projects, the records and the evidence extracts are committed.

Per example:

1. **Read the publication.** The description is fetched as text and split into its table blocks.
   `Table 1` holds one row per surface with the curvature radius, the thickness, the material index
   and Abbe number, and the focal length of the element; `Table 2` holds the conic constant and the
   even-asphere coefficients `A4 … A18` per surface. The printed `f`, `Fno` and `HFOV` are read from
   the table header.
2. **Transcribe.** `radius`, `thickness`, `nd`, `Vd`, `k` and `A4 … A18` are copied verbatim into
   the surface table; a `Plano` radius becomes a plane. No radius is re-signed, no thickness is
   re-spaced.
3. **Classify.** The stop row keeps its own plane. The IR-cut plate stays in the sequence, because
   it contributes to the back focus and to the aberration balance the publication reports.
4. **Import** with the engine's own importer (`project import-prescription`). The importer does the
   element and stop decomposition, the edge checks and the optical-solid checks; the transcription
   never second-guesses them.
5. **Assemble the Project**: one `COMPOUND` unit, an on-axis source at infinity, one observation
   plane at the published image distance.
6. **Check** with `project check` and `project solids`, and **verify** optically with the engine's
   thick-lens paraxial matrix at the reference wavelength.

### Surface conventions

- **Radius sign** follows the usual lens-design convention and is copied unchanged.
- **Aspheric coefficients** are read as powers of the radius in millimetres, which is what the
  publications' formula defines (`z = c r² / (1 + √(1 − (1+k) c² r²)) + Σ Aᵢ rⁱ`). They are not
  normalised by an aperture radius: the coefficients of these examples are of order `10⁻³ … 10⁻¹`
  and produce a physically defined profile over the apertures the records use.
- **Reference wavelength** is the d-line, 587.6 nm, as each publication states. No other sample is
  claimed.
- **Stop standoff.** Three of the main-camera examples list the stop a *negative* distance in front
  of the first surface. A surface table carries positive spacings only, so the stop plane sits
  0.05 mm in front of the first surface and the record carries `STOP_STANDOFF_ADJUSTED` with the
  printed value. The remaining eight examples keep their stop where the publication puts it.

## Material model

The publications state `nd` and `Vd` only; those two numbers do not define a dispersion curve.
Each material is therefore modelled explicitly:

1. a two-term Cauchy curve `n(λ) = A + B/λ²` is solved exactly from `(nd, Vd)`;
2. a three-term Sellmeier with fixed poles `(0.0035, 0.0125, 90) µm²` is fitted to that curve over
   450–660 nm and stored in the Project.

The index at the reference wavelength is the source's `nd`; the shape of the curve between samples
is a model, and the record says so with `ND_VD_DISPERSION_MODEL`. A record is therefore comparable
with another record of this batch at the reference wavelength, and its chromatic behaviour is
plausible but not the source's own glass data.

## Clear apertures

The publications state no clear apertures. Each surface's semi-diameter is derived, not invented:

1. the stop opening is solved so the modelled f-number reproduces the printed value (the engine and
   an independent paraxial trace agree to better than 0.5 %);
2. a real meridional ray trace covers fields at 0, 0.5 and 0.7 of the printed half-field and eleven
   pupil positions;
3. each semi-diameter is the envelope of that beam plus a 7 % mechanical allowance;
4. a surface is capped where its aspheric polynomial stops being physically usable (sag beyond 60 %
   of the radius, slope beyond 72°), because a clear aperture cannot sit where the profile folds.

The result is a lens that passes the engine's edge and body checks with a positive glass edge
everywhere. It is a **mechanical estimate**, flagged `CLEAR_APERTURES_DERIVED`; a drawing from the
manufacturer would supersede it. It also means the outermost field is partly vignetted at the front
element of some records — which is what a real module does, but the exact vignetting is not asserted.

## Field and image circle

The publications print a half field of view and no image height. The records therefore:

- carry the field as `SOURCE_STATED` (`half_field_deg`, `full_field_deg`);
- trace the chief ray at seven field fractions and record the image height and chief-ray angle at
  each (`field.traced_chief_rays`);
- derive the image circle from **twice the traced image height at the largest field that traces
  cleanly**, and state that field fraction. Nine records reach the printed half-field; two reach
  0.95 of it, because the last surface's polynomial is undefined slightly beyond.

The image circle is therefore `DERIVED`, not a sensor specification. It is a usable filter value,
not a coverage guarantee; the records do not claim a sensor format, a pixel pitch or a cover-glass
stack.

## Verification

Three outcomes are tracked separately, and a record is accepted only when all three hold.

| Check | Result |
|---|---|
| Conversion (engine importer) | 11 of 11 accepted |
| Native Project check (`project check`) | 11 of 11 `ACCEPTED` |
| Optical solids (`project solids`) | 11 of 11 `VALID`, no error-severity finding |
| Paraxial EFL against the printed focal length | 11 of 11 within the stated rule; at most 68 % of the allowance |

The paraxial comparison uses

```
|engine − source| ≤ atol + rtol · |source|
atol = 0.005 mm,  rtol = 3 × 10⁻³
```

The allowance covers three things, none of them tuning: the publication prints the focal length to
two decimals; the radii and thicknesses are printed to three; and the engine reports the focal
length relative to the Project environment's air index, which shifts EFL by about 0.13 % against a
unit-index trace. The tightest record uses 68 % of the allowance
(`patent-us10247911b2-ex08`), the loosest 8 % (`…-ex09`).

Reviewer commands, from the repository root:

```console
os-optics project check records/phone-modules/patent-us9366845b2-ex01/project.json
os-optics project solids records/phone-modules/patent-us9366845b2-ex01/project.json
os-optics project paraxial records/phone-modules/patent-us9366845b2-ex01/project.json \
    --components LENS --wavelength-nm 587.56
python -m unittest discover -s tests -v
```

`tests/test_phone_modules.py` re-derives every record hash, the evidence and Project hashes, the
comparison verdicts and the f-number from the committed files, and runs without the engine.

## What the records do not claim

- **No MTF, relative illumination or distortion values.** The publications print no MTF and no
  interpretable field-dependent numbers; the records trace chief rays only.
- **No continuous spectral coverage.** The source states one reference wavelength, so
  `continuous_coverage_nm` is `UNCONFIRMED` and the single-sample span is discovery-only.
- **No stop-dependent match.** Every record is eligible for stop-dependent evaluation (the stop
  plate blocks light) but none claims a match, because no pupil, illumination or MTF evidence is
  recorded.
- **No mechanical data.** Clear apertures are derived estimates, not drawings: no flange, barrel,
  filter stack or tolerance is claimed.
- **No production claim.** A published example is a design; the records do not assert that a
  module ships it, nor its yield or cost.

## Deferred and unavailable sources

| Source | Outcome | Reason |
|---|---|---|
| The other 11 examples of the two publications | `DEFERRED` (`VARIANT_OUTSIDE_BATCH`) | The batch already carries a record from the same family with a close focal length and f-number; the example stays available for a later batch. |
| [US11886038B2](https://patents.google.com/patent/US11886038B2/en), [US12271054B2](https://patents.google.com/patent/US12271054B2/en) (Largan) | Not converted | Continuations of the `US10247911B2` family: their examples are the same nine prescriptions. A record is kept once, so the later publications add no design. |
| [US10795123B2](https://patents.google.com/patent/US10795123B2/en) (Largan) | Out of series scope | Five-element wide-angle examples whose total track is roughly eight times the focal length (1.19 mm focal length, 10 mm class track). That ratio is not a phone module, so it belongs to no phone series. |
| [US20180314040A1](https://patents.google.com/patent/US20180314040A1/en) (Genius Electronic Optical) | Not converted | The description renders its numerical tables as images, so the prescription cannot be transcribed without OCR; no numbers were guessed. |
| [US10295800B2](https://patents.google.com/patent/US10295800B2/en) (Ability Enterprise), [US11199682B2](https://patents.google.com/patent/US11199682B2/en) (Tamron) | Not converted | The rendered description carries no readable numerical tables, so neither could be transcribed. |
| Further Largan, AAC, Sunny, Kantatsu and Samsung publications | Not yet inventoried in this batch | Their table layouts differ and each needs a reader; the batch stops at the two publications that could be transcribed and verified end to end. |

The series issue keeps the wider inventory; this batch is one contribution to it, not the whole
series.

## Reproducing the batch

The preparation workspace holds the fetch, the table reader, the surface-table builder, the
paraxial and real-ray checks and the record writer. They are source-specific tooling, kept out of
the corpus on purpose:

```
spec  →  surface_table.csv  →  project.json  →  record.json + evidence.json
```

Each step is deterministic: the same publication, table and example produce the same surface table,
the same Project bytes and the same record hash. The `source_input_sha256` in every record pins the
transcription, and `record_hash` pins the record.
