# Contributing

Individuals, research groups and companies can contribute a single optical prescription, a related design family or an independently maintainable collection. Agents can help prepare and check submissions. The contributor is responsible for the content and evidence in the pull request.

## Coordinate the work

1. Search the issue tracker for the collection, design family or tool change. Join an existing discussion when one covers the work. Open an issue for a new collection, bulk import, or change to the record format or retrieval interface. Include the scope, source, expected coverage and how the result can be checked.
2. Fork the repository and work on a focused branch. A single record or correction using an agreed format can come in a pull request directly. For a collection or bulk import, use its issue to agree on how to partition the work and avoid duplicate conversions.
3. Open a pull request with the intended change, related issue if any, and the checks run. Respond to review in the pull request. Maintainers review and merge into `main`.

During repository setup, contributors can open a draft data pull request to review representative native Projects alongside the proposed format and validation procedure. If a format proposal is already under review, link it and identify any fields or checks the new records need. Before merge, align the submission with the accepted record format and validation procedure.

## Prepare a prescription

- Supply the editable native `os-optics` Project with the material and configuration information it needs. Record the engine version used to check it.
- Supply the search facts relevant to the design, with units, conditions and their source or calculation basis. Use the [optical search vocabulary](SEARCH_VOCABULARY.md) to assign supported labels and propose new terms with a source record or a concrete search task. Record any substitutions or assumptions that affect the interpretation. Mark unknown values and state what was actually checked.
- Give a precise source reference and identify the design within it. Include the attribution and applicable license or other redistribution permission. For an original design, identify its contributor and confirm the terms for publishing it. Keep source files upstream and link to them.
- Report the checks you ran, starting with opening the Project in `os-optics`. Record relevant comparisons if you ran optical validation. If conversion fails, attach the failure details to the intake issue so the blocker is visible without adding an incomplete prescription to the corpus.

## Prepare a collection or batch

- Propose a collection identity, identify its maintainers and pin the source revision or edition where possible. Describe how source record IDs map to contributed records and how future updates can be tracked.
- Record the input count, successful conversions and pending or failed conversions, with reasons. Keep material substitutions and optical validation distinct from conversion status. Split large submissions into independently checkable batches.
- Review existing records for duplicates. Identify related designs and retain distinct variants when their optical parameters or structure make them useful. Let the shared index be generated from the individual records.

Project code and documentation use the [MIT License](LICENSE). Imported records retain their applicable attribution and license or permission. Reviewers check that the submitted files fit the corpus boundary, the source and redistribution basis are recorded, and the evidence supports each claimed result.
