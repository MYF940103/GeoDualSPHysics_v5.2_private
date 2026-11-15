# C08 C质量重试：私有 GPU Release 构建候选

仅新增 tests/support/c08_h18_wall_c_retry_GPU_r1_build.py 和本文。作者阶段不导入或执行该 builder，不生成私有源码、fixture、对象或程序，不启动 help、组件、solver、reader、VTK、PRE、其他 ψ 或 half。公共两成员由根线程已经另行应用并封存，此 builder 只消费其真实记录，绝不写公共源码或覆盖任何旧程序、失败、原始 BI4 和源码归档。

## 因果准入与实际数值候选

原 Release compiled-kernel packet 组件的 A原C 得到 aggregate invalid690/native894，B仅5000 fluid C=I 得到 invalid6805，目标 det C≈0.999999999999992；compute-sanitizer 0errors/0leaks。相同几何/J改变 C 后拒绝消失支持当前 C重构方向，但 identity 只是反事实，不是物理修复，也没有记录原失败拟合矩阵寄存器。

根已应用的 c08_h18_wall_c_retry_r1.source.json 绑定两个公共当前文件、两个原始 before、两个私有 candidate、diff、完整逆变换和原 kernel 组件收据。builder 只将这两份已审 candidate overlay 到新的276文件完整源码副本。CPU改动冻结为同一候选来源，本 GPU 任务不编译 CPU；GPU仅 helper JSphGpu_mdbc_ker.cuh 的有限非正 C一次原 nearest-source retry 改变数学路径。参数、正定向门、几何门、非有限字段/J拒绝、最多一次 retry、原G评价和公共 ABI 均按已审变换记录。

这是数值候选，不是 output-only。虽然 JSphGpu_ker.cu 主 TU 全部原 bytes 保留，重新编译其 helper 会影响 NVCC 优化/FMA/寄存器分配，不能宣称所有原有效物理路径天然逐位相同。通过构建也不是短门、完整塌陷或论文精度验收。

## 实际114对象闭包

基线是 logs/c08_h18_hg_wall_host_capture_r2_Release.build.json 的真实 owned link，而非重造 Visual Studio 对象清单。核验该 actual argv、Popen/Win32正常出口、ownership_failure=None，基线114对象唯一且有序，并核对它等于原 optimized114只替换一个 mDBC host对象的清单。

此候选从这114对象仅替换原 JSphGpu_ker.cu.obj；保留113对象，其中109为原 schema2对象、3为已审优化的 GPU host/Single/material-HG CUDA对象、1为 host_exception-only mDBC对象。新物理 CUDA对象1，加回仍114。host capture保留，可在以后实际异常时保存输入；没有重新编译其 host成员、HG Node、材料 producer/consumer 或其他 CUDA对象，没有额外 printf、参数或布局变更。

原CUDA对象通过基线 original_CUDA_objects 的真实 path/stat 绑定；原3个 opt对象通过实际 optimized Release收据绑定。后续组件需要另行链接同一新 CUDA对象和规定的 non-main闭包，不能借用旧或 Debug物理核。此 builder 不替根线程生成或执行组件。

## 完整源码与可逆闭包

从 host-capture r2 的276个 frozen_sources逐文件复制到新 outputs/c08_h18_wall_c_retry_GPU_r1_build/frozen，私有归档位于 outputs/c08_h18_wall_c_retry_GPU_r1_source/source.zip。只有 src/source/JSphCpu_mdbc.cpp 和 JSphGpu_mdbc_ker.cuh 用已审 candidate替代；其他274个源/头 bytes保持。原 JSphGpu_ker.cu 主TU、JSphGpu_mdbc.cpp及host捕获header额外显式比较原 bytes。

两个 candidate 的当前public bytes必须等于根封存candidate；封存before必须等于实际基线frozen成员。按根记录的七处CPU/一处GPU锚点逆序还原，必须逐byte恢复全部before。不会再次调用source transformation或向public目录apply。source.json记录两成员、编译member、未编译CPU来源、inverse proof和全部276源stat。输入、原程序、PRE、runtime及对象只做消费身份检查，无旧BI4或对象SHA扫描。

## 唯一 NVCC 和 link recipe

唯一编译 recipe来自原 schema2 Release真实日志中 JSphGpu_ker.cu 的唯一 NVCC命令。保留原CUDA11.7、sm86、fast-math、静态cudart、宏、优化、ccbin及所有数值标志。只允许换私有source路径、-o、--keep-dir、host /Fd及首个私有include根；不新增设备模块或device-link，不用全工程113TU重编。

沿已审 observer_r2 的环境修复：vcvarsall x64 -vcvars_ver=14.36后统一环境key大写，将原recipe真实 -ccbin HostX86/x64路径放PATH首位，并要求 shutil.which(cl.exe)==该ccbin/cl.exe。保留原HostX86编译器，不以HostX64替换权威recipe，也不改编译标志。移除环境外加 CL/_CL_/NVCC_PREPEND_FLAGS/NVCC_APPEND_FLAGS。NVCC和link均通过已有 m.invoke直接调用并消费各自实际Popen/Win32/创建身份记录；不以wrapper返回代替工具出口。

实际link仅在原有对象顺序上换一个新CUDA对象及4种输出路径，其余库和参数保持原样。九个runtime伙伴按原 bytes独立复制；成功收据记录原/新CUDA对象、113保留对象、原/实际编译与link argv、真实calls、完整来源和未执行component/solver声明。所有输出和call/check使用新标签，任何partial或已完成输出存在时都拒绝重跑；异常保留实际call/首因，不自动重试。

## 根线程后续准入

独立 logs/c08_h18_wall_c_retry_GPU_r1.root_build_admission.json 需包含 authorized=true、configuration=Release、allowed_stage=c08_h18_wall_c_retry_GPU_r1、execution_script与note当前stat、source_build=真实host_capture_r2_Release.build.json、candidate_source=根source.json、root_thread_id=当前原线程、build_only=true、automatic_component=false、automatic_solver=false、automatic_reader=false。

根完整审阅并准入后，构建命令为 D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_wall_c_retry_GPU_r1_build.py --execution-authorized。新对象位于无空格 TEMP/c08_h18_wall_c_retry_GPU_r1/JSphGpu_ker.cu.obj，程序/source冻结位于上述build目录。构建只进行NVCC1次/link1次，无程序调用。

顺序仍是新核 packet/常量与仿射场/拒绝路径组件，再检查必要旧有效case与材料/HG短门，最后根线程才决定新标签物理full3。不得从构建成功直接续算、重启旧full3或重算原10s PRE；也不得因为新末位差异而放宽任何原安全门或宣称物理等价。
