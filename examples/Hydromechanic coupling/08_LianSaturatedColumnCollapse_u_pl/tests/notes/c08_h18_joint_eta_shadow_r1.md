# C08 joint场四种压力权重的纯离线归因 r1

仅新增 `support/c08_h18_joint_eta_shadow_r1.py` 和本note，作者未import/运行分析、组件、求解器、原生读取、构建、Git或SHA。根必须全文审阅后独立准入唯一离线执行。无polyfit、参数拟合、新几何、物理轨迹、半步链或算子选择验收。

## 已封输入与常数闭合

消费已通过的 `logs/c08_h18_joint_darcy_probe_r1.check.json` 所绑定的60000条manufactured记录、5700条active wall记录及原两条selected clock。原scope为original P29/P30，H/N/X三场，各real_wall/analytic_ghost两种输入，共12组；每组全部5000土ID和475个真实active wall，不删FS、侧壁、角点或badID。所有60000土数据先与两条原clock核对，保留原part/time/completed-step。输入保护采用现有check.files的size/mtime，过程末再次核对；没有把新stat当旧证据。原program/call/build/completion及source archive绑定沿用已过收据。

常数不是从误差反拟合或Run.out的六位小数猜测。实际call锁定原AS03生成seed XML；该XML仍须匹配原完成run的input_xml stat。冻结 `outputs/c08_preload_schema2_source_r1/full_source.zip` 内：

- `JSph.cpp:718–732` 从 `case.execution.constants` 读h/rhop0/massfluid并各castfloat；dp和data2d保持其原类型。
- `ConfigConstants1:1717–1753` 先double h=已float的KernelH，KernelSize=f32(2h)，KernelSize2=f32(KernelSize²)，Eta2=f32((h*.1)²)，并写入CSP。
- `FunSphKernel.h:191–221` 二维 bwen=f32(-2.7852/(h*h*h))，Fac以float顺序计算 `rad=sqrt(f32(rr²)); qq=rad/h; t=1.f-.5f*qq; bwen*qq*t*t*t/rad`。
- `DualSphDef.h:132` 的ALMOSTZERO为1e-18f。V0=double(f32(MassFluid))/double(f32(RhopZero))，不能替换为dp²。

脚本对上述原source片段和实际2D/Wendland设置作封闭检查。实际h=.072f、mass=3.316f、rho0=2072.5f、Kw=1e9f、rho_w=1000f、Ck=2及当前自由渗出/非旧drainage配置保持原样。Run.out仅当前post-pass配置交叉检查，另记当前stat，不冒称退出时已有该stat。h/bwen/Eta2均由binary32后再promote的原公式形成，不转换成高精度“改良核”。

## 同邻居重建及预算

每part仅造一次几何候选表。SciPy KDTree检索半径带一个浮点安全superset，以避免候选查找漏掉边界点；**真正接受仍严格用原double r²、ALMOSTZERO及KernelSize2**，不放大物理支持域。所有group都核各receiver真实fluid/fixed donor计数，坐标及ID域必须相符。实际2D的d_y=0；当前C与所有wall J、p、Ace均来自各自真实group，不用native-J矩阵替代。

原Assemble在不同cell顺序逐项累计，离线采用明确顺序的数组操作/求和，因此不宣称逐位原序或CPU/GPU bit proof。实际Fac用NumPy binary32逐操作重建，并为原float求值形成事先的区间：输入float(rr²)向上下各扩一ULP，必须足以覆盖Gamma8-double距离舍入；sqrt、除h、1−.5q、四次乘法与除rad依次作binary32 roundoff区间传播。此区间不改变算子值，仅形成绝对Fac误差界；无从观测误差反推容差。不会在q接近2时使用失效的相对Fac误差假设，也不把原可能极小符号强行裁正。

区间半宽传播到Ci*g/Cj*g、weight、LP/Lx/Gp/Da/GJ各pair；double单项操作采用Gamma计数（16/32/64覆盖乘加、两边表达及分母舍入），每receiver再加两次Gamma(n+1)*sum(abs(term))覆盖原顺序和离线顺序的累计差。所有预算为输入量级和操作计数的前向误差界；没有5Pa或新增物理门。误差大于预算则保留首组/ID/量，不放宽、不重新计算物理场。

原pair-C/Eta先在12组、全部60000 receiver上核对导出的LP、Lx、Gp、Da、GJ及完整lap/chain/literal rate；每个新离线前向算术预算比都必须<=1，不替换或放宽旧joint字面门。LP+Taylor的双线性误差、Da误差和变k链误差继续传播到rate。wall J−1的真实小量照实保留，绝不强制J=1、删掉GJ/chain或把整个k模型关掉。旧source对actual field的逐bit证明由已过joint组件提供；本次只是独立离线有预算的重建。

