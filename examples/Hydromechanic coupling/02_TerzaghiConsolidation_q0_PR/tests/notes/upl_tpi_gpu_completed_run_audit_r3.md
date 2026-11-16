# GPU 完成记录离线审计 r3

本稿新增 `support/upl_tpi_gpu_completed_run_audit_r3.py`；没有执行审计或任何程序。
只审原已完成 `upl_tpi_gpu_Debug_B_debug2steps_r1`，原run必须仍failed_preserved，
failure精准为 `Actual GPU normal finish/steps/no-exclusion differs`。
不改原run/status、r1/r2 failed audit、原物理程序/原生数据/读取器。

## 两个分类检查修正与stat绑定

原check_output误要求Pos-Double，旧/新GPU实际均Stable - Pos-Cell - Single-GPU。
实际Hardware字段为 `Gpu_0?="NVIDIA GeForce RTX 3050"`；正确检测是忽略大小写的gpu。
AST逐项变换冻结r1的check_output，限定恰好一次mode常量替换和恰好一次Hardware
`.lower()`/gpu替换后，整个函数AST须等同run_r3。没有其他科学/数量门改变。

程序来源比较保留r2三stat方案：path/bytes/mtime_ns完全相同；build中额外已记录
sha256不参与字典直接相等，也不删除或重新hash。
绑定已失败audit_r2的stat、admission和作者稿，旧failure必须仍精确
`Actual GPU Run.csv metadata differs`，无任何solver/reader/build调用。
新stage为 `upl_tpi_gpu_completed_run_audit_r3.audit`，唯一新输出
`logs/upl_tpi_gpu_Debug_B_debug2steps_r1.completed_run_review_r3.json`。
已有输出(包括失败)不得覆盖/重跑。

## 原门完整保留

原start/call/run/status/admission、owner/tool/target creation/exe/argv/parent、真实
Popen/toolWin32/targetWin32均0、wait前取得target句柄；原源/构建/程序/输入/runtime/
consumed/outputsstat、2帧及真实scalar clock计划、原terminal文本全部复核。
完成检查调用run_r3的纯文件check_output，不调用context/run_owned/main。
HG、memcheck、16case marker及原生存在门均不改；native数组/sidecar/物理仍待独立审查。

交稿前仅用现有文本/CSV单独只读核对check_output全部22个predicate：全部true。
实际Steps2/PartFiles2/Np1040/PartsOut0；fixture恰1；memcheck0；HG4/2/2/4、cache3/1，
reference/actual net均0，maxdt/tau=.00497579、spin9.05213e-18；原cap formatter一致。
这份只读核对不是执行本审计，也不替代独立native。

入口：`python -X utf8 -B tests/support/upl_tpi_gpu_completed_run_audit_r3.py
--execution-authorized --admission ROOT_REVIEWED.json`。
root admission：stage=`upl_tpi_gpu_completed_run_audit_r3.audit_admission`、passed=true、
audit_only=true、tag=原Debug标签。inputs列实际消费stat，包括本稿/note、run_r3/note、
冻结原runner/note/CPUhelper、failed audit_r2及其admission/作者稿、原run/start/call/status/
admission及consumed/outputs/source/runtime/stat、memcheck/console/Run.out/CSV/BI4、
旧GPUrun/Run.out和原seed/XML/BI4/NBI4/originalCPUrun。

native_r4通过纯`accept_review`消费新passed审计，只特许这个唯一旧失败标签。
它不把原run改为passed，不能豁免别的失败。输出仍physical_acceptance=false，
没有自动native、solver、build、VTK、Git或新队列。
