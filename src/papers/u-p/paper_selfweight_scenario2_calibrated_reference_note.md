# Calibrated Reference Note for Self-Weight Scenario 2

Date: 2026-05-12

## Purpose

This note documents the paper-figure reference lines used for the self-weight
Scenario 2 GPU long-run validation. The figures compare the GPU `xi=0.05`
result against both the nominal Supporting Materials one-dimensional
consolidation solution and a calibrated effective time-factor reference.

The figure set is stored in:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/PaperFigures_SelfWeightScenario2/
```

## Nominal Analytical Solution

The nominal reference uses the Supporting Materials Eq. (4) undrained
self-weight excess profile as the initial condition and the top-drained /
bottom-no-flux eigenbasis for a one-dimensional consolidation column:

```text
u(y,t) = sum A_n cos(lambda_n y) exp(-lambda_n^2 cv (t - t_drain))
lambda_n = (2n+1) pi / (2H)
```

with `t_drain=0.002 s`. Total pore pressure is reconstructed as:

```text
p = p_hydro + u
```

This analytical reference is a quasi-static 1D consolidation reduction. It is
not the raw particle PR equation, because the PR implementation evolves:

```text
PorePressRate = Kw/n * (-DivVel + k/(rho_w*g) LapPorePress + k LapZ)
```

and the apparent storage enters through the coupled dynamic volumetric
response.

## A1/A2 Audit Summary

A1 showed that the boundary-operator mode does not control the remaining
bottom-excess discrepancy: GPU `PorePressureBoundaryOperator=0` and `1` give
nearly identical long-run bottom errors.

A2 showed that the actual generated state at `t~0.002 s` is not the Eq. (4)
profile. The generated bottom excess at the drainage activation frame is only
about `66.96%` of Eq. (4), then overshoots Eq. (4) at `0.003-0.005 s`, and
relaxes close to Eq. (4) around `0.01-0.02 s`. However, using the raw measured
early profile as the reference initial condition does not improve the long-run
comparison. The nominal Eq. (4) profile remains the most useful baseline
reference.

## Effective cv Calibration

The calibrated effective reference uses the same Eq. (4) initial profile and
the same boundary eigenbasis, but scales the consolidation coefficient:

```text
cv_eff = 1.1175 cv_nominal
```

This is not interpreted as a material permeability or material-parameter
recalibration. It is an apparent time-factor sensitivity that compactly
measures the difference between the quasi-static analytical reduction and the
dynamic coupled SPH response, including explicit volumetric storage, damping,
Shepard regularization, and particle operator effects.

## Comparison Results

For GPU `mode=0`, `xi=0.05` bottom excess pressure:

| Reference | RMSE (Pa) | Relative RMSE |
|---|---:|---:|
| nominal analytical | 550.17 | 7.59% |
| calibrated effective reference | 135.56 | 1.98% |

The calibrated effective reference reduces the relative bottom-excess RMSE by
approximately `73.9%`.

## Generated Figure Set

The generated figure files are saved as SVG, PNG, and PDF:

1. `figure1_bottom_excess_time`
2. `figure2_excess_profiles`
3. `figure3_total_pore_pressure_profiles`
4. `figure4_excess_envelope_decay`
5. `figure5_relative_error_time`
6. `figure6_cv_sensitivity`

The corresponding metrics are:

- `paper_figure_metrics.csv`
- `calibrated_reference_metrics.csv`
- `cv_sensitivity_summary.csv`

## Boundary and Corrected-Gradient Status

`PorePressureBoundaryOperator=1` remains an experimental strict-boundary path.
It is not promoted to the default production mode because it did not improve
the long-run analytical discrepancy.

Corrected-gradient PR operators remain deferred. The current discrepancy is
better described by effective time-factor / storage mapping than by a boundary
or corrected-gradient issue.

## Recommended Manuscript Wording

The nominal one-dimensional consolidation solution reproduces the overall
dissipation trend but slightly underestimates the apparent dissipation rate
observed in the fully coupled SPH simulation. A modest effective time-factor
adjustment, `cv_eff = 1.1175 cv`, reduces the bottom excess-pressure relative
RMSE from approximately 7.6% to 2.0%. This adjustment is not interpreted as a
material-parameter recalibration, but as a compact measure of the difference
between the quasi-static analytical reduction and the dynamic coupled SPH
response, including explicit volumetric storage, damping, Shepard
regularization, and particle-based operator effects.
