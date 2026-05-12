# Cryer C2 Center Pressure Postprocessing Plan

Date: 2026-05-12

## Purpose

Strict Cryer validation requires a center pore-pressure history. The current
`analyze_cryer_smoke.py` helper reports a near-center proxy for reduced smoke
only. A strict postprocessor must instead extract `p_w(r=0,t)/p0` and compare
it with a verified Mandel-Cryer reference.

## Center Definition

For a strict sphere, the center should be the fixed geometric center used to
generate the sphere. For a reduced workflow, the center can be reported as the
initial material-particle centroid, but that result must remain a smoke metric.

Recommended strict fields:

- `center_x`, `center_y`, `center_z`;
- sphere radius `a`;
- averaging radius `r_avg`;
- applied traction `p0`;
- dimensionless time `Tv`.

## Extraction Methods

### Method 1: Nearest Particle

Find the material particle closest to the fixed center and record its
`PorePress`. This is simple and useful for coarse smoke, but noisy and sensitive
to particle motion.

### Method 2: Small-Radius Average

Average all material particles inside `r_avg`, where `r_avg` is documented as a
fraction of the particle spacing or radius. This is the recommended first
strict method because it reduces particle noise without requiring interpolation.

### Method 3: Symmetry-Aware Average

For a full sphere, average particles in a small ball around the center. For a
validated axisymmetric surrogate, average the centerline/axis particles using a
documented geometric convention.

## Movement and Noise Handling

The center itself should remain a fixed reference point. Particle motion should
not move the evaluation point unless a separate deformed-coordinate comparison
is explicitly required. If pressure noise is visible, report both nearest
particle and averaged values.

## Normalization

Strict output should include:

- `center_pore_pressure`;
- `normalized_center_pressure = center_pore_pressure / p0`;
- `time`;
- `Tv`;
- reference value if available.

If the run uses an initial excess pressure instead of all-around traction `p0`,
it must not be labeled strict Cryer. A smoke-only normalization can be reported
separately.

## Proposed CSV Format

| Column | Meaning |
|---|---|
| `time` | Physical output time. |
| `Tv` | Dimensionless Cryer time, if the reference mapping is available. |
| `center_x`, `center_y`, `center_z` | Fixed evaluation point. |
| `center_pore_pressure_nearest` | Nearest material particle value. |
| `center_pore_pressure_avg` | Radius-averaged value. |
| `normalized_center_pressure` | `center_pore_pressure_avg / p0`. |
| `particles_used` | Number of particles in the averaging ball. |
| `averaging_radius` | Radius used for the average. |
| `reference_center_pressure` | Analytical value, if available. |
| `reference_source` | Reference identifier or blank. |

## Status of Existing Helper

`analyze_cryer_smoke.py` is a smoke helper. It is useful for verifying that a
near-center pore-pressure proxy is bounded and finite. It is not strict Cryer
postprocessing because it lacks:

- applied traction normalization by `p0`;
- dimensionless time `Tv`;
- verified analytical reference;
- a strict sphere center;
- a documented center averaging radius.
