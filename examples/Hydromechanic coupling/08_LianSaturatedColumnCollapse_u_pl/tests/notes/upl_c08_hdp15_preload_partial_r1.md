# 两个明确 PRE profile 的原生只读诊断（作者稿，未执行）

仅新增同stem `.cpp`、`_build.py`、`_run.py` 与本说明；事前查不存在/未跟踪。没有执行构建、reader、求解器、PartVTK、队列或修改生产/旧数据。仅复用封口六个BI4 utility对象及原公共22数组读取函数，不调用 `JGravityPreloadState::Load`，不伪造已认证PRE或正常Run.csv。

固定两profile：`h15_failed`消费真实 `upl_c08_hdp15_preload_GPU_r1`，H=float(.06)、52连续保存帧、最后completed204000；`h12_control`消费未来真实 `upl_c08_hdp12_preload_control_GPU_r1`，H=float(.048)、实际1..53帧、completed≤208000。后者只有真实exit0且其run及native都达到208000/53才可称正常短控制完成；exit1保留实际partial，不预造成功。两个profile始终uncertified，不是10s完成/接收资格/平衡或物理验收。

根完整审阅后，构建一次；随后每个真实封口profile单独读一次：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_hdp15_preload_partial_r1_build.py --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_hdp15_preload_partial_r1_run.py h15_failed --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_hdp15_preload_partial_r1_run.py h12_control --execution-authorized
```

构建目录 `outputs/upl_c08_hdp15_preload_partial_r1_build`，程序 `C08PreloadPartial_win64.exe`，收据 `logs/upl_c08_hdp15_preload_partial_r1.build.json`。实际utility父构建为 `mdbc_partition_ReleaseCPU_r1`，仅JPartDataBi4/JPartDataHead/JBinaryData/JObject/JException/Functions六对象+自己的main；不链接JSph/solver。生成 `public22_core_r1.h` 只机械截取既有case02公共reader的include/type aliases与Need到Original15，删去中性波物理常量及所有旧profile/main。真实运行归档的 `FunSoilMaterial.h` 覆盖新build目录内对应头；相关BI4/TypesDef ABI头逐字一致检查，保留原归档/对象不变。

CPP窄CLI为 `--read h15_failed|h12_control DATA MATERIAL_CSV FRESHOUT`，不准任意H/任意案例。唯一read薄wrapper消费原run/start/call/status/owner_admission、真实GenCase/seed/actual generatedXML、所有原consumed与连续PART stat；程序/source_build从实际owner_admission取，不能要求失败run中不存在的成功段字段。无活动相同reader或原输出使用者、无既有/partial decode才调用一次。收据分别为 `logs/upl_c08_hdp15_preload_partial_r1.check.json`、`...hdp12...`；输出分别为 `outputs/upl_c08_hdp15_preload_partial_r1`、`...hdp12...`。无SHA/BI4重写/自动重读或后续物理任务。

## 保留的确定门与实际输出

每帧7060 IDs=2060固定+5000soil，原22 typed数组/212 bytes每ID、原native排序按ID导出。`typed22.bin`头保留该profile**实际**帧数，不改成共同52/53；每record为真实f64 time与22列SoA。相同layout另导CSV。原有限性、P0固定材料基准及初始水静P0位、excess原float关系、double有效应力/float展示、κ0、固定几何/marker、饱和J/n/V/rho/k Model1-Ck2 ledger、rho float缓存等门保持。初始Part0的Time0/Step0单独处理，后续实际Get_Step+1逐次标量+=2.5us核clock；初始允许原空signed sentinel，非初始必须非空且signed≤1e−14，绝不由part*.01替代实际clock。

元数据核MaterialLawVersion2/sf0、Dynamic/schema1/Model1/Ck2、HydroMechFreeSeepage=true、GravityPreloadPhase0/event10/4M、原右墙260、DampingActive与ShepardActive。不到4M的原生记录不能出现最终handoff认证四键，也不能出现release/import/AS/NoPen激活字段。所有FS原值/p保留，分类仅检查原0..4域。

输出 `summary.csv` 为每帧全土体、固定初始材料top/bottom/left/right 2H带、内部及非空savedFS23组；各带重叠，不能相加成独立区域。`layers.csv`保留50个初始z层各100材料ID、全部实际时刻；`snapshots.csv`只存实际存在的part0/25/50/51各5000soil，用于后续散点。列包括p/速度/有效和总应力RMS、J/n/rho/k范围、DP f极值/ID/位置及savedFS23正/负/零数量。summary无FS23时仍在all行真实记0，不将空集合称边界通过；空savedFS组不造均值。

## source表面政策与保存顺序

以实际冻结runtime_r6归档为准：FreeSeepage1、Drainage0，完成步是FS2/3**正p才投影0、保负p**，不是drained全零。冻结 `JSphGpu::ShepardRegularizePorePressure` 在copy后已经再次ApplyFreeSurface并positive-only ponding。源不是free-seepage hold，接收重排序的临时hold不能推广到fresh源。

但SaveData还会再次ComputeFreeSurfaceTracking；保存帧没有投影当时FS mask的独立记录。因此本独立PRE诊断对**全部savedFS/p符号只作观察**，不施加savedFS≤0/全零新门，也不声称vacuous零压通过；这不是修改既有released6805门。明确记录initial和completed%40对应Shepard调度条件，保存原FS分类及各材料带分布，供根后续审查是否有假FS/分类切换；不重演或修改边界算式。

## DP数值口径及失败边界

系数来自实际generatedXML的DPCtes/φ/coh/残余/衰减，wrapper写只读绑定的material CSV。采用冻结InitSoilParameters相同顺序：XML先float degrees、`float(TORAD*float_degrees)`，再调用**冻结运行归档相同** `fsoil::UpdateDPvars`；不取理想25度double直接算。真实sf/κ均0、φ25固定、cp5000/cr1000/ncoh5；fresh无PartBegin，FOS触发不激活（冻结默认SoilTriggerFos1.65只记录，不错误除coh）。原生producer不写φ/coh/DP系数，不能声称从BI4直接读到了这些参数。host libm/编译与CUDA可能有末位差，输出α/kc/float-radian供核查，不把近零f最后1ulp当屈服错误或新验收门。

使用有效SigmaState构造I与q，`f=q+DP_phi*I−DP_kc`；不将p或总应力代入材料yield。只用UpdateDPvars/GetInvariants作保存态描述，未再次调用ReturnMaterial或积分；Material中K/G在该系数函数不参与计算。实际h15状态bits4经冻结enum/atomicOr核实是1<<Smooth2，被elastic_source严格资格拒绝，不能误叫枚举TensionRepair4。52保存态的κ0/DP f只能说明已接受的保存记录，不能恢复未保存Cor trial的ID/f/精确时刻，也不能用lastsaved当实际故障时刻。
