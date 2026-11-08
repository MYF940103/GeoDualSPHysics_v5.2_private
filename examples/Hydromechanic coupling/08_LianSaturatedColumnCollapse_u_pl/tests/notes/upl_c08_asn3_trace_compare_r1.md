# 三个固定材料点的 AS 指数 2.55 / 3 trace 对比

仅新增同名 Python 和本说明；不修改已完成的求解、57 列代数检查、原 CSV 或旧分析。固定 ε=.2，独立读取两份实际执行 XML，确认 AS 开启及指数分别 2.55 / 3；只在内存中归一指数再核其余物理、程序、PRE 和源时钟一致。

baseline 采用已通过 `upl_c08_as05_trace_compare_r1.check.json` 绑定的 extrema / frequency / growth / RHS 表；曲线采用其 `steps.csv` 的 baseline 90000 行。现无单独 large_steps 缓存，不重读旧约 176 MB trace。新 n3 CSV 仅完整读取一次，复用旧工具的纯 load / RHS / frequency 方法，不调用旧 main；450003 行的原代数门只消费已通过检查，不重复运算。

严格按实际 nstep、step_start、τ 和三个 ID 5809 / 4956 / 4959 配对。输出四种阶段压力 p_n / half / full-prepond / full-postpond 的全已记录、启动稀采样及 .60–.66 每步密集段 extrema / 样本 RMS；初始真实事件和额外 ponding 原样另存。启动每 40 步的样本 RMS 不是时间加权 RMS，不能排除未采样微秒峰。图显示原 full-pre / post，密集图另加 half，不平滑、滤波、截负压或重对齐。

频率沿原相同实际窗口 [.619,.621)、[.625,.627)、[.635,.637)：去均值 RMS，Hann 后最大非零 rFFT 格点、不补零，保留约 500 Hz 格点宽度；首末窗口 RMS 比与对数增长只作描述，不是特征值拟合。RHS 第三项仍为 Taylor 缺陷与 Ace 合成，不能凭分项幅度推断因果。这只是三个点及指定密集窗，不能代表全部土粒或全时高频，更不把不同指数当 half / 5 Pa / 理论误差。

root 全文审阅后的唯一离线入口（本作者未执行）：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn3_trace_compare_r1.py --execution-authorized
```

fresh 输出 `tests/figures/upl_c08_asn3_trace_compare_r1_*` CSV / PNG 和同前缀 `.check.json`。原 source 及缓存只 stat 核必要绑定，无 SHA、solver、reader、VTK、构建、queue 或自动后续。通过只表示本次离线分析完成，物理验收仍为 false。
