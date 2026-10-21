# 根目录退役BAT归档（2026-10-21）

用户授权清理无用/重复入口后，将下列三个历史BAT从case根目录移至此处；字节保持不变，属于可恢复归档，不是删除计算数据。

- `xCaseTerzaghiConsolidation_q0_PR_full_k1em2_win64_CPU.bat`：旧k=1e-2入口，不在本轮三组正式交付范围；含`-force`/递归删除旧输出的历史逻辑，移出根目录以免误用。
- `xCaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_win64_CPU.bat`：已退役的高低位孔压补偿入口。
- `xCaseTerzaghiConsolidation_q0_PR_full_k1em4_double_win64_CPU.bat`：已退役的double孔压迁移入口，旧计算未完成。

不要在本目录直接双击这些归档BAT：其相对路径按原case根目录设计，保留原文是为了历史审查/恢复，而非新运行。若确需恢复，先核对旧程序/源码要求与输出保护，再将指定BAT原样移回case根目录。当前不提供旧试验的新计算或续算入口。

对应旧XML暂留根目录：k1e-2仍被`tests/support/make_stage1_q0_tests.py`、`make_stage2_q0_tests.py`引用；precision被`support/run_double_q0.py`和历史测试引用，double保留其成对输入记录。它们不是当前三组发行参数，也不是逐字重复文件，不为清理入口破坏这些依赖。

三组当前正式XML和六份CPU/GPU BAT保留根目录；所有历史`*_out`、BI4、VTK、图表及旧哈希记录不移动、不删除。具体迁移哈希见`tests/logs/root_inputs_cleanup_r1.json`。
