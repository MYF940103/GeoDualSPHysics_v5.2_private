# u-pw work window summary

Date: 2026-06-04

Workspace: `D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\src`

Branch: `u-pw`

Latest committed node at the time of writing: `a407fbd Add u-pw PR hydromechanical verification`

This note is intended as a handoff for the next work window. It records the current u-pw CPU implementation state, verification results, unresolved issues, and the main traps already encountered.

## Current Direction

The Scenario 1 self-weight consolidation test is now frozen temporarily.

Reason: its gravity-off dissipation stage has an unresolved mismatch between the initialized static stress/pore-pressure state and the momentum equation. Multiple diagnostics indicate that the issue is not simply pore-pressure diffusion, nor simply whether the hydrostatic baseline is retained. The next suggested verification target is the main u-pw paper's 1D consolidation problem with external surcharge `q0`, because the loading and coupling response are cleaner and should be easier to compare against theory.

## Current Code State

The CPU-side u-pw PR framework is implemented and currently active behind `HydroMech`.

Important source areas:

- `source/DualSphDef.h`
  - u-pw soil material parameters are stored in `SoilCte`.
  - Includes pore-water density, pore-water bulk modulus, porosity, hydraulic conductivity, and related hydromechanical material constants.

- `source/JSph.h`
  - Hydromechanical controls include:
    - `HydroMech`
    - `HydroMechInitMode`
    - `WaterTableZ` / `HydroMechInitZ`
    - `PoreDtSafety`
    - `PoreShepardRegularization`
    - `PoreShepardInterval`
    - `SoilStressRateGradCorr`

- `source/JSph.cpp`
  - XML parsing reads `HydroMechInitMode`.
  - Backward-compatible fallback: if `HydroMechInitMode` is absent, it still reads old `WaterTableMode`.
  - Supported modes:
    - `None` / `0`
    - `FreeSurface` / `1`
    - `ConstantZ` / `2`
    - `AnalyticalSelfWeight1D` / `3`
  - Important: no `PoreDiffusionOnly` switch should exist. A temporary diagnostic switch was created and then removed during this window.

- `source/JSphCpu.cpp`
  - `InitHydroMechState()` initializes pore pressure, reference pore pressure `PorePress0`, and, for `AnalyticalSelfWeight1D`, effective stress.
  - `InteractionPorePressureRateT()` computes PR pore-pressure rate:
    - compression term from `-div(v_s)`
    - seepage/diffusion term from pressure Laplacian
    - hydraulic head term only when gravity norm is non-zero
  - Pore-pressure feedback is included in `InteractionForcesFluid()` as a separate pore-pressure driving contribution, not by folding pore pressure into `sigma_total`.
  - `SoilStressRateGradCorr` support remains a positive/kept diagnostic-improvement feature.

Current PR expressions of interest:

```cpp
const double compression=-divv;
const double seepage=(khyd>0?
  2.0*khyd*lapw/(double(SoilCte.PoreWaterRho)*ghyd)
  + (gnorm>0? 2.0*khyd*lapz: 0.0)
  : 0.0);
const double rate=kwn*compression + kwn*seepage;
```

and feedback is active as:

```cpp
const bool useporefeedback=(HydroMech && porepress);
```

## Important Cleanup Already Done

The following temporary diagnostics were created during this window and then cleaned:

- `PoreDiffusionOnly` source-code switch
- `Scenario1_DiffOnly` case files/output
- `Scenario1_K0Diag` case files/output
- `Scenario1_K0GravityDiag` case files/output
- `Scenario1_S2InitDiag` case files/output

`rg` checks confirmed that `PoreDiffusionOnly`, `DiffOnly`, `K0Diag`, `K0GravityDiag`, and `S2InitDiag` do not remain in the active case directory/source code.

CPU Debug and CPU Release were rebuilt after the diagnostic switch was removed.

## Example Directory State

Main hydromechanical examples currently under:

