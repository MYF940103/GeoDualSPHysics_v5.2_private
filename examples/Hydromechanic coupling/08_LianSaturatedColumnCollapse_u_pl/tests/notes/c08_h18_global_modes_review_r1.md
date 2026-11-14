# C08 全局交替场零推进结果的离线审阅 r1

本轮仅消费已经执行一次并通过的 `c08_h18_global_modes_r1` 与保留的 `c08_h18_work_conjugacy_r2`。新增一个离线 Python 脚本及本说明；不构建、运行组件、求解器、原生读取器或 GPU。根线程全文审读并单独准入后才可执行：

```powershell
D:/anaconda3/python.exe -B tests/support/c08_h18_global_modes_review_r1.py --execution-authorized
```

## 输入和不变证据

输入为原 `logs/c08_h18_global_modes_r1.check.json` 绑定的真实 call、DebugCPU build、program、completion 及六份 CSV。要求真实 Popen/Win32 均退出 0、owner/child/argv 对应、四次原 force、零个推进/材料步、四个保存态 Part38/76/92/300；真实 completed step 分别为2076001/2152001/2184001/2600000。这里不生成新的 call 或 reader，不补造未保存阶段。

逐块比较新旧 `soil.csv`、`groups.csv`、`walls.csv`、`summary.csv` 全部字节，保留两份原 receipt 的文件身份，分别核20000/40000/7220/8行。该证明仅表示四份诊断 CSV 与原零推进组件输出一致；原组件还检查了可见 primary 字段不变。不得把这些 CSV 当全部22原生数组的逐字节证明。`FSsaved` 与新重建的 `FSfresh` 不增加相等门。只核必要的 size/mtime 绑定，不重新扫描旧对象、源码或 BI4 的 SHA。

`modes.csv` 必须有精确32列表头及56行，即四态×七场×两receiver cohort。组件已经执行全5000 IDs、字面force/应力率/theta及模式覆盖门；本轮直接使用该有效收据，不建立第二套140000行数值检验。完整 `mode_fields.csv`（44列、140000行）仍保留并绑定原stat，供需要时追溯每个material ID、原格点相位及场值；本脚本不重算其邻域、矩阵或范数。

沿用56条组件既定 raw 虚功门 `abs(P+Iraw−cut_port) <= arithmetic_budget`，不提高预算，也不要求 G1 gap 为零。离线还核 `IC−Iraw` 和原残差的字面 double 算术，不新加数值/物理容限。模式norm、div和投影直接使用原组件已经封存的值。

## 三图与三份匹配 CSV

写入全新 `tests/figures/c08_h18_global_modes_review_r1`，已有完整或失败目录均拒绝覆盖；检查收据为 `tests/logs/c08_h18_global_modes_review_r1.check.json`。

- `response.png/csv`：四种全局交替场在 all-soil/no-fixed-neighbor 两cohort的 raw/C 对称梯度和散度响应；CSV32行保留全部原mode信息及真实 tau。
- `controls.png/csv`：解析 affine expansion 与 rigid translation 控制，CSV16行。affine 对称梯度参考 `diag(1,0,1)/s`；平移仅是soil-soil差分的代数控制，不是移动墙计算。
- `projections.png/csv`：实际保存速度对四交替场的有符号单场投影，CSV32行并列相同cohort的实际速度范数及实际 raw/C 响应。上图symlog线性区为无量纲 `1e-7`，只影响显示；下图采用速度范数对数轴。它们不是模态能量。

横轴用原 `summary.csv` 的真实 `tau_s=time_s−actual_release_time`，不以名义Part或 `n*dt` 替换。四个保存态之间连接线只是可读性连线，不是新积分或完整时间历史。raw虚散度为原stress-gradient stencil的trace，不宣称与另一路PoroTheta逐bit相同。

若当前二维V按每单位厚度面积计，`||u||_V` 单位为m²/s；`||sym L||_V` 与 affine error 为m/s；二者比值为1/m。投影字面为 `sum(V v·u)/sum(V |u|²)`；v和u均以m/s表示，原比例为无量纲。对交替场若再乘其约定的1m/s基幅，可得到数值相同的等效速度系数，但本图/CSV只报告原无量纲比例。cohort排除了fixed邻居的receiver，但保留完整soil donor；其cut-port不删掉。

## 解释边界

已有结果提示 interior `altX_Uz` 的 corrected 梯度/速度范数约由3.37增至4.08 1/m，affine参考约1.11降至1.01 1/m，实际有符号投影比例约0.00354降至1.1e−6。最终定量值必须取本轮真实CSV和检查收据，说明中的约数不参与任何门或拟合。

有限梯度响应不支持把这几个场直接称为精确零能模态；前次两个局部dipole并非近null也不能排除所有全局模式。这里没有预先设定 near-null 经验阈值，没有完整特征值/最小奇异值分析，也没有完整墙/接触/Darcy/塑性/时间离散的谱。冻结应力虚功和G1 gap只是条件性soil子算子诊断，不能单独证明代码错误或张拉团聚的因果。各场在当前非均匀V权重下不保证正交，单场投影不能相加解释为完整能谱。

因此本轮不支持直接全体更换矫正矩阵、盲目打开HG，或重试曾失败的旧 residual-viscosity。团聚的持续历程仍需与正在进行的独立压力storage累计观察相互核对；本脚本不触及其活动依赖，也不自动启动任何后续物理计算。
