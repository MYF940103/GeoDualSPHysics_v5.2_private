# P1 GPU private build author draft

2026-11-17, Asia/Tokyo. This script/note are new author assets only. They have
not executed preparation, vcvars, compilation, linking, help, a solver, native
reading, VTK, Git or SHA. One separately reviewed root admission is needed for
each real Debug or Release build. A successful build is not implementation,
numerical or physical acceptance and starts no next action.

The script is `tests/support/upl_tpi_gpu_build_r1.py`; it imports only definitions
from the already reviewed `upl_tpi_cpu_build_r2.py` for real owned-tool calls,
Win32/Popen exits and stat records. Import never invokes that module's CPU build.
It does not edit the lead's GPU helper, prepare generator or frozen source.

## Numerical/header boundary

The lead owns `logs/upl_tpi_gpu_r1.prepare.json` and the flat
`outputs/upl_tpi_gpu_r1_source`. The expected source schema is267 copied
source/header files plus `upl_tpi_gpu_r1.h` and `.cuh`,269 total; source_diff is
separate. Three numerical overlay TUs are JSphGpu.cpp, JSphGpuSingle.cpp and
JSphGpu_ker.cu. JSphHourglassGpu.h adds only nonvirtual inline const bulk-device
getters, with no member/layout/vtable or old kernel external-signature change.

Although those getters are binary-layout compatible, retaining an old object
that directly includes a different full class definition would leave a strict
ODR mismatch. Therefore the root selected a fourth, inexpensive host compile:
JSphHourglassGpu.cpp. Its method bodies must remain byte-identical to the
original archived file. The two direct complete-definition consumers are that
file and JSphGpuSingle.cpp. Exactly4 new objects replace the matching old4;
107 old objects remain untouched. No all111-object Debug rebuild is needed.

Device histories/rates remain Q/Mref, not current acceleration. Getter access
must be bulk device pointers; no per-ID D2H getter loop is admitted by this
design. The lead's numerical review still must prove ID-owned history/periodic
roles, exact float BC and commit rules, full endpoint residual and single
defect correction, current-J readonly-HG add, and unchanged original2 HG forces/
2 updates. The endpoint cannot advance material, kappa, J, solid state or P0.
Those are not established merely by compilation.

The explicit GPUState owner free must run before base JSphGpu's cudaDeviceReset,
be idempotent/no-throw, and free only its own buffers/clear its descriptor.
Derived JSphGpuSingle already deletes HourglassGpu before entering the base
destructor, so that free must never dereference HG. Static state destruction
must perform no CUDA operation. These are lead source-review/Debug checks,
not a new build-stage physical action.

## Exact retained recipes

Bases are `upl_gpu_stabilizers_{Debug,Release}_r1.build.json`, the shared
`upl_gpu_stabilizers_r1.source.json` (`source_count=265` code/header files,
`files` length267 after adding two document archives), and each real old MSBuild
call/log. Matching111 objects still exist in
`%LOCALAPPDATA%/Temp/upl_gpu_stabilizers_r1/<configuration>/int`.
Debug has original per-object sizes/SHA metadata; the author observed111 size
matches without rescanning hashes. Release has recorded111 object names but no
per-object old hash/mtime closure. New reuse pins their actual current stats;
it must not claim comparison with nonexistent old object hashes. Retained
compiler vc143.pdb files are also input-only dependencies. Later default-A real
native regression is necessary evidence of the paired implementation.

The authoritative solution remains `src/VS/DualSPHysics5Re.sln` and project
`DualSPHysics5Re.vcxproj`. Current Debug/Release active compile closure113 differs
from the old111 only by JSphCpu_mdbc.cpp and JSphGpu_mdbc.cpp. The private recipe
excludes exactly these two; no project file is changed. The original two
FunctionsGeo3d_iker.h.obj/FunctionsMath_iker.h.obj compilation items remain;
they must not be renamed to ordinary stem.obj or dropped.

The original MSBuild calls fixed v143/MSVC14.36.32532 and x64, disabled project
references/post-build copying, and used a private no-space IntDir. Direct
compilation replays their genuine emitted recipes:

- Host CL flags come from exact per-source CL.command.1.tlog entries.
  Debug retains /Od /MTd /RTC1; Release retains /O2 /MT. Both retain /Zi,
  /fp:precise, /openmp, original defines and CUDA include flags.
