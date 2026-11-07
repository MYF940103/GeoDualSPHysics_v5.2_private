# Lian 2023 饱和土柱塌陷：当前 r3 入口

当前交付说明见 [README_server_r3.md](README_server_r3.md)。r3 是待完整物理验证的计算包；正常退出、短程兼容和材料组件通过均不等于塌陷精度或地应力平衡验收。

**本机已有真实 GPU r2 PRE 回传。不要再次点击 PRELOAD 入口重跑 10 s。** 保留 `CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out` 全目录。三个根 GPU r3 接收 BAT 已通过显式 `C08_PRELOAD_SOURCE` 绑定该源，运行新版统一材料程序；加载器仍逐项认证旧版弹性 PRE。先完成 `tests` 内短窗及原生审查，再运行独立的完整分支。没有将 r2 数据重命名为 r3，也不使用撤墙后的塑性 PART 重启。

CPU 入口仍要求自己的 r3 CPU 认证源，本轮没有启动它。`support/LianCollapse_upl_win64_r3.zip` 是原冻结服务器快照，不代表本机后续入口更新；本机操作以此 README 和当前根 BAT 为准。

## 最新正式输入：4 XML、8 BAT

- 共享预载：[XML](CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml)、[CPU](xCaseLianSaturatedColumnCollapse_shared_preload_r3_win64_CPU.bat)、[GPU](xCaseLianSaturatedColumnCollapse_shared_preload_r3_win64_GPU.bat)。本机已有 PRE 的续算不重新运行这一源流程。
- ψ=0°：[XML](CaseLianSaturatedColumnCollapse_psi0_shared_r3_Def.xml)、[CPU](xCaseLianSaturatedColumnCollapse_psi0_shared_r3_win64_CPU.bat)、[GPU](xCaseLianSaturatedColumnCollapse_psi0_shared_r3_win64_GPU.bat)。
- ψ=+2.5°：[XML](CaseLianSaturatedColumnCollapse_psi2p5_shared_r3_Def.xml)、[CPU](xCaseLianSaturatedColumnCollapse_psi2p5_shared_r3_win64_CPU.bat)、[GPU](xCaseLianSaturatedColumnCollapse_psi2p5_shared_r3_win64_GPU.bat)。
- ψ=−5°：[XML](CaseLianSaturatedColumnCollapse_psim5_shared_r3_Def.xml)、[CPU](xCaseLianSaturatedColumnCollapse_psim5_shared_r3_win64_CPU.bat)、[GPU](xCaseLianSaturatedColumnCollapse_psim5_shared_r3_win64_GPU.bat)。

源和接收使用同一后端，一次只运行一个目标；已有物理输出保留并拒绝覆盖。现有源目录的 [只读 check BAT](xCheckLianSaturatedColumnCollapse_preload_win64.bat) 不替代原生PRE认证。当前双击入口已接入求解正常后处理：接收执行native→独立PartFluid/PartBound→PNG/CSV；新预载执行原schedule检查后做预载VTK。不会自动启动下一组或重试求解。

完整流程需Python 3、numpy、matplotlib及`support/runtime_r3`中的C08Native/PartVTK；优先`D:/anaconda3/python.exe`，否则用PATH的`python`。依赖检查先于任何GenCase/求解，不自动安装。对已完成输出可运行原入口加`--postprocess --unattended`，两个选项可互换顺序；该模式不GenCase、不求解、不改原BI4，并保留已有后处理记录的保护。现有r2 PRE的两套1001帧particles已完成，无需再次处理。

当前程序采用统一 DP v2；公开 u-pl 塑性范围仍限已审二维固定 φ、DP_PS、Symplectic 容器。5000 土粒子、dp=0.04 m、Cubic、侧壁 FreeSlip/底面 NoSlip、Model1/Ck=2 和自由渗流等具体参数及限制以 r3 说明为准。三组完整撤墙运动和论文对照仍需实际结果审查，不能据短窗放开三维、曲墙、大转动或通用 PART 重启。

## 历史与可恢复归档

旧 r1/r2 根 XML/BAT 已移入 `tests/outputs/retired_root_inputs_r4`，原路径、字节/mtime核对及恢复依赖见 [归档清单](tests/notes/retired_root_inputs_r4.manifest.json)。历史 BAT 需恢复到原根路径使用；旧打包脚本仍可能读取根 r2 Def，不改写其证据路径。

原 README 全文保存在 [历史记录](tests/notes/README_root_history_before_r3_cleanup.md)，其中相对链接按原根目录上下文理解。`support` 内旧 runtime、ZIP、manifest 和源版本记录继续保留，供历史复现；r2 原始输出不移动、不覆盖。许可证见 [LICENSE](LICENSE)。
