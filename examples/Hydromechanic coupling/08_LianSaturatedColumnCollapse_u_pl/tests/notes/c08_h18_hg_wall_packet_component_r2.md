r2 compatibility repair: the actual r1 compiler exited0, but removing the original main also removed its global AppInfo, so the linker exited1120. No component ran. This new host main restores the exact frozen original three-argument AppInfo definition/header. It adopts the existing902394-byte fixture without another raw-hex decode. No CUDA object, physical input, threshold or kernel is changed. All r1 partials remain protected.

# C08 原Release核：真实packet的C与常量I反事实组件

completion.json 采用独占写入：文件或同名目录已经存在即拒绝，若首次写入异常留下部分内容，catch 路径不能再次截断或覆盖它。此保护不改变组件查询、物理输入或编译标志。

仅作者阶段，新增support/c08_h18_hg_wall_packet_component_r2.cpp、_build.py和本文。未import输入decoder、打包、构建、运行组件/求解器/reader/VTK或Git/哈希。root完整审阅后分别准入pack/build和一次compute-sanitizer组件运行。没有Debug CUDA、物理solver、PRE、half、其他ψ或自动下一任务。

CPU独立复算使用真实重放异常packet：wall sorted690/native894、B=(4.9,0,−.02)，17个donor的C均正定；主MLS det约.00100002503距原.001门只有2.5e−8，而拟合C的xz行列式约−.02522。由于原GPU fast-math/FMA可能影响门附近分支，CPU复算不能冒称GPU寄存器原因。此组件直接复用实际原Release物理CUDA对象，检验不变几何下改变输入C是否改变拒绝。

## 一套原Release闭包

采用原schema2 Release的113个权威链接对象，去掉原main.obj，保留112个原non-main对象，加一个新host main，仍113对象。The r1 build already decoded the real raw-hex capture once and generated the sealed fixture; its CL passed but its link failed1120 without executing the component. The r2 builder verifies and byte-copies that existing fixture and description. It does not call inputs again, run a review main, or read BI4. Current raw_hex_input_calls=0; the original fixture decode count1 is recorded separately. Original CSV and PosCell.w bits remain unchanged.

新main使用原MSVC14.36 Release host recipe、MT、Zi、fp:precise及冻结原头，只有一次cl.exe和一次link.exe。Zi仅提供host符号，不是Debug物理核。构建后root可通过compute-sanitizer --tool memcheck --leak-check full --target-processes all --error-exitcode 99执行这一个组件；这是原Release核的内存检查，不宣称Debug程序或物理计算。

## 一次原hex解码与严格fixture

builder在独立root准入之后只调用已审c08_h18_hg_wall_fault_review_r1.inputs一次，读取真实失败run/捕获/逐项rawhex CSV。它不运行该review的main、绘图或任何BI4 reader。原CSV保持不变，解码后的数组原字节按原sorted顺序写入fresh fixture.bin；PosCell.w直接保留其float32原位模式，不经过浮点数值重构。

fixture显式逐标量little-endian序列化，无C++ struct padding：

1. 八字节magic为C08WPK1加零；16个uint32依次为version、Np、Npb、NpbOk、Nct、cellfluid、target、typecode_bytes、stage、kernel、axis、simulate2d、periactive、slipmode、cellcode、scelldiv。
2. 原Nstep uint64；nc四个int32、cellzero三个int32、ncells三个uint32。
3. 14个原float32：MassFluid、RhopZero、KernelH、KernelSize2、PosCellSize、Scell、KWend.awen/bwen、Gravity.xyz、水密度、MdbcThreshold、上传dp；五个float64：DomPosMin.xyz、solid0、TimeStep。
4. 11项数组，每项16字节零填充名字、scalar_kind uint32、components uint32、count uint64、payload_bytes uint64及原payload。kind1/2/3/4/5/6分别为u8/u16/u32/i32/f32/f64。次序为Idp、Code、Posxy、Posz、PosCell、Dcell、PoroJ、CorrMat、BoundNormal、BoundMode、FluidCells。

