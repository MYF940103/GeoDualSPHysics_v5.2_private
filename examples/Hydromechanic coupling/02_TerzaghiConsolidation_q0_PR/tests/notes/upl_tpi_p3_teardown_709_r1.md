# P3 Nsight 记录中的 teardown 709 附注

这是对已完成唯一性能 probe 的独立附注，不改原失败 run、已通过独立 cost review 或 SQLite/metrics。不是重新 profiling、native 读取或物理验收。

根线程从实际 capture 观察到：

| 实际调用 | 返回值 | capture 时间区间 / ns |
|---|---:|---:|
| `cudaDeviceReset` | 0 | `[55467378005, 55496146071]` |
| 随后的 `cuCtxSynchronize` | 709 | `[55700105155, 55700111173]` |

本机 CUDA 11.7 原头文件 `C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/include/cuda.h:2153` 将 709 定义为 `CUDA_ERROR_CONTEXT_IS_DESTROYED`。相邻说明涵盖已销毁当前 context，或尚未初始化的 primary context。

因此，这次非零 context 查询发生在已成功的 device reset 之后，其错误码含义与 teardown 后 context 不再可用相容。没有采集调用栈，不能仅凭顺序判定调用来自 solver、profiler 或其他具体责任方，也不能把此附注推广为所有 709 都无害。根线程保留的实际 solver/tool/target 三个退出均为 0；原 probe 的 console-marker 不可见失败仍保持 failed，独立 fixture kernel/code/实际退出替代观察证据另在 cost review 中说明，不能改写为原控制台已观察到。

本附注没有重查数据库或执行 CUDA/Nsight 程序，没有修改任何原始输出；它只解释这一个实际 teardown 事件，不证明内存检查、原生字段或物理精度。
