# 另外两ψ正式 native/post profile 的最小补齐计划

仅只读准备；本说明是唯一新文件。没有改正式根、程序、运行时或活动n4依赖，没有构建/GenCase/solver/reader。n4仍是运行中的诊断，尚未选定或验收；下文AS指数记作“根最终选定值”，不能先写死n4。现r6只有ψ0 XML/BAT、reader和post；两ψ留存r5模板仍为AS.2/n2.55且被launcher锁定，不能绕锁直接发包。

## 固定材料与共享源

|选择器|cp/Pa|ψ0/degree|DilationDecay(sf)|其余|
|---|---:|---:|---:|---|
|psi2p5|5000|+2.5|.2|cr1000、ncoh5、phi=phi_r25、n_phi0|
|psim5|7500|−5|.2|同上|

源仍是原r2 GPU `Part_1000.bi4`，不重新求解10s。`JGravityPreloadState.h:117–121`以 sourcecoh<=targetcoh 检查，因此5000→5000/7500都允许；`JSph.cpp:GetGravityPreloadContract`保留相同弹性/水力/核/边界/AV/预载/法向条件，cp/ψ/sf不是组间相等条件。现有loader分别接纳专用认证legacy MR1 ElasticV1或unified law2 PRE，接收帧须law2；这是特定弹性交接，绝不开放generic PartBegin。source κ严格0、真实ElasticSource认证、未退休/完整事件步/真实时钟、P0/全部原ID和22状态等原门不变。h15失败partial和h12 .52s短控制无完整PRE资格，不能用作源或fallback。

不启用FOS额外减强。fresh/custom-handoff的PartBegin保持0，`SOILPARTBEGIN && usesoftening`不触发；不要为表达“不减强”将合同内的默认SoilTriggerFos1.65改成1而破坏旧PRE兼容。

## 一份新native适配器，复用现有数值core

建议未来仅新增一个两组formal utility CPP及对应build/note，沿用 `upl_c08_n3_formal_native_r1.cpp` + `_build.py` 的六个封口BI4 utility对象和一份生成core；不复制解码循环、不链接JSph、不改旧reader。CLI仍为 `--read GROUP GPU DATA PRE 5200000 FRESHOUT`，GROUP严格限上表两个值。profile与AS常量须在根选定参数后才冻结。

需改的单组假设有明确位置：

- `upl_c08_plane_native_r1.cpp:wmain`第44行的psi0-only/targetCoh5000/sf0声明，在**新生成core**中换成两项固定profile表。targetCoh用于原certified.Load，sf用于第61行逐帧DilationDecay float-bits门；不能只放开CLI而漏改sf0。
- `upl_c08_bedkeep_formal_native_r1_build.py:derive_core`已提供300帧/global5200000/cadence4000/6805-IDs的数值不变基础。新builder只派生组选择、stage、formal_material_groups_admitted和选定AS CSV token，保留反向归一化/小diff审阅。现n3 builder的CORE_REPLACEMENTS不能误用于最终选定的其它指数。
- 新adapter沿现formal `wmain` lazy-header扫描：300帧各核keep5/retire255、AS ReleaseOnly/active/.2f/选定指数、CompletedOnly两实验ponding键均缺失。原core已有目标law2门，沿用它并将profile的目标sf改为.2f，由原每帧检查执行；不重复增加解码/检查链。原始数组仍只由core解码一次，PRE仍只加载一次。
- completion/metadata显式写实际group、profile期望cp/ψ/sf、source law1或2与target law2、300/5200000/4000。cp和ψ并非现有PART中的材料数值字段：只能称profile期望值，由实际执行XML/owner绑定验证，不能伪称reader从BI4直接读到。现生产只写MaterialLawVersion/DilationDecay；不为补profile新增生产metadata。

所有原22数组、7060原ID域/6805实际/1805固定/5000土、P0、固定marker、rho缓存、Model1-Ck2 ledger、κ有限非负不回退、真实FS/负p、plane/κ/时钟/signed门与容差字面保留；不要求最终κ非零或停止/流动达到某阈值。300帧仍为实际4004000..5200000，首帧不是t0/PRE，不重写实际header或用n*dt代替clock。native的GPU参数仍不自证后端，实际owner/Run.csv证明GPU。

## Post/入口的局部变化

未来新正式版本复用 `support/postprocess_lian_collapse_r6.py`，不动已消费r6文件：

- `GROUPS`加上表两tuple；`validate_input`和`main`去掉psi0-only，改为两组明确白名单。实际generatedXML逐项核cp/ψ/sf及原共同材料、hydro、keep、NoPen、clock；实际argv仍只走custom statefile，不走PartBegin/FOS。`summary`保留唯一AS token的严格分号修复，匹配根选定coef/exp。
- `native(...).done`更新新stage和admitted-groups/group/sf/材料期望绑定，同时保留原全部coverage/安全/预算；不放宽原numeric checks。工具调用和成功复用/失败partial保护沿现invoke，不新增decoder owner或自动重读。
- `bundle`、history及场图解码/数值口径不变；group-aware输出目录、manifest和图标签去掉硬编码psi0。`figures`中psi0专属paper-times面板不能原名硬套两组，按已定位的各组论文时间作显式小profile；不插值/拟合，早停不能一概判错。native excess p−固定P0与total p仍区分。
- `vtk`保持两次独立官方调用：PartFluid5000与PartBound1805，各300帧，同原变量/类型说明，绝不PartAll。保留Python/numpy/matplotlib、C08Native/PartVTK工具预检、fresh拒绝覆盖、postprocess-only及solver/post失败分离。
- 待方案选定后才新建两组正式XML/GPU BAT，并更新新版本launcher/profile许可、README/manifest/runtime closure。只做接收GenCase→solver→native→Fluid/Bound→PNGCSV；先核已认证原GPU PRE，不给两组入口连接PRELOAD。CPU源当前不存在，CPU入口继续拒绝，不以GPU源代替CPU证据。旧ZIP是历史快照，不能声明已更新。

已有共享交接/材料组件和弹性短接收证据可复用，不重跑旧矩阵或追加half链；它们不代替两组带塑性、keep5/固定plane/选定AS的实际轨迹。根全文审新profile、utility build及工具依赖后按组独立准入，正常退出和后处理完成仍不是论文/完整物理验收。本说明不触发这些后续步骤。
