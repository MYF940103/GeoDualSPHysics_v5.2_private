# Lian 2023 饱和土柱塌陷：r4 接收入口

最新接收流程见 [README_server_r4.md](README_server_r4.md)。r4采用既有NoPen法向速度/位移投影、AS关闭；输入和入口已准备，实际运行状态见 [STATUS_current](support/STATUS_current.md)。正常退出和后处理完成不等于完整塌陷或论文精度验收。

**本机已有真实r2 GPU 10 s认证弹性PRE，不要重新点击旧PRELOAD入口。** 六个接收入口中的三个GPU BAT固定读取原 `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out`；CPU BAT固定读取自有 `CaseLianSaturatedColumnCollapse_shared_preload_r3_CPU_out`。当前CPU源尚未运行，缺失即拒绝，不能用GPU源冒充CPU证据。本轮没有r4 PRELOAD入口，不重命名或修改原PRE。

|接收组|XML|CPU|GPU|
|---|---|---|---|
|ψ=0°|[配置](CaseLianSaturatedColumnCollapse_psi0_shared_r4_Def.xml)|[入口](xCaseLianSaturatedColumnCollapse_psi0_shared_r4_win64_CPU.bat)|[入口](xCaseLianSaturatedColumnCollapse_psi0_shared_r4_win64_GPU.bat)|
|ψ=+2.5°|[配置](CaseLianSaturatedColumnCollapse_psi2p5_shared_r4_Def.xml)|[入口](xCaseLianSaturatedColumnCollapse_psi2p5_shared_r4_win64_CPU.bat)|[入口](xCaseLianSaturatedColumnCollapse_psi2p5_shared_r4_win64_GPU.bat)|
|ψ=−5°|[配置](CaseLianSaturatedColumnCollapse_psim5_shared_r4_Def.xml)|[入口](xCaseLianSaturatedColumnCollapse_psim5_shared_r4_win64_CPU.bat)|[入口](xCaseLianSaturatedColumnCollapse_psim5_shared_r4_win64_GPU.bat)|

实际使用前须部署匹配的 `support/runtime_r4` 程序和后处理工具。双击所选BAT，流程为Python/工具预检→同后端源schedule检查→GenCase→唯一接收solver→native→分别PartFluid/PartBound→PNG/CSV。优先 `D:/anaconda3/python.exe`，否则PATH的Python；需NumPy/Matplotlib，不自动安装。各组顺序运行，启动器不设并发锁，不自动启动下一组。

保持dt=2.5µs、TimeOut=.01s、实际PRE/event约10s、TimeMax=13s，即完整撤墙后3s；保留实际标量时钟。XML显式NoPenetration=1/ArtificialStress=0，CLI为 `-mdbc_freeslip:1`；其余原物理设置不变。源载入后首循环撤右侧260墙样本、关闭预载阻尼和Shepard，保留自由渗流及Model1/Ck2。NoPen是分步投影，未把投影约束反力回馈同一步Darcy，元数据明确 `LegacyOperatorSplitReleaseOnly`、`ReactionClosed=false`；这项数值限制仍须随完整结果审查。

新输出统一 `CaseLianSaturatedColumnCollapse_<group>_shared_r4_<backend>_out`；已有输出即拒绝，旧r3失败结果不覆盖。求解已正常完成、仅需后处理时，在原BAT后加 `--postprocess --unattended`；不GenCase、不求解、不改BI4。两套VTK为5000土体的PartFluid与1800固定墙的PartBound，不生成PartAll。官方VTK显示坐标为float，原生double位置和应力精度另保留；κ为标量历史，不是完整塑性应变张量。

旧r3输入/启动器、README_server_r3.md和所有程序、PRE、输出原样保留，本轮尚未归档r3。历史r1/r2输入归档见 [原清单](tests/notes/retired_root_inputs_r4.manifest.json)，早期README见 [历史记录](tests/notes/README_root_history_before_r3_cleanup.md)。旧 `support/LianCollapse_upl_win64_r3.zip` 是冻结历史快照，未更新为r4，不用于证明当前部署。许可证见 [LICENSE](LICENSE)。
