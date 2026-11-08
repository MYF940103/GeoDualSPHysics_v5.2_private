# 同一 AS.2/n3：completed-only 与 released-substage ponding（作者稿）

仅新增同名 support/note，未 import/执行。必须新正常 run `upl_c08_stage_ponding_window_GPU_r2` 和未来 `logs/<job>.native_r1.json` 的原生守卫真实通过，root 全文审阅后才执行一次离线分析。新 native 为 out/native；独立检查 stage `upl_c08_stage_ponding_native_r1`，metadata profile window、66 个 ReleasedSubstages/Active header，以及 AS ReleaseOnly/.2f/3f、6805/5000/1805/22 与原 ledger/P0/J/缓存/κ/plane/clock/signed 守卫。旧 n3 的缺省 completed-only 元数据不被重标成新 policy。

新程序是 Release_r2/source_r2，旧 n3 程序不同符合预期，不施加 same-program 门。两者原 PRE Entry、source 实际时钟、22-layout、完整 special/parameters 及全部66个实际时间/步数须相同。绑定两闭合程序 source archive；只读取 ZIP 三 CPP 条目，并将新 capture 的 production.diff 原上下文逐行应用于旧程序归档，核对恰好得到新归档。Diff 限本轮三 CPP + doc、17+/8−；doc 只一条说明 comment/default0。既不扫整个旧 tree，也不绑定可编辑 live source 或 hash。旧 startup 文本早于 gravity 配置，不能替代实际 metadata 证明数值策略。

旧 n3 的 body66行/cohort396行只从已 passed `asn3_compare_r1` 缓存取。新66条 typed22 按真实原 header 顺序只读一遍，复用冻结 `c.inspect/quantities` 与 `cluster.measures/summarize`；不调用任何旧 main，也不使用旧固定2.55上下文 loader。新旧每态原 IDs/时钟语义匹配，不插值。CSV 保留每组完整66态：孔压均值/原范围/RMS、原 PRE 全5000材料平均沉降、前缘/高度、总应力、速度、κ、J/n/k 范围，以及全部原六 NN/cohort 统计。差表只是 Released−Completed 描述，不套5Pa/half/理论精度门。

末态新帧已在内存；旧 n3 仅额外 seek part65 一个1.4MB记录，保留原66头。实际 τ=.66 两组各5000土点导 endpoint CSV（ID/x/z/p/κ/NN/FS），不导全22字段。三行两列空间图依次原孔压/κ/NN：共同物理轴、每行共同原始色标，全部5000点、真实固定标记和 FS2/3 三角。压力采用 signed symlog 色标（1kPa线性区，仅绘图），原值及 ±峰不裁剪。另一张八面板 history 图同时显示保存态孔压、沉降/front/速度/总σ/κ/近对/NN。

fresh 前缀 `tests/figures/upl_c08_stage_ponding_compare_r1`，输出 body/cohorts/differences/endpoint 四 CSV、history/endpoint 两 PNG 和同名 logs check。严格拒绝已有完整或 partial 派生产物；不修改旧 CSV/header/收据。保存峰不是微秒 dense 峰，本工具不读新旧 dense trace。正常退出、孔压下降、少近对或应力/速度减小都不能自动等同解决团聚、稳定或更高物理精度；root 后续独立审查真实 trace/物理。无 solver/reader/VTK/build/queue 或自动后续。
