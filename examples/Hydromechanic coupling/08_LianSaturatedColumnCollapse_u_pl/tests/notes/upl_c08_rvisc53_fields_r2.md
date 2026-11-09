# 失败53帧 fields 色条刻度修复（作者稿，未执行）

仅新建 plot-only renderer；不修改原脚本、PNG、check、native 或 CSV。原图问题是 Matplotlib 自动色条刻度伸到实际正压最大值之外，非数据或原分析错误。

Root 全文审后可从 C08 根目录单次运行 `D:/anaconda3/python.exe -B tests/support/upl_c08_rvisc53_fields_r2.py --execution-authorized`。只绑定原已passed partial53分析与其实际native收据，保留baseline90/candidate53真实头；memmap仅读part49/52共四条既有typed记录的ID/位置/p/J和实际clock，不重做NN/历史、BI4解码或求解。原22 schema/6805 IDs及既有原生资格不改。

全域与局部ROI、四状态全土min/max和原散点定义保留。压力色条显式使用实际端点及区间内−2MPa/−1MPa/0，标签换为kPa（实际正端点约+17.329kPa）；J刻度也限制在实际范围。TwoSlopeNorm仍将负值、正值分到各半条色带，**两半使用不同尺度**，图注明确说明。无新正压裁剪、平滑或分位数限色。

唯一新图：`figures/upl_c08_rvisc90_partial_review_r1_fields_r2.png`；新小收据：`logs/upl_c08_rvisc53_fields_r2.check.json`，记录原始上下限、显式ticks/标签和四条来源。拒覆盖；失败保留新部分产物。脚本当前只作者/AST，未执行，图仍需Root实际视觉QA，不提供新的物理验收。
