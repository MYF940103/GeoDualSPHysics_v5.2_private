# C04 私有 TPI 候选：全 86 TU CPU Debug 构建

作者稿，只新增 `tests/support/upl_tpi_cryer_cpu_build_r1.py` 与本 note。尚未执行本构建脚本。root 必须另行完整审阅并准入唯一 build；脚本不会运行 help、solver、native、GenCase、VTK、Git、half、峰窗或后续 job。

## 为什么全量编译

已完成的 `upl_tpi_cryer_cpu_source_r1.prepare.json` 恢复了 C04 265 文件基线和原权威 CPU solution/project。历史 C04 ZIP 只有 8 个改动文件，旧 tlog 证明 201 个本地依赖的访问路径，但没有全部历史内容捕获。因此本轮是可追溯的新源码重建，不追认旧 86 对象的完整内容身份。

`upl_tpi_cryer_cpu_overlay_r1.prepare.json` 在新源码树仅修改 `JSphCpu.cpp`、`JSphCpuSingle.cpp` 两个 hook TU；通用 `upl_tpi_cpu_r1.h` 与已审 C02 helper 原字节一致。C04 保持真正 XYZ、freebody、HG0，不调用 HG adapter。新构建 **全部 86 个 CPU TU 重新编译**，不采用旧 C02 的 84 对象，也不采用旧 C04 的 86 对象。旧对象仅作为历史 tlog 路径背景，不被读入、复制或链接。

## 路径与权威项目

构建输入是 overlay receipt 指向的完整相对树：`VS/DualSPHysics5ReCpu_vs2022.sln`、`VS/DualSPHysics5ReCpu.vcxproj` 与 `source/`。VS/source 相对布局原样，不修改权威项目、不用 CMake，也不混当前 `src/source`。

恢复的 DebugCPU 项目共 96 个 ClCompile 条目，原 10 GPU TU 按项目配置排除，有效 CPU86 的名字必须与旧真实 `CL.command.1.tlog` 一致。私有 targets 只补编译依赖和输出/库路径元数据，不替换项目的物理宏或数值编译选项。

新标签 `upl_tpi_cryer_cpu_DebugCPU_r1`：

- `tests/outputs/upl_tpi_cryer_cpu_DebugCPU_r1/out/`：新 exe、PDB、import lib、必要 runtime。
- 同 root 的 `lib/vs2022/`：五个实际 Debug 项目第三方库私有副本。
- `%LOCALAPPDATA%/Temp/upl_tpi_cryer_cpu_DebugCPU_r1/int/`：全新无空格 IntDir，86 obj、编译 PDB、ILK、iobj、每 TU dependency JSON、真实 tlog。
- `tests/logs/upl_tpi_cryer_cpu_DebugCPU_r1.build.json` 和 environment/msbuild 两份真实 call/log、binlog。

已有同名 root/IntDir/receipt/call/log 均保护；失败不覆盖、不清理、不重试或自动换标签。规范程序、C02 GPU build、暂停 C08 owner/PRE/依赖均不操作。

## 原工具与实际库选择

保留 MSVC v143 **14.36.32532**。只读旧 C04 实际 link.read 发现原闭包为：5 个 Debug 项目库、12 个 Windows SDK8.1 UM 库、5 个 MSVC14.36 CRT/OpenMP 库、1 个 UCRT10.0.10240.0，共 **23 个实际 .lib**。不把新 C02 的 Windows10 SDK 库误称此旧 C04 配套。

恢复项目的 `WindowsTargetPlatformVersion=8.1` 保留并显式传同值。VS2022 本机 vcvarsall 文本明确支持 `x64 8.1 -vcvars_ver=14.36`。环境通过私有 literal CRLF CMD batch 加载；`cmd /d /s /c load_environment.cmd` 使用相对 batch 名与 private cwd，避免嵌套引号故障。只解析环境到内存；不保存可能含敏感值的完整 `set` stdout。移除 CL/_CL_/LINK/_LINK_ 注入变量与两个私有 TPI selector，不覆盖 vcvars `LIB`。

五个 Debug 项目库从旧真实 link.read 指向的原文件绑定到本次 admission，先复制至新私有 lib 目录并逐字节验证副本。原 system/MSVC/UCRT 目录也由同一 tlog 明确绑定，以 AdditionalLibraryDirectories 放在搜索前部；vcvars LIB 本身保留。实际 link.read 必须恰好消费这五个私有副本及原 18 个 system/toolchain 文件；未知或漂移的库使本次新构建检查失败。

运行时来源明确：旧 C04 build receipt 的 DsphConfig.xml、ChronoEngine.dll、dsphchrono.dll、vcomp140.dll，另 VS14.36 的 DebugOpenMP `vcomp140d.dll`。只新目录复制/字节比较，不替换旧文件，不调用新程序测试。

## 编译闭包、flags 与所有输出

原权威 SLN 通过 MSBuild `/m /t:Build /p:Configuration=DebugCPU /p:Platform=x64` 构建；补新 OutDir、IntDir、v143 version、SDK8.1、private ForceImportAfterCppTargets、禁用所有 build events 与 binlog。不运行 post-build 移动命令，不产生规范目录程序。

每个有效 TU 单独追加 `/sourceDependencies <IntDir>/<stem>.dependencies.json`。实际 evaluated compile list、86 个新 object 集合和 86 个 dependency.Source 必须全匹配。每 TU Includes 拒绝当前 `src/source` 与任何私有 source 树以外的仓库内头文件；正常 MSVC/Windows 系统 include 允许并记录真实 stat。必须实际消费私有 generic helper。

新/旧 CL.command 逐 TU 比较。唯一允许变化是源码路径、Fo/Fd 输出路径与新增的一对 sourceDependencies 参数；原 `/Od /MTd /RTC1 /fp:precise /openmp`、宏、原其他 flags 不变。不同数值优化或未知编译选项不能混入。

所有新 exe/PDB/ILK/iobj/import lib/obj/dependency 文件在上述私有路径；23 库的实际读取闭包另从真实 link.read 复核。编译与链接由真实 MSBuild 子进程拥有；脚本记录 MSBuild 的真实 Popen wait 与独立 Win32 handle 退出、PID/创建时间/exe/argv/父进程。没有单独持有内部 86 cl/link 的句柄，因此不编造每个内部工具的 Win32 退出，使用原命令/read tlog、dependency JSON 与 binlog 表明具体执行闭包。

## 单次 root admission

调用接口：

```text
python -B tests/support/upl_tpi_cryer_cpu_build_r1.py --execution-authorized --admission ROOT_REVIEWED_JSON
```

JSON：`stage=upl_tpi_cryer_cpu_build_r1.build_admission`、`passed=true`、`build_only=true`、`configuration=DebugCPU`、`inputs=[stat...]`。

inputs 包括两作者文件/Python/psutil、source/overlay prepare 与 manifests、overlay 所有 files、恢复 SLN/project、原 C04 build/call、实际旧四种 tlog、MSBuild/vcvarsall、23 原 lib、四个旧 runtime 与 DebugOpenMP DLL。按实际消费 stat 校核，不重复扫描旧 source/object/BI4 SHA，也不为新 exe 做本阶段未要求的 hash。

成功 receipt 提供 `configuration=DebugCPU`、`source_prepare`/`prepared`、source_root、program、runtime.source/destination、object_count86、original_objects_reused0、完整编译/依赖/库证据与 consumed_stats_unchanged。只代表新程序构建完成；A 对保留 CPU 控制的真实 native 回归和 B/C 极短窗口仍必须分别 root 准入，不能由 build 自动启动或宣称三维 TPI 物理验收。
