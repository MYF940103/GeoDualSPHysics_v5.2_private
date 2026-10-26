# Lian mode-4 mirrored contact: 15-s review (2026-10-26)

Two actual GPU Release fresh starts completed on RTX 3050: 10 us coarse and
5 us half, each 301 native frames. Actual endpoints are 15.000009999601302 s
and 15.000004999516719 s; neither is a PART restart. Raw inputs, source/build,
runtime and output hashes were verified; both wrappers exited normally and
no owned solver remains. Each complete 61-frame shared 3-s exact-time/step
prefix is all-native-field 0 ULP, with no unmatched final frame.

The independent full-history half maxima are 0.0153762103 Pa pressure RMS
and 0.000012898477 mm top-material displacement, below the original 5 Pa /
0.005 mm limits. All active FSType 2/3 drained nodes remain exactly 0 Pa;
native IDs, finite/positive-density/elastic/no-exclusion/geometry/natural-step
checks pass. Original source-clock drainage/ramp timing was not changed.

Against the retained same-dt/current-double-stress strict 15-s control:

| Quantity | Strict | Mirrored coarse / half |
|---|---:|---:|
| Native1744 contact transitions | 12 | 0 / 0 |
| Native1744 drained saved samples | 6 | 0 / 0 |
| Post-ramp load nodes | 12 or 13 | 13 / 13 |
| Post-ramp force (N/m) | 11999.99947 to 12999.99943 | 12999.99943 / 12999.99943 |
| Minimum pressure over saved history (Pa) | -3211.9873 | 0 / 0 |
| Maximum soil speed (m/s) | 0.07500275 | 0.001944381 / 0.001944395 |

The negative-pressure/contact-loss event is removed over this window.
Maximum speed drops by approximately 97.41%. This comparison changes only
the mode-4 symmetry-edge footprint; it is not a legacy-float precision A/B.
The original 13-node equivalent width is still 1.3 m, +4% versus 1.25 m;
the load was not rescaled. No SPR/HG/gradient correction or new damping was
enabled. Stress remains double, pressure/rate float.

Inspected `../figures/lian_mirror15_review_r1_history.png`, `_contact.png`
and `_fields.png`, with matching history/pairs/prefix/fields CSVs. The
machine-readable receipt is `../logs/lian_mirror15_review_r1.check.json`.
The diagnostic A/B histories still use their historical nearest-node IDs;
formal paper comparisons must use A(0,10) (native1744) and B(1.25,8.75)
(four initial-grid native IDs, each weight 0.25), plus the x0=1.25 profile.
PDF Fig9/11/12 were visually checked. Reference curves are numerical SPH/FEM,
not exact analytical solutions; no SPH/FEM accuracy is inferred here.

Accept the 15-s contact repair and admit one independent actual root 100-s
release run at 10 us. Full-cycle/late-plateau/reference accuracy remains
pending. In particular, smooth settlement alone does not prove agreement
with Fig12. Only 15-s half-step evidence exists. Source modifications remain
the two predicates already backed up at f14008c; this review adds no physics.

Current task order is Lian, Cryer, then case01 self-weight consolidation.
Yao and retrogressive slope are deferred by the latest user plan in
`../../../validation/poromech_next_r2.json`.
