# 孔压累计精度修复：验收结论

已完成当前 CPU/GPU 孔压单精度累计误差修复及最小验收。新增模型 C/D/E、总开关改名和 TPI **尚未实施**，不能将本报告视为完整 u-pl 验收。

本报告、[逐位置修改清单](01_修改位置.md)和 `02`—`10` 编号的 9 张中文名对比图均直接位于 `examples/Hydromechanic coupling/00_upl_precision/` 第一层。可直接查看[累计误差图](02_累计误差对比.png)、[时间步一致性图](04_时间步一致性对比.png)和[计算耗时图](07_计算耗时对比.png)；原始图形与数据路径仍在下文保留。

## 已通过

| 验收 | 结果 |
|---|---|
| CPU Debug、Release | 各 218 个真实积分函数案例 + 27 个加载/边界/状态检查通过；两个 r3 JSON 相同。 |
| GPU Debug、Release | 各 218 个真实更新核案例 + 22 个边界/Shepard 检查通过；CUDA 同步无错误。 |
| 固定孔压率解析检验 | 原应增加 5 Pa 却全部丢失的案例，修复后 high+low 最大终点误差约 `7.45e-8 Pa`；本组 high 正确为 20005 Pa。 |
| 状态一致性 | Pre/Corr 从同一整步历史更新；Verlet 原地更新、周期复制、normal-filter、旧/新 PART 低位加载及畸形 PART 拒绝检查通过。 |
| 耦合和分支算例 | 31 次运行、341 帧，逐字段有限值、唯一 ID、步数、零粒子退出、零 DtMin 调整检查通过。覆盖 CPU 动态 on/off、GPU off、Pair/Density、Shepard0/1/40 和 dry。 |
| dry 回归 | CPU 和 GPU 分别与修改前对比，11 帧已有输出字段逐位一致。 |
| 最终 CPU 二进制复跑 | 额外复跑与先前精度修复结果 11 帧逐位一致；新增加载校验没有改变合法输入的计算结果。 |
| 构建 | CPU/GPU Debug/Release 四套最终构建成功；Release 最终增量构建零警告/错误。Debug 有既有 Gm 弃用警告；前次 GPU 完整链接还出现第三方 PDB/CRT 链接警告，没有在本次更改第三方构建配置。 |

权威证据：`acceptance_manifest.json`；CPU 使用 `*_harness_r3.json`，GPU 使用 `*_final2.json`。初始 loader 验收 r1 曾发现 BI4 惰性数组 count 检查错误，已修复并在 r2/r3 验证；失败记录保留，不覆盖。

## 时间步自一致性改善，但不声称完整二阶

同一终点 0.5 ms、1000 个土粒子，以下为相邻步长的孔压 **RMS 差值（Pa）**，不是解析误差：

| 路径 | 250/125 ns，修复前 → 后 | 125/62.5 ns，修复前 → 后 |
|---|---:|---:|
| CPU 动态关闭 | 0.149749 → 0.000608 | 0.242279 → 0.000886 |
| CPU 动态开启 | 0.143139 → 0.000897 | 0.282804 → 0.000831 |
| GPU 动态关闭 | 0.151234 → 0.000600 | 0.242204 → 0.000865 |

CPU 动态关闭的细两档差值约缩小 274 倍。但相邻步长差值未普遍按二阶规律下降，且输出仍是 float high；现有力、压力率及其他状态量仍有单精度计算。因此本轮结论仅为**已定位的孔压累计舍入问题显著解决**，不是全求解器时间精度已全部验证，更不是 retrogressive landslide 长时失稳过程已完成验证。

对应图：

- `figures/frozen_pressure_accumulation.png`：旧 float 累计与真实 CPU 高低位状态对解析解的误差。
- `figures/cpu_gpu_dynamic_consistency.png`：CPU/GPU、动态 on/off 的时间步差值。
- `figures/coupled_timestep_consistency.png`：线性与对数尺度展示同一差值。
- `figures/coupled_pressure_history.png`：中心附近土粒子 ID 490 的孔压过程及独立差值面板。
- `figures/coupled_spatial_difference.png`：相同 ID、初始位置映射的终点孔压差，dt=62.5 ns，色标关于零对称。

