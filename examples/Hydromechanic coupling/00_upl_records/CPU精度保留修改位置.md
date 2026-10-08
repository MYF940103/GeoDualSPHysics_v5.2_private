# 恢复 u-pw 后独立保留的 CPU 孔压精度修正

基准节点：`fe72537f8b61616e98134535bfaf0535a4269855`。本记录只描述基准之上的精度补丁，不把已放弃的 u-pl 开发视为保留功能。

修改方式：基准先恢复，再通过 `apply_patch` 应用 6 个文件、56 个局部补丁。完整逐行记录见 [cpu_precision.patch](cpu_precision.patch)；正向应用前检查、实施后反向检查均成功。`FunPorePressure.h` 为主线程保留的共用精度工具，本子任务未改动它。

## 保留与明确排除

保留压力状态 `p = double(high) + double(low)`，积分时先合并 `low + dt * rate`，再拆回两个 float；避免小于高位 float ULP 的增量逐步丢失。SPH 力与孔压率接口仍使用原 float 高位，不是全双精度求解器。

没有恢复动态 Darcy 第二遍历、u-pl 总开关、TPI、变孔隙率/渗透率、u-pl 边界、惯性修正或额外时间步约束。机械方程、原孔压率方程、原时间积分阶段顺序及原排水时钟不变。Shepard 仍以固定 `PorePress0` 为参考，仅让原平滑计算读写完整 high/low 状态。

## 具体位置

以下为实施后源码行号；完整补丁保留每个上下文，后续增删行时优先按函数名定位。

| 文件 | 位置 | 功能与目的 |
| --- | --- | --- |
| `src/source/JSphCpu.h` | 159、166、172 | 当前、Verlet 历史及 Symplectic 前一整步压力各配一个 residual 指针。 |
| 同上 | 252 | `GetParticlesData` 增加可选残差输出参数。 |
| `src/source/JSphCpu.cpp` | 22、115 | 引入精度工具并初始化三个指针。 |
| 同上 | 206、213、219 | 调整原数组池配额，覆盖当前/保存临时 residual 和对应时间层。 |
| 同上 | 279、313、351、385 | `ResizeCpuMemoryParticles` 同步保存、释放、重新分配、恢复三个 residual 数组。 |
| 同上 | 438、446 | `ReserveBasicArraysCpu` 分配当前及 Verlet 历史 residual。 |
| 同上 | 491、502、557 | `GetParticlesData` 接收、复制并随 normal-only 筛选压缩 residual。 |
| 同上 | 620 | `InitRunCpu` 按现有高位初始化方式复制 Verlet 低位历史。 |
| 同上 | 1249 | 仅显式物理初始化时清 residual；`HMINIT_None` 提前返回，保留读入的 restart residual。 |
| 同上 | 1367、1407 | 原排水清零及有支撑的 Yao 外推实际覆盖压力时同步清 residual。 |
| 同上 | 1618、2984 | 两处原 mDBC 孔压规定值实际覆盖高位时清 residual，避免旧低位污染边界值。 |
| 同上 | 1663、1668、1677、1686、1706、1711、1714 | Shepard 使用独立低位暂存，读取高低位之和的原 excess pressure，完成全部邻居读取后再同步写回，保留原固定参考与并行安全性。 |
| 同上 | 3940、3946、3950 | Verlet 选择与原高位相同的历史低位；边界成对复制；流体采用补偿更新。 |
| 同上 | 3965、3969、3984、3988 | Symplectic predictor/corrector 都以原前一整步的 high/low 为基准；分别用半步/整步增量，不把 predictor low 当整步历史。 |
| 同上 | 4019、4045、4054、4333 | Verlet 交换低位历史；Symplectic 分配、交换及释放低位前一步数组。 |
| `src/source/JSphCpuSingle.h` | 49、51 | 两类周期复制函数参数补齐当前与匹配历史 residual。 |
| `src/source/JSphCpuSingle.cpp` | 138、144、151 | 重启继承低位；新初始化及原历史初始化同步清零。 |
| 同上 | 320、343、344、359、380、381、479、482 | 周期副本当前与历史高低位成对复制，并接入原周期处理入口。 |
| 同上 | 526、533、541 | 原 cell sort 中同步排序当前、Verlet、Symplectic residual。 |
| 同上 | 1280、1298、1302、1333、1352 | 原保存流程分配、取出、保存并释放 `PorePressRes`。原 `PorePress`/`ExcessPorePress` 高位输出语义不变。 |
| `src/source/JPartsLoad4.h` | 100、139 | 可选 float residual 数组及只读 getter。 |
| `src/source/JPartsLoad4.cpp` | 27、39、88、98、120 | 有限值检查依赖；初始化、释放、零初始化分配和内存计数。旧 PART 无 residual 时默认低位 0。 |
| 同上 | 163、167 | 可选排序辅助函数保持高位、参考与低位的粒子映射；没有启用原先未调用的排序路径。 |
| 同上 | 221、254 | residual 要求已有高位/参考，且各 PART 分片的 residual 存在性一致。 |
| 同上 | 235 | 汇总分片数量使用当前 `pd2.Get_Npok()`，修复不同分片大小时原重复第一片数量的问题。 |
| 同上 | 258、265、303、307 | 高位、参考和残差必须为 float、每片长度精确匹配且有限；正确处理 BI4 尚未加载时的 file-backed count。 |
| 同上 | 367、375、386 | 可选 `RemoveBoundary` 辅助函数保持三个压力数组映射并释放旧内存；不改动其调用策略，也不宣称修复其他塑性/应力历史。 |

