# Pore-Pressure Boundary Ghost / MLS Plan

This note is a CPU-F4 design document for the current CPU u-pw PR prototype.
It does not describe an implemented feature yet.  The goal is to plan a more
particle-consistent hydraulic boundary treatment before the GPU port and before
strict reproduction of Terzaghi, self-weight consolidation, Cryer, triaxial, and
slope benchmarks.

## 1. Current Hydraulic Boundary State

The current CPU hydromechanical implementation is intentionally minimal:

- `PorePressc` is a double particle field.
- `PorePressRatec`, `DivVelc`, `LapPorePressc`, `LapZc`,
  `PorePressureAcec`, and `PorePressureAceDiffc` are CPU diagnostic / update
  fields.
- `PorePress` can be written to `Part_XXXX.bi4` and restored on CPU restart.
- The PR rate is computed as

  ```text
  PorePressRate = Kw / n * (
      -DivVel
      + k / (rho_w * g_h) * LapPorePress
      + k * LapZ
  )
  ```

  where `DivVelc` stores the mathematical divergence of skeleton velocity.

### Current top drained boundary

Implemented by `JSphCpu::ApplyPorePressureTopDrained()` in
`source/JSphCpu.cpp`.

The method:

- Operates only on material/fluid particles (`CODE_IsFluid`).
- Computes hydraulic elevation using `GetHydraulicElevation()`.
- Finds `zmax_material`.
- For particles with

  ```text
  z >= zmax_material - drain_thickness
  ```

  it sets

  ```text
  PorePress = hydrostatic(z)
  ```

  so `ExcessPorePress = 0` in the top layer.
- It is a layer correction.  It does not create boundary pore-pressure values,
  ghost pressure values, or a kernel-consistent Dirichlet contribution.

### Current bottom no-flux boundary

Implemented by `JSphCpu::ApplyPorePressureBottomNoFlux()` in
`source/JSphCpu.cpp`.

The method:

- Operates only on material/fluid particles.
- Computes `zmin_material`.
- Defines a bottom correction layer:

  ```text
  z <= zmin_material + bottom_thickness
  ```

- Defines a reference layer above it:

  ```text
  zmin + bottom_thickness < z <= zmin + 2 * bottom_thickness
  ```

- Replaces the bottom layer excess pressure with the reference-layer mean
  excess pressure:

  ```text
  PorePress(bottom) = hydrostatic(bottom) + mean(excess_ref)
  ```

This approximates a zero normal gradient in 1D, but it is not a ghost or mirror
kernel contribution.

### Current hydromechanical operators

The following operators are material-material only:

- `ComputeHydroDivVelT()`
- `ComputeHydroLapPorePressT()`
- `ComputeHydroLapZT()`
- `ComputePorePressureAccelT()`
- `ComputePorePressureAccelDiffT()`
- `ApplyPorePressureShepardT()`

They all skip non-fluid particles with `CODE_IsFluid(code[p])`.
Therefore boundary particles do not currently carry hydraulic state in the
operators, and the kernel support is truncated near walls.

### Existing mDBC / cDBC correction machinery

The mechanical boundary correction path is in:

- `JSphCpuSingle::MdbcBoundCorrection()`
- `JSphCpuSingle::CdbcBoundCorrection()`
- `JSphCpu::Interaction_MdbcCorrection()`
- `JSphCpu::Interaction_CdbcCorrection()`
- `JSphCpu::InteractionMdbcCorrectionT2()`
- `JSphCpu::InteractionCdbcCorrectionT2()`

Relevant properties:

- Boundary normals are stored in `BoundNormalc`.
- For mDBC, `boundnormal[p]` points from a boundary particle toward its ghost
  node after `ConfigBoundNormals()`.
- Restart uses `PartExtra_XXXX.bi4` / `JDsExtraDataLoad` to recover normals.
- The mechanical correction reconstructs boundary `velrhop` and `sigma` from
  nearby material particles using MLS-like correction matrices:
  - 2D: `tmatrix3d a_corr2`
  - 3D: `tmatrix4d a_corr3`
- This machinery is currently specific to velocity, density, and stress.  It
  does not reconstruct `PorePress`.

## 2. Why the Current Scheme Is Enough for 1D Smoke, but Not Strict Reproduction

The layer corrections are sufficient for the current 1D smoke tests because:

