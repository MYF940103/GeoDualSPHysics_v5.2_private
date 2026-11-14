# C08 P76/P90 空间图排版修正 r2

仅作者资产，尚未执行。只新增 `support/c08_h18_rv_radial_spatial_plot_r2.py` 和本说明。根线程独立审阅、准入后才运行一次绘图；不含求解器、原生读取器程序、构建、VTK、Git、通知或下一物理任务。

已完成科学审查的 r1 数值结论不改：径向 RV 仍不能选为团聚修复。r1 的 history/P38 可读；P76/P90 的总标题与最右 colorbar 标签边距不足。本修正只为该排版缺陷生成两个新 PNG，绝不覆盖 r1 图、CSV、原 check 或 visual 收据。

## 封存输入和取值

- 根依据为 `logs/c08_h18_rv_radial_window_review_r1.check.json`，须已通过且为实际三轨迹×91保存、45000行空间表。
- 空间数据仍是其封存 `figures/c08_h18_rv_radial_window_review_r1_spatial.csv`。先核原 check 的 size/mtime seal，再读取全部45000行和原有3×3×5000材料身份/时钟布局；仅原样选择 P76/P90 的30000行绘图，不重算孔压、NN、材料历史或物理诊断，不剔除点。
- 每个 case 的固定边界取自已封存三 native 目录在 P76/P90 的真实记录。按原 check 的 `consumed` 原 seal 核 `typed22.bin`、layout、clocks，仅 seek/read 时间payload及原 Idp/Posd 两数组（共6记录）。不调用 C++ reader、不重新解码 BI4、不读其他20数组、不写 native。所有6805 IDs、CSV的5000土坐标和实际时钟须与这些原始导出字节一致，返回原1805固定点用于灰色边界散点。
- 不扫描 SHA；所有旧输入和四幅 r1 PNG 的原 seal 在绘图前后保持。失败保留新的 partial，不覆盖或自动重试。

## 数值与绘图范围不变

两张图分别仍为三轨迹×两个物理场：原 AS0.3 无RV、向量 RV alpha0.1、径向 RV alpha0.1。每个 panel 保留全部5000土点和原1805固定点；孔压使用原 Pa/1000 的 kPa 换单位、NN直接取原 `NN_over_dp`。不插值、平滑、clip、拟合或重新选材料点。

每个时刻的孔压/NN色限仍是三 case 原值的共同完整 min/max，坐标范围仍是三 case 土坐标共同 min/max 各加减原 dp=0.04。`Normalize(..., clip=False)`、`coolwarm/viridis`、土点面积6、边界面积3及原灰色均保持。原视域之外的远墙继续按同视域显示规则裁在轴外，不能因此改动土点或视域。

变化仅为18×14英寸画布、固定人工边距/GridSpec、较短并换行的 panel 标题、右侧留白和 colorbar 标签间距，避免 constrained-layout 收缩。行标题的 tau 显示6位小数并明确为 rounded label；全局标题保留实际 t/tau 的17位有效数字，check和原CSV/原生时钟不变。这不是把实际时钟替换成名义时刻。

## 新输出

- `figures/c08_h18_rv_radial_spatial_plot_r2_P76.png`
- `figures/c08_h18_rv_radial_spatial_plot_r2_P90.png`
- `logs/c08_h18_rv_radial_spatial_plot_r2.check.json`：原始输入/旧图 seal、新图 stat、所有真实色限/坐标限/时钟、点数和只读访问范围。

无需另造数值CSV；新 check 直接绑定原45000行空间CSV和原 native 固定点。`passed=true` 仅表示绘图成功及 seal 未变，仍为 `physical_acceptance=false`、`visual_QA_pending=true`。根必须实际看两张新图后另记视觉审查，不能用脚本正常结束替代目检。

未来仅根准入的绘图命令（作者未执行）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_rv_radial_spatial_plot_r2.py --execution-authorized
```
