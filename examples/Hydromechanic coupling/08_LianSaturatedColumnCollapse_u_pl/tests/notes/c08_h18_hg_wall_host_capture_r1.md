# C08 动态墙失败：仅 host 异常输入捕获

本轮仅编写 support/c08_h18_hg_wall_host_capture_r1.hpp、support/c08_h18_hg_wall_host_capture_r1_build.py 和本文。未import、prepare、build、运行求解器/reader/VTK/Git或哈希；没有jobs、watcher、queue、新XML或新的类ABI。root完整阅读后分别准入Debug/Release构建。旧full3失败、r1/r2 GPU printf候选、各自回归失败与全部PRE/程序/原生文件保持原样，不能延长旧r2运行。

先前GPU printf仅改失败分支，仍导致Release短回归边界应力约2.72e−11Pa、部分边界J约1e−15以及fluid θ一ULP差异，未通过全字段逐位实施门。p/坐标/速度/κ/HG八行/时钟相同并不能替代其余字段门。因此本版完全不重新编译任何CUDA TU，也不调用新增CUDA helper。它只在原GPU已经失败、host取得invalid之后捕获真实输入。

## 唯一补丁与构建范围

实际opt链接中JSphGpu_mdbc.cpp是独立JSphGpu_mdbc.obj，并非被JSphGpu.cpp include。本版只从原opt实际冻结树复制该mDBC CPP，新增一个私有header include，并在原owned且invalid小于Np分支的原Log->Printf之后、原Run_Exceptioon之前调用c08wallhost::TryCapture。原拒绝语句和正常路径全部字节通过逆向删除新增include/call恢复；不修改Gpu.cpp、GpuSingle.cpp、任何GPU TU或旧源码。

重编译一个原mDBC host对象，保留110个其他原对象及全部三个opt私有host/HG对象，共114对象。特别保留全部原CUDA对象；没有NVCC、CUDA模块、GPU printf、物理核、缓存material producer/consumer重编译。MSVC14.36权威原CL.command.1.tlog中mDBC CPP块及原实际CL工具为唯一recipe，原Debug/Release的fp:precise、优化、宏等保留；只变动源/include闭包、obj/PDB及输出路径。一次配置只有一次真实cl.exe调用和一次link.exe调用，均由原实际句柄helper封存。

私有输出为tests/outputs/c08_h18_hg_wall_host_capture_r1_<Configuration>_source/与对应_build/，无空格中间目录为TEMP/c08_h18_hg_wall_host_capture_r1/<Configuration>。完整原opt冻结源按原字节复制，只替换mDBC CPP、增加私有HPP；source.zip/diff/capture记录实际来源。旧程序、对象、PRE及runtime stat保持绑定，不扫描SHA、不以编译通过代替运行验证。

每个构建需独立logs/c08_h18_hg_wall_host_capture_r1_<Configuration>.root_build_admission.json：authorized、allowed_stage、configuration、本script/header/note stat、原opt source_build stat、当前root thread，以及build_only=true、automatic_solver=false、automatic_reader=false。不存在覆盖、自动重试或构建后自动help/求解/解码。MSVC环境键统一大写，PATH显式选择原实际CL所在目录，要求解析到同一cl.exe；没有更改编译器版本。

## 捕获内容与写出

唯一调用严格在真实GPU拒绝之后执行，正常路径不分配、不D2H、不写文件。helper为noexcept，所有捕获/IO异常均尽力记录并返回，原Run_Exceptioon仍执行；捕获失败不得掩盖原异常或改写求解器失败。使用既有fun::Mkdir API，只有返回0的新建独占DirOut/WallFaultCaptureHostR1/才允许写入。目录已存在或其他错误只报告失败，不覆盖、不删除、不自动重试，不引入Windows宏头。

每项数组独立CSV，逐项记录分配、cudaMemcpy返回码、复制与写入状态；复制失败不输出假零。整项失败或schema不完整保留partial。对应schema.json的schema=1、policy=HostExceptionOnlyWallInputs、capture_complete/capture_error与copies清单明确实际状态。每个浮点分量同时写17位十进制和值的raw hex：float用memcpy到uint32并写8位，double到uint64并写16位，不使用hexfloat；PosCell.w必须使用原位模式解析，不能因其编码浮点外观做有限数筛选。路径、错误文字等JSON字符串均转义。

| CSV数组 | 实际复制范围 | 内容 |
| --- | --- | --- |
| Idp、Code | Np | 原真实native ID、实际typecode宽度，CSV行号为当前sorted slot |
| Posxy、Posz、PosCell、Dcell | Np | double坐标、float4 cell编码及原cell代码 |
| PoroJ、CorrMat | Np | 当前真实J及九个double矩阵输入分量 |
| BoundNormal、BoundMode | NpbOk | 只复制保证有效的边界区，不假设分配长度为Np |
| FluidCells | Nct | 实际beginendcell+DivData.cellfluid起始的fluid区int2，不含bound或特殊cells |

Nct=nc.w*nc.z，其中nc.w必须等于nc.x*nc.y；先检查正维度、MGDIV_Z、scelldiv、stride及u64乘法溢出，再检查原unsigned/size_t范围、cellfluid=Nct+1与指针。只复制有源码定义保证的Nct项fluid表，不猜完整分配的2*Nct+5或SizeNct。离线必须先验证InitCte范围和ParticleRange表索引，再验证每个真实begin/end在[0,Np]和次序后使用。table CSV下标已是fluid局部下标，不再加cellfluid。

metadata记录Np/Npb/NpbOk、stage、invalid slot、实际Nstep uint64和原日志uint32值、TimeStep raw bits、原Preg指针存在情况及完整DivData逐字段值。另按ConstantDataUp原映射记录实际class参数的值/位：质量、ρ0、H/KernelSize2/PosCellSize/Scell、KWend.awen/bwen、坐标域、cellcode/axis、Dp、重力、孔隙率/水密度、原solid0表达式、MdbcThreshold及kernel/slip/维度/周期标志。这是host绑定参数，不是对GPU CTE设备符号的直接快照。

这些是新重放真实失败子阶段的输入数组，不是提交态native，不是恢复旧未保存故障，也不是GPU寄存器M/拟合C的dump。stage1失败墙的拟合C在corrmat[p1]=m前已return，故捕获该slot的C可能尚未写入、为零或旧值；metadata明确注明。fluid donor C是该失败阶段真正输入，可以在离线独立重算M/C、参与、最近点/重试和边界奇偶映射，但结果必须称独立复算，不能冒充原GPU实际寄存器结果或忽略浮点/遍历差别。本字段集仅完整针对stage1输入问题，未包含p/P0/ρ/κ等其他场。

## 后续单独准入

构建命令为python -X utf8 -B tests/support/c08_h18_hg_wall_host_capture_r1_build.py --configuration Debug|Release --execution-authorized。原VS工程和CLI不修改。新程序仍须两帧实际Debug memcheck与四帧6001步Release全22数组/真实时钟/layout/signed/HG/快照一致性验证；这些是实施回归，不新增物理half链。通过后root再独立决定一次有限重放、捕获解析和新native partial检查。正常退出、完整捕获或离线复算都不等于物理修复/精度验收，任何阶段不自动启动PRE、其他ψ、VTK或下一任务。
