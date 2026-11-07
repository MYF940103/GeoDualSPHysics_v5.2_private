# r4 43帧墙/压力/应力/接触离线审查稿

根首次离线执行在首frame因错误字段`Velrhop`失败，尚未生成derived输出；随后修正4行共7处为实际`Vel`（float32×3），密度另存于`native_Rhop`。第二次离线执行已写7份新CSV，绘图因将`linthresh`错误传给`Axes.set`失败，PNG/check尚未生成。这两次是分析脚本失败，不是solver或reader失败；原日志由根保留。现只将symlog设置拆成`set_yscale('symlog',linthresh=1e-6)`，并允许本次7CSV在内存重新生成UTF-8完整bytes后逐字节相等才复用，差异拒绝、不覆盖；任一PNG/check已有仍拒绝。本次修正版未执行、import或AST检查，不改数值算法/预算。该审查不启动solver/reader/build，不改生产、BI4或旧分析文件，不哈希、不自动续算。

固定输入为`tests/outputs/upl_c08_r4_partial_r1`的typed22、layout、completion、clocks和复制的`CfgInit_NormalsGhost.vtk`，以及`tests/logs/upl_c08_r4_partial_r1.check.json`。只消费passed的43帧原生审查，不能读growing CSV。原12字节header必须如实为6800/22/43，原ID是0..1799及2060..7059；Step/实际clock和原signed诊断门保持。已失败solver不因此变成正常完成或物理pass。

复用已封口`upl_c08_wall_geometry_r1.py`的Cubic float表达式、float半径、V0J、原det1e−3门、实际法向解析器，以及`upl_c08_wall_stress_decompose_r1.py`的6分量fit/anchor分解与既有affine算术预算。旧文件不修改、不monkeypatch；新loader独立支持43帧。double求和按native ID顺序，不能称为GPU packedPosCell、cell-order、FMA或失败substage精确重放。

全43帧各5000土体记录minz/minx、z<0/x<0计数、绝对孔压均值/RMS/范围、有效与总应力Frobenius RMS、速度RMS/最大值、κ与J范围；总应力为原生double有效应力减绝对孔压I。原生ij顺序为xy,yz,xz。固定7010逐帧原x/y/z、速度、p/κ/J及6σ并入history。独立contacts表记录每个z<0/x<0的soil-time、每ID首个保存穿底标志、前一保存帧z/v/p/κ/J，以及最近真实bed粒子的ID/B坐标、法平面和相对dx/dz/距离。它定位的是首个保存穿底区间，不是假定连续过程精确首穿时刻；不将7010代替其他先穿底ID。

墙点823及与它相同Bz/法向/Mk的左右最近各2个真实底墙点，共5个，每帧检查：B的double/cast-rr²/cast-components三种邻域数量及union激活代理、GP节点数、原矩阵det/条件数、有效正W点集的无权仿射秩及两个几何奇异值。最近全体实际土粒距离与真正访问到的nearest source分开保存；GP外最近点不能被拿来凭空救retry。

保留规则严格只在原primary几何门失败且有已访问nearest时尝试一次nearest-source中心；返回原GP/B不变，不放宽det，不逆病态无资格矩阵，不添加镜像墙或新法向。J延拓按原helper回GP。每相保存实际support土粒ID/位置/J/V/p/6σ/速度/κ和原wall p/J/σ/速度；后者是native保存值，不是derivative-image速度或新增反力观测。

额外反事实A只用于B激活代理为真且原nearest retry仍不合格的样本。在固定的“原GP同R初始sources”集合内按(distanceToOriginalGP,ID)依次用实际real-source为中心，每次仍同R和原det1e−3门；原nearest结果复用，不重复拟合。首个几何/J饱和/6σ有限候选即停止，因此shift最小；不把新中心的邻居加入候选集、不无限移步、不调半径/阈值。centres表保留每次尝试及最小shift，walls表给概要。这是几何/J/应力可恢复性检查，尚不等价完整pressure-head/velocity finite guards或实际动力学准入，不写回任何生产状态。

每个合法fit保留6σ的MLS截距、回B值、nearest residual、x/z gradient-distance及anchor总和，并记录既有制造affine误差/预算。这样能区分非线性外推放大与几何欠定。点集仿射秩只是binary64描述，不是新的生产门；只有实际节点及秩证据才讨论“一层/共线前缘”，不预设empty或穿底原因。

根已报告未保存失败点为stage0/native823，B=(4.38,−.06)、normal=(0,+.12)，step-start约10.4378925；43帧末态约10.43。新脚本将它作为外部诊断来源标明，不能将末帧拟合代理当成该瞬时的真实输入/first cause。

输出全在`tests/figures/upl_c08_r4_wall_review_r1*`：history/contacts/walls/support/stress/centres/local七份CSV，history/local两PNG及check JSON。局部图使用末前第7/4/1个真实保存帧（43帧时即parts36/39/42），范围固定为823左右.3m、z[−.15,.3]；显示实际土体、同排B/GP、primary support和一次retry中心。缺少的unsaved状态不插值。所有源前后stat，无SHA；已有CSV只允许与重新生成的完整bytes精确相同后复用，PNG/check仍要求不存在。

后续结论必须依据实际执行结果填写，本稿不宣布失败原因、NoPen反力/J-Darcy闭合、论文精度或新的墙重构候选已通过。
