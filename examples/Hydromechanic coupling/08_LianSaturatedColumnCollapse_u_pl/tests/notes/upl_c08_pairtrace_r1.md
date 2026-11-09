# 首近对 causal 观察：私有作者稿

本稿生成时未构建、未启动求解或读取原生场。新增 `support/upl_c08_pairtrace_r1_build.py` 和 `outputs/upl_c08_pairtrace_r1_source/`；原 causal 源/程序、runtime_r6、原 r2 GPU PRE、生产源码及旧结果不改。

私有 ZIP 从 `outputs/upl_c08_causal_source_r1/source.zip` 完整派生，仅改三成员的四个观察 ID 映射：`JSphGpu.cpp` 两处 `wanted[3]`，`JSphGpu_ker.cu` 与 `JSphGpuSimple_ker.cu` 各一处 slot 映射，从 `[7017,5944,6814]` 改为 `[7011,7012,6230]`。`pairtrace_IDs.patch`、`source.json` 保存精确差异及逆替换逐字节复原证明；其他归档成员逐字节不变，尤其 `C08StageTrace.h` 不变。

仍为三 slot、原 97/56 列、原 POD/设备缓冲区、相同分配/索引/输出算术和采样：.60 s 之前每40个 global step 取样，Totals每次真实 Pre/Cor material/plane 调用累计。将来的 .30 s 窗只落在稀疏采样段；不声称解析每个2.5 μs主表事件，Totals仍记录三 ID 的全步累计。保持旧 dense 范围，不为本轮改采样或上限。

构建重放已通过 causal 的权威 VS/MSVC14.36/CUDA11.7 编译和链接参数。只提取封存归档中的全部 source/include 到全新 build 目录，不编译当前工作树，不采用 AV15/effective-AS/Shepard 候选。GPU Release 重新编译 `JSphGpu.cpp`、`JSphGpu_ker.cu`、`JSphGpuSimple_ker.cu`，显式恢复旧环境注入的 `C08_STAGE_TRACE` 和 `C08_CAUSAL_TRACE`，保留110个原对象，合计113个链接对象。编译日志须有原 header 的宏启用声明。NVCC 的 host PDB使用当前新目录内无空格相对文件名，避免旧路径重定向错误；CUDA架构、优化及数值选项保持原值。

CPU Debug 两宏关闭，GPU观察代码不编入，因此没有受这次 ID 替换影响的 CPU TU。按根决定，仅重新编译归档中未修改的 `JSphCpuSingle.cpp` 并链接86个原对象，总87个，作为默认 CPU 构建检查；它不验证GPU观察 ID，也不产生 causal 观测。CPU4/GPU7个运行依赖复制至各自全新目录，源依赖和旧对象均只读绑定。

独立构建入口（根全文审阅后逐个决定，不自动串联）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_pairtrace_r1_build.py --configuration DebugCPU --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_pairtrace_r1_build.py --configuration Release --execution-authorized
```

准确产物为 `outputs/upl_c08_pairtrace_DebugCPU_r1/DualSPHysics5.2CPU_win64_debug.exe`、`outputs/upl_c08_pairtrace_Release_r1/DualSPHysics5.2_GEO_win64.exe`；收据为 `logs/upl_c08_pairtrace_{DebugCPU,Release}_r1.build.json`。成功 schema含 passed/configuration/program/source_capture/source_archive/runtime/calls/consumed/consumed_stats_unchanged及实际编译/链接对象数。捕获来自旧 causal 已封存时点，不以当前 Git HEAD冒称源码版本。

物理仍是 runtime_r6 的 total-AS ε.2/n3、AV.1、CompletedOnly、keep5、fixed-plane、释放后 damping/Shepard OFF，同原 r2 GPU PRE。只换观察 ID不会新增物理参数、字段或数值修复；无需为此重复 half 或大 memcheck 链。后续一次 .30 s 真实观察须由根另准入，再以30帧全部22数组/真实clock/signed及原格式前缀对旧 r6/causal核无反馈。尚未发生的计算/对照不能由本构建稿宣称通过。

数据用于观察首近对材料、投影及 RHS 时序，不预设张拉/接触因果。材料原错误可先于 TraceEnd抛出，失败子阶段不保证写入主 CSV；日志不是完整失败状态重建，也不是物理验收。
