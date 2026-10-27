# Cryer：现有加载/排水时钟的24步CPU事件冒烟（仅准备）

只准备本标签的 support脚本、配置XML、CPU BAT和本说明，不执行prepare或run，不编译，不修改生产源码、canonical程序、正式输入或旧结果。此事件故意极短，不是物理预加载方案，不检验静力平衡、半步或峰值精度，也不自动准入更长任务。

默认运行脚本只显示help。主代理全读后才可显式 `--prepare` 核验并独占封存新的 inputs；再以 `--run` 执行唯一fresh CPU8轨迹。没有GPU、queue、通知器或时间预算强杀。预计初始化和25帧输出比24步积分本身更耗时，不能因超过20秒擅自改参数或停止。

```powershell
python -B tests/support/cryer_preload_event_r1.py
python -B tests/support/cryer_preload_event_r1.py --prepare
python -B tests/support/cryer_preload_event_r1.py --run
```

## 唯一配置差异

复用已验证 `cryer_grad_fine_r1_c_Def.xml` 的完整球体几何、37173土ID、dp=.0025、材料、q0=10000Pa、raw confinement、grad1、double应力/float孔压、dt=2^-21s、SPR/HG/shifting关闭、CPU8。只改变以下既有参数和相应说明：

- SoilDampingCoef=.00004；已有阻尼仍开启。
- RampTime=8dt=.000003814697265625s。
- DrainageStartTime=16dt=.00000762939453125s，新增显式既有FixedGrid=1。
- TimeMax=24dt=.000011444091796875s，TimeOut=dt，共25个二进制精确时刻。

程序是已验证canonical CPU Release，SHA `dc4e2a1feb2245e5a9c567d1bc1877e774a6b70b1058e805f4c6d61aa063ca9c`。输入绑定沿用CPU fine独立审阅及完成记录，并核实原 `cryer_dt_short_r1.run.json` 内Release build log、相关源码/项目和runtime DLL/config哈希；旧decimal half的拒绝仍保留，不将它当作当前半步准入。不会覆盖或重编译已绑定exe。

## 对应边界条件的显式检查

所有25帧保持原native安全：完整唯一固定ID、有限场、正密度、无排除、弹性、double位置/应力、实际载荷遥测、质量/h不变、机械natural-step和pore-dt、半径<=.0525m。与保留CPU fine Part0核对相同初始材料/位置。

不能套用原始 `inspect()` 的“始终排水/立即满载”假设。本脚本明确按本次输入检查：

- `saved_t<=16dt` 时，FSType2/3表面不要求孔压为0，报告均值、最大绝对值和非零节点数；不强行要求其非零，也不以全零推断必然已被强制排水。
- `saved_t>16dt` 时，FSType2/3必须非空且孔压严格0；没有放松原active-drain门。
- `saved_t=0,dt` 的实际载荷向量严格全0；之后必须有正的向内径向实际力。
- 既有source clock是 `max(0,saved_t-dt)`，推导 `q_expected=q0*min(source_clock/RampTime,1)`。因此第二个非初始保存步才开始载荷，Part9才对应源时钟满载；不能用saved_t曲线误报一个step。

Run.out核实配置q0/ramp/start/fixed-grid和真实CPU8。现canonical native没有逐帧实际q标量metadata，只有实际 `HydroMechLoadAce` 向量；CSV明确区分“由绑定源码和时刻推导的q_expected”与“原生实际力”，不会把推导值冒充独立实测q。除前两帧严格零、后续非零向内外，不宣称完成了独立的全曲线q幅值反演。净矢量力接近0不作满载或平衡证据；同时报告径向力、载荷RMS和几何/原生体积两种外载虚功。

## 文件与失败处理

运行时仅生成本标签 `tests/outputs/cryer_preload_event_r1`、`tests/logs/cryer_preload_event_r1.*` 和 `tests/figures/cryer_preload_event_r1_summary.csv`。启动拒绝已有求解器或保留的新标签结果。batch/solver正常退出后先独占封存completion及所有输出哈希，再做native离线检查；后处理失败不重复物理求解器。仅能终止本次拥有的进程树，不碰旧worker或他人的计算。

本记录未宣称t=16dt达到正确初态。后续真正预加载必须另外检查p/有效应力/总应力/位移/密度及残余速度的连续目标，不能由这次开关冒烟替代。
