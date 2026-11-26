# Batch 1: US20240061211A1

One Sony-assigned full-frame imaging-lens family, transcribed from the numerical examples of
[US20240061211A1](https://patents.google.com/patent/US20240061211A1/en) ("Imaging lens and imaging
apparatus", Sony Group Corp, priority 2018-03-30). Every example in the publication is a 131 mm
f/1.85-class design with a printed image height of 21.633 mm, which is a 43.27 mm image circle: a
36 × 24 mm frame.

| Example | Record | Printed f (mm) | Engine f (mm) | Outcome |
| --- | --- | --- | --- | --- |
| 1 | `patent-us20240061211a1-ex01` | 130.950 | 131.157 | accepted |
| 2 | `patent-us20240061211a1-ex02` | 130.967 | 131.102 | accepted |
| 3 | — | 130.956 | 118.100 | deferred, `SOURCE_TABLE_INCONSISTENT` |
| 4 | `patent-us20240061211a1-ex04` | 130.957 | 131.168 | accepted |
| 5 | `patent-us20240061211a1-ex05` | 131.012 | 131.219 | accepted |

Each Project places its image-plane observation after the last tabulated thickness, so
`first_order.total_track_mm` equals the length `L` the publication prints: 145.000, 142.483, 144.819
and 150.000 mm for the four accepted examples.

The engine's focal length sits 0.10–0.16 % above the printed value in every accepted example. That
offset is the same one the patent-derived `phone-modules` batch documents: the printed radii and
thicknesses are rounded and the materials are constant indices at the reference wavelength, so the
comparison rule for patent records uses `atol = 0.005 mm` and `rtol = 0.003`. Each record states
that rule, the achieved fraction of the allowance, and the approximations that produced the
difference.

## What these records are not

- **Not a product reproduction.** The publication does not name a product. The records claim a
  patent example, not a Sony lens model.
- **Not a chromatic model.** The publication prints `nd` and `vd` only, so every element is a
  constant index at 587.56 nm and the vd values are kept as evidence, not modelled.
- **Not a stop-resolved model.** The publication prints no clear or mechanical semi-diameters. The
  Projects use one uniform 13 mm clear semi-diameter, so the modelled stop does not bound the beam
  and `design.aperture_validity` says `STOP_NOT_BLOCKING`: first-order and structural queries are
  supported, stop-dependent ones stay unconfirmed.
- **Not every focus state.** Each Project is the infinity-focus state. The printed focusing gaps
  `d1..d4` for the intermediate and closest ranges are kept in `evidence.json`.

## Example 3

Its transcribed table gives 118.10 mm against a printed 130.956 mm. The printed rounding cannot
account for a 10 % gap, so the example is withheld and reported in the batch manifest rather than
committed as a record. The likely cause is a surface row whose thickness or radius did not survive
the table extraction; the finding is recorded so a reviewer can compare the extraction against
TABLES 11–14 of the publication directly.
