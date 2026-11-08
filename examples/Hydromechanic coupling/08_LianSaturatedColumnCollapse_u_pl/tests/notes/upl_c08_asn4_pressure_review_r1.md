# n4近床真实CPU压力响应的纯离线审查（作者稿，未执行）

仅新增同名 support Python 和本 note。只在 `logs/upl_c08_asn4_pressure_cpu_r1.check.json` 实际 passed 后读取其已封口330 calls/13,530 rates；绑定实际退出、completion及这两CSV的stat，不扫描原BI4/native、源archive/objects/hash，不重复330部件或求解。已有/部分输出前缀拒绝覆盖。

严格 part64 τ≈.65、原41 native IDs/顺序，AS4和AS3各h16/32。每列从真实±两个call构造 `A[row,col]=(rate_plus−rate_minus)/(actual_float_p_plus−actual_float_p_minus)`，保留全部列。actual_rate与五个shadow项分别差分；不以名义2h代替实际float分母，不拟合、不平滑、不丢列。输出6724个(row,col,AS,h)记录，每条带所有矩阵分项/实际分母；无需新NPZ或泛用owner。

命名保持实际内容：compression、LP、defect、divAce、chain；另列actual_full、LP_plus_defect、full_minus_divAce、shadow5。FS2/3的defect本身含ρw Ace_i·Lx；chain同时含gradJ·Gp与ρw gradJ·Ace。因此LP+defect以及full−divAce均**不能称纯静态/纯direct**。仅五个原项加算术残差具有可加关系，其余组合重叠。

每个矩阵报告max/min Re eigenvalue、max|Im|、`(A+A.T)/2`最大特征值、offdiagonal符号/绝对和、diagonal范围及patch常量响应；这是**Euclidean局部压力范数**，不是全状态能量。局部列外土压力扰动固定为0，墙由真实CPU闭合每次正常重建；row sum非零不能冒充全域常压不保持。正/负谱或负offdiagonal都不能单独认定原n4爆发根因。

每AS按h16−h32报告Fro、inf及entry maxabs差异和相对范数，不设置收敛/物理通过阈值。compression理论在这个固定vel/J状态下FD应接近0，但只报告。实际float rate的量化、AS正谱分段和有限h都可影响数值差分；原shadow预算只作实际rate与五项和的算术残差传播诊断，不当作完整FD导数精度预算。

对每AS/h选actual_full最大Re的右特征向量，max|v|规范为1、最大分量相位转正。对**同一个v**计算每项 `Re(v* A_channel v)/(v* v)`；五项加actual_full−shadow5残差与full的sum residual一起导出。不能将各矩阵eigenvalue相减或这些数值变成因果/贡献百分比。modeCSV含41原坐标/实际CPU FS、复mode与各节点modal Rayleigh值。

baseline actual float rate对已通过zero_r2同AS/part64/ID记录floatbits相等数与数值差；差异只保留报告，不新增0ULP物理门。源component已核全部5000FS一致、仅显式p列扰动、主场/时钟不积分；本脚本不自行扩大范围。

输出 `tests/figures/upl_c08_asn4_pressure_review_r1_{matrices,eigenvalues,modes}.csv`、`_summary.json`与两PNG：

- `_spectrum.png`：局部谱和各命名矩阵maxRe，h16/32完整保留，signed symlog仅显示映射（linthresh=1/s），不裁剪特征值。
- `_modes.png`：h32两个AS实际leading mode的41点real/imag空间形状、FS2/3标记及两h各自full leading mode上的五项Rayleigh+残差。空间不插值；mode归一范围[-1,1]不是实际孔压色标。

不构造完整(v,σ,J,p,κ)谱、不线性化CompletedOnly正压投影/时间推进、不宣称GPU原半步重放或物理验收。不预设AS4压力子谱应增长，其他ψ仍不自动准入。2PNG执行后需根视读；作者阶段不伪称QA完成。

根全文审后唯一离线调用：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_pressure_review_r1.py --execution-authorized
```

独立成功check为 `tests/logs/upl_c08_asn4_pressure_review_r1.check.json`；作者只做AST/文本检查，未import/运行新脚本，未solver/build/reader/VTK。
