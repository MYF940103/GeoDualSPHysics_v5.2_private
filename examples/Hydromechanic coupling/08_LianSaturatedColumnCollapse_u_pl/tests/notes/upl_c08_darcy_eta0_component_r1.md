# Shepard保存态上的Darcy-only Eta0组件（作者稿，未执行）

只新增同stem CPP、_build.py、_run.py及本说明。原生产源码/objects、程序、PRE、Shepard失败输出/72帧native及旧分析均不改。当前仅作者和静态检查，根全文审阅后分别build/run一次；无新solver、GenCase、native解码、VTK、制造多项式或半步链，也不自动准入GPU窗口。

输入是已通过唯一partial原生检查的 `outputs/upl_c08_shepard_partial_r1`，只读取part49(τ约.50)、71(τ约.72)的原typed22记录。保留真实72/6805文件头，6805=1805固定＋5000土，keep5/退休255。绑定原failed run、实际执行XML/seed/PRE、唯一reader调用及原clock/layout；不把原solver退出1改称成功，不重读其原始BI4。真实认证PRE仍由合法Load路径载入一次，不扫描1001态。

完全复用AV组件已合法的InitRunCPU→原r2GPU PRE handoff→一次keep5 release→按ID恢复/分格再回填流程；原bedkeep DebugCPU86非main物理objects加新helper，共87，不重编物理obj。归档headers、MSVC14.36、/Od /MTd /fp:precise /openmp和4个runtime依赖保持相同。private GPU Shepard只改Single host释放策略/只读计量，force本体来源须与CPU closure匹配。保存p包含其真实Shepard历史；CPU本次不运行滤波，metadata仍原样ShepardON，非GPU rate重放或通用restart。

每态恰一次真实 `Interaction_Forces(INTERSTEP_SymCorrector)`，使用原Eta2；它内部已含一次动态Darcy调用，直接取作基线。随后仅 `ComputeDynamicPorePressureRateCpu()` 在RAII Eta2=0作用域调用一次，再在原Eta2作用域调用一次。因此总2次ct、6次Darcy、0updates/材料返回。没有重复baseline调用，没有重新计算机械/AV/AS，P0/J/σ/κ/位置/速度不改。

原Eta来自实例，核等于原float(0.1H)²。EtaScope只包Darcy调用，正常及异常都恢复原值；所有非Darcy工作和独立shadow在原成员Eta下执行，shadow显式接收其目标denominator。动态墙加速度由原Darcy wrapper真实重建；必须与既有完成Ace逐位不变，不能冻结错误墙或借此改墙算法。

两态分别保存force完成后的**全部6805槽**上游字段：p/P0、σdouble、κ、J/θ、Pos/Velρ、C/Ace、FS/FSNormal/PosDiv、Arc/Press、Rσ/AS、实际ID/Code/cell、墙normal/slip/mode、tangent/derivative velocity、NoPenShift和载荷。两次额外Darcy后逐字段memcmp，另核clock/Nstep及速度/加速度/粘性/变k速度统计不变；原soil primary/ledger/角色守卫继续保留。最后全部5000 Rate float必须逐字节等于ct基线，否则失败并保留现有证据。恢复后的rate仍是本次新CPU完成态，不能声称等于原GPU。

selected固定为每态81个输出receiver；每个五项Sum独立枚举全部fluid/fixed支持，不截邻居。沿用原AV/zero_r2的compression、LP、Taylor defect、divAce、变k chain及保留误差预算；候选shadow仅把相同w分母Eta设0。FS-Ace/chain-Ace/chain-Gp分项照旧。没有新物理阈值或将rate差当5Pa误差；有限性/原原生输入门不放宽。

输出3CSV：`receivers.csv`共324行（两态×原/候选×81）；`all_soil.csv`共10000行（真实ID/FS/p/J/κ、两rate及差）；`summary.csv`共6行，分别all_soil、FS23、not_FS23的rate RMS、差值mean/RMS/max及extrema ID。not_FS23只是当前非2/3分类，不据此称完整内部域。滤波参数不变、原AS total/.2/n3、AV、Cubic1.2、Ck2、dampingOFF及完整墙支持均保留。候选改变的是离散Darcy的短距regularisation，并非Eq23理论精度或长期稳定证明。

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_darcy_eta0_component_r1_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_darcy_eta0_component_r1_run.py --execution-authorized
```

新helper为 `outputs/upl_c08_darcy_eta0_component_r1_helper/component.exe`，结果浅目录 `outputs/upl_c08_darcy_eta0_component_r1`，收据 `logs/upl_c08_darcy_eta0_component_r1.{build,check}.json`。成功check含actual_call、component_completion、source_native及2ct/6Darcy/0updates、上游不变/原rate恢复bit相同的实际检查结果；不能在执行前假定passed。失败保留真实Popen/Win32出口、首因和部分CSV，不自动重试、重解码、减dt或改参数。无SHA扫描，正常完成也不代表物理验收或新正式能力。
