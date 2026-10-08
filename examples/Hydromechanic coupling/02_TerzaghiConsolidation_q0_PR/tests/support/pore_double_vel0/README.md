# CPU Vel0：double 孔压状态迁移的短程复核

本组仅完成正式 Vel0 边界的四组短算例与误差来源对照。不改变正式源代码、根目录 XML/BAT、旧结果或原有高低位补丁归档。不运行完整 2Tv，不扩大到孔压率/空间算子的 double 改造。

## 文件位置

- `tests/configs/pore_double_vel0/dt1em5/`、`dt5em6/`：同一步长的新旧版本共用配置。保留原 XML 排版，只替换四项时间参数，移除旧 timeout 覆盖块（如有）。
- `tests/outputs/pore_double_vel0/q0_vel0_{baseline,current}_dt{1em5,5em6}/`：四组原生计算结果、`particles` 转换结果、`native` 原生 CSV。
- `tests/outputs/pore_double_vel0/reader/`：隔离编译的 BI4 读取器及 QA 输出，不是求解器变体。
- `tests/logs/pore_double_vel0/`：运行来源、构建/读取器 QA、计算表与独立核验。
- `tests/notes/pore_double_vel0_chart_contract.md`：预先规定的统计/绘图口径。
- `tests/notes/pore_double_vel0_acceptance.md`：最终结论与修改清单。
- `figures/pore_double_vel0_history.*`、`pore_double_vel0_differences.*`：正式对比图。
- 同分组内 `_event` 四组与 `event_` 统计文件：仅追加 0--30 ms 的共同步点采样，图为 `figures/pore_double_vel0_event.*`。原四组结果保留。

## 复现顺序

以下命令在算例根目录运行。每个生成步骤拒绝覆盖已有输出；本次已完成的记录不应再次执行覆盖。新一轮比较应使用经确认的新分组，而不是删除旧结果或直接换程序覆盖。

```powershell
py -3 -B tests/support/pore_double_vel0/run_vel0.py
powershell -NoProfile -ExecutionPolicy Bypass -File tests/support/pore_double_vel0/build_export.ps1
```

逐组原生导出示例（其余三组替换运行目录名）：

```powershell
& tests/outputs/pore_double_vel0/reader/export_state.exe --dir tests/outputs/pore_double_vel0/q0_vel0_baseline_dt1em5/data --out tests/outputs/pore_double_vel0/q0_vel0_baseline_dt1em5/native
```

四组全部导出后：

```powershell
py -3 -B tests/support/pore_double_vel0/analyze_vel0.py
py -3 -B tests/support/pore_double_vel0/verify_vel0.py
py -3 -B tests/support/pore_double_vel0/plot_vel0.py
```

事件补测采用 `run_vel0.py --event`；本次为先检查首组输出时刻，实际先执行 `--event --first-only`、再执行 `--event --remaining`，各阶段拒绝覆盖已有运行。输出间隔 0.00049999 s，只改变诊断采样阈值，不改变 dt/边界/方程。四组各 61 帧原生导出后执行：

```powershell
py -3 -B tests/support/pore_double_vel0/analyze_vel0.py --event
py -3 -B tests/support/pore_double_vel0/verify_vel0.py --event
py -3 -B tests/support/pore_double_vel0/plot_vel0.py --event
```

原四组只有 85 个跨步长共同时间帧，10--30 ms 无共同帧；事件补测得到 61 个共同帧，补齐该窗口。原图在缺失时刻断线，不能把连线跨越的空白当成实际观测。图片 QA 的 `--replace` 仅允许替换本组明确命名的三幅生成图，不修改任何求解器输出。

运行器固定校验 retained high/low 与当前 Stage 1 CPU Release 的 SHA256，不能把任意新程序当成本次同一版本。`build_export.ps1` 使用本项目 MSVC 与生产 BI4 读取实现，隔离编译为独立测试程序。源码和二进制来源见 `reader.build.json`。

## 指标解释

1. 迁移差：同 dt 的 double 减高低位重构孔压；旧值为 double(high)+double(residual)，不能只比较旧 float 高位。
2. 步长差：同程序的 5 us 减 10 us，只是敏感性检查，不是真值或收敛阶证明。两个步长可能跨越 0.01 s 排水阈值的步点不同。
3. 土孔压均值/RMS：ID 40--1039 共 1000 个土粒子。全粒子机械量检查另含 40 个固定边界粒子，不能混用分母。
4. 沉降：初始顶部固定 10 个 ID `139,239,...,1039` 的 mean(z0-z)，向下为正，不逐帧重选顶层。
5. 原生 Part0 位置为 float，后续帧因 `-svextraparts:1` 为 double。初始保存位置的共同偏移在版本/步长沉降差中抵消，但绝对沉降仍沿用保存原点。
6. 实际输出时间容差 1e-11 s；跨步长不匹配帧不参与相减，不插值。全程迁移指标与共同采样集合指标分别保存。
7. 此前 RMS 0.01 Pa、最大 0.1 Pa 是迁移审查线，不是物理正确性标准。程序正常结束不等于严格迁移审查通过。
8. 单轮耗时保留用于追溯，不作为效率验收；本轮有读取/分析和一次增量 CPU Debug 检查，未实施受控重复性能试验。
