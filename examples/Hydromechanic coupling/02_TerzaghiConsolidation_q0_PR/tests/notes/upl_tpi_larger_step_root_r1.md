# TPI 大步长路线修正及原小步长长算退役

## 目的与原文定义

原文为 `src/papers/PDF/Lian 2023 u-pl.pdf`，第7–9页 Eq.(29)–(42)，第12–13页1D放大步长比较。
Eq.(30)去掉特定储水项 n/Kw；Eq.(38)–(39)以 p_j^n+alpha*(p_j^n-p_j^(n-1)) 近似邻居新孔压。
Eq.(40)要求 dt<=min(dt_s,R*dt_l)，dt_l 是原显式水力参考界，R是按渗透率、分辨率及精度验证的放大量。
论文5/10us约为其显式水力步长的17/35倍，不是当前材料的可直接采用值。
论文也明确继续放大步长会降低精度或不稳定；alpha=1的历史外推不能当作已求解的全局隐式系统。

当前私有B为M0 alpha=.5、保留Symplectic力学兼容的单次leading-LP更新，非逐项复现论文LF，也非二阶或无条件稳定。
原同dt短窗已完成必要实现对照，但把同小dt完整计算放在大步长策略之前，不能完成本次效率目标；现修正顺序。

## 当前实际限制与最低必要修改

旧dt=6.250143051147461us。初始有限Kw声速界约6.376503us，水力扩散界约47.660318us。
所以只将水力界乘R，仍被旧的含Kw声速限制。
新的私有host-only策略仅对已显式启用的B/C生效；A以及无policy路径保留原逻辑。
物理Kw不改零；只在M0时步估计调用中取kw=0以评估当前J/rho的骨架波速。
实际force、Vmax、ViscDt、HG及原有其他必要界保留。
第一轮R_h=1，先验证约10us和有条件的20us，无须预先宣称R>1已通过。
原含Kw声速界仍记录作诊断，不再伪称新B同时满足它。
静态/动态k物理、人工黏性、HG、阻尼、边界、加载/排水均不借此次修改调参。

原tD=.010000228881835938s不变。候选dt=tD/1000、tD/500，保持固定步长与事件整数网格。
实际时钟必须逐步binary64 +=dt；不得用n*dt代替、吸附/改写事件时钟或历史记录。

## 最小验证顺序

1. 独立新私有源码/程序，核对A不进入新分支和CUDA/类ABI闭包。
2. 一次真实A保存态控制，B Debug短窗/必要GPU memcheck，方法专用时步和signed dterror实测证据。
3. 一次B约10us、约2s窗口，覆盖启动、排水与1.5–2s列间模态；全部native IDs/22 typed arrays/clock/ledger/drain/HG门保留。
4. 对实际保存时刻作压力/固定材料顶底沉降/应力Q/J/n/rho/100层交替X模态诊断和未拟合的合适理论对照。
   不把跨dt/跨模型差异当作5Pa half误差，不插值制造精确配对，不新增half/细步reference链。
5. 只有结果支持才评估约20us，再按精度和实际每物理秒耗时选择新完整2Tv步长。
   若失败，查时间层/耦合误差；不靠提高阻尼、调HG或beta掩盖。

## 原小步长B全程的真实退役

tag=`upl_tpi_gpu_Release_B_full2tv_r1`。
`logs/<tag>.timestep_retirement_r1.request.json` 与 `.result.json` 为实际审计。
核定原owner PID38740和原GPU PID41920后，保留原句柄，先停止owner、后停止solver。
两者实际Win32退出3221225786是本次外部有意终止码，不是正常solver退出或原LASTEXITCODE。
旧run/call最终收据没有被伪造；所有部分BI4和原source/program/input留在原位。
最后原console PART行不完整；Run.out最后报告Part1352/time13.113375/steps2098092只作原样报告，不能推断未保存停止态。
1353个BI4文件的存在不等于1353帧均已完整原生验收。
原owner、通知和求解器均已退役，绝不恢复/重启/重新布防。

保留部分计算可在另行审阅的独立prefix profile下离线提取实际已保存2s数据，不能伪作完整全程run或重写原1682计划。
当前C08原暂停owner/solver保持原状；没有为了本轮恢复它们。

## 当前状态

本文是路线和审计记录，不是新程序、10us或完整2Tv验收。
新策略和大步长结果以各自真实prepare/build/run/native/physical收据为准。
不新增公共XML参数，不提前发布正式发行包。

## 已实际完成的构建与短资格（原生审查仍待完成）

CPU/GPU source prepare r2均passed；公共源码和原CUDA/AV方程不改。
GPU Debug/Release build r2各为2host+109保留对象，实际两CL及link均出口0。
CPU Debug build r3为2host+84保留对象，实际两CL及link均出口0。
CPU r1 C2065及r2 tlog空格源尾解析造成的依赖后检查失败均保留，不写成通过。
新HG额外reference在基类不可读取，r2明确available=false/DBL_MAX sentinel；原derived HG硬门保留。

真实GPU Acontrol原dt320步/18帧正常；新GPU B10us Debug2步/2帧、memcheck0；
新CPU B10us Debug200步/18帧正常。都尚待唯一原生读取/实现审查，不是2s/精度验收。
GPU两步实际selected min47.6603178813us、skeleton wave+AV min100.542521354us，
legacy Kw wave仍6.37650335209us；新dt10.0002288818us确实没有沿用旧声速硬界。
此时R_h=1，尚未证明R_h>1或任意更大dt可用。

纯代数r2已完成120 nominal模式、360矩阵/1440根，三个dt的模型放大根均未超过1。
它没有真实边界/HG/AV/current-J全谱，不能替代实际短窗稳定/精度。
原r1代数检查因1-m消减失败；r2仅稳定等价检查式修复，原map及预算不变，旧失败保留。
