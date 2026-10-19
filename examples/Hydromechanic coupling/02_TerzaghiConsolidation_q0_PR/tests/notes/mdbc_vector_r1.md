# 固定平面导数速度的向量推广

2026-10-17。当前是独立开发／验证阶段，不是新的完整固结验收，不代替已暂时接受的一维结果。先完成标量接口重构的半步回归并冻结，再编辑生产源码；不恢复 KEEP 密度诊断。

## 范围和数值变化

仅支持 CPU、静止单平面、统一 SlipMode 的二维／三维弹性情形。开关仍是默认关闭的 `SoilBoundaryDerivativeSPR`，不增加 S/P/R 三个独立选项。S/P/R 分别指应力率、孔压压缩源项和密度率。

令镜像点重构速度为 vg，单位墙法向为 n：

| 模式 | 导数辅助速度 | 含义 |
| --- | --- | --- |
| Vel0 | `-dot(vg,n)*n` | 保持零切向闭合；不等同于完整 NoSlip |
| NoSlip | `-vg` | 静止墙全部分量反射 |
| FreeSlip | `vg-2*dot(vg,n)*n` | 切向保持、法向反射 |

旧水平 Vel0 专门保持原 float 转换、负号及 x/y 位模式，并要求完整短窗逐位一致。其他方向按单位法向计算。现有 NoSlip／FreeSlip 的速度外推是零阶，新候选用一阶 MLS，且密度率同步使用该导数速度，因此是需要验收的离散扩展，不宣称等价于原 NoSlip／FreeSlip。

真实速度、`TangenVelc`、黏性、Darcy、外载及积分时序不改。mDBC 已判无效的墙不能被另一套 MLS 重新激活；其辅助速度回退到原真实墙速度。单平面之外的墙角、曲面、运动墙、NoPen 和混合 mk 滑移模式本阶段不开放；HG 的既有二维限制独立保留。

## 预定生产修改

- `JSphCpu.h/.cpp`：临时 `BoundDerivativeVzc` 改为三分量 `BoundDerivativeVelc`，同步池分配／释放；共享 MLS 一次邻域和矩阵求逆、单分量孔压或三个速度右端项；接入 S/P/R 全分量，保留关闭路径及原黏性差分。
- `JSphCpuSingle.cpp`：只调整 SPR 配置及单平面几何检查，不放宽 HG 或改变 force-stage 调用顺序。
- `doc/xml_format/_FmtXML_ElastoplasticSoil.xml`：同步候选适用范围、三种映射和限制；完成验证后才写入通过范围。

## 制造场和事先限定的检查

输入由 `support/mdbc_plane_prepare.py` 与 `configs/CaseMdbcPlane_Def.xml` 生成。`configs/xCaseMdbcPlane_win64_CPU.bat` 明确仅运行 GenCase，不运行求解器。18 变体的候选输入清单在 `logs/mdbc_plane_r2.prepare.json`：

- 二维水平、竖直、30°倾斜；三维水平、绕 y 轴30°、绕 (1,1,0) 轴30°。
- 每种几何各用 Vel0／NoSlip／FreeSlip。dp=0.01 m、h/dp=1.8、三层墙；二维208原生粒子、三维3328原生粒子。
- 外载、排水、HG、阻尼、shifting、密度扩散及周期全部关闭。测试全向速度重构不代表三维 HG 已支持。
- 常量场只验证重构和反射映射，不声称非零法向常量满足不透水边界；另用与各滑移模式相容的仿射场检验梯度。
- 墙 ROI 与侧边至少相隔一个核支持半径；逐分量重构误差限为 `32*FLT_EPSILON*max(0.125,abs(expected))`。外缘只检查有限值和无效墙回退，不据其宣称一阶一致。
- 单分量孔压另用非零 p0 加仿射超孔压检验；误差限 `32*FLT_EPSILON*max(1,abs(expected))`。
- 同一个生产交互函数分别使用 MLS 辅助速度和解析辅助速度，比较近墙土粒子的 S/P/R：应力率每分量 `20 Pa/s + 2e-5*abs(reference)`；孔压率 `2000 Pa/s + 2e-5*abs(reference)`；密度率 `0.02 kg/(m³·s) + 2e-5*abs(reference)`。这些阈值在运行前确定，不根据结果放宽。
- S/P 还需与解析弹性应力率和 `-Kw/n*div(v)` 比较。R 的未修正核矩误差单独量化，不能要求它无条件解析精确；另通过仅在 fixture 中将解析辅助速度暂写为真实墙速度、关闭辅助指针的同算子对照，检查 R 接线并恢复原状态。
- 记录原生 ID、真实字段隔离、法向、实际结果和输入／构建／输出哈希。无时间推进的制造场不是长期物理验收。

输入准备 r1 在求解器启动前被审阅发现旋转符号错误：GenCase `rotateaxis` 的正角方向与记录所用右手 Rodrigues 矩阵相反，90°变体的实际 X 范围为[-0.095,0.025]，并非预定[-0.025,0.095]。因此 r1 只保留为失败的输入准备记录，不能用于验收。脚本显式向 GenCase 写入负角，法向和记录仍用预定正角；以 r2 新标签重建，并由 fixture 检查实际坐标／法向，不仅检查 XML 解析。

