# P1 stage-load-clock private two-host builder: author only

New files: `support/upl_tpi_p1_loadclock_build_r1.py` and this note. Author does not
run CL, LINK, MSBuild, a program/help, native reader, VTK, Git or hash. Importing the
old stable build modules loads definitions only; none of their mains is called.
Root must read this draft and separately admit one configuration. No automatic later action.

## Exact scope and interface

Receipt stage is `upl_tpi_p1_loadclock_build_r1`; configuration is one of
DebugCPU,ReleaseCPU,Debug,Release. Artifact tag is
`upl_tpi_p1_loadclock_<configuration>_r1`, receipt `tests/logs/<tag>.build.json`,
program `tests/outputs/<tag>/out/<standard executable name>.exe`.
IntDir is a fresh no-space TEMP/upl_tpi_p1_loadclock_build_r1/configuration/int.
All CL/PDB/ILK/IObj/PGD/import-library/program outputs are redirected; canonical bin and old trees are unchanged.

The actual passed new preparations are
`logs/upl_tpi_p1_loadclock_{CPU,GPU}_r1.prepare.json`, stage `upl_tpi_p1_loadclock_r1.prepare`.
They contain the real flat268/271-file source closures, not a relabelled M0 preparation.
Exactly CPU `JSphCpu.cpp,JSphCpuSingle.cpp` or GPU `JSphGpu.cpp,JSphGpuSingle.cpp`
are freshly compiled. New `upl_tpi_p1_loadclock_r1.h` is host-only.
Pressure helpers/schema, original M0 policy, class layout, CUDA/CUH and device-facing declarations remain byte-identical.
The builder binds the full preparation/files/diff and actual old/new member associations;
post-CL sourceDependencies must show this new source/helper and exclude live/prior private source headers.

## Actual configuration recipes

| Config | Passed baseline/object set | Actual CL / LINK calls |
|---|---|---|
| DebugCPU | M0 DebugCPU_r3,86 objects | same r3 two CL and LINK |
| ReleaseCPU | P1 cpu_release_link_r3,86 objects | successful P1 ReleaseCPU_r2 CL calls; actual release_link_r3 LINK |
| Debug | M0 Debug_r2,111 objects | same r2 two host CL and LINK |
| Release | M0 Release_r2,111 objects | same r2 two host CL and LINK |

No passed M0 ReleaseCPU program previously existed. That configuration explicitly
adopts the actual passed P1 same-config r3 closure; the two newly compiled hosts
bring in the already prepared M0 policy plus stage clock. The other84 objects
remain bound through the unchanged-ABI/source lineage. The old r2 link failure is
not rewritten or reclassified. GPU retains109 objects including every CUDA object;
CPU retains84. Linker object order and all original numerical/configuration flags remain.

Use genuine JSON argument vectors from actual successful owned CL/LINK calls.
The DebugCPU original unquoted source-tail provenance is independently reconstructed
through the tested r3 exact `^source` header/two-tail-token parser. Never pass an
unquoted path through the old r2 filename-counting parser. New CL receives one
complete source argument and a new sourceDependencies output path.
Debug uses /MTd,/Od; ReleaseCPU and Release use /MT,/O2, with original /fp:precise,/openmp.

## Tools, SDK, libraries and runtime

Reuse the real MSVC14.36.32532 tools and the stable existing vcvars/owned-call helper.
The general environment loads actual SDK10.0.22000.0. DebugCPU then reproduces
its original SDK8.1 um/shared plus UCRT10240 front include/library adaptation;
all original vcvars INCLUDE/LIB paths remain. ReleaseCPU's actual CL/P1r3 link useSDK22000.
Do not replace vcvars LIB with the17 explicitly listed Release libraries: the
implicit C++ CRT `libcpmt.lib` must remain discoverable at its recorded actual path.

Every inherited explicit/CRT library binding is checked against the new actual
first-existing search candidate. Evidence labels distinguish original link-read
bindings from ReleaseCPU P1r3's CRT search-only evidence; no new linker-read trace
is invented. Necessary tool/library/source/object/runtime stat bindings are checked
before and after; no old object/source/BI4 SHA or new EXE SHA is needed here.
ReleaseCPU's17 legacy A library entries have only path/bytes/SHA. Their mtime is
not invented: use the same-path/size path/bytes/mtime_ns entries actually frozen
in the passed P1r3 root admission. Bind that unchanged admission and record both
its provenance and the legacy path/bytes; absent historical stat rejects, without
current-stat fallback or rehash. The prior unused build admission remains preserved.
Runtime copies come from the adopted configuration's actual existing package,
alongside the new program, so program-relative DsphConfig/DLL lookup remains valid.

## Root admission and results

Root JSON stage is `upl_tpi_p1_loadclock_build_r1.build_admission`, with passed/build_only
true, exact configuration and unique inputs[path,bytes,mtime_ns]. Inputs include
script/note/reused build modules/vcvars; actual new prepare and all source members;
source lineage/diff; same-config passed build/program/objects/runtime; genuine
CL/LINK calls/programs/logs; authoritative project/solution; library candidates;
DebugCPU original SDK header/tlog-source-tail evidence and compiler PDB inputs.
ReleaseCPU additionally consumes the original same-config A/P1 preparation and CRT evidence.

Only after full read: `python -B tests/support/upl_tpi_p1_loadclock_build_r1.py
--configuration DebugCPU --execution-authorized --admission ROOT_JSON` (one invocation/configuration).
Existing/partial output or receipt refuses overwrite. Each true tool keeps owned
PID/creation/argv and Popen/Win32 exits using the existing helper. A failure preserves
calls/partial outputs and final stat observations; it never retries another build.
Passed means two real CL calls, one real LINK, sourceDependencies, exact86/111-object
closure and runtime packaging succeeded. It is not program, default-A, component,
CPU/GPU physical, timestep or benchmark acceptance. All those later actions require
their own root review; this builder starts none of them.
