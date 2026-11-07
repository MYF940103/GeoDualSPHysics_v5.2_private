# C08 r4正式后处理与原生NoPen策略检查（author-only）

新文件 `C08/support/postprocess_lian_collapse_r4.py`、`tests/support/c08_post_native_r4.cpp`、`_build.py` 及本说明。均机械派生现已通过r3版本；尚未构建/读取/绘图/求解。r3脚本、reader、runtime和历史产物不改。

## 最小差异

原生reader保持CLI `C08Native_win64.exe --read GROUP CPU|GPU DATA CERTIFIED_PRE EXPECTED_GLOBAL_END FRESHOUT`，三组coh/ψ/sf不变。新增明确global4060000（.15秒60000新更新）短窗，原4040000/5200000声明窗口保留。只对撤墙后目标每个实际保存PART追加typed元数据门：text `DynamicNoPenetrationPolicy=LegacyOperatorSplitReleaseOnly`、bool `DynamicNoPenetrationActive=true`、bool `DynamicNoPenetrationReactionClosed=false`。原始22数组、6800IDs、P0、κ/J/n/V/rho/k/FS、scalar+=dt与signed dterror等数值/门原样保持，不增half/物理门。源PRE仍通过既有schema1、legacyMR1/unified2弹性资格读取；**不对源PRE套目标NoPen active门**，不改其合同或坐标。

completion新增真实目标policy/active/closed字段，`reaction_J_Darcy_closed=false`、`same_operator_PRE_contract_claimed=false`、`physical_acceptance=false`。NoPen源0→撤墙后投影1是明确阶段算子变化；现有22数组没有投影反力/冲量/耗功，不能据此声称J/Darcy一致性闭合。

build helper仅从原已封口mdbc_partition ReleaseCPU的6个BI4 utility对象＋冻结头编译新reader，7对象链接，无JSph ABI/求解器/旧对象写入；新build目录 `tests/outputs/c08_post_native_r4_build`、收据 `tests/logs/c08_post_native_r4.build.json`。源PRE原生输入旧头仍兼容；新NoPen值通过JBinaryData typed APIs直接核，不引入新自定义schema。

postprocess沿原CLI：`--check-tools`；`--group psi0|psi2p5|psim5 --outdir ABSOUT --source-pre ABSPRE [--figdir DIR]`。固定独立 `support/runtime_r4` 的新C08Native/PartVTK，r4根输出与figures路径；#RunName/实际RunName.xml/真实Hardware/no exclusions/数据序列门不变，增加4060000端点。collapse实际XML必须显式`NoPenetration=1`，Run.out还须包含实际完整日志：

`Dynamic NoPen: LegacyOperatorSplitReleaseOnly; elastic PRE uses NoPen off, collapse uses the existing corrector velocity/displacement projection; same-stage Darcy reaction is not included.`

preload模式跳过collapse native与NoPen1/active检查，只保持原VTK行为。三collapse材料/来源PRE事件仍逐项核，不因NoPen更新修改。source.json/postprocess_r4.json记录该policy及未闭合范围，native完成检查必须实际是本r4 reader并有上述NoPen声明，不能旧r3工具冒充。

全部帧分别导出 `PartFluid`5000土粒、`PartBound`1800保留固定墙（preload时2060），原变量、`-filexml`、`-threads:1`、实际点数及完成manifest复用规则保持；不导出PartAll。原pressure/settlement/κ/n/k/σ/velocity图CSV和三组共同色标图只更换r4目录，不重写任何BI4。已完成native/VTK可在匹配tool/input绑定时复用，仅派生图允许重绘，失败partial不重跑求解器。

根全文审后才执行：

```powershell
D:/anaconda3/python.exe -B tests/support/c08_post_native_r4_build.py --execution-authorized
# 根安装新reader和工具到独立runtime_r4并通过0.15实际短窗后，再由正式r4 BAT使用postprocess。
D:/anaconda3/python.exe -X utf8 -B support/postprocess_lian_collapse_r4.py --check-tools
```

本阶段不安装runtime、不改正式XML/BAT、不启动工具或solver，不增加长程前缀/half链。CPU/GPU来源仍由真实program/Run绑定证明，reader的backend参数本身不能证明后端。
