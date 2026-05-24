# Retrogressive slope failure sensitivity notes

Date: 2026-05-23

This note records the conclusions from the GPU release comparison cases that
were removed after inspection. The reference setup used restart from the
stable initial stress state, `TimeMax=10 s`, `DensityDT=3`, `hdp=2.16`, and
artificial stress enabled.

## Artificial viscosity

Cases: `cmp_base`, `cmp_visc015`, `cmp_visc020`, `cmp_visc030`.

Increasing artificial viscosity mainly reduced the runout distance and kinetic
spread. It did not fundamentally reduce the fragmentation/cracking degree.
Therefore artificial viscosity is not considered the primary control factor for
the excessive fragmentation currently observed.

## Drucker-Prager mapping and strength scale

Cases: `cmp_dp3d`, `cmp_coh115`.

Changing `DPCtes` to the 3D mapping suppressed excessive fragmentation to some
extent. However, this is not physically consistent for the present 2D plane
strain simulation. Although Bui 2021 CG reports the 3D mapping formula, the 2D
simulation should retain the original 2D mapping configuration.

Increasing cohesion and residual cohesion by about `2/sqrt(3) = 1.1547`
produced a result close to the 3D mapping case, confirming that the difference
is largely a DP strength-scale effect rather than a distinct mechanism.

## Artificial stress

All comparison cases still showed tensile instability or cracking to some
degree. The current default artificial stress parameters appear too weak for
this retrogressive slope failure setup, although earlier sensitivity tests
showed that changing the exponent alone has limited influence.

## Working conclusions

1. Artificial viscosity is not the main source of excessive fragmentation.
2. The 3D DP mapping can mask the issue but should not be adopted for this 2D
   case.
3. A pure cohesion-scale increase reproduces much of the 3D DP effect, so the
   DP strength level remains an important diagnostic axis.
4. The remaining problem is more likely related to the interaction between
   tensile instability control, stress/strength evolution, and local failure
   localization than to artificial viscosity alone.

## Artificial stress sensitivity after Kplastic restart reset

Date: 2026-05-23

After changing the restart logic so that the failure stage inherits `Sigma` but
resets `Kplastic`, the excessive softening was clearly reduced. However,
reverse internal cracking still appeared inside post-yield blocks.

At `hdp = 2.16`, GPU release comparison cases were run to `t = 5 s` with:

- `ArtificialStressCoef = 0.7`, `ArtificialStressExp = 4`
- `ArtificialStressCoef = 0.9`, `ArtificialStressExp = 4`
- `ArtificialStressCoef = 1.0`, `ArtificialStressExp = 4`
- `ArtificialStressCoef = 1.0`, `ArtificialStressExp = 2.55`

The default reset-restart case with `ArtificialStressCoef = 0.5` and
`ArtificialStressExp = 4` was used as the baseline.

All comparison cases completed without excluded particles. Increasing the
artificial stress coefficient from 0.5 to 1.0 did not materially remove the
reverse high-plasticity cracking bands inside the sliding blocks. Using the
lower exponent `2.55`, which gives the artificial stress a broader kernel-ratio
effect than exponent `4`, slightly increased the amount of high-plasticity
material in the current 5 s comparison.

Current conclusion: once inherited `Kplastic` is reset, simply increasing the
Bui artificial stress strength is not sufficient to recover the more coherent
post-yield blocks shown in the reference figures. The remaining reverse cracking
is likely not controlled by artificial stress magnitude alone.

The temporary artificial-stress comparison XML, BAT, run-log, and output
directories were removed after review. The summary figure
`ArtificialStressSensitivity_Kplastic_5s.png` is retained.

## Softening regularization diagnostics

Date: 2026-05-23

GPU release comparison cases were run to `t = 5 s` from the same reset-restart
state, with `DensityDT = 3`, `hdp = 2.16`, artificial stress enabled, and
default artificial stress parameters.

Test set:

- Reduced cohesion softening rate: `n_coh = 2`, `3`, `5`
- Increased residual cohesion: `coh_r = 2.0 kPa`, `2.5 kPa`, `3.0 kPa`
- Diagnostic code test: use kernel-weighted `Kplastic_bar` only in the
  softening law, while continuing to save the original local `Kplastic`

Final `t = 5 s` metrics:

