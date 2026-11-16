# P1 frozen-A CPU build preparation

Status: author preparation only. The builder has not been executed. It never
invokes help, a solver, native decoding, VTK or a watcher. A successful build
would establish implementation readiness only, not numerical acceptance.

The source input is the final finite-Kw A build
`logs/upl_spr_av_ReleaseCPU_r1.build.json`, its 265-member flat source snapshot,
and the separately admitted `logs/upl_tpi_cpu_r1.prepare.json`. Preparation
copies the original files and overlays only `JSphCpu.cpp`,
`JSphCpuSingle.cpp`, plus `upl_tpi_cpu_r1.h`; public classes and headers do
not change. Before linking, the builder independently compares the other
263 prepared files byte for byte with their retained snapshots. This is
one necessary source/ABI closure check, not an old-object or raw-BI4 hash scan.

The current authoritative `VS/DualSPHysics5ReCpu.vcxproj` has 87 active
CPU translation units. Its sole addition relative to A's exact 86-object
closure is `JSphCpu_mdbc.cpp`; the frozen A `JSphCpu.cpp` already contains
that implementation and its snapshot has no separate mDBC translation unit.
The private `ForceImportAfterCppTargets` adapter removes this one extra unit
and maps the remaining exact 86 members into the prepared frozen source
directory. Active per-file project options must still be absent, as reviewed.
The authoritative project, solution, configurations, default C++ standard,
v143 14.36.32532 toolset, floating-point mode and CPU target remain in use.
The original project is not edited. The include directory is the frozen
source directory, never current `src/source`.

For **DebugCPU**, no matching complete A debug object set is claimed. Build
all 86 units through the actual authoritative solution's DebugCPU/x64 Build
target, using the private import. Objects, compiler PDB, linked PDB, ILK,
LTCG outputs and executable all go under the fresh
`outputs/upl_tpi_cpu_DebugCPU_r2/{int,out}` tree. This is a frozen-A
reproduction build, not a claim that current canonical source passed its
default Debug build. The genuine owned MSBuild call, process-handle exit,
console log, binary log and original CL/link command/read tlogs are retained.
CL and link are MSBuild-owned child tools; their tlogs must not be described
as independently captured root-owned process-handle exits.
The retained A Release library list locks the base recipe only; it is not
proof of the actual Debug dependencies. After the genuine Debug build, the
builder retains `link.read.1.tlog` and records stats for every `.lib` path
actually listed there. These are post-link observations, not a claim of
independently frozen pre-build library identities or per-tool Win32 exits.

For **ReleaseCPU**, the matching original 86-object Release build is retained.
Compile the two prepared translation units with the original per-TU CL
commands, redirecting their outputs and header lookup to the new directory.
Link exactly 84 untouched original objects plus these two new objects using
the original link command and libraries. Preserve actual separately owned
CL/link calls, both Popen and Win32 exits, and compiler dependency manifests.
No public class/header ABI change is allowed. All output paths, including
PDB/ILK/import-library/LTCG state, are redirected under
`outputs/upl_tpi_cpu_ReleaseCPU_r2/{int,out}`.

Both configurations require an independently reviewed root admission:

```text
D:/anaconda3/python.exe -B tests/support/upl_tpi_cpu_build_r2.py
  --configuration DebugCPU|ReleaseCPU
  --execution-authorized --admission ROOT_ADMISSION.json
```

The admission has `stage="upl_tpi_cpu_r2.build_admission"`, `passed=true`,
`build_only=true`, the exact `configuration`, and an `inputs` list of frozen
`{path,bytes,mtime_ns}` records. At minimum this list pins the builder, this
note, prepared receipt, A build receipt and current authoritative solution
and project. The prepare receipt binds every prepared source and original
snapshot. Existing output trees or receipts, including failed ones, are
never overwritten or reused.

Old object files are checked once by stat and rechecked for no change after
the build; no old-source/object/BI4 SHA sweep occurs. The newly linked program
receives one SHA256 identity digest. Canonical executables, public source,
old object/PDB/ILK files and the suspended C08 source/PRE are not modified.
Runtime copies and a Debug OpenMP runtime are kept inside the new output
tree. Tool failure is preserved without help, solver retry, another build,
process replacement or an automatic follow-up.

The finite-Kw A trajectory is a qualified regression baseline. Its full-cycle
old 100-Pa bottom-stress accuracy condition did not pass (maximum
110.575504398 Pa), so neither building this overlay nor matching OFF can
silently promote it to unconditional physical truth. Independent P1 native,
pressure/history, residual and benchmark comparison gates remain subsequent
work. The current script does not admit a long calculation.

## r2 environment-start repair

The original r1 Debug build stopped before MSBuild/CL with actual Popen and Win32 exit 1. Its cmd stderr shows the embedded quoted vcvars path was interpreted with literal backslashes. All original r1 files and receipts remain failed and unchanged.

r2 writes a new CRLF load_environment.cmd under its own new output directory, invokes cmd from that output directory with the unquoted space-free filename load_environment.cmd as a single token, and captures the genuine direct-child exits. The script only calls the original vcvarsall.bat, returns its error, then prints the environment into a private pipe; raw environment is never logged. No separate help/connectivity test is performed. The source, compiler/link logic, qualification and physical formulas are unchanged. r2 is a new diagnosed build attempt, not a rearmed worker or physical solver.
