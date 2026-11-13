# C08 H1.8显式Wendland原生读取适配

只作者 `support/c08_h18_wend_native_r1.cpp`、`_build.py` 和本说明。没有构建、调用程序/help、读取BI4或typed22载荷、解码、求解、VTK、Git、SHA扫描或改变正在运行的Wendland源。旧Cubic工具、源、失败及数据保持原样。根线程完整审阅之后，才可单独构建一次：

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_wend_native_r1_build.py --execution-authorized
```

新程序为 `outputs/c08_h18_wend_native_r1_build/C08H18WendNative_win64.exe`；构建收据为 `logs/c08_h18_wend_native_r1.build.json`。以**实际已经通过的** `c08_h18_plastic_native_r1.build.json` 中六份generated代码为基线，不从尚在发展的工作区重抓取逻辑，也不以旧Cubic profile中的kernel标签给Wendland背书。逐项核基线program/generated/source archive、六个utility对象stat，独立新main加相同六个BI4 utility对象链接，共7对象，无JSph或数值更新对象。原utility归档头与实际schema2物理归档ABI一致后，使用其JGravityPreloadState/FunSoilMaterial头。旧pure22和实际5us标量调度profile正文不变；source/receiver/entry仅作声明过的stage/Kernel CSV与证书kernel身份检查的机械派生，逐替换有唯一锚和逆还原精确文本证明，保留diff。

读取CLI沿用：

```text
C08H18WendNative_win64.exe --source partial|full DATA MATERIAL_CSV COMPLETE_PLAN FRESHOUT
C08H18WendNative_win64.exe --receiver window|formal GROUP DATA PRE COMPLETE_PLAN PROFILE_CSV FRESHOUT
```

source MATERIAL_CSV现在必须恰好15个键：原14个 `group,ModulusE,PRvs,DPCtes,phi,phi_r,n_phi,coh,coh_r,n_coh,dlt,DilationDecay,SoilTriggerFos,fresh_trigger_active` 再加**实际生成XML取出的 `Kernel=2`**。receiver PROFILE_CSV恰好17个键：原16个（上述原14个加AS coefficient/exponent）再加Kernel2。不能传旧Cubic14/16键profile；也不能把文件名或未来source label当kernel证据。当前先供psi0源资格审查；保留原三个固定材料组的未来接口，不能因此自动准入另两组或任何receiver。

event/full source及receiver所读取PRE的typed schema2证书，新增token解析：先精确读取 `gravity-preload-2 gravity-preload-1`，再读取其后**八个实际数值字段**，顺序为CaseNp、CaseNpb、soil数、Dp、H、MassFluid、MassBound、RhopZero；下一项才是unsigned TKernel，必须等于2。前三个计数、几何及参考质量/密度同时与原7060/2060/5000、dp.04/H=.072f等既有范围核对，不能通过在合同字符串里搜数字2作假。其后的材料/历史合同仍交实际engine完整GetContract2与caller的actual XML/CSV绑定校验；本工具**不声称独立重构全部材料合同**。

非event帧本来没有这份certificate，因而只能核CSV里显式Kernel2，不能由H或22数组独立证明它采用Wendland。每次调用的根线程仍须绑定真实源/receiver XML `Kernel=2`、实际Run.out的Wendland配置和拥有者/program/input；partial completion明确报告 `non_event_kernel_identity_proven_by_reader=false`。full/source-PRE completion只声明其实际已解析证书的kernel身份。receiver当前输出本身不独立携带PRE合同，仍明确不能从其数组单独证明目标kernel；实际solver目标合同及XML/Run.out绑定不可省略。

其余原范围不变：bed-last geometry、source7060/2060/5000、phase0、AS/NoPen/keepoff；full必须event2M/1001个真实保存，κ保留实际非负/逐ID非减和fixedκ0，P0/22数组/212B/ledger/cache/FS/标量时钟/signed必要步长预算照旧。future receiver仍使用window2180000/91或formal2600000/301的完整原5列plan，active6805=1805fixed+5000soil、retire1805..2059、keepfalse、AS ReleaseOnly .3/.5/.7及原指数集合；NoPen反力同stage尚未闭合的限制不变。新stage仅为 `c08_h18_wend_native_r1.source/.receiver/.metadata`，source15/receiver17键数如实标出，原工具数值预算未修改。

构建成功不表示源完成、原生资格、平衡、接收连续性或物理精度已通过；本builder也不自动运行读器。若活动Wendland源失败，必须保留失败与partial，不能借full工具认证缺失event源。之后每次唯一解码仍由根线程单独审阅与显式调用；没有新solver/half/other-psi准入，也没有新增材料数组或物理方程。