```text
D:\MYF\SPH\GeoDualSPHysics_redevelop_f66777b\examples\Hydromechanic coupling
```

Key folders:

- `00_StaticSoilColumn_PorePressure`
  - Earlier hydrostatic pore-pressure initialization check.
  - Periodic and non-periodic pore-pressure initialization had been checked successfully.

- `01_SelfWeightConsolidation_PR`
  - Main self-weight consolidation PR verification workspace.
  - Contains current Scenario 1/2 XML, bat, support scripts, figures, and archived diagnostics.

- `02_FixedSoilColumn_PorePressure_Check`
  - Fixed-boundary soil-column pore-pressure check workspace.

Within `01_SelfWeightConsolidation_PR`, the root has been kept relatively clean:

```text
CaseSelfWeightConsolidation_Scenario1_Def.xml
CaseSelfWeightConsolidation_Scenario2_Def.xml
CaseSelfWeightConsolidation_Stage1_Def.xml
xCaseSelfWeightConsolidation_Scenario1_win64_CPU.bat
xCaseSelfWeightConsolidation_Scenario2_win64_CPU.bat
xCaseSelfWeightConsolidation_Stage1_win64_CPU.bat
figures/
support/
videos/
```

Archived diagnostic details are under:

```text
01_SelfWeightConsolidation_PR\support\diagnostics
```

## Scenario 2 Status

Scenario 2 is the stronger current verification result.

Setup:

- `HydroMechInitMode=AnalyticalSelfWeight1D`
- gravity on: `z=-9.81`
- retained hydrostatic baseline: `PorePress0` is hydrostatic pressure
- `PorePress = PorePress0 + excess`
- boundary excess pressure is initialized consistently with the ghost/projection logic
- fixed time step follows the supporting-material style: `DtFixed=1e-6`

Current conclusion:

- The PR diffusion/evolution behaves much more reasonably for Scenario 2 after the boundary initialization was corrected.
- Remaining early-time bottom-boundary discrepancy exists, especially at very early `Tv` such as about `0.005`.
- The remaining error is likely from local mDBC/boundary discretization and the mismatch between ghost-projected excess pressure and actual neighbor geometry near the impermeable bottom.
- This level was considered acceptable enough to pause Scenario 2 and move on later, but it should not be presented as a final validated result yet.

Important previous fix:

- For boundary analytical initialization, use actual-position hydrostatic pressure plus ghost/projection excess pressure.
- This keeps the hydrostatic baseline physically tied to actual elevation while enforcing undrained excess-pressure Neumann behavior through the projected state.

## Scenario 1 Status: Frozen

Scenario 1 was tested in several forms and is now frozen.

### Why it is frozen

The intended Scenario 1 logic was:

- initialize undrained self-weight excess pore pressure
- switch gravity off during dissipation
- expect the excess pore pressure to dissipate toward zero

However, in the current dynamic SPH implementation, this gravity-off setup introduces a static-balance problem:

- The initialized stress and pore-pressure state resembles a self-weight state.
- Once gravity is set to zero, the momentum equation no longer has the body force that made that state mechanically balanced.
- The skeleton responds dynamically, and the compression term in PR can dominate or distort the intended diffusion-only/analytical consolidation behavior.

### Diagnostics already tried

1. `HydraulicConductivity=0`, gravity off

Observation:

- Even with no seepage, pore pressure still changed significantly.
- This showed the source was mechanical response through `Kw/n * (-div(v_s))`, not diffusion.

2. `HydraulicConductivity=0`, gravity on

Observation:

- The same analytical self-weight state was much closer to mechanical equilibrium.
- This confirmed that the initialized state is meaningful under self-weight, but not after gravity is removed.

3. Temporary diffusion-only diagnostic

Observation:

- With skeleton feedback/motion/compression disabled, the pressure Laplacian diffusion followed the expected `Kw/n` diffusion timescale.
- This confirmed the pressure diffusion operator itself is not the primary failure mode.
- The diagnostic switch used for this was removed afterward and must not be reintroduced casually.

