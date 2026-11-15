# 壁894保存态proxy双attempt图：作者稿

仅新增同名support脚本和本文，作者不import/执行。root可审阅后一次运行 `D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_hg_wall_proxy_visual_r2.py --execution-authorized`。输入仅为已封存 `c08_h18_hg_wall_saved_proxy_r1_attempts.csv` 与原check；不读取原生或重新计算矩阵/拟合/alpha，不改原脚本/CSV/check/PNG。

只新增 `tests/figures/c08_h18_hg_wall_proxy_visual_r2.png` 和logs同名visual check，拒覆盖或自动重试。2×2面板依次显示attempt0原G与attempt1重试G的全部detM（log纵轴、原.001参考线）、两次donor数、仅geometry predicate通过的retry1 fitted detC和sym(C)特征值、最后geometry-valid proxy（retry1）的alphaL1及负系数数量（分左右纵轴）。最后accepted仅指本保存态proxy的geometry-valid行，不表示实际GPU阶段被接受；不将attempt0空拟合字段补零。

本图修复旧trends只取每时刻最后attempt、隐藏原G逼近.001的展示遗漏，不改变任何门槛或proxy数值。十个保存时刻仍为P89–98真实τ；不能把detM趋势外推成未保存stage1的实际失效证据。拟合C、对称特征值及alpha仍仅为现存CSV诊断；正常绘图不是物理/HG/接触验收，也不证明actual failure branch。root须目检新图后单独记录QA。
