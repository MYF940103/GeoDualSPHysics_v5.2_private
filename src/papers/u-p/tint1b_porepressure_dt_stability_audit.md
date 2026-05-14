# TINT1b Pore-Pressure Dt and Stability Audit

Date: 2026-05-14

## Current Dt Restriction

CPU `DtVariable()` is implemented at `source/JSphCpu.cpp:6929`. GPU
`DtVariable()` is implemented at `source/JSphGpu.cpp:1694`.

The pore-pressure restriction is active when:

- `HydromechCoupling=1`;
- `PorePressureModel=1`;
- `HydraulicConductivity > 0`;
- `WaterBulkModulus > 0`;
- `WaterDensity > 0`;
- `0 < Porosity0 < 1`;
- `PorePressureDtSafety > 0`.

The current formula is:

```text
c_w = rho_w * |g| * n / K_w
dt_pore = PorePressureDtSafety * c_w * KernelH^2 / k
```

The selected `dt` is limited by `dt_pore` after the usual acceleration/Courant
dt is computed.

## What Dt Does Not Use

The restriction does not use:

- instantaneous `PorePressRate`;
- `LapPorePress` magnitude;
- `LapZ` magnitude;
- boundary contribution magnitude;
- feedback acceleration magnitude;
- actual `DeltaP` after clamps or Shepard.

Therefore `DtMin` adjustments are not a direct indicator that the PR diffusion
CFL has failed. They usually indicate that the mechanical dt calculation has
fallen below `DtMin`, often because acceleration or velocity became large.

## Update Placement and DtVariable

Current ordering:

- Verlet computes `dt` after interaction and before pressure update.
- Symplectic computes predictor `ddt_p`, corrector `ddt_c`, then updates
  pressure with the current full `dt`.

Moving `UpdatePorePressure()` to end-step does not change `DtVariable()` by
itself, because `dt_pore` depends only on parameters and `KernelH`.

However, if the new staging changes feedback acceleration or pressure
corrections, it can indirectly change future `AceMax`, `VelMax`, and therefore
mechanical dt.

## First Symplectic Step Warning

`UpdatePorePressure()` warns if the used `dt` is larger than `dt_pore`. The
message explicitly notes that this can occur on the first Symplectic step
before the next-step dt restriction is applied.

TINT2 diagnostics should record:

- `dt`;
- `dt_pore`;
- whether `dt_pore` limited the final dt;
- `DtMin` adjustment count;
- `AceMax` and velocity max if available.

## BND1 Mode 2 Interpretation

BND1 mode `2` feedback-on produced many `DtMin` adjustments. Since `dt_pore`
does not use `PorePressRate`, that burst is more consistent with mechanical
feedback instability than with a direct PR diffusion dt violation.

The likely chain is:

```text
boundary pressure-rate spike -> updated pressure/correction -> next-step
feedback acceleration/velocity response -> mechanical dt collapse
```

This is another reason to add `DeltaP` bookkeeping and stage labels in TINT2.

