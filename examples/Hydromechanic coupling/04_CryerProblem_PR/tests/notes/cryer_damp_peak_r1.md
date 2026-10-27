# Cryer：较弱阻尼的 coarse 峰窗诊断（仅准备，尚未启动）

主代理明确准入本轮受控参数敏感性峰窗，不是自动物理或正式验收。
新增 support 脚本 `cryer_damp_peak_r1.py`、本说明及对应 XML/GPU BAT。
原峰窗、短窗和已封清单均不修改。

## 配置与依据

与已完成 `cryer_grad_peak_r1` 完全相同的 R=.05、dp=.0025、k=1e-5、
raw confinement、grad1、材料、初态、double 应力/float 孔压、α=.1、
dt=2^-21 s、结束`.0625 s`、输出间隔2^-11 s、131072步和129帧。
唯一物理改变为 `SoilDampingCoef .02 → .00004`，`SoilDamping`仍开启。
按已核对 SI，ξ无量纲，公式为 `c_d=ξ sqrt(E/(ρh²))`，与当前实现一致；
相同公式/数值系数不等于时间步、粒子布局、加载启动等整套论文复现。

前置证据是 `cryer_grad_peak_review_r1.check.json` 的数值一致性/原安全，
以及 `cryer_damp_short_review_r1.check.json` 的原安全/独立半步通过。
较弱阻尼短窗只有5对已保存样本，不被冒充为整个峰窗半步证明。

## 执行方式与保护

本次仅编写文件。主代理全读脚本后，才实际调用默认 prepare 封新 inputs；
再审查已封 inputs 才启动唯一新 coarse 峰窗：

```powershell
python -B tests/support/cryer_damp_peak_r1.py
python -B tests/support/cryer_damp_peak_r1.py --run
```

默认 prepare 只读核验并封存新输入。`--run`拒绝已有 GPU 求解器和新标签
的任何保留运行/结果；旧worker和通知器不启动、不重置。只使用现有canonical
GPU Release及相同build/runtime，启动隐藏，记录真实硬件和owned退出。
退出后先封独立 completion 及所有输出哈希，再做原生检查；后处理失败只修
新分析，绝不重复执行已经完成的物理求解器。

新输出为 `tests/outputs/cryer_damp_peak_r1`；状态、completion和一次性
回原thread的queue记录在 `tests/logs`；summary/effects CSV在`tests/figures`。
单次终态 queue 消息少于2000字符；不重试、不rearm、无连通性自测。

## 检查与解释

所有129帧检查原inspect安全、37173不变IDs、有限/正密度、无排除、弹性、
真实排水、原机械/孔压自然步长、实际外载、质量/h不变、半径≤.0525及
精确binary时刻/zero-based步号，不放松任何原门。

只在实际共有的两个样本：新Part0/1对弱阻尼短窗coarse的Part0/4，
比较34物理/身份字段0ULP。唯一分开记录的是`dterror_s`输出区间统计；
其两侧原guard仍须通过，不排除任何其他字段，不宣称完整fine prefix。

与原`.02`峰窗全129帧按相同实际time/step比较孔压、总应力、材料位移、
速度、密度、载荷等。两种阻尼不同，effects不是5 Pa后端门/半步误差或理论误差。
全部启动样本保留；全历史采样最大值与预先声明的Tv≥.005窗口峰值分开。
理论为球心点值，native中心为固定18-ID初始球平均，不是同一观察量。

完成后仍须检视图/CSV、加载/应力与时间敏感性，才能另行决定下一步。
本worker不授予峰窗half、全周期或物理验收，也不自动启动正式/更长计算。
