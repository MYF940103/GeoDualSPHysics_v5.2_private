# C08 残差黏性固定阶段：纯离线复核与两图

作者态，2026-11-14。仅新增同标签support Python和本说明；不执行/import组件、不构建、force、native、solver、GPU或Git。root须先封存通过的 `c08_h18_rvisc_force_r1.check.json` 并单独准入本离线分析；未通过或部分组件不能使用。新输出 `tests/figures/c08_h18_rvisc_force_review_r1` 和同标签check均排斥旧路径。原组件/失败/PRE/3秒物理数据不改。

脚本只消费原build/actual_call/completion/4个CSV收据，不重复原生读取。要求真实Popen/Win32出口0、所有权正常、2force/6Darcy/4extra/0推进、10000基线及zero-recompute位检查、30000 literal预算通过。两态原5000ID、真实保存clock/Step、两个固定材料对和三个制造场均必须完整，原墙计数、必要5us及alpha*dt*dmax、原机械/制造场budget原样核验。

在现成10000条土体输出上重算R差、5us×差、RMS/max，及mi=ρiVi下的实际float提交力：fi=mi×committed_da。重新累计Σvi·fi、合力范数、y力矩和Σ(nVi/Kw)pi deltaRi。CSV和不同累加顺序的独立算术误差界明确单列，不改变任何原物理预算、不伪造edge能量证明。原budget仍针对原组件已有的累加；不把CSV复核包装成一次新力计算。

输出两张PNG与两个匹配小CSV：

- `summary.png`：两态RMS及max压力率，机械新增功与条件pressure项使用独立纵轴，四个固定对原/候选rddot。图脚注明maxaddedAce、5us/原necessary bound、alpha*dt*dmax及未推进/未验收。
- `space.png`：两态全部5000土体实际位置上的5us×deltaR，统一线性全局min/max colorbar，不平滑、不裁色、不换范围；这不是更新后的孔压。
- `summary.csv`：原两个完整metrics行及重算值/独立算术预算。
- `pairs.csv`：原4行实际距离、rdot、曲率和rddot，保留真实clock，不插值。

root已告知封存组件的混合结果，图表必须展示，不能只强调负机械功：P38 max|R|约10.029→23.080MPa/s、RMS约.3979→.6110MPa/s，两个focus的rddot由+.318→−9.327和+1.891→−.807m/s²，条件下反而更靠拢；P76约9.718→14.594MPa/s、RMS2.568→2.649MPa/s，而两pair的rddot改善。max|5us deltaR|约77.17/73.65Pa，新增机械功约−3876/−3628W/m，原必要界约9us。这些近似摘要由根原组件审查提供，精确量以本次重新核算的CSV为准。

因此机械耗散与原必要步长通过不能证明水力响应或形态改善；本阶段不准入GPU物理窗口。RMS和rddot只描述冻结输入后的原算子响应，不能当新实际轨迹、全耦合谱、张拉团聚修复或其他psi的验收。check完成后仍须root逐图目视审阅；脚本不把保存成功写为已完成视觉验收。
