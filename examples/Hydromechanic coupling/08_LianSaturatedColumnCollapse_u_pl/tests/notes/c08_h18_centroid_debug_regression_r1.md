# Centroid candidate Debug regression: two explicit short jobs

Author-only helper and note; not imported or executed. Root must fully read
`support/c08_h18_centroid_debug_regression_r1.py` before separately authorizing
each action: `prepare`, `cpu`, `gpu_memcheck`, then `review`, always with
`--execution-authorized`. No action automatically starts the next action.

Preparation copies the actual original full AS.7 Def XML into two fresh labels:
`c08_h18_centroid_debug_regression_r1_CPU` and
`c08_h18_centroid_debug_regression_r1_GPU_memcheck`. Same certified Wendland
PRE, material, AS.7/n3.825, H1.8/dp.04/5us, original TimeMax/TimeOut and physical
inputs remain. Only the explicitly requested CLI cap `-nsteps:2000400` shortens
each invocation to400 new updates/2ms; genuine saves must be PRE+one update
(global2000001) and cap2000400. Original full91 launch plan remains stat-bound
and is not rewritten or presented as a completed91-frame window.

CPU uses the isolated authoritative `DebugCPU` candidate program with
`-cpu -ompthreads:8`. GPU uses the isolated authoritative `Debug` program under
CUDA11.7 compute-sanitizer at the verified installed path, with `--tool memcheck`,
`--leak-check full`, `--target-processes all`, `--error-exitcode 99` and a fresh
log. Existing `matrix.invoke` acquires actual child/target handles and captures
Popen/Win32 identities/exits; GPU passes its real solver executable as target.
No CPU/GPU reference/control/half/PRE rerun is added.

Each explicit job runs one GenCase and one solver invocation. It requires
the corresponding passed centroid build/source/runtime bindings, normal code0,
Run.csv Steps2000400/PartFiles2/PartsOut0, original initial7060/2060 registry,
actual CPU8 or GPU hardware, Kernel2/Wendland, one actual source import/release,
retire255, retained NoPen and actual AS logs. It checks the two real PART names
and console completed steps without decoding them. GPU additionally requires
present zero ERROR SUMMARY and zero bytes/allocations LEAK SUMMARY. Its true
tool/solver failure receipts and partial outputs are retained without retries.

`review` reads only the two passed/stat-sealed job receipts and their bound
outputs, then creates `logs/c08_h18_centroid_debug_regression_r1.check.json`
with the exact aggregate contract required by the Release owner. `gpu_smoke`
and `gpu_memcheck` deliberately point to the same genuine sanitized GPU job,
not two physical runs. Both builds must share the candidate source capture/
archive. Aggregate solver_invocations0 means the review itself starts no solver;
actual_jobs2 records the completed short job scope.

This is bounded Debug implementation evidence. It proves no Release0ULP
agreement, CPU/GPU bitwise equality, full collapse physics, general stability
or actual exercise of the new fallback branch. Centroid activation and physical
behavior require separate later evidence. Physical acceptance and exercised
proof stay false. No native decoder, VTK, Release run, notification, watcher or
next solver is launched here. External launcher files must use another prefix
than either exact job tag so the single-attempt guards cannot collide.
