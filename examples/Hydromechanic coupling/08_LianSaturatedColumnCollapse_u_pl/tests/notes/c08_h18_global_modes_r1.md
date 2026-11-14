# C08：原材料格点的全局交替模态（零推进作者阶段）

本阶段仅新增`support/c08_h18_global_modes_r1.cpp`、`support/c08_h18_global_modes_r1_build.py`及本文，没有导入/执行、编译、组件/solver/native调用或Git。当前GPU累计观察进程、程序、归档、PRE、旧失败及正式输入不变。根完整审阅后才分别决定一次build及一次组件；本工具不启动任何后续任务。

目的只补先前两个局部dipole不能回答的信息。局部probe响应不小不能排除交替X列Uz或全局checkerboard；本轮不预先规定near-null阈值，不把G1不共轭直接等同数值bug。

## 原计算与新增代数范围

复用已封存`c08_h18_work_conjugacy_r2.cpp`。原typed22/301读取、Map/Copy/Restore/Roles、原J/n/V/rho/k ledger、原4个实际保存态Parts38/76/92/300、真实time/steps、原AS.3/n2.55/WendlandH1.8/5us资格和全部primary不变门保持。原完整literal force/gradient/Rsigma/theta装配代码块逐byte保留；仍每态只一次原`Interaction_Forces(INTERSTEP_SymCorrector)`，总4次force/Darcy。没有OFF重算、积分、更新材料、撤墙新计算或第二源。

新builder沿已成功late-RHS的86原DebugCPU物理对象、160归档头和真实CL/link配方，只编译新entry并链接87对象。原GPU source archive与这些CPU对象来源仍相同schema2 full ZIP，原物理源和对象不改。旧work_r2完成收据、源native及新增格点输入按必要stat绑定，未重新扫描原始BI4或对象hash。

## 原始坐标格点而非ID排序

材料标签来自保留PRE源已解码`outputs/c08_h18_wend_psi0_pre_r2/native_r1/typed22.bin`的**初始Part0**：读取真实7060-ID/22-array/1001-record header及首record原ID/Posd，要求实际time=0、IDs唯一、坐标有限。只取该初始位置记录，不读取/积分1001段轨迹。

土体2060–7059的实际X、Z唯一坐标集排序后必须分别为100、50且每个X-Z格点恰一个材料ID；相邻间距与dp=.04在预注册`16 FLT_EPSILON*(|a|+|b|+dp)`的初始生成坐标舍入识别内。该门只识别原矩形格点，不修改坐标或物理阈值。随后按**真实坐标匹配每个ID的ix/iz**，不能用当前cell数组次序或`id%Nx`推列。最低X/Z为索引0、正符号；此相位在四保存态固定。

## 七个预先声明场

每个场只在诊断vector中赋值，不写Vel或其他原数组：

1. `altX_Uz`：`u=(0,0,(-1)^ix)`m/s。
2. `altZ_Ux`：`u=((-1)^iz,0,0)`m/s。
3. `checkerXZ_Ux`：`u=((-1)^(ix+iz),0,0)`m/s。
4. `checkerXZ_Uz`：`u=(0,0,(-1)^(ix+iz))`m/s。
5. `translation_xz`：所有soil `u=(1,0,1)`m/s，rigid-translation控制。
6. `affine_expansion_xz`：当前坐标的`u=(x−cx,0,z−cz)/1s`，c为当前V加权soil中心；解析梯度diag(1,0,1)/s。这个平移中心不改变解析梯度，系数不拟合响应。
7. `actual_velocity`：原保存态真实soil速度，仅作同一冻结soil子算子的描述参照。

所有soil donor仍是原actual cell搜索得到的完整有向邻域。虚场不外推墙ghost速度，也不调用新force来实现它。各receiver另按原bound cell范围和raw float距离识别是否存在任意fixed粒子于kernel support；包括可能inactive或重合的墙邻居，保守地排除它们。`no_fixed_neighbors` cohort只含没有这种固定邻居的receiver。不是截掉其soil donor或另切一个局部闭合域。

