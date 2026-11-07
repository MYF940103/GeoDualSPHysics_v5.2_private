# Lian 2023 饱和土柱塌陷：r5 接收诊断

当前入口与依赖见 [README_server_r5.md](README_server_r5.md)，实际运行状态见 [STATUS_current](support/STATUS_current.md)。保留浅床点的0.6 s检查已通过，当前仅准入并运行 **ψ=0°、完整撤墙后3 s**；另外两组已准备配置，但入口会在调用任何工具之前拒绝启动。正常求解或后处理结束不是论文精度验收。

**复用本机原r2 GPU 10 s认证弹性PRE，不重新计算预载。** 保持完整目录 `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out`，三个GPU包装BAT均固定该源；本轮没有新PRELOAD或CPU入口。认证的是受限弹性状态承接，不是任意塑性PART重启。

|接收组|正式格式XML|GPU BAT|状态|
|---|---|---|---|
|ψ=0°|[配置](CaseLianSaturatedColumnCollapse_psi0_shared_r5_Def.xml)|[入口](xCaseLianSaturatedColumnCollapse_psi0_shared_r5_win64_GPU.bat)|单组3 s诊断已启动|
|ψ=+2.5°|[配置](CaseLianSaturatedColumnCollapse_psi2p5_shared_r5_Def.xml)|[入口](xCaseLianSaturatedColumnCollapse_psi2p5_shared_r5_win64_GPU.bat)|已准备，待独立准入|
|ψ=−5°|[配置](CaseLianSaturatedColumnCollapse_psim5_shared_r5_Def.xml)|[入口](xCaseLianSaturatedColumnCollapse_psim5_shared_r5_win64_GPU.bat)|已准备，待独立准入|

双击已准入BAT，流程为Python/工具预检→源schedule检查→GenCase→唯一接收求解→原生审查→分别导出Fluid/Bound→PNG/CSV。程序与工具在 `support/runtime_r5`；Python优先 `D:/anaconda3/python.exe`，否则PATH，需NumPy/Matplotlib，不自动安装。已有同名输出时拒绝求解，不能再次点击以覆盖正在运行或已经完成的数据。

保持dt=2.5 µs、TimeOut=.01 s、事件10 s、TimeMax=13 s，保留实际标量时钟；Part0为撤墙后的首帧而非PRE。采用原材料、Model1/Ck2与自由渗流，AS显式ε=.2/exp2.55，仅释放后开启。撤墙时保留原ID 1800/1852/1904/1956/2008作为NoSlip浅床，实际退休其余255点，活动集合为6805=5000土粒+1805固定点。

NoPen仍为 `FixedPlaneStageProjectionReleaseOnly`、`ReactionClosed=false`：半步投影会影响本步Corrector，但额外接触冲量未同阶段闭合进Darcy。0.6 s已有局部负孔压脉冲及后期负压区，完整3 s需继续分析，不能用短窗或正常退出替代物理验收。依据见 [窗口结论](tests/notes/upl_c08_bedkeep_window_result_r1.md)。

输出为 `CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out`。成功后自动生成300帧 `particles/PartFluid_####.vtk`（5000土粒）、`PartBound_####.vtk`（1805固定点），不生成PartAll。正式图与同名CSV在 `figures/collapse_psi0_r5`；总孔压与原生超孔压分开，后者是相对固定材料P0的差值，不冒充当前静水场差或论文中唯一的超孔压定义。VTK显示位置为float，原生double位置/应力另保留；κ是标量塑性历史。

求解正常完成而后处理失败时，只修复派生步骤，并在原BAT后加 `--postprocess --unattended`，不重算求解。成功且绑定一致的native/VTK调用会复用，失败partial保留；图形修复采用新目录。细节见 [后处理说明](support/README_postprocess_lian_collapse_r5.md)。

旧r3/r4输入、runtime、失败输出和原PRE继续用于对照与复现，不作为当前r5运行入口。历史说明见 [r4记录](README_server_r4.md)；更早归档见 [清单](tests/notes/retired_root_inputs_r4.manifest.json)。旧ZIP是历史快照，不能证明r5部署。Git保存代码/配置/必要图表，原始BI4、PRE、程序及源码ZIP另在本地保留。许可证见 [LICENSE](LICENSE)。
