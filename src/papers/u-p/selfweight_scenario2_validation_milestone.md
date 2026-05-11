# Self-Weight Scenario 2 Validation Milestone

Date: 2026-05-12

## Final Figure Directory

The current paper-ready Scenario 2 figure set is stored in:

`examples/u-pw/02_SelfWeight_Consolidation/experiments/PaperFigures_SelfWeightScenario2/`

This directory contains the GPU Scenario 2 `xi=0.05` comparison line, nominal
analytical reference, calibrated effective reference, metrics CSVs, and
SVG/PNG/PDF-style figure outputs.

## Nominal Analytical Reference

The nominal Supporting-Materials-style analytical reference uses:

- Eq.(4) undrained self-weight initial excess-pressure profile;
- nominal consolidation coefficient / time factor;
- top drained, bottom no-flux eigenbasis;
- hydrostatic end-state reference for total pore pressure.

Against the GPU Scenario 2 `xi=0.05` long run, the nominal bottom excess-pressure
relative RMSE is about `7.59%`.

## Calibrated Effective Reference

A1/A2 showed that the main sensitivity is the apparent consolidation time
factor. Using:

```text
cv_eff = 1.1175 * cv_nominal
```

reduces the bottom excess-pressure relative RMSE to about `1.98%`.

This is not interpreted as a material-property retuning. It is an effective
time-factor / apparent consolidation-coefficient sensitivity that compactly
captures the difference between the quasi-static 1D analytical reduction and
the dynamic coupled SPH response, including explicit volumetric storage,
damping, Shepard regularization, and particle-operator effects.

## Boundary Audit Conclusion

Boundary-focused follow-up phases do not change the Scenario 2 interpretation:

- B4/B5 `PorePressureBoundaryOperator=1` GPU long run produced essentially the
  same bottom excess-pressure RMSE as mode 0:
  `550.17 Pa` for mode 0 versus `550.18 Pa` for mode 1.
- H1 `PorePressureBoundaryOperator=2` CPU hydraulic mDBC boundary-particle
  prototype was stable but did not improve hydrostatic, pressure-only, or
  self-weight short metrics.

Therefore the remaining nominal discrepancy is not primarily controlled by the
legacy layer boundary correction.

## Final Recommendation

Scenario 2 is closed for the current paper validation path:

- Use GPU `xi=0.05`, `PorePressureBoundaryOperator=0` as the main simulation
  line.
- Present both the nominal analytical reference and the calibrated effective
  reference.
- Describe `cv_eff=1.1175 cv` as an effective time-factor sensitivity, not a
  changed material calibration.
- Keep mode 1 and mode 2 as experimental boundary paths.
- Keep corrected-gradient production deferred.

Further effort should move to Scenario 1 staged workflow rather than continuing
boundary/operator changes for Scenario 2.
