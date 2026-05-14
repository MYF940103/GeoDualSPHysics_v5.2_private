# BND1 Source Audit: PorePressureBoundaryOperator=2

Date: 2026-05-14

## Scope

This audit checks the CPU hydraulic boundary-particle route before using it as a pre-landslide u-pw boundary operator. It focuses only on `PorePressureBoundaryOperator=2`; modes `0` and `1`, PR pressure-rate governing equations, feedback, constitutive models, and mechanical loading remain outside the change scope.

## Current Implementation Locations

- Parser and GPU protection: `source/JSph.cpp`.
  - `PorePressureBoundaryOperator=2` is parsed in the hydromechanical parameter block.
  - GPU execution hard-errors for mode `2`: `PorePressureBoundaryOperator=2 is CPU-only in this branch. GPU support is not implemented.`
- CPU call site: `source/JSphCpuSingle.cpp`.
  - `ApplyPorePressureBoundaryOperator(...)` is called after material `LapPorePress` and `LapZ` are computed and before `PorePressRate`.
- CPU implementation: `source/JSphCpu.cpp`.
  - `ApplyPorePressureBoundaryOperatorT(...)` contains mode `1`, mode `2`, and mode `3`.
- GPU implementation: `source/JSphGpu.cpp` and `source/JSphGpu_ker.cu`.
  - GPU applies only mode `1`; mode `2` is not ported.

## Pre-BND1 Mode 2 Behavior

The pre-BND1 CPU mode `2` already scanned original boundary particles (`p2 < pini`) and filtered them with:

```cpp
const bool p2bound=(CODE_IsNormal(code[p2]) && !CODE_IsFluid(code[p2]));
```

It then classified a boundary particle only as:

- top drained if `topactive && zb >= ztopthreshold`;
- bottom no-flux if `bottomactive && zb <= zbottomthreshold`;
- inactive otherwise.

Therefore lateral and ordinary solid boundary particles were scanned but skipped by `bndinactive++` unless their hydraulic elevation also fell in the bottom reference band. This is not equivalent to an "all solid walls are no-flux" hydraulic boundary.

## Top and Bottom Recognition

- Top drained is geometry/elevation based, not `mk` based: material `zmax`, `PorePressureDrainThickness` or `KernelH`, and `PorePressureTopDrainedStartTime`.
- Bottom no-flux is also elevation based: material `zmin`, `PorePressureBottomNoFluxThickness` or `KernelH`.
- No lateral wall classifier existed in mode `2` before BND1.

## Boundary State

Mode `2` reconstructs a hydraulic excess state for a boundary particle by weighted nearby material samples:

```cpp
excess_b = sum(V_j W_bj excess_j) / sum(V_j W_bj)
```

The boundary total pressure used in the PR operator is:

```cpp
p_b = hydrostatic_linear(z_b) + excess_b
```

For `HydraulicElevationSource=1`, this is a hydraulic-head/excess no-flux convention, not a naive zero-gradient of total pore pressure. For `HydraulicElevationSource=0`, the hydrostatic term vanishes and the mirror reduces to an excess/pore-pressure reconstruction.

## mDBC/cDBC Relationship

The mode uses mechanical boundary particles and optionally `BoundNormal` to define the hydraulic sample point:

```cpp
pos_b_hyd = pos_b + BoundNormal_b
```

It does not change mDBC/cDBC mechanical behavior. Boundary particles only enter the PR `LapPorePress` / `LapZ` quadrature.

## GPU Status

GPU mode `2` remains unsupported and protected by the existing parser hard error. The GPU kernel path currently supports only mode `1`.

## BND1 Source Change

BND1 changes CPU mode `2` only:

- top/free drained boundary particles keep excess Dirichlet `p'=0`;
- all other ordinary solid boundary particles are classified as no-flux;
- bottom no-flux is still counted separately for diagnostics;
- lateral/ordinary no-flux boundary contribution pairs are logged;
- mode `0` and mode `1` are unchanged;
- GPU mode `2` remains unsupported.

The new implementation is intentionally opt-in and does not change the default operator.
