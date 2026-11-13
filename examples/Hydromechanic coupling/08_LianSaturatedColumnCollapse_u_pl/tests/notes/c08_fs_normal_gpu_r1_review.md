# Offline GPU FS controls review r1

Author-only new `support/c08_fs_normal_gpu_r1_review.py` and this note. The author does not import/invoke this helper, run GPU/CPU components, rebuild, read BI4, decode native data, scan SHA or modify any bound source/result. Root full-reads the source, then may invoke it once with `--execution-authorized` after the two actual Debug memchecks are complete. There is no automatic physical launch or other executable call in this script; it imports only Python standard-library readers/math.

The fixed input is `logs/c08_fs_normal_gpu_r1.run.json`. It must be passed/nonphysical, bind the actual Debug build Entry, and contain exactly Raw and Normal completed items (list items labelled `label`, or a dict keyed Raw/Normal). Each item binds program, actual_call, completion, memcheck_log and exactly controls.csv/nodes.csv/free_off_rates.bin/Run.out. Expected output directories are `outputs/c08_fs_normal_gpu_r1_raw` and `_normal`; no alternate or newly generated physical data is consumed. The retained CPU comparison is bound through `logs/c08_fs_matrix_cpu_r2.run.json` and its actual build/calls/completions/files, not through a guessed fresh run.

## Actual execution and build evidence

The GPU build must be the private Debug intervention with113 unique objects per executable,111 shared retained project objects, one identical new fixture object, and exactly one physical GPU object difference: original JSphGpu_ker versus candidate JSphGpu_ker. It must report two compile/four total actual build calls, two links, seven frozen companions, unchanged consumed stats, exact inverse-original source proof, and unchanged archived mDBC include. The script binds the source/archive/capture and relevant actual objects/calls/runtime; it performs stat checks and never rescans their bytes or old code-object contents.

Every build/run actual call must have typed Popen/Win32 zero exits, no ownership failure, positive actual handle-derived PID/creation FILETIME, and matching owned tool image/argv/parent. GPU memchecks must also have a distinct actual target handle, matching original/candidate fixture image and exact `--expect raw|normal --out FRESH_DIR` argv, and target Win32 exit0. Actual CUDA11.7 compute-sanitizer argv must select memcheck, leak-check full, error-exitcode99 and the bound sanitizer log. Console and sanitizer logs must be distinct. All present ERROR SUMMARY and LEAK SUMMARY records must exist and be zero. The fixture's own Run.out must identify actual RTX3050 device0 and zero physical steps; no A6000/historical hardware claim is substituted.

Each completion must state own production GPU FS/C, no CPU-array injection, J-feedback tracking, full input/tail-bit preservation, zero physical steps,1620 controls/162 nodes and no physical/CPU-GPU bitwise/coupled-stability acceptance. The exported CSV cannot independently recreate unexported tail canaries: the review checks the genuine, stat-bound source/program completion guards plus the actual successful invocation, and expressly avoids claiming a second tail reconstruction.

## Offline arithmetic checks

Both complete keyed node sets are162 rows: `(profile,native_ID)` over2x81. Each GPU controls set is1620 rows: `(profile,field,free_on,ID)` over2x5x2x81. Native coordinates/J must match the predeclared C08-scale manufacture. The existing sourcefloat factor B=32*FLT_EPSILON+4096*DBL_EPSILON checks the exported n/V/rho/k ledger; uploaded binary32 rho-cache values must match their prescribed J ledger exactly.

All stored pressures must match the five manufactured fields and remain negative. Actual binary32 rate bits must match their CSV numbers; labels must match the fixture's own node row. Actual-reference error must stay within the original exported arithmetic budget. The helper independently recombines exported LP/Lx/gp/Da/gradJ using the intended raw or actual-normal projected formula, and the nonzero variable-k product-rule chain, then compares that rate and the separately exported lap/chain rate to the same original budget. It does not reimplement a neighbor search or infer new fields from BI4.

Hydrostatic F0 uses the existing `2*arithmetic_budget+pressure_input_quantization_budget` null gate, unchanged. Uniform-J gradJ/chain must be exactly zero. The constant negative field must have exact zero actual/reference rate. Profile1's real ON-FS chain witnesses are counted with `abs(s*chain)/whole_rate_budget>1` and must match each completion and be nonempty. Their actual count is reported; no31/32 fitted-count requirement is added. All actual inner OFF/ON rate bits must agree. Each810-float OFF file must exactly match its keyed actual CSV rate bits/order/count.

Cross-GPU Raw/Normal nodes.csv and OFF binaries must be byte-exact. All exported controls outside ON-FS must agree exactly; within ON-FS only intended result/reference/budget/gpcorr/lap/chain columns may differ, while prescribed inputs and LP/Lx/gp/Da/gradJ remain equal. A nonempty actual ON-FS rate-bit difference is required to make the comparison nonvacuous. No CPU array is loaded into either GPU process by this offline script.

## CPU comparison and artifacts

The valid CPU r2 controls have1134 rows (972 first-three-field OFF/ON controls plus162 constant basis baselines). Match the first three fields to GPU by `(profile,field,on,ID)`, all972 keys per executable. Report GPU/CPU actual rate RMS and difference RMS/maximum in Pa/s. For each profile/executable, report classification mismatch count and maximum C-component, normal-vector and posdiv differences. These are descriptive comparisons of separately generated tracking fields; no matching FS labels, normal bits, CPU/GPU rate bits, pressure5Pa gate or continuum-accuracy threshold is imposed.

On success the helper creates only:

- `logs/c08_fs_normal_gpu_r1.review.json`: actual receipt/build/source bindings, all checks, chain counts/maxima, cross-GPU equality evidence and CPU comparison metrics.
- `figures/c08_fs_normal_gpu_r1_control_metrics.csv`:40 rows of own GPU rate/error metrics.
- `figures/c08_fs_normal_gpu_r1_cpu_gpu_metrics.csv`:24 rows for the first-three-field CPU/GPU rate comparisons.
- `figures/c08_fs_normal_gpu_r1_node_differences.csv`:4 rows of actual CPU/GPU tracking differences.

Existing complete or partial review/CSV paths are protected. Consumed size/mtime Entries are checked before and after analysis/output; no hashes are used. Failure preserves a failed receipt and any partial newly written CSV, with no rerun or cleanup. A passed review means the declared zero-step Debug controls and memory/receipt evidence passed. It does not grant unit/scientific admission, Release equivalence, coupled stability, conservative Neumann flux, C08 causation or physical acceptance. Root must review these findings and the separate CPU scientific result before any distinct physical admission.
