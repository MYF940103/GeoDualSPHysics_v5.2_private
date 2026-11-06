# Actual GPU material-wrapper component: deferred build/run plan

Fresh r2 plan, explicitly authorized once after root reviewed the actual successful `upl_material_Debug_r1`111/110-object build. The first r1 CL passed, but linking failed solely because the small fixture omitted the main-owned `AppInfo` global. r2 adds only its header/three-string definition and changes own labels; original71 inputs, budgets and production closure remain unchanged. All r1 source and failure artifacts are preserved. No new engine build or physical solver is authorized.

Reuse the already successful recipe in `logs/upl_free_seepage_GPU_r1_execute.py`, current-only build/link/memcheck portion, without its old-header extraction, second build, or free-seepage-specific result checks. The retained library arguments are from `logs/upl_noslip_gpu_component_r1_link.call.json`. No new execution framework is required.

Use these fresh locations:

- helper: `outputs/upl_material_gpu_step_r2`, executable `upl_material_gpu_step_r2.exe`;
- component result: `outputs/upl_material_gpu_step_r2/result`;
- logs: `logs/upl_material_gpu_step_r2.compile/link/memcheck.call.json` and corresponding console logs; sanitizer report in the separate `logs/upl_material_gpu_step_r2.sanitizer.log`;
- final build/check receipts: `logs/upl_material_gpu_step_r2.build.json` and `.check.json`.

Before any build, require absent fresh destinations and no existing component owner, read the successful `upl_material_Debug_r1.build.json`, and consume its actual `project_objects`. It must contain111 project objects including `main.obj`; exclude exactly that object and link the remaining110. All must belong to the new `C:/Users/syosh/AppData/Local/Temp/upl_material_r1/Debug/int` closure. Do not substitute objects from earlier free-seepage/material builds. Use existing source/object size+mtime records and root's closed build review; no SHA scan.

After the normal MSVC14.36 x64 environment setup, compile the absolute fixture path once with:

```text
cl.exe /nologo /c /std:c++17 /EHsc /W3 /openmp /fp:precise
 /DWIN32 /D_CONSOLE /D_MBCS /D_WITHGPU
 /I<repo>/src/source /I<Cuda11.7>/include
 /Fo<fresh-helper>/helper.obj /Fd<fresh-helper>/compile.pdb
 /sourceDependencies <fresh-helper>/compile.dependencies.json
 /Od /MTd /Zi /RTC1 <absolute-T08>/support/upl_material_gpu_step_r2.cpp
```

The compiler is `D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64/cl.exe`. Link once with its matching `link.exe`, `/NOLOGO /MACHINE:X64 /SUBSYSTEM:CONSOLE /DEBUG`, fresh `/OUT` and `/PDB`, fixture object and the110 actual project objects. Preserve the retained library arguments:

```text
/LIBPATH:<repo>/src/lib/vs2022
/LIBPATH:C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/lib/x64
dsphchrono.lib LibJVtkLib_x64_v143_Debug.lib LibJNumexLib_x64_v143_Debug.lib
LibJWaveGen_x64_v143_Debug.lib LibDSphMoorDyn_x64_v143_Debug.lib
kernel32.lib user32.lib gdi32.lib winspool.lib comdlg32.lib advapi32.lib
shell32.lib ole32.lib oleaut32.lib uuid.lib odbc32.lib odbccp32.lib cudart_static.lib
```

Copy only the required existing runtime companions into the fresh helper directory: `DsphConfig.xml`, `ChronoEngine.dll`, `dsphchrono.dll`, and `vcomp140.dll` from `<repo>/bin/windows`, preserving their source stat records and copy metadata. No canonical program/config is replaced. Retain all actual warnings; do not suppress them or rerun to obtain a clean-looking log.

Only after compile/link success and a valid fresh executable, run it once under:

```text
<Cuda11.7>/compute-sanitizer/compute-sanitizer.exe --tool memcheck
 --leak-check full --target-processes all --error-exitcode 86
 --log-file <separate-sanitizer-log> <fresh-helper>/upl_material_gpu_step_r2.exe
 --source <T08>/outputs/upl_material_return_CPU_result_r1/points.csv
 --cpu <T08>/outputs/upl_material_shared_CPU_r1/result/points.csv
 --out <T08>/outputs/upl_material_gpu_step_r2/result
```

Line wrapping above is explanatory only; pass each option and value as separate argv entries. Capture native owner/tool/target identities and actual process-handle exits using the existing successful recipe. All compiler/linker/tool/target exits must be0, with explicit zero memcheck errors and zero leaked bytes/allocations. No second direct target run follows memcheck. On any failure preserve the first evidence and report; no automatic retries.

Review the actual142 CSV stage rows and completion:54 Pre-history,54 Cor-history,34 failure-no-write,284 tail-point and2982 protected-input-record checks. CPU same-input stress uses the original combined tensor budgets. Record actual warnings and numerical maxima. This does not test legacy default bit equivalence, host allocation/exception cleanup, spatial force integration, apex policy, Release parity or a plastic case admission.
