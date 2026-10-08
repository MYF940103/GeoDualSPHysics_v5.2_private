# 孔压 double 状态替换：阶段 1 修改位置
日期：2026-09-09。以下行号对应本阶段源码，可用函数名搜索定位。

## 范围与基线

基线是替换前工作区中的“float 高位＋float 余量”补丁，并非直接使用 Git HEAD。
源码归档：`pore_double_stage1_baseline_sources.zip`；
文件及基线执行程序 SHA256：`pore_double_stage1_manifest.json`。
基线 CPU/GPU Release 与 DLL 保存在 `../outputs/pore_double_baseline/`。

本阶段仅简化权威孔压状态、历史、搬运及持久化。孔压率仍为 float；
n、k、Kw、密度、应力、速度以及原 SPH/边界/时间积分方程不升级。
旧数组的 float 高位原来用于空间算子，本阶段在相同入口显式投影为 float，
防止把存储替换和空间算子升级混在一次验收中。这些过渡性投影不是“全 double 孔压方程”。

## 生产文件逐项清单

所有源文件均位于 `src/source/`，工程文件位于 `src/VS/`。
总计修改 19 个既有文件，删除 1 个已归档的补偿头文件。

| 文件 | 位置/函数 | 功能与目的 |
|---|---|---|
| JSphCpu.h | 41 stinterparmsc、62 StInterparmsc；158、164、169；246；276–289；相互作用函数接口 | 当前孔压、参考孔压、活动积分历史改为 double 指针；删除余量成员和形参；rate 保持 float。 |
| JSphCpu.cpp | 22、113；178 AllocCpuMemoryParticles；246 ResizeCpuMemoryParticles；410 ReserveBasicArraysCpu | 移除补偿头文件和余量生命周期；double 内存池计数、分配、扩容保存恢复。 |
| JSphCpu.cpp | 475 GetParticlesData；603 初始历史复制；1230 附近 InitHydroMechState | double 状态提取/粒子筛选、初始化与历史复制；保留原初始化数值计算和土体状态逻辑。 |
| JSphCpu.cpp | 1336 ApplyFreeSurfacePorePressure；1357 Yao；1416 InteractionPorePressureRateT；1521 mDBC | 排水直接写 double 零；Yao/mDBC 按旧 float 输入及 prescribed-value 舍入；独立孔压率接口使用 double 状态、float rate。 |
| JSphCpu.cpp | 1636 ShepardRegularizePorePressureT；1696 调用 | 用单个 double 临时数组替代高低位临时数组；先读全部邻域再写回；参考压力、权重和调用时序不变。 |
| JSphCpu.cpp | 2109 相互作用入口；2179、2263、2332 压力读取；2781 附近集成 mDBC | 传递 double 状态；孔压反馈的两个加数分别转 float，Darcy/邻域/边界同样保留旧算子输入精度。 |
| JSphCpu.cpp | 3912 ComputeVerletPorePressure；3930 ComputeSymplecticPrePorePressure；3949 ComputeSymplecticCorrPorePressure；3977–4024、4294–4300 调用/交换 | 直接 old + dt * double(rate)；删除高低位更新；不改 Verlet 历史选择、预测半步、校正整步、边界阶段和指针交换顺序。 |
| JSphCpuSingle.h | 48、50 PeriodicDuplicateVerlet/Symplectic | 周期复制签名接收 double 当前/参考/历史，去掉余量。 |
| JSphCpuSingle.cpp | 134 附近 ConfigDomain；315、353 周期函数；472 调用；518 排序 | 重启 double 复制；周期映像及排序不丢失低于 float ULP 的状态；rate 仍按 float 复制。 |
| JSphCpuSingle.cpp | 1254 SaveData，1269–1341 | 输出临时缓冲使用 double；PorePress、PorePress0、ExcessPorePress 均输出 double；不输出 PorePressRes。 |
| JCellDivCpu.h | 169 SortArray(double*) | 新增标量 double 排序声明。 |
| JCellDivCpu.cpp | 411 SortArray(double*) | 复用原 VSort 缓冲；保持原 SortPart 排列和部分排序起点。 |
| JSphGpu.h | 115–118、160–162、173、179；粒子上下载/边界相关接口 | 主机、设备、输出、历史孔压统一 double；删除余量；设备孔压率仍 float。 |
| JSphGpu.cpp | 139 初始化；271、307 主机内存；365、438、619 设备内存 | 按 double 计算字节数和池容量，匹配 sort/Shepard 临时需求；删除余量数组。 |
| JSphGpu.cpp | 777 ParticlesDataUp；822 附近 ParticlesDataDown；1064 InitRunGpu；1169 Shepard；1184 初值 | 上下传及筛选使用 double；原 float 初值提升到 double；Shepard 单个 double 结果缓冲。 |
| JSphGpu.cpp | 1387 ComputeVerlet；1434 ComputeSymplecticPre；1484 ComputeSymplecticCorr | 传递 double 当前/历史；去掉余量交换及复制；积分和边界时序不变。 |
| JSphGpuSingle.cpp | 172 重启；385 RunCellDivide；420、451、470 排序；1049 SaveData/1095 数组输出 | double 重启、周期排序、正常粒子提取和 double PART 输出。 |
| JSphGpu_ker.h | 159、203、277–308、381–385 | CUDA 相互作用、边界、积分、周期复制统一 double 压力指针；rate 保持 float。 |
| JSphGpu_ker.cu | 1040 排水；1138 Yao；1178 KerUpdatePorePressure；1254 mDBC；1349 Shepard | 直接 double 状态积分；先按值读取 old 以兼容 Verlet 原位写；边界/非流体复制；Shepard 用 double 权威状态。 |
| JSphGpu_ker.cu | 1519 压力反馈；1589、1787 孔压算子；2426、2753 mDBC | 显式 float 投影维持旧空间算子精度及 prescribed-boundary 舍入。 |
| JSphGpu_ker.cu | 2157 Interaction_ForcesT_KerInfo | 内核占用率查询的函数指针签名同步为 const double*；修复首次 GPU 编译暴露的遗漏。 |
| JSphGpu_ker.cu | 4633、4687 附近周期核及包装 | double 当前/参考/历史周期复制，删除余量参数和复制。 |
| JCellDivGpu.h | 162 SortDataArrays | 新增 double 标量排序声明。 |
| JCellDivGpu.cpp | 372 SortDataArrays(const double*,double*) | 将 double 数组转交排序核；沿用 DivideFull/NpbFinal 确定排序起点，使用原排序数据。 |
| JCellDivGpu_ker.h | 60 SortDataParticles | 新增 double 标量 CUDA 排序包装声明。 |
| JCellDivGpu_ker.cu | 646 核；746 SortDataParticles | double 标量排列；pini 之前仍复制原序，之后使用 sortpart。 |
| JPartsLoad4.h | 98、136–137 | loader 仅保存 double 当前/参考状态；移除运行期余量与 getter。 |
| JPartsLoad4.cpp | 39、86、116、160、386 | 内存、大小计数、ID 排序、删除边界适配 double。 |
| JPartsLoad4.cpp | 216–328 LoadParticles | 旧 float 直接提升；旧 float+余量按 double(high)+double(low) 恢复；新 double 直接读取。检查类型、长度、有限值、分片一致性；拒绝 double+余量等歧义/损坏数据。 |
| FunPorePressure.h | 删除整个文件 | 不再需要 Split/Value/Increment 等高低位辅助函数；原文件可从基线 ZIP 恢复。 |
| DualSPHysics5Re.vcxproj | 原 532，FunGeo3d.h 附近 | 移除已删除补偿头文件的 ClInclude；不改编译配置。 |
| DualSPHysics5ReCpu.vcxproj | 原 529，FunGeo3d.h 附近 | 同上。 |