- The geometry is simple.
- X is often periodic.
- The top and bottom boundaries are horizontal.
- The benchmark can tolerate a thin correction layer when the goal is a
  qualitative pressure-only or short coupled check.
- The difference-gradient feedback operator avoids the worst constant-pressure
  boundary force in material-only support.

The same scheme is not enough for strict reproduction because:

- `LapPorePress` and `LapZ` suffer kernel deficiency near boundaries.
- The layer correction changes particle values after the update rather than
  contributing a consistent boundary term to the operator.
- Lateral no-flux is not represented unless lateral periodicity is used.
- Cryer, triaxial, and slope cases need non-horizontal and curved boundaries.
- A strict drained boundary should be imposed through Dirichlet boundary /
  ghost values in the operator, not only by clamping top material particles.
- A strict no-flux boundary should use mirror/Neumann ghost values, not only a
  reference-layer mean.
- Boundary particles currently have no `PorePress` state, so they cannot
  participate in hydraulic diffusion, feedback, or restart consistently.

## 3. Candidate Designs

### A. Continue layer correction

Keep the current method and add more layer cases:

- top drained layer
- bottom no-flux layer
- lateral no-flux layer
- optional overlap checks

Pros:

- Smallest CPU change.
- No new persistent boundary arrays.
- Easy to keep GPU port simple initially.

Cons:

- Not kernel-consistent.
- Does not fix boundary deficiency in `LapPorePress` or `LapZ`.
- Poor fit for curved boundaries and Cryer.
- Still requires special layer logic for every boundary orientation.

Recommended use:

- Keep as a fallback and smoke-test path.
- Do not make this the strict reproduction path.

### B. Boundary particles carry `PorePress`

Add boundary hydraulic state:

```text
PorePressc[p] valid for boundary and material particles
```

Boundary values are assigned by a boundary condition policy:

- Dirichlet: `PorePress(boundary) = prescribed value`
- Neumann/no-flux: `PorePress(boundary) = extrapolated / mirrored value`
- hydrostatic baseline for excess-pressure mode

Pros:

- Minimal conceptual extension of current arrays.
- Restart/output already can include `PorePress`.
- GPU arrays are straightforward.

Cons:

- Boundary values must be updated every step.
- Operator formulas must intentionally include boundary particles.
- Mechanical boundary particles may be fixed/moving/floating, so their
  hydraulic meaning must be defined.

Recommended use:

- Good first step if combined with a simple boundary classification and
  ghost-value assignment.

### C. Ghost/mirror pressure for no-flux

For a material particle near a no-flux boundary, use a ghost pressure that
mirrors the material value across the wall:

```text
p_ghost = p_material_mirror
```

or, for a local boundary particle and normal:

```text
p_ghost = p_i
```

for zero normal derivative of excess pressure.  In hydrostatic total-pressure
mode, care is needed: no-flux should apply to hydraulic head / excess pressure,
not necessarily to total `PorePress` itself.

Pros:

- Directly targets Neumann zero-gradient behavior.
- Better bottom/lateral no-flux behavior than layer correction.
- Can be added as boundary contributions to `LapPorePress`, `LapZ`, and
  feedback diagnostics.

Cons:

- Requires boundary normals or mirror positions.
- Needs clear treatment for corners.
- For material-only loops, it may require an additional material-boundary loop.

Recommended use:

- Priority for bottom and lateral no-flux in 1D/2D.
- Should be tested first in pressure-only mode.

### D. Dirichlet ghost for top drained

For drained boundaries, set a ghost pressure corresponding to zero excess:

```text
p_ghost = hydrostatic(z_ghost)
```

or impose excess pressure:

```text
excess_ghost = 0
```

in an operator contribution.

Pros:

- More consistent than clamping the top material layer.
- Does not need to overwrite interior top-layer values before/after every
  pressure update.
- Extends naturally to sloped drained surfaces.

Cons:

- Needs boundary normal / ghost position.
- Needs a boundary classification: drained vs no-flux vs inactive.
- Dirichlet ghost values can introduce stiffness if applied too strongly.

Recommended use:

- Add after no-flux ghost diagnostics.
- Initially use in pressure-only diffusion before coupled feedback.

### E. MLS / mDBC-compatible pressure extrapolation

Reuse the mechanical mDBC / cDBC reconstruction idea for pore pressure:

