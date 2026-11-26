# Search semantics

## Outcomes

Each hard constraint is evaluated against one configuration view of a record:

* `MATCH` - a comparable value exists under the requested conditions, its evidence resolves when
  required, and every predicate holds.
* `DOES_NOT_MATCH` - a comparable value exists and violates a predicate. Numeric violations carry
  a `shortfall` (absolute distance to the violated limit, in the fact's unit) and `relative`
  (shortfall / |limit|). A strict `gt`/`lt` at equality has shortfall 0.0 and `strict: true`.
* `UNCONFIRMED` - the record cannot confirm or refute the constraint; `reason` says why. A
  missing value is never a match and never a failure.

A configuration is DOES_NOT_MATCH if any constraint is, else UNCONFIRMED if any is, else MATCH.
All hard constraints are evaluated against the same configuration: a record never matches by
combining different configurations. A record is shown at its best configuration (MATCH before
UNCONFIRMED before DOES_NOT_MATCH, then more MATCH, then fewer DOES_NOT_MATCH, then order);
`other_configurations` summarizes the rest.

Specification search reports how far the record meets the brief. Starting-point search ranks
records as places to start refining: targets are flexible and ranked by normalized deviation,
hard constraints still count, and `shortfalls`/`unknowns` show what you would have to change or
verify.

## Reason codes (UNCONFIRMED and unknown targets/preferences)

| reason | meaning | what to do |
|---|---|---|
| `FACT_MISSING` | the configuration has no such fact (`details.available_alternatives` lists related facts; they are never substituted) | choose a fact the record has (`fields`), or treat as open |
| `CONDITIONS_DIFFER` | no entry has the requested conditions (`details` shows expected vs actual) | relax or change `conditions`, or inspect the record |
| `AMBIGUOUS_FACTS` | more than one entry matches the conditions | pin more conditions or use `select` |
| `DISCOVERY_ONLY` | the fact is a discovery label (e.g. `spectrum.sampling_span_nm`) | constrain a confirmed fact instead |
| `COVERAGE_UNCONFIRMED` | continuous spectral coverage is not established | treat coverage as open |
| `SAMPLING_DIFFERS` | the sampled field fractions differ from `required_sampled_field_fractions` | inspect the samples |
| `STOP_NOT_ELIGIBLE` | stop-dependent fact, but the Project's stop does not block light | evaluate the Project with a real stop |
| `STOP_MATCH_NOT_SUPPORTED` | stop-dependent value passes, but the record may not claim a stop-dependent match | verify with os-optics |
| `EVIDENCE_MISSING` | evidence is required but the fact has no source | treat as unverified |
| `EVIDENCE_UNRESOLVED` | the source does not resolve in the index (file, hash or section) | treat as unverified |
| `VALUE_MISSING` | the value at the predicate path is null or absent | check `path` |
| `VALUE_TYPE` | the value has the wrong type for the operator | check `path` and `op` |
| `PREFERENCE_NOT_COMPARABLE` | the preference value exists under other conditions (e.g. cost weights) | rank by another fact |

## Stop gates

Stop-dependent facts are every `aperture.*` member except `aperture.stop_opening_diameter_mm`,
plus `performance.mtf`, `performance.mtf_field_minimum` and `performance.relative_illumination`
(`fields` reports `stop_dependent`). For a stop-dependent constraint (or one with
`requires_blocking_stop: true`):

1. if `design.aperture_validity` does not have both `stop_blocks_light` and
   `eligible_for_stop_dependent_evaluation` true: UNCONFIRMED `STOP_NOT_ELIGIBLE`;
2. otherwise it is evaluated; DOES_NOT_MATCH stands, but a passing value is MATCH only if
   `satisfies_stop_dependent_constraints` is true, else UNCONFIRMED `STOP_MATCH_NOT_SUPPORTED`.

Targets and preferences use step 1 only. The `stop_state` facet shows the state per record.

## Spectral coverage versus discovery span

* `spectrum.sampling_span_nm` is the span of the sampled design wavelengths: discovery only.
  The `band` facet and the `filters.spectral_span` filter use it. It never satisfies a hard
  constraint (UNCONFIRMED `DISCOVERY_ONLY`).
* `spectrum.continuous_coverage_nm` is established coverage. `covers_interval [a, b]` matches
  only when its state is CONFIRMED or SOURCE_STATED and it contains [a, b]; otherwise
  UNCONFIRMED `COVERAGE_UNCONFIRMED` (details show the sampling span).
* Sampled wavelengths: `spectrum.sampling_wavelengths_nm` with `includes_all` or `eq`; spectral
  weights with `proportional_weights` (same ordered wavelengths, weights compared by ratio).

## Aperture conventions

An image-space f-number (`aperture.f_number`), a paraxial working f-number, a ray-traced working
f-number (`aperture.working_f_number`), an entrance-pupil f-number from EFL and pupil diameter
(`aperture.entrance_pupil_f_number`, with a `convention` condition), an entrance pupil diameter
and an object-side numerical aperture are different quantities. None is derived from or
substituted for another. The `system_aperture` facet names the one the design file declares.
Constrain the quantity your brief means; a record without it is FACT_MISSING.

## Back focus endpoints

`first_order.back_focal_length_mm` is the paraxial distance from the last surface vertex to the
paraxial image point. A geometric back focus to a fixed image plane is a different fact,
e.g. `first_order.final_powered_vertex_to_sensor_mm` with conditions `distance_kind:
geometric_axial_distance`, `from: last_powered_surface_vertex`, `to: fixed_image_plane` and
`includes_cover_glass`. Pin those conditions; a fact with other endpoints is CONDITIONS_DIFFER.

## Performance conditions

Performance entries (`performance.<metric>`) carry structured `conditions` (frequency, field
mapping, spectrum, image plane, ...). A constraint compares only entries whose conditions equal
every key it pins (JSON value equality: `0 == 0.0`, `true != 1`, lists ordered). Keys it does
not pin are listed as `unpinned` on a MATCH, so a compact bare `"MATCH"` means the constraint
pinned every condition of the matched fact and the fact has no prose conditions. Prose
conditions appear as `unpinned._text`; they are information, not comparison keys. An interval
MTF is a sampled minimum: `required_sampled_field_fractions` pins the samples and
`requires_evidence_source` requires a resolvable source.

## Evidence

A fact's `source {path, sha256, section}` resolves when the index holds that file with that
sha256 (over LF bytes) and the section exists. Resolution uses only the index, never the file
system. An index built with `--allow-unresolved-evidence` keeps unresolvable references as
unresolved, which leaves the constraints that need them UNCONFIRMED.

## Bases

Each fact has a `basis`: SOURCE_STATED (from the source), DERIVED (computed from stated data),
ENGINE_COMPUTED (computed by os-optics from the Project) or another text (class OTHER). A basis
is reported, never used to decide an outcome.

## Configurations

A record whose native Project declares configurations (e.g. zoom positions `Wide`/`Tele`) is
indexed per configuration with its native `configuration_id`. A record without them has one
configuration, the Project as written, with `configuration_id: null`. `inspect --configuration
ID` and `compare id@ID` select one.

## Multi-valued facts

A fact key with several entries in one configuration (e.g. `performance.mtf` at several
frequencies) is summarized as `{values: n, min, max, unit}`; a range filter matches when any
value is in range (`notes` say so). Constraints must narrow to one entry with `conditions` or
`select`, else AMBIGUOUS_FACTS.
