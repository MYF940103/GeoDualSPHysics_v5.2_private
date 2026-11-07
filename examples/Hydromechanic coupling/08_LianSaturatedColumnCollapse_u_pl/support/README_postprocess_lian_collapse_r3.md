# C08 r3 后处理

`postprocess_lian_collapse_r3.py` 仅后处理，不构建、GenCase、运行solver或重启。需要 Windows x64、Python 3 + NumPy/Matplotlib，以及 `support/runtime_r3/C08Native_win64.exe`、`PartVTK_win64.exe`。当前本机Python为 `D:/anaconda3/python.exe`；没有自动安装或缺依赖fallback。

```powershell
D:/anaconda3/python.exe support/postprocess_lian_collapse_r3.py --check-tools
D:/anaconda3/python.exe support/postprocess_lian_collapse_r3.py --group psi0 --outdir CaseLianSaturatedColumnCollapse_psi0_shared_r3_GPU_out --source-pre CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4
```

`--group` 支持 psi0、psi2p5、psim5、preload。preload只按已完成的4M/1001份原始结果导出VTK，不套collapse原生读取/图形模板；source-pre仍应明确给真实PRE。collapse接受完整global5.2M或已完成的短窗4.04M。真实backend来自实际Run.csv Hardware（CPU或Gpu_N），再传给native工具；native库本身不证明后端。CPU全程本轮未物理验收，支持入口不等于验收。

脚本读取实际RunName.xml，核各组φ25°、coh5/5/7.5kPa、ψ0/+2.5/−5°、sf0/.2/.2、Ck2、dt2.5µs、输出.01s和真实PRE路径。`C08Native`真实读取并认证源Version1或2及全部22数组/原门，输出`out/native`；不改原BI4/时钟/ID。`out/logs/native.call.json`封口实际程序exit和source/tool stat，无SHA。仅当既有成功call的输入、参数、全部派生输出仍匹配时复用，不重复native；失败或无manifest的partial必须保留并离线诊断，不能自动覆盖/重跑。

粒子严格分成两套：`out/particles/PartFluid_####.vtk` 为5000土体，`PartBound_####.vtk` 为fixed边界，preload2060、撤墙后1800；该模型没有moving边界。使用实际已验证变量表、`-threads:1` 和 `-filexml <out/RunName.xml>`（传入实际GenCase生成的XML，以正确导出mk），全部帧；不生成PartAll。每套都有独立call及全帧输出stat，已完整且绑定不变可复用。原BI4 Posd/native是double，当前PartVTK输出坐标为float；精度与位移验收应读取native，不拿VTK坐标代替原生double。

默认GPU图在根`figures/collapse_<group>_r3`；CPU在`figures/collapse_<group>_CPU_r3`，避免覆盖GPU。短窗可显式`--figdir tests/figures/<tag>`。已有figure source.json若指向别的输出/后端则拒绝。history图与CSV覆盖压力均值/极值、真实PRE位移均值/RMS/最大、实际前缘x/最大高度、κ/n/k、速度、总应力及J。位移直接采用native reader以真实PRE算出的history；当前没有PRE坐标导出，**不假造顶部/底部材料层位移，也不把首个post帧当t0**。

散点图选实际已保存且接近τ=.1/.5/1/2/3s的帧，图中明确actual τ；没覆盖就跳过。p、κ、n、k使用该组全历程实际min/max颜色范围，不平滑、不插值、不clip、不改数据。constant字段以单色加实际常数标注，不造色条范围。每张图都有同名CSV。

同backend三组full native和成功call全部齐全且源绑定一致后，生成`figures/collapse_three_groups_r3`（CPU加_CPU）历史比较，以及末帧四变量共同色标形态PNG/CSV；否则明确输出SKIP，不拿短窗冒充全程。孔压/塌陷这里没有被自动当作论文精度验收。

已完成solver后可仅重复上述后处理命令以修复/刷新图CSV，成功native/VTK会按manifest复用。派生PNG/CSV可更新，原始BI4、输入、PRE不变；工具失败或partial不自动重试。最终`out/postprocess_r3.json`记录完成项，但`physical_acceptance=false`，仍需根线程检查图和论文对比。正式BAT/owner的对接由根线程另行审核，本次仅新增脚本和本说明，未执行。
