# Camera search evidence

This proposal adds optional, condition-specific facts to camera lens records. The
[Yutong Cup problem 2 acceptance case](../acceptance/yutong-2025-mirrorless-problem-2.json)
specifies the queries and expected outcomes. Its record is the
[P2b finite-film camera model](../records/yutong-cup/yutong-2025-mirrorless-18-p2b/record.json).
Apply the constraints together within one nominal configuration.

| Fact | Comparable conditions |
| --- | --- |
| Geometric back focus | Use `first_order.final_powered_vertex_to_sensor_mm` with `distance_kind: geometric_axial_distance`, `from: last_powered_surface_vertex` and `to: fixed_image_plane`. The `includes_cover_glass` flag and `image_format.cover_glass` identify the plate included in the distance. `first_order.back_focal_length_mm` can also carry endpoints for its paraxial focal distance. |
| MTF over a field interval | In `performance`, `mtf_field_minimum` gives the minimum over the declared frequency, spectral weights, field mapping, samples and orientations at a fixed image plane. For this case, the field coordinate is real image height divided by the diagonal image radius. `sampled_field_fractions` gives the sampled positions, including the center, interior positions and the 0.8 endpoint. `limiting_sample` identifies the lowest point and orientation. |
| Corner relative illumination | In `performance`, use `relative_illumination` with the image-circle diameter, normalized field position and mapping, center normalization, scene radiance, transmission model and spectral sampling. `design_coatings` marks the modeled coated result and `uniform` marks a geometric throughput calculation. |
| CRA and distortion | Record the sampled field bounds and mapping. CRA requires an angle reference and the wavelength aggregation. Distortion requires the reference projection, wavelength and signed minimum and maximum. |
| Sensor, spectral sampling and cost | `pixel_pitch_um` is the horizontal and vertical pitch in micrometers. Keep discrete wavelength and weight arrays together and compare relative weight ratios in wavelength order. The span of the samples expresses a search interval. Compare `cost_proxy` only for the same element weights and scope. The contest gives spherical and aspheric powered glass elements weights of one and three and prefers lower cost. |

The camera records use the [shared record format](RECORD_FORMAT.md). A native iris
specifies its opening diameter as the system aperture. The separate
`aperture.entrance_pupil_f_number` fact describes the f-number from EFL and the
entrance pupil with its measurement convention. The case requires a blocking
stop and comparable pupil-based evidence for f-number, MTF and relative
illumination.

`field.verification` points to the original fixed-plane chief-ray results and
records the largest difference from the intended field heights. A reported
image-circle diameter carries the meaning of the tested field. The Sonnar's
largest verified image height is 21.63 mm, which gives a tested diameter of
43.26 mm for a nominal 36 × 24 mm frame.

The MTF result is a sampled minimum. The P2b record covers 11 field heights
through 0.8 at 40 lp/mm in both orientations. Its value of 0.722847 describes
the tested set. A query for a field interval needs a field sweep with a stated
sampling basis. An isolated MTF point leaves the interval unconfirmed. This
case compares the specific sweep bounds and condition signature given in the
fixture. Other search cases can define which additional evidence they accept.

## Analysis entries and source locators

- `analysis_evidence.tolerance` states the method and simulation or measurement
  status. Gate results include sample and pass counts, conditions and source
  locators. Keep physical lot yield separately.
- `analysis_evidence.ghost` lists sourced methods with their scope, assumptions
  and results. Trace outcome and omitted-power bounds remain separate from
  whether the study exists. Problem 2 requires both studies and sets no
  numerical gate for either. The P2b native ghost trace is partial and the
  two complementary screens cover their stated modeled paths.
- Source locators use `archive_member` with a SHA-256 against the named source
  archive, or a source URL and hash when available. P2b pins the original
  prototype archive in `collection.evidence_archive`. The archive remains
  upstream.

## Run the acceptance case

```console
python -m unittest discover -s tests -v
```

The fixture defines 16 checks and one ranking preference. It uses the P2b
infinity-focus configuration for the exercise. The test runs
them against the frozen record and exercises counterexamples for wrong distance
endpoints, absent or mismatched field coverage, strict MTF thresholds, mismatched
corner illumination, a nonblocking stop and missing analysis evidence. A missing or inapplicable
fact is `UNCONFIRMED`. A comparable value outside the requested limits is
`DOES_NOT_MATCH`. The test runs directly on the record and is the reference
for a future index-backed implementation.
