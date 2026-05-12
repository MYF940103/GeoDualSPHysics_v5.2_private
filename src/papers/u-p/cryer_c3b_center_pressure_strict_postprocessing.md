# Cryer C3-B Strict Center-Pressure Postprocessing

Date: 2026-05-12

## Purpose

Strict Cryer validation is controlled by the center pore-pressure history. The
postprocessor must produce `p_w(0,t)/p0` versus `T_v` for each Poisson ratio and
compare against the analytical series.

## Center Definition

For the true sphere route:

- the center is the fixed geometry center used in the XML;
- do not move the evaluation point with deformed particle positions;
- report the center coordinates in the output metadata.

## Extraction Methods

Two values should be reported:

1. nearest material-particle pressure;
2. small-radius averaged pressure.

The averaged value should be the primary comparison. Suggested first averaging
radius:

```text
r_avg = max(1.5 dp, 0.05 a)
```

The script should support a radius sweep so the sensitivity can be reported.

## Particle Motion Handling

Select particles by current distance from the fixed center unless a stronger
argument is made for initial IDs. For each frame, report:

- number of particles used;
- min/max distance of used particles;
- whether the averaging ball is empty.

## Normalization

Required inputs:

- applied traction `p0`;
- sphere radius `a`;
- consolidation coefficient `c_v`;
- Poisson ratio `nu`;
- reference CSV for that `nu`.

Output:

```text
T_v = c_v * t / a^2
p_norm = p_w_center / p0
```

## CSV Schema

| Column | Meaning |
|---|---|
| `time` | Physical time. |
| `Tv` | Dimensionless time. |
| `nu` | Poisson ratio for the run. |
| `p0` | Applied all-around traction. |
| `a` | Sphere radius. |
| `center_porepress_nearest` | Nearest particle pressure. |
| `center_porepress_avg` | Averaged center pressure. |
| `center_porepress_avg_over_p0` | Normalized averaged center pressure. |
| `particles_used` | Count inside averaging radius. |
| `averaging_radius` | Radius used for center average. |
| `reference_p_over_p0` | Analytical value interpolated at `Tv`. |
| `error` | Numerical minus reference. |

## Metrics

For each `nu`:

- peak pressure ratio;
- peak `T_v`;
- peak magnitude error;
- peak-time error;
- NRMSE over the plotted `T_v` range;
- late-time residual;
- center-radius sensitivity.

Across the sweep:

- overshoot ordering with decreasing `nu`;
- curve collapse/spacing relative to Figure 7B;
- final decay toward zero.

## Figure 7B Layout

Recommended plot:

- x-axis: `T_v` on log scale;
- y-axis: `p_w(0,t)/p0`;
- four curves for `nu=0.1`, `0.2`, `0.3`, `0.45`;
- analytical lines and simulation markers/lines;
- one combined figure plus per-`nu` diagnostics.

## Current Status

`analyze_cryer_smoke.py` should not be extended in place for strict work. A new
strict tool should be created in C4 after the reference CSV format is fixed.
The smoke helper can remain as a reduced-workflow utility.
