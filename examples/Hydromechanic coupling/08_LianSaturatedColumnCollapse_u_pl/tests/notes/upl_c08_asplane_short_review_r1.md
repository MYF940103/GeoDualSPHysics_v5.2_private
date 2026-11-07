# AS＋fixed-plane两项短离线implementation review（author-only）

新 `support/upl_c08_as_short_review_r1.py`，两phase单次显式调用，未执行。复用已审 `upl_c08_plane_window_review_r1.load` 的真实22 typed loader，不用旧400step/2frame专用review，不调用其main，不启动solver/reader/下一阶段。脚本与本说明在首个smoke消费前整体冻结，OFF完成后不需再改源码stat。

`smoke`：要求新CPU/GPU各自wrapper native.json实际passed、stat/AS_metadata r2与全部已封口产物绑定，复用Load(1,4000040)。6800材料IDs与真实clock/全局Step相同（clock原1e-14门）；全部5000soil计算native pressure RMS差<=5Pa、每ID XYZ坐标差最大绝对值<=.005mm。只这两个既有backend数值门，不追加AS理论/应力/FS-bit等门。输出 `figures/upl_c08_as_short_review_r1_smoke_pairs.csv` 全5000配对数据及 `logs/..._smoke.check.json` 指标。CPU selected source_run可为adopted_run，原failed owner也绑定保留，不重跑或伪改原receipt。

`off`：新AS0/NoPen1 ReleaseGPU两帧（Load2,4008000）与已passed `upl_c08_plane_partial_r1` 的54真实保存帧（Load54,4216000）核原生typedlayout、**完整两条record doubletime＋全部22数组bytes**，及clocks.csv header＋完整前2条signed行bytes逐一相同。原12B header必须分别2/54并原封保留，不篡改count、不删旧54记录或掩盖signed诊断。旧原solver必须仍failed/exit1，partial check runtime_success=false；prefix相同不等于旧runtime成功。输出OFF两行配对CSV及独立check，失败保留实测而不重解码/求解。

所有产物fresh拒覆盖，必要stat核对，不SHA。passed只表示implementation检查通过，physical_acceptance=false。根全文审后：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as_short_review_r1.py smoke --execution-authorized
D:/anaconda3/python.exe -B tests/support/upl_c08_as_short_review_r1.py off --execution-authorized
```

每phase仅在其真实native已封口后调用，第二条不自动由第一条启动，无半步或额外链。