## 精度与重启边界

- 保留小增量不意味着所有孔压运算均为 double：rate、空间算子输入及规定边界值仍保留旧精度。
- double 状态与 float 高低位补偿不是逐位等价的表示；Shepard 重构及 CUDA 融合乘加也可能产生微小差别。
- 旧文件向新程序兼容；未宣称旧执行程序可读取新的 double PART。
- 新 PART 保存 double 状态不丢低位，不代表原程序所有力学/积分历史都支持精确续算。
  例如原重启重置 Kplastic、密度及部分历史的行为，本阶段不改变。
- 核心孔压 current/reference/rate/活动历史为 28 B/粒子，基线为 24 B/粒子；
  增加来自参考压力 4→8 B，当前/历史的 double 与原两个 float 各自同为 8 B。
  内存池预留和主机输出缓冲另计，不能将 4 B 直接当作整个求解器总内存增量。
- 新执行程序已替换 bin/windows 下相应目标；旧补丁 Release 单独归档且旧算例结果不覆盖。

## 测试文件组织

只使用本算例既有 tests 分类，不添加根目录正式 XML/BAT：

- `tests/configs/pore_double_stage1/`：短程派生配置。
- `tests/support/pore_double_stage1/`：CPU/GPU/loader harness、构建和回归脚本。
- `tests/outputs/pore_double_baseline/`：基线执行程序及 DLL。
- `tests/outputs/pore_double_stage1/`：独立短程求解输出和可再生测试产物。
- `tests/logs/pore_double_stage1/`：构建日志、验证明细、运行命令与哈希。
- `tests/notes/pore_double_stage1_*`：基线归档、修改清单及验收记录。
- 正式验收对比图统一保存于本算例根目录 `figures/`，使用 `pore_double_stage1_` 前缀。
