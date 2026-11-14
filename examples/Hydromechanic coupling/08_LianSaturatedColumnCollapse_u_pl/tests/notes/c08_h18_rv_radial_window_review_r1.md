# C08 radial .90s：三轨迹离线物理对比 r1

作者文件 support/c08_h18_rv_radial_window_review_r1.py；未运行、未导入作者脚本、未分析实际新数据，也不含 solver、reader、VTK、build、Git 或通知调用。根全文审阅并确认新91帧 run/native 均真实通过后，另行准入唯一离线命令：python -B support/c08_h18_rv_radial_window_review_r1.py --execution-authorized。存在同tag check/partial派生输出即拒绝，不能覆盖；已完成solver/reader后本分析失败只修新的派生分析，绝不重复物理计算或解码。

## 输入和复用边界

- 新实际 run：logs/c08_h18_rv_radial_window_GPU_r1.run.json；独立原生：同tag.native_r1.check.json。要求实际91帧/2180000、5us、180000新更新、原6805 IDs/5000土及原22 typed布局、原schema2 PRE/keepfalse/retire255，不以退出0或本脚本存在代表通过。
- 两条真实对照由已封存 logs/c08_h18_rv_window_review_r1.check.json 绑定：原 AS.3/n2.55/AV.1 无RV，和 c08_h18_rv_window_GPU_r2 的原vector RV alpha.1。它们都是实际轨迹，不是CPU反事实受力。旧vector gate/form/contraction函数既不导入也不调用。
- 使用 c08_h18_storage_review_r2 的 typed/schema/read22 纯原语；nearest/physical_frame/plot基础块机械复用已通过 c08_h18_rv_window_review_r1.py 的同名纯物理函数，扩为3条轨迹/3行空间图，不携带旧66列或vector数值资格。
- 初始材料层、真实initial/PRE坐标、fixed P0和PRE κ取自已封存 c08_h18_rv_window_review_r1_source_cohorts.csv 的5000行及其已通过review stat绑定。原50层×100列、顶部100与底部100是固定初始材料IDs，绝不按当前最高/最低点重选。无需重新读取PRE的1001帧，source raw frames read=0。全6805 P0从已认证原轨迹首帧继承参考，土P0与封存cohort逐位相符。
- 新实现资格只复用当前径向runner内纯telemetry检查（schema3、87列、182真实stage快照、5制造、8fixture）和真实run/source/build绑定，原112物理对象/2私有对象/114链接、C08_RV_RADIAL_H18=1。该函数只读现有侧车，不调用其prepare/run/通知。MFG committed_*是hypothetical candidate，实际committed=false，不记真实stage提交。

所有必要绑定只用size/mtime，不SHA扫旧对象或BI4、不再reader。新native收据的files逐一核其封存stat；两个旧控制的typed22.bin/layout/clocks必须先按OLD_GATE.consumed中各自唯一原封stat绑定（完全相同的重复entry允许去重），再读取已有typed22，不能把当前rawstat冒充历史seal。公共源、活动GPU依赖、PRE、原图CSV均不写。

## 全91时刻与指标

三case分别遍历全部91真实保存记录，每个时刻全部5000材料ID，不插值。实际time必须逐bit相同，completed/saved和原5us一致，全部6805 native IDs一致；原signed dterror保留其符号，并要求原signed<=1e-14，绝不改成abs或丢弃负诊断。原native安全/ledger/FS/NoPen/源材料门保持，NoPen同stage Darcy反力仍不闭合。

逐帧孔压min/max/mean/RMS、负孔压节点，native float(p-fixedP0)，有效/总应力六分量与Frobenius/trace，速度，J/n/rho/k/κ，固定初始top/bottom沉降、整体运动与前沿/最大高度/尾部.6–.9s材料位移。总应力=σeffective−pI，ij顺序xy,yz,xz。逐帧全5000非自身NN以及严格 r<.7/.5/.3dp 的唯一pair数，无材料排除、压力剪裁/平滑、拟合半径/时刻/荷载或颜色隐藏。

每个新径向时刻分别对原轨迹、旧vector作同时间/同材料的压力、XYZ位移、总应力、J/n/κ RMS/最大差。差值是改算子的描述，不是5Pa半步或CPU/GPU误差，更不是解析/论文真值。native p-P0仅固定初态参考，不称Lian的plastic excess。

全窗每字段保存极值及原ID/位置/时钟；summary显式给真实已保存的最差负孔压和最大正压、NN最差、.5dp pair最多、压力RMS峰值和尾部运动。不推断两次save之间的未保存极值或substage因果。8个固定材料ID4953/4954/6767/6865/6964/7012/6918/6967同时输出全部273组轨迹的p/κ/J/位置/速度等，共2184行，供之后按证据选态。

## 输出与图

仅 tests/figures/c08_h18_rv_radial_window_review_r1_* 新浅标签：history273行、matched182行、extrema全窗表、spatial45000行（3case×P38/P76/P90×5000）、material_tracks2184行、timing3行。所有图所用数值都有对应CSV。

四幅PNG：一幅4×3全历史（含压力/应力/速度/κ/J/n/k/沉降/前沿/NN/pair数），及P38/P76/P90三幅3行×2物理场空间图，三条轨迹同实际时间、同一坐标视域，压力和NN分别有专属colorbar并使用三case原生全范围。无插值/平滑，全部5000土点均绘制，保留负压与极端点。固定边界灰色另绘。空间图是实际轨迹快照，不展示旧CPU shadow力。

observed timing直接取三组Run.csv的TSimul/TTotal与实际Hardware；速率分子仅180000新更新，不使用继承的2.18M全局步或绝对物理时长。轨迹/邻居数不同会改变成本；它不是控制性能基准，不预言加速。

check通过仅 analysis_complete=true、physical_acceptance=false、visual_QA_pending=true；根必须实际查看四图与CSV后做科学取舍。压力脉冲下降不能独自认定成功，需同时看负压极值、团聚尾部、早停/整体运动、κ/J与应力。短窗和机械证书均不自动允许3s、另外ψ、正式计算、额外half或PRE重算。