- Evaluate a ghost node position from `pos[pb] + boundnormal[pb]`.
- Search material neighbours.
- Build the same 2D/3D correction matrix used by mDBC.
- Reconstruct pressure and pressure gradient.
- Assign boundary `PorePress` or use reconstructed ghost values directly in
  hydraulic operators.

Possible reconstruction modes:

1. Zeroth-order pressure extrapolation.
2. First-order MLS pressure reconstruction.
3. Excess-pressure MLS reconstruction.
4. Hydraulic-head MLS reconstruction.

Pros:

- Matches existing mDBC philosophy.
- Works for non-horizontal boundaries.
- Provides a route to corrected-gradient PR operators.

Cons:

- Larger implementation.
- Needs robust determinant fallback.
- Needs decisions for total pressure vs excess pressure vs head.
- More expensive on GPU.

Recommended use:

- Plan as the strict boundary path.
- Implement diagnostic-only first, then use for operators.

## 4. Change Scope by Design

| Design | New arrays | Boundary PorePress | LapPorePress/LapZ impact | Feedback impact | GPU impact |
|---|---:|---:|---:|---:|---:|
| Layer continuation | No | No | Post-update only | Post-update only | Small |
| Boundary `PorePress` | Maybe no, reuses `PorePressc` | Yes | Can include boundary terms | Can include boundary terms | Medium |
| No-flux ghost | Optional temporary ghost values | Optional | Yes | Optional | Medium |
| Top Dirichlet ghost | Optional temporary ghost values | Optional | Yes | Optional | Medium |
| MLS/mDBC pressure | Optional gradient / matrix diagnostics | Recommended | Yes | Yes | High |

## 5. Recommended Minimal Implementation Path

### CPU-BG1: boundary classification for hydraulic BCs

Add a CPU-only classification for boundary particles:

```text
0: none / inactive hydraulic boundary
1: drained Dirichlet
2: no-flux Neumann
```

Initial version can be derived geometrically:

- top drained: boundary/material near max hydraulic elevation
- bottom no-flux: near min hydraulic elevation
- lateral no-flux: near min/max horizontal coordinate for non-periodic cases

Do not require XML-rich boundary markup in the first version.

### CPU-BG2: diagnostic boundary pressure assignment

Compute diagnostic boundary / ghost pressure values without changing PR rate:

- `PorePressBoundary` or temporary arrays:
  - `PorePressGhost`
  - `PorePressBoundaryMode`
- Log counts for drained / no-flux / inactive boundary particles.

For excess mode:

- drained: `excess_ghost = 0`
- no-flux: `excess_ghost = excess_material_mirror` or MLS extrapolated

### CPU-BG3: pressure-only boundary contribution diagnostic

Add diagnostic variants only:

- `LapPorePressGhost`
- `LapZGhost`
- `PorePressureAccelDiffGhost`

Do not replace production fields yet.

Compare against current fields on:

- hydrostatic-only
- uniform excess
- profile 2
- 1D pressure-only diffusion

### CPU-BG4: enable ghost boundary in PR pressure-only path

Add an option such as:

```xml
<parameter key="PorePressureBoundaryOperator" value="0" />
```

Possible values:

```text
0: current material-only + layer correction
1: material-boundary ghost contribution
```

Keep default `0` for compatibility.

### CPU-BG5: coupled feedback path

After pressure-only parity is acceptable, allow the difference-gradient
feedback to use ghost / boundary contributions.  Keep symmetric feedback as
compatibility only.

## 6. Minimum Smoke Tests

### Hydrostatic consistency

Case:

- `PorePressureInit=1`
- body gravity may be 0 or active
- `HydraulicGravity=(0,0,-9.81)`
- no excess

Expected:

- `ExcessPorePress ~ 0`
- `LapPorePress/(rho_w*g) + LapZ ~ 0`
- `PorePressRate ~ 0` away from activation transients
- ghost operator should reduce boundary error relative to material-only.

### Uniform excess no-boundary-force

Case:

- `PorePressureFeedbackMode=1`
- uniform excess
- no drained boundary
- no-flux boundaries

Expected:

- difference-gradient feedback near zero everywhere
- no top/bottom/lateral spurious acceleration
- ghost path must not reintroduce symmetric-operator constant-field forces.

### Pressure-only diffusion

Case:

