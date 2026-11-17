# C02 TPI 10 µs 全程原生读取器作者稿

本稿准备独立的全程读取工具，不准入或启动 full2Tv 求解，也不自动解码。旧 `upl_tpi_m0_dt_native_r1.cpp`、程序、收据和输出保持原样；未来只有根线程分别审查、构建和原生读取。作者阶段未调用编译器、链接器、读取器或求解器。

## 新文件和接口

- `tests/support/upl_tpi_m0_full10us_native_r1.cpp`：唯一 `GPU/full2tv10us` 入口。
- `tests/support/upl_tpi_m0_full10us_native_build_r1.py`：仅独立构建工具，不含 read/review 或 solver phase。
- 本说明；709 teardown 另记在 `upl_tpi_p3_teardown_709_r1.md`，不改旧性能输出。

工具未来 CLI：

```text
upl_tpi_m0_full10us_native_r1.exe --read GPU DATA PLAN_CSV full2tv10us FRESHOUT
```

完成标签为 `stage=upl_tpi_m0_full10us_native_r1`、`backend=GPU_M0_full10us_private`、`window=full2tv10us`。CLI 的 GPU 字符串不证明所读求解器后端；真实程序、owner、输入、退出、唯一读取准入和 P3 五相/三轮侧车仍需后续独立 wrapper 审查。本稿没有那个 wrapper，不冒用旧四 profile 或旧 6.25 µs 全程 wrapper。

## 精确 full profile

| 项目 | 声明 |
|---|---:|
| 固定步长 | `(5243 * 2^-19) / 1000 = 1.0000228881835938e-5 s` |
| completed updates | 7,288,262 |
| 最后原生零基 `Step` | 7,288,261 |
| PART 帧数 | 1,653，含初态 |
| 原配置 `TimeMax` | 72.88428690075874 s |
| 实际逐次 binary64 `+=dt` 终点 | 72.88428815806371 s |
| 原事件 completed step | 1,000，事件保存态仍 pre-open |
| 首个 post-open 保存步 | 1,001 |
| post-open 帧数 | 1,549 |
| true FSType2/3 零压检查数 | 15,490，即每个 post-open 帧 10 个材料接收点 |
| 1040-ID typed22/ledger | 1,000 soil + 40 fixed，每帧完整检查 |
| 非初态 signed dterror 区间 | 1,652，保留原符号和原 `<=1e-14 s` 守护 |

该真实终点是原 M0 `Cv` 换算 2Tv 的 `TimeMax` 首个 scalar crossing，不能用 `N*dt` 替代。计划 CSV 使用原八列 `part,completed_steps,saved_step,time_s,dt_s,post_open_by_completed_step,target_time_s,forced_final`；每个保存态仍验证第一次 target crossing，terminal forced save 仍按原字段验证。继承的 completion 键 `final_frame_forced_by_step_stop` 直接报告原 CSV `forced_final`，并非读取器独立证明退出是 step cap 还是 TimeMax；后续必须结合真实 run/argv 说明。

`LoadNative`、`Initial`、`Read` 的 completion 之前主体逐字节保留原 M0 版本。保留原 22 数组类型/有限性、全部 IDs、2D/periX/质量/几何、实际时钟和零基 Step、signed 空区间处理、固定材料 P0、float excess、double stress display、J/n/V/rho/k ledger、fixed 零标记、排水和写出检查。这里只改声明 profile、CLI、输出标签；没有压力、应力、几何或物理验收阈值修改。

输出仍是原五个二进制导出及相同 CSV/schema：`original15.bin`、`physical.bin`、`clock.bin`、`common_j_theta.bin`、`soil_n.bin` 和原 IDs/history/ledger/fixed/columns 等。`physical.bin` 是 common26，不冒称全 22 raw arrays bit export；common26 的 column21 仍为真实 `ExcessPorePress`，独立原生 PosDiv/V/rho/k 检查不被它取代。

与已保留 2 s P3 窗仅前 **1,262** 个记录存在真实 shared clock/step；其 forced 最末 `N=199996` 不属于将来全程的共同序列。未来应保留 1263/1653 原头和全部 signed clock 再逐记录比较；本稿不承诺尚不存在 full 输出的 bit prefix。

## 真实构建 recipe 与 ABI

实际成功基线为 `logs/upl_tpi_m0_dt_native_r1.build.json` 及同标签 `.compile.call.json`、`.link.call.json`；原 compile 为 MSVC 14.36.32532、`/std:c++17 /O2 /MT /fp:precise /openmp`，实际 SDK 10.0.22000.0。它是 **CPU-only Release ABI 原生工具**，不是 CPU Debug solver 或 `/MTd` 工具。沿用真实 recipe 避免只把新一 TU 改 Debug 而混入 Release CRT/迭代器 ABI。

新构建只编译新 reader TU；真实旧 link 的 86 个对象里仅替换旧 reader.obj，保留另外 85 个已有对象和 17 个显式库，不重编 solver、不运行 NVCC。CL/Link 其余 flags/库次序保持；所有 EXE/obj/PDB/ILK/依赖输出和四个并列 runtime 放在全新 `tests/outputs/upl_tpi_m0_full10us_native_r1_build/`。原路径不写入，旧程序不覆盖。

构建稿使用既有 `upl_tpi_cpu_build_r2.py` 的 stat/read/独立 Win32 句柄工具调用，以及已通过的 `upl_tpi_gpu_full2tv_native_r1.environment`。环境仅保留工具调用状态和 stderr，不把 `set` 的完整环境输出写日志。固定 MSVC ABI，并在工具调用前检查环境 SDK22000；编译后完整 includes 集必须与实际旧 dependencies.json 完全相同，且源必须是新 CPP。旧调用中实际 includes 名单证明当时名称；额外系统 header 的本次 stat 是新准入时绑定，不伪称旧编译时已捕获其 mtime。

未来独立 build CLI：

```text
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_tpi_m0_full10us_native_build_r1.py --root-admission ADMISSION_JSON --execution-authorized
```

准入应为 `stage=upl_tpi_m0_full10us_native_r1.build_admission`、`passed=true`、`action_only=true`，`inputs` 使用真实 `{path,bytes,mtime_ns}`。所消费清单由 `Admission.pin/context` 事前可完整审阅：新 CPP/build/note、旧 CPP/中立 loader、两个纯 helper、原成功 build/三个 call/依赖和环境批处理、实际工具/vcvars、旧 original_dependencies、原 136 includes 的本次 stat、85 retained 对象/17 库，以及实际四 runtime 源。原收据自有 stat 逐项比对；不扫 SHA，不改原收据。

构建完成只生成 `logs/upl_tpi_m0_full10us_native_r1.build.json` 和对应新 environment/compile/link 调用证据；记录真实 Popen/Win32 退出、实际 dependencies、runtime copy 和所消费 stat。`solver_invocations=reader_invocations=CUDA_compilations=0`、`physical_acceptance=false`。失败保留新目录、实际工具日志和 false 收据，无自动重试、清理或接续解码。

## 尚待独立完成

根线程全文审稿并决定一次构建；真实 full solver 完成后，另行审查独立 read/review wrapper、原生全部覆盖和真正共同前缀，再进行压力/沉降/总应力/体积与理论的全程物理审查。原生通过本身不能代表完整物理、半步、论文精度、HG 能量或重启验收。
