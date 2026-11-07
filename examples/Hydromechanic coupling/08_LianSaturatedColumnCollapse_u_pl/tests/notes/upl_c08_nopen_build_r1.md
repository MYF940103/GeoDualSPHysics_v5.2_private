# C08 NoPen隔离诊断构建（author-only）

新增 `support/upl_c08_nopen_build_r1.py` 与本说明；目前未prepare/build/evaluate，也未启动程序、求解器、reader或queue。生产worktree、正式XML/BAT、runtime和旧对象全部不改。

目的仅隔离现有 legacy NoPen 位置/速度投影对C08撤墙后的影响；其反力与J/孔压/Darcy一致性未闭合，不正式发布、不物理验收、不加half。唯一物理试验将使用AS0，仅改变NoPen，准确CLI必须 `-mdbc_freeslip:1`（不带`:1`的旧`-mdbc_freeslip`会覆盖XML并关闭NoPen）。本脚本不运行该试验。

## 分阶段、原工程编译

1. `prepare` 读取已通过AS Release build和完整冻结 `outputs/upl_c08_artstress_source_r1/source.zip`，把完整ZIP/原source.json保存至 `outputs/upl_c08_nopen_source_r1/baselineAS_source.*`，仅从原ZIP派生三份CPP overlay：JSph.cpp、JSphCpu.cpp、JSphGpu.cpp；保存可审 `three_files.diff` 和 `overlay.props`。源文件的其余内容/换行保持，无新的force/积分/ledger方程。所有其它worktree源码必须仍与AS捕获stat一致，避免混入未记录实现。
2. 对DebugCPU、GPU Release分别先`evaluate`。通过 `/p:ForceImportBeforeCppTargets=.../overlay.props`，在原权威vcxproj中捕获原三ClCompile项，以Remove/Include transform换为三个overlay路径，逐项保留原子节点metadata（包括JSphGpu在CPU配置的ExcludedFromBuild），只增加原source include目录。原工程/solution不写入。自定义只读target输出原/新三项实际求值metadata；脚本核三项唯一、实际FullPath正确，其余metadata原样，仅AdditionalIncludeDirectories允许加原source路径。evaluate直接调用原vcxproj自定义target，不调用solution不存在的自定义target，也不ClCompile。
3. 根审三file.diff及两配置实际求值报告后，分别`build`。仍调用原solution的 `/t:Build`、原MSVC14.36/CUDA11.7方案，只增加该import/property；BeforeTargets=ClCompile再次输出并核metadata。每配置新无空格 `LOCALAPPDATA/Temp/upl_c08_nopen_r1/{DebugCPU,Release}/int`，新 `outputs/upl_c08_nopen_{DebugCPU,Release}_r1` OutDir，禁PostBuildEvent。对象总数仍CPU87/GPU113。保护canonical bin、runtime_r2/r3、三个已通过AS build程序/对象的stat，不构建到旧目录。

具体overlay改动均按根批准的唯一原文匹配：common container仅给已认证elastic PRE handoff/NoPen/AS0放行；CPU/GPU observer仅相应container+handoff准入；源contract仅对该probe将TMdbc2/NoPen两个源token归一Std/false以匹配原AS0 PRE。**不修改PRE或其合同字符串文件**，不声称NoPen与原源是同算子；其余contract字段全部不改。新增运行日志 `NoPenLegacyProjectionDiagnostic` 和typed元数据 `DynamicNoPenetrationPolicy=LegacyProjectionDiagnostic`、`DynamicNoPenetrationReactionClosed=false`，明确这只是诊断而不是闭合耦合模型。

根全文审后命令（本稿未执行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_nopen_build_r1.py prepare --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_nopen_build_r1.py evaluate --configuration DebugCPU --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_nopen_build_r1.py evaluate --configuration Release --execution-authorized
# 审diff/evaluated items后再各一次build
D:/anaconda3/python.exe -B tests/support/upl_c08_nopen_build_r1.py build --configuration DebugCPU --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_nopen_build_r1.py build --configuration Release --execution-authorized
```

准备/求值/构建各自fresh收据保护，失败不覆盖、不自动重试，不启动solver/half/读器。MSBuild真实wait及Win32退出由已有持句柄primitive封口，含PID/创建/exe/argv/parent；无SHA扫描、无Git或服务器包变更。若metadata求值报告格式/继承与预期不同，停止于纯求值阶段供根离线审查，不擅自忽略差异继续编译。

根审阅后prepare已完成；第一次evaluate在调用任何MSBuild之前因本工具漏定义case路径常量C触发NameError。两配置均未启动MSBuild、未写evaluate收据或任何对象；已补充C=T.parent，源overlay与prepare记录没有改动。此为辅助工具错误，不是求解器或NoPen物理失败。
