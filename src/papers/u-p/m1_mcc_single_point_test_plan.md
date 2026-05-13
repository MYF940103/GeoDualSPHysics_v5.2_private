# M1 MCC Single-Point Test Plan

## Purpose

MCC should not be connected directly to the SPH triaxial workflow. A standalone or pseudo-standalone single-point driver should validate the return mapping, state update, and sign convention first.

## Driver Recommendation

Create a small material-point test harness before SPH integration:

- preferred first version: Python reference driver for rapid plotting and equations;
- second version: C++ unit-style driver calling the same MCC update helper intended for SPH;
- outputs: CSV and figures for stress path, yield residual, `p_c`, void ratio, and plastic strain.

## Test 1: Isotropic Compression and Swelling

Goal:

- validate `p'-v` behavior;
- validate `p_c` hardening;
- validate elastic unloading/reloading slope `kappa`;
- verify sign mapping for hydrostatic compression.

Expected:

- elastic response for overconsolidated loading inside the yield surface;
- virgin compression updates `p_c`;
- unloading follows the swelling/recompression slope.

## Test 2: Drained Triaxial Compression

Goal:

- verify `q-p'` path under controlled radial stress and axial strain;
- check approach to critical-state slope `q = M p'`;
- verify plastic volumetric strain sign.

Outputs:

- `q` vs axial strain;
- `p'` vs axial strain;
- `q-p'` path;
- `p_c` evolution;
- plastic volumetric strain.

## Test 3: Undrained Triaxial Compression

Goal:

- validate effective stress path under zero volumetric strain at the material point level;
- compare qualitative pore-pressure-equivalent response before returning to full u-pw SPH.

Because full SPH pore-pressure feedback is deferred, this test should be a constitutive material-point constraint, not a claim of full u-pw validation.

## Test 4: Elastic Unloading and Reloading

Goal:

- ensure no plastic update occurs inside the yield surface;
- verify no drift in `p_c`;
- verify stress returns to the expected elastic path.

## Test 5: Yield Surface Consistency

Goal:

- after each plastic step, evaluate

```text
f = q^2 + M^2 p' (p' - p_c)
```

- require `abs(f)` below tolerance;
- record iteration count and failure status.

## Test 6: Hardening Check

Goal:

- compare numerical `p_c` update against the analytical hardening relation for simple paths;
- verify monotonic increase of `p_c` under compression-positive plastic volumetric strain.

## Test 7: Stress Convention Regression

Use a stored-code stress tensor with negative diagonal compression, convert it to compression-positive MCC variables, run an elastic step, convert back, and verify the stored sign is preserved.

## Acceptance Before SPH Integration

MCC should not be inserted into the SPH path until:

- isotropic compression/swelling passes;
- drained triaxial material-point path is stable;
- undrained material-point path is qualitatively correct;
- yield residual is controlled after plastic return;
- `p' <= 0` guards are tested;
- restart/output state variables are designed.
