# C02 M0启动/步长偏置的前2s离线对照作者稿

只新增同名support Python和本文。未执行科学脚本、构建、原生读取或求解器，
未调用旧analysis/main、队列、Git或SHA扫描。原source、程序、数据、图表、检查及失败均保留。
根完整读审并给独立offline_only准入后，才可执行一次。

## 三条真实轨迹

- A：已完成旧CPU1/FreeSlip有限Kw，原decoded文件头1682保持不变，只view前1292记录。
  原native/descriptive review passed不等于100Pa物理验收；原超限明确保留。
- B625：原GPU6.25us长算被有意停止，唯一新partial reader/read/review实际通过后，
  只用其1292记录，末点320001/2.0000520265024098s；不把旧full或其后61帧认证完成。
- B10：新的10us199996更新/1263状态，末点2.00000577545594s；原native passed，
  原科学审查analysis_complete=true但top非劣失败仍是失败，不能改写原check。

这三者只作已有前2s观察，不是full2Tv验收。总体primary source保持
`source_full_completed=false`/`partial2s_only=true`；每个source中另外明确A原full完成事实。
不新跑A/B/C、half、20us或reference；不重读BI4、不重解码、不恢复旧worker。

源关联、22schema/IDs/实际clock/Step/原signed门、排水及rho-ledger都继承真实通过的native，
再核本次实际消费记录的身份。A文件头及文件长度仍按1682核，只取前1292；A ledger只读
所选1292000行，不再处理其后全周期数据。B625和B10的导出必须是各自完整prefix，不能吞尾。
三个series固定原1000材料ID和同一100层/10列初始几何。

## 正确参照和原预算

直接复用 `upl_tpi_m0_B10us_review_r1.py` 的未拟合定义：H=1、512模态、E=2e6、
nu=.3、k=1e-4、Kw=2e8、n0=.3、q0=10000Pa及原ramp/tD，参考g=9.81。
A的压力幅值与Cv都乘有限Kw容量；两个B都用M0。每个状态按各自实际时间评估，
材料顶部/底部分别为原z0=.995/.005，预算分母仍为表面S∞=q0H/Mc。
参照是准静态单顶排水伴随，不能当有限ramp、核带外载、惯性、当前J-n启动的精确解。
不拟合H、荷载、时间起点或平台，不补造pre-drain理论值。

Tv=.005/.05分别取三条轨迹各自实际最近保存态，显示各自clock/target差。
沿原计划报告每个B相对A：孔压100层均值剖面RMS误差增量<=10Pa；
顶部绝对误差增量<=.001S∞；底部绝对误差<=.005mm且<=A+.002mm。
同时报告newB-oldB各自适用理论下的误差增量，不为该增量新增验收预算。
每个t>=.1-1e-7状态的原100Pa层总应力及top-gap门完整列出，不用late-only隐藏失败。
科学check.passed仅表示该离线因果对照成功完成；原预算是否通过单列，
`physical_acceptance=false`，不据此豁免旧B、A或新B已出现的失败。

## 因果诊断的限制

保存六分量sigma为有效应力；总应力=sigma'-pI，剪切不改。
Q仍是100层均值总sigma_zz的98个二阶差分RMS，与交替X列Uz模态分开。
两B的nearest对照只查实际最近保存态，显示有符号clock差，不插值、不重写时钟，
不套5Pa/.005mm half或跨后端等价门。A为不同模型/后端，不能孤立归因或宣称速度收益。

附加的贡献分解只作小应变受限压缩诊断：在固定材料中心.005至.995之间使用
原.01m材料中心间距、两端半权重作材料中心梯形积分，分别积分总压应力/Mc和-p/Mc，并与原生top-bottom沉降差比较。
另积分-(J-1)作为一维体积应变近似。这是明确的材料中心梯形积分近似，不是新增精确守恒、
能量或力闭合证明；横向应变、旋转、离散/惯性及有限变形可进入诊断残差。
不能仅靠一张贡献图宣布压力时层或边界已经被证明是唯一原因。

## 产物和唯一准入

全部新增于 `tests/figures/upl_tpi_m0_dt_causal_r1.*`，不覆盖正式图：

- history.csv：三条轨迹全部3847个实际状态，包含孔压误差、固定材料沉降误差、
  六有效/总应力、Q、J/n/实际rho、速度、交替Uz及上述诊断贡献。
- layers.csv：只给两个B共255500行100层历史、压力范围/沉降/六应力/模态；
  不复制A完整层表。该本地大表无需进入Git，只备份脚本、结论和必要轻量数据。
- profiles.csv/targets.csv：三series两Tv共600层点、原预算及new-old误差增量。
- nearest.csv：1263个newB时刻各自最近oldB状态及显式clock差；events.csv包含
  初态、preopen、首post、约.15/1.5s和末态的原样汇总。
- history/startup/late/profiles/modes/nearest六张PNG及metrics.json；每条图线均有上述CSV。
  startup保留全启动并放大closed ramp/event；late单独展示1.5-2s，仍保留全历史。
  模态图只比较两个B，共用各物理量色标，不平滑、裁剪或重采样原状态。

根准入 `stage=upl_tpi_m0_dt_causal_r1.admission,passed=true,offline_only=true`，
inputs列本两稿、原B10us科学定义/基础XML/原TPI计划及实际消费的native/read/review、
columns/IDs/physical/soil_n/clock/history/ledger和原计划；B10us原run/科学check也绑定。
消费文件逐stat固定并在结束复核；不重新扫描源码、objects或原BI4哈希。
本稿没有任何自动后续solver、reader、Git或队列。

```text
python -B tests/support/upl_tpi_m0_dt_causal_r1.py --execution-authorized --admission ROOT_JSON
```

已有收据、产物或partial任一存在即拒绝覆盖，保留真实首因，由根离线审查后决定后续。
