# H1 CPU Hydraulic mDBC Boundary-Particle Prototype Design

Date: 2026-05-12

## Objective

H1 tests a CPU-only experimental path for making existing mDBC/cDBC boundary
particles participate in the u-pw PR hydraulic operator. The goal is strict
hydraulic boundary consistency, not explaining the self-weight Scenario 2
effective time-factor mismatch. A1/A2/P1/O1 indicate that the Scenario 2
nominal analytical discrepancy is dominated by effective `cv` / dynamic storage
mapping, while boundary-particle-aware quadrature is still useful for a more
consistent production boundary treatment.

## Existing Source State

The mechanical mDBC/cDBC path reconstructs mechanical state, including
`Velrhop`, EOS pressure/density, boundary normals, and correction matrices. It
does not create a production hydraulic pore-pressure state on boundary
particles.

The PR hydraulic operators before H1 were material-centric:

- `ComputeHydroDivVel()`: material-material velocity divergence.
- `ComputeHydroLapPorePress()`: material-material pore-pressure Laplacian.
- `ComputeHydroLapZ()`: material-material hydraulic elevation Laplacian.
- `ComputePorePressureAccelDiff()`: material-material difference-gradient
  feedback.
- `PorePressureShepard`: material-material pore-pressure regularization.

The production loops use `CODE_IsFluid` for material neighbours. Boundary
particles are therefore not used as hydraulic quadrature points in the PR
operator. The existing `PorePressureBoundaryGhost` fields are diagnostic-only.

## Operator Switch

`PorePressureBoundaryOperator` keeps legacy behaviour by default:

- `0`: legacy post-update layer corrections only.
- `1`: simple virtual boundary contribution, experimental.
- `2`: CPU-only hydraulic boundary-particle reconstruction prototype.

GPU mode `2` remains unsupported and should fail explicitly rather than falling
back silently.

## H1 Mode 2 Design

Mode `2` is implemented in `ApplyPorePressureBoundaryOperator()` after
material-only `LapPorePress` and `LapZ` have been computed and before
`PorePressRate` is formed.

Boundary particles are not given an advected pore-pressure degree of freedom in
this prototype. Instead, a hydraulic state is reconstructed on the fly:

- The boundary quadrature position is the mDBC projected position
  `pos_b + BoundNormal_b` when a normal is available; otherwise the particle
  centre is used.
- Top drained boundary particles use a Dirichlet excess condition:
  `excess_b = 0`, `p_b = p_hydro(z_b)`.
- Bottom no-flux boundary particles use the hydraulic-head/excess convention:
  the boundary excess pressure is reconstructed from nearby material particles,
  representing zero normal gradient of head/excess. This is not a zero-gradient
  condition on total pore pressure.
- The reconstructed boundary state contributes to both `LapPorePress` and
  `LapZ` using the same Brookshaw-style pair form as material interactions.

The current CPU cell-neighbour path for PR operators is material-centric, so the
mode `2` prototype explicitly scans original boundary particles (`0..Npb-1`)
and filters them by distance and hydraulic boundary classification. This is
acceptable for the CPU prototype and avoids changing mode `0` / mode `1`.

## Reused and Deferred Pieces

Reused:

- mDBC boundary normals (`BoundNormalc`) to define the hydraulic quadrature
  location.
- Existing top drained / bottom no-flux geometry filters and thickness defaults.
- Existing legacy layer projection as a safety correction after update.

Deferred:

- Stored boundary arrays such as `PorePressBndHyd`.
- Boundary participation in `PorePressureAccelDiff` and Shepard.
- GPU implementation of mode `2`.
- Corrected-gradient production operators.
- Full MLS polynomial reconstruction beyond the zero-order SPH reconstruction
  used for bottom excess in this H1 prototype.

## Validation Plan

H1 uses short CPU Release diagnostics only:

- Hydrostatic cancellation with top drained and bottom no-flux.
- Pressure-only diffusion short run.
- Coupled self-weight very short run.
- Standalone O1-revised eigenmode scaling reference for mode `0`, mode `1`,
  idealized boundary-particle mode `2`, and 1D MLS.

The acceptance criterion is not long-run analytical improvement. The key
questions are whether mode `2` actually includes boundary particles, preserves
hydrostatic cancellation, stays stable with `excluded=0`, and shows enough
promise to justify a future GPU or fuller MLS phase.
