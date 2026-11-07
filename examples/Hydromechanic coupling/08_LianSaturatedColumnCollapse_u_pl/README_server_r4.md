# r4：NoPen开启、AS关闭的三个共享PRE接收分支

本轮仅准备三个完整3 s接收分支，不新增PRELOAD、不重新求解10 s源。实际启动/结束由 [support/STATUS_current.md](support/STATUS_current.md) 记录；本文不把准备完成或0.15 s短诊断当作三个完整分支已经运行。

GPU BAT固定绑定原 `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4`。CPU BAT固定绑定自有 `CaseLianSaturatedColumnCollapse_shared_preload_r3_CPU_out/data/Part_1000.bi4`；当前该CPU源尚未运行，缺失即停止，不能复制或改名GPU源来冒充CPU证据。源目录、真实标量时钟、P0/J/应力/κ等完整状态原样由专用PRE加载器认证；不扩展成通用塑性PART重启。

运行环境为Windows x64、UCRT及合适NVIDIA驱动，CPU默认8线程、GPU默认GPU0。部署匹配的 `support/runtime_r4`，包含CPU/GPU求解器、GenCase、C08Native、PartVTK及随程序配套的DsphConfig、Chrono/MSVC运行库。只使用明确部署的r4程序，缺失时停止，不回退到runtime_r3或canonical旧exe。预编译程序无需安装Visual Studio/CUDA Toolkit。

完整后处理另需Python 3、NumPy、Matplotlib。启动器优先 `D:/anaconda3/python.exe`，否则PATH的Python，调用 `support/postprocess_lian_collapse_r4.py --check-tools` 先检查依赖；不自动安装。源schedule检查及依赖预检均在GenCase/求解之前。schedule只核原4M/1001帧和PRE文件存在，不代替solver的原生资格认证。

双击根目录对应三组的CPU或GPU BAT。每个BAT只运行自己的一组：检查认证源路径和新输出不存在→将XML唯一statefile marker替换为源PRE绝对路径→GenCase→solver→正常退出后native→独立PartFluid/PartBound→PNG/CSV。三组顺序运行；启动器没有并发锁，不自动接着启动下一组、不重试或删除失败输出。

|组|ψ0 (°)|cp (Pa)|cr (Pa)|n_coh|sf|
|---|---:|---:|---:|---:|---:|
|psi0|0|5000|1000|5|0|
|psi2p5|+2.5|5000|1000|5|0.2|
|psim5|−5|7500|1000|5|0.2|

三组φ=φr=25°、n_phi=0，统一DP v2、材料参数和保存κ仍为float、局部返回为double。几何/初始化保持原5000土+2060初始固定墙、dp=.04m、Cubic h/dp=1.2、侧壁FreeSlip/底面NoSlip、E20MPa/ν.33/n0.35/Kw1GPa/k0=2e−4、Model1/Ck2、自由渗流及全部原稳定门。保留负孔压，不引入论文额外负压松弛、TPI、HG、独立SPR或shifting。

唯一新增边界算子选择为NoPen=1，XML显式声明且solver CLI为 `-mdbc_freeslip:1`；ArtificialStress显式0，等价于r3原隐式关闭。NoPen沿既有法向速度/位移投影，属于受限分步边界选项，不改变原投影公式，也没有将投影约束反力回馈同一步Darcy。输出应明确 `DynamicNoPenetrationPolicy=LegacyOperatorSplitReleaseOnly`、Active=true、ReactionClosed=false；不能将该限制隐藏或称为反力闭合接触。

dt=0.0000025 s、DtMin=1e−8 s、TimeOut=0.01 s、event=10 s、TimeMax=13 s均保持。加载实际PRE后首循环撤去右mkbound2的260个样本，关闭预载SoilDamping(.02)和Shepard40，继续至总时刻13 s。实际累计时钟不能强写10或0；τ取实际撤墙时刻之差，Part0是真实post帧。完整终点应由Run/native实际核global约5.2M步及保存时钟，不捏造首帧为PRE或固定301帧。

输出路径是 `CaseLianSaturatedColumnCollapse_<group>_shared_r4_<CPU|GPU>_out`。已有路径即拒绝，不覆盖旧r3失败out。若solver正常完成而后处理失败，先检查保留的日志，再只做后处理，例如：

```bat
xCaseLianSaturatedColumnCollapse_psi0_shared_r4_win64_GPU.bat --postprocess --unattended
```

这两个参数可互换顺序；postprocess模式位于已有输出拒绝之前，不GenCase、不求解、不改BI4。后处理仅复用已闭合且输入/输出绑定仍匹配的记录，失败或未绑定partial不会自动覆盖。

每组保留native的22数组/真实ID与时钟、logs、全部BI4、GenCase companion/Normals，以及 `particles/PartFluid_####.vtk` 5000土体和 `PartBound_####.vtk` 1800固定墙全系列，不生成PartAll。图及匹配CSV进入独立r4 figures；三个同后端完整native齐全后再作三组比较。官方VTK坐标float，原BI4 Posd及原生应力精度保留，κ不是完整塑性应变张量。

既有NoPen/AS0的ψ0 GPU .15 s诊断跨过原故障位置，15帧保存状态未见穿底/左墙；这不是完整3 s或其他两ψ组的物理验证。旧r3 ψ0在10.11 s失败，原数据不删除、不重跑冒充r4。正常求解退出、代数ledger安全门和后处理完成均不等于预载平衡或论文精度验收。

本轮不移动旧输入、程序、PRE或结果；旧r3脚本、README_server_r3.md、ZIP和manifest作为历史保留。原 `support/LianCollapse_upl_win64_r3.zip` 未更新，不代表r4部署。不要从旧ZIP或旧runtime自动补缺当前程序。
