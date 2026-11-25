# os-optics-lens

A planned library of optical prescriptions for AI agents. An agent uses an optical design brief to find candidate prescriptions, inspects a few relevant properties or structural details, and retrieves a native Project to continue design in `os-optics`.

## Project rules

- Design the library, index, retriever and documentation for agents with limited context. Return compact candidate summaries and load details on demand.
- Keep the corpus to native `os-optics` Projects and the metadata needed to search and cite them. Link to original sources. Keep PDFs, exchange files, images and 3D assets outside the corpus.
- Keep a specification match and a promising optimization starting point distinguishable in search results. The agent chooses which candidate to use and verifies it against its brief.

`os-optics` owns the native model and optical evaluation. `os-optics-lens` will own the prescription collection and its installed retrieval interface. `os-optics-kit` provides agent skills, study tools and worked cases. [Engine](https://github.com/JunLin615/os-optics) · [Kit](https://github.com/JunLin615/os-optics-kit)

## Status and contributions

The repository is in setup. The first usable PyPI release is planned to ship the search interface and a searchable collection together. The proposed seed is a batch conversion of supported LensLibrary prescriptions with their source records, attribution and conversion outcomes. [LensLibrary](https://github.com/nzhagen/LensLibrary)

Use [ARCHITECTURE.md](ARCHITECTURE.md) for the design, [AGENTS.md](AGENTS.md) for repository rules, and [CONTRIBUTING.md](CONTRIBUTING.md) for proposals, single-record contributions and batch intake. The project uses the [MIT License](LICENSE).
