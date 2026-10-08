# GPU：回到 u-pw 后保留的孔压精度修正

增量基线为 Git 提交 `fe72537f8b61616e98134535bfaf0535a4269855`。本次只恢复下列五个 GPU 文件中的 high/low 孔压状态补丁，共 167 行新增、94 行删除；与回退前已验收的精度快照在统一换行后文本一致。没有恢复 u-pl、动态 Darcy、TPI、变孔隙率/渗透率或相关配置保护。

压力状态表示为两份 float：`high + low`。积分更新先用 double 计算 `high + (low + dt * rate)`，再拆回 high/low，保留小于单个 float ULP 的累计增量。原 GPU 力学、本构及孔压率算子继续读取 float high；这不是全求解器双精度，也不保证全耦合时间二阶。边界直接覆盖压力时清除旧 low；Shepard 用原权重处理完整 high/low 状态。

以下行号对应本次恢复后的实际源码。

## 1. `src/source/JSphGpu.h`

| 修改行 | 字段 | 功能和目的 |
|---|---|---|
| 116、119 | `PorePressRes`、`AuxPorePressRes` | 主机下载及输出镜像，低位与正常粒子输出顺序一致。 |
| 163 | `PorePressResg` | device 当前孔压低位。 |
| 177、184 | `PorePressResM1g`、`PorePressResPreg` | Verlet 历史及 Symplectic 整步历史低位；避免把不同时间层的高低位混用。 |

## 2. `src/source/JSphGpu.cpp`

| 函数及修改行 | 功能和目的 |
|---|---|
| 构造函数：68；`InitVars`：153、158、161 | 所有新增低位指针初始化为空。 |
| `FreeCpuMemoryParticles`：285、288；`AllocCpuMemoryParticles`：327、330 | 释放/分配主机当前和输出低位，并计入原有内存统计。 |
| `AllocGpuMemoryParticles`：394、401、408 | 增加当前、M1/Pre 低位及排序/Shepard scratch 的数组池容量。 |
| `ResizeGpuMemoryParticles`：471、475、477；509、513、515；551、555、557；589、593、595 | GPU 扩容时成组保存、释放、重新保留和恢复 current/M1/Pre 低位，防止丢失或错配历史。 |
| `ReserveBasicArraysGpu`：652、659 | 分配当前低位及 Verlet M1 低位。 |
| `ParticlesDataUp`：806、810 | 初始/重启状态的当前及 M1 低位上传 device。 |
| `ParticlesDataDown`：841、868、892 | 下载低位，normal-only 输出压缩时同步移动，再放入 Aux 镜像。 |
| `InitRunGpu`：1093 | 当前压力与 M1 历史低位采用同一初始化来源。 |
| `ApplyFreeSurfacePorePressure`：1130；`ApplyYaoTopStripPorePressureExtrapolation`：1141；`InteractionPorePressureMdbcCorrection`：1184 | 将低位传给既有排水、条带外推和独立 mDBC 覆写路径，便于压力被指定时清除过期低位。 |
| `ShepardRegularizePorePressure`：1194、1196、1198、1200、1202 | 两个独立 scratch 预拷贝 current high/low，滤波后同步拷回并释放；无支撑 fallback 保留原状态。 |
| `InitHydroMechPorePressure`：1319、1321、1325 | 显式初始化压力时同步清零主机/device/M1 低位；不改变原初始化模型。 |
| `ComputeVerlet`：1432、1438、1448 | 原 `dt`/`2dt` 及 phase 规则不变；传入相应高低位历史并成对交换。 |
| `ComputeSymplecticPre`：1475、1483、1485 | 保留并交换 Pre 高低位，从原整步状态产生半步预测。 |
| `ComputeSymplecticCorr`：1528、1544 | 从同一 Pre 高低位计算整步校正，随后释放 Pre 低位。 |

## 3. `src/source/JSphGpuSingle.cpp`

| 函数及修改行 | 功能和目的 |
|---|---|
| `ConfigDomain`：173、179 | 继承共享 PART 加载器的低位；新初始化则补零。旧 PART 缺低位时由共享加载器补零。 |
| `RunPeriodic`：359、362 | 周期粒子复制同时传 current/M1/Pre 低位。 |
| `RunCellDivide`：423、428、433；457、459、461；479、481、483 | 当前、Verlet M1、Symplectic Pre 的低位使用与高位相同的 cell-sort 映射。 |
| `MdbcBoundCorrection`：647 | 合并机械 mDBC 调用增加低位参数；不改变 mDBC 力学公式或滑移方式。 |
| `SaveData`：1109 | PART 增加可选 float `PorePressRes` 数组。原 `PorePress` 和 `ExcessPorePress` 输出仍按既有 high 接口，不冒充完整 double 压力。 |

## 4. `src/source/JSphGpu_ker.h`

| 修改行 | 功能和目的 |
|---|---|
| 277、282、284、286、291、296、308 | 排水、条带外推、Verlet/Symplectic 更新、独立/合并 mDBC、Shepard 的声明贯通相应低位参数。 |
| 381、385 | 两种周期复制入口贯通 current 与 M1/Pre 低位；可选参数保留原非水土耦合调用兼容性。 |

