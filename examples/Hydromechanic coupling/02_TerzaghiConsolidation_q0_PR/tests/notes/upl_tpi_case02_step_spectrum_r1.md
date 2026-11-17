# C02 TPI B 候选步长：仅代数的 nominal interior 谱筛查作者稿

仅新增 `support/upl_tpi_case02_step_spectrum_r1.py` 及本note。作者不执行；不import或重跑
任何旧24/32组件，不调用求解器、读取器、构建、Git、hash，也不触碰活动或暂停owner。
根完整阅读后，最多一次独立代数准入。数学产物不证明实际SPH全谱稳定或物理精度。

## 真实C02参数与三个dt

从既有 `configs/upl_bigstep_c625_r1.xml` 读E2MPa、nu.3、rho2100、rhow1000、
k1e-4、Kw2e8、n.3、dp.01、h.018、H1和X周期width.1。按实际JSph.cpp3753–54的
all-float初始化顺序重放K/G，再用原动态步长代码的double `Mc=K+4G/3`；
XML理论Mc和实际loaded Mc分别记录，不用旧Fourier例子的29.6MPa材料。
k/h也保留实际float加载；gamma沿原动态实现 rhow*9.80665，而不是改成理论绘图g9.81。
该float replay只涉及初始化标量，不冒称CUDA整条指令或物理状态重放。

三个代数dt固定为：

1. 原dt=tD/1600=6.250143051147461us；
2. tD/1000=10.00022888183594us，原步长1.6倍；
3. tD/500=20.00045776367188us，原步长3.2倍。

不改原tD=.010000228881835938s；这些只是未来事件可整步对应的候选，不生成owner时钟或输入。
不采用论文R35、Kw/(nMc)或固定2tau作为步长判据。

## μ来自核符号，而不是任意取值

当前GPU rate代码的leading LP权重为

`w_ij=Vj*d_ij·[(Ci+Cj)*gradW_ij]/(r²+Eta²)`，`S=-k*sum(w_ij)`。

仅在**无限均匀、J1、对称内域、Ci=Cj=cI**的条件下，Wendland梯度的共同系数
`bwen/h`、V、c可解析约去。对当前36个邻居，令

`t_r=(1-r/(2h))^3`，`D=sum(r_z²*t_r)`，
`a_r=2*t_r*r²/[(r²+Eta²)*D] > 0`。

a的单位为1/m²，它就是该nominal corrected positive-LP的系数；Eta²沿
JSph.cpp1661为float((double(KernelH)*.1)^2)。当前h/dp=1.8产生36邻居，支持半径2h
小于X周期半宽，故这个内域符号没有多重周期镜像。

对指定几何波向量 q_geo=(qx,qz)，

`ell=sum[a_r*(1-cos(q_geo·r))]`，`mu=1-ell/sum(a_r)`，
`q_eff=sqrt(ell)`。

ell单位1/m²，mu无量纲。原P1 map使用**共同符号q_eff**而非悄悄用q_geo²替代LP：

`S_P1=k*q_eff²/(1-mu)=k*sum(a_r)`，单位1/(m*s)；Rgamma单位Pa/(m*s)，故Rgamma/S单位Pa。

这个等式只证明nominal内部口径；浮点消去的条件数和差值另报，不把q_eff称作实际
momentum/divergence/Da共同特征值。Wendland的归一化形状用double解析计算，
未声称逐bit复现GPU float/fast-math。既有P3实际核符号证明过固定邻居的矩量偏差，
不允许据其另一材料/无墙/全周期的单模式结果冒称当前实际全谱。

120个q向量固定为：

- 100个postdrain连续参照模式 qx0、qz=(j+.5)pi/H，j=0..99，来自底不排水、顶排水的
  解析模态，均在dp.01的几何Nyquist范围内；并不把这些当成实际墙矩阵的特征向量。
- X周期10列的五个非零模式qx=2pi*i/.1、qz0，i=1..5，最后一个是交替X列。
  它们仅内域probe，不声称qz0满足全局顶Dirichlet。
- 上述五个qx各与j=0/49/99的qz组合，共15个内域纵向probe。

不任意扫mu=.2/.8或把[-1,1]当实际全算子谱包络。实际closed startup的均匀载荷/压力约束、
q0 gauge、墙/自由表面、Taylor/Neumann项都仍有明确缺口。

## 原P1完整四状态更新

状态为(sigma',v,p,p_previous)，B alpha=.5且机械half=.5、beta0。
新稿把原 `upl_tpi_time_layers_r1.py::step` **函数体原样复制到仅改变物性闭包的函数中**；
运行时只读AST逐句对照，绝不import或执行旧组件入口。仍是：

1. 用pn计算机械predictor；
2. half压力用pn+.5(pn-previous)，完成机械full；
3. endpoint以同一邻压预测估计加速度/完整连续M0项；
4. 一次leading-LP pressure修正；成功后previous成为pn。

每个q对三个dt构造完整4x4 map，共360矩阵、1440根，所有历史/物理根均保存。
参考是相同common-symbol q_eff的独立连续M0两根；根匹配仅作诊断，不丢掉其余根，
不把连续参考或正谱半径结果冒充实际SPH。

实际C02初态的M0连续松弛tau=k*(rho-rhow)/gamma约11.2169us；骨架和M0耦合波速分别
sqrt(Mc/rho)、sqrt(Mc/(rho-rhow))。原P1已证明该单次方案一般一阶；
压力滞后系数 m/[2(1-m)] 随空间行变化，m=rhow/rho+(1-rhow/rho)*mu。
本组件记录dt/tau及该系数，不把2tau加成运行硬门。

`passed`只检查核正权/对称、ell/S量纲算术、完整map线性/h0一致性、4根特征残差及覆盖数。
各dt的谱半径>1数量/最大值如实报告，不以改容差救稳定，不因此自动通过或中止物理任务。
真实Kr/Ks/Ksigma/Ka不同符号、边界/Taylor/Neumann/pressure-to-acceleration项、HG/AV、
当前J、force限制等均未被本common-symbol模型证明。后续M0时步策略必须继续保留这些原门，
候选仍需原授权的实际短窗与精度审查，不能据此直接放大正式2Tv。

## 唯一新输出与准入

未来只写 `tests/outputs/upl_tpi_case02_step_spectrum_r1/` 下
neighbors.csv、nominal_modes.csv、matrices.csv、roots.csv、summary.json，
及 `tests/logs/upl_tpi_case02_step_spectrum_r1.check.json`。
任一既有目录/收据包括partial即拒绝，不重跑/覆盖。

根准入stage=`upl_tpi_case02_step_spectrum_r1.admission`，passed/algebra_only=true，
inputs stat绑定本script/note、XML、P1script/note和当前full2Tv冻结目录内
JSph.cpp、JSphGpu_ker.cu、FunSphKernel_iker.h、upl_tpi_gpu_r1.h；不扫整树SHA。
仅全读之后用 `python -B .../upl_tpi_case02_step_spectrum_r1.py --execution-authorized --admission ROOT_JSON`。
作者稿没有被执行，也没有任何solver、native、half、reference或自动后续作业。
