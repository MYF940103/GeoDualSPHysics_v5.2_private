# C08 已有 HG0/HG 两状态窗与 Fig14：作者稿

仅新增同名 `tests/support/c08_h18_hg_paper06_r1.py` 和本文。作者不 import/运行脚本，不求解、解码原生BI4、导出VTK、构建、Git或哈希扫描。root 完整审阅后可单次执行 `D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_paper06_r1.py --execution-authorized`。已有完成或 partial 一律拒绝，不覆盖或自动重试；正在运行的 opt 3s 及其全部依赖不进入本脚本。

输入只有已封存 HG0 `c08_h18_as03_n255_r1` 与 cached HG `.9s` 的 `native_r1` 两套91帧 typed22、layout、clocks，以及既有 Fig14 轮廓CSV。绑定旧AS03 native检查、cached独立export seal和已通过physical review中的相应六个文件stat；不重新遍历全部构建依赖，不扫SHA。沿用 `c08_h18_storage_review_r2.typed` 的原22字段schema及 `c08_h18_compare_r2.read22`；原91帧头不改，仅各读取两个选定状态，共四个22数组记录。实际5000材料IDs和1805固定粒保留，所有计算使用完整土体而非显示域筛选。

按真实clock在名义τ=.3/.6s选最近保存帧，两组必须实际completed step/time/dt完全相同，偏差仍受原输出节奏5.01us限定。不插值或改写元数据；预期保存τ约.300005/.600005s，而不是精确.3/.6。每次调用现成read22保留全部IDs、有限值、真实clock和原signed≤1e-14门；完成native收据保留原91帧的P0/J/ledger/FS等安全声明，本文不把这次绘图当新的完整解码。

未来只输出四份派生：`tests/figures/c08_h18_hg_paper06_r1_native_excess.png`、`_paper_shape.png`、`_spatial.csv`（4×5000行）及 `_summary.csv`（4行），另有 `tests/logs/c08_h18_hg_paper06_r1.check.json`。空间CSV包含实际ID/坐标/clock、原总p、固定初始P0、原生ExcessPorePress、κ、J/n/ρ/k和速度，未从截色后的图反算任何值。摘要保存两种压力原始极值/RMS、超出±10kPa的人数/比例、前缘及参考表示限定。

压力图为2×2：两个真实时刻×两个算子，共用纸面Fig14的−10..10kPa显示范围、equal aspect和x约0..8m/z约0..2m的相同视域。使用jet式视觉近似（原纸面是蓝青绿黄红，未提取精确RGB；不声称精确复刻色板）。colorbar两端扩展三角明确过色域；标题给出实际上下越域人数，CSV保留全部原值。没有平滑、插值、删负压、分位裁剪或为匹配论文而调色域。总p和κ不被冒充paper excess/等效塑性应变；它们单独存CSV供审查。

论文Fig14右列标签为excess，正文归因于塑性体积变形，但并未给出可重算的统一全场背景式。当前原生 `p−固定材料初始P0` **未被证明等于该paper excess定义**，图标题/脚注与check均明确这一点，不输出精确压力误差或“ψ0必须零压”的结论。两组是不同HG算子比较，不是半步长误差。

第二张图只叠加5000原生材料中心与既有 `upl_c08_lian14_outline_r1_outline.csv` 的可见主体像素边界，不嵌入拥挤原页图。参考CSV的.3/.6s可见前缘为4.06780/4.48869m；约±.036m栅格辨读量级与单独dp/2=.02m中心表示差分开保留，不校正或拟合位置，不当理论解门。原轮廓按像素行序，不是闭合多边形；这里只散点显示，不据此算面积。全部统计仍用完整材料域，x=8m只是与paper同图视域。

正常绘图、原生安全或短窗几何改善不表示完整3s、论文或三组验收。root须目检两张新PNG；若派生失败保留首因及partial，不能重复物理计算、覆盖旧图或启动其他ψ/half/PRE。
