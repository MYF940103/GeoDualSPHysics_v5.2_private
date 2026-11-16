# C04 CPU128 native r2：补齐首次准入漏项

新增 `support/upl_tpi_cryer_cpu_native_review_r2.py` 与本文；作者稿，尚未执行。原 r1 脚本、note、失败 receipt、实际 solver和所有原始数据保持不变。仍复用真实旧 `upl_cryer_public_native_DebugCPU_r1/reader.exe`，不重编读器、不重跑求解器。

## 唯一允许恢复的实际 preflight

原 A job `upl_tpi_cryer_cpu_DebugCPU_A_startup128_r1` 已完成 solver，但第一次 native admission 漏列 run 中的 `root_admission`。原 `.native_r1.json` 精确失败为：

```text
Consumed input absent from root admission: <该run.root_admission.path>
```

失败位于 `actual_job`，尚未进入 decode；没有 native 目录、reader call/log，也没有原 receipt 的 reader invocation/product字段。r2 必须独立绑定该失败及原 native admission，实际验证原 inputs 确实缺该 run-root entry；原失败仍为 false，不能改成成功。

root 新 admission 的 `adopt_preflight_failure` 是该原 `.native_r1.json` 的实际 stat。只对上述精确 A 标签、原 first_error 和缺漏项放行，并要求旧 `_native_r1` 目录、`.native_r1.call.json`、`.native_r1.log` 均不存在。旧失败有任何 reader/call/output痕迹、其他原因或其他标签则拒绝；活动原 reader 由既有 decode 逻辑按实际 DATA/输出 argv 拒绝。新 B/C 无 r1尝试，直接使用新 r2，`adopt_preflight_failure` 不设置。

此恢复只解除“未开始读取”的前置审计漏项，绝不采用失败/部分解码，不新增物理试验。r2 没有放宽完成、安全或科学门。

## 新身份与两个独立动作

- stage：`upl_tpi_cryer_cpu_native_review_r2`。
- `--phase native`：新输出 `outputs/<tag>_native_r2`、call/log `<tag>.native_r2.call.json/.log`、receipt `<tag>.native_r2.json`。
- `--phase review`：只读已有成功 r2 解码，receipt `<tag>.native_review_r2.json`；不再启动 reader。

两 phase 分别准入：`stage=upl_tpi_cryer_cpu_native_review_r2.native_admission` 或 `.review_admission`，`passed=true,tag=<actual tag>`；native 另 `one_native_read_only=true`，review 另 `offline_only=true`。`inputs` 全部真实 stat。B/C review 的 `reference_A_review` 为通过的新 A `.native_review_r2.json` 路径字符串，且该文件本身必须在 inputs；r1 A review 不能作此新引用。

tag 仍仅允许原 `upl_tpi_cryer_cpu_DebugCPU_[ABC]_startup128_rN`。新输出/receipt/call/log已有则拒绝；没有自动下一 phase、solver、half、峰窗、PRE、VTK、build、Git 或 hash。

## 完整准入消费清单

为避免再次漏项，root 逐项加入以下文件的**实际 stat**，不猜路径/字段存在性：

**native 和 review 共同的 `actual_job` 输入：**

1. r2 Python、本文、`support/upl_tpi_cryer_cpu_build_r1.py`、实际 Python、`numpy.__file__`、`psutil.__file__`。
2. `logs/<tag>.run.json`、`logs/<tag>.start.json`、run 的 `call.path` 和该 call 的 `log.path`。
3. run 的以下六个 stat 条目各自指向的文件，不能漏 `root_admission`：`program`、`source_build_review`、`original_failed_build`、`prepared`、**`root_admission`**、`plan`。对这些条目执行原 `same` 绑定，而不以重新取当前 stat 掩盖旧身份。
4. 上述 build review 的 `source_program.path`、全部 `runtime[].destination.path`；实际新 program copy 和这些五个 runtime同目录。
5. 原 data 目录的全部 `*.bi4` 和 `*.ibi4`（含两个真正 Part、原 Head/Info），以及 output 的 `Run.csv`、`Run.out`。
6. 需要精确恢复 A preflight 时，再加入原 `<tag>.native_r1.json`、其 `root_admission.path` 指向的原 native admission、原 r1 Python/note；后两项须匹配原 native admission记录的stat。`adopt_preflight_failure` 绑定原失败receipt stat。A review phase也保留这四个审计输入。不存在的旧 native目录/call/log只检查不存在，不能伪造文件stat。

**仅 native decode 另需：**

7. 原真实 `reader.exe`、`logs/upl_cryer_freebody_smoke128_CPU_r1.native.call.json`、reader同目录所有实际 `.dll/.xml`。原 successful reader call内 program stat仍须匹配；不能把新程序名字当旧读器证明。

**仅 offline review 另需：**

8. 新 `<tag>.native_r2.json`、其 `reader_call.path`、新 `_native_r2` 目录全部实际文件（completion、common26、clock、native IDs、summary/center等）。
9. 当前 output 内实际存在的 `UplTpiCpuR1.policy.json/.summary.json/.csv`；A 应不存在，B/C需完整三个。
10. A：原 `upl_cryer_freebody_smoke128_CPU_r1.call.json`、对应 `.native.call.json`，以及原 `_native/completion.json/common26.bin/clock.bin/native_ids.csv`。
11. B/C：新通过 A r2 review及该记录 `native_directory` 下 `common26.bin/clock.bin/completion.json`。`reference_A_review` 不是待执行 job，不创建新控制解。

清单只补实际消费的已存在文件，不递归 hash/重解码旧数据。read阶段产生的新call/products不是启动前输入，完成后才封存；review再以其真实 stat独立准入。

## 科学部分保持原样

`completion`、`common`、`pressure_history` 函数不改：仍核22 typed数组/37181 IDs、8 fixed/37173 soil、实际2帧/128更新/Step127/t2^-13、原 signed dterror非初始非空、ledger/弹性/几何/原半径/FS门。没有排水后帧，不冒称排水后验证。

A 只比较真实保留 CPU128 common26、clock含signed、native_ids原字节；不冒称全22 raw数组 bit证明。B/C两帧74346土体侧车、128生命周期、double leading-LP defect/原唯一 J 算序及原字段逐项检查不改。对 A 的跨模型差异仅描述，不套 half 或 5Pa等价门，也不据短窗宣称理论/峰值或完整验收。
