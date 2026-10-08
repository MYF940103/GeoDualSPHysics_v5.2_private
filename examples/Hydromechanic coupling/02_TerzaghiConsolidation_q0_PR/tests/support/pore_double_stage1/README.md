# 孔压 double 状态迁移：阶段 1 验收

这些是临时验收工具，不是正式算例入口。正式根目录的 XML/BAT 和历史结果不改动。

范围：当前/参考/历史孔压为 double，孔压率和空间算子仍沿用阶段 1 约定的 float 运算。不检验完整固结解析精度，也不解决 Tv>1 平台问题。

目录保持分类：本目录放测试源码/脚本；派生输入在 `tests/configs/pore_double_stage1`；运行结果和测试可执行文件在 `tests/outputs/pore_double_stage1`；日志及 JSON/CSV 证据在 `tests/logs/pore_double_stage1`。任何已有同名结果均拒绝覆盖。

## 真实生产函数测试

必须先按 `src/VS` 工程完成对应生产配置的构建。测试只编译测试入口，链接工程中实际启用的生产对象，不复制实现、不修改求解器源码。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/support/pore_double_stage1/build_harness.ps1 -Configuration DebugCPU -Label r3 -ProductionBuildConfirmed
powershell -NoProfile -ExecutionPolicy Bypass -File tests/support/pore_double_stage1/build_harness.ps1 -Configuration ReleaseCPU -Label r3 -ProductionBuildConfirmed
powershell -NoProfile -ExecutionPolicy Bypass -File tests/support/pore_double_stage1/build_harness.ps1 -Configuration Debug -Label r3 -ProductionBuildConfirmed
powershell -NoProfile -ExecutionPolicy Bypass -File tests/support/pore_double_stage1/build_harness.ps1 -Configuration Release -Label r1 -ProductionBuildConfirmed
```

CPU/GPU 各覆盖 218 个冻结孔压率算例：正负源项、低于 float ULP 的增量、Pre/Corr 时序、Verlet 历史/别名和中途内存状态恢复。另测边界/非流体复制、周期数据映射；CPU 检查正常粒子输出筛选，GPU 检查 double 排序。PART 格式加载检查由相邻 `loader_double_harness.cpp` 单独负责。

`cpu_state_harness.cpp` 另外提供两个只读原生 BI4 工具：

```text
--export-state DATA_DIR PART --csv NEW.csv
--compare-parts BEFORE_DIR PART AFTER_DIR PART --json NEW.json
```

导出时旧格式按 `double(high)+double(low)` 重构，新格式保留 double；CSV 使用 17 位有效数字。比较重启文件时直接按 Idp 比较 double 位，不借助 VTK。

## 同输入短程回归

当前测试脚本假定保留补丁的 CPU/GPU 基线程序在 `tests/outputs/pore_double_baseline`，新程序在 `bin/windows`。每项均记录执行程序 SHA-256、原输入 SHA-256、派生 XML SHA-256、命令、步数及排除粒子数。

```powershell
py -3 tests/support/pore_double_stage1/run_regression.py --build baseline --backend cpu
py -3 tests/support/pore_double_stage1/run_regression.py --build baseline --backend gpu
py -3 tests/support/pore_double_stage1/run_regression.py --build current --backend cpu
py -3 tests/support/pore_double_stage1/run_regression.py --build current --backend gpu
py -3 tests/support/pore_double_stage1/run_regression.py --compare
```

每个 backend/build 运行六项：q0 k=1e-4 的 0.2 s / 20000 步；自重 k=1e-3 历史 PART56 重启后 0.5 ms，dt=250/125/62.5 ns；另用 250 ns 检查 Shepard40 和关闭 HydroMech。两版本使用相同 mDBC/稳定排序/积分配置。CPU 的 q0 用 4 线程，自重用 1 线程。本轮编译与其他测试并行，记录的 walltime 不能用于效率结论。

比较按 Idp 和 Run.out/BI4 实际时刻对齐。权威孔压使用原生 BI4 的重构状态，而非旧 float 可视化输出；后者的量化差另列。`regression_history.csv` 的 mean/RMS/max 孔压都是土粒子权威值。

比较前确定的审查线：全帧土粒子孔压 RMS≤0.01 Pa、最大差≤0.1 Pa；位置最大差≤1e-6 m；速度≤1e-5 m/s；应力≤1 Pa；参考孔压逐位相同；干路径逐值相同；自由表面分类不变。超线必须报告并定位，不能看到结果后放宽阈值。

## 实际新格式重启

```powershell
py -3 tests/support/pore_double_stage1/check_restart.py --backend cpu --seed
py -3 tests/support/pore_double_stage1/check_restart.py --backend gpu --seed
```

生成 0.02 s q0 小算例，显式 `-svextraparts:1` 保留 mDBC 重启所需额外数据，从 0.01 s 的新 double PART 重启。比较原 checkpoint 和重启后初始 PART 的 PorePress/PorePress0（1040 粒子）是否逐位一致；随后仅运行 1 步结束程序，不声称完整重启轨迹等价。`--verify-only` 可在不重跑求解器的情况下对既有结果复验，但输出仍不覆盖。

本轮早期试验未保存 mDBC 额外数据，被求解器拒绝重启；该日志和原生导出工具调试记录保留在 logs 中，不能算通过项。成功验收以最终 `.native_verify.json` / `.native.json` 及通过状态为准。

## q0 基线确定性复核

```powershell
py -3 tests/support/pore_double_stage1/repeat_baseline.py
```

读取已保存的基线执行记录，复用同一 XML、同一 CPU 程序、4 线程和原命令，只替换输出目录为 `q0_baseline_cpu_repeat`。对 21 帧全部 1040 粒子比较重构孔压、原 high、low 和参考孔压的位模式。本轮这四项均零差异；这并不使迁移对照中超线的 q0 结果自动通过。

以上命令描述从干净测试目标开始的复现顺序。已有结果时不要删除或覆盖，应先明确新的归档/标签规划，再复现。
