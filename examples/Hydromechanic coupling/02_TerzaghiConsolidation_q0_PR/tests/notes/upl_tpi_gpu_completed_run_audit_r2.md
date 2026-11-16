# GPU 已完成但模式后检查失败的独立离线审计 r2

本稿只新增 `tests/support/upl_tpi_gpu_completed_run_audit_r2.py` 和本说明。
不修改求解器、读取器、原 runner、原失败记录、二进制粒子或 source/build 归档。
作者阶段没有执行本审计、native、help、solver、build、Git，也没有新增 watcher。

## 精确适用范围

仅 `upl_tpi_gpu_Debug_B_debug2steps_r1`；原 run 必须仍是
`stage=upl_tpi_gpu_run_r1.run`、`passed=false`，且失败文字精确为
`Actual GPU normal finish/steps/no-exclusion differs`。
原 status 必须仍是 `failed_preserved`，未启动后续任务；任何其他失败一律拒绝。

错误的原模式门要求 `Stable - Pos-Double - Single-GPU`。实际旧 GPU
和新 GPU 都应为 `Stable - Pos-Cell - Single-GPU`。
`SavePosDouble` 是保存位置精度，不是内部 RunMode。本审计不改原 run/status
为 passed；输出新的、分别标明已完成求解与原生审查仍待完成的审计收据。

## 原样保留的必要检查

- 原 start/call/run/status/root admission 的 stat 绑定，历史 owner/tool/target
  PID、创建时间、父子关系、exe/argv；真实 Popen/tool Win32/target Win32 均为 0，
  target 原生句柄在 wait 前取得。不得从退出状态推算未保存粒子时刻。
- 原 program/source_build/prepared、私有源条目、runtime、原输入 seed、全部 consumed
  与已封存 outputs 的 stat；不扫描旧 objects/BI4 的 SHA。
- 原修正后 Debug build/source269/111对象身份；输入和实际 selector B 不变。
- 通过 AST 比较，新的 `check_output` 与冻结旧函数只有一处 mode 字符串差别。
  随后仅调用新的纯文件 `check_output`，不调用 context/run_owned/main。
- 全部原正常 finish、2 steps、0 exclusion、1040 IDs 的 Run.csv 数目、2帧存在性，
  HG force/update/rate/cache 次数、finite/nonnegative、dt/tau<=.2、spin<.01、
  原 16-case device marker恰1次、memcheck ERROR SUMMARY 0 errors。
- 基座旧 GPU 真实 Pos-Cell 模式；原 seed 计算的 binary64 scalar+=dt 计划与已封存
  两行 CSV 完全一致。时钟只是计划审查；实际 native 数组/时钟仍待独立读取。
- 原 console/Run.out 的首个错误与最后原样 PART 文本必须与封存 run 一致。

## 独立准入、唯一新输出

入口只有：

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_gpu_completed_run_audit_r2.py --execution-authorized --admission ROOT_REVIEWED.json
```

root admission 要求 `stage=upl_tpi_gpu_completed_run_audit_r2.audit_admission`、
`passed=true`、`audit_only=true`、`tag=upl_tpi_gpu_Debug_B_debug2steps_r1`。
`inputs` 是所有实际消费文件的 `{path,bytes,mtime_ns}`。包含新脚本/本 note、
冻结 r1 runner/note、新 r2 runner/note、CPU 公用 helper，原 run/start/call/status/
root admission、run 内 consumed/outputs_stat_only/source_entries/runtime、program/
build/prepared/plan/tool stat，console、memcheck、Run.out/Run.csv/2 BI4、旧 GPU
run/Run.out、原 seed XML/BI4/NBI4 及 original CPU full run。任何缺项/变动即失败。

唯一新收据：
`logs/upl_tpi_gpu_Debug_B_debug2steps_r1.completed_run_review_r2.json`。
已有成功、失败或部分收据都阻止再次执行，不覆盖。输出包括原失败的 stat引用、
`original_run_passed=false`、`all_original_postconditions_except_bad_mode_passed`、
`completed_output_checks`、原出口和终态文本；`physical_acceptance=false`。
没有自动解码、后处理、求解、构建、队列或通知。

## native r3 的有限消费

`accept_review` 是纯收据 eligibility 检查，不运行本审计。
新 native r3 只有在 root 的 job.completed_run_review 指向上述 passed 审计，
且准确绑定仍 failed 的原 run/call/start/status 和唯一错误分类时，才允许
Debug 已完成数据进入一次独立 read。其他 failed run 不享有该入口。
同一读取器 CPP/program/build/runtime 保留 r1 身份，不复制、不重建。
审计通过不等于 native/sidecar/HG/物理验收。

## r2 与保留的失败审计

r1 实际审计失败保留在 `logs/upl_tpi_gpu_Debug_B_debug2steps_r1.completed_run_review_r1.json`，
首因为 `Actual patched Debug build/source preparation binding differs`。
只读逐项检查原数据18组字典比较：唯一不等的是 build.program 附有已经记录的 sha256，
run.program 仅含 path/bytes/mtime_ns。三项实际 stat完全一致，其余 owner/tool/target、
start/call/run/status、source_prepare、原admission、clock/environment比较均相同。

本版唯一已有检查修正：program binding仅比较上述stat三字段。额外sha字段保留，
不删除、不重新计算hash；方程、程序、原门槛、源码/运行绑定和check_output都不变。
另用新stage/note/输出身份，并stat绑定原failed审计和它的admission及作者稿。
新收据标明 `previous_failed_audit`、`program_binding_stat_fields_only=true`。
该旧失败必须仍是r1 audit的精确首因且invocations为0，不可用它替代新的passed审计。

实际执行只待root单独准入；本作者稿未执行。已完成求解绝不重跑。
