# GPU P1 r2 private build author

Author only, not executed. The r1 builder, successful Debug build, source
preparation and objects remain unchanged and do not grant a physical run.
This new script imports only their reviewed helper definitions. It does not
rewrite function source, monkeypatch globals, fabricate receipts or call
their main/context routines with an old label.

The source input is `logs/upl_tpi_gpu_r2.prepare.json`, its root-passed r1
ancestor and all 269 stat-bound members. The private `.cuh` is the only
changed member; all other 268 files are independently byte-compared once.
The actual public class layout, private host API and old external kernel
signatures therefore remain unchanged. No old object/BI4 SHA sweep occurs.

Debug uses the genuine passed `logs/upl_tpi_gpu_Debug_r1.build.json` and
adopts its three newly compiled host objects: JSphGpu, JSphGpuSingle and
JSphHourglassGpu. Their actual objects, old compiler PDB, original source
preparation and genuine tool-call records are root-pinned. Only one new
JSphGpu_ker.cu object is compiled from the actual original Debug NVCC recipe
with its new included `.cuh`. The final original 111-object ordering retains
107 original stabilizer objects, three adopted r1 hosts and one new CUDA
object. The receipt distinguishes compiled=1, adopted=3, effective retained=110.

Release has no P1 r1 build to adopt. It compiles all four matched source TUs
against r2: JSphGpu.cpp, JSphGpuSingle.cpp, JSphHourglassGpu.cpp and
JSphGpu_ker.cu. It retains exactly the original 107 other objects. Both paths
reuse the reviewed r1 linker helper with an explicit four-entry replacement
map; no source or linker-order rewriting beyond the approved new paths occurs.

The original Debug/Release compiler/SDK/CUDA commands, exact *.cu.obj and
two *.h.obj identities, library-read closure and preserved vcvars LIB remain.
New output, compiler/link PDB, ILK, LTCG and no-space CUDA intermediate paths
use `outputs/upl_tpi_gpu_<configuration>_r2` and the new temporary
`upl_tpi_gpu_build_r2/<configuration>/int` tree. Neither old PDB/objects nor
canonical programs are written. The new linked EXE receives one necessary
identity digest. Runtime copies remain in the new output tree.

Each configuration needs its own reviewed root admission:

```text
python -B tests/support/upl_tpi_gpu_build_r2.py --configuration Debug|Release
  --execution-authorized --admission ROOT_BUILD_ADMISSION.json
```

Admission fields are `stage="upl_tpi_gpu_build_r2.build_admission"`,
`configuration`, `passed=true`, `build_only=true`, and
`inputs=[{path,bytes,mtime_ns}, ...]`. Pin this author/note, the unchanged r1
builder and common CPU helper, r1/r2 prepare/diffs/all source members, matched
original GPU build/program/111 objects/compiler PDB, true CL/link/read tlogs
and original MSBuild log/call, original tools and resolved libraries/runtime,
and current authoritative solution/project closure. Debug additionally pins
its genuine r1 Debug build/program/calls, adopted host objects and their PDB.

New records are `logs/upl_tpi_gpu_Debug_r2.build.json` and
`logs/upl_tpi_gpu_Release_r2.build.json`; prepared/source_prepare point to
the new source receipt and base_prepare preserves ancestry. Actual tool
Popen/Win32 exits and logs are retained even on failure. Existing outputs
or failures are protected. No help, solver, fixture, native, VTK, watcher,
Git or next action is run. In particular a successful CUDA build cannot
claim the 16 device fixtures executed; only a later separately admitted
Debug two-update run can supply its genuine marker and memcheck evidence.
