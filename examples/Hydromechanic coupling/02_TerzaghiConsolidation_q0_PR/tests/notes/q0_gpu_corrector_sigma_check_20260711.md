# q0 GPU Symplectic corrector sigma writeback check

## Purpose

Check whether the previously recovered GPU accuracy for the `k=1e-4`, `dp=0.01` Terzaghi q0 case depends on the extra boundary `sigma` writeback that had been added in `KerComputeStepSymplecticCor`.

## Code state

- GPU Release was rebuilt after removing the three boundary-branch assignments in `KerComputeStepSymplecticCor`:
  - `sigma[p*3] = sigmapre[p*3]`
  - `sigma[p*3+1] = sigmapre[p*3+1]`
  - `sigma[p*3+2] = sigmapre[p*3+2]`
- The Verlet and Symplectic predictor boundary stress-copy indexing fixes were kept.

## Test case

- XML: `tests/configs/gpu_validation/CaseTCq0_gpu_expfast0_nocorrsig_Tv025_Def.xml`
- BAT: `tests/xCaseTCq0_gpu_expfast0_nocorrsig_Tv025_win64_GPU.bat`
- Output: `tests/outputs/gpu_validation/CaseTCq0_gpu_expfast0_nocorrsig_Tv025_out`
- Command includes explicit `-mdbc_fast:0`.
- Run log reports:
  - `mDBC-FastSingle=False`
  - `PoreMdbcInterpolationMode="ZeroOrder"`
  - `SoilDamping="BuiFukagawa2013"`, `SoilDampingCoef=0.02`
  - `Finished execution (code=0)`

## Results

Comparison files:

- `tests/figures/gpu_validation/gpu_expfast0_nocorrsig_Tv025_vs_cpu_summary.csv`
- `tests/figures/gpu_validation/gpu_expfast0_nocorrsig_Tv025_vs_cpu_profiles_data.csv`
- `tests/figures/gpu_validation/gpu_expfast0_nocorrsig_Tv025_vs_cpu_profiles.png`

| Tv | CPU RMS (kPa) | GPU RMS (kPa) | GPU/CPU RMS | CPU norm L2 | GPU norm L2 | CPU U | GPU U |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.005 | 0.047672 | 0.047698 | 1.001 | 0.005052 | 0.005055 | 0.078994 | 0.079004 |
| 0.05 | 0.020892 | 0.020885 | 1.000 | 0.002603 | 0.002602 | 0.251247 | 0.251249 |
| 0.1 | 0.019510 | 0.019523 | 1.001 | 0.002768 | 0.002770 | 0.355491 | 0.355489 |
| 0.25 | 0.034353 | 0.082744 | 2.409 | 0.007026 | 0.016944 | 0.564504 | 0.568604 |

## Conclusion

Removing the GPU Symplectic corrector boundary `sigma` writeback keeps the early-time pore-pressure profile essentially identical to CPU through `Tv=0.1`, but the mid-stage `Tv=0.25` error grows substantially. The earlier explicit `-mdbc_fast:0` good full-run result therefore appears to depend on the source state that included this corrector `sigma` writeback, or on a source/compiler state tightly coupled to it.

This does not yet prove that the corrector `sigma` writeback is physically the right final implementation. It does show that simply rolling it back to the CPU-style corrector responsibility loses the recovered GPU mid-stage accuracy in this benchmark.

## Follow-up: old mDBC plus corrector sigma rollback

A later check tried to reproduce the old good GPU result with the explicit combination that was suspected to matter:

- GPU double mDBC density fallback restored to the old expression:
  - `rhopfinal=(rhopfinal!=FLT_MAX? rhopfinal: CTE.rhopzero)`
- GPU Symplectic corrector boundary branch temporarily restored to:
  - `sigma[p*3]   = sigmapre[p*3]`
  - `sigma[p*3+1] = sigmapre[p*3+1]`
  - `sigma[p*3+2] = sigmapre[p*3+2]`
- XML/BAT:
  - `tests/configs/gpu_validation/CaseTCq0_gpu_oldmdbc_sigrollback_Tv025_Def.xml`
  - `tests/xCaseTCq0_gpu_oldmdbc_sigrollback_Tv025_win64_GPU.bat`
- Output:
  - `tests/outputs/gpu_validation/CaseTCq0_gpu_oldmdbc_sigrollback_Tv025_out`

Result:

| Tv | GPU RMS (kPa) | GPU norm L2 | GPU U |
|---:|---:|---:|---:|
| 0.005 | 0.047689 | 0.005055 | 0.079001 |
| 0.05 | 0.020886 | 0.002602 | 0.251249 |
| 0.1 | 0.019511 | 0.002768 | 0.355491 |
| 0.25 | 0.093388 | 0.019167 | 0.569741 |

This is worse than the CPU baseline at `Tv=0.25` (`0.034353 kPa`) and worse than the earlier good GPU `diagAM` snapshot (`0.034669 kPa`). Therefore the previous conclusion was too strong: the old good result is not reproducibly explained by corrector boundary `sigma` writeback, even when paired with the old double-mDBC `rhopfinal` fallback.

The temporary corrector `sigma=sigmapre` writeback was removed again after this check.
