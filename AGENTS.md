# Repository rules for agents

## Purpose

Help an agent find a usable optical design starting point or reference structure and continue work with a native `os-optics` Project. Optimize the repository layout, index, retrieval, help and contribution path for agent use. Spend context on the optical facts and operations needed for the next decision.

## Corpus and evidence

- The native `os-optics` Project is the authoritative prescription. Preserve geometry, units, configuration relationships and the material records or references needed to interpret it. Use the engine's native representation for each.
- Record only the metadata needed for discovery, comparison, compatibility and provenance. Name the units, conditions and meaning of indexed quantities. A half-field angle, a full-field angle and an object-space field size are different quantities.
- Identify source-stated, derived and engine-computed values. Record the basis and validation state. A missing value leaves a constraint unconfirmed. Track conversion, successful opening and optical validation as separate outcomes.
- Give records a stable identity and traceable revision. Preserve meaningful variants and identify the design family when known. Keep source identifiers, upstream revision or edition when available, attribution and the basis for redistribution.
- Keep PDFs, raw exchange files, duplicate prescription exports, screenshots, renderings and 3D assets out of the corpus. Cite upstream resources and pinpoint the original design where possible. For example, cite the patent publication and the example or table that supplied the prescription.

## Retrieval requirements for the future package

- Ship a searchable collection and the retriever together. After installation, queries should run locally with the package's index and data. Use an index that can be generated from the source records. Keep each record independently maintainable so contributors can work in parallel.
- Return compact, structured summaries by default. Support narrowing the query, comparing a short list and inspecting selected fields, surfaces or configurations before fetching the full Project. Allow direct retrieval by record ID and include the resolved revision in the result.
- Let the agent distinguish confirmed constraints from preferences, shortfalls and unknowns. Expose enough evidence to tell a prescription that meets a requirement from a promising starting point for refinement.
- Bound total output for a multi-query request as well as output for a single query. Provide deterministic ordering within a collection snapshot and a way to continue through omitted results. Keep details accessible on demand.
- Retrieval hands off an editable native Project. `os-optics` evaluates it. `os-optics-kit` can teach or apply the relevant downstream workflows.

## Changes

Use English by default for repository documentation, agent-facing text, issues and pull requests. Preserve source titles and original identifiers in citations.

Follow the architecture and field semantics in [ARCHITECTURE.md](ARCHITECTURE.md) and the workflow in [CONTRIBUTING.md](CONTRIBUTING.md). Use a focused pull request linked to the relevant issue when one exists. Keep shared decisions in issues or repository rules so later contributors can find them.
