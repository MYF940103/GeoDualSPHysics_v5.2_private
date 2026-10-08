# q0 GPU mDBC fastsingle dispatch check, 2026-07-11

Purpose: verify whether a hydromechanical GPU q0 run without explicit
`-mdbc_fast:0` can leak into the mDBC FastSingle correction kernel path.

## Code path checked

- `source/JSphGpuSingle.cpp::MdbcBoundCorrection()` passes:
  `fastsingle = (MdbcFastSingle && !HydroMech)`
- `source/JSphGpu_ker.cu::Interaction_MdbcCorrectionT2()` dispatches the fast
  kernel only when this `fastsingle` argument is true; otherwise it dispatches
  the double-precision mDBC correction kernel.
- `source/JSph.cpp` now also forces `MdbcFastSingle=false` for CPU or
  HydroMech cases during XML/command loading and HydroMech initialization.

## Runtime check

Case:

- XML: `tests/configs/gpu_validation/CaseTCq0_gpu_mdbcdispatch_noflag_t0001_Def.xml`
- BAT: `tests/xCaseTCq0_gpu_mdbcdispatch_noflag_t0001_win64_GPU.bat`
- Output: `tests/outputs/gpu_validation/CaseTCq0_gpu_mdbcdispatch_noflag_t0001_out`
- Command style: no explicit `-mdbc_fast:0`
- TimeMax/TimeOut: 0.001 s short dispatch diagnostic

Temporary one-time logging was added inside `JSphGpuSingle::MdbcBoundCorrection()`
for this run and then removed after verification.

Relevant `Run.out` evidence:

```text
Hydromechanics="Enabled"
PoreMdbcInterpolationMode="ZeroOrder"
mDBC-Corrector=True
mDBC-FastSingle=False
GPU mDBC-FastSingle requested=False
GPU mDBC-HydroMech guard=True
GPU mDBC fastsingle kernel dispatch=False
Finished execution (code=0).
```

## Conclusion

For the current q0 HydroMech GPU code path, a run without explicit
`-mdbc_fast:0` does not enter the mDBC FastSingle correction path. The final
kernel dispatch argument is `fastsingle=false`, so the double-precision mDBC
correction path is selected.

This means the remaining GPU-vs-CPU q0 pressure-profile discrepancy should not
be attributed to accidental mDBC FastSingle dispatch in this current code state.
The next suspects should be other GPU-side update-order, precision, or boundary
state differences.
