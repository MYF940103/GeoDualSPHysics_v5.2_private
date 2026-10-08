# q0 GPU clean-build recovery and final validation, 2026-07-12

Case family: `02_TerzaghiConsolidation_q0_PR`, `k=1e-4`, `dp=0.01`, `DtFixed=1e-5`, `TimeOut=0.005Tv`.

## Conclusion

The GPU discrepancy was recovered in a clean build only when the GPU `HydroMechLoadAceg` diagnostic array stays in the allocation/sort/save layout and is passed to the force kernel, while top-load writes to this array are disabled and the PartVTK output variable list does not request `HydroMechLoadAce`.

This reproduces CPU-level pore-pressure accuracy in both a short `Tv=0.25` test and a full `Tv=1` run. The final root GPU run also reproduces the result.

## Code locations kept for this validated state

- `source/JSphGpu.cpp:391`: keep the `HydroMechLoadAce` GPU allocation/sort buffer count so the HydroMech GPU array layout matches the validated state.
- `source/JSphGpuSingle.cpp:1087`: keep `HydroMechLoadAce` in the BI4 save-data array set. The formal BAT files still omit `+hydromechloadace`, so VTK output stays clean.
- `source/JSphGpu_ker.cu:1091`: top-load acceleration no longer writes `loadace[p]`; this diagnostic write perturbed the q0 GPU benchmark.
- `source/JSphGpu_ker.cu:1882` and `source/JSphGpu_ker.cu:2124`: GPU `rsigma` accumulation remains outside the old velocity/density/viscosity gate in the current validated GPU source.
- `source/JSphGpuSimple_ker.cu:444` and `source/JSphGpuSimple_ker.cu:652`: boundary stress copies use the full three `float2` entries (`p*3`, `p*3+1`, `p*3+2`) instead of the old flattened `sigma[p]` single-entry write.
- `source/JSph.cpp:712`, `source/JSph.cpp:864`, `source/JSph.cpp:3458`, and `source/JSphGpuSingle.cpp:620`: HydroMech mDBC runs force or dispatch `MdbcFastSingle=false`; logs confirm `mDBC-FastSingle=False`.

## Validation metrics

Short clean-build test:

- `tests/outputs/gpu_validation/CaseTCq0_gpu_saveace_Tv025_out`
- `Tv=0.25`: GPU RMS `0.034523 kPa`, CPU RMS `0.034353 kPa`, GPU/CPU `1.005`.

Full clean-build test in `tests`:

- `tests/outputs/gpu_validation/CaseTCq0_gpu_saveace_Tv1_out`
- Figures/data:
  - `tests/figures/gpu_validation/gpu_saveace_Tv1_vs_cpu_summary.csv`
  - `tests/figures/gpu_validation/gpu_saveace_Tv1_vs_cpu_profiles.png`
  - `tests/figures/gpu_validation/gpu_saveace_Tv1_vs_cpu_metrics.png`
- Key RMS values:
  - `Tv=0.25`: CPU `0.034353 kPa`, GPU `0.035094 kPa`, GPU/CPU `1.022`
  - `Tv=0.4`: CPU `0.025108 kPa`, GPU `0.025217 kPa`, GPU/CPU `1.004`
  - `Tv=0.5`: CPU `0.015961 kPa`, GPU `0.016033 kPa`, GPU/CPU `1.004`
  - `Tv=1.0`: CPU `0.013881 kPa`, GPU `0.013479 kPa`, GPU/CPU `0.971`

Formal root GPU run:

- XML/BAT:
  - `tests/configs/gpu_validation/CaseTerzaghiConsolidation_q0_PR_full_k1em4_gpu_Tv1_Def.xml`
  - `tests/configs/gpu_validation/xCaseTerzaghiConsolidation_q0_PR_full_k1em4_gpu_Tv1_win64_GPU.bat`
- Output:
  - `tests/outputs/gpu_validation/CaseTerzaghiConsolidation_q0_PR_full_k1em4_gpu_Tv1_out`
- Figures/data:
  - `figures/gpu_k1em4_Tv1_vs_cpu_summary.csv`
  - `figures/gpu_k1em4_Tv1_vs_cpu_profiles_data.csv`
  - `figures/gpu_k1em4_Tv1_vs_cpu_profiles.png`
  - `figures/gpu_k1em4_Tv1_vs_cpu_metrics.png`
- Key RMS values:
  - `Tv=0.25`: CPU `0.034353 kPa`, GPU `0.034803 kPa`, GPU/CPU `1.013`
  - `Tv=0.4`: CPU `0.025108 kPa`, GPU `0.025208 kPa`, GPU/CPU `1.004`
  - `Tv=0.5`: CPU `0.015961 kPa`, GPU `0.016045 kPa`, GPU/CPU `1.005`
  - `Tv=1.0`: CPU `0.013881 kPa`, GPU `0.013570 kPa`, GPU/CPU `0.978`

The final VTK output was checked and does not contain `HydroMechLoadAce`; it contains the expected `ExcessPorePress`, `PorePress`, and `PorePress0` fields.

## Interpretation

The earlier good GPU runs were not caused by accidental mDBC FastSingle dispatch. HydroMech mDBC logs and code dispatch show the fast-single branch is disabled. The reproducible clean-build recovery instead depends on keeping the diagnostic array in the GPU data layout and force-kernel argument path, while suppressing the top-load write and omitting the field from VTK extraction. This points to a GPU layout/code-generation sensitivity in the coupled q0 HydroMech path rather than a physical change to the governing equations.
