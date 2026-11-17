# P3 full10us 原生读取与独立方法审查作者稿

本轮只新增 `tests/support/upl_tpi_p3_full_native_r1.py` 和本说明。没有调用任何 context/main、求解器、读取器、编译、数据分析或 Git；不修改当前运行中的 full runner、计划、程序、冻结源码/helper、旧收据或输出。根线程可在长算期间独立审稿；本稿完成不是求解器继续运行的前置条件。

## 唯一真实任务和两阶段接口

只消费将来真正完成的 `upl_tpi_p3_B10us_full2tv_GPU_r1`，实际 owner stage 为 `upl_tpi_p3_full_run_r1.run`，Release/GPU/B/full2tv。独立 `read` 和 `review` 各要求一次根准入；没有自动串行、重试、通知、下一个 solver、half 或 reference。正常求解出口仍只代表等待原生与物理审查。

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_p3_full_native_r1.py read --admission ROOT_READ_JSON --execution-authorized
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_p3_full_native_r1.py review --admission ROOT_REVIEW_JSON --execution-authorized
```

准入：`stage=upl_tpi_p3_full_native_r1.<read|review>_admission`、`passed=true`、`action_only=true`、唯一 `job.tag`，`inputs` 为无重复的真实 `{path,bytes,mtime_ns}` 清单。两个阶段分别产生新收据：

- `logs/<JOB>.native_full10us_r1.json`，stage `upl_tpi_p3_full_native_r1.read`；
- `logs/<JOB>.native_review_full10us_r1.json`，stage `upl_tpi_p3_full_native_r1.review`；
- 唯一新原生输出为 `outputs/<JOB>_native_full10us_r1/`。

读取器只使用已经独立建成的 `upl_tpi_m0_full10us_native_r1.exe`，不是旧 M0 四 profile 程序。真实 CLI 是 `--read GPU DATA PLAN_CSV full2tv10us FRESHOUT`。其中 `full2tv` 是真实 solver mode，`full2tv10us` 是新工具唯一支持的 native profile；二者分别记录，不借修改旧模块全局变量混用。工具 completion 保持其诚实标签 `upl_tpi_m0_full10us_native_r1`、`GPU_M0_full10us_private`。

## 真实 provenance 和时钟

在任何读取前，检查完成的实际 run/status/start/call、原根准入、所选新 full Release build、source preparation、实际 EXE/runtime、full input/seed/plan 和原 P3 窗口 argv。程序/source 使用已审 `full_short.source_build` 的纯只读身份函数，不调用旧或新 runner context/main，不启动程序。所选源闭包仍为 Single-only 时间域拓展，既有压力 helper、CUDA、原数值公式和 ABI 不改。

原始 Popen 与 Win32 tool/target 出口均须 0；Release 的 tool 必须实际就是 solver。真实 target 的 PID/创建时间/完整 exe/argv/parent、原句柄在 wait 前取得、source build 和完整六 selector 环境均保持原独立所有权审查。数据目录显式关联到真实新 `output_directory/data`。原 owner 的 terminal status 必须绑定同一真实 run，不能由通知或进程不存在推断完成。

新 full 只把已完成 P3 窗口的 input prefix、output directory 和唯一 `-nsteps:200000` 改成根已准备的 full prefix、fresh output 和 `-nsteps:7288262`；其余 argv 原样。full input preparation 必须真实 passed，原 seed、计划及 clock 绑定一致，XML 仅 TimeMax 值变为 `72.88428690075874`。本 wrapper 不创建或改写计划，不操作暂停的 C08 或任何进程。

精确 profile：dt `1.0000228881835938e-5 s`；7,288,262 completed updates；1,653 帧；实际 end `72.88428815806371 s`。clock 用 `array('d')` 逐项执行 `clock[-1] + dt`，含初态共 7,288,263 个 binary64，约 58.3 MB。没有 `n*dt` 替代时钟。每个八列计划行核实际保存时间、零基 Step、dt、原 target 和 pre/post mask；target 调用原已审输出时间公式，只处理 1,653 个保存节点。末态必须为原 TimeMax 首次真实 scalar crossing。

事件 completed1000 是 pre-open 的 part103，首个 post-open 为 completed1001 的 part104。完整 post-open 1,549 帧，每帧 10 个真实 FS2/3 接收点，共 15,490 次排水零压检查。原事件压力必须仍有真实非零值，不借新脚本提前归零。

## 唯一读取及原始守护

`pin_reader` 绑定新 full10us build、EXE、四个并列 runtime、原实际工具双出口及根独立 reader 身份/原守护字节保留证明。它如实是 CPU-only Release ABI 工具；这是离线 BI4 loader，不是 CPU Debug solver。没有新编译或 help 调用。

read 拒绝已有输出目录、调用/日志或读收据；执行前检查真实同名/同 data active reader，防止重复解码。只有明确新准入后，直接调用这个全程工具一次，独立保存真实 Popen/Win32 出口和新调用日志。其完整22数组/1040 IDs/实际 scalar 时钟与 Step/原 signed dterror/P0/float excess/双精度应力/J/n/V/rho/k ledger/fixed markers/FS/几何/排水及有限性守护均由既有 body 原样执行。

完成声明进一步核全1653帧、1652个非初态 signed 非空区间、1,653,000 soil ledger 行、66,120 fixed marker 行、1,719,120 J/theta 行与事件/排水覆盖。初态 signed 值不改写，不把 `-DBL_MAX` sentinel 归零。新 native manifest/真实 completion 和工具调用绑定保持独立；没有物理压力或应力验收阈值替换。

如果求解已完成但 reader 或派生审查失败，保留新原生/partial、实际首因和 false 收据。这个 wrapper 不重跑已完成 solver、不自动覆盖或重复 reader。原生成功也不使此前失败的运行标签自动变 passed。

## 独立全程方法审查

review 先验证这个真实 full read、原调用 argv/出口、全部产品 stat 和实际 completion。继而直接调用既有已审的 P3 纯函数：

- `science.m0.hg_run(job)`：实际原 HG 生命周期、cache、dt/tau 与 spin 原门；不是新 HG 模型或能量证书。
- `science.intervals(ad,job)`：完整五相/每步三 endpoint、全部1653 interval 行、1652个非初态 signed bit 算术和原始初态 sentinels，原必要步长守护不变。
- `science.pressure(ad,job)`：全部1,653,000 saved-ID triplets、三个完整 Rγ/S、实际 `q2=p1_BC`、`q3=p2_BC`、一次 J/material/history 提交、陈旧 provisional finalP 和原 BC/history/计数守护，原 GPU RN/FTZ 和允许的原 J 表达式不变。
- 既有 `ptx_evidence(ad,job)`：只读取原真实 PTX/编译/链接 provenance，核新 full build 仍含那个相同 CUDA 对象；不新运行 cuobjdump、编译或 GPU kernel。独立旧证据支持实际 RN divide/add/float FTZ，而不是为比较放宽 ULP。

原 `PorePressRate` 仍只描述在实际 p2 处第三轮 R3 的旧尺度 residual，不是 dp/dt、也不是在 p3 处重新计算的残差。原数值函数全部保持，不把有限 Kw 与 M0 跨模型差异当作 5Pa half 门；本稿没有新 half 或参考求解。

## 与真正旧2秒窗口的五导出前缀

只对保留的 `upl_tpi_p3_B10us_window2s_GPU_r1` 实际 passed run、唯一 native read/真实 reader 出口和独立 P3 review，核其原 plans、IDs、列模式及完整文件大小。五个导出为 `original15.bin`、`physical.bin`、`common_j_theta.bin`、`soil_n.bin`、`clock.bin`。两侧原头分别保留1263/1653，不改 frame count、layout 或 payload。

只有原前 **1262** 条、index0–1261 的实际 step/time 完全共有。先核其全部八个计划字段，再逐记录比较五个导出的真实字节，包括初态和 signed clock 所有28字节。固定/soil ID 与 columns CSV 也直接逐 byte 比较，不用 SHA。

原窗口 forced 最末 `N=199996`、saved Step199995、actual2.00000577545594 不共有；full 的 part1262 是普通 `N=200000`、saved Step199999、actual2.0000457763714676。wrapper 读取这两个真实 payload 时间并明确验证区别，旧末帧不加入 prefix；剩余 full 记录由全程 native/方法审查覆盖。没有插值、near-time 等价、假 header 重写、额外 ULP 或容差。

这只证明五个导出、IDs 和实际 clock 的共有保存态逐字节一致。原22 native 数组各自守护独立通过，不由五个导出冒称全22 raw bit proof；隐藏 HG/history 的跨运行字节相等也不由这些产品推出。

## 产物和后续限制

新收据记录 `HG_original_guards`、`method_intervals`、原实际 PTX 证据、`pressure_three_rounds`、`window_prefix`、真实 reader identity/completion/manifest 和全部消费 stat。`solver_invocations=build_invocations=VTK_invocations=Git_invocations=SHA_scans=queue_invocations=0`；read 时 reader_invocations1，review 为0。

`physical_acceptance`、`physical_theory_or_full_cycle_acceptance` 始终 false。原生/方法/共有前缀通过后，根线程另行审查压力、材料沉降、总应力、J/n/rho、100层模态和各自有限Kw/M0未拟合参考的全程精度与效率；本稿不自动调用科学分析、绘图、后续 solver 或正式发包。
