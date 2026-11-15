# 已封存两份测试说明的中文补遗

`c08_h18_hg_wall_host_jobs_r1.md` 的末段及 `c08_h18_hg_wall_host_jobs_r2.md` 的首、末段，在 PowerShell 向 Python 传递新增中文文本时被转为问号。两份文件已经绑定历史运行的 stat，因此原始字节不改；对应的可读文字补在此处。脚本逻辑、程序、输入和数值数据未受该备注编码问题影响。后续此类管道已显式设为 UTF-8。

host_jobs_r1 末段的原意：host-capture r1 的两配置因已有 Windows max 宏导致 C2589 编译失败，原记录保留，未运行该程序。尚未执行的 jobs 改为只接受 r2 的局部括号兼容修复及其实际 header/build；物理参数和验证门保持。

host_jobs_r2 首段的原意：本 r2 只将后续实施准入指向新的 `.review_r2.check.json`，并绑定本说明。新的离线审查修正首步快照实际为 CSV 的文件名，保留原分析失败。已完成的 Debug2 及其唯一 native 由原 r1 owner 真实执行，直接采用，不重跑、不重解码、不改旧输入或收据。Release4 和故障重放由新的 r2 根准入分别启动，未放宽门或修改物理。其末段同上一段补遗。

实际状态以各次原始 start/call/run、编译及原生收据和 `c08_h18_hg_wall_host_stage_r1.md`、`c08_h18_hg_wall_fault_outcome_r1.md` 为准。编码补遗不是新的运行、验收或对原历史证据的替换。