## 回归与后续

CPU Debug／Release 全量 Rebuild；Debug 0.03 s、关闭路径0.1 s、旧水平 Vel0 开启路径0.15 s粗／半步分别与通过的标量版本比较。`support/mdbc_vector_check.py` 复用旧严格检查，仅将参考冻结映射切换到 `mdbc_scalar_base`；物理量、原生ID、HG、drained及缓存摘要均要求一致，不使用旧显示例外。

上述通过后再评估 mDBC 邻域融合。不能以融合为由跳过 corrector 的辅助速度更新；若无法保持等价或无稳定效率收益，保留独立入口，继续 GPU 分阶段交付，不无期限扩大边界诊断。

## 当前实测记录

CPU Debug／Release 全量 Rebuild 均退出0；Debug为53条既有 `/Gm`／第三方PDB警告，Release零警告。18组新的 Release 制造场 `mdbc_vec_rel_r2_*` 均正常退出，原生网格、法向、真实字段隔离及输入／构建／输出哈希检查通过。独立CSV复算见 `logs/mdbc_vector_review_r2.check.json`，两张图见 `figures/mdbc_vector_review_r2_*.png`，图像审阅见同名 `.visual.json`。

- 最大速度分量误差 `5.62006e-8 m/s`，各分量误差／自身预定限额的最大值为0.1179；单分量孔压共享MLS误差 `3.80965e-6 Pa`。
- 真实交互函数的 MLS／解析辅助壁速对照，S/P/R最大绝对差分别为 `1.5 Pa/s`、`384 Pa/s`、`0.00109863 kg/(m³·s)`；均满足事前限额。
- 校正S/P相对解析制造场的最大误差分别为 `1.7125 Pa/s`、`471.841857 Pa/s`，最大限额比分别0.0365和0.04641。
- 原始R算子的解析偏差约 `1.807–5.869 kg/(m³·s)`，保持原核矩离散，不把它隐藏或当作本次接线失败；同生产算子的R接线0 ULP覆盖合计31824个原生粒子。
- 仅测共享孔压标量MLS，不代表 `PoreMdbcInterpolationMode=1` 调度已验收；人工inactive测试仅覆盖辅助值fallback。制造场未作时间推进，不代表任意二维／三维实际算例或HG已验收。
- Debug 0.03 s原安全检查通过；关闭路径0.1 s与冻结标量版全轨迹0 ULP。开启路径0.15 s粗／半步也已完成：实际末时分别为0.15000000000000924／0.15000000000007963 s，15000／30000步，各151帧；两条完整短窗与各自标量参考的物理/native/HG/drained/缓存摘要均0 ULP，未使用显示例外。收据为 `mdbc_vector_015_c.check.json` 与 `mdbc_vector_015_h.check.json`。这不是另一次15 s或2Tv物理验收。

测试入口失败记录：旧 `mdbc_vector_run.ps1` 的固定 `-mdbc` 会覆盖XML的SlipMode，首个NoSlip组 `mdbc_vec_rel_r1_2d_h_s2` 在进入误差检查前被正确拒绝。原脚本按字节保存在该输出目录 `runner_snapshot.ps1`（SHA256 `D0C2176A9862CC0BD8A2542C5787868633941B2B8E7E485757A1778D802FD30C`）；仅将脚本改为按模式使用 `-mdbc/-mdbc_noslip/-mdbc_freeslip`，全部18组使用新r2标签重跑，无生产修复或阈值放宽。r1 pilot不混入r2验收。

第一版图的最大值标签与阈值线重叠，仅调整文字纵向位置后重新生成r2图；原分析脚本存于 `outputs/mdbc_vec_rel_r2_2d_h_s1/review_r1_script.py`，旧图和收据保留。新版检查器的六项纯内存负例另通过 `mdbc_vector_review_selftest_r2.selftest.json`，它不是实际运行完整性或物理验收。

## mDBC 遍历融合审查与冻结

没有直接复用现有mDBC矩阵：原mDBC路径采用float距离、核权及体积乘积，SPR采用double距离/权重和不同有效判据；两者虽然矩阵元素最终可为double，仍不是同一离散累加。直接共用矩阵会改变已验证结果。安全共享至多是cell/粒子枚举，仍需分别执行两套累加和支持判定；corrector仍必须更新导数速度，不能借用predictor缓存。

本轮据此保留独立入口，没有创建融合候选或测得新的融合加速。未来若单独尝试，须保留两套算术、全轨迹0 ULP，并对同一mDBC+SPR区域及整步交替计时；目前CF计时范围不能直接比较。已验收的HG端点缓存优化不受影响，也不重复计为本次收益。

通过版本已冻结为 `outputs/mdbc_vector_base`（470文件及对应snapshot收据）。继续GPU分步移植；任意二维/三维实际物理算例、复杂墙和GPU SPR仍不在本次制造场验收内。
