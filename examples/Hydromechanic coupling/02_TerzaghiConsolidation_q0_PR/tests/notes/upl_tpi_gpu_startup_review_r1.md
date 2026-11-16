# GPU A/B/C startup science：独立纯离线作者稿 r1

本轮仅新增 `tests/support/upl_tpi_gpu_startup_review_r1.py` 和本说明。
没有执行本分析、读取器、求解器、build、help、VTK、hash、Git或新通知。
必须等三个真实Release job各自native read/review passed后，root全读并独立准入。

## 精确来源与实现边界

复用已完成CPU版 `support/upl_tpi_cpu_startup_review_r1.py` 的相同科学定义。
references/describe/figures/science数值过程逐字保留，只load改为真实GPU身份：

- `upl_tpi_gpu_Release_A_startup015_r1`；
- `upl_tpi_gpu_Release_B_startup015_r1`；
- `upl_tpi_gpu_Release_C_startup015_r1`。

每个`.native_review_r4.json`必须是实际passed的`upl_tpi_gpu_native_r4.review`，
original_native_guards_not_relaxed=true，绑定准确Release/scheme/startup015。
读取现有`<tag>_native_r4`；reader completion仍真实r1 CPP协议
`upl_tpi_gpu_native_r1` / `GPU_P1_private`，不伪称新reader。
缺失或失败的任一方案(包括C)立即报告，不用A/B替代三方案。

Run.csv严格24000steps/344frames/1040IDs/40fixed/PartsOut0，Hardware检测casefold
`gpu`，RunMode含真实`Stable - Pos-Cell - Single-GPU`；保留原CellsFull前缀文本。
字段schema已由实际Debug2 GPU输出只读核对；没有把SavePosDouble当Pos-Double模式。
每组保留TSimul/TTotal原token、TSeg/Hardware/RunMode和实际观测steps/s；
它是非隔离、含instrumentation/sidecar的观测，不是受控性能基准。
B/C status保留先前native review中的same-scheme CPU/GPU比较结果，不重跑该比较器；
A默认与旧GPU的真实22rawbit证明属于已passed native review，不能由common26替代。

## 完全相同的科学定义与原门

保留全部344实际时刻、1000土材料ID(40..1039)、40fixed资格与22typed数组，
原始common26列21仍ExcessPorePress，不能当PosDiv。土ledger原n/J/rho及fixed零标记
由原reader审查；本脚本不生成固定粒子替代值。时钟按原scalar+=dt和原plan核对，
不n*dt替换、不插值/改头/筛掉signeddterror。1600步preopen；226post帧/2260真排水检查。

每个100层/10X列在全344帧都参与原材料顶部/底部沉降、孔压、六分量总应力、
J/n/rho、speed、Q和交替列Uz/总应力模态。沉降=-1000*(z-z0)，总应力=effective-pI。
保留全启动波动/负压；原t>=.1-1e-7的100Pa最大层总应力误差和顶部两层gap门不改。
科学门失败仍输出完整图表和失败记录，不把normal/native pass当物理通过。
跨A/B/C是描述性模型差别，不加5Pa/half等价门，不启新half/full任务。

A用finiteKw伴随曲线，B/C共同M0伴随曲线。原XML E2e6/nu.3/k1e-4/rhow1000/
Kw2e8/n0.3/q010000/tD.010000228881835938，H1/g9.81/512 Fourier modes均不拟合。
有限ramp/band/inertia/Jn等使它们仅准静态比较参照，不是精确动态启动真值或精度门。
PorePressRate依然旧缩放endpoint residual诊断，不是B/C实际dpdt。

## 唯一新派生输出与准入

只写`tests/figures/upl_tpi_gpu_startup_review_r1.*`：history/profiles/modes/cross CSV，
metrics.json及history/profiles/modes PNG；所有既有/partial路径禁止覆盖。
新check为`logs/upl_tpi_gpu_startup_review_r1.check.json`；它并非GPU物理发行验收。
每图/表定义和CPU原版相同；三方案使用各自同时间/材料状态，不混CPU作GPU物理数据。

root admission为`stage=upl_tpi_gpu_startup_review_r1.admission`、passed=true、
offline_only=true和全部实际消费inputs stat。包括本script/note、原XML、两份definition
脚本、三个native_review_r4、每组completion/columns/native_ids/physical.bin/soil_n.bin/
clock.bin/history.csv/ledger.csv及实际job.plan、owned Run.csv。无需BI4/旧objects/hash。

入口：`D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_gpu_startup_review_r1.py
--execution-authorized --admission ROOT_JSON`。作者阶段未执行；无自动后续。
