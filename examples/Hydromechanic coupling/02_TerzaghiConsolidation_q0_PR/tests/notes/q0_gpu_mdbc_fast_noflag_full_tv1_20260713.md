# q0 GPU no explicit mdbc_fast flag full Tv=1 check, 2026-07-13

Purpose: verify whether the current final GPU release can reproduce the CPU
baseline without explicitly passing `-mdbc_fast:0`.

## Setup

- Source/exe: current rebuilt GPU Release, `DualSPHysics5.2_GEO_win64.exe`.
- XML: copied from validated `CaseTCq0_gpu_saveace_Tv1_Def.xml`.
- BAT: `tests/xCaseTCq0_gpu_noflag_Tv1_win64_GPU.bat`.
- Command style: no explicit `-mdbc_fast:0`.
- Output: `tests/outputs/gpu_validation/CaseTCq0_gpu_noflag_Tv1_out`.
- Figures/data: `tests/figures/gpu_validation/gpu_noflag_Tv1_vs_cpu_*`.

Runtime log confirmed:

```text
Hydromechanics="Enabled"
mDBC-FastSingle=False
TimeMax=36.4471428571428
TimePart=0.182185714285714
Finished execution (code=0).
```

## Result

The no-flag GPU run reproduced the CPU baseline through full `Tv=1`.

Key RMS values:

- `Tv=0.25`: CPU `0.034353 kPa`, GPU `0.034676 kPa`, GPU/CPU `1.009`.
- `Tv=0.4`: CPU `0.025108 kPa`, GPU `0.025143 kPa`, GPU/CPU `1.001`.
- `Tv=0.5`: CPU `0.015961 kPa`, GPU `0.015992 kPa`, GPU/CPU `1.002`.
- `Tv=1.0`: CPU `0.013881 kPa`, GPU `0.013997 kPa`, GPU/CPU `1.008`.

## Conclusion

For the current final q0 HydroMech GPU code state, the formal GPU BAT does not
need to explicitly pass `-mdbc_fast:0`. The root formal GPU BAT was changed to
the default no-flag form after this full-run validation.
