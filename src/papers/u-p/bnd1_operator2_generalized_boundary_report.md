# BND1 Report: Generalized Pore-Pressure Boundary Particle Operator

Date: 2026-05-14

## Objective

BND1 generalizes the CPU `PorePressureBoundaryOperator=2` path so ordinary solid boundary particles can act as hydraulic no-flux boundary samples. This is a pre-landslide boundary audit, not a landslide run and not a GPU port.

## Source Change

Mode `2` now classifies boundary particles as:

- top/free drained if the top drained band is active: `excess_b=0`;
- bottom no-flux if in the bottom band;
- ordinary solid no-flux otherwise.

Mode `0` and mode `1` are unchanged. GPU mode `2` remains unsupported/hard-error. The default remains mode `0`.

## Verification Cases

Directory:

`examples/u-pw/01_1D_Consolidation/experiments/BND1_Operator2Generalized/`

Cases:

| Case | Feedback | Operator | Result |
|---|---:|---:|---|
| `l3c_mode1` | off | 1 | reference |
| `l3c_mode2` | off | 2 | generalized solid-wall no-flux |
| `l5_mode1` | on | 1 | reference |
| `l5_mode2` | on | 2 | generalized solid-wall no-flux |

All cases use `PorePressureInit=3`, `p_w0=10 kPa`, no `AccInput`, no `MechanicalTopLoad`, `TimeMax=0.005 s`, and CPU Release only.

## Run Status

| Case | code | excluded | DtMin adjustments |
|---|---:|---:|---:|
| `l3c_mode1` | 0 | 0 | 0 |
| `l3c_mode2` | 0 | 0 | 0 |
| `l5_mode1` | 0 | 0 | 0 |
| `l5_mode2` | 0 | 973 | 10252 |

The generalized operator is active: mode `2` reports `1180` boundary contribution pairs, with `490` bottom no-flux pairs and `690` ordinary solid no-flux pairs. There are `40` unique no-flux boundary targets, including `20` ordinary solid targets. Thus the old lateral/ordinary-wall skip is fixed in the CPU operator.

## Feedback-Off Comparison

Feedback-off mode `2` is numerically stable:

- `code=0`;
- `excluded=0`;
- `DtMin=0`;
- top drained residual final `0 Pa`;
- bottom no-flux proxy final `0 Pa`;
- lateral no-flux proxy final `0 Pa`.

However, it is not better than mode `1` for the short Terzaghi comparison:

- mode `1` bottom RMSE: `2.77e3 Pa`;
- mode `2` bottom RMSE: `9.13e3 Pa`;
- mode `1` final profile RMSE: `6.43e3 Pa`;
- mode `2` final profile RMSE: `9.67e3 Pa`.

This means BND1 should not promote mode `2` as the preferred 1D validation operator yet.

## Feedback-On Comparison

Feedback-on mode `2` is not stable at the L5 target amplitude:

- `code=0`, but `excluded=973`;
- `DtMin adjustments=10252`;
- peak excess reaches `1.18e9 Pa`;
- velocity / DivVel / PorePressRate become nonphysical.

Mode `1` remains stable for the same feedback-on case (`excluded=0`, `DtMin=0`). Therefore generalized mode `2` is not ready for feedback-on landslide use.

## Interpretation

BND1 confirms the original concern: old mode `2` did not automatically treat lateral/ordinary solid walls as no-flux. The source patch now does that, and diagnostics prove ordinary solid boundaries enter the quadrature.

The same verification also shows the new generalized mode `2` needs more boundary-method work before it can be a production/recommended route. The feedback-off case is stable but analytically worse than mode `1`; the feedback-on case is unstable. This is likely due to the stronger solid-wall boundary quadrature interacting with the current 1D feedback route and mDBC wall geometry. It should be treated as an experimental CPU branch, not a landslide-ready operator.

## Decisions

- Do not make mode `2` default.
- Do not port mode `2` to GPU yet.
- Do not use generalized mode `2` for landslide baseline yet.
- Keep mode `1` as the recommended current feedback-on 1D gate.
- Proceed to BND2 only if the next goal is broader CPU boundary validation and stabilization of mode `2`.

## Build Status

- CPU Release build passed.
- CPU Debug build passed.
- GPU Release build passed.
- No GPU simulation was run.
