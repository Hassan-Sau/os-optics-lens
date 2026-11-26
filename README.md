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

## Canon full-frame photography lenses

`records/canon-full-frame/` extends the library from Zemax exchange files to prescriptions
transcribed from published patent numerical examples: Canon full-frame photography lenses, from a
24.74 mm f/1.24 ultra-wide prime to an 814.8 mm f/5.88 super-telephoto, with zoom ends and aspheric
designs among them. Each record cites its publication, the example it transcribes and the
configuration, and carries the transcribed prescription as evidence beside the native Project.

| | |
|---|---|
| Candidate inventory | 227 full-frame examples in 37 publications, screened from 629 examples in 54 publications |
| Inputs considered | 31 published numerical examples |
| Accepted records | 18 |
| Deferred, with a reason | 5 |
| Conversion failed | 8 |

[Intake of the Canon full-frame collection](docs/CANON_FULL_FRAME_INTAKE.md) records the inventory,
the selection, the glass and aperture models, the field evidence, the verification run and the open
work — including the three wide-angle examples whose printed half field does not reproduce their
printed image height, and the reflective and odd-order-asphere systems this format cannot represent.

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

## Status and contributions

The repository is in setup. The first usable PyPI release is planned to ship the search interface
and a searchable collection together. The seed collection is the first batch of that collection.
[LensLibrary](https://github.com/nzhagen/LensLibrary)

Use [ARCHITECTURE.md](ARCHITECTURE.md) for the design, [AGENTS.md](AGENTS.md) for repository rules,
and [CONTRIBUTING.md](CONTRIBUTING.md) for proposals, single-record contributions and batch intake.
The project uses the [MIT License](LICENSE).

## Data sources and acknowledgments

The initial prescription records are derived from Nathan Hagen's [LensLibrary](https://github.com/nzhagen/LensLibrary), using [revision `86b2c0ca`](https://github.com/nzhagen/LensLibrary/tree/86b2c0cac5a67e2112d58518230c4d8728154f4e). Thanks to Nathan Hagen for compiling and sharing the collection. See the [LensLibrary MIT notice](licenses/LensLibrary-MIT.txt) for the upstream copyright and license. Individual records cite the upstream design and its original publication or patent when available.

The LensLibrary notice must stay with the converted records in any distribution. The repository's
own [MIT License](LICENSE) covers its code and documentation.