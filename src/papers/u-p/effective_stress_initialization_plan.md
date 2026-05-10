# Effective Stress and Pore-Pressure Initialization Plan

Date: 2026-05-11

Milestone: IC-1 from `full_cpu_implementation_backlog.md`

This plan defines the initialization decisions that must be explicit before
strict u-pw paper case reproduction. It does not change source code.

## Current Convention

Current CPU PR prototype:

- treats `Sigmac` as effective stress for u-pw coupling;
- stores total pore pressure in `PorePress`;
- derives `ExcessPorePress = PorePress - hydrostatic`;
- uses `HydraulicGravity` for the hydrostatic baseline, `LapZ`, and `dt_pore`;
- can use `PorePressureFeedbackMode=1` so momentum feedback uses excess pressure;
- can restart `PorePress` from BI4 for staged workflows.

## General Initialization Rules

1. Do not add pore pressure directly into `Sigmac`.
2. Do not use total hydrostatic pore pressure for feedback in cases where
   hydrostatic pressure should not produce mechanical acceleration.
3. For Terzaghi/self-weight style cases, prefer:
   - `PorePressureFeedbackMode=1`;
   - `PorePressureFeedbackOperator=1`;
   - `PorePressureShepardMode=1`.
4. If a restart file contains `PorePress`, restart values override XML
   `PorePressureInit`.

## Case-Specific Initialization

| Case | Recommended current initialization | Strict gap |
|---|---|---|
| 01 pressure-only Terzaghi | `PorePressureInit=3` for uniform/profile excess, or `PorePressureInit=1` hydrostatic for self-weight variants. | External-load strict case needs mechanically consistent loading/initial excess route. |
| 02 Scenario 1 | Stage A hydrostatic baseline with body gravity on; Stage B restart `PorePress`, body gravity off, hydraulic gravity on. | Boundary treatment and analytical comparison remain. |
| 02 Scenario 2 | Hydrostatic baseline, body gravity on, top drained delayed. | Boundary treatment and paper-compatible stabilization line remain. |
| 03 Cryer | TODO. Likely requires initial pore pressure/stress state from paper benchmark. | Paper parameter extraction, drained boundary, center pressure reference. |
| 04 triaxial | TODO. Needs initial isotropic confinement and undrained pore pressure response. | Confinement boundary and material model decision. |
| 05 retrogressive slope | TODO. Needs slope effective-stress equilibrium and pore-pressure field. | Sensitive clay, initial stress, boundary conditions. |
| 06 Sainte-Monique | TODO/data-blocked. Needs field stress, water table/pore pressure, material zones. | Field data and calibration. |

## Hydrostatic Baseline

The hydrostatic baseline uses:

```text
z = -dot(pos, HydraulicGravityUnit)
p_hydro = WaterDensity * |HydraulicGravity| * max(PorePressureWaterLevel - z, 0)
```

This should be treated as the reference for `ExcessPorePress`. If body gravity
is switched off, `HydraulicGravity` must remain nonzero for hydraulic head
consistency.

## Self-Weight Undrained Response

Supporting Information Eq. (4) gives:

```text
p_w0(z) = [(Kw/n) * rho * g * (H-z)] / [K + 4G/3 + Kw/n]
```

With hydrostatic initialization, compare:

- total `PorePress` vs Eq. (4) only if Eq. (4) is interpreted as total pressure;
- `ExcessPorePress` vs `Eq.(4) - hydrostatic` when the numerical initial state
  starts from hydrostatic pressure.

The current workflow should keep both comparisons in analysis scripts until the
paper convention is verified from the PDF/SI.

## Dynamic Relaxation / Restart Use

For cases requiring an equilibrated initial stress state:

1. run a short gravity or confinement generation stage;
2. use damping/Shepard as documented;
3. save `PorePress`, stress, velocity, density, and plastic state;
4. restart into the analysis stage.

This is currently available for CPU `PorePress`. GPU restart remains a later
porting issue.

## Missing Decisions

- Does each strict paper case start from prescribed effective stress or from a
  dynamic relaxation stage?
- Which cases require total pore pressure feedback versus excess-only feedback?
- How should lateral/curved boundary pressures be initialized?
- What exact initial pore pressure is used in Cryer and triaxial tests?

## Smoke Tests

For any strict-case initialization:

- `PorePress` and `ExcessPorePress` finite at `Part_0000`;
- hydrostatic-only excess near zero where intended;
- restart preserves `PorePress` exactly for staged runs;
- feedback mode does not produce hydrostatic-only acceleration;
- velocity and `DivVel` remain bounded at the start of analysis.

## Current Recommendation

Keep the current 01/02 initialization workflows as the regression baseline.
Before strict 03/04/05/06 reproduction, extract paper initial state definitions
and add case-specific initialization notes. Do not start GPU coding based on
reduced placeholder initial states.

