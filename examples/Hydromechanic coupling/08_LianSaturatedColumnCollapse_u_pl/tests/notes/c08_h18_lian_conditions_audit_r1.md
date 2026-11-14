# C08 H1.8：Lian 2023 算例条件与当前基线核对

2026-11-15。独立只读审计；仅新增本文和同名 `tests/logs/*.check.json` 状态记录。没有修改源码、XML/BAT、PRE、旧审计或结果，没有构建、求解、native/VTK、Git、SHA 扫描或重新计算物理轨迹。本文不准入新算例、其他 psi、半步或正式长算，也不把参数名称相同当作离散算子相同。

## 1. 原文与证据定位

主要依据为 `src/papers/u-pw/Lian 2023 u-pl.md` 和同名 `src/papers/PDF/Lian 2023 u-pl.pdf`，论文 *Computer Methods in Applied Mechanics and Engineering* 408 (2023), 115967。以下“页”均为论文打印页；MD 行号按此次实际文件。已有原页渲染 `tests/outputs/upl_c08_as_paper_r1/lian2023_p19.png` 本次再次目检，确认 Fig.13 和 Table1。未重新渲染或改图。

边界引用链另直接阅读本地 Bui2008 MD（`src/papers/elastoplastic basic/Num Anal Meth Geomechanics - 2008 - Bui - Lagrangian meshfree particles method  SPH  for large deformation and failure.md`），以及 Bui2013 MD；已有 Bui 原页审计 `notes/upl_c08_bui2008_as_audit_r1.md`、`notes/upl_c08_bui_as_audit_r1.md` 保留并作为补充。与冻结代码的对应沿用 `notes/c08_h18_boundary_AV_audit_r1.md`、`notes/c08_lian_boundary_consistency_audit_r1.md`，本轮未重新证明其编译链或扫描历史程序/原始 BI4。

## 2. 底面 NoSlip 有 C08 自身的引用依据

Lian §4.4 打印18页，MD838–850：本算例有5000土粒、初始粒距0.04m，左右墙为自由滑移，底面为 solid boundary，并引用 [11]。该 [11] 的书目在 MD1227–1229，对应 Bui2008，DOI `10.1002/nag.688`。

Bui2008 §4.4 打印1555页，MD1047–1056 明确区分：boundary particles 实施 solid-wall no-slip，ghost particles 实施对称/自由滑移。其 MD1049–1050 的短原文为“boundary particles enforce the no-slip condition at solid boundaries”。因此，当前 C08 底面 NoSlip 不是从 C05 条形荷载算例自动移植来的；C08 自己的描述及明确引用链支持这种滑移区分。C05 的打印18页以前相关 MD781–782 也写底面水平和竖向固定，但本结论不依赖那一段。

原 Bui 边界并非一个独立库仑底摩擦参数：打印1554页 Eq72–74（MD998–1013）外推边界虚速度，系数由墙距比并以上限1.5–2限制；打印1554–1555页 Eq75（MD1014–1046）说明逐邻对的墙应力赋值。没有在 Lian §4.4/Table1 找到单独的底摩擦系数，亦没有发现作者在该例选择另一组有限摩擦系数的证据。不能据经验把 solid bottom 改释为 FreeSlip，也不能把 NoSlip 直接等同于某个有限库仑摩擦角。

当前已完成原 AS03 基线 `configs/c08_h18_as03_n255_r1_Def.xml:148–152` 是右墙 MK2 于重力预载后撤除、左 MK0 FreeSlip、底 MK1 NoSlip，keep_bed_overlap=false。底最后绘制，浅角点从源初始即归底角色；这与旧 keep5 源不可互换。

但是，**滑移标签一致不等于机械边界离散相同**。Bui 的 ghost/virtual 粒子、逐邻对墙应力及墙距虚速度，与当前动态 mDBC 拟合、分开的导数/黏性速度及释放期固定平面 NoPen 并非同一算子。现固定平面政策仍为 `FixedPlaneStageProjectionReleaseOnly`、`ReactionClosed=false`；后置投影未闭合进同阶段 Darcy 的限制并未因 NoSlip 标签而消失。当前近床近对和早停不能据本审计归因于错误滑移标签，也不能认定已有边界完全复现文献。

## 3. 几何、重力初态与撤墙