## 四个固定数据变体

令d=xi−xj，g=Fac*d，Gi=Ci*g，Gj=Cj*g，Vj=V0Jj。对完全相同的真实邻居，固定比较：

| 标签 | 压力weight |
|---|---|
| pair_C_eta | Vj*d·(Gi+Gj)/(r²+Eta2)，原始anchor |
| pair_C_bare | Vj*d·(Gi+Gj)/r² |
| receiver_C_eta | 2Vj*d·Gi/(r²+Eta2) |
| receiver_C_bare | 2Vj*d·Gi/r² |

最后一项是所审Lian二维Hessian trace的receiver-C/bare标量候选；不重新造全tensor，也不宣称实现了完整论文时间积分/压力边界或精确constant-J论文场。这里仍共享实际wall近1的J、Ci/Cj、FS、Gp/Da/chain，标签是 **changed pressure weight only at the same actual J/C/FS**。

每个变体一起改变LP和Lx，不单改LP。定义dw=w_variant−w_original，deltaLP=sum(dw*(pi−pj))，deltaLx=sum(dw*d)，则

\[
\delta\mathrm{lap}=\delta LP-Gp\cdot\delta Lx\quad(\mathrm{interior}),
\]
\[
\delta\mathrm{lap}=\delta LP+\rho_w A_i\cdot\delta Lx\quad(\mathrm{raw\ FS}).
\]

使用实际导出Gp/Ai和原FS分支。Da和chain不变，deltaRate=(Kw/n)*(ki/gamma_ref)*deltaLap。shadow rate以原导出的double literal rate为anchor加该delta；原pair_C_eta的delta定义为零。这个anchor避免离线不同求和顺序造成的无关小差被伪装为新权重效果。delta也有单独算术误差预算；不回写原Rate，不运行新API或材料更新。

delta列单位：deltaLP、deltaLap为Pa/m²；deltaLx各分量及其norm为1/m；deltaRate、原/shadow rate及rate算术预算为Pa/s；Cplane condition和预算比无量纲。小表同名mean/RMS/absmax沿用该量单位。δ始终是variant减original，不是误差真值。

常量/affine、quadratic及cubic的抵消需分别理解：N约1.36%残差与Eta分母特征相容，但只有实际dw分解才可归因。Ci各向异性、Cj变化、Gp误差、非对称高阶矩、float输入和ghost闭合仍可留下残差。某variant在这两个冻结几何上rate更接近0，不是动态稳定或collapse修复证明；原Eta0物理失败仍保留，不能重标成功。real/analytic RMS接近也不自动排除ghost贡献，逐ID差由另一个joint科学review保留。

## 输出、限制与一次执行

新独占本地 `outputs/c08_h18_joint_eta_shadow_r1/per_ID_weights.csv` 保留12×5000×4=240000条receiver/variant记录：真实ID/time/FS/原cohort、坐标、实际plane condition、原rate/shadow/delta、deltaLP/Lx/lap及算术预算。该可再生大表留本地，不是建议上传Git的raw替代品。

紧凑派生位于 `tests/figures`：

- `_metrics.csv`：12×4×3=144行，all5000、既有legal_flat_bed、既有interior_no_wall的count、condition、原/新rate及delta的signed mean/RMS/max、deltaLP/Lx和预算；不按新误差选cohort。零样本仍保留N/A，condition未定义不夹值。
- `_reconciliation.csv`：12组、八种重建量的新离线前向算术预算最大比。
- `_rates.png`：H/N/X×all/bed/interior的四weight RMS，保留两个part与两oracle。
- `_deltas.png`：bed/interior的changed−original signed mean和RMS；symlog保留符号及零，刻度稀疏。所有小表含图中数值，原全部ID行留本地。
- `logs/c08_h18_joint_eta_shadow_r1.check.json`：真实输入/常数推导、重建与数据变体范围、文件stat。通过只表示analysis_complete，physical_acceptance=false，visual_QA待根检查。

根全文审阅后才可唯一运行：

`D:/anaconda3/python.exe -B tests/support/c08_h18_joint_eta_shadow_r1.py --execution-authorized`

同tag已有完整/partial就拒绝；失败只保留新派生与首因，不重跑组件/读取器/物理算例。全域X的side/FS不兼容多项式物理IBVP，只能描述，不能取其RMS改善来宣称平床或整体修复。本资产不启动任何源码改动、压力裁剪、Q翻号、TPI、其它ψ或正式轨迹。
