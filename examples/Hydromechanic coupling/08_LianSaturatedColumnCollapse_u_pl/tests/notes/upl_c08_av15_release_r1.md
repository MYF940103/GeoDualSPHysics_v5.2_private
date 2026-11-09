# 认证加载后 AV=.15 的私有构建（作者稿）

本轮只准备私有源码 capture、build脚本与本说明，尚未构建或运行。生产源码、VS项目、默认输入/合同、正式root/runtime及原PRE不改；没有新public XML参数。后续CPU smoke与GPU窗口均须根独立准入，不由本脚本启动。

`outputs/upl_c08_av15_release_r1_source` 从封口 bedkeep 原source.zip派生，含三份私有CPP、`av15_release.patch`、完整private `source.zip` 与stat说明 `source.json`。旧archive保持原样；仅 `JSph.cpp`、`JSphCpuSingle.cpp`、`JSphGpuSingle.cpp` 三个archive成员不同。逐文件撤销插入后与原bytes精确相同，其他archive成员逐byte相同；没有SHA扫描。三份CPP保留原换行，不增加类字段、CUDA代码或接口。

CPU/GPU `RunGravityPreloadRelease` 在实际认证导入、原260 target退休255/保留5及divide/count检查完成并置Released后，要求原handoff/keep5、Artificial AV模式、Visco=.1f且没有ViscoTime，再唯一设置 `Visco=.15f`。原damping/Shepard仍关闭，其他物理项不变。加载前/合同仍取原 .1，不能把XML直接改 .15绕过原PRE合同。新独立log明确 `Private AV: policy=ReleaseOnly input_coefficient=... actual_coefficient=...`；原startup/Run.csv Configuration仍描述认证输入 .1，不能借该文本冒称运行AV仍.1。

实际消费不是 stale CTE：CPU `JSphCpu.cpp:2820/2824` 每次邻域调用读当前Visco及Visco×BoundFactor；GPU `JSphGpuSingle.cpp:652–654` 每stage传同两实际值至原CUDA kernel参数。外层ViscoTime本可再次覆盖，但此私有release明确拒绝它。无需移动原ConstantDataUp或修改CU/索引。AV增强同时可经assembled Ace改变动态Darcy，不是TPI、材料或接触闭合修复。

common `SavePartData` 在 qualified handoff且Released时新增三typed元数据：`DynamicArtificialViscosityPolicy` text=`ReleaseOnly`；`DynamicArtificialViscosityOverrideActive` bool=true；`DynamicArtificialViscosityCoef` float=**实际Visco**。Active指release override，不能把加载前 .1 称AV关闭。只加头值，没有第23数组或target HandoffContract，不修改源认证schema/合同。native adapter由独立作者负责，必须核float `.15f` 而非只看启动文字。

新build脚本复用已审Shepard host overlay的Windows argv解析与typed Popen/Win32 invoke。仅重编common JSph和本backend Single两个host TU：DebugCPU 保留85旧对象+2新=87；GPU Release保留111+2=113（所有原CU对象保留）。每TU沿实际bedkeep CL.command.1.tlog、原MSVC14.36 flags/CRT/宏，归档全部source headers置首，两个sourceDependencies验证类ABI；link沿原tlog仅替换两个对象与新输出路径，无双旧对象。CPU复制原4个runtime文件，GPU复制r6原7个DLL/config，copy2 stat与bytes核同。原program/对象/归档/source/运行时stat前后保护，失败仅留新partial，不重试。

计划产物：`outputs/upl_c08_av15_release_DebugCPU_r1` 和 `outputs/upl_c08_av15_release_Release_r1`，program basename沿各原build；收据为logs同stem `.build.json`，含实际2 CL+1 link、87/113对象与private source/runtime绑定。只有build功能，无GenCase、help、solver、reader、VTK、queue或后续串联。

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_av15_release_r1_build.py --configuration DebugCPU --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_av15_release_r1_build.py --configuration Release --execution-authorized
```

这些是根全文审后可分别调用的命令，本作者任务未执行。AV.15是release-only数值敏感性候选，原necessary dt/FS/J/P0/κ/plane门不变，不是物理验收。
