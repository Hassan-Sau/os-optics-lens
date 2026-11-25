# Prescription library architecture

An agent searches by optical requirements, inspects a small set of candidates, then retrieves a native `os-optics` Project to open, check, edit or evaluate. The library also supports finding a reference structure, such as a lens group to adapt within a different design. The repository layout, index, retrieval interface and documentation serve these agent workflows.

## Records and index

- Keep one native Project per design record, with compact metadata for search and provenance. A Project can contain multiple configurations. Keep the material references and surface models needed to interpret it.
- Give the record a stable ID, a traceable revision and a design family where known. Retain the source reference, attribution and redistribution basis. Record whether a value came from the source, a derivation or an engine calculation, with its conditions and validation state.
- Generate the search index from independently editable records. Bundle the index, collection and retriever in the first usable PyPI release for local queries after installation. An embedded SQLite index is the initial storage option for facets, ranges and sorting. Keep the source records independent of the index backend.
- Index configuration-specific values against the configuration that produced them. A query with several hard constraints must find them together in the same configuration. Keep detailed performance samples accessible on demand.

## Classification and search fields

Use independent facets to narrow candidates and typed fields to compare them. A prescription may have multiple optical functions, applications and structural traits. Keep family membership separate so an agent can search across families or inspect variants of one design.

Assign a controlled term when a source statement, native Project property or documented contributor observation supports it. Keep optional facets sparse. Prefer a query alias when a new phrase means the same thing as an existing term. Add a term when it identifies a useful group of records or helps an agent choose the right search fields. See [Optical search vocabulary](SEARCH_VOCABULARY.md) for first-pass terms, candidate terms and source mappings.

| Area | Search fields and interpretation |
| --- | --- |
| Design scope | Complete system, lens group or singlet. This lets a system search and a component search use the same collection. |
| Spectral band | Facets for visible, near-infrared, ultraviolet, extreme ultraviolet, mid-wave infrared and long-wave infrared, using documented band definitions. Store the design wavelength range and any sampling wavelengths separately. Filter on the numeric interval when the brief requires specific coverage. |
| Image format | Full frame and APS-C are discovery facets. Store the image-circle diameter and the image or sensor dimensions when known. Use actual dimensions for coverage checks because APS-C sizes vary. A 36 × 24 mm frame requires about a 43.3 mm image circle for geometric coverage. Use field-dependent results to assess edge image quality. |
| Optical function | The task performed, such as imaging, illumination, collimation or spectral dispersion. |
| Design type | The kind of prescription, such as a microscope objective, projection lens, condenser or spectrometer. |
| Application | A documented use, such as microscopy, machine vision, endoscopy or projection display. |
| Structure | A supported layout or optical property, such as zoom, catadioptric, cemented or image-space telecentric. |
| First-order properties and size | Record effective focal length, back focal length, f-number, clear aperture and total length with units, definitions and applicable configuration. Identify the conjugate and f-number convention where relevant. State the endpoints and measurement convention for total length, especially for folded designs. |
| MTF | Record spatial frequency and units, field position, wavelength or spectral weighting, and sagittal or tangential direction where applicable. Compare values under matching conditions. |
| Chief ray angle and distortion | For CRA, record the image-plane field position and angle convention. For distortion, record the field position, the reference projection and the sign or absolute-value convention. |

Prioritize wavelength range and configuration, with image circle, effective focal length, f-number, total length and back focal length for the initial imaging records. Expose optional task-specific fields where records support them. For example, a microscope objective can supply object-side NA and working distance. Illumination can supply source and target conditions and output distribution. Attach each value to its configuration and, where relevant, its optical path or output. Keep missing or inapplicable values explicit when requested. Use MTF, CRA, distortion and other condition-specific quantities for general ranking once the collection contains comparable data.

## Collection scope

- Start with complete optical systems, alongside a small set of representative singlets and lens groups with clear design reuse value. A singlet may contribute a useful aspheric form or a documented operating condition. A cemented doublet may provide a material pairing, interface geometry and correction strategy that another design can reuse.
- Treat focal length as a search value. Choose representative structures and meaningful variants for the library. Route selection by stock focal length, diameter or part number to the optical component catalog.
- Preserve coatings that are part of a design as native surface properties. Record wavelength, incidence angle, polarization and source where needed to interpret their optical effect. Catalog part selection remains the route for purchasing finished coated optics.
- Index the properties each record can support. Image circle, CRA and edge MTF require a defined image plane and field conditions. A group or singlet with no such conditions can still be found by structure and the first-order properties it supplies.

## Retrieval behavior

- For discovery, expose a bounded list of facet values present in the current collection or query scope, with record counts. After a type or function is selected, surface the applicable numerical fields and relevant conditions. Keep the full vocabulary and detailed field definitions available on demand.
- Resolve aliases to canonical terms. Intersect filters across facets and allow the caller to request alternatives within a facet. Check each label and numerical fact at the scope where it applies. For a projector with an illuminator and an imaging path, an illumination uniformity constraint applies to the requested illumination output.
- **Specification search** applies the requested constraints to comparable values. An unknown value leaves a requirement unconfirmed. Report the conditions and evidence behind the matches.
- **Starting-point search** can include near matches. Distinguish fixed requirements from flexible targets and show the differences that affect selection. For example, a 27 mm design can be a useful candidate for a 24 mm brief if its image circle and back focus are close and focal length is flexible.
- Return a bounded shortlist with record IDs, configurations, selected optical facts, gaps and missing values. When the agent is exploring structures, show representative matches across families and make family variants available on demand. Let the agent expand selected fields, surfaces or groups, then fetch an editable Project by ID and revision. Agents with a known ID can fetch it directly. Bound total batch output and make additional results available from the same index snapshot.

This document establishes the architecture and field semantics. Record layouts, exact band boundaries, database schema and command syntax are implementation decisions to be documented with the first usable package.
