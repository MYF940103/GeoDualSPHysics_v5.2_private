# Cryer dp=0.002 old root output vs new tests output, 2026-07-14

Purpose: compare peak-region accuracy between the old complete root-level
`dp = 0.002 m`, `nu = 0.30` output and the newer `tests` output.

## Cases

Old complete output:

- Case: `CaseCryerProblem_PR_dp002_rampclosed_nu030_out`
- Particle spacing: `dp = 0.002 m`
- Solver output: root example directory
- Load/drainage timing: `HydroMechTopLoadRampTime = 0.0025 s`,
  `HydroMechDrainageStartTime = 0.0025 s`
- Existing metrics:
  `figures/formal_validation/cryer_poisson_sweep_dp002_rampclosed_center_r1dp_metrics.json`
- Existing center history:
  `figures/formal_validation/cryer_poisson_dp002_rampclosed_nu030_center_r1dp.csv`

New tests output:

- Case: `tests/outputs/cpu_release_peak_dp002/CaseCryerProblem_PR_cpu_rel_peak_dp002_out`
- Particle spacing: `dp = 0.002 m`
- Solver: CPU Release
- Load/drainage timing: instantaneous load and drainage from `t = 0`
- Metrics:
  `tests/figures/cpu_release_peak_dp002/cryer_cpu_release_peak_nu030_dp002_summary.json`
- Center history:
  `tests/figures/cpu_release_peak_dp002/cryer_cpu_release_peak_nu030_dp002.csv`

The two cases are therefore not identical loading histories. The old case is
the closed-ramp formulation; the new case is the one-stage drained formulation.

## Peak Comparison

| Metric | Old root `dp=0.002` rampclosed | New tests `dp=0.002` one-stage | Old - new |
| --- | ---: | ---: | ---: |
| SPH peak `p/q0` | 1.2225849674 | 1.2224858268 | +0.0000991406 |
| SPH peak `Tv` | 0.0492555477 | 0.0490000000 | +0.0002555477 |
| Analytical peak `p/q0` | 1.2490229494 | 1.2490074664 | +0.0000154830 |
| Deficit vs analytical peak | 0.0264379819 | 0.0265216396 | -0.0000836576 |
| SPH value at analytical peak `Tv` | 1.2217821530 | 1.2214666146 | +0.0003155384 |
| Deficit at analytical peak `Tv` | 0.0272407964 | 0.0275408518 | -0.0003000554 |
| Deficit at SPH peak `Tv` | 0.0255638414 | 0.0258111046 | -0.0002472632 |

## Interpretation

The old complete root-level `rampclosed` output is marginally more accurate
around the peak. Depending on the peak-error definition, the advantage is only
about `0.00008` to `0.00030 p/q0`.

This is much smaller than the remaining peak deficit itself, which is about
`0.0265 p/q0`. The old closed-ramp/drainage timing therefore does not solve the
main Cryer peak underprediction; it only gives a very small improvement in the
peak-region metrics.

