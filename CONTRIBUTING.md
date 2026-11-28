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

Run the same intake check as CI from the repository root. Stage or commit new files before comparing against a base branch.

```console
python -m pip install os-optics==0.14.0
python scripts/check_intake.py --base origin/main --output intake-report.json
```

The check validates the collection's record, Project and evidence references, then opens each affected Project and checks all its native configurations. For supported single-lens configurations, the report contains EFL and BFL recomputed at the native vacuum wavelengths. For those configurations, the check verifies indexable `ENGINE_COMPUTED` EFL and BFL against its results. Leave unsupported metrics absent. Run without `--base` to check all Projects.

### Model and check aperture

When a source gives an f-number, use it to model the stop and clear apertures of the relevant native configuration. Account for pupil magnification and any surface that limits the admitted cone. Keep the printed number as a `SOURCE_STATED` `aperture.nominal_f_number`, with its convention and conditions when known.

For each new or revised Project with a nominal f-number, use the intake report's `paraxial_aperture.samples`. Copy one applicable sample's `data` object under its named aperture field in the matching configuration. Use the relevant native vacuum wavelength. The checker recomputes the value from the submitted Project and reports differences from nominal values when the comparison conditions are known. An unsupported path or an indeterminate conjugate reports `UNCONFIRMED`. Leave the numerical fact absent and describe the modeling limit in the PR.

The initial calculation covers forward, coaxial sequential imaging with centered circular clear apertures. It uses the admitted entrance pupil for an infinite object and the admitted marginal-ray angle at the native object conjugate for a finite object. Use the configured Gaussian waist as the finite object plane. See the [record format](docs/RECORD_FORMAT.md#axial-paraxial-aperture) for the field names and conditions.

## Open a pull request

A single record or correction can come directly in a focused pull request. Describe the intended change. For a new collection, bulk import, or change to the record format or retrieval interface, first check the issue tracker and use the relevant issue to coordinate the scope.

The **Lens intake** check reports the result for routine data submissions and attaches a `lens-intake-report` JSON artifact. Maintainers review changes to the retrieval code, record contract or validation rules. A draft data PR can show a representative Project when a format or validation change is under discussion.

## Prepare a collection or batch

- Propose a collection identity, identify its maintainers and pin the source revision or edition where possible. Describe how source record IDs map to contributed records and how future updates can be tracked.
- In the PR or series issue, summarize the inputs, submitted records and any deferrals or failures. Split large submissions into independently checkable batches.
- Review existing records for duplicates. Keep the positions of one design in the same Project when native configurations can represent them. Retain distinct prescriptions where their optical parameters or structure make them useful, and group related designs by family.

Project code and documentation use the [MIT License](LICENSE). Imported records retain their applicable attribution and license or permission.
