# C08 ψ0 trace窗口66帧原生读取器（仅作者准备）

本新入口只允许ψ0、global completed4264000、66个真实保存帧（每4000次更新保存；首帧completed4004000，末帧saved Step4263999）。源为原r2 GPU的真实认证10秒PRE，实际source clock从PRE读取；逐次scalar+=2.5e-6核原生时钟，绝不将绝对时钟重写为10.66或将tau写死为.66。本工具不启动、编译或重算求解器，不直接读取trace CSV；阶段CSV由另一个检查器审查。

仅新增本CPP、同名build.py和本note。builder复用已通过的formal/bedkeep核心派生和严格AS Configuration嵌入分号解析，仅将300/5200000固定profile改为66/4264000及相应scope名称。生成新builddir内的core、unified diff、derivation stat；不更改旧1/3/60/300帧读取器、原输入、程序或结果。保存节拍为明确窗口常数，不声称来自外部启动前plan；真正正常Run.csv仍必须为Steps4264000/PartFiles66及原7060/2060登记和零排除。

原始6805IDs、22typed数组、5000土粒与1805固定点、P0逐位、单J ledger、κ单调、FS正压政策、signed dterror<=1e-14、scalar clock<=1e-14及4e-8m固定平面门均不变。源释放资格仍原260目标；五保留床点1800/1852/1904/1956/2008的源半dp几何、原固定坐标与零速度保持，实际非连续退休255。每帧额外lazy header扫描严格核KeepBedOverlap/Kept5/Retire255以及AS ReleaseOnly/Active/.2f/2.55f，不另解码字段数组；NoPen仍FixedPlaneStageProjectionReleaseOnly、ReactionClosed=false。没有第23数组，也不声称力学反力/Darcy已闭合或物理精度验收。

root全文审后可单次构建（目前未执行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_stage_trace_window_native_r1_build.py --execution-authorized
```

新程序为 `tests/outputs/upl_c08_stage_trace_window_native_r1_build/C08StageTraceWindowNative_win64.exe`；构建收据 `tests/logs/upl_c08_stage_trace_window_native_r1.build.json`，仅链接原六个封口Release utility objects和本main，不链接JSph。未来唯一读取调用保留8参：

```text
C08StageTraceWindowNative_win64.exe --read psi0 CPU|GPU DATA CERTIFIED_PRE 4264000 FRESHOUT
```

FRESHOUT必须不存在。输出leaf与原工具相同：typed22.bin、typed22_layout.csv、clocks.csv、history.csv、plane_gaps.csv、completion.json、bedkeep_metadata.json；completion stage=`upl_c08_stage_trace_window_native_r1`，metadata stage=同名`.metadata`。raw头为6805/22/66，source旧260/actual255/kept5含义分别保留。程序/backend/实际求解退出及配置绑定仍由根owner独立审核；无自动后续、half、全程或物理准入。
