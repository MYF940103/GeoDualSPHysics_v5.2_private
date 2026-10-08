# Cryer CPU shell-plus-one peak test, 2026-07-14

Purpose: test whether moving the drained free-surface layer outward by one
particle spacing improves the Cryer center pore-pressure peak.

## Setup

- Baseline: `tests/configs/cpu_release_peak/CaseCryerProblem_PR_cpu_rel_peak_Def.xml`.
- Variant: `tests/configs/cpu_release_peak_shellplus1/CaseCryerProblem_PR_cpu_rel_peak_shellplus1_Def.xml`.
- Solver: `DualSPHysics5.2CPU_win64.exe`.
- Particle spacing: `dp = 0.0025 m`.
- Formal Cryer radius: `R = 0.05 m`.
- Variant particle-generation radius: `R + dp = 0.0525 m`.
- Loading, drainage, material parameters, `dt`, `TimeOut`, and center sample
  radius were kept the same as the CPU peak baseline.
- `TimeMax = 0.055566642857 s`, covering the existing baseline peak window to
  about `Tv = 0.061` when interpreted with the formal `R = 0.05 m`.

GenCase increased the fluid particle count from the baseline `37173` particles
to `42752` particles. The solver completed normally with `Part_0000` through
`Part_0061` and no stderr output.

## Results

Two postprocess interpretations were retained:

- `formalR0p05`: compare against the original Cryer theory radius `R = 0.05 m`.
- `actualR0p0525`: treat the enlarged particle domain as the theory radius.

| Metric | Baseline R=0.05 | Shell+1 formal R=0.05 | Shell+1 actual R=0.0525 |
| --- | ---: | ---: | ---: |
| SPH peak `p/q0` | 1.2157689 | 1.2158645 | 1.2158645 |
| SPH peak `Tv` | 0.0500 | 0.0550 | 0.0499 |
| Theory at SPH peak | 1.2476399 | 1.2413151 | 1.2477248 |
| Theory peak `p/q0` | 1.2490075 | 1.2490075 | 1.2490214 |
| SPH at theory peak | 1.2146685 | 1.2102542 | 1.2148306 |
| RMSE | 0.0362578 | 0.0527535 | 0.0376668 |
| MAE | 0.0355650 | 0.0446740 | 0.0373774 |
| Final `p/q0` | 1.2045346 | 1.2130587 | 1.2130587 |
| Min free-surface count | 5153 | 5579 | 5579 |

## Conclusion

The simple shell-plus-one change does not materially improve the center peak.
The absolute peak increases by only about `9.6e-5 p/q0`, which is negligible
relative to the remaining peak deficit of about `0.033 p/q0`.

Interpreting the run as an artificial drainage shell around the original
`R = 0.05 m` sphere makes the theory-peak value worse and shifts the numerical
peak later. Interpreting the run as a genuinely larger `R = 0.0525 m` sphere
mostly removes the apparent timing shift, but the peak amplitude is still
essentially unchanged and the global error is slightly worse.

For now, simply enlarging the particle radius by one layer should not be adopted
as a Cryer accuracy fix. The remaining peak deficit is more likely tied to the
free-surface drainage/loading treatment itself than to the missing one-particle
outer shell.
