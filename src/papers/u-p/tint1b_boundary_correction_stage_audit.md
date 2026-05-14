# TINT1b Boundary Correction Stage Audit

Date: 2026-05-14

## Scope

This audit covers hydraulic boundary contributions and pressure overwrites for
PR mode `0`, mode `1`, and generalized CPU mode `2`. It excludes deprecated
Cryer boundary modes and does not change any implementation.

## Mode 0: Legacy Layer Projection

Mode `0` does not add boundary contributions to `LapPorePress` or `LapZ` inside
the PR operator.

If the XML enables the simple top/bottom boundary flags:

- top drained is applied at initialization and after the scalar pressure update
  through `ApplyPorePressureTopDrained()`;
- bottom no-flux is applied at initialization and after the scalar pressure
  update through `ApplyPorePressureBottomNoFlux()`.

Current CPU placement:

- Verlet: top/bottom clamps run after `ComputeVerlet()`.
- Symplectic: top/bottom clamps run after `ComputeSymplecticCorr()`.

Current GPU placement:

- top/bottom clamps run immediately after `UpdatePorePressureGpu()` and before
  the mechanical update/corrector.

This CPU/GPU ordering difference matters if TINT2 moves the scalar update.

## Mode 1: Simple Ghost Boundary Operator

Mode `1` adds a virtual hydraulic ghost contribution before
`ComputeHydroPorePressRatePR()`.

Current behavior:

- top active band: ghost enforces excess pressure `0`;
- bottom active band: ghost mirrors material excess pressure to impose
  hydraulic-head/excess no-flux;
- contributions are added to `LapPorePress` and `LapZ`;
- pressure itself is not overwritten by mode `1` during the interaction.

The legacy top/bottom material clamps may still run after `UpdatePorePressure`
when their flags are enabled. Therefore the rate is computed from one pressure
field, but the final pressure may be clamped to a different field.

## Mode 2: Generalized CPU Boundary-Particle Operator

Mode `2` is CPU-only. BND1 generalized it so ordinary solid boundary particles
become hydraulic no-flux boundary samples.

Current behavior:

- top/free drained boundary particles use excess pressure `0`;
- bottom boundary particles use reconstructed excess/head no-flux state;
- other ordinary solid boundary particles also use reconstructed excess/head
  no-flux state;
- contributions are added to `LapPorePress` and `LapZ` before `PorePressRate`;
- reconstructed boundary state is based on current old/stage pressure.

Mode `2` does not directly overwrite material pressure. If top/bottom material
clamps are enabled, those overwrites still happen after the scalar update.

## Shepard Ordering

`PorePressureShepard` currently runs after `UpdatePorePressure()` and before the
mechanical update in both CPU step functions. It smooths total pressure or
excess pressure depending on `PorePressureShepardMode`.

Shepard changes actual pressure but does not alter the already computed
`PorePressRate`. There is no bookkeeping for the pressure change introduced by
Shepard.

## Update-Move Consequences

If TINT2 moves `UpdatePorePressure()` to end-step, the following must move with
it or be explicitly staged:

- Shepard should run immediately after the moved scalar update.
- Top drained and bottom no-flux material clamps should run immediately after
  the moved update and Shepard.
- Boundary operator contributions should remain in interaction as rate
  contributions, using previous-step pressure in Strategy 1.
- Output should use the corrected post-update pressure.

## Rate Versus Actual Pressure Change

The current chain can produce:

```text
DeltaP_rate = PorePressRate * dt
DeltaP_actual != DeltaP_rate
```

because Shepard and clamps overwrite pressure after the raw scalar update.

TINT2 should record:

- `DeltaP_rate`;
- `DeltaP_shepard`;
- `DeltaP_top_clamp`;
- `DeltaP_bottom_projection`;
- `DeltaP_actual`.

This is the only clean way to diagnose whether a boundary instability comes
from the PR rate, from post-update correction, or from feedback-driven
mechanics.

