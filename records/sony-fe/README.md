# Sony FE collection

Full-frame Sony photography lenses, transcribed from the numerical examples of Sony-assigned
patent publications into native `os-optics` Projects. Series issue: [#13](https://github.com/JunLin615/os-optics-lens/issues/13).

```
records/sony-fe/
├── batch-sony-fe-<N>.json        batch outcome manifest, one row per source input
├── NOTES-batch-<N>.md            what that batch contains and what it does not claim
└── patent-<publication>-ex<NN>/  one directory per record
    ├── project.json              the native os-optics Project (authoritative)
    ├── record.json               search facts, provenance, validation
    └── evidence.json             the transcribed table and stated parameters
```

Each batch adds a manifest and a note beside the records it adds. The note states the comparison
rule applied, every deferral with its reason code, and the modelling limits of the batch. Read a
batch's manifest before its records: an accepted record is one whose four validation outcomes all
hold, and a deferred input is named there with the reason it is not a record.

Records are authored from the publication's own printed tables. Nothing is inferred: a value the
publication does not print is absent from the record, and a quantity that had to be derived says so
with its `basis`.
