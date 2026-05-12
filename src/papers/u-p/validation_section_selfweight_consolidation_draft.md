# Self-Weight Consolidation Validation Section Draft

Date: 2026-05-12

## 1. Overview of Self-Weight Consolidation Validation

The self-weight consolidation validation is organized as two complementary
Supporting-Materials-style tests of the current u-pw PR implementation.

Scenario 2 verifies the long-time drainage trend when mechanical body gravity
remains active after the undrained stage. This test is the closest match to a
quantitative one-dimensional consolidation comparison, so it is reported
against both the nominal Supporting Materials analytical reference and a
calibrated effective time-factor reference.

Scenario 1 verifies the staged response in which self-weight pore pressure is
generated first, then the mechanical body force is removed while hydraulic
gravity remains active and drainage proceeds. The validated GPU route uses the
single-run `BodyGravityStopTime` workflow. Because this dynamic workflow does
not exactly impose an instantaneous Eq.(4) initial pressure profile, Scenario 1
is treated as a stability and drainage-to-equilibrium validation rather than a
strict analytical-profile reproduction.

Together, the two tests exercise the production u-pw PR path:

- pore pressure state, rate, diagnostics, and output;
- top-drained and bottom no-flux hydraulic correction;
- difference-gradient feedback operator;
- hydromechanical damping;
- excess-pressure Shepard regularization;
- GPU pressure update and `dt_pore` restriction;
- mechanical and hydraulic gravity decoupling.

## 2. Numerical Setup and Production Configuration

The paper-compatible validation line uses the production hydraulic boundary and
feedback settings:

| Setting | Value / status |
|---|---|
| `PorePressureBoundaryOperator` | `0`, legacy production layer correction |
| `PorePressureFeedback` | `1` |
| `PorePressureFeedbackMode` | `1`, excess-pressure feedback |
| `PorePressureFeedbackOperator` | `1`, difference-gradient operator |
| `PorePressureShepard` | `1` |
| `PorePressureShepardMode` | `1`, excess-pressure regularization |
| `PorePressureShepardInterval` | `10` |
| `HydromechDamping` | `1` |
| `HydromechDampingXi` | `0.05` for the paper-compatible GPU line |
| `PorePressureDtSafety` | `0.20` |
| `HydraulicGravity` | `(0,0,-9.81)` |

Experimental boundary modes remain available for diagnostics only:

- mode `1`: simple operator-level ghost treatment, GPU-supported but
  experimental;
- mode `2`: CPU-only hydraulic mDBC boundary-particle prototype;
- corrected-gradient PR diagnostics: CPU diagnostic only, not production.

## 3. Scenario 2: Calibrated Analytical-Reference Comparison

Scenario 2 keeps mechanical body gravity active after drainage begins. Total
pore pressure should trend toward the hydrostatic profile while excess pore
pressure dissipates.

The final paper figure set is stored in:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/PaperFigures_SelfWeightScenario2/
```

The nominal analytical reference uses the Supporting Materials Eq.(4)
undrained self-weight excess profile and the one-dimensional top-drained,
bottom-no-flux cosine eigenbasis. This reference captures the correct
dissipation trend, but the fully coupled SPH run shows a modestly faster
apparent dissipation rate.

An effective time-factor calibration,

```text
cv_eff = 1.1175 cv
```

reduces the bottom excess-pressure relative RMSE from about `7.59%` to about
`1.98%`. This factor is not interpreted as material-property retuning. It is a
compact measure of the difference between the quasi-static one-dimensional
reference and the dynamic coupled SPH response, including explicit volumetric
storage, damping, Shepard regularization, and particle operator effects.

## 4. Scenario 1: Mechanical-Gravity-Switch Drainage Validation

Scenario 1 was validated with the single-run `BodyGravityStopTime` route. The
simulation starts with mechanical body gravity and hydraulic gravity both
active. At `t=0.002 s`, the GPU path stops the mechanical body force while
leaving `HydraulicGravity` active. Top drainage is activated at the same time.

The final paper figure set is stored in:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/PaperFigures_Scenario1_BodyGravityStop/
```

The validation sequence was:

- S1-1b short CPU/GPU parity after adding GPU `BodyGravityStopTime` support;
- S1-2 GPU medium smokes to `0.05 s` and `0.2 s`;
- S1-3 GPU long run to `3.600001 s`;
- S1-4 paper figures and reference-context note.

The long run completed with `code=0`, `excluded=0`, and `3,775,438` steps. The
final `ExcessPorePress` maxAbs was `1.645 Pa`, the final bottom excess mean was
`-1.645 Pa`, and the final maximum velocity was approximately
`2.997e-7 m/s`. The top-drained residual was about `1.4e-9 Pa`, and the bottom
no-flux proxy was about `1.87e-6 Pa`.

The S1-3 long run also agrees with the S1-2 medium run at the shared
`0.2 s` frame:

| Quantity | S1-2 medium | S1-3 long |
|---|---:|---:|
| `ExcessPorePress` maxAbs [Pa] | `27.3597` | `27.3566` |
| bottom excess mean [Pa] | `-27.3506` | `-27.3475` |
| max velocity [m/s] | `5.59964e-6` | `5.59949e-6` |

