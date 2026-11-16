# C04 新完整源：全111 GPU Debug 构建作者稿

尚未执行。只新增同名 support Python 和本文；根线程全读并独立准入后才可
构建一次。此稿不运行 help/solver/native/VTK，不发通知、不做 Git 或 SHA，
不启动下一任务。仅支持本次 Debug；Release 如需要须后续独立准入。

## 真实原 GPU 工具链，区别于 CPU

原 C04 GPU `upl_cryer_freebody_r1_Debug/Release` 两个 MSBuild 真实调用和
构建均正常出口，各111对象。de2492 的 GPU 项目使用 Windows target10.0；
真实 CL/CUDA read tlog 和 link.read 显示 **SDK10.0.22000.0**，不是 CPU
构建的 SDK8.1。原 GPU 使用 CUDA11.7、MSVC v143 14.36.32532。
根线程已明确采用这些实际 GPU 来源，不把 CPU8.1 配方误套 GPU。

原 Debug 实际 27 个库：5 个项目 Debug 库、3 个 CUDA11.7 库
（cudart_static/cudart/cudadevrt）、12 个 SDK UM、6 个 MSVC
CRT/OpenMP 和1个 SDK UCRT。原 Release 为26个库。Debug 的原27库
路径全部从真实旧 link.read 绑定，新 link.read 必须正好采用原22个
CUDA/系统/工具库与5个新私有项目库副本，不能漂移到 CPU/UCRT旧版本。

MSBuild、vcvarsall、nvcc、cl、link、四个 CUDA11.7 BuildCustomizations
文件和所消费第三方/系统库均绑定实际 stat。vcvars 使用 x64、明确
10.0.22000.0、14.36；只在子进程环境设原 CUDA路径，保留 vcvars LIB，
移除 CL/_CL_/LINK/_LINK_ 注入和两 TPI selector。
完整环境 set 只在内存解析，不输出可能含敏感内容的环境清单。

## 完整源树与全部111对象

输入必须是新 `logs/upl_tpi_cryer_gpu_r2.prepare.json` passed 所指
`outputs/upl_tpi_cryer_gpu_r2_source`：source265＋两个 C04 私有 helper，
恢复的权威 `VS/DualSPHysics5Re.sln`、`DualSPHysics5Re.vcxproj`。
仅 JSphGpu.cpp/JSphGpuSingle.cpp/JSphGpu_ker.cu 三个 TU 挂接，类布局和
外部 kernel 签名不变，HG0不挂 adapter。公共 src/当前 C02 freezes 不读入。

r1 prepare 在创建输出前因旧 CUDA dependency tlog 将唯一 VS 项目路径误归
为源码而失败，原失败收据保留，不重跑。r2 仅明确分开257个源码依赖与1个
项目 metadata，未知仓库路径仍拒绝；18处 hooks/两个 r1 命名 helper/数值
定义不变。本未执行 builder 只改消费 r2 收据，Debug构建标签/配方不改。

原项目 Debug97 CL＋14 CUDA，有效集合必须与真实旧 CL.command 和旧
NVCC 编译回显完全一致。CUDA保留原14个名称/输出，包括两个
`FunctionsGeo3d_iker.h.obj`、`FunctionsMath_iker.h.obj`，不能按 .cu-only
或去掉扩展名来猜对象名。不存在旧107对象复用；全111在新空 IntDir 从头
编译。旧 tlog/日志仅是配方来源，不升级为旧完整编译时源内容捕获。

新标签 `upl_tpi_cryer_gpu_Debug_r1`：

- `tests/outputs/<tag>/out`：真实新 EXE/PDB/importlib/runtime。
- 同标签 `lib/vs2022`：5个 Debug 项目库私有逐byte副本。
- `%LOCALAPPDATA%/Temp/<tag>/int`：无空格新 IntDir，全111 obj、
  97个 CL sourceDependencies、CUDA read/write tlog、PDB/ILK/iobj。
