# T4b Zhao Renormalized-Gradient Confinement Source Audit

## Scope

T4b audits and implements an opt-in Zhao-style renormalized/corrected gradient
for the existing CPU `FlexibleConfiningStress` pair term. The change is limited
to the flexible confinement source path. It does not modify the PR pore-pressure
governing equation, soil constitutive model, Cryer boundary code, AccInput, or
the normal stress-divergence operator.

## Current Raw-Gradient Path

The current flexible confinement contribution is assembled in
`source/JSphCpu.cpp` inside the CPU material interaction loop:

```cpp
const float frx=fac*drx,fry=fac*dry,frz=fac*drz;
...
const float prsconf=massp2*(confp0+confp0)/(rhopp1*velrhop2.w);
const tfloat3 aceconf=TFloat3(prsconf*frx,prsconf*fry,prsconf*frz);
```

This is directionally close to Zhao Eq. 51 because it adds an isotropic
confining-pressure pair term whose interior contribution cancels when kernel
support is complete. The missing piece is that Zhao uses a renormalized kernel
gradient, while the current path used the raw kernel gradient.

## Existing Corrected-Gradient Infrastructure

The branch already contains a CPU corrected-gradient diagnostic for PR
operators in `JSphCpu::ComputeHydroCorrectedOperatorsT`. That code builds a
local first-order correction matrix:

`L_i = - sum_j V_j r_ij tensor grad W_ij`

and applies `L_i^{-1} grad W_ij` to diagnostic `DivVel`, `LapPorePress`, and
`LapZ` outputs.

That diagnostic path is useful as a template, but it is not directly reused by
the flexible confinement force loop because:

- it writes PR diagnostic arrays rather than force-pair gradients;
- it runs as a separate diagnostic pass;
- it is material-only and not tied to the opt-in confinement selectors;
- T4b needs the corrected gradient only for the confinement pair term, not for
  the governing PR operators or normal mechanical stress divergence.

## Implemented T4b Route

T4b adds:

```text
ConfiningStressGradientMode
  0 = raw kernel gradient, legacy default
  1 = CPU renormalized/corrected gradient for FlexibleConfiningStress only
```

Default behavior remains `0`.

When mode `1` is enabled, each active confinement target builds a local
correction matrix from target material neighbours:

`L_i = - sum_j (m_j/rho_j) r_ij tensor grad W_ij`

If the matrix has enough neighbours and a valid determinant, the confinement
pair term uses:

`grad W_ij^R = L_i^{-1} grad W_ij`

If the matrix is insufficient or ill-conditioned, only that particle falls back
to the raw gradient. The fallback is reported in diagnostics.

## Interaction With f_i and Lateral Selectors

The T3 selectors remain unchanged:

- `ConfiningStressUseFiSelector=1` restricts force application to
  `f_i <= ConfiningStressFiThreshold`;
- `ConfiningStressUseLateralSelector=1` restricts force application to the
  cylinder lateral class;
- the renormalization matrix is only built for particles that pass those
  selectors.

The matrix itself uses target material neighbours, not only active selected
neighbours. This mirrors the existing `f_i` support estimate and avoids making
the correction matrix too sparse on the selected surface.

## Diagnostics

T4b adds a confinement gradient diagnostics line:

```text
FlexibleConfiningStress gradient diagnostics:
  gradient_mode, corrected, fallback, det_min, det_max
```

The T4b smokes reported `corrected=112`, `fallback=0`, with determinant range
about `0.1169` to `0.1952` for the selected active lateral targets.

## Numerical Consequences

The correction is p1-local rather than pair-symmetric. That is acceptable for a
CPU diagnostic prototype, but it is not yet a production Zhao boundary. Any
strict route must keep monitoring net force, COM acceleration, and symmetry
residual. In T4b the symmetry residual remains small, but the lateral
confinement magnitude roughly doubles compared with the raw-gradient T4 case.

## CPU/GPU Status

The implementation is CPU-only. GPU execution now hard-errors explicitly when
`ConfiningStressGradientMode=1` is requested; `FlexibleConfiningStress=1` also
remains GPU-unsupported in this branch. The GPU Release build was used only as
a parser/shared-source compile check; no GPU run was performed.
