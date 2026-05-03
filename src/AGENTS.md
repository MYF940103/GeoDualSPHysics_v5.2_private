# Project instructions for Codex

This is a Windows Visual Studio 2022 C++/CUDA project for GeoDualSPHysics / DualSPHysics v5.2.

## Project structure

- `source/`: main C++/CUDA source code
- `lib/`: project and third-party libraries
- `VS/`: Visual Studio solution and project files
- `.vscode/`: VS Code build, IntelliSense, and debug configuration
- `../bin/windows/`: compiled executables

## Build environment

- OS: Windows
- Compiler: MSVC v143
- Build system: MSBuild
- IDE: VS Code
- Original IDE: Visual Studio 2022
- Main CPU solution: `VS/DualSPHysics5ReCpu_vs2022.sln`
- Main GPU solution: `VS/DualSPHysics5Re.sln`

## Build configurations

CPU Debug:

```powershell
msbuild .\VS\DualSPHysics5ReCpu_vs2022.sln /m /t:Build /p:Configuration=DebugCPU /p:Platform=x64 /v:minimal
```

CPU Release:

```powershell
msbuild .\VS\DualSPHysics5ReCpu_vs2022.sln /m /t:Build /p:Configuration=ReleaseCPU /p:Platform=x64 /v:minimal
```

GPU Debug:

```powershell
msbuild .\VS\DualSPHysics5Re.sln /m /t:Build /p:Configuration=Debug /p:Platform=x64 /v:minimal
```

GPU Release:

```powershell
msbuild .\VS\DualSPHysics5Re.sln /m /t:Build /p:Configuration=Release /p:Platform=x64 /v:minimal
```

## Default VS Code workflow

The default VS Code build task is CPU Debug:

```text
Build DualSPHysics5ReCpu Debug x64
```

The default VS Code debug configuration is:

```text
Debug CPU slope45 ImpactForces
```

CPU Debug executable:

```text
..\bin\windows\DualSPHysics5.2CPU_win64_debug.exe
```

GPU Debug executable:

```text
..\bin\windows\DualSPHysics5.2_win64_debug.exe
```

CPU Release executable:

```text
..\bin\windows\DualSPHysics5.2CPU_win64.exe
```

GPU Release executable:

```text
..\bin\windows\DualSPHysics5.2_GEO_win64.exe
```

## Current debug case

The currently configured debug case is:

```text
D:\MYF\SPH\GeoDualSPHysics_v5.2\examples\myf\02_ImpactForces
```

CPU Debug arguments:

```text
-cpu -mdbc CaseImapctForces3D_slope45_out\CaseImapctForces3D_slope45 CaseImapctForces3D_slope45_out -dirdataout data -svres
```

GPU Debug arguments:

```text
-gpu -mdbc CaseImapctForces3D_slope45_out\CaseImapctForces3D_slope45 CaseImapctForces3D_slope45_out -dirdataout data -svres
```

Note: the case name is intentionally spelled `Imapct`, matching the actual file names.

## Rules for code changes

- Do not change physical equations unless explicitly requested.
- Do not change SPH formulation, rheology, kernel functions, boundary conditions, time integration logic, mDBC, shifting, or DEM coupling without explaining the numerical consequences.
- Prefer minimal and local patches.
- Preserve existing coding style and variable names when possible.
- Before editing, summarize the files you plan to change.
- After editing, run the default CPU Debug build task.
- Use GPU Debug only when CUDA-specific logic, GPU memory, or GPU kernels must be checked.
- Treat Visual Studio project files `.sln` and `.vcxproj` as authoritative for compilation.
- Do not replace this project with CMake, MinGW, or a new build system.
- Be careful with CUDA kernels, GPU memory indexing, cell-linked-list logic, neighbor interaction loops, particle shifting, mDBC, and DEM-related coupling.

## Preferred workflow

1. First read and explain relevant code.
2. Do not edit files unless explicitly asked.
3. For debugging, start from the CPU path when possible.
4. Use the GPU path only for CUDA kernels and GPU memory behavior.
5. Keep patches minimal and reversible.
6. Report all modified files after making changes.
7. Build after changes and summarize compiler errors or warnings.