| case | Kplastic > 1 (%) | Kplastic p99 | SigmaMax > 20 kPa (%) | SigmaMax max (kPa) | mean cohesion (kPa) |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline `n_coh=5`, `coh_r=1.5 kPa` | 15.47 | 9.20 | 3.02 | 75.07 | 12.60 |
| `n_coh=2` | 11.02 | 8.36 | 2.90 | 61.43 | 12.94 |
| `n_coh=3` | 13.84 | 8.70 | 2.60 | 67.60 | 12.71 |
| `coh_r=2.0 kPa` | 14.86 | 8.56 | 2.82 | 67.63 | 12.72 |
| `coh_r=2.5 kPa` | 14.37 | 8.14 | 2.87 | 58.83 | 12.85 |
| `coh_r=3.0 kPa` | 14.00 | 7.68 | 2.71 | 60.72 | 12.96 |
| `Kplastic_bar` softening | 22.03 | 9.12 | 2.11 | 51.05 | 11.22 |

Conclusions:

1. Lowering `n_coh` and increasing `coh_r` both reduce the most severe
   high-plasticity tail and tensile peak stresses, but subsequent visual
   inspection showed that these material-parameter changes do not remove the
   reverse internal cracking.
2. `coh_r = 2.5-3.0 kPa` is the cleaner purely material adjustment in this
   batch because it reduces `Kplastic p99` and peak `SoilSigmaMax` without
   introducing a new numerical mechanism, but it is not sufficient as a final
   remedy.
3. The `Kplastic_bar` diagnostic lowers high tensile stress most strongly, but
   it also broadens the plastified region and can produce excessive particle
   fragmentation. This supports the suspicion that the local softening variable
   is too sharp, while also showing that simple one-pass averaging is a
   numerical smoothing diagnostic rather than the final solution.

The summary figure `SofteningRegularization_Kplastic_5s.png` and table
`SofteningRegularization_summary.csv` are retained together with the comparison
XML/BAT/output files for inspection.

Update after visual inspection: the `n_coh` and `coh_r` comparison XML, BAT,
run-log, and output directories were removed. The `Kplastic_bar` switch and its
diagnostic case were retained for further observation.

## Return-mapping diagnostics

Date: 2026-05-23

A GPU release diagnostic case `CaseRetroSlope_Bui2021_rm_diag` was added and
run to `t = 5 s`. It saves the following additional fields:

- `SoilI1Trial`, `SoilJ2Trial`, `SoilYieldFTrial`, `SoilDk`
- `SoilI1FinalRM`, `SoilJ2FinalRM`, `SoilCapDelta`, `SoilFscale`

Key observations:

1. The reverse internal bands are not generated by the tensile cap or the final
   deviatoric stress scaling in the current run. `SoilCapDelta = 0` and
   `SoilFscale` remains essentially `1` in the high-plasticity/low-`J2` bands.
2. The low `SoilJ2` value in those bands is the return-mapped residual shear
   state. Since the current undrained case uses `phi = 0`, `dlt = 0`, and
   `DPCtes = 3`, the yield function reduces to `sqrt(J2) - c = 0`. With
   `coh_r = 1.5 kPa`, fully softened material is projected to
   `J2 = coh_r^2 = 2.25e6 Pa^2`, matching the observed low-`J2` band.
3. At `t = 5 s`, particles with `Kplastic > 0.5` and `J2_final < 5e7` have
   median `J2_trial = 5.69e6`, median `J2_final = 2.25e6`, median
   `SoilYieldFTrial = 805 Pa`, and median `SoilDk = 5.54e-5`.

Current conclusion: the reverse bands are more likely fully softened residual
shear bands that are being over-localized inside later sliding blocks, not a
direct tensile-cap artifact. The useful diagnostic axis is therefore the spatial
pattern of new `SoilDk` and trial overstress before return mapping, rather than
final `SoilJ2` alone.

The summary table `ReturnMappingDiagnostics_summary.csv` and figure
`ReturnMappingDiagnostics_5s.png` are retained.

### `SoilDk` / `SoilYieldFTrial` burst tracking

Date: 2026-05-23

The diagnostic output was post-processed around `t = 2.5-3.5 s` to check
whether the reverse residual bands are preceded by concentrated plastic
increments. The following files were generated:

- `DkYieldFTrial_2p5_3p5_analysis.png`
- `DkYieldFTrial_2p5_3p5_stats.csv`
- `DkYieldFTrial_first_residual_crossing.png`
- `DkYieldFTrial_first_residual_crossing_stats.csv`

Key observations:

1. At `t = 2.5`, `3.0`, and `3.5 s`, the top `1%` `SoilDk` particles and the
   top `1%` `SoilYieldFTrial` particles are all particles that later belong to
   the final high-plasticity/low-`J2` residual bands.
