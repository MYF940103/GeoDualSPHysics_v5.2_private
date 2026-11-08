# 冻结速度→AV→Darcy块：CPU组件（作者稿，未执行）

只新增同名CPP、_build.py、_run.py及本note。原zero_cpu_r2、330call压力组件、生产源码/物理objects、runtime、PRE和所有输出保护。根全文读后才分别build/run一次，当前不执行。

输入是新Shepard失败但72帧原生门通过的 `outputs/upl_c08_shepard_partial_r1`，仅part49(τ.50)/71(τ.72)。CPP一次各读该原typed22 record的全部22字段，不重读BI4/旧PRE1001态、不补零保存场；原头72/6805不改。运行绑定实际failed run、唯一partial check、clocks/layout及原generatedXML/BI4/Normals、原认证r2GPU PRE。

**源码闭包：**完全复用封口 `upl_c08_bedkeep_DebugCPU_r1` 的86非main物理objects、同源归档headers、MSVC14.36 /Od /MTd /fp:precise /openmp；只新helper CL+Link87objects，无物理obj重编。private GPU Shepard包只变JSphGpuSingle host释放flag和计量，force/kernel本体与bedkeep相同，source.json的baseline capture/archive、唯一changed member和reverse proof必须匹配。故这是**新CPU保存状态force评估**，不是同binary、GPU packed重放或通用跨backend restart。

合法原LoadConfig→InitRunCpu→真实PRE handoff→一次keep5 release；使用原6805=1805fixed+5000soil。BoundNormal/slip/code来自真实seed和原5点覆盖，再按原ID恢复主状态、LoadDcell/RunCellDivide并重新复制保存primary/FS/θ/PosDiv。restore临时禁Shepard/FreeSeepage避免滤波/投影；不改原ShepardActive=true元数据。CPU原release清Shepard，仅此次force-only诊断完全不调用filter wrapper；保存的p包含GPU此前真实滤波历史。damping仍OFF、AS总应力ε.2/n3、AV.1、Cubic1.2、Ck2及所有其它原scope/finite/domain门不变。

**恰10次force/0updates：**每态baseline优先，随后η=.001/.0005各正负：仅5000 soil速度写 `float((1±η)*double(v_saved))`，ρ缓存不改。实际float差与方向值导出，不用名义η伪造向量。每次完整Restore→真实wall/FS/C/AS/AV→wallAce→Darcy→导出→PosInteraction cleanup；不ComputeStep、ReturnMaterial、接触投影或clock推进。每次相对于明确incoming Snapshot核全部soil位置/速度/ρ/σ/κ/p/P0/J bits不被force更新；baseline还核原值。J/n/V/ρ/k ledger原bits门保留。

源码五项Sum/传播预算沿zero_r2原文，仅输出附带FS-Ace、chain-Ace与chain-Gp拆分。≤81 receiver独立allparticle shadow核实际rate，gamma=(64*Nneighbor+256)eps/(1−...)及32eps_float绝对传播scale原预算不变。中心差分预算为两端原预算相加除2η，再加已声明16eps_double减法传播；不调物理阈值。全5000真实force/rate/θ参与范数与条件性功，不为每点另做N×N shadow；所选点只限制输出，邻域/真实wall闭合绝不截断。

记B=Kw/n，M=ρtV，Wp=nV/Kw，Dδa=ΣVj(δaj−δai)·Ci∇W；冻结压力/几何/系数及FS时：

`δr = −B δθ + (Bρw/γ)[ki(Dδa+χFS δai·lx)+k'_J gradJ·δai]`，其中k'_J=ki/[(1−n0)Ck]。

本scope没有damping/HG/DEM/load/SPS等速度依赖动量项，AS谱输入p/σ/J固定，所以方向δAce主要检验当前AV；但若重算FS/C/AS发生变化全部记录，不能继续冒称严格固定块。baseline-relative变化计数不藏匿/删样本，不把此模型干预强压0ULP。近边AV的dot<0开关只做选中receiver的test-side rawfloat/TangenVel shadow计数，非生产新telemetry；同正比例缩放在实数保持approaching符号，实际float/MLS舍入及单边非对称仍需如实报告，不许据有开关就放宽预算。

输出4CSV：calls(10)、rates(5×两态selected总数)、response(2×selected总数)、directions(4)。rates保留原实际p/J/κ/FS与actualrate、五项shadow、AS不改、实际velocity差和AV开关shadow；response分别给两η的真实direction、Ace/θ/rate与LP/defect/divAce/chain及两个Ace拆分的中心差分、传播预算。direction给全5000 `||δa||M/||δv||M`、`||δr||Wp/||δv||M` [1/s]及dt×gain，实际方向偏离原v的质量范数，以及正负单边不对称范数。

条件性功使用实际float方向u=(vplus−vminus)/(2η)：ΣM u·δa、ΣWp p·δr、压缩项ΣWp p(−Bδθ)、非压缩速度响应ΣWp p(δr+Bδθ)。p为此保存态absolute孔压，单位W（2D按既有单位厚度解释）；只是当前冻结方向的动能/压力存储率代理，非完整固液能量定理，不能把局部/全局正值自动叫不稳定或忽略边界功/应力/塑性反馈。soil FS/C/AS held计数不能单独证明全部墙p/σ/J/C不变，因此全域余项只能称AV-mediated candidate；选中点的LP/chain-Gp等差分用来检查其它贡献。Σeff后续返回、J演化、两个stage映射与pressureJacobian均未求导，不能宣称full coupled稳定性。

预计10force本体秒级：既有zero_r2四forces实际call区间0.978s、330pressure组件33.334s；本轮含新输入重建/少量shadow/CSV可能数秒至十余秒，非新benchmark保证。失败保留首因与部分输出，不自动重试/改AV/缩dt/另一ψ；完成也不等于Shepard或物理塌陷验收。所有新输出浅放 `outputs/upl_c08_av_velocity_r1`，helper独立`_helper`，logs同tag；不生成新solver/GenCase/native/VTK。

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_av_velocity_r1_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_av_velocity_r1_run.py --execution-authorized
```