4. Scenario 2 initialization followed by gravity-off restart

Observation:

- Starting from a Scenario 2 state and then switching gravity off caused a strong unloading response.
- Bottom total pore pressure dropped from about `20 kPa` to around `1 kPa` by the first diagnostic output.
- Excess pore pressure became negative near the bottom.
- Conclusion: adding back the hydrostatic baseline does not solve Scenario 1; it makes the gravity-off imbalance even clearer.

### Current conclusion for Scenario 1

Do not continue tuning Scenario 1 parameters for now.

The issue is not primarily:

- Shepard on/off
- damping coefficient
- artificial viscosity
- hydrostatic baseline yes/no
- pressure diffusion term

The unresolved issue is how to reproduce the paper/supporting-material Scenario 1 mechanical constraints in this dynamic SPH implementation when gravity is removed but a self-weight-type stress/pore-pressure field remains.

## Shepard Regularization Notes

Important correction made during this work:

- Shepard regularization should not be forced on by default for all hydromechanical cases.
- Literature such as Lian 2023 suggests it is mainly appropriate for coupled flow-deformation problems with low-permeability materials and large deformation.
- Therefore it remains controlled by:

```xml
<PoreShepardRegularization value="0 or 1" />
<PoreShepardInterval value="..." />
```

Current implementation direction:

- Shepard regularizes excess pore pressure relative to `PorePress0`, not total pore pressure directly.
- `PorePress0` is then added back.
- This avoids corrupting a hydrostatic baseline when regularization is used.

Stage 1 parameter-tuning results are stored in:

```text
01_SelfWeightConsolidation_PR\support\STAGE1_PARAMETER_TUNING_SUMMARY.md
```

Useful Stage 1 combination found before Scenario 1 was frozen:

```xml
<soilproperty name="SoilDampingCoef" value="0.04" />
<soilproperty name="PoreShepardRegularization" value="1" />
<soilproperty name="PoreShepardInterval" value="40" />
```

with `Visco=0.4`.

This should be treated as a historical tuning result, not as the final recommended approach for future q0 tests.

## Boundary and mDBC Notes

For undrained impermeable boundaries, the boundary condition is interpreted as:

```text
grad(pw) dot n = 0
```

For gauge pore pressure with a hydrostatic baseline, it is cleaner to apply the Neumann/mDBC projection to excess pore pressure, while retaining the hydrostatic part separately.

Current conceptual split:

- `PorePress0`: hydrostatic/reference pore pressure baseline
- `ExcessPorePress = PorePress - PorePress0`
- mDBC-style undrained boundary projection should act on excess pore pressure
- total pore pressure is rebuilt as baseline plus projected excess

Boundary caveat:

- Even if the boundary value is physically constructed from a ghost/projection point, the SPH interaction still uses actual boundary particle coordinates in neighbor geometry.
- This can create local early-time boundary errors, especially at the bottom impermeable boundary.

## Time-Step and Coefficients

Keep strict PR coefficient:

```text
kwn = Kw / n
```

Do not use the earlier temporary harmonic/effective coefficient:

```text
(kwn * M) / (kwn + M)
```

That harmonic coefficient made some curves appear closer to Terzaghi-like behavior but is not the strict PR equation from the target paper. It should only be used if explicitly introduced later as a separate reduced/quasi-static model, not as the PR implementation.

For fixed-time-step verification matching the paper/supporting materials, use:

```xml
<parameter key="DtFixed" value="0.000001" />
```

Do not hide behavior by only tuning `PoreDtSafety`.

## Signs and Stress Convention

Current code uses a tensile-positive stress convention for the stress tensor variables.

PR compression currently uses:

```text
compression = -div(v_s)
```

This sign was checked during the diagnostics and should not be casually flipped without re-deriving the full convention of:

- effective stress rate
- pore-pressure feedback force
- velocity-gradient sign
- pressure rate

## Known Worktree Notes