## 5. Boundary-Condition Audit and Production-Mode Justification

The boundary audit was performed because the Scenario 2 nominal analytical
comparison retained a bottom-excess discrepancy of about `7.6%`. The audit
showed that this discrepancy is not primarily controlled by the legacy
post-update layer correction.

Key findings:

- GPU mode `1` and legacy mode `0` produce nearly identical Scenario 2 long-run
  bottom excess RMSE.
- CPU mode `2` successfully lets reconstructed hydraulic boundary particles
  enter `LapPorePress` and `LapZ`, but it does not improve hydrostatic,
  pressure-only, or self-weight short metrics.
- Corrected-gradient PR diagnostics did not improve the relevant hydrostatic
  or self-weight metrics and remain deferred.

Therefore the production validation uses `PorePressureBoundaryOperator=0`.
Mode `1` and mode `2` remain experimental diagnostic paths.

## 6. GPU Stability and Computational Performance

The GPU implementation has now covered the production u-pw PR path needed for
the self-weight validation:

- G1: passive pore pressure state and output;
- G2: PR diagnostic fields;
- G3: pressure update and `dt_pore`;
- G4: top drained / bottom no-flux pressure-only parity;
- G5: difference-gradient feedback operator;
- G6: hydromechanical damping and pore-pressure Shepard;
- G7/G8/G9/G9b: Scenario 2 short, medium, and long GPU runs;
- S1-1b/S1-2/S1-3/S1-4: Scenario 1 gravity-switch route.

Scenario 2 G7 short parity reported a GPU speedup of about `9.6x` over CPU for
the short coupled window. Longer Scenario 1 and Scenario 2 runs were performed
on GPU only after short/medium gates passed.

## 7. Summary of Validation Findings

Table 1. Validation cases and objectives.

| Case | Purpose | Main configuration | Reference / comparison | Key outcome | Status |
|---|---|---|---|---|---|
| Scenario 2 | Long-time self-weight consolidation with body gravity retained | GPU `xi=0.05`, feedback operator `1`, Shepard, damping, mode `0` boundary | Nominal Supporting Materials 1D reference and calibrated effective reference | Nominal trend captured; `cv_eff=1.1175 cv` reduces bottom relative RMSE from `7.59%` to `1.98%` | Paper-compatible quantitative validation |
| Scenario 1 | Gravity-switch drainage-to-equilibrium stability | GPU `BodyGravityStopTime=0.002`, hydraulic gravity retained, mode `0` boundary | Stability, boundary residuals, short/medium/long consistency; reference context only | `code=0`, `excluded=0`, final excess maxAbs `1.645 Pa`, final max velocity `2.997e-7 m/s` | Paper-compatible stability validation |
| Boundary audit | Test whether boundary correction controls Scenario 2 discrepancy | Modes `0`, `1`, `2` | Hydrostatic, pressure-only, self-weight diagnostics | No material improvement over mode `0` | Experimental paths retained, production unchanged |

Table 2. Scenario 2 metrics.

| Reference | Bottom excess RMSE | Relative RMSE | Interpretation |
|---|---:|---:|---|
| Nominal analytical reference | `550.17 Pa` | `7.59%` | Captures trend but underestimates apparent dissipation rate |
| Calibrated effective reference | `135.56 Pa` | `1.98%` | Effective time-factor sensitivity, not material retuning |

Table 3. Scenario 1 metrics.

| Metric | Value | Interpretation |
|---|---:|---|
| GPU long-run code / excluded | `0 / 0` | Stable run, no particle exclusion |
| Runtime / steps / frames | `8841.97 s / 3,775,438 / 37` | Completed long-run gate |
| Final `ExcessPorePress` maxAbs | `1.645 Pa` | Dissipated to small residual |
| Final bottom excess mean | `-1.645 Pa` | Small residual at no-flux side |
| Final top drained excess maxAbs | `1.4e-9 Pa` | Drained top remains enforced |
| Final bottom no-flux proxy | `1.87e-6 Pa` | Stable no-flux proxy |
| Final max velocity | `2.997e-7 m/s` | Near-static final state |

Table 4. Boundary operator status.

| Mode | Description | CPU support | GPU support | Production status | Reason |
|---|---|---|---|---|---|
| `0` | Legacy layer correction | Yes | Yes | Default production | Stable and sufficient for current paper validation |
| `1` | Simple operator-level virtual ghost | Yes | Yes | Experimental | Does not improve Scenario 2 long-run discrepancy |
| `2` | Hydraulic mDBC boundary-particle prototype | Yes | No, hard error | CPU-only experimental | Stable but not improving hydrostatic or self-weight metrics |
| corrected-gradient | Material-only corrected PR diagnostics | CPU diagnostic only | No | Deferred | No demonstrated benefit for current validation |

## 8. Limitations and Next Benchmarks

The self-weight validation is now closed for the current paper line. The
remaining limitations should be stated explicitly:

- Scenario 2 uses a calibrated effective reference as an interpretation aid,
  not as a material-parameter change.
