# C04 新完整源：全111 GPU Release 构建作者稿

尚未执行。仅新增 `support/upl_tpi_cryer_gpu_release_build_r1.py` 和本文。
从根已完整审查并真实通过的 Debug builder 最小克隆，根线程须独立审阅、
准入后才可构建一次。程序不运行 help/solver/native/VTK，不发通知，不做
Git/hash，也不自动启动后续任务。现有 DebugB2/memcheck及暂停 C08不操作。

## 只切换真实 Release 配方

源码仍使用已通过 `logs/upl_tpi_cryer_gpu_r2.prepare.json` 所指完整
`outputs/upl_tpi_cryer_gpu_r2_source`：265 原基线文件＋两个私有 helper，
仅 C04 三个 GPU TU 的既定挂接。prepare、helper、物理方程和所有旧文件
不改；无需另起 source prepare。原 C04 `upl_cryer_freebody_r1_Release`
build/call、真实 Release.log 和六份 tlog 是实际编译/链接配方来源。
原 Debug build/call 仅作为同一基线的既有闭包记录，绝不提供对象或运行时。

权威恢复 GPU SLN/project 使用 Release/x64/v143。Release 条件下全部
97 CL＋14 CUDA 重新编译，包含 `FunctionsGeo3d_iker.h.obj` 和
`FunctionsMath_iker.h.obj`。新空 IntDir 中必须恰有111对象，全部链接输入
均来自此处；不复用 Debug、旧 Release、C02或任何已有对象。旧 source
恢复和 tlog 路径不被称为原历史完整编译时源码内容捕获。

实际 GPU 工具链为 SDK10.0.22000.0、CUDA11.7、MSVC14.36.32532；不套用
CPU SDK8.1。vcvarsall 的真实子进程明确选择这些版本，保留其 LIB，清掉
CL/_CL_/LINK/_LINK_ 以及两 TPI selector。只在子进程设置原 CUDA 路径，
环境 set 在内存解析，不把可能敏感的完整环境写日志。

## Release 的真实26库与4项 runtime

真实旧 Release link.read 中是26个库：5个项目 Release库、3个CUDA库、
12个 SDK UM库、5个 MSVC CRT/OpenMP库以及1个 SDK UCRT库。新链接必须
恰为原21个 CUDA/系统/工具库加5个新私有项目库副本：

- dsphchrono.lib
- libjvtklib_x64_v143_release.lib
- libjnumexlib_x64_v143_release.lib
- libjwavegen_x64_v143_release.lib
- libdsphmoordyn_x64_v143_release.lib

上述五库从真实旧 Release依赖中绑定并逐byte复制到新 `lib/vs2022`，不使用
Debug库。实际 SDK/UCRT/MSVC/CUDA库来源逐项绑定；不扫描旧对象或BI4 SHA。

Release仅复制其原 build receipt 中的4项runtime到新EXE目录：
`DsphConfig.xml`、`ChronoEngine.dll`、`dsphchrono.dll`、`vcomp140.dll`。
逐byte检查副本，不加 Debug 的 `vcomp140d.dll`，不执行程序来猜缺失DLL。

## 完全保留实际 flags 与依赖验证

MSBuild仍是权威SLN `/m:1 /nr:false /t:Rebuild`，显式 Release/x64/v143、
SDK10.0.22000.0/MSVC14.36，BuildProjectReferences=false。私有 targets
只关 build events、设新输出/库路径、补97个 `/sourceDependencies` 和实际
CL/CUDA evaluated列表；不替换项目或CUDA工作流。

逐97条CL对照真实旧Release，仅允许 source、Fo/Fd和新依赖记录路径变化。
保留原 `/O2 /MT /fp:precise /openmp /Zi`、宏及其它全部flags；不混入
Debug的 `/Od /MTd /RTC1`。CL先用真正 `^` source header 剥离完整行末
source，再解析flags，避免含空格但未加引号的源码路径假拒。

14条NVCC对照真正旧/新编译回显，保留原 compute86/sm86、machine64、
cudart static、use_fast_math及全部原host Release flags；没有Debug的
`-G/-g`。只允许source、-o、keep-dir和host Fd路径变化，不为了审查改FMA、
FTZ或 fast-math。原CL/CUDA include目录只允许同一路径的slash/case规范化。

每个97 CL dependency.Source必须是新私有TU；CUDA使用实际
`CudaCompile.read.1u.tlog` 的14个source blocks，不另起nvcc -M。
全部编译依赖拒绝公共/其它仓库源，只允许本私有source、恢复的project、
新targets和真实系统头；两个私有helper必须实际被消费。

最终旧/新link命令的111对象顺序及非路径flags必须相同；原Release的
`/OPT:REF /OPT:NOICF /LTCG:incremental` 等并不改写。新库/PDB/ILK/iobj/
importlib路径私有，所有库必须与上面的原26库来源精确对应。

## 新标签、独立调用与真实出口

构建标签 `upl_tpi_cryer_gpu_Release_r1`：

- `tests/outputs/<tag>/out`：新 `DualSPHysics5.2_GEO_win64.exe`、PDB、
  importlib及4项runtime。
- `tests/outputs/<tag>/lib/vs2022`：5个Release项目库副本。
- `%LOCALAPPDATA%/Temp/<tag>/int`：无空格全新IntDir，111对象、97份依赖、
  CUDA tlog、PDB/ILK/iobj。
- `tests/logs/<tag>.build.json`、environment/msbuild真实call/log和binlog。

已有上述输出、调用、IntDir或receipt均拒绝覆盖；原Debug成功及原失败、
C08/PRE/BI4、源码快照和正式数据保留。实际MSBuild通过既有owned调用持有
真实Popen+Win32句柄，记录PID/creation/exe/argv/parent和两个出口。未独立
持有内部cl/nvcc/link句柄，不编造它们各自的Win32退出码；commands、依赖、
完整对象/库闭包及binlog另作真实实施证据。

入口仅供根独立准入：`python -B tests/support/upl_tpi_cryer_gpu_release_build_r1.py
--execution-authorized --admission ROOT_JSON`。

准入stage=`upl_tpi_cryer_gpu_release_build_r1.build_admission`，passed=true、
build_only=true、configuration=Release。inputs必须绑定两作者文件、Python/
psutil、复用CPU build helper、prepare/files/source_diff、恢复项目、原Release
build/call/log/六份tlog与Debug build/call、所有工具/customizations、原26库、
原4runtime及旧依赖映射后的新私有文件/系统头。

成功receipt给出实际program/runtime、111全新对象、97CL/14CUDA配方及依赖、
26库闭包、source_root/prepare、所有输入stat未变，help/solver/native/VTK
调用均0。构建通过不等于默认A回归、同算法CPU/GPU对照、数学/物理精度或
正式发布验收。若构建完成而后审失败，只保留真实出口和failed wrapper，
后续离线修派生审查，不重编、覆盖或自动启动物理计算。
