# T3 Flexible Confinement Implementation Plan

## Objective

T3 should implement the smallest CPU-only source changes needed to turn the current `FlexibleConfiningStress` route into a diagnosable triaxial confinement candidate. It should not implement MCC, full paper reproduction, GPU support, or Cryer boundary work.

## Principle

Keep the legacy behavior as the default. New diagnostics and selectors must be opt-in so existing cases are unchanged.

## Planned Source Tasks

1. Add kernel completeness `f_i` diagnostic.
   - Compute `f_i = sum_j (m_j/rho_j) W_ij`.
   - Report summary/histogram.
   - Optionally write per-particle diagnostic CSV for small cases.

2. Add geometric cylinder classification.
   - Axis, center, radius, height.
   - Classify lateral, top cap, bottom cap, edge ring, interior.
   - Diagnostic-only at first.

3. Add optional near-boundary selector.
   - Off by default.
   - Candidate rule: `f_i <= threshold`.
   - Initial threshold: `0.70` for 3D diagnostics.

4. Add optional lateral-only selector.
   - Off by default.
   - Candidate rule: target mk and lateral class.
   - Cap and edge-ring exclusion by default.

5. Extend diagnostics.
   - Selected count.
   - Cap false-positive count.
   - Radial acceleration projection.
   - Axial leakage.
   - Net force.
   - COM acceleration.
   - Symmetry residual.

6. Preserve CPU first.
   - GPU remains hard-error for `FlexibleConfiningStress=1`.
   - No GPU port until CPU confinement-only and axial compression smokes pass.

## Proposed XML Controls

Names are provisional and should be refined during source implementation:

```xml
<parameter key="ConfiningStressDiagnostics" value="1" />
<parameter key="ConfiningStressFiDiagnostics" value="1" />
<parameter key="ConfiningStressFiThreshold" value="0.70" />
<parameter key="ConfiningStressSelector" value="0" />
<parameter key="ConfiningStressUseFiSelector" value="0" />
<parameter key="ConfiningStressUseCylinderSelector" value="0" />
<parameter key="ConfiningStressCylinderAxis" value="0 0 1" />
<parameter key="ConfiningStressCylinderCenter" value="0 0 0" />
<parameter key="ConfiningStressCylinderRadius" value="0.025" />
<parameter key="ConfiningStressCylinderHeight" value="0.100" />
<parameter key="ConfiningStressCylinderCapMargin" value="auto" />
```

Legacy `FlexibleConfiningStress=1` without selectors should behave as it does today.

## Tests

### Test 1: Cylinder Confinement-Only Smoke

- CPU Release only.
- No axial loading.
- Ramped `ConfiningStressP0`.
- Check inward lateral acceleration, cap leakage, net force, COM acceleration, and velocity decay.

### Test 2: Axial Compression Plus Flexible Confinement

- CPU Release short smoke.
- Same reduced geometry family as T1 or a smoother cylinder if available.
- Compare against T1 fixed-side route.
- Record pore pressure, stress proxy, velocity, and confinement diagnostics.

### Test 3: Stress-Path Postprocessing Upgrade

- Improve `p'` and `q` extraction.
- Define central measurement region.
- Separate boundary/cap/platen particles from soil material.

## Not In T3

- MCC implementation.
- Full paper reproduction.
- Parameter sensitivity.
- GPU implementation.
- Cryer boundary work.
- Deprecated Cryer modes 5/6/7/8.

## Success Criteria

T3 should be considered successful if:

1. diagnostics identify a coherent lateral boundary layer;
2. cap leakage is small or excluded;
3. confinement-only smoke has inward radial acceleration and small COM drift;
4. axial compression plus confinement completes with `code=0`, `excluded=0`, no NaN/Inf;
5. pore pressure and stress-path proxies are interpretable;
6. defaults preserve old behavior.

If these fail, do not proceed to MCC or paper comparison. Fix confinement geometry/selection first.
