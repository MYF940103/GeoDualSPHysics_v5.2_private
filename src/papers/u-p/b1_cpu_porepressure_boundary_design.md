# B1 CPU Pore-Pressure Boundary Operator Design

## Objective

The current u-pw PR implementation uses material-material operators for
`LapPorePress`, `LapZ`, `DivVel`, and pore-pressure feedback. Hydraulic boundary
conditions are then imposed by post-update layer corrections:

- top drained: material particles in the top layer are reset to hydrostatic
  pore pressure, i.e. zero excess pore pressure;
- bottom no-flux: material particles in the bottom layer are reset to the mean
  excess pressure of a reference layer above the bottom.

This is robust enough for smoke tests, but it is not an operator-level boundary
treatment. The B1/B2 goal is an optional CPU-only production prototype that adds
boundary-consistent contributions to the PR pressure operator while preserving
legacy behavior by default.

## Existing CPU Path

### PR operator computation

The CPU single-domain force path is in
`source/JSphCpuSingle.cpp::Interaction_Forces()`.

Current hydromechanical order:

1. `JSphCpu::Interaction_Forces_ct(...)` computes standard SPH mechanics.
2. `ComputeHydroDivVel(...)` computes material-material skeleton velocity
   divergence.
3. `ComputeHydroLapPorePress(...)` computes material-material pore-pressure
   Laplacian.
4. `ComputeHydroLapZ(...)` computes material-material hydraulic elevation
   Laplacian.
5. `ComputeHydroCorrectedOperators(...)` computes diagnostic-only corrected
   operators.
6. `ComputePorePressureAccel(...)` and `ComputePorePressureAccelDiff(...)`
   compute feedback diagnostics.
7. `ApplyPorePressureFeedback(...)` adds feedback to `Acec` when enabled.
8. `ApplyHydromechDamping(...)` optionally adds kinematic damping.
9. `ComputeHydroPorePressRatePR(...)` computes
   `Kw/n * [-DivVel + k/(rho_w*g)*LapPorePress + k*LapZ]`.

The production PR rate uses only `DivVelc`, `LapPorePressc`, and `LapZc`.
Corrected-gradient arrays `DivVelCorrc`, `LapPorePressCorrc`, and `LapZCorrc`
remain diagnostic-only and are not used by `PorePressRatec`.

### Pore-pressure update and layer corrections

The pressure update is in `source/JSphCpuSingle.cpp`:

- `ComputeStep_Ver()`
- `ComputeStep_Sym()`

Both call:

1. `UpdatePorePressure(...)`
2. `ApplyPorePressureShepard(...)`, if due
3. particle motion integration
4. `ApplyPorePressureTopDrained(...)`
5. `ApplyPorePressureBottomNoFlux(...)`

The layer corrections are implemented in `source/JSphCpu.cpp`:

- `ApplyPorePressureTopDrained(...)`
- `ApplyPorePressureBottomNoFlux(...)`

These functions directly modify `PorePressc` after the explicit update. They do
not contribute to `LapPorePressc`, `LapZc`, or `PorePressRatec`.

### Existing diagnostic-only boundary ghost path

The diagnostic ghost path already uses the names:

- `PorePressureBoundaryGhost`
- `PorePressureBoundaryGhostOutput`
- `PorePressureBoundaryModec`
- `PorePressGhostc`
- `ExcessPorePressGhostc`
- `LapPorePressGhostc`
- `LapZGhostc`

This path is output-only. CPU-BG3 showed that the simple diagnostic ghost
Laplacian did not improve hydrostatic consistency near the bottom boundary, so
it must not be promoted directly to production.

## XML Switch

Add a new execution parameter:

```xml
<parameter key="PorePressureBoundaryOperator" value="0"
  comment="Hydraulic boundary contribution in PR operator. 0: legacy layer correction only, 1: CPU boundary-consistent PR operator, 2: reserved." />
```

Semantics:

