# ReleaseShepard smoke 离线准入复核（作者稿，未执行）

只新增同名support脚本和本说明，复用已冻结jobs的纯计量核验函数；不调用prepare/run/build/reader或通知，不改旧文件。固定输入为 `logs/upl_c08_shepard_smoke_GPU_r1.run.json` 与根独立生成的 `logs/upl_c08_shepard_smoke_GPU_r1.native_r1.json`。后者顶层必须有passed、consumed_stats_unchanged、source_run（本smoke实际run的stat）、actual_call、completion、metadata、outputs或files；原守卫从实际completion的计数与阈值逐项核验，不要求冗余顶层original_native_guards_passed键。

原始Debug+memcheck80步/2帧/2次真实滤波先正常闭合；独立native call实际Popen/Win32为0且有真实child identity。复核真实memcheck ERROR/LEAK summary全0，按原completion计数保留6805/22/5000/1805、P0/J-ledger/cache/κ、FS正压、signed非空≤1e−14及fixed-plane/keep5/retire255。metadata须两帧ShepardActive=true、damping=false、AS .2/n3/ReleaseOnly与CompletedOnly，2帧每40步保存且不是final-only。

`C08ReleaseShepard.csv`原两行由jobs.metering读取：严格19列、call1/2、Nstep4000039/4000079、completed4000040/4000080、原实际step-start scalar与dt、5000土/interval40；首行P0/J/κ bitcheck performed1/pass true，第二行performed0/pass空。复核函数不重新滤波、不假称每次都有bitcheck。native clocks按真实源时间逐步+=2.5us，原pressure rate、负压、J和任何物理阈值不改。

滤波量S=Σ(nV/Kw·p)不是fluidmass；原两行存储项直接保存在新receipt，含wrapper自由面正压投影，不以S变化0当守恒门。没有绘图、全场raw重读或新增精度判据。

唯一新输出 `logs/upl_c08_shepard_smoke_GPU_r1.review_r1.json`，拒覆盖。window rootAD三Entry依次为smoke_run→本run、smoke_native→本native_r1.json、smoke_review→本review_r1.json；jobs已要求三个passed且native source_run等于smoke_run。通过仅允许根另行考虑window，脚本本身不会启动它，不等于物理验收。

根全文阅读后才执行一次；作者阶段仅AST/UTF-8静态核验，未import/运行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_shepard_smoke_review_r1.py --execution-authorized
```
