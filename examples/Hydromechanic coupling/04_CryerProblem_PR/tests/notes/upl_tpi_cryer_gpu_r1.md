# C04 GPU XYZ/HG0 压力时间候选：私有完整源准备

作者稿，只新增四个资产：`support/upl_tpi_cryer_gpu_r1.h`、`.cuh`、`_prepare.py` 与本文。尚未执行 prepare、构建、device fixture、help、solver、native 或 VTK。根线程完整审阅后仅能单独准入一次 source prepare；后续 full111 build和物理 job均须另行准入。

## 完整 C04 基线与来源口径

以已实际通过的 `upl_tpi_cryer_cpu_source_r1.prepare.json` 及 `outputs/upl_tpi_cryer_cpu_r1_source/source_diff.json` 为来源。按265个 source_origins逐项复制原字节，不复制其额外 CPU-private helper，也不采用 CPU两TU TPI overlay。这个基线是253份上游档案＋8份C04 freebody ZIP＋4份明确Git GPU-HG blob的新重建，不追认旧CPU/GPU编译时全部本地源内容。

从同一明确提交 `de2492afb5be33e9077f8e4a96bfe755b0ffc7ed` 只读恢复 GPU `DualSPHysics5Re.sln` 与 `DualSPHysics5Re.vcxproj`。新目录保持 `source/VS/docs` 相对布局。两份原文档和原 source manifest保留，新的 source_diff另写，不覆写旧档。

Debug和Release旧实际GPU tlog/项目闭包分别核对：97 CL＋14 CUDA=111。CUDA中的 `FunctionsGeo3d_iker.h.obj`、`FunctionsMath_iker.h.obj` 保留完整 `.h.obj` 名称，不能按stem误改。旧本地依赖路径必须均在265源集合内；tlog只证明路径，不证明当时所有文件内容。因此下一阶段必须 **全111重新编译**，不采用旧C02或C04对象，不仅替3个旧obj。

新 `outputs/upl_tpi_cryer_gpu_r1_source` 包含265原文件、两个新private helper、两份权威GPU项目、两份原docs/base manifest和新的source_diff。只有原 `JSphGpu.cpp`、`JSphGpuSingle.cpp`、`JSphGpu_ker.cu` 三TU作18处局部挂接；其他262个基线源/头逐字节复制。没有整文件 C02覆盖，没有原头文件/class layout/virtual ABI或公共kernel签名变动，也没有修改HG类或增加getter/第四TU。

## 范围与数学

私有 namespace为 `upl_tpi_cryer_gpu_r1`，仍用进程环境 `UPL_TPI_GPU_R1=A|B|C`。缺省/精确A不进入新数值分支，不分配历史、不创建sidecar、不作额外force；真实A无反馈仍需后续独立native比较，源审查不能代替位证明。

B：`qhalf=qguess=pn+.5*(pn-previous)`；C：`qhalf=qguess=pn`；β=0。只有时间预测和单次 `pnew=float(q+Rγ/S)` 变化。它是single leading-LP defect correction，不是paper literal LF、收敛隐式解、二阶或无条件稳定求解。没有额外迭代或新公共XML参数。

`S=-k Σw` 是leading-LP正预条件，不是完整Jacobian。S和完整double `Rγ=-γθ+k*lap` 从原C04三维动态压力kernel内直接捕获，不从float旧rate反算。原 w、XYZ corrected gradient、Taylor/closed-FS Neumann defect、`ρw*Da`、原η²分母、kernel、力/AV/grad、材料与source-clock ramp/drain全部保留。

原kernel只改为 `template<bool CaptureRows>` 的一份共享空间body，默认A/常规机械阶段false、额外endpoint才true。没有另写第二套Darcy算子。尤其保留原C04公共wrapper末尾的 `bodycentre,bodyradius2` 参数，保留每receiver原 radius/separation有限门及其实际launch参数；不将C02无freebody签名搬来。`JSphGpu_ker.h` 原字节不改。

数学和source/role验证由已测C02 r2 helper定向移植，去掉C02所有只读HG代码。显式RN double add/sub/mul/div和原float转换保留。原CUDA `-use_fast_math`/FTZ策略不改：float↔double与float存储的真实PTX可能采用ftz，不能把RN函数名字当作禁用FTZ；此prepare不改变物理算术来迁就reviewer。后续科学审查必须按真实编译语义核对。

## C04真实资格与生命周期