- Scenario 1 is a drainage-to-equilibrium stability validation, not a strict
  analytical-profile reproduction.
- The restart route remains deferred because the `BodyGravityStopTime` route is
  stable and avoids GPU restart-state mapping risk.
- Experimental boundary modes and corrected-gradient operators are not promoted
  to production.

Recommended next benchmark:

1. Cryer problem if the next goal is pressure-boundary / poroelastic benchmark
   coverage.
2. Undrained triaxial test if the next goal is stress-path and constitutive
   response.
3. Retrogressive slope only after benchmark coverage is sufficient, unless the
   paper structure requires the application case first.

## Figure and Table Map

### Recommended Main Text Figures

| Manuscript figure | Source file(s) | Recommended title | Placement |
|---|---|---|---|
| Figure 1 | Scenario 2 `figure1_bottom_excess_time`, `figure2_excess_profiles` | Self-weight Scenario 2 consolidation against nominal and effective references | Main text |
| Figure 2 | Scenario 2 `figure5_relative_error_time`, `figure6_cv_sensitivity` | Effective time-factor sensitivity in Scenario 2 | Main text or supplementary, depending on space |
| Figure 3 | Scenario 1 `figure1_bottom_excess_time`, `figure2_excess_decay`, `figure5_velocity_decay` | Scenario 1 gravity-switch drainage stability | Main text |
| Figure 4 | Scenario 1 `figure6_boundary_checks`, Scenario 2 boundary-mode summary table | Boundary residuals and production-mode justification | Main text or supplementary |

### Supplementary Figures

| Supplementary figure | Source file(s) | Recommended title |
|---|---|---|
| S1 | Scenario 2 `figure3_total_pore_pressure_profiles`, `figure4_excess_envelope_decay` | Scenario 2 total pressure and envelope decay |
| S2 | Scenario 1 `figure3_excess_profiles`, `figure4_total_pore_pressure_profiles` | Scenario 1 profile evolution |
| S3 | Scenario 1 `figure7_short_medium_long_consistency` | Scenario 1 short, medium, and long consistency |
| S4 | Scenario 1 `figure8_rate_contributions` | Scenario 1 PR rate contribution diagnostics |
| S5 | Boundary audit mode table and H1/O1 figures | Hydraulic boundary audit diagnostics |

## Main-Text Paragraph Drafts

### Validation Overview

The self-weight consolidation tests were used to validate the coupled u-pw PR
implementation under drainage paths that exercise the pore-pressure update,
hydraulic boundary conditions, feedback acceleration, hydromechanical damping,
and excess-pressure Shepard regularization. Two complementary scenarios were
considered. Scenario 2 retains mechanical body gravity during drainage and is
used for comparison with a one-dimensional consolidation reference. Scenario 1
removes the mechanical body force after the undrained self-weight stage while
retaining hydraulic gravity, and is used as a staged drainage-to-equilibrium
stability test.

### Scenario 2

In Scenario 2, the nominal one-dimensional consolidation solution reproduced
the overall dissipation trend, but the fully coupled SPH response showed a
slightly faster apparent drainage rate. Using the nominal reference, the bottom
excess-pressure relative RMSE was approximately 7.6%. A modest effective
time-factor adjustment, `cv_eff = 1.1175 cv`, reduced this value to
approximately 2.0%. This adjustment is not interpreted as a permeability or
material-parameter recalibration; rather, it summarizes the difference between
the quasi-static analytical reduction and the dynamic coupled SPH response,
including explicit volumetric storage, damping, Shepard regularization, and
particle-discrete operator effects.

### Scenario 1

In Scenario 1, the mechanical body force was stopped after the undrained
self-weight stage, while hydraulic gravity remained active. The GPU
implementation completed the 3.6 s drainage simulation with no particle
exclusion. The excess pore pressure decayed to a final maximum magnitude of
approximately 1.65 Pa, and the maximum velocity decreased to approximately
`3.0e-7 m/s`. The top-drained residual and bottom no-flux proxy remained small,
indicating that the gravity-switch drainage workflow is stable in the coupled
GPU implementation.

### Boundary Audit

Additional boundary-operator audits were performed to determine whether the
remaining Scenario 2 discrepancy was caused by the legacy hydraulic boundary
projection. A simple operator-level ghost treatment and a CPU-only hydraulic
mDBC boundary-particle prototype both remained stable, but neither materially
reduced the Scenario 2 analytical error. The production validation therefore
uses the legacy mode `0` boundary treatment, while modes `1` and `2` are kept as
experimental diagnostics.

### Concluding Validation Paragraph

The two self-weight scenarios provide complementary evidence for the current
production u-pw PR path. Scenario 2 verifies the long-time consolidation trend
and quantifies the effective time-factor sensitivity relative to the nominal
one-dimensional reference. Scenario 1 verifies the stability of the mechanical
gravity switch and the subsequent drainage-to-equilibrium response. Together
with the boundary audit, these results support retaining the current production
configuration for the self-weight validation while deferring corrected-gradient
and hydraulic boundary-particle production operators to future targeted studies.
