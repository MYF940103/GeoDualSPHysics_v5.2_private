# 孔压 double 状态：阶段 1 验收记录

日期：2026-09-09。状态：阶段 1 代码已实现；严格数值验收尚未完全关闭（q0 的两项孔压审查线超限），不进入下一阶段。

## 这一步验收什么

基线是当前保留的 float 高位＋余量补丁。新代码只换成单个 double 权威状态，
并贯通 CPU/GPU 存储、历史、排序、周期、输出和旧格式加载。
空间算子仍投影为 float、rate 仍为 float。
不把阶段 1 当作孔压方程全部双精度化，不改变 u-pw 物理，不开发 u-pl。

原版本/源码 SHA256 与本阶段源码、执行程序和编译日志见
[pore_double_stage1_manifest.json](pore_double_stage1_manifest.json)；
每个修改位置及用途见 [pore_double_stage1_changes.md](pore_double_stage1_changes.md)。

## 已完成的检查

| 项目 | 结果 | 证据（相对 tests） |
|---|---|---|
| CPU DebugCPU / ReleaseCPU | 均编译成功，无错误 | logs/pore_double_stage1/after_cpu_debug.log、after_cpu_release.log |
| GPU Debug / Release | 修正内核查询 function-pointer type 后均成功 | logs/pore_double_stage1/after_gpu_debug_r2.log、after_gpu_release.log |
| CPU 实际生产对象积分测试 | DebugCPU / ReleaseCPU 各 218 积分样本＋9 项结构检查通过 | cpu_state_DebugCPU_r3.json、cpu_state_ReleaseCPU_r3.json |
| GPU 实际生产核测试 | Debug / Release 各 218 积分样本＋18 项结构检查通过 | gpu_state_Debug_r3.json、gpu_state_Release_r1.json |
| 实际 BI4 loader | 73/73，通过三种格式、分片、ID排序、边界删除、坏数据拒绝 | loader_debug.json |
| GPU Compute Sanitizer | memory-smoke：56 个四步样本＋全部 18 项映射/尾部保护检查；0 errors、0 bytes leaked | gpu_state_Debug_r3.memcheck.log |
| 新 double PART 重启初始化 | CPU/GPU 各 1040 粒子的 PorePress、PorePress0 逐位差异均为 0 | q0_restart_current_cpu_part0001.native_verify.json、q0_restart_current_gpu_part0001.native.json |
| 安装的 PartVTK | 旧三种压力字段输出 float；新 PorePress/PorePress0/ExcessPorePress 输出 double，正常转换 | 各 case .vtk.log 和 regression_comparison.json 字段类型 |

除特别给定路径外，上表 JSON/日志位于 `tests/logs/pore_double_stage1/`。
CPU/GPU 单元测试链接实际求解器对象，不是另写一份孔压公式假装测试生产代码。
来源 `.build.json` 记录对象、源码和执行程序校验值。

代表性微小增量试验：初始 20000 Pa，rate=10000 Pa/s，dt=62.5 ns，8000 步，
解析终值 20005 Pa。新 double 状态为 20005.000000004657 Pa，误差 4.6566e-9 Pa；
CPU/GPU、Debug/Release 在该样本一致。
旧“不带补偿的逐步 float 写回”在 Symplectic 样本停在 20000 Pa；
此处旧 float 仅为舍入问题演示，不是本阶段的高低位补丁基线。
GPU 全套样本最大预测/完整步解析误差约 5.3551e-9 Pa。

重启这里只验证保存/恢复的孔压状态精确，不宣称力学状态及全部积分历史的续算等价。
测试初稿没保存 mDBC 法向额外文件，重启被拒绝；已新增独立 0.02 s 小算例，
使用原生额外数据保存选项，再从 0.01 s 的 PART 验证。失败日志保留，未改生产行为。

## 短程回归口径

每个后端与同后端的补丁基线比，不以 CPU/GPU 互相作为真值。
输入哈希、步数、输出实际时刻、粒子 ID 要一致；
全部粒子均应保留、无 DtMin 强制调整、无非有限值。

- 外载 1D 固结：k=1e-4、dt=1e-5 s、0.2 s，20000 步，21 帧。
  此次新旧配对均使用 NoSlip mDBC，与原正式算例的 Vel0 不同；只作同条件短程迁移检查，不能替代正式 2Tv 验收。
- 自重旧格式 PART 重启：k=1e-3、0.5 ms；
  dt=250/125/62.5 ns，分别 2000/4000/8000 步，11 帧。
- Shepard：自重 dt=250 ns，每 40 步一次。
- HydroMech 关闭：自重 dt=250 ns，用于检查干路径；要求同后端数值逐值一致。
- 基线权威压力为 double(high)+double(low)，从原始 BI4 重构；
  新权威压力直接读取 double。旧 VTK high 与新 double 的可见输出差另列，不混作权威状态差。
- 全帧土粒子权威压力 RMS ≤ 0.01 Pa、最大绝对差 ≤ 0.1 Pa；
  位置最大差 ≤ 1e-6 m、速度最大差 ≤ 1e-5 m/s、应力最大差 ≤ 1 Pa。
  这些是短程迁移审查线，不是理论准确度保证；已在最终比较前指定，越界需先定位。
- 同时报告参考压力、自由面分类差异及 dt 减半的自洽性；不能将两个有限步长的差直接称为理论误差。

