# C08 fixed-plane 0.6秒封口后离线审查（author-only）

仅新增 `support/upl_c08_plane_window_review_r1.py` 和本说明，未运行/读取活动产物，不改旧记录。脚本不会调用reader/solver/PartVTK或自动开启full/half。根完整审阅，且ON GPU .6窗与唯一native实际封口后才显式运行：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_plane_window_review_r1.py --execution-authorized
```

先要求 `logs/upl_c08_plane_on_GPU_r1.native.json` 与43帧 `upl_c08_r4_partial_r1.check.json` 实际passed且consumed未变，再读取其原输出；同时核新实际run/call退出0、4240000/60帧、无ownership错误和reader实际退出0。新60帧必须22数组/6800IDs/5000soil完整、300000 ledger、408000 P0、108000fixed、300000κ/rho-cache、60非空signed区间、600000plane检查及原clock1e-14/ledger5e-13/signed1e-14全部门，NoPen=FixedPlaneStageProjectionReleaseOnly/Active true/Reaction false。旧43帧只是已保存安全状态，不把其失败runtime改称成功。必要产物对原native manifest的stat绑定检查，不扫描SHA或所有旧源码。

全22 loader按各数组真实type/components/SoA顺序建立struct dtype，尤其Vel严格为float32×3，对全部XYZ转double仅为范数与CSV计算；无省略水平速度、伪造速度或修改数组。新旧逐帧材料ID集合固定，首帧始终真实post-PRE。新旧实际source clock一致，43个共有actual保存时刻/全局Step/material IDs直接配对（<=1e-14原clock预算），不插值、不拟合时间/半径/荷载。

所有输出以 `tests/figures/upl_c08_plane_window_review_r1` 浅前缀命名；已有同前缀文件则拒绝覆盖：

- `_history.png/.csv`：全部5000土粒pressure mean/RMS/min/max、总应力Frobenius RMS（double有效应力−原绝对pI）、XYZ speed RMS/max、κmean/max、Jmin/max、minx/z、原tol外粒子数和理想0平面near-plane几何数；native history真实double PRE的整体材料沉降。曲线与旧43帧描述性同图，不采用5Pa/.005mm half或跨算子等价门。
- `_material7010_7011.csv`：两个固定原native IDs7010/7011的完整XYZ位置/速度、速度模、κ/p/J/n/k/总σzz；history图含其z/vz/κ/p随真实tau历史，不重选点、不把首保存当PRE。
- `_matched43.csv`：43真实同时间/Step的pressure RMS差、每ID XYZ位移最大差、总应力差、κ最大差，均为物理算子改变的描述，不称theory error/half error。
- `_morph_pressure.png/.csv`、`_morph_kappa.png/.csv`：新实际保存状态tau约.1/.2/.3/.43/.5/.6，以及旧实际存在的前四个状态；按相应globalcompleted选择原生帧，图标题/CSV写真实actualtime/tau。旧.5/.6没有数据就留白标明，无插值/平滑/裁色。压力/κ分别用两数据集中实际值共同色标，所有面板共用位置轴，native scatter保留全部5000粒子，未为了匹配paper调参。全部曲线为线性坐标，不调用symlog参数。
- `.check.json`：有限状态统计、必要consumed stat与图CSV清单；passed仅指离线审查产物完成，physical_acceptance=false/automatic_full_admission=false。

几何count以理想C08左x0/底z0与既有planetol=1e-6*dp=4e-8m描述；new plane_gaps.csv须与typed位置重算完全一致。near-plane是位置分组，不能冒称active接触数、反力或冲量。该脚本不新增几何阈值或paper匹配门。

从已封口旧partial check保存的真实诊断行读取old step_start10.43789250051325及step4175157。只报告new保存窗是否越过这个旧force-stage source-clock、之后实际保存帧数；不拿10.43旧末帧重建未保存错误状态，不声称复现或修复所有未来3秒不稳定。新接触算子仍没有被观测的reaction/冲量/耗功与same-stage J/Darcy闭合，压力/位置看起来稳定也不等于完整物理验收。
