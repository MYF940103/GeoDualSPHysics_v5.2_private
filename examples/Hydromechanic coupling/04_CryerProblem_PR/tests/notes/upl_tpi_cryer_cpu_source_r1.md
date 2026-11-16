# Cryer CPU 3D TPI：完整源树恢复的窄准备阶段

状态：作者稿，尚未执行 prepare、编译、求解或原生解码。

本轮只新增：

- `tests/support/upl_tpi_cryer_cpu_source_r1_prepare.py`
- 本说明。

根线程完整阅读并明确准入后，prepare 才可创建新标签：

- `tests/outputs/upl_tpi_cryer_cpu_r1_source/`
- `tests/logs/upl_tpi_cryer_cpu_source_r1.prepare.json`

已有同名路径即拒绝，不覆盖、不删除，也不自动换名重试。prepare 只读旧档、
Git 对象和 tlog，复制新源文件；不编译、启动程序、读取粒子数据、生成 VTK、
运行分析、Git 写入或计算 SHA。失败时保留新建的部分目录及第一原因。

## 为什么不复用旧 84 个对象

C04 需要 `DynamicPoreFreeBody` 的完整对象布局和原来的三维全向运算。
C02 较早的 265 源码/86 对象基线不含相同的 C04 类布局；只替换两个 TU，
同时链接旧 C02 84 个对象，不能证明 ABI 一致。因此本阶段准备完整 C04
源树，下一阶段必须从新快照完整编译全部 86 个 CPU Debug TU。

旧 C04 `upl_cryer_freebody_r1_DebugCPU` 的程序和真实 86 个对象仍是有效的
历史运行证据，不能被改写为新源码编译的结果。本轮也不复用这些旧对象。
当前没有同家族完整 ReleaseCPU 主程序可直接采用；旧 CPU component 是
局部组件，不是完整 ReleaseCPU 求解器。

## 已审证据和历史口径限制

`logs/upl_cryer_freebody_r1.source.json` 指向真实存在的 Git 提交：
`de2492afb5be33e9077f8e4a96bfe755b0ffc7ed`。

它的 ZIP 只有 8 个源文件/头文件和 2 份文档：

`JSph.h`、`JSph.cpp`、`JSphCpuSingle.cpp`、`JSphGpuSingle.cpp`、
`JSphCpu.cpp`、`JSphGpu.cpp`、`JSphGpu_ker.h`、`JSphGpu_ker.cu`，
以及当时 XML 格式文档和 C04 README。

旧 DebugCPU 的真实 MSBuild 调用使用权威
`src/VS/DualSPHysics5ReCpu_vs2022.sln` 和独立 IntDir：
`C:/Users/syosh/AppData/Local/Temp/upl_cryer_freebody_r1/DebugCPU/int/`。
实际调用和构建出口均为 0。其 `CL.read.1.tlog` 有 86 个 TU 和 115 个本地
头文件，共 201 个仓库内依赖；这些路径全部能在上游 265 文件档案中找到。
旧 `CL.command.1.tlog` 没有 `/sourceDependencies`，也没有配套依赖 JSON。

tlog 能证明编译访问过哪些路径，不能证明这些路径当时所有内容。旧 source
收据只封存了上述 8 个源文件，不曾封存全部 201 个依赖。因此任何新清单都
不能追认“旧 DebugCPU 的完整编译时源码捕获”，也不能以这次重建宣称旧
86 对象与恢复的全部文件逐字节一致。

## 新 265 文件源树的逐项来源

上游采用 C02 `upl_spr_av_ReleaseCPU_r1.build.json` 已保留的 265 份源码
快照，不读取当前 `src/source`。逐文件与上述 Git 提交比较时，CRLF/LF
差异单独记录：255 份仅换行不同、2 份完全相同、8 份有内容差异。

内容差异只有以下 8 项：

- `JSph.cpp`、`JSphGpu.cpp`、`JSphGpu_ker.cu`、`JSphGpuSingle.cpp`：
  被本次历史 freebody 8 文件 ZIP 的原字节覆盖。
- `JSphHourglassGpu.cpp`、`JSphHourglassGpu.h`、
  `JSphHourglassGpu_ker.cu`、`JSphHourglassGpu_ker.h`：
  从明确的 de2492 Git blob 恢复，而不是混入较早上游 GPU HG 版本。

最终新源树共有：253 项上游档案原字节、8 项历史 freebody ZIP 原字节、
4 项 Git 基线 blob，共 265 项。每个文件记录来源、长度、上游与 Git
关系。已有 SHA 只作为来源收据的原有字段展示，不在本轮重算。

旧实际 CPU 的 201 个本地依赖中，4 项来自 freebody ZIP：`JSph.h`、
`JSph.cpp`、`JSphCpuSingle.cpp`、`JSphCpu.cpp`；其余 197 项来自上游
档案，且与 Git 基线内容一致（允许明确记录的换行差异）。4 项 GPU HG
恢复文件均未被该 CPU 编译依赖。此项证据说明新候选闭包在源码家族上可
追溯，不将其提升为旧编译时的完整内容证明。

新树另外从 Git 基线恢复权威 CPU SLN 和 `DualSPHysics5ReCpu.vcxproj`，
保留相对 `../source` 布局。项目原有 96 个 ClCompile 条目在 DebugCPU 下
排除 10 个 GPU TU，实际有效的 86 个名字必须与旧真实 tlog 完全一致。
不替换 MSBuild，不引入 CMake 或新构建系统。

此外原样复制已测 C02 私有 `upl_tpi_cpu_r1.h`，并先与 C02 作者稿逐字节
核对。它只是独立第 266 个私有 helper，不改变原 265 个基线源文件。
当前准备不向任何 C04 TU 添加调用，不变更方程、参数、边界、材料或默认
A 路径；也不声称 TPI 已经支持三维实际程序。

## 完整编译前的下一步

先审 `source_diff.json` 的逐项来源及新 prepare 收据，再做独立的两 TU
接入。该后续接入只允许已测 helper 的同一数学定义，在 C04 `HG=0` 的
freebody 资格下处理真正 XYZ；不得把 C08 schema2、周期列、SPR/HG
或 AV 新参数移植为本阶段默认值。

新完整 CPU Debug 编译必须使用恢复的权威项目及全新 IntDir/OutDir，实际
编译 86 个 TU，不复用旧 C02 或 C04 对象。原项目的 5 个 Debug 第三方
库、系统工具链和必要运行时须在构建准入时另行绑定；本 prepare 不复制
库/运行时，不擅自创建 build runner。权威项目仍通过
`../lib/vs2022` 定位库，后续构建应使用明确绑定的实际库目录覆盖，或保留
同一私有相对目录，不能误链接当前未知库。

最低成本后续资格为真实 C04 极短 CPU A/B/C，而不是 CPU 长峰窗：
先证明新 A 在相同原物理/XYZ/生命周期下与保留 CPU 128 步控制一致，再
覆盖 B/C 独立压力行和压力历史生命周期，以及原 full Rγ 的 Taylor 和
加速度项。128 步原 A 只有启动区、没有排水开启，不能冒充排水后峰值或
完整精度验收；排水/压力行的独立小夹具须保留。此处仅列缺口，不准入任何
求解、额外 half、长窗、正式工况或新 reader。

当前 C02 CPU/GPU 冻结快照、C04 旧源 ZIP/程序/原生数据、所有 PRE 和
暂停的 C08 owner/GPU 全部原位保护，不在此次准备中改动。