## 短程结果与未关闭项

24 次求解（12 对同后端基线/新代码）均正常完成，全部无粒子排除、无 DtMin 调整。
12 对中 10 对通过上述审查线；两对 q0 的压力差超出本次预设严格审查线。

| q0 同后端迁移差 | 全帧土粒子压力 RMS (Pa) | 最大绝对压力差 (Pa) | 结果 |
|---|---:|---:|---|
| CPU | 0.024589414 | 0.125927256 | 未通过 0.01 / 0.1 Pa 审查线 |
| GPU | 0.033016817 | 0.114858100 | 未通过 0.01 / 0.1 Pa 审查线 |

最大压力差约为 10 kPa 外载的 **0.0013%**。量级很小，但不能因此事后放宽审查线或称为零差异。
这些是与保留补丁的差异，**不是新程序相对真实解的误差**。
q0 位置最大可见差 5.96e-8 m，速度最大差 1.44e-6 m/s，应力最大差小于 0.295 Pa，
都在本阶段相应线内。参考压力逐位差异、自由表面分类差异均为 0。
压力比较读原生 BI4；力学字段通过同 ID 的 VTK 对齐，其中位置为 float 输出，
所以这不是 double 位置轨迹的逐位等价验证。

其余结果：

- 自重三档 dt 与 Shepard 的 8 个有水土耦合对照全部通过，
  最大压力差均小于 0.001 Pa。
- CPU/GPU 各一个 HydroMech 关闭对照：导出的全部共同字段逐值相同。
- 最细两档 dt=125/62.5 ns 的终点压力自洽性：
  CPU 补丁 0.000756795 Pa，新代码 0.000759774 Pa；
  GPU 补丁 0.000765983 Pa，新代码 0.000762887 Pa。
  小步长自洽性没有数量级退化，也不能据此声称整体理论精度提升。
- 安装的 PartVTK 三种孔压输出确认为旧 float / 新 double；无需更换后处理执行程序。

汇总来源：`tests/logs/pore_double_stage1/regression_comparison.json`；
逐时刻数据：`regression_history.csv`。
原始全帧比较标记 `passed=false`，没有掩盖未通过结果。

### q0 补充定位

CPU 按相同基线执行程序、同 XML、同命令再跑一次 0.2 s：
21 帧 × 1040 粒子的重构压力、高位、余量、参考压力均为 **0 bit mismatch**，
时间及步数也相同。证据为 `q0_baseline_cpu_repeat.json`。
因此这次 CPU 差异不能解释成基线自身重复运行的随机波动。

源码再审未发现排水/积分时序漏改：
q0 为 TopVertical、Shepard=0、CLI 使用 NoSlip mDBC；Yao 专用外推在此路径早退，
集成 mDBC 输入投影和规定边界舍入保留。
但旧更新为 `high + (low + dt * rate)`，新更新为 `double_state + dt * rate`；
低位舍入和加法结合顺序并不逐位等价。
此外在 float 半 ULP 处，重构 double 后再转 float 未必返回旧的存储 high。
这说明“仍给算子 float 输入”不能保证逐位复现旧 high/low 轨迹。

上述表示机制有精确二进制例子支持，但**尚未通过隔离试验证明它就是 q0 的全部差异来源**。
本轮未将兼容性模拟 helper、nextafter 修正或新开关加入正式代码。
详见 `pore_double_stage1_q0_audit.md`。

### 对比图

按 visualize-data 规范，分别画平均压力与逐粒子差值；两后端使用同一尺度，
没有只画重合的均值曲线掩盖小差异。已打开并检查 PNG，修正脚注重叠。
图中的 pooled RMS 0.01 Pa 线是全帧审查值参考，不代表每帧独立制定的新门槛。

- [q0：压力历史与差值](../../figures/pore_double_stage1_q0_history.png)
- [自重最细 dt：压力历史与差值](../../figures/pore_double_stage1_selfweight_history.png)
- 同名 PDF 为矢量导出；绘图脚本在 `tests/support/pore_double_stage1/plot_regression.py`。

当前 `bin/windows` 下四个目标执行程序是阶段 1 的新 double 状态构建，
但**尚未作为严格验收全部通过的最终版本**；旧补丁 Release 保留于
`tests/outputs/pore_double_baseline/`，历史完整固结结果未覆盖。

## 限制与下一步边界

- 本阶段没有再跑完整 2Tv，也不能推断长期平台已解决。
- 不用此次 walltime 判断性能：编译和多个测试发生并行，硬件竞争明显。
  效率应在固定硬件、线程数、串行成对重复运行下单独验收。
- 新程序兼容旧 PART；旧执行程序读新 double PART 的反向兼容未保证。
- 原 Kplastic 重置、密度/部分积分历史重建等重启语义不变。
- Debug 构建保留 D9035、LNK4099；GPU Debug 另有 LNK4098 默认库冲突警告。
  本次没有修改编译/链接配置来掩盖警告。
- 继续下一阶段前先确认本阶段结果。下一阶段若获确认，再单独升级 rate/空间算子，
  移除过渡 float 投影，并重做步长、解析固结与受控性能对比。

所有临时配置/程序/输出归入本算例 tests 分类；正式对比图置于根目录 figures，
未覆盖已有完整固结结果，未修改根目录正式 XML/BAT。
