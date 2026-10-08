# k=1e-4 孔压累计精度对比（完整 Tv=2）

## 正式入口

双击根目录 `xCaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_win64_CPU.bat`。
顺序为 GenCase → CPU Release（4 线程）→ PartVTK → 新旧结果及解析解比较。
需要 `py -3` 可用且安装 numpy、matplotlib。BAT 不回退到 Debug。

新结果保存到 `CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_out`，其中：

- `data`：原生 BI4 粒子结果。
- `particles`：导出的流体 VTK。
- `Run.out`、`Run.csv`：计算日志和统计。

若新输出目录已存在，BAT 会保留数据并退出，不清空任何结果。
已有完整计算结果、但还没有比较图时，可在命令行调用同一 BAT，加 `-postprocess` 完成后处理。
比较脚本不会覆盖同前缀图表；若图表已存在，或后处理失败留下了部分图表，
在已导出完整 VTK 的情况下，使用一个新的 `precision_` 前缀重新比较：

```bat
py -3 support\compare_precision_q0.py --output-prefix precision_q0_k1em4_rerun
```

自动运行可再加 `-nopause`，双击默认在完成/失败时暂停。

正式图表使用根目录 `figures/precision_q0_k1em4_*` 前缀；
历史 `full_validation_q0_*` 图和旧 `full_k1em4_out` 全部保留。
临时短程检查统一放在 `tests/outputs/precision_k1em4_smoke`；
正式运行第 5 帧的早期有限值/粒子数抽查导出放在 `tests/outputs/precision_k1em4_early`；
编译/运行诊断日志放在 `tests/logs`，不放仓库根目录。
`support/precision_q0_k1em4_run.json` 保存本次启动时间、程序及相关源文件 SHA256、
原始输入和历史图表 SHA256；它是启动追溯记录，不代表计算已完成。

## 固定参数与唯一输出调整

- k = 1e-4 m/s，n = 0.3，Kw = 2e8 Pa。
- E = 2e6 Pa，Poisson 比 = 0.3，H = 1 m，dp = 0.01 m。
- 外载 q0 = 10000 Pa，0.01 s 线性加载，0.01 s 开启顶面排水。
- Symplectic，dt = 1e-5 s，CPU 4 线程。
- 原有阻尼、边界、周期设置、Shepard=0 等均沿用原正式 XML。
- M = E(1-nu)/((1+nu)(1-2nu))，cv = k M/(rho_w * 9.81)。
- Tv = cv * max(t-0.01,0)/H^2；TimeMax = 72.8842857142858 s。
- 保留原 TimeOut = 0.182185714285714 s，并按
  `doc/xml_format/_FmtXML_TimeOut.xml` 的 `special/timeout/tout` 规则
  在 TimeMax 增加最终输出帧；原 0–400 帧时序不变，新结果预期 402 帧。

精度补丁随 CPU Release 程序生效，没有额外物理模型 XML 开关。
每步将孔压保存为 float 主值和 float 低位余量，避免微小增量在回写时长期丢失；
本轮未把空间算子、应力、密度等改为双精度体系。

## 对比和解释范围

历史基线：
`CaseTerzaghiConsolidation_q0_PR_full_k1em4_out`，2026-07-08 CPU 4 线程。
历史完整计算 7,288,429 步，约 19,077 s，零排除粒子。
历史最后一帧实际为 t=72.874290 s、Tv≈1.999726，略早于停止时刻；
比较脚本读取 Run.out 中的实际 PartTime，不能以帧号乘 TimeOut 代替。

图表检查平均超孔压、固结度 U、顶层沉降和指定 Tv 的孔压剖面，
同时检查完整粒子数、计算退出码、最终实际时间。
主值孔压使用 PartVTK 输出，与旧图一致；低位余量是累计内部状态，不是新的物理孔压项。
经典 Terzaghi 解析解与有限 Kw、加载阶段、移动几何的 SPH 解仍可能存在模型/离散差异。

本轮先回答“当前补丁版对实际算例是否有明显改善”。
7 月历史程序与当前 fe72537 基础版本之间还存在已有 u-pw 代码变化
（包括 mDBC 邻域孔压处理），因此新旧历史曲线差异不能全部归因于精度补丁，
历史耗时也不能直接解释为补丁加速比。严格因果/效率结论需要同版本有/无补丁配对。

最终数值结果与图表见运行后生成的 `figures/precision_q0_k1em4_*`。

## 2026-09-08 启动验收（不是完整计算结论）

- CPU Release 编译通过：0 警告、0 错误。
- 0.02 s 短程检查正常结束：2000 步、零排除粒子。
- 新旧生成 XML 逐项匹配物理和数值参数，仅终点输出段不同。
- 正式运行于日本时间 17:19:31 开始，RunCode = `zm8tgxmx`。
- 早期 t=0.910930 s（Part_0005）抽查：新旧均有 1000 个土粒子，
  位置、孔压和速度均为有限值。旧平均超孔压 8225.233702 Pa，
  新平均超孔压 8225.227446 Pa；这只是加载后的运行检查，不说明 Tv>1 平台已解决。
- 比较脚本旧=旧自检通过，样图只放在 `tests/figures/precision_selfcheck_20260908_*`，
  图例明确标记同一历史输入，不属于新补丁计算结果。
- 完整验收以新 `Run.out` 的正常结束标记和生成的正式比较报告为准。