以上图和性能图均经实际图像检查；已修复空间横坐标拥挤和内存图最大数据点贴边问题。SVG 与生成脚本一同保留。

## 精度修复的性能代价

独立批次 `perf/release_idle_r1/benchmark.json`：48 次运行，其中 12 次预热、36 次测量（6 组 × 3 对）。固定同一 1040 粒子算例、2000 步，动态关闭，无粒子输出或转换。表内为每对 after/before 比值的中位变化，不是两个独立中位数之比：

| 后端 | Shepard 关闭 | Shepard 每 40 步 |
|---|---:|---:|
| CPU 1 线程 | +0.82% | −0.35% |
| CPU 4 线程 | −1.93% | +0.11% |
| GPU | −0.15% | +0.43% |

在该小算例中未观察到明显额外耗时，不能用 3 对样本的负值宣称稳定加速，也不能外推大模型。程序统计的 CPU 数组分配增加 35,604 bytes；GPU 版本主机分配增加 23,736 bytes、device 数组分配增加 47,472 bytes。进程峰值工作集与 device 数组分配分开统计，不混称显存峰值。

最终性能图在 `perf/release_idle_r1/figures_v2/`：`solver_wall_paired.png`、`simulation_runtime_paired.png`、`host_memory_paired.png`、`solver_memory_paired.png`。`chart_data.json` 记录原始报告和图片哈希；第一次导出的 `figures/` 保留，最终用 v2。

性能批次结束后，只给 `run_cases.py` 的历史模块导入增加了禁写字节码缓存设置，不改 XML、命令、算式或计时逻辑。批次记录的是执行当时 helper 哈希；不回写该原始证据。后续重跑会记录新 helper 哈希。一个已产生的测试缓存留在历史目录，不影响原始结果；缓存清理被工具策略拒绝，未尝试绕过。

## 目录、源代码位置和后续基线

- 每一个生产修改位置、函数名、功能和目的见 [01_修改位置.md](01_修改位置.md)，共 14 个生产源码/工程文件。
- 三个历史验证目录已从仓库根迁入 `examples/Hydromechanic coupling/validation/`；纯移动时 2339/2339 文件 SHA256 相同，路径适配只改 12 个脚本/README，151 份历史 JSON 不变。未删除历史仿真结果。
- 本轮全部新算例、日志、脚本、对比图在本目录。大型二进制、对象、原始粒子输出受局部 `.gitignore` 排除，但**本地仍保留**；本轮未暂存、提交或推送 Git。
- `precision_baseline/` 保存修复后四个可执行文件、DLL、源文件和工程文件快照（273 文件），逐文件与当前版本一致的哈希在 `acceptance_manifest.json`。这不是包含全部 lib 的独立发行包；用于后续关闭 u-pl 时的回归基线。
- 新旧 PART 保存的是当前压力 high/low；完整 Verlet 冷重启、塑性历史/密度重置等原有语义没有被悄悄改写。

## 下一阶段需要明确的 TPI 假设

Lian §3.4 式(29)→(30)先令 `n/Kw→0`，然后才给出 TPI 压力外推更新。原版 TPI 应视为独立的不可压缩水模式，默认关闭；不能称为现有有限 Kw PR 的等价加速器。总开关建议 `HydroMechUpl`；关闭时新增 n/k、动态通量、TPI 历史和新时间步机制均不得参与。TPI 的精度、稳定性、效率应另行报告，并区分物理假设差异与数值误差。

变 n/k 采用何种物理体积/固体质量闭合、Lian 指数渗透率律的 Ck，以及原 TPI 不可压缩假设，应在 C/D/E 实现前明确。验证算例可使用论文参数，但不得默认为当前敏感黏土的标定参数或修改其原本构。
