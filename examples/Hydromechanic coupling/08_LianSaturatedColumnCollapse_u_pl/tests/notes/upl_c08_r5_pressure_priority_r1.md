# r5 pressure probe r2：排查优先级

只读现有 `logs/upl_c08_r5_pressure_probe_r2.check.json` 与 `figures/upl_c08_r5_pressure_probe_r2_{rows,AS_nonlinear_vs_Jacobian}.csv`。18 receiver均在原完整fluid-only/two-hop范围；本次没有新分析计算、图、reader或solver。新note名先查不存在、精确git ls-files为空。

| 保存态 | direct pressure / Pa/s | pressure→raw Ace→Darcy合成 / Pa/s | 加实际谱非线性AS作用的proxy / Pa/s |
|---|---:|---:|---:|
| 5809, tau .63, FS0, p=−450.667 kPa | +7.39002e9 | −4.70696e9 | −2.24845e9 |
| 4956, tau .64, FS0, p=+1352.125 kPa | −4.94171e10 | −1.85533e10 | −1.85588e10 |
| 4959, tau .64, FS2, p=−437.757 kPa | +6.20208e10 | +5.27309e10 | +5.27309e10 |

所有项都来自**保存几何的冻结谱/算子proxy**，不是实测dp/dt。AS列使用R(p)本身，不是Jacobian乘p；仍保留double eigensolve/float输入与CUDA逐pair舍入差异的原限定。

第一优先是5809：direct项本来恢复负压，raw-pressure Ace经divAce产生−1.20975e10 Pa/s的项，将合成方向翻负；AS非线性作用约+2.45850e9，部分缓和但未翻回。该点此时仍FS0，故FS0→2的转换不是出现此冻结反向作用的必要条件。局部C条件数约1–2.7，也不支持先把问题归于病态逆矩阵。这里值得查实际stage的压力梯度/动量/divAce配套，而不是依据少数负系数或直接删AS。

第二优先是4959的阶段压缩：tau .64仍FS2，但J=.9574086、saved theta=+38.9344/s，−Kw/n*theta为强负源，effective stress也出现强压缩。此时direct与所算压力/Ace合成均恢复负峰；它们不能单独解释该负峰如何生成。4956正峰处direct和合成均为负，也属于“保存态正在恢复峰值”的证据，不能反推先前未保存的半步没有放大。

FS切换仍值得观察，但不能叫唯一原因：5809先在FS0达到负峰，后为FS2；4956到tau .7仍FS0；4959是FS2。现有源码明确切换的lap差为(gp+rho_w*Ace_i) dot lx，真实幅值需实际stage fields而不是全步保存态替代。

若下一步要选择生产修改，**实际stage RHS观测是必要的最小证据补齐**。先限这3个ID及其真实邻域、峰前短段，记录Nstep/Time/预测或校正阶段、当时FS/PosDiv、p/J/theta、总Ace、Darcy的compression/direct lap/divAce/FS-Ace-lx/grad-k链各项与最终rate、p更新前后，以及完成步ponding前后p。首轮无需先拆全部力学核：总Ace及Darcy分项已能核实proxy的翻符号是否真实存在；若仍有缺口，再区分σ、AS、AV贡献。接触投影反力未回馈Ace是既有明确限制，不能用保存22补造。

saved22可给完成几何p/J/σ/速度/FS和上一个force阶段theta，但缺实际C/packed PosCell、总Ace及力分项、R_sigma、pressure rate、半步主状态、ponding前p和接触冲量。故本轮不能证明完整因果、构造完整真实stage Jacobian，或判断“调整哪个参数就能修复”。不建议clip、删除AS、放松有限/饱和守卫、自动新half或继续其他psi；其他psi维持当前hold，由root据阶段证据选择下一有界诊断。
