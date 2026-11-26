# Search request format

A request is one JSON object (a single query) or a batch `{"queries": [...], "max_output_bytes"?}`.
Pass it as `--request FILE` (recommended), as `-` on stdin, or as one positional argument.
Files may be UTF-8 (with or without BOM) or UTF-16/UTF-32 with a BOM. The schema is closed at
every level: an unknown key is `INVALID_REQUEST` with `details.pointer` (a JSON pointer such as
`/constraints/3/predicates/0/op`) and `did_you_mean`.

## Single query

```
{"mode": "specification" | "starting_point",        required
 "filters": {...},                                   discovery narrowing (below)
 "constraints": [...],                               hard constraints (both modes)
 "targets": [...],                                   starting_point only
 "preferences": [...],                               ranking after outcome/targets
 "include": ["MATCH", "UNCONFIRMED"],                outcomes listed (spec default MATCH+UNCONFIRMED,
                                                     starting_point default all three)
 "hard_shortfall": "exclude" | "allow",              starting_point only (default exclude)
 "evaluation_scope": "one_nominal_configuration",    the only accepted value (default)
 "fields": ["first_order.effective_focal_length_mm"],summary facts per candidate (<= 12)
 "detail": "compact" | "full",                       full adds per-constraint fact evidence
 "limit": 10,                                        1..50
 "cursor": null,                                     page.next_cursor of the previous page
 "max_output_bytes": 32768}                          2048..262144 (single query only)
```

A specification query needs at least one constraint (use starting_point or `facets` to explore).

## Filters (discovery only; they never produce constraint outcomes)

```
"filters": {
  "facets": {"design_type": ["camera_lens"], "band": ["visible"]},   OR within, AND across; aliases ok
  "ranges": [{"fact": "first_order.effective_focal_length_mm", "min": 15, "max": 30}],  min or max may be omitted
  "spectral_span": [450, 650],         the sampling span overlaps [450, 650] nm
  "record_ids": ["yutong-2025-mirrorless-18-p2b"],
  "collections": ["lenslibrary"]}
```

A configuration without the ranged fact is excluded and counted in `total.excluded.missing_fact`.
A multi-valued fact matches a range if any value is in range (`notes` say so).

## Constraints

Shorthand (recommended):

```
{"id"?: "efl", "fact": "first_order.effective_focal_length_mm", "op": "between_inclusive",
 "value": [17.1, 18.9], "path"?, "conditions"?, "select"?, "tolerance"?,
 "requires_blocking_stop"?, "required_sampled_field_fractions"?, "requires_evidence_source"?}
```

* `fact` naming an object (`first_order.effective_focal_length_mm`) compares its `value`
  member; a scalar (`image_format.image_circle_diameter_mm`, `design.conjugate`) compares
  itself; `performance.<metric>` selects entries with that metric and compares `value` (or the
  first `value_*` member). Set `path` to compare another member, e.g. `"path": "min_percent"`.
* An interval fact (min_/max_ pair) needs an explicit `path`; `covers_interval` takes the
  interval itself.
* `conditions` pins condition members by JSON value equality, e.g.
  `{"frequency_lp_mm": 40, "spectrum": {...}}`. Condition keys you leave out are reported as
  `unpinned` on a MATCH.
* `select` narrows performance entries by top-level members before conditions are compared,
  e.g. `{"select": {"frequency_lp_mm": 30, "image_height_mm": 12.0, "direction": "sagittal"}}`.
* `id` defaults to `c0`, `c1`, ... ; ids must be unique.

Fixture form (as in `acceptance/*.json`), accepted verbatim:

```
{"id", "scope": ["performance"], "metric": "mtf_field_minimum",
 "predicates": [{"path": "value", "op": "gt", "value": 0.3}],
 "conditions"?, "select"?, "requires_blocking_stop"?, "required_sampled_field_fractions"?,
 "requires_evidence_source"?}
```

Operators:

| op | value |
|---|---|
| `eq`, `ne` | any JSON value (JSON equality: 0 == 0.0, true != 1) |
| `gt`, `gte`, `lt`, `lte` | finite number |
| `between_inclusive` | `[low, high]` |
| `in` | list of allowed values |
| `includes_all` | list of numbers that must all be members; optional `tolerance` |
| `covers_interval` | `[a, b]`: a confirmed continuous coverage interval object must contain it (a list of samples is `VALUE_TYPE`) |
| `proportional_weights` | weight list compared by ratio |
| `has_source`, `has_sourced_method` | no value (or `true`): evidence must resolve |

An unknown operator is `UNSUPPORTED_OPERATOR`.

## Targets (starting_point)

```
{"id"?: "t0", "fact": "first_order.effective_focal_length_mm", "target": 24,
 "op"?: "near", "tolerance"?: 3, "relative_tolerance"?: 0.15, "conditions"?, "select"?, "path"?,
 "weight"?: 1}
```

`normalized = |value - target| / scale`; scale = `tolerance`, else `relative_tolerance * |target|`,
else `|target|`, else 1. A target needs exactly one comparable numeric value, otherwise it is an
unknown with a reason code. Interval facts cannot be targets.

## Preferences

Always a list, applied in order: `[{"fact": "design.powered_element_count", "direction":
"ascending" | "descending", "conditions"?, "select"?, "path"?}]`. The fixture's cost form is
accepted verbatim: `{"scope": ["cost_proxy"], "metric": "weighted_spherical_element_count",
"spherical_element_weight": 1, "aspheric_element_weight": 3, "scope_of_cost": "...", "direction":
"ascending"}`; a record whose cost weights or scope differ is `PREFERENCE_NOT_COMPARABLE`.

## Batch

```
{"queries": [{"mode": ...}, {"mode": ...}], "max_output_bytes": 32768}
```

At most 20 queries; one budget covers the whole response. Each sub-query has its own `limit`,
`cursor`, `fields` and `detail` (not `max_output_bytes`). A failing sub-query becomes an error
entry; the batch exits 0 unless every sub-query failed. A sub-query whose first candidate cannot
fit even alone fails wherever it is; pages that each fit alone but not together give way from the
last.

## Continuation

When `page.next_cursor` is a string, send the same query (same mode, filters, constraints,
targets, preferences, include, hard_shortfall) with `"cursor": "<next_cursor>"` (or
`--cursor`). `limit`, `fields` and `detail` may change between pages. A cursor from another
index snapshot is `SNAPSHOT_MISMATCH`; from another query, `CURSOR_MISMATCH`.

## Quick flags (CLI)

`search --mode MODE` plus:

| flag | becomes |
|---|---|
| `--filter FACET=V1,V2` (repeatable) | `filters.facets` (OR within a facet) |
| `--range FACT=MIN:MAX` (either end empty) | `filters.ranges` |
| `--spectral-span LOW:HIGH` | `filters.spectral_span` |
| `--record-id ID` (repeatable) | `filters.record_ids` |
| `--where 'FACT OP VALUE'` (repeatable) | shorthand constraint; VALUE is JSON, else a bare string |
| `--target FACT=VALUE~TOL` or `FACT=VALUE~15%` | target with tolerance or relative_tolerance |
| `--prefer FACT[:asc|desc]` (repeatable) | preference |
| `--include MATCH,UNCONFIRMED` | `include` |
| `--hard-shortfall allow` | `hard_shortfall` |

`--fields`, `--detail`, `--limit`, `--cursor` and `--max-output-bytes` also combine with a
single-query `--request FILE`. `--fixture FILE` runs an acceptance fixture (specification mode,
its record id, its constraints and ranking preference, detail full). `--explain-request` prints
the normalized request and its `query_digest` without searching.
