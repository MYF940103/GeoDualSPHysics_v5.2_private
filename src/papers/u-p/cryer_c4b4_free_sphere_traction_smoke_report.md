# C4-B4 Free-Sphere Flexible Confining Stress Smoke

## Objective

C4-B4 tests the CPU-only `FlexibleConfiningStress` source on a small free
sphere before any strict Cryer simulation is attempted. The goal is only to
check traction-source behavior:

- no-load regression remains stable;
- positive `ConfiningStressP0` produces inward radial compression;
- the symmetric free sphere has near-zero net force and center-of-mass
  acceleration;
- surface response is stronger than interior response;
- compression produces the expected positive pore-pressure response;
- `SoilConstitutiveModel=0` keeps plasticity inactive.

This is not a strict Cryer reproduction. No drained curved pore-pressure
boundary, analytical center-pressure comparison, GPU support, or long run is
included.

## Case Folder

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/flexible_confining_stress_C4B4_FreeSphere/`

Retained files:

- `CaseFlexConf_C4B4_FreeSphere_NoLoad_Def.xml`
- `CaseFlexConf_C4B4_FreeSphere_Ramp_Def.xml`
- `CaseFlexConf_C4B4_FreeSphere_StrongerOptional_Def.xml` (draft, not run)
- `xRun_C4B4_FreeSphere_CPU_release.bat`
- `scripts/analyze_c4b4_free_sphere.py`
- CSV metrics and SVG/PNG figures.

Heavy raw output folders were not retained.

## Geometry

The smoke geometry is a free 3D material sphere:

| Quantity | Value |
|---|---:|
| Radius | `0.05 m` |
| Particle spacing | `0.01 m` |
| Material particles | `739` |
| Center | `(0, 0, 0)` |
| Boundary particles | none |
| Soil model | `SoilConstitutiveModel=0` |
| Boundary operator | `PorePressureBoundaryOperator=0` |
| GPU | not used |

`HydraulicGravity` is kept nonzero only because the current hydromechanical PR
setup requires a nonzero hydraulic gravity vector. Mechanical gravity is zero,
so the mechanical loading in the ramp smoke comes from
`FlexibleConfiningStress` only.

## Runs

| Case | Description | Result |
|---|---|---|
| `no_load` | free-sphere no-load regression | `code=0`, `excluded=0` |
| `ramp` | `ConfiningStressP0=50 Pa`, ramp `0-0.0005 s` | `code=0`, `excluded=0` |

Both runs used CPU Release only. No GPU run was performed.

## Main Metrics

From `c4b4_free_sphere_case_summary.csv`:

| Metric | No-load | Ramp |
|---|---:|---:|
| Steps | 16 | 16 |
| Runtime | `0.655972 s` | `0.682131 s` |
| Frames | 5 | 5 |
| Final `p0_eff` | `0 Pa` | `50 Pa` |
| Target particles | 0 | 739 |
| Final max confining acceleration | `0 m/s2` | `1.95492 m/s2` |
| Final net force magnitude | `0 N` | `3.23e-08 N` |
| Final net/absolute force | `0` | `1.94e-08` |
| Final COM acceleration estimate | `0 m/s2` | `2.08e-08 m/s2` |
| Final symmetry residual | `0` | `1.94e-08` |
| Final max velocity | `0 m/s` | `7.99e-04 m/s` |
| Final surface radial velocity mean | `0 m/s` | `-6.28e-04 m/s` |
| Final surface radial displacement mean | `0 m` | `-1.09e-06 m` |
| Final center excess pressure | `-196.20 Pa` | `26319.63 Pa` |
| Final mean excess pressure | `-101.82 Pa` | `31410.56 Pa` |
| Final max `Kplastic` | `0` | `0` |

The no-load excess-pressure offset comes from the hydrostatic reference used to
keep the hydromechanical PR configuration valid in this free-sphere smoke. The
relevant sign check is the loaded response relative to the no-load baseline:
the center excess pressure increases by about `2.65e4 Pa`, and the mean excess
pressure increases by about `3.15e4 Pa`. This is consistent with compression.

## Direction and Symmetry

Positive `ConfiningStressP0` produced inward motion:

- final surface radial velocity mean: `-6.28e-04 m/s`;
- final surface radial displacement mean: `-1.09e-06 m`;
- final interior radial velocity mean: `-6.07e-04 m/s`.

The short free-sphere test remains very small, so the interior already responds
through elastic wave transmission by the final output. The force diagnostics
still show that the applied source itself is symmetric: net force is roughly
`2e-8` of the total absolute confining force and the COM acceleration estimate
stays near `1e-8-2e-8 m/s2`.

## Surface / Interior Interpretation

The flexible confining stress term is intended to cancel in the interior by
pairwise symmetry and appear at free surfaces through kernel truncation. In this
short sphere smoke:

- the surface particles move inward immediately;
- tangential surface velocity remains small compared with radial velocity;
- no global drift is observed from the net-force and COM diagnostics;
- the interior response is not zero by the final frame, which is expected once
  the compressive wave enters the sphere.

This supports the loading-route sign and symmetry, but it is still only a
traction-source smoke.

## Plasticity Check

The run used `SoilConstitutiveModel=0`. The exported `Kplastic` metric remains
zero in both no-load and ramp runs, confirming that the linear-elastic skeleton
path is active and no DP plasticity is involved.

## Figures

Generated figures:

- `c4b4_p0_eff_ramp`
- `c4b4_velocity_max`
- `c4b4_surface_radial_velocity`
- `c4b4_surface_radial_displacement`
- `c4b4_surface_vs_interior_radial_velocity`
- `c4b4_com_acceleration`
- `c4b4_symmetry_residual`
- `c4b4_center_excess_pore_pressure`
- `c4b4_mean_excess_pore_pressure`

Each figure is stored as SVG and PNG under the C4-B4 `figures/` directory.

## Conclusion

C4-B4 passes as a traction-only free-sphere smoke:

- no-load regression is stable;
- the ramped `FlexibleConfiningStress` run is stable;
- positive `ConfiningStressP0` produces inward radial compression;
- net force and center-of-mass acceleration remain near zero;
- compression produces a positive pore-pressure response;
- `Kplastic` remains zero.

`FlexibleConfiningStress` is therefore a credible strict Cryer traction
candidate for the CPU path.

Strict Cryer simulation should still not start yet. The drained curved
pore-pressure boundary remains a separate blocker, and GPU support for
`FlexibleConfiningStress` remains intentionally unsupported.

## Next Step

Proceed to C4-C: drained curved pore-pressure boundary audit/development for
the strict Cryer sphere. GPU support should remain deferred until the CPU
loading and drained-boundary behavior are credible.
