# ReleasedSubstages 与原 n3 的三材料点 trace 对比

仅新增同名 support Python / 本说明，事前两个目标不存在且未跟踪；作者未执行 / import。输入为实际 window_GPU_r2 已封口 run / native 和通过的新 `stage_ponding_review_r1` window检查；消费540003行 / 30000次half / 全原代数门，不重复其 float/RHS/clock 代数。

新 raw CSV 只完整读取一次。按三个固定ID与真实core `RHS2/UPDATE2/RHS3/UPDATE3` 提取 p_n、raw half update、half投影后供force读取的p、full-pre / full-post。mandatory half 必须真实位于该step UPDATE2行之后且RHS3之前，并为interstep2；不能只按event3/stage2挑第一条而误选初始leading。最后ponding按UPDATE3之后的真实尾行取，其余真实leading/repeated事件和初始step全行另存，不改原CSV。

基线只读已通过 `figures/upl_c08_asn3_trace_compare_r1` 的 extrema / frequency / growth / RHS 四张小表并filter原n3 group，不读旧176MB trace或另造steps缓存。基线 p_half_Pa命名为raw half；其half-after摘要复用同值，因为已通过原checker证明无半投影且Corrector读取该raw half，这不是新增观测。新旧程序必然不同，但实际物理XML、AS .2/exp3、原PRE及源clock相同；不加same-program误门。

输出all-recorded / 启动稀采样 / .60–.66每步dense的五压力通道 extrema和样本RMS；频率仅沿原 [.619,.621)、[.625,.627)、[.635,.637) full-pre压力，严格核两组缓存/新数据的实际窗首尾/中心/平均dt与样本数一致。去均值RMS、Hann最大非零rFFT格点及约500Hz格点宽度原样；不滤波、补零、相位移动或拟合特征值。启动每40步采样不能证明未采微秒峰；不同密度的样本RMS也不是全程时间加权RMS。

新图只画本轮三ID，两列为已记录全窗及密集窗，raw half和force-consumed half分开；原n3用小表并列及频率RMS比，不因缺基线steps而补画插值曲线。RHS第三项仍含Taylor defect与Ace合成，不能作独立因果分解。无跨policy5Pa/half/理论精度门，也不能代表全部土粒或全时高频。

root全文审阅后一次离线入口（作者未执行）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_trace_compare_r1.py --execution-authorized
```

fresh输出 `tests/figures/upl_c08_stage_ponding_trace_compare_r1_*` CSV / PNG和同前缀check；保持原输出，失败保留首因。无reader/solver/build/VTK/queue/SHA，analysis通过仍physical=false。
