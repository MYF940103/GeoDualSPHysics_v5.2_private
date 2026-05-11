# O1-Revised Hydraulic Operator Source Audit

## Purpose

This audit separates two concepts that are easy to conflate:

1. **Mechanical boundary support**: the case uses mDBC/cDBC-style multilayer boundary particles for mechanics, density, velocity, and stress support.
2. **Hydraulic boundary state participation**: the u-pw PR pore-pressure operator needs pore-pressure or hydraulic-head values at boundary/ghost locations if boundary particles are to enter `LapPorePress`, `LapZ`, feedback, or Shepard operations consistently.

The current question is not simply whether kernels are geometrically truncated. The case already has multilayer boundary particles. The question is whether those particles carry a consistent hydraulic state and participate in the PR pore-pressure operator.

## Mechanical Boundary Particles

The CPU mDBC correction path is in `source/JSphCpu_mdbc.cpp`, especially `JSphCpu::InteractionMdbcCorrectionT2()`.

The GPU mDBC/cDBC path is in `source/JSphGpu_mdbc_iker.cu`, especially `Interaction_MdbcCorrection*()` and `Interaction_Mdbc2Correction*()`.

These routines:

- evaluate ghost-node positions from boundary normals;
- interact boundary/ghost locations with neighboring fluid/material particles;
- reconstruct or extrapolate `velrhop`;
- assemble correction matrices such as `a_corr2` / `a_corr3`;
- use EOS pressure or density cloning for boundary density/pressure behavior;
- update mechanical boundary velocity/density-related state.

The audited mDBC/cDBC correction files do **not** contain `PorePress`, `LapPorePress`, `LapZ`, or u-pw hydraulic-state reconstruction.

## Current PR Pore-Pressure Operator Boundary Participation

The CPU PR hydraulic operators are implemented in `source/JSphCpu.cpp`:

- `ComputeHydroLapPorePressT()`
- `ComputeHydroLapZT()`
- `ComputeHydroPorePressRatePR()`
- `ComputePorePressureAccelDiffT()`
- `ApplyPorePressureShepardT()`

The GPU equivalents are in `source/JSphGpu_ker.cu`:

- `KerComputeHydroPrDiagnostics()`
- `KerComputePorePressureAccelDiff()`
- `KerApplyPorePressureShepard()`

In these PR paths, both target particles and neighbor particles are filtered through `CODE_IsFluid(...)`.

Therefore:

- mDBC/cDBC boundary particles do not enter the production `LapPorePress` neighbor sums;
- mDBC/cDBC boundary particles do not enter production `LapZ` neighbor sums;
- mDBC/cDBC boundary particles do not enter production `PorePressureAccelDiff`;
- mDBC/cDBC boundary particles do not enter production `PorePressureShepard`;
- boundary-particle `velrhop` reconstruction does not automatically provide a pore-pressure boundary state.

This means the current production hydraulic operator is effectively **material-material only**, even though the mechanical SPH domain has multilayer boundary particles.

## Boundary Hydraulic State Arrays

The hydromechanical arrays include `PorePress` for the particle array length, but the active PR updates and operators only apply to `CODE_IsFluid` particles. Boundary particles may have allocated slots, but they do not receive a physically enforced Dirichlet or Neumann hydraulic state for production PR interactions.

The diagnostic-only boundary ghost fields are:

- `PorePressureBoundaryGhost`
- `PorePressureBoundaryGhostOutput`
- `PorePressGhostc`
- `ExcessPorePressGhostc`
- `PorePressureBoundaryModec`
- `LapPorePressGhostc`
- `LapZGhostc`

These are output/diagnostic paths. They are not production PR operators.

CPU-BG3 found that the simple diagnostic ghost Laplacian worsened bottom-region hydrostatic consistency, so that path was not promoted.

## Current `PorePressureBoundaryOperator=1`

`PorePressureBoundaryOperator=1` is implemented as a virtual boundary contribution after the material-material `LapPorePress` and `LapZ` operators.

It does not use existing mDBC/cDBC boundary particles. It constructs material-adjacent virtual states:

- top drained: excess-pressure Dirichlet ghost, `excess_ghost = 0`;
- bottom no-flux: hydraulic-head / excess-pressure Neumann mirror, `excess_ghost = excess_i`;
- both `LapPorePress` and `LapZ` receive matching virtual contributions to preserve hydrostatic cancellation.

B5 showed that this mode is stable and CPU/GPU consistent, but it did not reduce the long-run Scenario 2 bottom excess RMSE relative to legacy mode 0.

## LapPorePress and LapZ Consistency

For material-material interactions, `LapPorePress` and `LapZ` use the same pair list, same kernel gradient factor, same volume weight, and same Brookshaw/Morris form. For a hydrostatic total pressure field, the pairwise combination:

```text
LapPorePress/(rho_w g_h) + LapZ
```

cancels by construction when the same neighbor set is used.

For `PorePressureBoundaryOperator=1`, the top and bottom virtual additions are also paired so that the same cancellation is intended when a linear hydrostatic reference is used.

## Paper / Supporting-Material Evidence

The converted paper text in `papers/u-p/converted/u_pw_paper_text.md` states that:

- the domain is enveloped by boundary particles for velocity/mechanics;
- Dirichlet pore-pressure conditions may be applied at free surfaces or boundary/dummy particles;
- Neumann pore-pressure conditions require additional treatment;
- the paper adopts a moving least-squares formulation from Chow et al. to extrapolate pore pressure from domain particles to boundary particles using a specially corrected kernel.

The local notes in `papers/u-p/u_pw_sph_implementation_notes.md` summarize the same point: the paper uses MLS to extrapolate pore pressure to boundary particles for Neumann pore-pressure boundaries.

Therefore, an MLS or boundary-particle hydraulic-state treatment is supported by the paper as a target formulation. It is not currently implemented in the production GeoDualSPHysics u-pw PR path.

## Audit Conclusion

The current consistency question is:

> Given that mechanical mDBC/cDBC boundary particles exist, does the hydraulic PR operator need boundary-particle pore-pressure/head states or MLS-style hydraulic quadrature to match the paper more strictly?

The source audit answer is:

- current production PR hydraulic operators are material-material only;
- existing mDBC/cDBC boundary particles do not carry production hydraulic state for `PorePress`;
- `PorePressureBoundaryOperator=1` is a virtual material-adjacent ghost contribution, not an mDBC/cDBC boundary-particle hydraulic operator;
- the paper does contain evidence for MLS extrapolation of pore pressure to boundary particles for Neumann pore-pressure conditions.

The standalone O1-revised diagnostic tests whether such boundary-aware hydraulic participation is likely to explain the observed `cv_eff/cv ~= 1.1175` time-factor sensitivity.