Lian §4.4 打印18–19页，MD842–850、885–889：初始充分饱和、上表面给定水位；先施重力得到原位总/有效应力，再突然移除右墙。Fig13 原页确认长4m、高2m，左/底不透水，右墙移除；初始孔压约0–20kPa、竖向总应力约0–40kPa、有效应力约0–20kPa。色条尺度不是逐粒子精确参考解，不能由其反推出唯一水平 K0、预载时长或误差容差。

当前基线定义的4m×2m、dp=.04m、初始顶面水位 z=2、重力预载后撤右墙与上述方向一致。床长12m、4层墙（Def20–23）属于本实现的数值设置，文献 Fig13 未给出相同数值；床长和纸图显示范围不应混称成已核相等。

Lian 未在 §4.4 给出10s预载时长、阻尼日程、确切静水平衡容差或存储 P0 定义。当前源审查 `notes/c08_h18_wend_source_decision_r1.md` 已记录：源末实际时刻9.999999999706008s、全部5000土粒保存、末速度最大5.80691e-6m/s、RMS4.15116e-6m/s；最后约.5s同ID孔压变化RMS52.46Pa、总应力变化RMS37.60Pa，kappa全程0。该结果允许用作 psi0 参数筛选的准静止基线，不能称完全静水平衡或论文初态逐点相同。

源/接收状态不得为贴初态云图而重置。原生 p 是绝对表压，P0 是固定初始材料参考；p-P0 不自动等同于论文所谓塑性体变诱发超孔压。接收首帧发生在真实 PRE+1 update 后，其 sigma/J 已更新，不能拿它与 PRE 图的差异伪称更新前继承失败。原始 loader/P0/历史证据沿用既有资格；本审计没有重新解码或创建接收初帧。

## 4. 核函数、H/dp 与人工稳定参数

Lian §3.1 打印5页，MD280–292、Eq21 明确采用 Cubic，h=1.2dx；§4.4 仍为5000粒子/dx=.04m。当前 AS03 使用 Wendland Kernel2、H/dp=1.8、H=.072m、支持2H（Def13、165）。粒距和土粒数量一致，核及邻域权重/梯度明确不同；不能称 h-only 比较或完整同论文离散。当前改核依据是旧 Cubic 源失败与 Wendland 源稳定的实际证据，不是论文原选项。

Lian Eq26 讨论（打印6页，MD359–363）沿用 [11]/[18] 的 AV/AS 形式及推荐参数，并沿用 [18] 的声速规则。它未在 Table1 指定 AV=.5。Table1 打印19页的 alpha=.5，结合打印8页 Eq38–39、MD463–474，属于 TPI 中间压力历史外推；与人工黏性 alpha、AS epsilon、剪胀衰减 sf 不是同一参数。

Bui2008 打印1551页 Eq60–62、MD790–839：AV 有线性和二次项，多数计算系数约.1/.1；第二项对该低速试验影响较小。Bui2013 打印35页 Eq17、MD269–278 改变土体声速规则。当前原 AS03 采用 AV=.1，但实际只有线性项，实际 c0 约119.574852m/s且声速定义不同；因此不能只凭相同 .1 宣称同强度，也不能把 Table1 .5 当作应将 AV 提高五倍的依据。

Bui2008 打印1552–1553页 Eq63–71（MD874–948）给出 AS 主应力及核比形式，打印1563页给 Cubic/h1.2 的试验推荐 epsilon=.5、n=2.55；.3减轻而未完全消除该干土试验的破裂，.5/.7消除，同时警告 n=4 可能斥力过强。Lian 的引用链支持以该组参数为文献对照，但不能改述为 Lian 在 Table1 逐字给出 AS=.5/2.55。

当前基线 AS=.3/n2.55 是已实测比较后保留的数值选项；在 Wendland/H1.8、变J/变k及总应力AS适配下，既非严格原论文参数，也非已证实物理最优。AS 强度、核比、原 AV 和孔压加速度反馈须一起审阅。原 AS05 更规整但运动受抑制的失败方向仍保留，不能只按末态粒子排列或降低压力RMS选修复。

## 5. 三组材料与 PRE 独立性

Lian 打印19页 Table1（MD860–879）给出：

