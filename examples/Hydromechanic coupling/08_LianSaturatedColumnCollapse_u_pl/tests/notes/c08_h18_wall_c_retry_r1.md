# C08：有限非正 C 重构的一次原 nearest-source 重试候选

本阶段仅新增 tests/support/c08_h18_wall_c_retry_r1.py 和本文。脚本是纯 bytes 变换 API，无导入副作用、文件读写、CLI apply、构建、组件调用、reader 或 solver。作者阶段没有导入或执行此脚本，没有改公共 CPU/CUDA 源码、原程序、PRE、失败结果或阈值。后续是否应用到新的私有源码、构建以及运行，均由根线程完整审阅和独立准入；原 kernel packet 组件若不支持当前因果判断，不得据此自动应用候选。

本候选是实际数值路径变更，不是输出观察器。GPU helper 需要重新编译，NVCC 的寄存器分配、FMA 和优化变化可能使原有效路径出现末位差异；可逆文本证明不能充当程序逐位无反馈证明，不能把正常退出或 packet 通过称为完整塌陷、论文精度或物理验收。

## 已有证据与候选含义

真实新 replay 异常输入是 stage1、sorted slot690/native894、step2196678、host time10.983389999668779；它不是原失败 solver 未保存数组的恢复，也不是已提交 native 状态。原独立 CPU 复算的首拟合有17 donors，det M≈0.00100002503，虽满足原0.001几何门，但分量式一阶外推得到 det C≈−0.02522，所有 donor 的 C 本身为正定。接近原几何门的 GPU fast-math/FMA 分支仍须通过原 compiled kernel packet 组件确认，不能用 CPU 复算冒充实际 GPU 寄存器。

根线程已单独执行的一次离线反事实保持首 attempt 与 donors 的真实位模式，仍使用原一次 nearest-source 重拟合并回到原镜像 G 评价；第二次24 donors，det M≈0.21706、det C≈2.162256、min eig(sym C)≈1.10979。这只说明存在值得验证的局部候选，不证明全程稳定，也不证明所有边界场均为 SPD。

候选不引入新的第三拟合、centroid、identity、平滑或半径调整；不降低原几何阈值、不取消有限域和正定向检查、不添加 XML 参数、类成员或公共头文件 ABI。

## CPU 的局部提交约定

变换只接受完整原 JSphCpu_mdbc.cpp 字节，并且恰好命中七处原锚点：

1. InterpolateBoundaryGhostFieldT 的原 else write(...) 改为 else if(!write(...))geometryfailed=true。false 只表示尚未提交当前有限非正 C，复用紧随其后的原 geometryfailed 分支及一次 retry。
2. 原 pressure writer、SPR velocity writer、dynamic state writer、matrix writer、acceleration writer 共五个 writer 统一返回 bool。四种非 matrix writer 的原算式和提交顺序均保留，仅在完成后返回 true；SPR 原 inactive early return 也改为 return true，保持该路径无写入的行为。
3. Matrix writer 先按原九分量/原 parity 算式构造局部 m。只在 DynamicPoreWall && Simulate2D && !PeriActive 且有限 detXZ=m11*m33−m13*m31<=0 时返回 false，不写 CorrMatc。其他情况原样写入 m 并返回 true，原逐墙 postguard 完整保留。
4. false 进入原一次 nearest-source 分支；只有原非周期2D、未 retried、全部 nearest 有限且位移非零时重拟合。若已经 retry，沿原 missing++/异常退出，不提交失败 C。CPU 非有限重构分量仍由原 interpolator 直接 missing；非有限 Cdet 不会新增 retry，沿原提交及 postguard 拒绝。J guard 和其他字段安全门保持原样。

这没有改 JSphCpu.h 的模板声明：TWrite 已经是内部模板参数，返回约定仅在上述实现与五个调用端对齐。原 u-pw pressure、非动态 SPR、3D 和周期路径不增加质量重试，但仍需要实程序短回归，不能仅凭算式未改宣布行为相同。

## GPU 的唯一局部变更

变换只接受完整原 JSphGpu_mdbc_ker.cuh 字节，恰好替换 stage1 的原 Cdet 检查/提交三行块。原 moment 累加、邻居顺序、权重、逆矩阵、anchoring、Q C Q、stage0/2 和全部原 geometry-failure retry 分支保持字节原样。

在原 stage1 局部 m 与 determinant 已计算之后，仅 finite(determinant) && determinant<=0 && CTE.simulate2d && !CTE.periactive && !retried 时检查同次原 nearest/nearx/nearz；全部有限且位移非零才执行与原 geometry retry 相同的 gp/fitshift 更新并 continue。原代码在下一 attempt 通过 fitshift 把重拟合仍评价于原 G，不是把物理镜像目标移到 donor。

任何非有限重构分量仍按原位置 hard-fail，非有限 Cdet 没有新 retry，invalid J 仍立即拒绝；原 MLS geometry 分支，包括其原有 moment-det 处理，完整保留。若首次 C质量重试已用掉唯一 retried，后续几何或 C质量失败都不能再试第三次。原最终 !finite(det)||det<=0 hard-fail 和仅成功后 corrmat[p1]=m 保留，因此失败拟合不会先提交墙 C。

## 后续最小验证顺序，尚未执行

1. 先完成当前原 Release compiled-kernel 的真实 packet A原C/B仅fluid C=I 因果组件。A必须重现原invalid690；若不支持当前因果判断，保留失败且不自动 apply 本候选。
2. 另行准入生成两个私有成员及其完整源码/对象闭包，并保留每个成员的逆变换证明。编译 CPU Debug 和必要 GPU candidate；原 CUDA 需重编，不能宣称与旧对象天然逐位相同。
3. 用新 GPU candidate 在同一冻结 packet 上检查原 C。只改变质量重试，不改变真实几何/J/CTE/输入位。保留实际 invalid/全部墙 C，不能只观察目标墙并忽略其他低 slot。
4. 有限 constant/affine SPD 场检查一阶重构与正确镜像；也必须设计并检查原G处目标确实非正 C 的 affine 场，要求重试后仍拒绝，不能把所有非正 C 当作几何问题绕过。
5. 明确检查 already-retried、nearest非有限或零位移、非有限组件/Cdet、invalid J 等拒绝路径；原门和异常保持，不能为了得到通过改变字段或阈值。
6. 有效旧 u-pw/SPR/动态墙及当前材料/HG真实短门，CPU/GPU 有限与原生所有数组/时钟/signed guards；根据编译末位影响报告实际差异。没有新的物理 half 链或自动其他 ψ。
7. 以上实施与安全证据完整后，根线程才决定是否准入新标签 full3；不重启或覆盖旧失败、不重算10s PRE、不使用 HG PART restart。

## 纯变换接口与冻结方式

供未来私有 builder 调用的 API 为 transform_cpu(raw)、transform_gpu(raw)，或仅接受两个精确 basename 的 transform_source(filename,raw)。每次要求 bytes 输入、统一原 LF 或 CRLF、每个原锚点恰好一次、每个候选锚点尚不存在；保留 UTF-8 BOM 及完整行尾。按逆序逐项替换回原锚点后，必须恢复全部原 bytes。函数返回 changed_bytes 和 proof，不读写源目录、不生成派生文件、不做 hash 扫描。

本 note 描述的是待验证候选，不修改当前发行版能力和默认值，因而本作者阶段不更新正式 XML 参数文档。只有后续公共集成另行验证后，才同步正式行为说明。
