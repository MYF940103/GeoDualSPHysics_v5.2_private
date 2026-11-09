# residual-viscosity 失败53帧离线审查（作者稿，未执行）

本稿机械派生已审30/90比较数学，尚未执行。Root 全文审后才可从 C08 根目录运行 `D:/anaconda3/python.exe -B tests/support/upl_c08_rvisc90_partial_review_r1.py --execution-authorized`。原90未来稿及原30成功分析保持冻结。

真实候选为 `upl_c08_rvisc90_GPU_r1`：solver/run 失败1，原计划90/end4360000；只消费通过的 `.partial_native_r1.json`、`native_partial_r1` 的53条，最后 saved step4211999/completed4212000。与 true causal90 前53个实际clock/ID/P0配对，保留90/53真实头。原成功 rvisc30 仍以30真实头及已passed物理history缓存为参照；只消费本次native内已通过的53/30全22/time/layout/signed byte证明，不再读其30条payload。partial sidecar只消费已有106行审查，不循环重验。

原22/6805/5000soil/1805fixed、keep5/退休255、AS总应力.2/n3、CompletedOnly、P0/J/ledger/FS/plane等资格沿原native。signed dterror仍是 **signed≤1e−14**，不取绝对值；本次负值不是新的失败。逐条c.inspect保持实际scalar时钟，τ≈.01–.53，不插值、不造t0；normal Run.csv不作为失败输入的成功证明。

输出history106行、matched53行、全场extrema（含ID/位置），以及固定首对/对照7011/7012/6230/6231与两组全窗p/speed/J/n/k/κ/D极端ID的同材料轨迹。原始payload顺序处理一次，轨迹从小型内存列缓存提取，不二次读取BI4或调用force。history含p/J/n/k相邻保存态差、ON−OFF量；摘要列最剧烈的保存间隔、首次保存近对、全窗极值及.30/.50/.51/.52/.53检查点，不设增长阈值或把首个非零差称物理失稳起点。

saved diffusion 独立描述：按封存 `JSphGpu_ker.cu:1382–1406`、`JSphGpu.cpp:1871–1883`，`D=(Kw/n)*k/(rho_w*9.80665)`，`dt_diff=safety*h*h/maxD`。h/safety/Kw/rho_w从各自actual generated XML先float32后提升double，n/k直接用ledger已通过的原生double；报告53个Dmax/dt_diff/limitingID与其轨迹。它仅为**保存态扩散分量**，不重构wave、k-gradient或总necessary bound，也不声称为实际失败阶段的全步尺度。

三PNG：history分开正峰/RMS与负峰（负峰symlog仅显示，linthresh1kPa不是数值门），简短ON/OFF图例；hydraulic显示J/n/k/D/dt_diff；fields保留.50/.53两组全域与局部p/J视图。局部ROI由此次已读保存极端ID5196/5198/5294/5296/5847/5895/5897/5941的四状态位置并集加2H构造并导出，未用ROI筛选指标。色标始终取四状态全部5000土粒的完整min/max，无平滑或分位裁剪；不输出冗余整域raw spatial大CSV。

mean_dz沿native认证double PRE；top/bottom绝对沉降仍明示旧float-VTK PRE参考，同ID当前double ON−OFF差则参考相消。动能只称当前混合物二次量；NN近对只作描述，不定张拉根因。

异常reported step4212949来自原始错误文本；最后保存实际时钟由native读取。两者之间没有可重构的状态，本稿不推断未保存J/ID/精确失败时间。输出全为新浅层前缀 `figures/upl_c08_rvisc90_partial_review_r1_`（history/matched53/extrema/material_tracks/retained30_context CSV、history/hydraulic/fields PNG），新check为 `logs/upl_c08_rvisc90_partial_review_r1.check.json`。拒覆盖并保留失败部分产物；analysis passed不等于runtime成功、物理验收或后续solver准入。无SHA/新reader/solver/VTK/build/queue。