- profile 2 or uniform initial excess
- drained top
- no-flux bottom/lateral
- feedback off

Expected:

- monotonic or smooth decay
- top excess remains zero
- no-flux gradient proxy remains small
- analytical amplitude trend is not degraded.

### Self-weight short window

Case:

- body gravity on for undrained generation
- excess-mode difference-gradient feedback
- damping + Shepard

Expected:

- positive self-weight excess pressure
- no NaN
- excluded=0
- boundary ghost does not amplify oscillations.

### Lateral no-flux test

Case:

- non-periodic lateral boundaries
- uniform or 1D vertical excess profile

Expected:

- no lateral pressure leakage
- lateral `PorePressureAccelDiff` is near zero for 1D fields
- no lateral edge spikes.

## 7. GPU Implications

Boundary ghost support will affect GPU design more than most CPU-only cleanup
items.

Likely GPU additions:

- boundary hydraulic classification array
- optional boundary or ghost `PorePress` array
- material-boundary hydraulic interaction kernels
- reductions for layer/reference statistics if layer fallback remains
- duplicate / periodic copy of new arrays
- output fields for diagnostics

Potential GPU kernels:

- assign boundary hydraulic mode
- compute boundary / ghost pressure
- PR `LapPorePress` and `LapZ` with boundary contributions
- difference-gradient feedback with boundary contributions
- optional MLS pressure reconstruction

Sorting / duplicate considerations:

- Persistent boundary arrays must be sorted with particles.
- Boundary classification must follow boundary particles across cell divide.
- Periodic duplicates need consistent pressure and boundary mode values.
- Restart should restore `PorePress`; if boundary `PorePress` is persistent,
  restart must define whether boundary values are restored or recomputed.

Recommendation:

- Do not start strict GPU PR operators before deciding whether boundary ghost
  support is part of the GPU parity target.
- For early GPU G1-G4, material-only pressure-only parity can proceed, but the
  design should reserve array names / kernel interfaces for boundary support.

## 8. Recommended Next Step

The next CPU feature should be diagnostic-only:

```text
CPU-BG1/BG2: classify hydraulic boundary particles and compute ghost pressure
diagnostics, without changing production PR rate.
```

Suggested minimal diagnostic output:

- counts of drained / no-flux / inactive boundary particles
- ghost pressure min/max by boundary mode
- ghost excess pressure min/max
- optional `PorePressGhost` CSV/BI4 output if memory impact is acceptable

After that:

1. Add `LapPorePressGhost` / `LapZGhost` diagnostics.
2. Test hydrostatic consistency and uniform excess.
3. Only then replace or optionally select the production hydraulic operator.

## 9. Notes on Existing Code Reuse

Reusable pieces:

- `BoundNormalc` and mDBC ghost-node geometry.
- `ConfigBoundNormals()` and `PartExtra_XXXX.bi4` restart support.
- MLS-like matrix assembly in `InteractionMdbcCorrectionT2()` /
  `InteractionCdbcCorrectionT2()`.
- `GetHydraulicElevation()` and hydrostatic helper logic.
- `PorePressureFeedbackMode=1` excess-pressure convention.

Pieces not reusable as-is:

- mechanical `sigma` reconstruction is hard-coded component-by-component.
- cDBC currently uses the boundary particle position rather than the mDBC ghost
  offset.
- mechanical correction overwrites boundary `velrhop` / `sigma`; hydraulic
  pressure should be separately controlled by hydraulic boundary mode.
- current layer corrections are post-update value edits, not operator terms.

## 10. Open Decisions

Before implementation, decide:

1. Should hydraulic boundary mode be inferred geometrically or declared in XML?
2. Should boundary `PorePress` be persistent or temporary?
3. Should no-flux be imposed on total pressure, excess pressure, or hydraulic
   head?  For current self-weight / Terzaghi cases, excess/head treatment is
   safer than total-pressure mirroring.
4. Should the first strict operator target be Laplacian-only or feedback-only?
5. Should MLS reconstruction use total pressure, excess pressure, or hydraulic
   head?
6. How should corner boundary particles combine drained and no-flux conditions?

Conservative default:

- drained condition overrides no-flux at the drained surface;
- no-flux applies to lateral and bottom boundaries;
- excess-pressure mode is used for Terzaghi / self-weight feedback;
- material-only layer correction remains available as fallback.
