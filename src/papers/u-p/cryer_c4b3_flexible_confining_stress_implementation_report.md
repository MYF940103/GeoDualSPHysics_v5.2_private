# C4-B3 CPU Flexible Confining Stress Implementation Report

Date: 2026-05-12

## Objective

C4-B3 adds the first minimal CPU implementation of the flexible confining stress
route selected in C4-B2. The purpose is to provide a source-controlled
mechanical loading term for future strict Cryer work without using an
`AccInput` patchwise surrogate, without reintroducing `TopLoad*`, and without
changing the u-pw PR pore-pressure equation.

This task is a loading-source smoke only. It is not a strict Cryer simulation.
The drained curved pore-pressure boundary remains a separate blocker.

## Source Changes

Modified source files:

- `source/JSph.h`
- `source/JSph.cpp`
- `source/JSphCpu.cpp`
- `source/JSphGpu.cpp`

New XML parameters under `<execution><special><soils>`:

| Parameter | Default | Meaning |
|---|---:|---|
| `FlexibleConfiningStress` | `0` | `0`: off, `1`: CPU-only flexible confining stress. |
| `ConfiningStressP0` | `0` | Positive external compression magnitude in Pa. |
| `ConfiningStressRampStart` | `0` | Start time of linear load ramp. |
| `ConfiningStressRampEnd` | `ConfiningStressRampStart` | End time of linear load ramp. |
| `ConfiningStressTargetMk` | `-1` | `-1`: all normal material particles; otherwise one `mkfluid` value. |
| `ConfiningStressMode` | `0` | `0`: isotropic flexible confining stress. Other modes are unsupported. |

The default is off, so existing XML files do not receive any contribution.

## Momentum Implementation

The term is added only in the CPU material-material stress-divergence pair
summation in `JSphCpu::InteractionForcesFluid`. It is not written to the
material stress tensor, does not enter the constitutive update, does not alter
the effective stress state stored for output, and does not affect `PorePress`,
`PorePressRate`, `LapPorePress`, `LapZ`, `HydraulicGravity`, or `AccInput`.

The implemented sign convention is:

```text
ConfiningStressP0 > 0 means external compression.
```

In the current SPH stress-divergence sign convention, this is added as a
positive isotropic stress-like pair contribution. The sign-smoke velocity
projection confirms inward surface motion for positive `ConfiningStressP0`.
This corresponds to the continuum intent of a compressive
`sigma_conf = -p0 I`; the implementation sign is adapted to the existing
pair-force convention.

The target filter is restricted to normal material particles. It excludes
boundary, floating, and inout particles.

## GPU Status

GPU support is intentionally not implemented in C4-B3. If
`FlexibleConfiningStress=1` is used on the GPU path, the code hard-errors during
configuration instead of silently falling back to a no-load state.

## Diagnostics

The CPU path prints compact diagnostics when the confining stress is active:

- effective ramped `p0`;
- target particle count;
- net force vector from the confining term;
- total absolute confining force;
- maximum confining acceleration;
- center-of-mass acceleration estimate;
- force symmetry residual.

The postprocessing script also computes velocity magnitude and a surface radial
velocity projection from the VTK particle output. Negative surface radial
velocity means inward motion relative to the small smoke specimen centroid.

## Build

Both requested release builds passed after the source patch:

- CPU Release: `DualSPHysics5ReCpu_vs2022.sln`, `ReleaseCPU|x64`
- GPU Release: `DualSPHysics5Re.sln`, `Release|x64`

No strict Cryer simulation was run.

## Smoke Cases

Smoke directory:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/flexible_confining_stress_C4B3/`

Cases:

- `CaseFlexConf_C4B3_NoLoad_Def.xml`
- `CaseFlexConf_C4B3_Sign_Def.xml`
- `CaseFlexConf_C4B3_Ramp_Def.xml`

These are tiny free-material CPU tests, not Cryer physics cases.

Generated retained artifacts:

- `c4b3_flexible_confining_stress_summary.csv`
- `c4b3_confining_force_diagnostics.csv`
- `c4b3_sign_smoke_metrics.csv`
- `figures/*`

## Smoke Results

| Case | code | excluded | final p0_eff [Pa] | targets | final max conf. accel [m/s2] | final symmetry residual | final surface radial velocity mean [m/s] |
|---|---:|---:|---:|---:|---:|---:|---:|
| no_load | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| sign | 0 | 0 | 50 | 216 | 1.78994 | 1.21395e-08 | -1.05313e-03 |
| ramp | 0 | 0 | 50 | 216 | 1.78997 | 1.19541e-08 | -1.00461e-03 |

The no-load regression produced no confining diagnostics and remained stable.
The sign smoke produced inward surface velocity for positive `p0`, confirming
the implemented sign. The ramp smoke reached the same final `p0` while avoiding
an instantaneous first-step load. Both loaded runs had near-zero net force
relative to total absolute force, with center-of-mass acceleration estimates of
order `1e-08 m/s2`.

The pressure sign check is intentionally not claimed in C4-B3 because the smoke
uses a mechanics-only tiny specimen (`HydromechCoupling=0`). A coupled
poroelastic sign check belongs in the next loading smoke, after the geometry is
closer to the strict Cryer sphere.

## Compatibility

- Default-off behavior is preserved.
- Existing DP, DP+softening, and PR pore-pressure paths are not changed.
- `SoilConstitutiveModel` defaults are unchanged.
- `PorePressureBoundaryOperator` modes `0/1/2` are unchanged.
- `TopLoad*` was not reintroduced.

## Remaining Blockers

- GPU flexible confining stress support is not implemented.
- Strict Cryer has not been run.
- Drained curved pore-pressure boundary support remains separate.
- The current smoke is a cube-like mechanics sanity check, not a traction-only
  sphere benchmark.
- The analytical reference still needs Figure 7B digitized validation when data
  become available.

## Recommendation

C4-B3 is sufficient to proceed to **C4-B4 traction-only sphere smoke**: create a
small free 3D sphere, enable `FlexibleConfiningStress`, and verify radial
compression, symmetry, net force, and optional coupled pressure sign. The
drained curved boundary work should remain separate as C4-C. Strict Cryer
simulation should still remain paused until both loading and drained boundary
routes are credible.
