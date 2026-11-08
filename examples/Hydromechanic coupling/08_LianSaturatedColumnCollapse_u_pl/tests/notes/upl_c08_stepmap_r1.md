# 固定负压方向的10个独立CPU一步映射（作者稿，未执行）

新增同stem CPP、_build.py、_run.py及本说明；生产源码、物理objects、原程序/PRE/Shepard失败结果/72帧native及旧组件不改。当前只作者和静态检查，根完整审阅后才分别build/run一次，无自动后续、solver Run、GenCase、native解码、VTK或半步长链。

输入仅 `outputs/upl_c08_shepard_partial_r1` 原typed22的part71：实际t=10.720000000602795、completed=4288000，读取一次该原生record的22字段。固定ID5205，saved FSType=0、p=-271776.375Pa；坐标约(2.65316,0,1.62660)m。这是一条事先选定的负压AS敏感方向，不自适应重选更危险或更好看的粒子，不能称全状态最危险mode。保持原72帧头及实际clock/ID，未保存失败步4289868不参与。

复用已通过AV组件的合法生命周期：原bedkeep DebugCPU86非main objects＋新helper，归档类头/本构/接触头与同source闭合，MSVC14.36原flags。builder只换TAG，物理obj不重编。真实InitRunCPU→原认证r2GPU PRE Load/handoff→一次keep5 release→按ID恢复part71；PRE仍按其2.5µs合同加载，不借generic PART重启或修改metadata。保存态的GPU Shepard滤波历史保留在输入p中。CPU原release关闭Shepard，本轮每clone只走completed4288001（非40周期点），无滤波调用；不得将此组件推广为后续多步Shepard完整运行。

每h=2.5/1.25µs独立做baseline、+100、−100、+50、−50Pa，共10clone updates、20原force调用。每次从同一保存态完全Restore；只把ID5205孔压设为 `float(double(p_saved)+amplitude)`，实际float差导出；P0/κ/J/σ/位置/速度/ρ等primary均按显式incoming Snapshot逐bit检查，excess重新按p−P0派生，不要求它保持旧值。扰动mask只选原FS0点，不覆盖后续真实FS分类，也不预先clamp压力。

导入及恢复后，每clone用独立RAII `JDsFixedDt(h)`，显式设置SymplecticDtPre/LastDt=h；返回或异常均先恢复原FixedDt指针再销毁临时对象。直接调用原protected `ComputeStep_Sym()`，因此真实Pre/Cor ReturnMaterial、J、plane、half cell/force及两次DtVariable完整保留，不抄积分器、不跳necessary bound或DtMin。正常返回后仿原outer loop仅RunCellDivide→TimeStep+=实际used_dt→LastDt→Nstep++一次。各短h的completed索引只是本clone的一步记账，不冒充原2.5µs全局保存网格或GPU精确重启。

结果统一相对**同h baseline输出**求差，权重固定为原part71各材料点的n、V、ρ；实际K/G/Kw来自原SoilCte。三项平方范数：

`Qp=Σ(nV/Kw)δp²`；`Qv=ΣρV|δv|²`；`Qσ=ΣV[(trδσ)²/(9K)+devδσ:devδσ/(2G)]`。

有效应力使用完整3D的xx/yy/zz、xy/yz/xz，dev按trace/3，offdiagonal在Frobenius里×2。三项均未乘1/2，单位可相加但**只定义扰动范数**，不称完整固液能量或稳定谱。输入只有局部孔压Qp，Qv/Qσ为0；报告总quadratic ratio和其平方根gain。baseline自差为0，除零的ratio/gain留空，不伪造0或1。J、κ、位置及FS另报，不混入该总范数。

每个±结果除以其真实float输入δp，报告符号两侧不对称；100/50Pa中心方向按实际两端δp之差作分母，再比较幅度一致程度。只比较同一个有限步长映射，不把h改变当5Pa跨模型/half误差，不自动推出应该改变正式dt。

输出仅3CSV：maps.csv（10行，各clone实际clock/一步数/绝对状态范围、初末范数与差异）、differences.csv（8个扰动clone×全部5000土ID＝40000行的δp/δv/δσ/δJ/δκ/δ位置/FS）、consistency.csv（两个h的符号/幅度一致性）；另completion与Run.out。原P0 bit、κ非减、饱和J/cache、完整ID/固定角色、completed FS2/3非正孔压及4e−8m平面门保留。

额外零force观测为 `theta_mid=PoroThetac`（原ComputeStep后保留的Cor-stage量）和 `T=trσ_end−trσ_in−3K*h*theta_mid`，每条soil差异行同时导出baseline/扰动值及差，maps给max|T|。它不设新gate，不直接等于塑性体积应变或错误：ψ0 smooth返回的理论trace保持、apex/tension-face附加流、packed梯度舍入与时间积分均可能影响它。未导出逐ID实际return status，不以T反推分支或λ。

直接原方法不暴露实际contact hit计数，故只记录原plane守卫及端点落在4e−8m带内的membership变化，不能当反力、投影调用次数或接触闭合证明。失败停止，不开始下一clone；保留原exception及部分CSV。`STEP_MAP_COMPUTE_RETURNED`逐次记录实际完整原积分器返回，失败收据区别它与已完成输出检查的map行数，不把10计划值当实际。没有正常completion时不读取半步指针重建失败态。

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stepmap_r1_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stepmap_r1_run.py --execution-authorized
```

新helper=`outputs/upl_c08_stepmap_r1_helper/component.exe`，结果=`outputs/upl_c08_stepmap_r1`，收据=`logs/upl_c08_stepmap_r1.{build,check}.json`。真正发生的是10条新CPU独立一步轨迹，不声称physical_steps=0；正常完成仍非GPU重放、完整状态重启支持、长程稳定或物理塌陷验收。
