# Cryer：较弱 Bui–Fukagawa 阻尼的受控短窗（未启动）

本轮只新增 `tests/support/cryer_damp_short_r1.py`、本说明及
`tests/configs/cryer_damp_short_r1_{c,h}_Def.xml`、
`tests/configs/xcryer_damp_short_r1_{c,h}_win64_GPU.bat`。
不修改正式入口、canonical C++/CUDA、旧输入、结果或清单。
主代理静态审查前不调用脚本；编写完成不代表已 prepare 或已运行。

## 唯一物理差异及范围

以已核验的 `cryer_gpu_grad_fine_r1_c/h` 为同后端、同步长控制，
仅将 `SoilDampingCoef` 从 `0.02` 改为 `0.00004`，仍开启 `SoilDamping`。
这是当前 Bui–Fukagawa 阻尼系数的减弱诊断，也是与文献相同阻尼公式及数值系数的对照。
主文 Fig. 7 给出 ξ=4e-5；补充材料 SI 第1页明确 ξ 无量纲，
`c_d = ξ sqrt(E/(ρ h²))`，与当前源码的阻尼形式一致。
采用相同公式和系数不等于复现整套论文：时间步、粒子布局及加载路径等差异仍须分别核对。
保留原始 raw confinement、grad1、float 孔压、double 应力、
R=.05、dp=.0025、k=1e-5、原材料与初态；SPR/HG/shifting 仍关闭。

- coarse：dt=2^-21 s，1024 步；half：dt=2^-22 s，2048 步。
- 时长 2^-11 s；native 输出间隔 2^-13 s；每组严格 5 帧含 t=0。
- 新输出仅为 `tests/outputs/cryer_damp_short_r1_c/h`。
- 运行记录与 completion 在 `tests/logs`；summary/effects/half CSV 在 `tests/figures`。

## 启动和验收

默认调用只核验 peak 独立 review 的 evidence/safety、GPU fine 已通过的
10 个 cross/5 个 half 及其已封存结果，检查新 XML 仅阻尼值不同、BAT 仅标签不同，
然后以新路径独占创建 `logs/cryer_damp_short_r1.inputs.json`。

```powershell
python -B tests/support/cryer_damp_short_r1.py
# 经主代理检查已封 inputs 后，才允许下列唯一短窗 pair：
python -B tests/support/cryer_damp_short_r1.py --run
```

只拒绝同时存活的 Cryer GPU 求解器；独立 CPU 或无关工作不会被停止。
运行真实 canonical GPU Release BAT，先 coarse 原安全通过才运行 half。
程序退出后先独占封存原生输出/输入/程序哈希的 completion，再检查元数据及 native。
若仅分析失败，只能基于 sealed 结果修复分析，不可重复运行原求解器。

全部帧核验 37173 不变土 IDs、有限/正密度、无排除、弹性、真实 FSType2/3 排水、
双精度位置/应力标志、原机械及孔压自然步长、实际外载、质量/h 不变、半径≤.0525，
实际 binary 时刻及 zero-based saved step 必须准确，不移位、不插值。
coarse/half 全 5 对继续使用原孔压 RMS≤5 Pa、材料位移最大差≤.005 mm，阈值不放松。

同 dt 的 `.00004` 与 `.02` 比较只记录孔压、材料位移、总应力、速度、
密度、外载及排水分类变化；不施加 5 Pa cross gate，不要求 0 ULP，
也不将选项改变认作半步误差或理论误差。
本轮短窗通过不授予峰窗、全程或理论物理验收；无通知器、自动长算或自动 Git 操作。