- `tests/logs/<tag>.build.json`，environment/msbuild 两个实际 call/log 和 binlog。

已有任一新输出/IntDir/收据/调用不覆盖、不清理、不重试。原 source、程序、
PRE、失败 partial、正式结果及暂停的 C08 owner/GPU 均不操作。

## 原数值 flags 与依赖证据

权威 SLN 使用原 `/m:1 /nr:false /t:Rebuild`、Debug/x64/v143、
BuildProjectReferences=false，补新路径和明确原 SDK/toolset。私有 targets
仅改输出/库路径、关 build events、补97个 CL `/sourceDependencies` 和
实际 evaluated CL/CUDA 列表，不替换项目或原 CUDA settings。

CL 命令先按真实 `^` header 剥离行末完整 source，再解析 flags，避免
本次 CPU review 已发现的含空格但未加引号 source 被拆 token 假拒。
NVCC 使用真实旧/新 MSBuild 编译回显，不执行 XML 内历史遗留的 custom
命令字符串；按完整 quoted source 尾部先剥离再解析 flags。

逐97 CL比较仅允许 source、Fo/Fd 与新增 sourceDependencies 路径变化；
原 /Od /MTd /RTC1 /fp:precise /openmp、宏等全部不变。CUDA14逐项保留
原 compute86/sm86、-G、-g、machine64、cudart static、use_fast_math、
fmad/FTZ默认行为与所有原 host flags；只改变真实 source、-o、keep-dir、
host Fd 路径。include路径仅规范化同一路径的slash/case，不准换目录。
不为了审查方便禁掉 fast-math/FMA/FTZ。

每个97 CL dependency.Source均须匹配私有源码。CUDA依赖使用权威
CUDA11.7 MSBuild工作流实际生成的 `CudaCompile.read.1u.tlog`，要求14个
真实 source block及全部当前依赖；不另起一次 nvcc -M 或 reader。
全部实际 CL/CUDA依赖拒绝公共/其他仓库源码，只允许本私有 source、
恢复的项目和新 targets；CUDA/SDK/MSVC系统头保留真实stat。
实际编译必须消费两个新 helper。

最终检验真实 evaluated97/14、全部111对象、链接输入对象集合与原27库
闭包。实际 MSBuild 子进程采用既有只读 ownership helper，保留 Popen wait
与 Win32 handle 出口、PID/creation/exe/argv/parent。内部 cl/nvcc/link
未单独持有句柄，不编造这些子工具各自的 Win32 出口；其真实 commands、
sourceDependencies/CUDA read tlog、binlog与完整链接闭包另行保存。

运行时在新 EXE同目录复制原4 runtime和真实 DebugOpenMP vcomp140d.dll，
逐byte核副本，不运行程序探测。构建 passed 仍不是默认A回归、GPU memcheck、
XYZ B/C native资格或物理验收。

## 独立 root admission

入口：`python -B tests/support/upl_tpi_cryer_gpu_build_r1.py
--execution-authorized --admission ROOT_JSON`。

stage=`upl_tpi_cryer_gpu_build_r1.build_admission`、passed=true、build_only=true、
configuration=Debug、inputs 为全部消费 stat。包含两作者文件、Python/psutil、
复用 CPU build helper、新GPU prepare/files/source_diff、原C04 Debug/Release
build/call、Debug真实log与6份tlog、工具/customizations、原27库、原4 runtime
和DebugOMP，以及旧CL/CUDA依赖映射后的新私有文件/系统头。
不读取旧对象/原生BI4或做旧SHA扫描。

成功收据提供实际 program/runtime、111新对象、97CL/14CUDA配方和依赖、
原27库闭包、source_root/prepare及所有输入stat未变；不自动运行任何程序。
若实际构建完成但后审失败，保留真实成功工具出口和failed wrapper，后续
只做新离线审查，不重编已完成程序或覆盖失败证据。
