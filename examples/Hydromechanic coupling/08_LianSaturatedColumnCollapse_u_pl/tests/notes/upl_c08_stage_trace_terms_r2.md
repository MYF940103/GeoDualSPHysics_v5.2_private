# C08 阶段分项绘图修复

原 r1 在已封存的 Release 0.03 s 数据上执行一次，分项 CSV 已写出，首次绘图因局部坐标轴变量 `a` 遮蔽 CLI 参数变量而报错。原脚本、说明、失败 check 与三份 CSV 原位保留，未重算或解码任何物理结果。

r2 仅改新 TAG/输出前缀，并在 main 显式保存 `profile=a.profile`，闭包使用该 profile；原六项公式、所有真实事件、RHS/pressure 舍入记录、实际 PRE 时钟、原生输入和检查门均不变。数值与方法说明仍参见 `upl_c08_stage_trace_terms_r1.md`。两份脚本不是两套物理实现，r1 仅作为失败历史。

根已全文审查 r1 及此机械补丁；单次短窗派生验证：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_trace_terms_r2.py --profile short --execution-authorized
```

新输出为 `tests/figures/upl_c08_stage_trace_terms_r2_short_verify*`。只有将来 window run 和独立 trace check 均封口通过后，才可单独调用 `--profile window`；其输出使用另一个新前缀。没有自动运行、求解器、解码或参数修改。