As of this summary, the branch is `u-pw` and the last committed node is `a407fbd`.

There are uncommitted changes and untracked outputs under the hydromechanical example directory. Some are intended case/script/result files; some are archived diagnostics. Do not blindly run `git clean` or `git reset`.

Notable current modified/untracked hydromechanical files include:

- `01_SelfWeightConsolidation_PR/CaseSelfWeightConsolidation_Scenario1_Def.xml`
- `01_SelfWeightConsolidation_PR/xCaseSelfWeightConsolidation_Scenario1_win64_CPU.bat`
- `01_SelfWeightConsolidation_PR/support/postprocess_self_weight_consolidation.py`
- `01_SelfWeightConsolidation_PR/support/postprocess_self_weight_scenario1.py`
- `01_SelfWeightConsolidation_PR/figures/*.png`
- `01_SelfWeightConsolidation_PR/support/diagnostics/*`

Current source modification of interest after `a407fbd`:

- `source/JSphCpu.cpp`
  - analytical self-weight initialization has been adjusted to support gravity-on and gravity-off variants
  - strict PR coefficient restored
  - water-head term is excluded automatically when gravity norm is zero
  - pore-pressure feedback is active in the main force loop

## Recommended Next Task: q0 1D Consolidation

The next work window should start with the u-pw main paper's 1D consolidation case with external load `q0`.

Why this is recommended:

- It avoids the ambiguous gravity-off self-weight static-balance issue in Scenario 1.
- External surcharge loading is cleaner to define.
- It should produce a more direct coupled response for checking PR rate plus pore-pressure feedback.
- It is closer to the main paper's verification target than continuing to tune the frozen Scenario 1.

Suggested plan:

1. Re-read the q0 1D consolidation setup in the main u-pw paper and supporting material.
2. Identify:
   - geometry
   - drainage boundaries
   - impermeable boundaries
   - material parameters
   - q0 load magnitude and application method
   - analytical solution variables and nondimensional time definition
3. Decide how to apply `q0` in the current codebase:
   - external top load through boundary/force mechanism
   - prescribed load particles
   - initial stress jump plus consolidation
4. Prefer CPU first.
5. Keep `DtFixed=1e-6` for direct comparison unless the paper states otherwise.
6. Initially disable Shepard unless the paper/reference case explicitly uses filtering or unless oscillations make it necessary.
7. Track both:
   - pore pressure profiles
   - degree of consolidation
   - displacement/settlement if available in the reference

## Do Not Repeat These Pitfalls

- Do not re-add a global `PoreDiffusionOnly` switch as a normal feature.
- Do not replace strict `Kw/n` PR coefficient with an effective/harmonic storage coefficient unless explicitly implementing a separate model.
- Do not assume Scenario 1 is fixed by adding hydrostatic pressure.
- Do not treat mDBC pressure boundary values as purely local actual-position values; remember the ghost/projection split.
- Do not over-tune damping/Shepard to hide a mechanical balance issue.
- Do not use `PartBegin=0` as restart; in DualSPHysics, restart requires `PartBegin > 0`.
- For restart diagnostics, `Part_0001` was used after a single `1e-6 s` step when a near-initial state was needed.
- Do not delete untracked diagnostics/results blindly; several are useful records.

## Quick Status for Next Window

Recommended opening actions:

1. Read this file.
2. Read:
   - `papers/u-pw/a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.md`
   - `papers/u-pw/u-pw supporting material.md`
   - `papers/u-pw/An SPH framework for drained and undrained loading.md`
   - `papers/u-pw/Single-layer soil-water coupled SPH method and its application.md`
3. Inspect `source/JSphCpu.cpp` around:
   - `InitHydroMechState()`
   - `InteractionPorePressureRateT()`
   - pore-pressure feedback in `InteractionForcesFluid()`
4. Use `01_SelfWeightConsolidation_PR` only as historical reference.
5. Create a new q0 consolidation case instead of continuing Scenario 1.
