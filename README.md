# os-optics-lens

A planned library of optical prescriptions for AI agents. An agent uses an optical design brief to find candidate prescriptions, inspects a few relevant properties or structural details, and retrieves a native Project to continue design in `os-optics`.

## Project rules

- Design the library, index, retriever and documentation for agents with limited context. Return compact candidate summaries and load details on demand.
- Keep the corpus to native `os-optics` Projects and the metadata needed to search and cite them. Link to original sources. Keep PDFs, exchange files, images and 3D assets outside the corpus.
- Keep a specification match and a promising optimization starting point distinguishable in search results. The agent chooses which candidate to use and verifies it against its brief.

`os-optics` owns the native model and optical evaluation. `os-optics-lens` will own the prescription collection and its installed retrieval interface. `os-optics-kit` provides agent skills, study tools and worked cases. [Engine](https://github.com/JunLin615/os-optics) · [Kit](https://github.com/JunLin615/os-optics-kit)

## The seed collection

`records/lenslibrary/` holds the first records: native `os-optics` Projects converted from
Nathan Hagen's LensLibrary at a pinned revision. Each record directory holds the Project and a
`record.json` with the search facts, their basis and the provenance. The batch outcome manifest
reports an outcome for every source input.

| | |
|---|---|
| Source inputs | 77 ZMX files at revision `86b2c0ca` |
| Accepted records | 39 |
| Deferred, with a reason | 32 |
| Conversion failed | 6 |

Read the Project directly, or start from a record:

```
os-optics project check records/lenslibrary/lenslibrary-528155/project.json
os-optics project solids records/lenslibrary/lenslibrary-528155/project.json
os-optics project paraxial records/lenslibrary/lenslibrary-528155/project.json \
    --components LENS --wavelength-nm 587.7220645720764
```

[Record layout and field semantics](docs/RECORD_FORMAT.md) defines the metadata.
[Importing the LensLibrary seed collection](docs/LENSLIBRARY_IMPORT.md) records the conversion
method, the material and surface decisions, the verification run and the known limits.

### Spectral band boundaries

`band_facets` in a record uses these boundaries, in vacuum nanometres:

| Facet | Interval (nm) |
|---|---|
| `extreme_ultraviolet` | 0.1 – 10 |
| `ultraviolet` | 10 – 380 |
| `visible` | 380 – 780 |
| `near_infrared` | 780 – 3000 |
| `mid_wave_infrared` | 3000 – 8000 |
| `long_wave_infrared` | 8000 – 15000 |

A facet is a **discovery** label derived from the record's sampling span. It never asserts that the
design is usable across the interval: a record's `spectrum.continuous_coverage_nm` is `UNCONFIRMED`
unless the source states a range, so only established continuous coverage can satisfy a hard band
constraint.

## Search the collection

The `os-optics-lens` package ships the retriever together with a prebuilt index and the
collection it indexes. Queries run locally, using only the Python standard library (Python 3.10
or newer). Every command prints one bounded JSON document.

```
pip install os-optics-lens
os-optics-lens help quickstart
```

From brief to an editable Project:

```
os-optics-lens facets --facet design_type --facet image_format
os-optics-lens fields --fact image_format.image_circle_diameter_mm
os-optics-lens search --mode specification --filter design_type=camera_lens \
  --where 'first_order.effective_focal_length_mm between_inclusive [17.1,18.9]' \
  --where 'image_format.image_circle_diameter_mm gte 43.27'
os-optics-lens project yutong-2025-mirrorless-18-p2b --out work/p2b.project.json
```

- **Specification search** reports each hard constraint as `MATCH`, `DOES_NOT_MATCH` or
  `UNCONFIRMED`, with a reason code for each unknown.
- **Starting-point search** (`--mode starting_point --target FACT=VALUE~TOL`) ranks near matches
  and lists their shortfalls and unknowns.
- `compare` and `inspect` load details on demand.
- `project --out` writes the exact native Project bytes. Their SHA-256 equals the record's
  `native_project.sha256`.

On Windows PowerShell, pass JSON requests with `--request FILE`. Outside an installed wheel,
build an index from a checkout with `os-optics-lens index build --corpus . --out
build/os-optics-lens-index.sqlite`, then pass `--index` to each command.
[Retrieval](docs/RETRIEVAL.md) documents installation, the request and response formats, the
search semantics, the error codes and how to rebuild the index.
[Index schema](docs/INDEX_SCHEMA.md) documents the index tables and build findings.

## Status and contributions

The first package ships the search interface and the searchable collection together. The seed
collection is the first batch of that collection, and new series are added as further batches.
[LensLibrary](https://github.com/nzhagen/LensLibrary)

Use [ARCHITECTURE.md](ARCHITECTURE.md) for the design, [AGENTS.md](AGENTS.md) for repository rules,
and [CONTRIBUTING.md](CONTRIBUTING.md) for proposals, single-record contributions and batch intake.
The project uses the [MIT License](LICENSE).

## Data sources and acknowledgments

The initial prescription records are derived from Nathan Hagen's [LensLibrary](https://github.com/nzhagen/LensLibrary), using [revision `86b2c0ca`](https://github.com/nzhagen/LensLibrary/tree/86b2c0cac5a67e2112d58518230c4d8728154f4e). Thanks to Nathan Hagen for compiling and sharing the collection. See the [LensLibrary MIT notice](licenses/LensLibrary-MIT.txt) for the upstream copyright and license. Individual records cite the upstream design and its original publication or patent when available.

The LensLibrary notice must stay with the converted records in any distribution. The repository's
own [MIT License](LICENSE) covers its code and documentation.