# Corrected-Gradient PR Operator Plan

This is a CPU-F5 read-only design note. It plans corrected-gradient diagnostic
operators for the CPU u-pw PR prototype before any production replacement or GPU
implementation.

## 1. Current PR Operator State

The current CPU PR operators in `source/JSphCpu.cpp` are material-material only
and use the uncorrected kernel gradient:

- `ComputeHydroDivVelT()`
- `ComputeHydroLapPorePressT()`
- `ComputeHydroLapZT()`

They skip non-fluid particles with `CODE_IsFluid(code[p2])`, so boundary
particles do not enter the hydraulic operators. The production PR rate is:

```text
PorePressRate = Kw/n * (
    -DivVel
    + k/(rho_w*g_h) * LapPorePress
    + k * LapZ
)
```

where `DivVel` is the mathematical divergence of skeleton velocity. Compression
therefore gives `DivVel < 0`, and the PR volumetric term uses `-DivVel`.

### Current divergence operator

For material particle `i`:

```text
DivVel_i =
sum_j (m_j/rho_j) * (v_j - v_i) . gradW_ij
```

where the code uses:

```text
dr = x_i - x_j
gradW_ij = fac * dr
```

This is the mathematical divergence with the sign convention already fixed in
the PR rate.

### Current Laplacian operators

The pore-pressure and elevation-head terms use a Morris/Brookshaw-type form:

```text
Lap(f)_i =
2 * sum_j (m_j/rho_j) * (f_i - f_j)
    * (r_ij . gradW_ij) / (|r_ij|^2 + eps)
```

with `f = PorePress` for `LapPorePress` and
`f = hydraulic elevation z_h` for `LapZ`.

These operators have passed pressure-only 1D diffusion sanity checks, but they
remain uncorrected and lose consistency near incomplete particle support.

## 2. Literature Corrected Gradient

The u-pw implementation notes describe the first-order corrected kernel
gradient as:

```text
gradWcorr_ij = L_i * gradW_ij
```

with:

```text
L_i = [ sum_j (m_j/rho_j) * (x_j - x_i) tensor gradW_ij ]^-1
```

Because the current code uses `r_ij = x_i - x_j`, an equivalent implementation
can build:

```text
C_i = - sum_j V_j * r_ij tensor gradW_ij
L_i = inverse(C_i)
gradWcorr_ij = L_i * gradW_ij
```

where `V_j = m_j/rho_j`.

The PR terms map as:

```text
DivVelCorr_i =
sum_j V_j * (v_j - v_i) . gradWcorr_ij

LapPorePressCorr_i =
2 * sum_j V_j * (p_i - p_j)
    * (r_ij . gradWcorr_ij) / (|r_ij|^2 + eps)

LapZCorr_i =
2 * sum_j V_j * (z_i - z_j)
    * (r_ij . gradWcorr_ij) / (|r_ij|^2 + eps)
```

These formulas preserve the current sign convention and should not change the
`-DivVel` sign in the production PR rate.

## 3. Existing Correction Matrix Code

### source_DualSPHysics+ lcorr path

The reference `source_DualSPHysics+` tree contains `lcorr` implementations in
CPU and GPU preloop / normal computation code. The matrix is accumulated as:

```text
lcorr.a11 += -drx * frx * vol2
lcorr.a12 += -drx * fry * vol2
lcorr.a13 += -drx * frz * vol2
...
```

This matches the `C_i = -sum V_j r_ij tensor gradW_ij` form needed here.

For 2D, the reference code extracts the x-z submatrix:

```text
[ a11 a13 ]
[ a31 a33 ]
```

and inverts that 2x2 matrix. For 3D, it inverts the full 3x3 matrix. If the
determinant is too small, the reference code falls back to identity-like
behavior.

### mDBC/cDBC a_corr2 / a_corr3 path

`InteractionMdbcCorrectionT2()` and `InteractionCdbcCorrectionT2()` build
`a_corr2` and `a_corr3` matrices for MLS reconstruction of boundary velocity,
density, and stress. These matrices include constant and gradient terms:

- 2D: 3x3 matrix for `[1, x, z]`
- 3D: 4x4 matrix for `[1, x, y, z]`

This is useful design guidance for determinant checks and fallback behavior,
but it is not the same matrix as the first-order gradient correction for PR
operators. Do not reuse `a_corr2/a_corr3` directly for `DivVelCorr`,
`LapPorePressCorr`, or `LapZCorr`.