| 参数 | psi0 | psi+2.5 | psi-5 |
|---|---:|---:|---:|
| E [MPa]、nu | 20、.33 | 20、.33 | 20、.33 |
| 固体/水密度 [kg/m3] | 2650/1000 | 2650/1000 | 2650/1000 |
| n、Kw [GPa] | .35、1 | .35、1 | .35、1 |
| 初始 k [m/s]、Ck | .0002、2 | .0002、2 | .0002、2 |
| 峰/残余 phi [deg] | 25/25 | 25/25 | 25/25 |
| cp/cr [kPa] | 5/1 | 5/1 | 7.5/1 |
| cohesion softening eta | 5 | 5 | 5 |
| 初始 psi [deg]、sf | 0、N/A | 2.5、.2 | -5、.2 |
| TPI alpha | .5 | .5 | .5 |

打印5页 Eq17–19（MD258–273）为摩擦角/黏聚力指数软化与 psi=psi0*exp(-sf*eqPlasticStrain)。打印3页 Eq4（MD162–168）为 k=ksat*exp((e-e0)/Ck)。当前参数名称对应，混合参考密度为(1-.35)*2650+.35*1000=2072.5kg/m3。参数与历史变量定义的对应不自动证明有限步返回算法或孔压积分完全相同。

当前已审实际 psi0 AS03 Def115–134 对应表中 psi0 组，源为认证的 Wendland schema2 同材料 PRE。另实际读取根目录 `CaseLianSaturatedColumnCollapse_psi2p5_shared_r5_Def.xml` 和 `CaseLianSaturatedColumnCollapse_psim5_shared_r5_Def.xml`：两组的 phi/cp/cr/softening/psi/sf 数值分别对应表中后两列，**但仍是旧 Kernel1、hdp1.2、dt2.5us、statefile=__GRAVITY_PRELOAD_STATE__**，不是当前 Kernel2/H1.8/schema2 的已可运行正式接收配置。本审计不修改它们或解锁运行。

现 schema2 loader 绑定精确组材料 cp/psi/sf 及完整材料/触发/张拉合同。即使已审 psi0 源 kappa 恰为0，也不能凭这一结果把另两组输入改名后共享源；不同 psi/cp 的重力历史是否仍无塑性、同一应力是否合法及后续历史是否一致仍须实证。Lian 的三组材料表也未证明可跨组共享一份数值 PRE。当前应维持同核/H/dt/几何/材料合同匹配，独立资格清楚后再决定各组 PRE；本次不启动新源或接收。

## 6. 已确认的算法差异与本次结论

Lian 打印19页、MD885–889 在该高渗算例采用 TPI、dt2e-5s。打印7–8页 Eq29–39（MD395–474）去掉水相存储项并使用压力历史外推；打印11页 Eq47（MD584–608）还对塑性负压给出 beta=.04 的对角和历史配套稳定化。当前保持有限 Kw 的显式预测/校正、5us，不含完整 TPI/Eq47。直接裁剪负压或只乘一个压力率系数不能称实现 Eq47。

打印19页 MD881–883 要求墙不透水、自由面采用引用[36]的 free-seepage 与 p_l<=0。当前 completed-only 正压投影的符号方向一致，但 FS 识别、法向通量闭合及积分阶段并未证明与其全文一致。文献打印10页 Eq46、MD562–576 将 Shepard20–40明确限于§4.5低渗大变形示例；当前 C08 释放后 ShepardOFF 不能据此称漏项，而重力预载的40周期过滤是实现选择。全局阻尼仅用于非耗散/弹性情况的范围及.02–.1建议见打印9–10页 Eq43–45、MD523–559；§4.4并未逐项给出预载和释放阻尼日程。

结论：没有发现“底面 NoSlip 是由 C05 误套”的证据，也没有证据支持直接改为 FreeSlip。较明确、可保留为后续因果审查方向的差异是实际近墙机械/Darcy反力一致性、finite-Kw显式积分与TPI/Eq47、FS识别/通量以及核/H。它们尚未被证明是当前团聚或早停的唯一原因。本次不选择新物理方案，不以正常退出、短窗一致或较平滑云图认领论文精度；旧失败、全部负压和空间极值仍保留。

同名 JSON 记录此次阅读对象的当前 stat、引用位置和结论分类；stat 不是历史哈希证明或新物理测试。
