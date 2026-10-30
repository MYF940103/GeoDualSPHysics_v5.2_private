# 应力率梯度修正短窗与诊断重启

本轮没有修改 C++/CUDA、正式根输入、已有输出或服务器 Cryer。仅在 tests 中验证已有参数与状态交接；下面均不是完整固结或物理验收。

## G1 短窗

唯一数值参数差异为 SoilStressRateGradCorr=1；Shepard 关闭，其余沿用 Stage1 的 k=0、阻尼 .02、mDBC vel=0、材料和积分格式。CPU8、GPU 粗步 1 us、GPU 半步 .5 us 三组均正常完成 2 ms；每组按同实际时刻保存五帧。

| 检查 | 最大孔压 RMS 差 Pa | 最大材料位移差 mm |
| --- | ---: | ---: |
| 同 dt CPU/GPU | .008690737581 | 1.551252278e-8 |
| 独立 GPU 粗/半步 | .034750581176 | 1.273329255e-8 |

原 5 Pa/.005 mm 门限不变。独立核对 15 个新状态和 11 个参考状态；1040 个 ID、38 个原生字段的原安全、p0 和 float32 excess 均通过，2313 个去重文件的大小/SHA 一致。

2 ms 去掉十个钳压顶层粒子后，R=q_native+Mf*trace(sigma)/(3K) 的粒子 RMS 由 G0 GPU 的 38.49694 Pa 降为 G1 GPU .020571 Pa，CPU 为 .021858 Pa。这支持孔压率与应力率使用一致 div 的效果；R 不是孔压理论误差，也不证明 .3 s 平衡或长期沉降已改善。全部 100 层数据保留，没有为计算 R 而删除顶层原生数据。G0 的四个同实际步状态仅作选项描述，不冒充半步门限。

CPU8/GPU 粗步 Simulation Runtime 为 3.815051/5.818453 s，GPU 半步为 11.646623 s；只是短窗实测，不是受控长程速度结论。新的 .3 s G1/ShepardOFF 使用 GPU，保持与保留 G0/ShepardOFF 的同后端单开关比较；不重跑 G0。

## Scenario2 状态交接

仅采用已封存 r2_OFF Part60 作为透明的诊断交接，不将其升级为已验收初态。原实际时间 .3000009999988915 s 单独保存，新阶段时钟重置为零；k 改为 1e-3，初始模式 None 继承 p/p0/应力，Shepard/SPR/HG/梯度修正/symC 保持关闭。

原 Scenario2 的 1 us 固定步长不满足当前配置的扩散预算：生产公式给 dtw=.47676598 us，1 us/dtw=2.097465。FixedDt 不自动截断到 dtw。因此本短检使用 .25 us，不增加 PoreDtSafety；dt/dtw=.524366。源码确认新的正 FixedDt 会在运行前覆盖继承的 SymplecticDtPre，实际首步 .25 us、预测半步 .125 us，未沿用旧 1 us。

CPU8/GPU 两组各 10 步、11 个原生状态，正常退出且无自有残留。每组初态全部 1040 ID 的 16 个持久状态字段逐位继承：位置、速度、rho、六项 double 应力、float p/p0、Kplastic；两组共 33280 个位模式一致。p0 全程固定，原生 excess 严格符合 float32(p-p0)。11 对同实际时刻的最大孔压 RMS 差 .0003547358 Pa，最大材料位移差 8.42708e-13 mm。

mDBC 的 BoundNormal 从 PartExtra60 读取，新旧 Ghost 法向文件 SHA 相同。FSType/FSNormal 是重建的派生字段，不是持久状态：CPU 的 normal_x/z 与原 GPU 参考有差异，最大 .665063；FSType 和当前十个排水顶层未变，GPU 重建结果相同。这一差异已显式记录，不谎称全部 38 个初态字段逐位相同。

适用限制：当前 GPU 重启会把 rho 重置到 RhopZero，CPU/GPU 都会清零 Kplastic。本输入恰好 rho=2100、Kplastic=0，故上述严格交接通过不能推广为任意非均匀密度、塑性或带 HG 历史的精确重启。独立核对 22 个新状态与原 Part60、337 个去重文件的大小/SHA 均通过。

证据为 logs/sw_grad_short_r1.check.json、logs/sw_restart_short_r1.check.json 及各自独立 completion/receipt 和 figures 中完整 CSV。原始 BI4 和程序仍本地保留，不把清单等同于原始数据云备份。新的 G1 .3 s 结束后须检查完整材料剖面、沉降交错和末窗漂移，再决定后续初态和消散验证；本记录不自动批准正式长程。