## 4. Per-Particle Matrix Strategy

The recommended corrected-gradient matrix is one matrix per material particle:

```text
C_i = - sum_j V_j * r_ij tensor gradW_ij
L_i = inverse(C_i)
```

Initial scope should be material-material only, matching the current PR
operators. Boundary/ghost contributions should remain a separate design path
because CPU-BG3 showed that the simple boundary ghost Laplacian worsened bottom
hydrostatic consistency.

### 2D cases

For `Simulate2D`, use x-z correction:

```text
C2 =
[ C_xx C_xz ]
[ C_zx C_zz ]
```

Then:

```text
gradWcorr.x = L2.xx * gradW.x + L2.xz * gradW.z
gradWcorr.y = 0 or original symmetry-handled y term is not used
gradWcorr.z = L2.zx * gradW.x + L2.zz * gradW.z
```

This avoids singularity caused by all particles lying at constant `y`.

### 3D cases

For 3D, use the full 3x3 matrix. The implementation can use the existing
`fmath::Determinant3x3()` and `fmath::InverseMatrix3x3()` helpers on CPU.

## 5. Fallback Strategy

Fallback must be explicit and counted:

- If neighbour count is too small, use uncorrected gradient.
- If `abs(det2d) < det_limit` or `abs(det3d) < det_limit`, use uncorrected
  gradient.
- If the inverse produces non-finite values, use uncorrected gradient.

Recommended initial diagnostic thresholds:

```text
det_limit_2d = 1e-6 to 1e-4
det_limit_3d = 1e-8 to 1e-6
min_neighbours_2d = 6
min_neighbours_3d = 12
```

These are diagnostic defaults only. They should be reported in logs and tuned
from hydrostatic and linear-field tests.

Fallback output should include:

- total material particles
- corrected count
- fallback count
- fallback ratio
- min/max determinant

## 6. Persistent Array vs Temporary Two-Pass Design

### Option A: persistent `HydroGradCorrc`

Store `L_i` as a per-particle matrix:

- 2D could store four floats/doubles, but GPU and 3D parity favor a 3x3 storage
  layout.
- CPU array candidate: `tmatrix3f* HydroGradCorrc` or `tmatrix3d* HydroGradCorrc`.
- Add sorting and periodic duplicate logic.
- GPU port needs corresponding `HydroGradCorrg`.

Pros:

- Build once per step and reuse for `DivVelCorr`, `LapPorePressCorr`, `LapZCorr`.
- Cleaner parity with GPU.
- Enables output of determinant/fallback diagnostics.

Cons:

- Adds memory, sorting, duplicate, resize, and output plumbing.
- More GPU port work.

### Option B: temporary two-pass inside each operator

For each diagnostic operator:

1. First neighbour pass builds `C_i` and inverts it.
2. Second neighbour pass computes the corrected operator.

Pros:

- Minimal persistent state.
- Good for the first CPU diagnostic prototype.
- Avoids committing to GPU array layout too early.

Cons:

- Repeats matrix build for each operator.
- More expensive on CPU.
- Harder to make GPU efficient.

### Recommendation

Start with Option B for CPU diagnostic-only implementation, then promote to
Option A only if corrected diagnostics demonstrate clear value. If corrected
operators become production or GPU targets, use a persistent
`HydroGradCorrc/HydroGradCorrg` matrix.

## 7. Diagnostic Operators to Prioritize

Implement diagnostics in this order:

1. `DivVelCorr`
   - Directly affects the stiff `Kw/n * (-DivVel)` term.
   - Important for self-weight and coupled stability.
2. `LapPorePressCorr`
   - Directly affects diffusion and hydrostatic consistency.
3. `LapZCorr`
   - Needed with `LapPorePressCorr` to test
     `LapPorePress/(rho_w*g_h) + LapZ`.

Do not change the production PR rate in the first implementation. Add output
fields only:

```text
DivVelCorr
LapPorePressCorr
LapZCorr
HydroGradCorrFallback
```

The fallback field can be a scalar `0/1` or a float determinant/fallback code.
If output scope must stay small, log counts only and skip the per-particle
fallback output.

## 8. Feedback Operator

Do not modify pore-pressure feedback in this phase.

