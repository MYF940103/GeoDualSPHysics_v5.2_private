# L3b Mechanical Top-Load Validation Report

## Setup

L3b adds a CPU-only opt-in mechanical surface-load prototype for the
paper-aligned 1D consolidation case:

- `MechanicalTopLoad=1`;
- `MechanicalTopLoadMode=1`;
- `MechanicalTopLoadQ0=-10000 Pa`;
- `MechanicalTopLoadArea=0.1 m2` for the 2D per-unit-depth column;
- ramp `0 -> 0.005 s`;
- top material surface auto-detected;
- no `AccInput`;
- `PorePressureInit=1`;
- `PorePressureFeedback=0`;
- top drainage starts at the end of the ramp;
- bottom no-flux correction remains enabled.

The L3b route applies `Fz=q0*A`, so the full load scale is `-1000 N` and the
selected top-row acceleration is `-476.19 m/s2`.

## Build and Run

- CPU Release build: passed.
- CPU Debug build: passed with existing MSVC/PDB warnings.
- GPU Release build: passed.
- GPU simulation: deferred; `MechanicalTopLoad=1` is CPU-only and hard-errors
  when requested on GPU.
- L3b CPU run: `code=0`, `excluded=0`, `DtMin=0`.

## Metrics

From `ExternalLoad_L3b_MechanicalTopLoad/l3b_case_summary.csv`:

| metric | value |
|---|---:|
| peak excess pressure | `5.897e5 Pa` |
| bottom RMSE vs q0 Terzaghi | `2.724e5 Pa` |
| final profile RMSE vs q0 Terzaghi | `4.401e5 Pa` |
| final top drained residual | `0 Pa` |
| final bottom no-flux proxy | `-1.93 Pa` |
| max velocity | `0.136 m/s` |

The applied force is correct in scale, but the generated excess pore pressure
is still far above the physical `10 kPa` Terzaghi initial excess pressure.

## Comparison

| route | bottom RMSE | final profile RMSE | peak excess |
|---|---:|---:|---:|
| L2 AccInput | `2.206e5 Pa` | `4.791e4 Pa` | `6.246e5 Pa` |
| L3a initial pressure | `7.287e3 Pa` | `9.129e3 Pa` | `1.000e4 Pa` |
| L3b mechanical top load | `2.724e5 Pa` | `4.401e5 Pa` | `5.897e5 Pa` |

L3b is numerically stable and uses the correct total force scale, but it does
not approach the L3a analytical diffusion gate. The result shows that applying
the force directly to top material particles still behaves like a dynamic
surface-row acceleration route.

## Boundary Checks

Top drainage and bottom no-flux remain mechanically stable:

- final top drained excess residual is `0 Pa`;
- final bottom no-flux proxy is about `-1.93 Pa`.

The boundary operators are not the main L3b blocker. The blocker is mechanical
load generation and dynamic response.

## Interpretation

L3b implements a mechanical top-load prototype, and it no longer uses
`AccInput`. However, it is still not a paper-faithful constant surface traction
or force-controlled loading plate. It cannot be used as a strict Terzaghi
validation route.

## Recommendation

Do not start a broad damping or viscosity sweep from L3b. The recommended next
strict route is:

1. L3c consistent initial stress plus initial excess pore pressure; or
2. a true force-controlled platen/traction boundary with quasi-static force
   balance and reaction diagnostics.

If the project needs a reliable paper-compatible PR diffusion gate now, use
L3a. If the goal is full mechanical load reproduction, continue with L3c or a
proper force-controlled boundary design.

