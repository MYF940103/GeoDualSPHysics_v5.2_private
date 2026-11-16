# GPU P1 native r5：只读复核真实RN-f32/FTZ压力转换

本轮仅新增 `support/upl_tpi_gpu_native_r5.py` 与本note。未执行本review。
CLI只有review，不带build/read，不重复解码、求解或重建；继续使用已passed的
`<tag>_native_r4`和`.native_r4.json`，真实reader仍native_r1实现。
原B的`.native_review_r4.json`保持failed，原始solver/native仍保留。

## 真实指令和故障因果

唯一已获准只读工具为 `cuobjdump --dump-ptx`，输入本次新Release r3 CUDA对象。
真实Popen/Win32均0，前后输入对象/tool stat不变，无GPU kernel/物理求解调用。
证据：`logs/upl_tpi_gpu_Release_r3.raw_write_ptx_r1.{binding.json,call.json,log}`。
实际NVCC compile call为`upl_tpi_gpu_Release_r3.JSphGpu_ker.call.json`，
保留-use_fast_math，未改编译旗标。

原PTX日志指令位置：

- BeginRowsKernel 1481741/1481749：pn/previous由float扩double时`cvt.ftz.f64.f32`；
  1481751/53/55为分开RN double减/乘/加，1481827为`cvt.rn.ftz.f32.f64`。
- GuessKernel 1482569：相同RN float32+FTZ转换。
- PrepareKernel 1483317：q扩double亦带float输入FTZ；1483319 `div.rn.f64`，
  1483321 `add.rn.f64`；1483307 `cvt.rn.ftz.f32.f64`后1483309原样store。
  因此不是FMA、近似division或新的力学/孔压算法差别。

[NVIDIA CUDA11.7 PTX ISA7.7 cvt说明](https://docs.nvidia.com/cuda/archive/11.7.0/parallel-thread-execution/index.html#data-movement-and-conversion-instructions-cvt)
规定FTZ将single-precision非正规输入/结果转为保符号零。
这里复制真实指令语义，不从Python默认双舍入推断CUDA必须保留float subnormal。

独立单遍诊断定位：344000侧车行中20个旧raw重放差异，全部在part1/2，各10行，
均为Python非零float subnormal对GPU有符号零；native最终值与CSV最终值全行bit一致。
最大该差约1.9767627e-39Pa。此统计不是验收容差，不设20行特例。

## 最小重放修正

原sidecar的half/q/raw三处double→float统一使用pressure_f32_ftz：
先原RN float32，随后若0<abs(float32)<2^-126，返回保原符号的0。
所有normal float、正负0、真实Dirichlet +0均精确bit比较；没有ULP/绝对误差容限。
输入也显式复现真实`cvt.ftz.f64.f32`：pn/previous先经相同float-input有符号FTZ，
再升为Python double执行原分开RN减/乘/加；alpha0直接采用FTZ后的pn。
raw的q输入同样先经float-input FTZ，再执行原RN double除/加。
FTZ只作用于float输入/输出转换；double预测与R/S除加、J计算本身没有FTZ或新算式。
单遍统计观察到的pn/previous/endpoint_q非零float subnormal数，原样报告，
不以零数目作新门、不屏蔽历史行或放宽bit检查。源状态一致性、J两种精确FMA路径、
全部时钟和counter门不改。实际可正常观测值不依赖“history一定无subnormal”的隐含假设。

`hg_run/load_plan/prefix_A/cross_cpu`逐字不变；sidecar只上述input/output casts、单遍描述统计与语义字段。
该review仍检查原344帧/1040IDs/22数组资格、真实J/pressure对native、实际schema仍28列、344000行、all226post-open/2260drainchecks、原HG与ledger/clock/signed。
跨CPU原预算不变，不把cross-model当half或物理精度等价。

## 原失败、对象及程序绑定

仅Release B/C startup015既有数据。B必须有准确绑定同job的原r4失败，
错误精确为`Actual beta0 float writeback or original final Dirichlet policy differs`；
C尚未作旧r4 review，不能忽略C任意既有失败。
新review先只读绑定PTX工具call/退出、tool/inputobject、原compile flags和真实build
111objects中相同CUDA对象，再核三个实际kernel各自唯一RN-FTZ转换和raw RNdiv/add。
不再运行cuobjdump，不修改flags/程序/对象。

root admission：`stage=upl_tpi_gpu_native_r5.review_admission`、passed/action_only=true，
沿原job/inputs schema；输入包括本script/note、公用helper/旧readerCPP/note/build/runtime、
原job/run/start/call/program/sourceprepare/plan及native_r4所有消费、sidecar和CPU同方案控制，
另加PTX binding/call/log、CUDAcompilecall、实际CUDAobject/tool和B原r4failed收据。
原文件stat不一致即拒绝；不扫旧objects或BI4 hash。

入口：`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_gpu_native_r5.py review
--execution-authorized --admission ROOT_JSON`。
唯一新输出`logs/<tag>.native_review_r5.json`；任何既有输出(含失败)禁止覆盖。
physical_acceptance=false；无自动native/solver/VTK/half/full/下一程序。