全soil cohort用于代数描述；对近-null的空间解释优先看`no_fixed_neighbors`，不能将墙邻域的held-zero虚墙误称真实mDBC/NoPen响应。原真实4force仍完整包含墙、AS、AV和原动态孔压；虚字段只考察冻结soil-soil力/导数子算子。NoPenScratch不是实际投影反力，本轮不重构未保存before/after状态。

## 范数、虚功与切面端口

沿旧组件完整stencil取`gij`、当前Vi/Vj及实际Ci；`Ti=float(σeff_i)−p_i I`。每场构造double代数影子：

```
Lraw_i = Σsoil_j Vj (u_j−u_i) ⊗ gij
LC_i = apply_rows(Ci,Lraw_i)
P_I = Σi∈I,j ViVj u_i·(Ti+Tj)gij
Iraw_I = Σi∈I Vi Ti:Lraw_i
IC_I = Σi∈I Vi Ti:LC_i
```

全soil的raw伴随恒等式为`P+Iraw≈0`。对interior receiver子集I，跨到非I soil邻居的切面不能省掉，显式保留：

```
port_I = Σi∈I,j∉I ViVj [u_i·Tj gij + u_j·Ti gij]
P_I+Iraw_I−port_I≈0
```

只对这两个raw恒等式沿旧`Sum.Budget`及`gamma_double(128*directed_edges+128)`绝对项和执行算术门；不会要求`IC`也闭合。G1 gap=`IC−Iraw`单列。全耦合塑性/孔压/时间积分/接触能量不在该恒等式中，Γ非零不能独立证明zero-energy或不稳定。

每cohort输出V加权`||u||`、`||sym Lraw||`、`||sym LC||`、`||tr Lraw||`、`||tr LC||`。梯度或散度范数与速度范数之比单位为**1/m**，不是1/s。若速度范数恰0只标`u_norm_nonzero=false`并打印比值0，不用epsilon替代分母，也不据它验收。另给真实速度对该场的一维V内积投影系数；场在非均匀体积下不保证正交，不能把这些系数称完整模态谱。

affine只报告相对解析sym梯度diag(1,0,1)/s的V加权误差，不新增经验通过阈值。虚散度是上述stress-gradient stencil的trace；原PoroTheta另有`GetKernel_Fac`/double累加路径，二者数学相同但不声称逐bit同一数组。原实际theta重构及其既有预算仍在旧保留输出中检查。

## 输出与限制

唯一新program为`outputs/c08_h18_global_modes_r1_build/C08H18GlobalModesR1.exe`，新build收据`logs/c08_h18_global_modes_r1.build.json`。唯一组件输出`outputs/c08_h18_global_modes_r1`保留旧soil20000/groups40000/walls7220/summary8行，并新增：

- `modes.csv`实际56行：4保存态×7场×2cohort，全部范数、work/端口、预算和affine控制信息。
- `mode_fields.csv`实际140000行：4×7×5000原ID，含初始ix/iz、当前坐标/V、虚u/真实v、interior标志、每ID功、raw/C矩阵/trace/应变平方。不得筛掉不利ID或仅看全域抵消。
- `completion.json`真实计数和格点映射证明；physical_steps/material_steps/new_OFF_windows=0，near_null_threshold_defined=false，physical_acceptance=false。

数据用于比较交替场、smooth affine及实际场的原raw/C响应，以及不同实际时刻/cohort的定量差异。它不是全系统特征值/最小奇异值检验，不包含虚墙反应，不证明或修复张拉团聚，也不新增半步/步长/分辨率/截断或参数试验。失败保留真实首因及新partial，根独立决定后续，绝不自动build、运行或重算。

根独立审阅后的唯一执行前补充：PRE的typed22/layout/clocks/completion必须与已通过的storage-window R2收据中原消费Entry完全绑定，源run的source_native也必须指向同一certificate；不是只取当前文件的新stat。此补充不改变CPP、数值或任何物理门，不作SHA扫描。