C++严格检查magic/version/dtype/extent/顺序/EOF、原6805/1805/940/608/609/690范围、native894、step2196678和5000fluid身份。fixture.json记录来源、字段顺序、原host时刻、块大小及decoder事实；没有拟合或插值。打包发生在构建任务中一次，组件后续只读取fixture，不再次解析原CSV。

## 两次原stage1查询

每次都重新分配并上传整个真实packet，invalid初值为Np。实际Idp、Code、Posxy/z、PosCell、Dcell、J、C、BoundNormal940、BoundMode940均上传。Idp用于host结果映射，Dcell并非此API的输入，二者不被冒称参与核数学。

真实FluidCells是原beginendcell+cellfluid后的608项。组件分配609前缀padding加608真实项，将前缀初始化但不声称它被捕获，真实表放在+609，DivData其余字段原样。原wall wrapper仅把beginendcell+cellfluid传给stage1核，不访问padding。不得构造指向分配之前的负base指针。

通过原cusph::CteInteractionUp上传零初始化StCteInteraction，并按原ConstantDataUp映射填入此stage实际读取的host参数；其余原源码证明stage1不读取的成员为零。这是host映射的packet重放，不是对旧GPU CTE的直接快照。

只调用原cusph::DynamicPoreWall(stage=1)。原noslip表达式先判stage==0，stage1短路不读取per-MK BoundSlipMode，因此未捕获的该数组传NULL不造成stage1缺口。原Read<1>只读C；velocity、sigma、pressure、theta、ace、tangenvel、derivativevel等未读取参数也明确NULL。GlobalSlip3和实际+Z床法向保持；没有尝试运行stage0或stage2。

A查询使用全部原C，真实CUDA launch/synchronize/复制必须成功，且原aggregate invalid必须为690；否则组件保留失败并不执行B，不调整任何输入位来强行复现。690是数值拒绝标志，不是CUDA runtime错误。

B查询完整reset原packet，仅把5000个fluid donor C赋成3×3常量I，所有fixed C、J、坐标、法向、mask、cell表与其他输入均不变。该I仅是因果反事实，绝不是选择identity作为物理边界修复。结果不要求B“修好”；只记录真实aggregate及目标返回C。如果原A为690、B目标被写且C正定，则说明该目标拒绝依赖C场而非不变几何；如果B仍690，则应继续审几何/J或映射，而非放宽门。

两次各输出940墙的实际native ID、mode、完整before/after C的17位值/rawhex、是否变化及是否等于aggregate invalid。原API只有atomicMin，不能据此列出全部逐墙invalid；其他墙状态未逐个认证。A失败目标的C可能仍为原零/旧值，不是失败拟合C寄存器。组件completion的passed只证明规定的两次安全查询、A复现及输出完成，不证明物理修复、论文精度、能量一致或完整塌陷验收。

## 文件与准入

新程序、fixture、描述JSON、编译依赖与九文件runtime位于tests/outputs/c08_h18_hg_wall_packet_component_r2_build；中间对象位于无空格TEMP/c08_h18_hg_wall_packet_component_r2。真实CL/link调用和检查位于tests/logs同标签。已有partial/完成或输出目录全部保护，不删除、覆盖或重试。

独立root_build_admission需绑定script、component_source、note、source_build=实际opt Release、packet_run=实际host replay、packet_review=已完成纯离线检查、同root线程，并明确pack_and_build_only=true、automatic_component=false、automatic_solver=false。

后续构建形式为python -X utf8 -B tests/support/c08_h18_hg_wall_packet_component_r2_build.py --execution-authorized。构建不运行help或组件。之后只有root单独准入的compute-sanitizer运行，组件参数为fixture.bin和FRESHOUT；其main绝不启动求解器、解码器或下一任务。
