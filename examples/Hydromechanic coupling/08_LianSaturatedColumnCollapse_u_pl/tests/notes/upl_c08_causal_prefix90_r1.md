# C08 causal90 与根 r6 前90保存态的一次离线核验

仅新增同名 support Python 与本说明；事前确认目标不存在且未跟踪。脚本从已用过的 `upl_c08_n3_full_prefix_r1.py` 机械派生，固定比较 `upl_c08_causal_window_GPU_r1/native` 的90帧与根 `CaseLianSaturatedColumnCollapse_psi0_shared_r6_GPU_out/native` 的300帧之前90条。不执行 BI4 解码、VTK、solver、构建、队列或 SHA，不修改旧脚本、收据、输出或元数据。作者只做 AST 静态检查，未执行比较。

两方须有各自通过的真实 run/native 闭合及当前有效的导出绑定；源 PRE stat 和真实 source clock 一致。程序、source_build、source_capture/source_archive 分别记录，不扫描 ZIP/对象；不同程序身份只作来源说明，不是逐位门，也不能据此推断数值相同。

使用真实 `typed22_layout.csv` 得到22个字段跨度，要求6805 ID、212 bytes/particle。原二进制头必须各为 **6805/22/90**、**6805/22/300**，完整文件大小各按原计数核验，绝不改头。流式读取共同90条，每条真实 f64 时钟和22字段所有 bytes 均比较；每字段记录相同条数与首个不同 part/byte。全程300后210条不重新读取或审查。

`clocks.csv`、`history.csv`、`plane_gaps.csv` 各保留原91/301行，比较原 header 和90条共同整行 bytes。时钟整行包含所有 signed dterror/empty/Step 字段，无排除；另核原每4000更新保存、actual saved_step=completed−1、dt2.5µs、非空 signed≤1e−14，并核二进制/文本真实时间一致。相同保存节拍才比较 signed interval；不使用插值、近时或5Pa替代逐位证据。

根完整审阅后的一次入口：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_causal_prefix90_r1.py --execution-authorized
```

只生成 `logs/upl_c08_causal_prefix90_r1.start.json`、`.check.json` 与 `figures/upl_c08_causal_prefix90_r1_fields.csv`（真实时间加22字段）。独占创建 start 后拒绝已有或活动同名尝试；失败保留该记录及首差异，不自动重试。检查通过仅说明两个已完成求解的共同保存前缀没有可观测反馈差异，不是全场阶段轨迹相同、理论精度、半步收敛或物理验收。现有两方原生安全门复用其独立通过收据，不重复解码。