## 5. `src/source/JSphGpu_ker.cu`

| 函数及修改行 | 功能和目的 |
|---|---|
| 24 | 包含 CPU/CUDA 共用 `FunPorePressure.h`，不复制另一套算术实现。 |
| `KerApplyFreeSurfacePorePressure`：1042、1045；host wrapper：1052、1056 | 排水压力指定为零时 high/low 同时清零。 |
| `KerExtrapolateYaoTopStripPorePressure`：1113、1144；分派：1153、1157、1163、1166、1171 | 保留原外推公式；覆写 high 时清 low，并贯通 2D/3D、Wendland/Cubic 参数。 |
| `KerUpdatePorePressure`：1180、1185；Verlet wrapper：1194、1197、1199；Symplectic wrapper：1203、1206、1208 | 更新前把旧 high/low 读入局部值，支持 Verlet 原地历史更新；边界/非流体成对复制，土粒子调用共享补偿更新。 |
| 独立 `KerPorePressureMdbcCorrection`：1219、1301；分派：1308、1312、1320、1323、1328 | 保留原 mDBC 压力外推，实际覆写点清除旧低位。 |
| `KerShepardRegularizePorePressure`：1340、1346、1356、1380、1385；分派：1391、1393、1395、1403、1406、1411 | 自项与邻居项读取完整 high/low 超孔压；原权重不变，输出重新拆分；排水双零，无支撑保留预拷贝 scratch。 |
| 合并 `KerInteractionMdbcCorrection_Fast`：2354、2538；`_Dbl`：2684、2866 | 两套既有 mDBC 实现均在实际孔压赋值点清 low。 |
| 合并 mDBC 分派：3014、3026、3031、3041、3045、3049、3053、3068、3073、3078 | 保留原 fast/double、维数、核函数及滑移分支，仅传递低位数组。 |
| `KerPeriodicDuplicateVerlet`：4641、4660、4664；wrapper：4676、4681 | current 与 M1 低位按相同粒子索引复制。 |
| `KerPeriodicDuplicateSymplectic`：4697、4714、4723；wrapper：4736、4741 | current 与有效 Pre 低位按相同周期映射复制。 |

## 共享依赖、未修改项与验收边界

共享 `src/source/FunPorePressure.h` 的 `Split`（14 行）和 `Update`（18 行）由主线程原样保留；`JPartsLoad4` 的可选低位加载与格式检查由 CPU/共享加载器补丁负责，不包含 u-pl 状态或 metadata。

`JSphGpuSimple_ker.cu` 没有相对上述 Git 基线的实质差异，本轮保持 HEAD，不改 GPU 力学、孔压率、核函数、本构、动态 Darcy、变 n/k 或 TPI。GPU 专用这五文件中无 `HydroMechUpl`、`PoreDynamicDarcy`、`UplCk`、TPI 配置/分支。

独立验收入口执行时位于 `verification_work/`：`gpu_pressure_accumulation_harness.cu`、`build_gpu_harness.ps1`、`run_gpu_precision.ps1`；完成后方法已收入 `rollback_verification_methods.zip`，临时目录已清理。harness 复用已有真实 CUDA 更新、Shepard 与自由面检查；构建脚本只从权威 `VS/DualSPHysics5Re.vcxproj` 选取有效编译项，对应每配置 107 个对象，排除 main 及废弃 u-pl 对象，记录源文件/对象/可执行文件哈希。

既有覆盖是 218 个真实 GPU 更新案例与 22 个附加检查，包括有效 Verlet 历史、Pre/Corr 同源、内存中的 high/low/history/phase 恢复、二维/三维两类核函数 Shepard、排水双零。它不证明 GPU 完整 BI4 热重启，也不单独覆盖 GPU 扩容/排序/周期低位、mDBC Fast/Dbl 或条带外推所有分支；这些不能用 CPU 专项检查冒充。完整耦合收敛及 long-time 精度不在此算子验收结论内。

本轮在生产 GPU Debug/Release 权威工程分别完整 `Rebuild` 成功后，已重新链接并运行同一真实 CUDA harness（NVIDIA GeForce RTX 3050）：两配置均为 **218 项积分 + 22 项附加检查通过，失败 0**。结果分别为 [Debug](gpu_precision_Debug_r1.json) 和 [Release](gpu_precision_Release_r1.json)，两份结果 JSON 逐字节相同，SHA256 均为 `9661AD658CE359063198E97711B9FEA645CCDEC3133DEDBBD7E095F5E6CDF1E8`。构建清单的 `inputs_unchanged` 和运行清单的 `executable_unchanged` 均为 true。

构建与执行日志、命令、源文件/对象/可执行文件哈希保留在本目录的 `gpu_pressure_accumulation_{Debug,Release}_r1.build.json`、对应 `.compile.log`/`.link.log` 和 `gpu_precision_{Debug,Release}_r1.run.json`/`.run.log`。Debug 链接保留既有第三方 PDB 缺失及运行库冲突警告，未出现编译/链接错误；Release 的第三方 `/GL` 自动重启 `/LTCG` 提示不影响完成。这里的运行耗时只记录复现过程，不作为 GPU 算法效率或 Debug/Release 性能对比结论。
