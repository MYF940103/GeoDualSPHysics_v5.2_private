# hdp1.5 fresh10s PRE：仅准备，未执行

本轮只新增五个文件：同名 support Python/本说明、`configs/upl_c08_hdp15_preload_GPU_r1_Def.xml`、`configs/xupl_c08_hdp15_preload_GPU_r1_win64_GPU.bat` 和 `configs/upl_c08_hdp15_psi0_GPU_r1_Def.xml` 草案。事前均不存在且未跟踪。未运行 GenCase/solver/PartVTK/reader/构建/队列，未改根目录、旧输入/程序/PRE/结果，也未生成新的 runtime 或 native reader。

源Def由根 `CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml` 机械复制，数值只将 `<hdp value="1.2">` 改为1.5，另改说明。保持Cubic、dp.04、dt2.5us、TimeMax13、event10、TimeOut.01、原材料/Model1-Ck2、阻尼.02及Shepard每40步；`elastic_source=true`，AS/NoPen/keep_bed_overlap仍为默认关闭，不直接赋应力或读取任何旧PRE。源使用现有官方 `support/runtime_r6` GenCase/Release solver，CLI `-nsteps:4000000` 停在事件PRE，不能执行下次循环的撤墙。

接收草案从根r6 ψ0 Def复制，仅改hdp1.5、说明与statefile，指向未来 `tests/outputs/upl_c08_hdp15_preload_GPU_r1/data/Part_1000.bi4`。keep5、NoPen固定平面、AS.2/n3、CompletedOnly及所有材料原样。没有接收BAT/owner，当前不准入、不启动接收；新PRE必须先经真实源状态/同H合同与物理审查。源仍应有7060=2060固定+5000土粒，接收若以后准入才为6805=1805+5000。

## 根审阅后的唯一入口

Root先写 `logs/upl_c08_hdp15_preload_GPU_r1.admission.json`，至少包含以下明确准入；没有它双击不会启动任何程序：

```json
{"passed":true,"allowed_job":"upl_c08_hdp15_preload_GPU_r1","hdp":1.5,"planned_global_end":4000000,"expected_saved_frames":1001,"root_thread_id":"01a07683-bc64-7463-8db7-9ee6243967d8"}
```

之后可双击新测试BAT，或由根直接执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_hdp15_preload_r1.py --execution-authorized --notify
```

仅一个owner：fresh GenCase一次→GPU solver一次→原schedule PS一次→selected PartVTK六次（Fluid/Bound分别part100/500/1000）。BAT位于configs，以自身路径定位tests/support；采用本机D:/anaconda3 Python，否则PATH Python，不安装依赖。它不是正式根目录发行入口。并发或既有owner/output/失败partial由独占claim和fresh检查拒绝，不自动重跑。

源输出为 `tests/outputs/upl_c08_hdp15_preload_GPU_r1`，保留全部1001个原始BI4。`particles/PartFluid_0100/0500/1000.vtk` 为5000土粒，PartBound同帧为2060固定点，含真实P0/excess/J/n/k/κ及有效应力字段；VTK坐标仅float。1/5/10是输出序号对应的名义时刻，实际保存clock仍以native后续审查为准，不能用名义整数替换原生时间。

owner复用现有 `base.owned` 的真实Win32句柄/创建时间/exe/argv/parent及出口封口，每30s刷新原始Run.out最后完整PART行。`.start/.call/.owner_admission/.run/.status` 保存在tests/logs。输入、root模板、runtime/DLL、原build/source捕获、GenCase真实生成的XML/BI4/Normals均用stat绑定，不扫SHA或旧objects；所有源原稳定性/材料守卫仍由原程序执行，不放宽或禁用。

正常solver后要求真实4M steps、1001帧、注册7060/2060、H=.06/dp.04、无排除、未import/未release及预载阻尼/Shepard启用。schedule PS只证明调度/文件存在；本owner**不独立认证22数组、MaterialLawVersion、κ0、严格平衡或时步数值**。新最终PRE资格留给既有认证loader与新同H窄profile；不扩成1001帧新认证框架。真实solver出口0后立即保留solver_completed=true；纯输出审查失败标为solver_output_review，派生失败标为postprocess，均保留真实solver出口0，只修审查/派生，不重新计算source。

`--notify`只在封口终态后向上述已准入根线程尝试一次 `codex queue`，45s超时可能已送达，绝不重发/重新布防/连通性测试。真实环境线程若存在必须与该根线程一致；普通双击没有环境线程时仅使用admission固定的同一根线程，不能任意选择其他目标。通知不会启动native、receiver、其他ψ、half或新PRE。

## 对照限制

保留的h1.2源来自server旧law1程序；新h1.5源将由runtime_r6统一law2程序生成。两者均受测的弹性PRE资格可复用，但不能把来源不同说成独立h-only/0ULP控制，也不因此自动新增fresh h1.2参考或半步链。本机旧CPU8/4M步10s PRE耗时约6h42m只作成本背景，新GPU h1.5时间未知；更大支持域不保证MLS、稳定性或更高精度。10s正常完成不等于平衡，.03s更不是平衡。Root根据真实结果决定后续，不由本脚本自动延长、撤墙或接收。
