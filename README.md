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

## The telescope and observation collection

`records/telescope-observation/` holds the second collection: nine classical eyepieces from
MIL-HDBK-141 section 14, one Nikon eyepiece numerical example, and four MIT-licensed sample designs
— refracting telescope objectives and eyepieces. Every record is a coaxial sequential refracting
prescription with a real image plane, because that is what the prescription importer accepts;
reflecting systems, prism erectors and afocal trains are deferred with a reason rather than
approximated.

| | |
|---|---|
| Candidates examined | 88 |
| Accepted records | 14 |
| Deferred, with a reason | 74 |
| Conversion failed | 0 |

[Collection README](records/telescope-observation/README.md) covers the scope, the record table, the
aperture and stop conventions, the validation run and the deferred sources.
[Batch manifest](records/telescope-observation/batch-telescope-observation-1.json) reports one
outcome per candidate.

## Status and contributions

The repository is in setup. The first usable PyPI release is planned to ship the search interface
and a searchable collection together. The seed collection is the first batch of that collection.
[LensLibrary](https://github.com/nzhagen/LensLibrary)

Use [ARCHITECTURE.md](ARCHITECTURE.md) for the design, [AGENTS.md](AGENTS.md) for repository rules,
and [CONTRIBUTING.md](CONTRIBUTING.md) for proposals, single-record contributions and batch intake.
The project uses the [MIT License](LICENSE).

## Data sources and acknowledgments

The initial prescription records are derived from Nathan Hagen's [LensLibrary](https://github.com/nzhagen/LensLibrary), using [revision `86b2c0ca`](https://github.com/nzhagen/LensLibrary/tree/86b2c0cac5a67e2112d58518230c4d8728154f4e). Thanks to Nathan Hagen for compiling and sharing the collection. See the [LensLibrary MIT notice](licenses/LensLibrary-MIT.txt) for the upstream copyright and license. Individual records cite the upstream design and its original publication or patent when available.

The telescope and observation collection draws on MIL-HDBK-141 (a US Government work in the public
domain), on US10527839B2 and on the MIT-licensed [optiland](https://github.com/optiland/optiland)
sample designs. Each record states its own attribution and redistribution basis; the [collection
README](records/telescope-observation/README.md) lists the sources and the exact revision read.

The LensLibrary notice must stay with the converted records in any distribution. The repository's
own [MIT License](LICENSE) covers its code and documentation.