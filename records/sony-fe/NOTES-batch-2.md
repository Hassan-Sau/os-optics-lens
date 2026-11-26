# Batch 2: two 50 mm-class Sony families, and the sweep behind them

Two Sony-assigned full-frame families, transcribed from the numerical examples of
[US20190004278A1](https://patents.google.com/patent/US20190004278A1/en) and
[US9491348B2](https://patents.google.com/patent/US9491348B2/en). Both are normal-angle designs
around 50 mm at a large aperture; the first is the f/1.4 class, the second the f/1.8 class.

| Publication | Examples | Records | Printed f (mm) | Printed F | Derived image circle (mm) |
| --- | --- | --- | --- | --- | --- |
| US20190004278A1 | 6 | 5 accepted, 1 deferred | 50.29–51.54 | 1.45–1.48 | 42.8–43.8 |
| US9491348B2 | 11 | 10 accepted, 1 deferred | 46.19–55.01 | 1.80–1.88 | 43.0–43.9 |

Neither publication prints an image height. The image circle in each record is therefore `DERIVED`
as `2 f tan(omega)` from the printed focal length and half field angle, and a record claims the
full-frame facet only where that diameter lands on the 43.27 mm diagonal of a 36 × 24 mm frame. The
derivation is stated in `image_format.basis` and the angle itself is kept as `SOURCE_STATED` in
`field`.

## The comparison rule and what it produced

The rule is the one the patent-derived `phone-modules` batch established and batch 1 applied:
`atol = 0.005 mm`, `rtol = 0.003`, covering the printed rounding and the engine's air-referenced
index convention. Across the fifteen accepted records the engine sits 0.04–0.44 of the allowance
from the printed focal length — 0.013 % to 0.14 % in relative terms, all of it in the direction the
constant-index model predicts.

Nothing was tightened or relaxed per example: the same script, the same rule, and the achieved
fraction recorded in each record.

## Two deferrals inside this batch

| Input | Reason code | Why |
| --- | --- | --- |
| US20190004278A1 example 6 | `IMAGE_FORMAT_OUTSIDE_COLLECTION_SCOPE` | 82.55 mm at a 23.61° half field gives a 72.2 mm image circle, twice the full-frame diagonal: a larger-format design. |
| US9491348B2 example 5 | `SOURCE_TABLE_INCONSISTENT` | Surface 5 prints `nd = 1.290300` against `vd = 54.0`. No catalogue glass sits below about 1.4 at the d-line, and with the printed value the system is divergent (paraxial EFL −3775.6 mm against a printed 53.45 mm). |

The first is a scope decision, not a defect: the example is well-formed and simply not a 36 × 24 mm
lens. The second is a transcription the publication cannot support, so no Project is committed for
it; a reviewer can read surface 5 of that example directly.

## One printed zero gap

`US9491348B2` example 11 prints a 0.000 mm gap after surface 13, between two glass bodies. The
importer requires a positive thickness, so the Project carries 1e-6 mm there and the record states
`ZERO_GAP_SUBSTITUTED` with the printed value. The effect is below a nanometre; the alternative —
dropping a surface — would have changed the design.

## What the sweep examined, and why the other publications are not here

Twenty-two Sony publications surfaced in the search for full-frame photography lenses. Two became
this batch, one was batch 1, and the rest are accounted for below. The dispositions are the
outcome of reading each publication's tables, not of a title match.

| Publication | Examples | Disposition | Reason code |
| --- | --- | --- | --- |
| US20240061211A1 | 5 | batch 1, 4 records | — |
| US20190004278A1 | 6 | 5 records | — |
| US9491348B2 | 11 | 10 records | — |
| US20200026047A1 | 9 | none | `ENGINE_DISAGREES_BEYOND_TOLERANCE` |
| US20190369371A1 | 5 | none | `ZOOM_MULTI_CONFIGURATION` |
| US20150077859A1 | 4 | none | `ZOOM_MULTI_CONFIGURATION` |
| US10877251B2 | 7 | none | `NO_FIRST_ORDER_DATA` |
| US10838178B2 | 12 | none | `NO_FIRST_ORDER_DATA` |
| US10302918B2 | 5 | none | `NO_FIRST_ORDER_DATA` |
| US9274308B2 | 6 | none | `NO_FIRST_ORDER_DATA` |
| US9804358B2 | 7 | none | `NO_FIRST_ORDER_DATA` |
| US9638892B2 | 1 | none | `NOT_A_COMPLETE_SYSTEM` |
| US10025074B2, US10191254B2, US10491825B2, US9042030B2, US10823942B2, US20190049700A1, US20200319430A1, US20210396955A1 | — | none | `LAYOUT_NOT_READ` |
| WO2020213337A1 | 5 | none | `TABLE_IS_IMAGE` |

What each code means here:

- **`ENGINE_DISAGREES_BEYOND_TOLERANCE`** — US20200026047A1 is a 388/485/582 mm telephoto family
  (nine examples, image circles 21.1–21.3 mm half height, i.e. full frame). Its printed group focal
  lengths reproduce within 0.41 %, but the compound sits 0.49–1.44 % above the printed focal length,
  outside the rule. The gap is systematic and grows with focal length, so the transcription is not
  obviously at fault and the engine's composition of a long, widely spaced system is not obviously
  at fault either. Nothing is claimed until that is separated.
- **`ZOOM_MULTI_CONFIGURATION`** — both publications print one table per zoom position (16.5–33.9 mm
  and 28.8–72.7 mm). The collection has no zoom record and a single-state Project would misrepresent
  a zoom, so they wait for a multi-configuration layout rather than being flattened into one state.
- **`NO_FIRST_ORDER_DATA`** — the surface tables parse, but the publications print no `f`, `Fno`,
  `omega` or image-height block tied to an example, so the design cannot be placed in a format from
  the publication alone. Their tracks are 5–22 mm, which is consistent with small-format designs,
  but "consistent with" is not a basis and so no format is claimed.
- **`NOT_A_COMPLETE_SYSTEM`** — US9638892B2 is a rear conversion lens: a group, not a camera lens.
- **`LAYOUT_NOT_READ`** — the page carries numeric tables (11 to 43 of them) but not in the labelled
  block form this reader keys on. They were not inspected by hand either, so no claim is made about
  their format.
- **`TABLE_IS_IMAGE`** — every numerical table in WO2020213337A1 is a page image
  (`JPOXMLDOC01-appb-T000001..026.png`); the publication PDF has no text layer (`pdftotext` returns
  97 bytes) and the CN and JP family members are the same. OCR of the bilevel scans does not hold:
  after deskew and table-rule removal, tesseract returns character soup on the surface table. Digits
  that cannot be read verbatim are not put into the corpus, and the engine's focal-length check only
  catches aggregate error, not a wrong digit in a weak surface. This family needs a per-cell
  extraction with confidence, or a double-keyed read, before it can be a batch.

## What these records are not

- **Not product reproductions.** Neither publication names a product.
- **Not chromatic models.** Only `nd` and `vd` are printed, so every element is a constant index at
  the reference wavelength.
- **Not stop-resolved.** No semi-diameters are printed; one uniform clear semi-diameter is used (13 mm,
  or 11 mm for US9491348B2 example 6, where 13 mm made two neighbouring surfaces intersect inside the
  clear aperture). `design.aperture_validity` is `STOP_NOT_BLOCKING` in every record, and
  stop-dependent queries stay unconfirmed.
- **One focus state.** Each Project is the infinity-focus state; the printed gaps for the closer
  conjugates stay in `evidence.json`.
