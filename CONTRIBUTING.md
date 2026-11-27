# Contributing

## Submit a native Project

For a single prescription, submit the editable `os-optics` Project and a small record with its identity and direct provenance. For example, a contributor named Example Lab could submit an original design as follows.

```text
records/example-lab/example-lab-doublet/
  project.json   Native Project with the geometry, materials and configurations needed to open it
  record.json    ID example-lab-doublet, revision 1, source Example Lab, attribution and redistribution terms
```

Include the Project path, the `os-optics` version used to check it and the hashes defined in the [record format](docs/RECORD_FORMAT.md#record-identity). For a library conversion, name the library, input and revision when available. For a direct transcription, name the publication and example. Include any required license notice. Optional classification can use the [optical search vocabulary](SEARCH_VOCABULARY.md).

**Lens takes search metrics from the committed Project and calculations on it.** Submit the Project without transcribing optical numbers into metadata. Leave unsupported metrics absent. If you include an optional Project analysis, give its configuration, units and calculation conditions. Comparisons with printed or upstream numbers are optional transcription evidence for the contribution discussion. A source match is not an admission requirement. Keep source files and source-specific conversion scripts outside this repository.

Run the native Project check from the repository root, substituting your record path.

```console
os-optics project check records/example-lab/example-lab-doublet/project.json
```

Use the engine version stated for the Project. Look for `ACCEPTED` and a `VALID` optical-solids result where applicable. For a Project with configurations, check that each submitted configuration passes in the report.

## Open a pull request

A single record or correction can come directly in a focused pull request. Describe the intended change and list the checks you ran. For a new collection, bulk import, or change to the record format or retrieval interface, first check the issue tracker and use the relevant issue to coordinate the scope.

The contribution workflow is designed for CI to decide routine data-only submissions, with maintainer review for changes to the retrieval code, record contract or validation rules. While repository CI is being set up, report the native check result in the data PR for the maintainer. A draft data PR can show a representative Project when a format or validation change is under discussion.

## Prepare a collection or batch

- Propose a collection identity, identify its maintainers and pin the source revision or edition where possible. Describe how source record IDs map to contributed records and how future updates can be tracked.
- In the PR or series issue, summarize the inputs, submitted records and any deferrals or failures. Split large submissions into independently checkable batches.
- Review existing records for duplicates. Keep the positions of one design in the same Project when native configurations can represent them. Retain distinct prescriptions where their optical parameters or structure make them useful, and group related designs by family.

Project code and documentation use the [MIT License](LICENSE). Imported records retain their applicable attribution and license or permission.