- `0`: legacy behavior. Material-material PR operators plus post-update layer
  correction only. This is the default and preserves all existing cases.
- `1`: CPU-only boundary-consistent PR operator prototype. Boundary
  contributions are added to `LapPorePressc` and `LapZc` before
  `PorePressRatec` is computed. Legacy layer correction remains as a safety
  projection in this prototype.
- `2`: reserved / experimental, not implemented.

This switch is separate from `PorePressureBoundaryGhost`, which remains
diagnostic-only.

## Boundary Convention

The PR diffusion term is expressed through hydraulic head:

```text
k/(rho_w*g_h) * LapPorePress + k * LapZ
```

where `Z` is hydraulic elevation. A hydrostatic state satisfies:

```text
LapPorePress/(rho_w*g_h) + LapZ = 0
```

The boundary operator must preserve this convention.

### Top drained boundary

The top drained condition is a Dirichlet condition on excess pore pressure:

```text
excess p_w = 0
```

For a virtual boundary state:

```text
p_ghost = p_hydrostatic(z_ghost)
```

The contribution is added to both `LapPorePressc` and `LapZc`, so that a
hydrostatic total pressure field remains balanced.

### Bottom no-flux boundary

The bottom no-flux condition is zero normal hydraulic-head gradient. With the
hydrostatic reference split used by this branch, this can be implemented as a
zero normal gradient of excess pore pressure:

```text
d(excess p_w)/dn = 0
```

The first prototype uses a mirror state:

```text
excess_ghost = excess_i
p_ghost = p_hydrostatic(z_ghost) + excess_i
```

This is not `d(total p_w)/dn = 0`; the hydrostatic part is retained so that the
head convention is respected.

## Proposed CPU Implementation

Add a CPU helper that runs after the material-material `LapPorePress` and `LapZ`
operators and before `ComputeHydroPorePressRatePR(...)`.

For each material particle:

1. determine hydraulic elevation `z_i`;
2. compute material `zmin` and `zmax`;
3. if top drained is active and `z_i >= zmax - drain_thickness`, add a top
   mirror/Dirichlet virtual contribution;
4. if bottom no-flux is active and `z_i <= zmin + bottom_thickness`, add a
   bottom mirror/Neumann virtual contribution;
5. add the resulting terms to the existing `LapPorePressc[p]` and `LapZc[p]`.

The first implementation is deliberately local and CPU-only:

- no new persistent particle arrays;
- no boundary particle pressure state;
- no corrected-gradient production switch;
- no GPU changes;
- no change to the PR governing formula.

The virtual volume is initially taken as the local material particle volume
`MassFluid / rhop_i`, which is the simplest mirror-particle approximation.

## Validation Plan

The first test directory is:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/CPU_B1_BoundaryOperator/
```

Short CPU Release tests:

1. hydrostatic consistency;
2. uniform/smooth excess with top drained and bottom no-flux;
3. pressure-only analytical diffusion comparison, legacy mode 0 vs mode 1;
4. short self-weight Scenario 2, legacy mode 0 vs mode 1.

Summary table columns:

```text
test, mode, excluded, max PorePressRate residual, top excess maxAbs,
bottom no-flux proxy, total profile RMSE, excess profile RMSE,
bottom excess RMSE, notes
```

Decision criteria:

- if mode 1 reduces analytical RMSE while keeping hydrostatic residual equal or
  better, it can proceed to B3 CPU medium validation;
- if mode 1 improves one metric but worsens hydrostatic consistency, keep it
  experimental;
- if mode 1 does not improve mode 0, do not port it to GPU.

## Deferred Items

- `PorePressureBoundaryGhost` remains diagnostic-only.
- Corrected-gradient PR operators remain diagnostic-only.
- GPU boundary operator support is not part of B1/B2.
- Strict MLS / mDBC-compatible pressure extrapolation is deferred until this
  CPU prototype shows a clear benefit.
