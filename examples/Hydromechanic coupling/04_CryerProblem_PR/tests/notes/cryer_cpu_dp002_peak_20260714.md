# Cryer CPU dp=0.002 peak-window test, 2026-07-14

Purpose: after cleaning the previous shell-plus-one output, test whether
increasing the native Cryer sphere resolution from `dp = 0.0025 m` to
`dp = 0.0020 m` continues to reduce the center pore-pressure error.

## Cleanup

The previous shell-plus-one run outputs were removed:

- `tests/outputs/cpu_release_peak_shellplus1/`
- `tests/logs/cpu_release_peak_shellplus1/`
- `tests/figures/cpu_release_peak_shellplus1/`

The previous shell-plus-one XML and conclusion note were kept as records.

## Setup

- Baseline: `tests/configs/cpu_release_peak/CaseCryerProblem_PR_cpu_rel_peak_Def.xml`.
- Higher-resolution variant:
  `tests/configs/cpu_release_peak_dp002/CaseCryerProblem_PR_cpu_rel_peak_dp002_Def.xml`.
- Solver: `DualSPHysics5.2CPU_win64.exe`.
- Radius: `R = 0.05 m`.
- Particle spacing: `dp = 0.002 m`.
- `TimeMax = 0.055566642857 s`, equivalent to `Tv = 0.061` for the formal
  Cryer radius.
- `TimeOut = 0.000910928571429 s`, equivalent to `Delta Tv = 0.001`.
- Center sample radius: `r <= 1dp = 0.002 m`.

GenCase produced `71170` fluid particles, compared with `37173` in the
`dp = 0.0025 m` CPU peak baseline. The CPU solver completed normally with
`Part_0000` through `Part_0061` and `Finished execution (code=0)`.

## Results

| Metric | CPU `dp=0.0025` | CPU `dp=0.0020` | Change |
| --- | ---: | ---: | ---: |
| SPH peak `p/q0` | 1.2157689 | 1.2224858 | +0.0067170 |
| SPH peak `Tv` | 0.0500 | 0.0490 | -0.0010 |
| Theory at SPH peak | 1.2476399 | 1.2482969 | +0.0006571 |
| Theory peak `p/q0` | 1.2490075 | 1.2490075 | 0 |
| SPH at theory peak | 1.2146685 | 1.2214666 | +0.0067982 |
| Peak deficit | 0.0332386 | 0.0265216 | -0.0067170 |
| RMSE | 0.0362578 | 0.0313029 | -0.0049549 |
| MAE | 0.0355650 | 0.0300891 | -0.0054760 |
| Final `p/q0` at `Tv=0.061` | 1.2045346 | 1.2103814 | +0.0058468 |
| Max speed | 0.0399112 | 0.0214062 | -0.0185050 |
| Min free-surface count | 5153 | 8045 | +2892 |

## Conclusion

Increasing resolution from `dp = 0.0025 m` to `dp = 0.0020 m` does reduce the
center pore-pressure error. The peak deficit drops from about `0.03324 p/q0` to
about `0.02652 p/q0`, and the RMSE drops by about `0.00495`.

The improvement is real but limited: the SPH peak is still about `2.65%` below
the analytical peak. Resolution alone is therefore helping, but it is not likely
to fully close the Cryer peak gap unless we go substantially finer or also
improve the loading/drainage treatment.

For the next resolution check, `dp = 0.0015 m` would be the natural step, but
the CPU cost will be much higher. It is probably better to run that one with GPU
Release or a shorter, carefully chosen peak-window output plan.