只允许fresh、非周期、真正XYZ的37181 native（8 fixed＋37173 soil），dt=2^-20，明确NstepsBreak1–128。原TimeMax不设人为`.15`上限；由显式更新数限制短窗。原远端inactive DBC、WendlandH1.8/dp.0025、constant-k1e-5/n0.3/Kw2e8、rho0=2100/rhow1000/E2e6/ν.3/coh1e9、rawFlexibleConfinement q10000/ramp2^-8/drain2^-7、grad1/SPR0/HG0/AS0/AV.1/η4e-5均在实际Init资格检查中固定。

没有从C02引入x-periodic、mDBC、normalized band荷载、HG.1、κ重置、孔压滤波或其他物理设置。原C04 freebody初始化/rest/几何/separation门继续执行。当前128更新仅ramp早期pre-open，不宣称排水后或Mandel峰值精度。

Pre在原PorePress swap后预测；Corr入口先捕真实half pressure/Jhalf/θhalf，原唯一solid/material corrector继续执行；原 `ComputeSymplecticPorosity(true,dt)` 后CaptureJ；原full positions更新后只替pressure guess。主循环原cellDivide之后、原`TimeStep+=stepdt`之前额外一次force/rate与必要dt检查；不重复solid/J/κ/P0更新。

endpoint先按真实native IDs拍core（double2xy+z、float4vel/rho、六double应力、κ、P0、q、J），读器排序不改变ID-owned历史。验证所有row/原七类committed字段后才write；原BC之后两阶段验证再唯一commit/history旋转。若发生失败，保留实际错误/partial，不旋转历史或自动保存rejected状态，不重试。

HG在Init及每endpoint强制对象为null、xi0。删除HG allocations、Stats/RateInfo、D2D HG snapshots、getter、AddHistory和row中h/rate解引用；core七类检查仍全部进行，HG checks恒0。私有owner在base JSphGpu析构原cudaDeviceReset之前幂等释放自有CUDA缓冲和descriptor；static State析构只处理host stream，不碰已reset CUDA，不访问已删HG。

## 独立device夹具与侧车

保留8个source＋8个normal/periodic owner-role制造case；role参数用实际fixed8/total37181/soil首ID8。source门沿用r2：true-drained必须实际+0，nonzero或−0即使等于旧final也不能放行；unconstrained必须保留旧float每bit。fixture用独立真实上传device输入/错误包，不引用物理View/history/force，不增加物理计数。

真正B/C Init后才有一次stdout marker：

```text
UplTpiCryerGpuSourceRoleFixtureR1: source_cases=8 owner_role_cases=8 device_cases_checked=16 device_kernel_completed=true private_error_bits=0
```

它由`fprintf(stdout)`输出，不保证进入Run.out；后续wrapper只能从本次fresh console统计。构建/源码/prepare通过不能宣称device16 case已实际执行，A也不应执行该fixture。

新侧车为 `UplTpiCryerGpuR1.policy.json/.csv/.summary.json`，stage `upl_tpi_cryer_gpu_r1`。CSV沿用已审28列、每保存态37173土体行；native37181/fixed8/soil37173，core checks=`7*37173*N`，HG checks0，actualsource/save clocks与commits独立记录。原native PorePressRate仍为Kw/n缩放的endpoint residual，不是M0实际dp/dt。只在原真正SaveData之后输出sidecar，无虚构pre-update receiver初态。

## prepare准入和后续接口

`stage=upl_tpi_cryer_gpu_r1.prepare_admission,passed=true,prepare_only=true,inputs=[stat...]`。绑定四作者文件、C04 source prepare/manifest、原265源/两docs、原Debug/Release build/call及各CL.read/CudaCompile.read/link.command三tlog、C02冻结r2 h/cuh来源。prepare执行时仅两次明确commit的只读git show恢复项目，无Git写入、hash、build或程序。已有新目录/receipt拒绝；失败保留新partial/首因。

成功receipt：`source_root`含VS/source；`files`为本次复制资产stat；`source_diff`；`changed_sources`三TU；`changed_headers=[]`；`new_private_helpers`两名字；`class_or_header_ABI_changed=false`、`HG_adapters_called=false`、`requires_full_new_111_object_compile=true`、`old_GPU_closure`保留97/14和完整111 basename。diff同样提供 `only_changed_TUs` 和上述关键限制，供作者中的全111 Debug builder使用。

GPU Debug/Release工具、SDK与库选择由旧实际GPUrecipe另行绑定，不能套CPU8.1；后续build/run/native均不由本prepare启动。现C02 GPU、C04 CPU和所有旧source/program/archive/PRE、正式结果与暂停C08依赖均保持原状。
