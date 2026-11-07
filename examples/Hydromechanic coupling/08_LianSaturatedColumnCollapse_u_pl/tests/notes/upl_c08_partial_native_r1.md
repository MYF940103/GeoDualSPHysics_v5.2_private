# C08 ψ0正式失败的11帧只读诊断（author-only）

新增 `support/upl_c08_partial_native_r1.cpp`、`_build.py`、`_run.py`；尚未构建、解码或运行工具。不改旧读取器、生产源码、成功/失败历史收据、原生BI4/元数据或正式输出。新产物仅在 `tests/outputs/upl_c08_partial_native_r1`（reader程序在同级 `_build`），日志/收据在 `tests/logs`。

原运行 `upl_c08_formal_psi0_r1` 已封口：真实GenCase0、wrapper1、GPU solver1，ownership_errors为空；不是post失败、材料status8，也没有Run.csv成功汇总。原Run.out错误是 `ComputeDynamicPoreWallGpu` 的finite saturated first-order mirror fit，最后完整console行仅报告Part0010、10.110000、completed4044000。该六位小数不作为精确原生时间，更不是精确故障时刻。

## 最小差异

CPP机械派生已审 `upl_c08_release_native_r3.cpp`：仅移除成功Run.csv依赖，限定本次psi0/GPU、11个标准原文件；从每个BI4真实读取time/Step/dt/signeddterror，最后必须原savedStep4043999、completed4044000。所有22数组/6800 IDs、P0、κ单调、J/n/V/rho/k、FS和scalar+=dt/1e-14、ledger5e-13等原数学与门原样保留。completion的actual_end_s取最后BI4实际TimeStep，另列scalar replay；明确diagnostic_partial=true/runtime_success_claimed=false/failure_stage_reproduced=false/unsaved_failure_time_known=false。

build只复用同冻结source.zip头和6个Release utility objects（JPartDataBi4、JPartDataHead、JBinaryData、JObject、JException、Functions），无JSph对象、GPU核、求解器或新物理。新reader名C08NativePartial_win64.exe，不安装或覆盖runtime_r3。

owner先核原始failed run/call/status真实exit1和唯一target身份、代码/输入/源PRE stat绑定、11个实际原文件和无Run.csv；绝不把失败数据改成成功运行。一次decode后原始初始 `CfgInit_NormalsGhost.vtk` 按完整字节复制到新诊断目录，源文件只读；该文件由真实初始化输出含double B位置、原Idp、float Normal，是B到镜像点的完整向量（源2060墙，后续筛去已退260）。**不是FSNormal，也不直接把GenCase _Normals当最终运行时mirror向量。** 此处不解析或重构墙fit，留给下一步Python只读几何分析。

同时对保留成功short的前10帧做真实逐字节比较：每record为double actual time +全部22 SoA typed arrays，共1,441,608字节；partial11帧与short10帧的原头分别保留，第三uint计数不改写。signed时钟CSV header及10真实行也逐字节对比，额外第11帧不伪称公共前缀。若前缀不同，原生读取收据与数组保留，标比较失败，不能重跑reader掩盖差异。

## 根线程完整审阅后两条独立命令

从case08根目录：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_partial_native_r1_build.py --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_partial_native_r1_run.py --execution-authorized
```

没有自动接续、half、solver、watcher、通知、重试或清理；使用stat而不扫描SHA。失败或partial output一律保留，不能覆盖。`passed`只表示这11个已保存状态通过原有检查且公共前缀位相同，不代表正式计算成功、完整塌陷验收、精确失败stage重现或已找到根因。

下一步可用导出的typed22和真实NormalsGhost，逐wall ID审B/GP支持、最近距、sumW/submerged、moment det、Jfit及原一次nearest-source retry，区分缺支持、rank不足和J外推越饱和界。saved22不含BoundMode/PosCell/C/Ace，坏状态是未保存力阶段；不得把保存态离线几何重放冒充失败瞬间的GPU分支观测。