2. Tracking particle IDs shows that all 1901 final residual-band particles
   entered the residual state in saved frames where their `SoilDk` and
   `SoilYieldFTrial` ranks were high. Across all first residual crossings, the
   median rank is about the `95.94` percentile for both fields; `96.37%` of the
   particles cross with `SoilDk` above the `90` percentile, and `61.28%` cross
   above the `95` percentile.
3. For the specific `2.5-3.5 s` interval, 295 particles first enter the final
   residual-band set. Their median `SoilDk` rank is about the `95.78`
   percentile, with median `SoilDk = 1.07e-4` and median
   `SoilYieldFTrial = 1.55 kPa`.

Interpretation:

The reverse bands are not produced by a single catastrophic plastic increment.
The absolute per-step `SoilDk` is modest, but the increments are strongly
localized and repeatedly concentrate on the same future residual-band particle
sets. This supports the hypothesis that the current local softening plus
return-mapping update is allowing narrow residual shear bands to nucleate inside
later sliding blocks too easily.

Diagnostic cleanup reminder: the return-mapping diagnostic XML option,
temporary GPU arrays, and diagnostic VTK output fields should be removed after
this mechanism study is complete so the production code path remains unchanged.

### Velocity-gradient check of reverse residual bands

Date: 2026-05-23

The diagnostic VTK files were further post-processed using a local affine fit
of the saved particle velocity field over a radius of `0.45 m`, approximately
the Wendland support radius for the current `Dp = 0.1 m`, `hdp = 2.16` setup.
The goal was to determine whether the reverse bands are only stress/softening
colour bands, or whether they coincide with actual local velocity shear.

Generated files:

- `DkVelocityGradient_2p5_3p5_analysis.png`
- `DkVelocityGradient_2p5_3p5_stats.csv`

Key observations:

1. At `t = 2.5`, `3.0`, and `3.5 s`, all top `1%` local shear-rate particles
   are also particles that later belong to the final high-plasticity/low-`J2`
   residual bands.
2. The top `1%` `SoilDk` set strongly overlaps the top `1%` local shear-rate
   set: about `65.5%` at `2.5 s`, `61.1%` at `3.0 s`, and `69.0%` at `3.5 s`.
3. The top `1%` `SoilDk` particles have median local shear-rate ranks of
   approximately the `99.35-99.50` percentile.
4. Final residual-band particles have median local shear rates of about
   `0.74-1.07 s^-1` during `2.5-3.5 s`, while particles outside those bands
   have median values of only about `0.0013-0.0017 s^-1`.

Updated mechanism interpretation:

The reverse bands are active local shear-localization zones, not merely a
visual artefact of plotting `Kplastic` or `J2`. The apparent mechanism is a
positive feedback loop:

`local velocity shear -> trial overstress -> high SoilDk -> cohesion reduction -> easier renewed localization`.

The problem is therefore best classified as excessive post-yield localization
of the current local strain-softening model inside later sliding blocks. This
is consistent with the discussion in Bui and Nguyen (2021): the benchmark uses
a classical strain-softening constitutive model without an intrinsic material
length scale, and relies on the SPH kernel support as the numerical length
scale. Our current pointwise `Kplastic` softening is probably too sharp relative
to the regularization implied by that kernel scale.

## Diagnostic cleanup inventory

Date: 2026-05-23

After the mechanism checks above, the temporary diagnostic code paths were
removed from the production source:

- `SoilReturnMappingDiagnostics` XML switch and GPU diagnostic arrays.
- `SoilSofteningKplasticAveraging` XML switch and temporary `Kplastic_bar`
  GPU path.
- Extra diagnostic VTK fields used only for the return-mapping study:
  `SoilI1Trial`, `SoilJ2Trial`, `SoilYieldFTrial`, `SoilDk`,
  `SoilI1FinalRM`, `SoilJ2FinalRM`, `SoilCapDelta`, and `SoilFscale`.

The temporary diagnostic XML/BAT/log/output folders can be deleted after this
note is saved. The retained evidence files are the PNG and CSV summaries listed
in the sections above.

## Follow-up stabilization tests

Date: 2026-05-23

After the return-mapping and velocity-gradient diagnostics, three controlled
test hooks were added and evaluated in the GPU release solver. All hooks are
disabled or neutral by default, so the default XML files keep the previous
behaviour unless the new parameters are explicitly supplied.

### Scheme 4: stress-rate kernel-gradient correction

Test case:

- `CaseRetroSlope_Bui2021_failure_gradcorr_Def.xml`
- `xCaseRetroSlope_Bui2021_failure_gradcorr_win64_GPU.bat`
- output: `CaseRetroSlope_Bui2021_failure_gradcorr_GPU_out`