- The genuine JSphGpu_ker.cu NVCC command is in its MSBuild.log, not a guessed
  missing CudaCompile.command tlog. Preserve CUDA11.7, ccbin14.36.32532,
  compute86+sm86, static cudart, use_fast_math, original host options, and
  Debug -G/-g versus Release optimization. Only source/output/keep-dir/host-PDB
  paths change. No new precision/fast-math/kernel formulation flag is added.
- Original111-object link.command.1.tlog order and options/libraries remain.
  The4 exact object paths change; /OUT, /PDB, /IMPLIB and /LTCGOUT become new
  private destinations. An explicit new /ILK path prevents accidental writes
  outside the private tree. Old compiler PDBs and all107 old objects remain
  read-only inputs; they are not copied or recompiled.

Actual old linker-read inputs identify MSVC14.36.32532 and WindowsSDK10.0.22000.0:
27 Debug or26 Release libraries. The new literal CRLF/mbcs environment.cmd calls
vcvarsall x64 with that SDK and -vcvars_ver14.36. Invoke its simple relative
filename with cwd set to the private build root, avoiding the previously failed
nested-call quoting. Preserve vcvars LIB exactly; do not replace it with an old
receipt's partial LIB. Actual library search's first existing candidate must
match every original linker-read library path. This is search evidence, not a
new linker-read trace. Compiler-injection environment variables CL/_CL_/LINK/
_LINK_/NVCC_PREPEND_FLAGS/NVCC_APPEND_FLAGS are removed by name, without logging
their possibly secret values. Full environment stdout is never persisted.

## Strict inputs, new outputs and invocation

One root admission contains `stage="upl_tpi_gpu_build_r1.build_admission"`,
`configuration="Debug"|"Release"`, `passed=true`, `build_only=true`, and
`inputs=[{path,bytes,mtime_ns}, ...]`. It must pin:

1. This script/note and the actual common CPU helper; authoritative GPU solution
   and project; vcvarsall; actual cmd/cl/link/nvcc tools.
2. Passed GPU prepare receipt, all269 new source/helper files, source_diff,
   original267 source manifest and original unchanged HG.cpp snapshot.
3. The selected old GPU build/program, real MSBuild call/log, matching111
   objects, compiler vc143.pdb, CL/link command tlogs and linker-read tlog.
4. All27/26 actual linker-read library files and the original private runtime
   files. Debug additionally requires the actual VS14.36 debug OpenMP
   vcomp140d.dll if not present in the old runtime list.

Paths are stat-frozen and checked before each actual compile/link and again at
the end. Case-insensitive Windows path keys avoid casing differences in old
tlogs; each frozen entry itself is compared by exact recorded stat. No original
source/object/BI4 SHA sweep is performed. The only intended hash during an
authorized build is once for the newly sealed executable's identity.

Execution shape, only after root review:

```text
python -B tests/support/upl_tpi_gpu_build_r1.py --configuration Debug|Release
  --execution-authorized --admission ROOT_ADMISSION.json
```

Fresh outputs are `outputs/upl_tpi_gpu_<configuration>_r1`, its out directory,
and the new no-space temporary
`%TEMP%/upl_tpi_gpu_build_r1/<configuration>/int`. All new objects, compiler PDB,
dependency JSON, NVCC temporary/keep files, linker iobj/ilk, executable, program
PDB/importlib and copied runtime stay in those private locations. Existing or
partial destinations reject; the script never cleans or retries them. New tool
calls/logs and final receipt use `logs/upl_tpi_gpu_<configuration>_r1.*`.

Host sourceDependencies must not read any live src/source header. NVCC consumes
the prepared flat source/header tree with original CUDA include flags; no new
NVCC dependency run is fabricated. Runtime copies come from original private
base outputs plus the necessary VS debug-OpenMP source, never from a mutable
canonical executable. No canonical program/source/project/input is installed.

Before execution the root should review the generated source/header differences,
4/107 closure, every rewritten output path, expected SDK/library resolution,
same-header ODR scope, explicit-free ordering, and branch-OFF scope. Compilation
then needs actual owned exits and preserved failure calls. Failures remain
failed, including partial object outputs; no caller retries an old label.
Actual compile/link invocation counts are obtained from recorded real children,
not inferred from an intended4/1 count. Build success starts no help, memcheck,
component, native read, solver, VTK, watcher, queue or Git action. Root must
separately admit each later implementation check; no physical claim follows.
