# q0 GPU mdbc_fast flag isolation

Case: Terzaghi q0, k=1e-4, dp=0.01, Tv~0.25 (Part_0050), current GPU release.

Key result:
- CPU baseline RMS = 0.034353 kPa, normalized L2 = 0.007026.
- GPU full Tv1 with explicit `-mdbc_fast:0` RMS = 0.034669 kPa, normalized L2 = 0.007090.
- GPU short Tv0.25 without explicit `-mdbc_fast:0` RMS = 0.088124 kPa, normalized L2 = 0.018052.
- GPU short Tv0.25 with explicit `-mdbc_fast:0` RMS = 0.034830 kPa, normalized L2 = 0.007123.

Conclusion:
For this HydroMech GPU q0 case, root/formal GPU BAT files should explicitly include `-mdbc_fast:0`. Although both explicit and no-flag runs print `mDBC-FastSingle=False`, the no-flag run did not reproduce CPU-level precision in this isolation check. The log field alone is therefore not sufficient evidence that the precision-sensitive path is identical. Keep explicit `-mdbc_fast:0` in GPU validation runners until the command/config initialization path is audited further.

Cleanup:
The root no-flag and explicit-flag GPU diagnostic outputs and figures were moved to `tests/configs/gpu_validation`, `tests/outputs/gpu_validation`, and `tests/figures/gpu_validation`. The failed long-name no-flag attempt was deleted because it only demonstrated a GenCase/path-length failure.
