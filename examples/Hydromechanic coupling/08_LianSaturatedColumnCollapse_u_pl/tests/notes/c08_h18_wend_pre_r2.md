# Wendland 预载启动入口修复

r1 在任何 GenCase 或求解器启动之前拒绝：原共享 helper 中固定的旧版 Codex 可执行路径已不存在。原 r1 的 claim、run、status 和配置保留，实际 GenCase/solver 调用均为零，不重新布防或重发其通知。

r2 是薄启动适配器，明确复用完整审阅的 `c08_h18_wend_pre_r1.py` 数值 owner；不修改该文件。优先选择当前 PATH 上实际存在的 `codex`，不存在时选择已安装扩展中的最新程序；使用独立 r2 标签，并让 BAT 指向新适配器。终态单次投递前重新定位入口以适应升级，仍只调用原来的一次 queue，不重试通知。当前入口已查询 `queue --help`，仍支持 `--thread` 和 `--message`；没有发送连通性测试消息。

实际新适配器、新说明、原实现和原说明全部进入 prepare/owner/run 的 stat 消费绑定，不把旧实现文件伪装成新调用者。r2 XML 与未启动 r1 XML 的结构签名必须完全相同；物理差异仍只有相对失败 Cubic 预载的 Kernel1→2。

命令为 `prepare|run --group psi0 --execution-authorized`，只有 run 可加 `--notify`。新的 root admission 六个文件 Entry、kernel=2、材料、10s/2M/1001、实际线程等规则与 r1 相同。prepare 只生成测试 XML/BAT/收据，零 GenCase/solver。run 每次仅允许一份新结果，真实句柄记录及原守门全部复用；不自动启动 reader、half、其他 ψ 或后续求解器。

数值仍为 hdp1.8/H.072、dp.04、5µs、阻尼.03/Shepard40、ψ0、同材料塑性 schema2、AS/NoPen/keepbed OFF 和床最后绘制。完整10s输出及其平衡均待独立审查。唯一终态通知仍只投递一次，45s超时也不重发。
