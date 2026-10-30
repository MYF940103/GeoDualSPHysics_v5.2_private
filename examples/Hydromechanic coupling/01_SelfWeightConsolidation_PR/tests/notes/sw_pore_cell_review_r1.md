# GPU pore-boundary cell-size implementation review

This is a bounded implementation repair, not acceptance of self-weight consolidation accuracy. Existing formal case inputs/results and canonical executables were not replaced. Cryer server work was not touched.

## Cause and single production change

`src/source/JSphGpu_ker.cu`, host wrapper `PorePressureMdbcCorrectionT`: pass `dvd.poscellsize` instead of reading device constant `CTE.poscellsize` in host code. A separately compiled actual CUDA probe observed configured host/device/API-copy cell size 0.035999998450279236, but the direct host expression passed zero. The repair restores the intended cell-coordinate conversion; it does not alter the Darcy, MLS, stress, time-integration, or Shepard equations/defaults.

The previous source is preserved under `tests/outputs/sw_pore_cell_base_r1`; the exact corrected compilation input is preserved under `tests/outputs/sw_pore_cell_verified_r1` (SHA256 efc1cc9bc838067a88427f397811eaa80d591d9ac69e00358421a168e62682ea). Only the one argument differs byte-for-byte. Private CPU DebugCPU, GPU Debug and GPU Release builds passed; the unchanged verified CPU Release was adopted. GPU Debug compute-sanitizer reported zero errors. Build warnings and original raw logs are retained, not normalized.

## Evidence and results

All comparisons use native material IDs and actual saved time/step, including all 40 boundary and 1000 soil nodes. The new reader exports the original 35 columns plus `is_boundary`, actual `porepress0` and actual `excess_native` (38 columns). Initial p0 and float32 excess identities were independently checked; they were not reconstructed to force agreement.

| Same-physics CPU/GPU pore-pressure RMS difference | Previous GPU | Corrected GPU |
| --- | ---: | ---: |
| First Shepard event, 40 us | 0.743827315 Pa | 0.000107306 Pa |
| At 80 us | 2.516978354 Pa | 0.000249929 Pa |
| Maximum over five saved 2-ms states | 39.121374128 Pa | 0.003072999 Pa |

The corrected 2-ms material-displacement difference is at most 2.71175e-8 mm; stress-component absolute difference is at most 0.000655980 Pa. Shepard-OFF old/new GPU results are bit-identical in all 38 numeric fields at all 84 retained event/short frames (3,319,680 values). These are implementation-agreement improvements, not reductions in error against a consolidation theory solution.

The controlled 80-us event experiment localized the old divergence to natural step 40: before it, same-backend Shepard ON/OFF states were bit-identical. At that event CPU boundary pressure changed but old GPU boundary pressure did not. An initial zero-radius MLS hypothesis was tested offline and rejected as the cause of this actual event: the actual moving event states had no coincident query/soil pair. No global zero-radius kernel patch was introduced.

Case02 `sw_pore_cell_1d_r1` repeated both retained symC variants separately with the corrected GPU program. Each variant passed all 151 saved states with all 1040 IDs and all 38 numeric columns bit-identical to its own previous same-variant control, with no field exclusion/interpolation. Original load, drainage, post-.1-s 100-Pa stress/top-gap and HG guards remain. This does not erase the previously observed intentional symC ON/OFF difference or claim a new 2Tv/half-step result.

## Scope, provenance and next stage

Primary receipts: `sw_cte_host_r1.check.json`, `sw_pore_cell_build_r1.check.json`, `sw_pore_cell_native_r1.check.json`, and case02 `sw_pore_cell_1d_r1.check.json`, with immutable per-job completions and SHA-bound inputs/outputs. Raw BI4/executables remain local; Git backup of code/configuration/receipts/CSVs is not a cloud backup of raw particle data.

Next: a fresh corrected-GPU 2-ms half-step diagnostic, then independent 0.3-s Stage1 Shepard ON/OFF equilibrium windows. Stage1 has k=0 and cannot test the symC Darcy term. No restart, full consolidation, theory accuracy, plasticity or general-boundary acceptance follows from the repair. Persistent stress remains double; pore pressure and density remain float. The accepted formal case02 inputs remain unchanged with symC default OFF.
