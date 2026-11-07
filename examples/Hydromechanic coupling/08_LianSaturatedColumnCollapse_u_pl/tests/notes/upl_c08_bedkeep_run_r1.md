# Retained shallow-bed single-job owner

Author-only new `support/upl_c08_bedkeep_run_r1.py`, mechanically derived from frozen `upl_c08_asplane_run_r2.py`. No import/AST/execution, source change, capture, build, GenCase, solver, reader, VTK or queue was performed during authoring. Existing evidence and source PRE are unchanged. Exact new source/note paths were checked with exists and targeted git ls-files before creation.

Each invocation chooses one action with `--execution-authorized`; there is no automatic task sequence or retry. SPECS tuple is `(stem,conf,backend,nopen,ason,keep,updates,cadence,end,tout,memcheck)`:

|Action|Tag below outputs|Configuration|keep|AS|Updates / cadence|Frames|TimeMax / TimeOut|Memcheck|
|---|---|---|---:|---:|---|---:|---|---|
|CPUdebug|upl_c08_bedkeep_smoke_CPU_r1|DebugCPU|true|1|40 /40|1|10.0001 /.0001|No|
|GPUdebug|upl_c08_bedkeep_smoke_GPU_r1|Debug|true|1|40 /40|1|10.0001 /.0001|Single sanitized target|
|OFF|upl_c08_bedkeep_off_GPU_r1|Release|false|1|12000 /4000|3|10.03 /.01|No|
|SHORT|upl_c08_bedkeep_short_GPU_r1|Release|true|1|12000 /4000|3|10.03 /.01|No|
|WINDOW|upl_c08_bedkeep_window_GPU_r1|Release|true|1|240000 /4000|60|10.6 /.01|No|

OFF means only the new keep option is disabled; AS remains1. Its later native comparison control is the retained `upl_c08_asplane_short_GPU_r1`, which has the same3 saves/AS1/NoPen1. This owner does not execute that comparison. Each new tag has independent config/output/start/call/status/admission/logs/plan and refuses previous actual invocations. An existing root admission is retained/stat-bound; the real owner writes owner_admission instead.

All cases retain the same root r4 psi0 template, source r2 GPU PRE actual clock/global4M, dt2.5us/DtMin1e-8, NoPen1, Cubic, material, Ck2, free seepage, original gradients and AS .2f/2.55f. Input creation adds only explicit gravitypreload `keep_bed_overlap=true|false` beyond existing statefile/end/cadence/AS fields. It does not modify the template or PRE, alter source qualification/contract, or invent a CPU preload run. CPUdebug explicitly imports the qualified GPU source into CPU.

Programs bind the new `upl_c08_bedkeep_<conf>_r1.build.json` with matching common `upl_c08_bedkeep_source_r1` capture, actual build exits,87/113 objects, FixedPlaneStageProjectionReleaseOnly, AS ReleaseOnly and KeepBedOverlapReleaseOnly. Runtime copying remains missing-known-file only with unchanged size/mtime; no executable fallback or canonical replacement. The strict AS Configuration semicolon summary and real AS log `[:=]` checks are retained and the parser remains stat-bound.

Run.csv continues to describe the original registry Np7060/Nbound2060/Nfixed2060, regardless of the planned intentional wall retirement. A true keep job requires one phase retirement255 plus the exact release log retaining original IDs1800,1852,1904,1956,2008 at their original coordinates/native fixed MK codes with +DpZ normal and per-particle NoSlip. Expected later native registry is6805=5000 soil+1805 fixed; OFF requires retirement260, no enabled keep log, and later native6800. Actual per-frame metadata presence/absence, native IDs/P0/J/ledger/FS/clock/signed fields are pending the separate reader; the owner does not claim to inspect BI4 metadata.

Original real process identity/handle/wait/finally capture, raw complete console status, two-column planned_steps.csv, unique release, source import, required step/frame/no-exclusion summary and memcheck gates are retained. GPUdebug has only one compute-sanitizer target, no preceding direct run. Any unexpected failure is preserved without restart. Normal runpass means native/physical review pending.

Only WINDOW may use `--notify`, with the same root thread UUID and one terminal45s queue attempt. Its new message explicitly requests the bedkeep6805 reader and new keep metadata, not the old6800 AS adapter; it does not automatically decode, export, continue a solver or admit full physical acceptance. Timeout/failed delivery is not resent, rearmed or tested with another watcher.
