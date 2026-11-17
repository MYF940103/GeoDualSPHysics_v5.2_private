# Offline P3 Nsight cost evidence review — author only

2026-11-17. `support/upl_tpi_p3_cost_review_r1.py` is newly authored and has not
been executed. No SQLite query, analysis main, solver, reader, build, profiler,
export, stats command or hash scan was run by this authoring task. Root must read
the entire script and admit one offline-only review. The original failed probe
run, call/start, logs, BI4, source/program and Nsight artifacts remain unchanged.

## Original failure and independent evidence

The original `upl_tpi_p3_cost_probe_GPU_r1.run.json` remains `passed=false`, with
the exact failure `Actual GPU mode/hardware/once16 fixture differs`. Its actual
tool Popen/native exits and independently captured solver Win32 exit are all0.
The Nsight outer log does not carry the target fixture stdout marker. A nonfatal
protobuf UTF8 diagnostic during stats output is separate evidence and not silently
removed. New performance evidence does not rewrite that run or invent a console.

Root has separately observed real target PID31932, encoded globalPid282010706771968,
nonempty kernel/runtime/memory events, and one SourceRoleFixtureKernelR2 execution
lasting1312ns. The new script will independently check those observations, not
treat this note as proof. The actual original CUH launches that kernel once,
copies its result D2H, and throws unless bits=0, firstId=UINT_MAX and checked=16.
Successful execution of the frozen linked program through2000 updates plus the
captured kernel and that rejection chain provides an independent fixture
observation. Source alone cannot prove a kernel ran, and a kernel name alone
cannot prove its returned bits. The old console observation remains unavailable.

Retained CUDA compile/PTX receipts and linked object stats are consumed without
another dump or hash. The linked object is selected by one unique resolved path;
only path/bytes/mtime_ns are compared, without rejecting unrelated extra receipt
keys. The fixture CUH in the actual P3 capture must equal the CUH
beside the real original NVCC source, which is bound to the actual retained object.
No assertion repairs the entire old runtime postcheck or grants native/physical
acceptance. This review validates only the stated performance-evidence scope.

## Root admission and immutable inputs

Required admission: stage `upl_tpi_p3_cost_review_r1.review_admission`, passed=true,
offline_only=true, unique `inputs` entries with path/bytes/mtime_ns. Inputs include
this script/note, original probe script/note/run/call/start/root admission and log,
source run/build/prepare/program/runtime/seed/clock plan, actual target Run.csv and
Run.out, report container and SQLite, retained compile/PTX receipts/call/tool/object,
old compiled CUDA source/CUH and current P3 CUH. Actual consumed stats are checked
again after the review; no historical source or raw BI4 SHA sweep is performed.

SQLite is opened with URI mode=ro and immutable=1, plus connection query_only=ON.
The database is already sealed; no journal, schema change, export or new profiler
call is requested. Table and required-column checks precede const-SQL aggregates.
The target filter uses exact globalPid; runtime uses the same high-bit mask as
the installed Nsight reports. Native clock/22-array validation is not performed.

## Queries and time semantics

- API counts/durations come from CUPTI_ACTIVITY_KIND_RUNTIME, grouped by the
  installed report's normalized API name. Exact known cudaMemcpy456300 calls /
  33779186856ns and cudaLaunchKernel723944 calls /5072882843ns are rechecked.
- Kernel counts/durations use CUPTI_ACTIVITY_KIND_KERNEL shortName. All actual
  target kernel groups remain visible, including the independently observed fixture.
- Memory groups retain copy kind, exact bytes per operation, count, total bytes
  and device duration; memset is separate. Correlation joins require both matching
  correlationId and process identity. API duration is counted once per API within
  each kind/byte group, rather than repeated for every associated device event.
  If one API has several byte/kind groups its API duration can occur in several
  rows; those group-associated durations must not be summed into wall time.
- Optional returnValue records are reported only if the real schema includes
  that column. Nonzero raw returns are not universally a failed CUDA API: pointer
  returning/error-query functions differ. Missing returns remain unavailable,
  never an invented zero-error count. A separate count covers integer nonzero
  returns of explicitly listed cudaError_t-status APIs (copy/memset/alloc/free,
  launch and synchronize); it is not a universal application error certificate.
  Root must interpret any observed code/name.
- ProcessStreams is joined to StringIds using actual filename/content IDs. The
  exact target filter must return two records, the stdout/stderr pair named
  `stdout_0d7f-0e32-4266-cdf8.log` / `stderr_0d7f-0e32-4266-cdf8.log` under
  `quadd_session_1029272/streams`. Their contentId is13 and content must remain
  unavailable (empty or NULL, distinguished in metrics). Complete original
  filenames remain in metrics; those temporary paths are not opened, recreated
  or required to still exist. Root's prior inspection identified a third record
  as global config.ini (globalPid281474976710656); it is not a third target stream
  and this review does not read its content. No target stdout, marker or unsaved
  field is reconstructed.
- GPU/session metadata is limited to the explicit four-table whitelist
  `TARGET_INFO_GPU`, `TARGET_INFO_SESSION_START_TIME`, `META_DATA_CAPTURE`,
  `META_DATA_EXPORT`, at most16 rows each. No broad TARGET_INFO scan, SYSTEM_ENV,
  unrelated environment or global configuration content is read. No giant
  event-row DataFrame or whole-event JSON is generated.

The connection returns text as bytes. Valid UTF8 decodes normally; invalid UTF8
uses backslashreplace for display and retains the complete original byte hex in
new metrics, avoiding the prior text-decoder issue without rewriting the SQLite.

API time includes blocking/waiting that may overlap GPU execution and copies.
GPU kernel sums, GPU memop sums and host API sums cannot be added. A long8-byte
cudaMemcpy API with short GPU transfer is a synchronization clue, not proof of
poor transfer bandwidth or pure memcpy cost. No application-wall percentage is
claimed. CUDA-only tracing lacks CPU stack sampling, so gaps cannot be labelled
CSV/formatting CPU time solely from this trace.

## Outputs and decision limits

New `tests/outputs/upl_tpi_p3_cost_review_r1` would contain compact API/kernel/
memcpy/memset/correlation CSVs, optional nonzero-return CSV, and metrics.json.
`tests/logs/upl_tpi_p3_cost_review_r1.check.json` would seal performance evidence
only. Existing new paths reject overwrite; failures keep their actual first cause
and partial products. No following action, fixture repair, native reader or second
solver is automatic.

The target loop reports52.946587s, while the whole tool call took about382s
including profiling startup/export/stats. The probe saves210 frames in2000 updates,
about16.6 times the full2s per-step save density, with630000 three-round CSV rows.
These observations prevent clean runtime extrapolation to2Tv or a controlled
speedup claim. The original P3 physical acceptance is independent; a new trace
review pass cannot substitute for its gates or authorize a production optimization.