Configuration:

- `SoilStressRateGradCorr = 1`
- `TimeMax = 5 s`
- default hdp, DDT, artificial stress, and softening settings otherwise

Result:

- The run reached `t = 5.000004 s`.
- `Excluded particles = 22`, all due to `RhopOut`.
- The default GPU failure run reached `t = 5.000055 s` with
  `Excluded particles = 0`.

Interpretation:

The direct Bonet-style correction of the velocity-gradient operator in the
stress-rate path is not a good default for this case. It did not immediately
solve the reverse-band problem and made density/exclusion stability worse in
the 5 s check. Keep it only as an optional diagnostic switch unless a more
careful boundary/free-surface treatment is added.

### Scheme 3: return-mapping plastic-increment cap

Test case:

- `CaseRetroSlope_Bui2021_failure_dklim001_Def.xml`
- `xCaseRetroSlope_Bui2021_failure_dklim001_win64_GPU.bat`
- output: `CaseRetroSlope_Bui2021_failure_dklim001_GPU_out`

Configuration:

- `SoilPlasticDkLimit = 0.001`
- `TimeMax = 5 s`
- `SoilStressRateGradCorr = 0`
- default hdp, DDT, artificial stress, and softening settings otherwise

Result:

- The run reached `t = 5.000055 s`.
- `Excluded particles = 0`.

Interpretation:

The plastic-increment cap is numerically stable in this first check. It is a
useful next diagnostic because it targets the positive feedback identified in
the diagnostics: localized velocity shear -> trial overstress -> localized
plastic increment -> faster strength loss. Visual comparison of the VTK output
is still needed before deciding whether this is physically acceptable.

### Scheme 2: softening-rate length-scale calibration hook

Test case:

- `CaseRetroSlope_Bui2021_failure_softscale050_Def.xml`
- `xCaseRetroSlope_Bui2021_failure_softscale050_win64_GPU.bat`
- output: `CaseRetroSlope_Bui2021_failure_softscale050_GPU_out`

Configuration:

- `SoilSofteningRateScale = 0.5`
- `TimeMax = 5 s`
- `SoilStressRateGradCorr = 0`
- default hdp, DDT, artificial stress, and softening settings otherwise

Result:

- The run reached `t = 5.000078 s`.
- `Excluded particles = 0`.

Interpretation:

The neutral implementation is working: `SoilSofteningRateScale = 1` keeps the
old softening law, while values below one slow the exponential softening rate.
This is the cleanest hook for later support-domain or characteristic-length
recalibration. The current `0.5` test is only a first numerical check, not yet
a calibrated material model.

### Cleanup after visual comparison

Date: 2026-05-23

Visual comparison showed that Scheme 3 and Scheme 2 did not suppress the
non-physical reverse crack propagation. Their temporary XML parameters and code
hooks were therefore removed:

- `SoilPlasticDkLimit`
- `SoilSofteningRateScale`

The corresponding `dklim001` and `softscale050` XML/BAT/output folders were
also deleted. Scheme 4, `SoilStressRateGradCorr`, is kept for now because it
appeared to slightly improve the internal reverse cracking pattern, although it
still caused particle exclusion near the bottom boundary in the first 5 s test.

### mDBC corrector scheduling check with gradient correction

Date: 2026-05-23

The Geo branch mDBC scheduling was aligned with the explicit corrector switch:
mDBC boundary correction is applied in Verlet and Symplectic predictor, but in
Symplectic corrector only when `MDBCCorrector=1`. The `CDBC` branch is
unchanged.

The gradient-correction test was rerun with:

- `CaseRetroSlope_Bui2021_failure_gradcorr_Def.xml`
- `SoilStressRateGradCorr = 1`
- `MDBCCorrector` absent, therefore logged as `mDBC-Corrector=False`
- `TimeMax = 5 s`

Result:

- The run reached `t = 5.000030 s`.
- `Excluded particles = 17`, all due to `RhopOut`.
- The excluded particles in `PartFluidOut_0044.vtk` are still close to the
  bottom boundary/sliding base: `z = 0.088-0.323 m`, `x = 25.28-34.55 m`.

Interpretation:

Skipping the repeated mDBC correction in the Symplectic corrector reduced the
gradient-correction out-particle count from the earlier 22 to 17, but it did
not eliminate the bottom-boundary density instability. The remaining issue is
therefore probably not only the repeated mDBC scheduling; the interaction
between gradient correction, bottom boundary extrapolation, DDT, and artificial
stress still needs to be isolated.
