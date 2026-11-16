# GPU P1 native r3：复用 r1 读取器的检查修复

本稿新增 `support/upl_tpi_gpu_native_r3.py` 和本说明；不新增 CPP、不复制或构建
读取器。冻结 `upl_tpi_gpu_native_r1.cpp/.py/.md` 及 build/program/runtime 保持原样。
作者阶段不执行 audit、reader、solver、help、build、VTK 或 Git。

## 实现身份与审查身份

- Python reviewer/admission stage 前缀：`upl_tpi_gpu_native_r3`。
- 实际 CPP/protocol stage：`upl_tpi_gpu_native_r1`，仍位于旧 support 原路径。
- 实际 reader：`outputs/upl_tpi_gpu_native_r1_build/upl_tpi_gpu_native_r1.exe`。
- 实际 build：`logs/upl_tpi_gpu_native_r1.build.json`。每次动作都绑定旧 CPP、旧 note、
  新 Python/note、公用 build helper、旧 passed build、program 和所有 runtime destination stat。
- 收据同时记录 `reader_implementation_r1` 和 `reviewer_r3`，不把 r1 CPP 伪称为 r2。
  CLI 只保留 `read` / `review` 两动作；不存在 build 分支。

## 仅修正后端模式与特定已完成数据入口

实际 RunMode 采用 `Stable - Pos-Cell - Single-GPU`。其余原身份、原生、科学门不变。
成功的新 run 使用其原 passed 收据，禁止附带 completed_run_review。
唯一可使用 offline recovery 的 failed run 是
`upl_tpi_gpu_Debug_B_debug2steps_r1`，原 failure 必须精准匹配错误模式 postcheck。
root job 额外提供：

```text
completed_run_review = {path,bytes,mtime_ns}
```

该值只能指向独立 passed 的
`logs/upl_tpi_gpu_Debug_B_debug2steps_r1.completed_run_review_r2.json`。
`upl_tpi_gpu_completed_run_audit_r2.accept_review` 严格核原run/call/start/status绑定、
错误分类、原 failed 标志、审计原三出口、所有原postcondition、16fixture与memcheck；
原 run 不作任何 passed 改写。只从该审计读取已完成文件检查 metadata。
不推广豁免其他失败、标签、方案、时间窗或真实求解错误。

## 一次独立读取

同旧 reader：Debug B 两更新/2帧，或 Release A/B/C startup015/344帧。
root admission stage 为 `upl_tpi_gpu_native_r3.read_admission`，passed/action_only=true，
job 和 frozen inputs 沿原 r1 schema；仅特定恢复 job 加上 completed_run_review。
inputs 另含 audit脚本/note、旧 CPP/note/build/program/runtime，以及新脚本/note。

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_gpu_native_r3.py read --execution-authorized --admission ROOT_READ.json
```

输出使用新 `outputs/<jobtag>_native_r3`、`logs/<jobtag>.native_r3.json` 和
`logs/<jobtag>.native_r3.call.json`。旧 r1 或新 r2 的输出、attempt call/log/失败收据
任一已存在即阻止重复读取；先检查实际活动读取器和数据目录 owner。
2/344帧、1040 IDs、22 typed arrays、真实scalar clock/Step/dt、signed dterror、
ledger/fixed markers/排水/HG原门、FMA两种精确允许路径完全不变。
实际 completion stage 必须还是 r1 CPP protocol，不改头或数据。

## 分开的离线 review

review 同样独立 root 准入：stage=`upl_tpi_gpu_native_r3.review_admission`。
消费已 passed 的 `.native_r3.json` 和同 native_r3 导出；输出
`logs/<jobtag>.native_review_r2.json`。原科学函数 `hg_run/load_plan/prefix_A/sidecar/cross_cpu`
逐字保留。A默认分支仍无sidecar；B/C侧车、实际环境、policy/summary、保存J精确FMA
两路径、跨CPU界限和原case时间序列检查均不变。

PorePressRate仍为旧缩放endpoint residual诊断而非真实dp/dt。
22原始数组及真实clock/signed比较不能被common26替代；A vs旧GPU真实shared步可严格
作原生byte比较，B/C跨模型差别不套5Pa门。短Debug仍不代表Release位真值，短一致性
不代表完整固结/重启/理论/物理验收。没有自动下一solver/native/VTK/half链。

## r3 的最小衍生修正

相对冻结native_r2，只改为消费修正后的audit_r2，使用新reviewer/admission和native_r3
输出路径。r1/r2/r3任一已有attempt都阻止重复read；原失败audit_r1/run/status不改。
读取器仍是原native_r1 CPP/exe/build/runtime，未复制或重建。
`hg_run/load_plan/prefix_A/sidecar/cross_cpu`全部逐字保留；没有新科学门或数值容差。
本稿未执行，不能把脚本作者完成当作native或物理通过。
