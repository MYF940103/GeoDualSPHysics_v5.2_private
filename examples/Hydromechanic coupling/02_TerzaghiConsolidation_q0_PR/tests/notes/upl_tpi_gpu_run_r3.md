# GPU P1 bounded runner r3

本稿新增 `support/upl_tpi_gpu_run_r3.py`，不改变冻结 r1/r2、原失败记录或求解数据。
基于 r2；除了本版 note/admission/run stage 身份，只把 Run.csv Hardware 的检测改为
`"gpu" in rows[0]["Hardware"].lower()`。实际旧/新 GPU 的 RunMode 均使用 Pos-Cell。
SavePosDouble是保存位置精度，不是内部RunMode。

实际已完成 Debug 的 Hardware 精确为 `Gpu_0?="NVIDIA GeForce RTX 3050"`，
旧 case-sensitive `"GPU"` 检测误拒。该变化不放宽求解、数量或物理门。

其余原 runner 代码不变：一个独立 root admission、一个新标签、Debug B两更新/2帧
或 Release A/B/C 24000更新/344帧，原 seed/special cadence/6.250143051147461e-6 s，
原真实Popen及Win32句柄、fixture、HG、no-exclusion、native存在、memcheck门。
root stage 改为 `upl_tpi_gpu_run_r3.run_admission`；入口仍需 --execution-authorized
和 --admission。实际输出保持 tag.run/start/call/status/clock 等原格式，新标签才能运行。

旧 Debug B 两更新求解已经完成，不通过这个runner重跑。原run/status仍false，
两个旧failed audit仍保留；由独立audit_r3与native_r4审旧数据。此稿未执行。
没有自动native/VTK/下一solver/half链，不触碰暂停C08或旧源码/程序。
