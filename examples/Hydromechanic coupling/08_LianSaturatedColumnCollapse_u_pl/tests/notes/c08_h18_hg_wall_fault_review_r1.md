# C08 真实重放异常输入：独立墙面重算（作者稿）

仅新增 `support/c08_h18_hg_wall_fault_review_r1.py` 和本文。不执行、不import新脚本，不读未来不存在的数据，不构建、求解、解码BI4、VTK、Git或SHA扫描。root需完整审阅新脚本和未来实际capture后，才可独立执行一次 `D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_wall_fault_review_r1.py --execution-authorized`。已有成功或partial输出均拒绝覆盖/重试。

唯一预期输入为真实 `c08_h18_hg_wall_host_replay_GPU_r1.run.json` 指向的 `WallFaultCaptureHostR1/schema.json` 及11份CSV，只有实际有所有权的求解器退出1和完整schema1/HostExceptionOnlyWallInputs才解析。schema同r1头文件，r2仅修Windows max宏和标签，不改捕获字段。实际来源是**新重放在异常后捕获的数组**，不是旧运行未保存状态的恢复，不是committed native，也没有GPU失败M或fittedC寄存器值。

浮点主身份由memcpy得到的uint32/uint64 IEEE整数hex字串解码，保留sign/NaN位；17digit decimal只交叉核对有限值的位或非有限类别。整数CSV为无损十进制字，不经float转换。校验实际dtype/sizeof/count/逐行sorted_slot或fluid_table_index、实际完整6805 IDs及np/npb/npbok边界。**数组始终保持真实sorted顺序**，只在核ID集合时对ID副本排序。

11份实际捕获为Idp/Code/Posxy/Posz/PosCell/Dcell/PoroJ/CorrMat（Np）、BoundNormal/BoundMode（NpbOk）及FluidCells（Nct）。NpbOk不硬编码为1805。PosCell.w只按uint32位解，不能当普通float做有限性门。全Np的fixed CorrMat可能未写或陈旧，包含被拒绝墙槽；其数值只记录、不用于物理失败判断。阶段1拟合仅从实际cell遍历内的CODE_IsFluid donor读取J/C。

FluidCells已经是 `beginendcell+cellfluid` 的Nct项副本，索引从0开始，**不得再次加cellfluid**。先核真实nc/nw/Nct/scelldiv/cellzero和非空范围bounds；空cell的begin不消费。查询严格按原JCellSearch_iker::InitCte(double)的截断、axisZ和c3/c2顺序，逐行原ParticleRange合并首末非空cell后按sorted slot访问；不换KDTree、不按ID重排、不删source。物理B参与度另用实际PosCell前三分量及w位码复算原double/float xz/float xyz联合支持，并保持它是独立数值复算，非设备原判据寄存器。

常数来自schema中原始hex的host参数，交叉核对DivData映射；**它们不是直接device CTE快照**。采用实际KWend.awen/bwen、KernelH、KernelSize2、MassFluid/RhopZero，不重新拟合核常数或体积。沿用已审saved-proxy的显式float32 Wendland操作次序，但实际CUDA fast sqrt、division和FMA仍未知。M和9分量C按真实donor遍历次序逐项独立累积，det/inverse用原源码的六项/余因子表达式；这些重算中间量不冒充GPU原寄存器。

先复算原G=B+bn的拟合；仅原geometry条件失败、nearest全部有限且非零移位时，执行**同一次**nearest-source retry，仍回算至原G。原|detM|≥.001、sumW/active及C xz行列式>0保持原样；不新增C失败重试、阈值修正、第三次重心、零阶、identity或删除source。非法donor J和非有限拟合分量按原顺序分别列候选首因；没有参数搜索。

输出独立M、完整拟合C、原门距离、每个实际donor的ID/slot/原C9/J/坐标和独立权重、C对称特征值/方向、anchored系数负值/L1/和。仅对称部分特征值作诊断，原C不对称化或裁剪；方向同时保留谱隙，特征值接近重复时方向不稳定。若原顺序在第一个J非法时已拒绝，donor CSV可以仅有明确空表头，attempt中保留实际非法J的slot/ID和值，不虚构已消费的C。被拒绝墙自身CorrMat输入只保留rawhex并明确未写/陈旧可能，**绝不当作rejected fittedC**。所有分类都标 `independent_*` 和actual_GPU_branch_confirmed=false；接近门限时不能据CPU重算认定设备实际分支。

预期派生仅 `figures/c08_h18_hg_wall_fault_review_r1_{arrays,attempts,donors}.csv`、`_diagnostic.png`、新check JSON。不复制原始数组为另一套大型数据。所有结果均physical_acceptance=false、solver_still_failed=true，旧运行仍失败。包未捕获p/P0/rho/kappa/stress/完整22ledger，不能声称这些安全门通过；原99帧的唯一原生验证属于另外的收据和状态，不由本包升级。
