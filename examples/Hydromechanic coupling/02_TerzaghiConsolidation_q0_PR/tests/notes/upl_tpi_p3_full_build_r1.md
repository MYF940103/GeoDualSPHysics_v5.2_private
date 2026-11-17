# Private P3 full-scope one-Single-TU builds (author only)

support/upl_tpi_p3_full_build_r1.py and this note are new author assets. Nothing
has been compiled, linked, prepared or executed while authoring. One root-admitted
configuration per invocation is allowed; no help, solver, reader, VTK, notifier,
following case or automatic configuration chain exists. CPU Debug must actually
pass first before any other configuration is admitted by this script.

Configuration mapping is inherited literally from the passed P3 builder:

| Configuration | Backend | Total objects | New object | Retained objects |
|---|---|---:|---|---:|
| DebugCPU | CPU | 86 | JSphCpuSingle.obj | 85 |
| ReleaseCPU | CPU | 86 | JSphCpuSingle.obj | 85 |
| Debug | GPU | 111 | JSphGpuSingle.obj | 110 |
| Release | GPU | 111 | JSphGpuSingle.obj | 110 |

All CUDA objects are retained; new NVCC invocations are zero. The source-only
parent receipt must be the passed new upl_tpi_p3_full_source_r1.prepare stage,
CPU/GPU inventory 267/270, with only Single.cpp changed and no changed headers.
The builder independently rereads every source byte: Single must equal the exact
one-expression sourceprep.patch(parent), and all other source/helper/header/cuH
bytes must equal the actual P3 parent. This is a local source diff check, not SHA.
No public class/virtual/shared inline ABI changes are permitted. Original header
and device tokens therefore remain valid for retained objects. There is no host
kernel or pressure-only optimization in this candidate.

Each configuration consumes its actual passed logs/upl_tpi_p3_<cfg>_r1.build.json,
the actual P3 Single CL call and P3 link call, their executable/log stat bindings,
all 86/111 object stat records and old compiler dependency records, original
compiler PDBs, selected libraries/runtime, tools, and authoritative VS project /
solution. The genuine helper requires passed calls and both actual owned Popen
wait and Win32 exits equal zero. Link object order is copied from the actual P3
call; only the Single object is substituted, without stem-based CUDA header loss.

The existing audited P2 environment routine is called directly, without globals
or schema mutation. Original MSVC v143 14.36 numerical/CRT/optimization/OpenMP
flags are retained; source, /I source root, /Fo, /Fd and /sourceDependencies move
to the new private tree. DebugCPU retains the actual SDK8.1/UCRT10240 prepend
adaptation recorded by its passed P3 build. GPU and remaining configurations
retain their actual vcvars/library search. vcvars LIB is preserved and each named
library must resolve to its previous actual first candidate. Authoritative .sln /
.vcxproj are read/bound, not edited or replaced by another build system.

New /sourceDependencies must name the exact new Single.cpp and include actual
new pressure/dt helpers and JSph.h. Any live src/source or original frozen parent
include is rejected. System/SDK/library includes remain legitimate. New objects,
compiler PDB, EXE/PDB/import LIB/LTCG IOBJ/ILK/PGD and runtime copies are isolated.
Original object/program/runtime/PDB paths are consumed read-only. Build stage is
upl_tpi_p3_full_build_r1; an old P3 receipt is never renamed to the new stage.

Invocation after complete root review, one configuration at a time:

```text
D:/anaconda3/python.exe -B tests/support/upl_tpi_p3_full_build_r1.py --configuration DebugCPU --admission ROOT_JSON --execution-authorized
```

Admission stage is upl_tpi_p3_full_build_r1.build_admission, passed=true,
build_only=true, exact configuration, inputs is a duplicate-free stat list. It
must include this script/note, original P3 builder/note, new source prepare/note,
P2 build module/note, defining CPU/GPU helper modules and vcvars; all receipt,
source, paired original/snapshot, CL/link log/tool, object, dependency, SDK header,
library, runtime, project/solution and PDB inputs listed above. Non-DebugCPU
actions also consume the genuinely passed new DebugCPU full-scope build receipt.

Fresh outputs: outputs/upl_tpi_p3_full_<cfg>_r1/{out,environment.cmd,...},
%TEMP%/upl_tpi_p3_full_build_r1/<cfg>/int (no spaces), owned CL/link call/log
receipts under the same new tag, and logs/upl_tpi_p3_full_<cfg>_r1.build.json.
The final receipt records actual compile/link counts, zero new CUDA/physical
invocations, original_recipe_evidence, source_prepare/base_build, object_count,
replacement_object_count=1, retained_effective_object_count=85 or110, actual
dependencies/environment/library resolution/runtime and consumed stat checks.
Existing output/IntDir/failure receipts are protected. Failures preserve partials
and no retry or later action is launched. Build success only qualifies the new
program for separately admitted short implementation regression, then separately
reviewed full execution; it is not full-cycle or physical acceptance.
