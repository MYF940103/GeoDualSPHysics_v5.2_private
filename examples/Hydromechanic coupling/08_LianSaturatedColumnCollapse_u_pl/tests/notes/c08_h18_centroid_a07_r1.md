# Experimental centroid-wall AS.7 owner: author only

Only new `support/c08_h18_centroid_a07_r1.py` and this note are authored. The
script has not been imported or executed. No preparation, build, GenCase,
solver, native reader, VTK, analysis, Git, hash or queue action is performed
during authoring. Root must fully read this owner and the separate build design.

The fresh fixed run tag is `c08_h18_centroid_a07_GPU_r1`. This is a **physical
dynamic-wall closure change**, intervention `dynamic_wall_centroid_retry_once`:
one extra centroid retry from the existing moments after the existing nearest
retry fails. It is not an output-only replay or proven physical repair. No new
XML parameter is introduced; experimental physical acceptance remains pending.

Authorized `prepare --execution-authorized` only copies the original actual
AS.7 Def XML under the fresh tag and creates its `.prepare.json`. The existing
probe's `original_context()` binds the genuinely failed original, its actual
owned exits, complete same-material Wendland PRE, full91 schedule and input.
No old tag or result is overwritten. Existing input-signature, material-profile,
schedule and actual-handle helpers are reused without monkeypatching them.

The later Release run is explicitly:

```text
python -X utf8 -B tests/support/c08_h18_centroid_a07_r1.py run --execution-authorized
```

It requires `logs/c08_h18_centroid_Release_r1.build.json`, stage
`c08_h18_centroid_Release_r1.build`, with passed actual typed/Win32 exits0,
intervention above, unchanged build/source statistics, authoritative113 project
objects and seven runtime companions. Its isolated program is
`outputs/c08_h18_centroid_Release_r1/DualSPHysics5.2_GEO_win64.exe`.
Candidate source capture/archive must be genuinely changed, with the reviewed
two-file CPU/GPU intervention and original schema2 baseline provenance bound
separately. The owner reads the accepted build receipt; it does not rescan
objects or compile anything.

Before Release, root supplies a stat-bound actual Debug aggregate through
`admission.debug_regression` with this contract:

```text
stage:"c08_h18_centroid_debug_regression_r1", passed:true,
intervention:"dynamic_wall_centroid_retry_once",
source_stats_unchanged:true, consumed_stats_unchanged:true,
source_capture:Entry, source_archive:Entry,
CPU_Debug_smoke_passed:true, GPU_Debug_smoke_passed:true,
GPU_Debug_memcheck_zero_errors_and_leaks:true,
cpu_build:Entry, gpu_build:Entry,
cpu_smoke:Entry, gpu_smoke:Entry, gpu_memcheck:Entry,
physical_acceptance:false
```

The source Entries must equal the Release candidate snapshot. Debug build
receipts must be the actual accepted `DebugCPU` and `Debug` centroid builds;
smoke/memcheck check receipts must themselves be passed and stat-sealed. A
manufactured algebra component, design note or promise of future tests cannot
satisfy this gate. The owner never launches these tests automatically. Root
must derive the aggregate only from genuine completed checks.

The distinct run admission `logs/c08_h18_centroid_a07_GPU_r1.admission.json`
requires passed/allowed_job, intervention, physical_intervention_authorized=true,
experimental_pending_physical_acceptance=true, and exact Entries named
prepared, candidate_build, input_xml, original_run, source_pre_file,
planned_steps, program, source_capture, source_archive and debug_regression.
It also fixes planned_global_end2180000/expected_saved_frames91,
native_auto_authorized=false, terminal_queue_once=true and the actual original
root_thread_id `01a07683-bc64-7463-8db7-9ee6243967d8`.

One GenCase and one Release GPU calculation retain the original numerical
AS.7/n3.825/H1.8/Wendland/dp.04/5us/AV.1/NoPen/CompletedOnly inputs, same actual
PRE, .9s/full91 launch plan and `-nsteps:2180000`. The new physical operator is
explicit in source/build/run receipts. There is no artificial early stop, new
PRE, half chain, control, other-psi or second physical run. Original first save
remains PRE+one real update. No automatic native decode or PartVTK is invoked.

The existing actual-handle owner preserves true PID/creation/exe/argv/parent,
tool/Win32/solver exits and raw logs before raising on failure. A normal full91
exit qualifies runtime completion only and remains pending root native/physical
review; failures retain their actual saved file count and last original console
without inventing unsaved state or changing any guard. Queue uses the current
Codex path on the verified admitted root thread exactly once with45s timeout;
uncertain delivery never resends/rearms and no watcher is installed.

External launcher receipts/logs must use a different prefix, for example
`c08_h18_centroid_launch_r1.*`. Do not create `TAG.launch.*` before invoking
this owner: its single-attempt same-tag guard allows only prepare and root
admission before the claim. Root owns all later acceptance and next-stage work.
