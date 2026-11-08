# n4两态实际CPU零步RHS/墙响应分析

仅新增同名Python及本说明，事前确认新路径不存在且未跟踪。作者只AST/接口静态检查，不import或执行，不更改r1失败或r2通过的任何数据/程序/输入。根全文审阅后一次运行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_zero_review_r1.py --execution-authorized
```

仅消费已通过 `upl_c08_asn4_zero_cpu_r2.check.json`、真实双出口0 call、completion和evaluations/receivers/walls三CSV，并绑定原n4失败run、通过partial66原生检查及clocks。没有BI4/typed读取、解码或新的force调用。必须四次实际评估、6805=1805fixed+5000soil、物理steps=材料return=0和全部5000土primary bits守卫已通过；源solver1继续保持失败身份。

实际输入part29/64（τ≈.30/.65），AS4/3都是**同一n4保存输入**上的新CPU力阶段。每组输出接收点及相关墙ID要一致，接收点x/z/v/p/P0/κ/J/n/ρ/k/savedFS文本同一；真实clock/Step与封口clocks逐条一致。原sum-vs-actual float rate算术预算不变，仅再消费CSV复核：`abs(actual−shadow)<=shadow_budget`。不重算新的C/Ace/FS、核函数或物理RHS。

新浅前缀 `tests/figures/upl_c08_asn4_zero_review_r1_*`：

- `focus_RHS.png`：两态×四个实际focus7013/7015/6963/7014，每一面板比较compression/LP/defect/divAce/chain五项test-side shadow柱与实际CPU float rate菱形点，单位MPa/s。symlog线性区`.01 MPa/s`只为同时看见大项抵消与小净值，不改变任何物理数据/门。
- `diagnostics.png`：输出接收点actual rate AS3−AS4、compression/LP残差比例、原eval全5000最大率与输出接收点最大率、相关墙finished Ace差、C差与全5000 FS数量/相对saved改变数。只对输出接收点extrema给真实ID；全5000 maxabs来自原eval，没有伪造其对应ID。
- 五份配套CSV：`receivers`保留原数据并增加抵消scale/比例、C det/condition及Ace量级；`differences`给同输入AS3−4各项及C/Ace；`walls`保留两次墙p/J/σ/C/Ace和真实normal/slip/code/bed标志及配对差；`extrema`记录输出接收点六个率字段min/max及ID/位置/状态；`evaluations`四行保留全部原全5000摘要并注明selected/global范围。所有压力原符号保留，C奇异/condition无效只记空值，不另加门。

抵消指标用 `|compression+LP|/(|compression|+|LP|)` 及 `sum|五项|/|actual_rate|`，真实零净率对应后者空值；不剪裁、不拟合。FS changed0应由实际四行eval计算而非硬填；C/p/J墙角色是否同样由表记录。另从实际Cxz/Czx计算 `0.5*(C+C.T)` 的2×2最小特征值，CSV逐点保留、evaluation摘要给selected soil与related wall的最小值和ID；不加正定验收门，不推广到全部墙/所有pair方向。新check写 `logs/upl_c08_asn4_zero_review_r1.check.json`，拒覆盖、结束核必要stat，无SHA。

大compression与LP抵消、defect/divAce随Ace变化仅是此新CPU条件评估的量化事实。AS3不是n3轨迹；保存输入不等于原GPU半步，零步不是原GPU率/未保存失败态重放，也不是压力Jacobian、完整耦合稳定谱或因果证明。反力/J/Darcy闭合、其他ψ和物理验收均不据本分析成立，不自动调用求解器/原生读取器/VTK。
