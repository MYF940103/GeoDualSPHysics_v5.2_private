# 当前发包状态

**完整ψ0 r3 GPU已中断，最后保存总时刻10.11s，尚未完成3s撤墙。已定位state重构墙点791，并发现土点7010穿底；其他两组不启动。原始输出/PRE保留，tests内的撤墙后人工应力候选待验证，正式runtime和输入未切换。详情见tests/notes/upl_c08_wall_failure_review_r1.md。**

当前使用根目录 r3 正式模板和 `support/runtime_r3` 统一材料程序，操作说明以根 README.md 为准。r1/r2 根入口已可恢复归档；其 runtime、ZIP 和 manifest 保留作历史复现，不再作为当前新塌陷入口。

服务器 r2 GPU 10 s PRE 已回传本机。三个根 GPU r3 接收 BAT 明确读取原 r2 GPU 源，实际加载器仍检查认证弹性合同和完整状态；不重命名数据或重算10 s。先完成 ψ0 撤墙后0.1 s短窗及原生审查，再启动独立完整分支。已有输出继续拒绝覆盖。

当前启动器接入完整双击流程：求解前检查Python 3及numpy/matplotlib和runtime中的C08Native/PartVTK；优先D:/anaconda3/python.exe，否则PATH的python，不自动安装。接收正常退出后执行native→PartFluid→PartBound→PNG/CSV；新PRELOAD正常结束且原schedule检查通过后调用preload后处理（当前为VTK及源完成记录）。后处理短程联调已实际通过；完整物理验收状态不变。

原入口加`--postprocess`只处理已完成输出，绝不GenCase或求解；`--unattended`可与它任意顺序并用。已完成且匹配的后处理可复用，失败或未绑定的部分结果不覆盖。回传r2 PRE的Fluid/Bound各1001帧已完成，不需要重新认领或导出。PartFluid/PartBound分别保存，预载为5000/2060，撤墙后接收为5000/1800；不生成PartAll。官方VTK显示坐标float，原BI4精度保留，κ不是完整塑性应变张量。

现有LianCollapse_upl_win64_r3.zip及其manifest/SHA仍是更新前历史快照，未包含本次入口/后处理更新，不以旧清单证明当前文件。使用新流程需同步当前脚本及所需runtime工具，并安装Python依赖；无须重编物理程序。

已通过四种构建、CPU/GPU源与接收短窗的全部22数组及带符号时钟精确连续性、旧默认回归、三个材料短承接、塑性源拒绝及新路径解压/四份GenCase输入检查。源码及说明见tests/notes/upl_preload_handoff_root_r1.md。

10 s源的正常完成已观测；三组完整塌陷、论文精度及预载平衡的物理验收仍需实际数据。通用塑性/HG/任意 PART 重启仍不在本次范围内。所有旧包、程序和原始结果均保留。