## 验证范围

主线程完成 authoritative CPU Debug/Release 全量重建后，本轮已重新编译并执行两组 fixture：各 218 个积分用例与 27 个辅助检查全部通过，两组构建/运行退出码均为 0。D/R 新结果互相逐字节相同，也与归档的历史精度 r3 结果逐字节相同，SHA256 为 `3AF2E158430BDEC2C05FA151B8D6B2DE87179C08C816A407C44C90FF2973FC6F`。

实际执行记录与日志索引见 [cpu_precision_execution_r1.json](cpu_precision_execution_r1.json)，结果为 [Debug](cpu_debug_precision_r1.json) / [Release](cpu_release_precision_r1.json)。运行后再次核对 198 项对象、源码、项目及 runtime DLL 哈希，均与各构建清单相同，见 [cpu_precision_postrun_r1.json](cpu_precision_postrun_r1.json)。Debug fixture 链接有既有第三方 LNK4099 缺 PDB 警告；Release 链接发生既有 VTK LTCG，不影响通过。运行日志的畸形 PART 异常属于预期拒绝测试，不是验收失败。

本轮 Symplectic 重构压力最大误差 `7.44913e-8 Pa`，Verlet（相容初始历史）为 `2.42107e-8 Pa`；相同测试中的旧 float-only 递推最大误差分别为 `5 Pa` 与 `2.8125 Pa`。这些是冻结孔压率的储存/积分误差，不是整场空间或时间离散误差。

新 fixture 执行时在 `verification_work/cpu_pressure_accumulation_harness.cpp`，去掉了唯一的旧 `PoreDynamicDarcy=false` 测试配置。构建脚本按 CPU `.vcxproj` 的启用源文件选择 84 个对象，不把残留 u-pl 对象混入。所有结果、日志、执行记录写在本记录目录；方法现已收入 `rollback_verification_methods.zip`，临时 `verification_work` 已统一清理。

该 fixture 覆盖真实 CPU frozen-source 积分、部分压力状态映射、周期复制和真实 BI4 高低位读写；不单独证明完整 cell-sort/resize 生命周期、整场空间收敛、GPU 精度或运行效率。完整求解器短回归由主线程单独记录。
