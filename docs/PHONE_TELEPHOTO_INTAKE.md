# Phone telephoto modules, batch 1

This note records how the first telephoto batch was prepared so a reviewer can repeat the
conversion and check every claim. It covers the sources, the transcription rules, the stop and
aperture decisions, the field evidence and what the records leave unconfirmed. The batch belongs to
the series issue [#25](https://github.com/JunLin615/os-optics-lens/issues/25), which coordinates
dedicated phone telephoto modules and treats folded and straight designs as retrieval traits.
Main-camera and ultrawide modules are their own series.

- **Collection:** `phone-telephoto`
- **Batch:** [`batch-phone-telephoto-1.json`](../records/phone-telephoto/batch-phone-telephoto-1.json)
- **Engine:** public `os-optics` **0.14.0**, no catalog release (every material is defined in the
  Project)
- **Format:** `csv-surface-table/1`
- **Records:** 7 accepted, 15 deferred, 0 conversion failures
- **Path:** every record is a **straight** module; no folded design is included

## What the batch contains

| Record | EFL | f-number | Total track | Track / EFL | Full field | Image circle | CRA at edge | Elements |
|---|---|---|---|---|---|---|---|---|
| `patent-us20220299735a1-ex01` | 5.717 | f/2.82 | 5.198 | 0.91 | 42.0° | 4.47 | 28.5° | 5 |
| `patent-us20220299735a1-ex02` | 7.030 | f/2.82 | 6.296 | 0.90 | 34.4° | 4.47 | 22.3° | 5 |
| `patent-us20220299735a1-ex08` | 5.863 | f/2.60 | 5.453 | 0.93 | 41.0° | 4.48 | 23.1° | 5 |
| `patent-us20220299735a1-ex09` | 6.344 | f/2.82 | 5.838 | 0.92 | 49.0° | 5.51 | 31.1° | 5 |
| `patent-us11372203b2-ex01` | 10.077 | f/2.53 | 9.570 | 0.95 | 29.4° | 5.36 | 20.0° | 5 |
| `patent-us11372203b2-ex02` | 8.647 | f/2.40 | 8.558 | 0.99 | 32.0° | 5.20 | 22.8° | 5 |
| `patent-us11372203b2-ex09` | 9.004 | f/2.25 | 9.269 | 1.03 | 31.2° | 5.27 | 22.8° | 5 |

All lengths are millimetres. EFL, total track, image circle and CRA come from the committed Project;
the f-number and the field are the publication's printed values.

The two families cover the two telephoto classes a phone uses: a **short** group at
`5.7 mm … 7.0 mm` focal length and `f/2.6 … f/2.8`, and a **long** group at `8.6 mm … 10.1 mm` and
`f/2.25 … f/2.53`. Every record has a track/EFL ratio below 1.05, which is what makes the design a
telephoto rather than a general camera lens; image circles span `4.5 mm … 5.5 mm`.

## Sources

| Publication | Assignee | Examples | Used here |
|---|---|---|---|
| [US20220299735A1](https://patents.google.com/patent/US20220299735A1/en), *Imaging lens system, image capturing device and electronic device* | Largan Precision Co., Ltd. | 10 | 4 |
| [US11372203B2](https://patents.google.com/patent/US11372203B2/en), *Optical imaging lens system, image capturing unit and electronic device* | Largan Precision Co., Ltd. | 12 | 3 |

Each record names the tables it came from (`Table 1` surface data, `Table 2` aspheric coefficients)
and the embodiment. The publications are granted US patents: the numerical examples are a public
record, and the patent document itself is not redistributed. The transcription, the native Project
and the evidence extract are MIT.

A numerical example is a **published design**, not a measured product. Nothing in the batch claims
that a shipped module uses it.

## Conversion method

The method is the one the main-camera and ultrawide batch documents, with the differences this
series needs:

1. **Read the publication** as text and split it into table blocks. In these two publications the
   data and asphere tables are not strictly alternating — a conditions table sits between some
   embodiments — so each surface table is paired with the next asphere table rather than by number.
2. **Transcribe** `radius`, `thickness`, `nd`, `Vd`, `k` and `A4 … A18` verbatim; a `Plano` radius
   becomes a plane. No radius is re-signed, no thickness re-spaced.
3. **Import** with the engine's own importer, which does the element and stop decomposition and the
   edge and solid checks.
4. **Assemble the Project**: one `COMPOUND` unit, an on-axis source at infinity, one observation
   plane at the published image distance.
5. **Check** with `project check` and `project solids`, and **verify** with the engine's thick-lens
   paraxial matrix at the reference wavelength.

The reference wavelength is the d-line, printed as 587.6 nm. That is an air wavelength, so it is
converted once with the engine's own air model to **587.720064 nm vacuum**; the record keeps both
values (`sampling_wavelengths_nm`, `sampling_wavelengths_air_nm`), and the conversion is stated in
`sampling_wavelengths_basis`.

### The stop, and the examples that were deferred for it

These designs put the aperture stop in front of the first element, at a **negative** standoff
(`−0.550 mm` and `−0.808 mm` in two examples). A surface table carries positive spacings only, so
the stop plane sits 0.05 mm in front of the first surface and the record carries
`STOP_STANDOFF_ADJUSTED` with the printed value. The stop shift changes the pupil position slightly;
the first-order layout is unchanged and the record says so.

Two examples of `US11372203B2` (the 7th and the 12th) carry **two** aperture stops — one in front of
the first element and one inside the stack. The intake models one system stop, and the second
aperture's diameter cannot be placed without guessing it, so both are deferred with `MULTI_STOP`
rather than half-modelled.

### The paraxial rule for this collection

```
|engine − source| ≤ atol + rtol · |source|
atol = 0.005 mm,  rtol = 5 × 10⁻³
```

`atol` covers the two-decimal focal length; `rtol` covers the prescription printed to three decimals
in radius, thickness and index — about 0.3 % on EFL for a five-element plastic design — together
with the engine's air-referenced index convention (about 0.13 %). The largest measured deviation in
the batch is 0.4 % (`patent-us20220299735a1-ex08`, 5.863 mm against the printed 5.84 mm), and the
tightest record uses 68 % of its allowance. The rule is wider than the one the LensLibrary batch
uses because a patent prints rounded numbers, not a full-precision design file.

## Focus configuration

Every record is `focus: "FIXED_AT_INFINITY"`: the publications tabulate one object distance
(infinity) and one image plane, and none identifies the moving group of an autofocus actuator. The
record states that rather than inventing a macro or finite-conjugate configuration. A focus variant
would be a new configuration once a source documents it.

## Folded designs

None of the accepted records is folded, and `design.folded` is `false` on each. Periscope modules
put a prism or mirror in front of the lens, and the surface-table format refuses reflecting rows in
a sequence — the same limitation that deferred sixteen reflecting designs in the LensLibrary batch
([os-optics#57](https://github.com/JunLin615/os-optics/issues/57)). A folded module therefore needs
either a separate component for the prism or an engine change; until then this series records the
straight half and states the boundary.

## Verification

Four outcomes are tracked separately, and a record is accepted only when all four hold. `paraxial`
is scoped to the effective focal length: the publications print no back focal length, so that
quantity is `UNCONFIRMED` in the comparison.

| Check | Result |
|---|---|
| Conversion (engine importer) | 7 of 7 accepted |
| Native Project check (`project check`) | 7 of 7 `ACCEPTED` |
| Optical solids (`project solids`) | 7 of 7 `VALID` |
| Paraxial EFL against the printed focal length | 7 of 7 within the rule; at most 68 % of the allowance |

Reviewer commands, from the repository root:

```console
os-optics project check records/phone-telephoto/patent-us11372203b2-ex01/project.json
os-optics project solids records/phone-telephoto/patent-us11372203b2-ex01/project.json
os-optics project paraxial records/phone-telephoto/patent-us11372203b2-ex01/project.json \
    --components LENS --wavelength-nm 587.720064
python -m unittest discover -s tests -v
```

`tests/test_phone_telephoto.py` re-derives every record hash, the prescription hash from the
committed extract text, the evidence and Project hashes, the comparison verdict and the cross-file
consistency, and runs without the engine.

## What the records do not claim

- **No MTF, relative illumination or distortion values.** The publications print curves, not tables
  of numbers under stated conditions, so the records trace chief rays only.
- **No continuous spectral coverage.** One reference wavelength; the span is discovery-only.
- **No stop-dependent match.** Every record is eligible for stop-dependent evaluation but none
  claims a match.
- **No autofocus or macro configuration.** One object distance, stated.
- **No mechanical data.** Clear apertures are derived from the traced beam with a mechanical
  allowance and capped where the aspheric polynomial stops being usable; they are estimates.
- **No folded path.** Straight modules only.

## Deferred and unavailable sources

| Source | Outcome | Reason |
|---|---|---|
| 13 further examples of the two publications | `DEFERRED` (`VARIANT_OUTSIDE_BATCH`) | The batch already carries a record from the same family with a close focal length and f-number. |
| `US11372203B2` examples 7 and 12 | `DEFERRED` (`MULTI_STOP`) | Two aperture stops; the second opening cannot be placed without guessing. |
| [US20210041674A1](https://patents.google.com/patent/US20210041674A1/en) | Out of series scope | Four-element f/1.5 examples at 42° half field: a main-camera design, which belongs to the main-camera series. |
| [US11953659B2](https://patents.google.com/patent/US11953659B2/en), [US12259524B2](https://patents.google.com/patent/US12259524B2/en) (Corephotonics) | Not converted | The rendered description carries no readable numerical tables. |
| `TWI689748B` | Not converted | No readable numerical tables in the rendered description. |
| `CN114063268B` | Not converted | Table headers are Chinese; the reader that expects the English layout cannot transcribe it. |
| Folded periscope publications | Out of scope for this batch | A prism or mirror in the sequence is refused by the format; see [os-optics#57](https://github.com/JunLin615/os-optics/issues/57). |

The series issue keeps the wider inventory; this batch is one contribution to it.

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