Reasons:

- The recommended production feedback path is already the difference-gradient
  operator, selected by `PorePressureFeedbackOperator=1`.
- The previous symmetric corrected-gradient feedback diagnostic failed to
  remove the constant-pressure boundary spuriosity and was removed.
- Corrected PR operators should first be assessed on `DivVel`, `LapPorePress`,
  and `LapZ`, not on feedback.

If corrected gradients later prove useful for PR rate terms, a separate
diagnostic may test a corrected difference-gradient acceleration. It should not
block the PR operator diagnostic phase.

## 9. Minimum Smoke Tests

### A. Hydrostatic consistency

Case:

- `PorePressureInit=1`
- explicit `HydraulicGravity=(0,0,-9.81)`
- `SavePorePressure=1`

Metrics:

```text
HeadResidual       = LapPorePress/(rho_w*g_h) + LapZ
HeadResidualCorr   = LapPorePressCorr/(rho_w*g_h) + LapZCorr
```

Expected:

- Corrected residual improves in the interior.
- Boundary improvement is not guaranteed without boundary/ghost treatment.
- Fallback count should be low in the interior and higher near boundaries.

### B. Linear elevation field

Use `z_h = -dot(pos, hydraulic_unit)` from current particle positions.

Metrics:

- `LapZ` vs `LapZCorr`
- internal and boundary-layer max/mean

Expected:

- `LapZCorr` should be closer to zero for a linear field, especially in the
  interior.

### C. Pressure-only diffusion

Use the validated 1D pressure-only baseline.

Expected:

- Production output remains unchanged.
- Corrected diagnostics do not alter `PorePress`.
- Corrected diffusion indicator is smoother or at least not worse in the
  interior.

### D. Self-weight short response

Use the short self-weight smoke window.

Metrics:

- `DivVel` vs `DivVelCorr`
- `PorePressRate` production remains unchanged
- no excluded particles
- no NaN

Expected:

- Corrected divergence can be compared to production divergence without
  changing pressure evolution.

## 10. GPU Implications

If corrected-gradient PR operators become production, GPU needs:

- a correction matrix build kernel;
- a matrix storage array, likely 9 floats per particle for simple 3D layout;
- a fallback flag/count array or reduction;
- sorting and periodic duplicate logic for the matrix and fallback flag;
- corrected variants of:
  - `ComputeHydroDivVelGpu`
  - `ComputeHydroLapPorePressGpu`
  - `ComputeHydroLapZGpu`
- parity tests comparing CPU/GPU corrected diagnostics.

For G1-G4 GPU porting, do not require corrected gradients unless CPU diagnostics
show a clear benefit and the production switch is already decided. Otherwise,
port the existing material-only PR baseline first.

## 11. Recommended Implementation Path

### CPU-CG1: diagnostic matrix prototype

- Add local helper to build/invert `L_i`.
- Use temporary two-pass loops.
- No persistent matrix array.
- Output corrected diagnostics only.

### CPU-CG2: hydrostatic and linear-field tests

- Compare material-only vs corrected diagnostics.
- Evaluate interior, top layer, bottom layer, and side-layer metrics.
- Decide whether boundary errors still dominate.

### CPU-CG3: pressure-only parity

- Run pressure-only baseline with corrected diagnostics enabled.
- Confirm production fields are unchanged.

### CPU-CG4: optional production switch design

Only if diagnostics improve:

```xml
<parameter key="PorePressurePROperator" value="0" />
```

Possible meanings:

```text
0: current material-only uncorrected
1: corrected material-only
2: corrected + boundary treatment (future)
```

Do not add this switch until diagnostics justify it.

### CPU-CG5: GPU planning update

If corrected operators become production, update `gpu_port_plan.md` before G1.

## 12. Current Recommendation

Implement corrected-gradient PR operators as diagnostic-only first:

- `DivVelCorr`
- `LapPorePressCorr`
- `LapZCorr`

Do not replace production PR rate yet.
Do not modify feedback yet.
Do not combine this with simple boundary ghost operators from CPU-BG3.

The main decision after CPU-CG diagnostics is whether corrected material-only
operators improve interior consistency enough to justify GPU matrix storage. If
boundary-layer errors remain dominant, prioritize a proper boundary/MLS pressure
treatment instead of promoting corrected material-only operators to production.
