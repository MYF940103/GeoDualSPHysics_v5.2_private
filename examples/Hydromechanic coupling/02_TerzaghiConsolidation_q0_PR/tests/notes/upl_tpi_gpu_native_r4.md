# GPU P1 native reviewer r4

本稿新增 `support/upl_tpi_gpu_native_r4.py`，未执行。
相对冻结r3只换import为audit_r3、新stage/note/reviewer_r4和输出_r4，
并保护r1/r2/r3/r4任一已有read attempt，避免重复解码。
原Cpp、旧中性loader和所有旧作者稿/failed记录不改。

实际reader仍为`outputs/upl_tpi_gpu_native_r1_build/upl_tpi_gpu_native_r1.exe`，
actualbuild为`logs/upl_tpi_gpu_native_r1.build.json`，CPP为原support/native_r1.cpp。
它们的真实stage/protocol仍r1，并stat绑定旧CPP/note/build/program/runtime destination。
收据明确reader_implementation_r1与reviewer_r4；CLI没有build分支。

root job schema沿前版；特殊已完成Debug job额外提供completed_run_review stat，
只能指向`.completed_run_review_r3.json`，严格通过audit_r3.accept_review，
同时保持原run/status及旧audit_r1/r2失败记录不变。其他failed数据一律拒绝。
正常未来passed新run直接消费原完成收据，不使用特殊恢复入口。

两个动作独立准入：`upl_tpi_gpu_native_r4.read_admission`或
`upl_tpi_gpu_native_r4.review_admission`，passed/action_only=true，inputs实际stat。
新read输出`outputs/<tag>_native_r4`与`logs/<tag>.native_r4.json`；新review输出
`logs/<tag>.native_review_r4.json`。任何旧或本版partial/attempt均保护，先核活动reader。
先read通过后才能review；没有自动下一动作。

实际2/344帧、1040IDs、22typed数组、scalar时钟/Step/dt/signeddterror、ledger、
fixed markers、排水/HG、FMA精确双路径和sidecar物理门均未改。
`hg_run/load_plan/prefix_A/sidecar/cross_cpu`相对r1/r2/r3逐字相同。
B/C跨模型差异不套5Pa等价门；A真实shared旧GPU前缀仍须真实原始bit核对。
PorePressRate仍旧缩放endpoint residual诊断，不是真实dp/dt。
短窗完成不等于完整固结/理论/重启/物理验收，不额外solver、half、VTK或build。
