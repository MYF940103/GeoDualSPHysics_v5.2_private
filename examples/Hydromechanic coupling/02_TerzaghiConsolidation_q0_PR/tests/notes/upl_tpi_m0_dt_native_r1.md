# C02 M0 dt：四个窄profile的独立原生适配器作者稿

尚未执行build/read/review、程序、solver或Git。只新增同名CPP、Python与本文；
不改被冻结的M0 r1/r2 header/prepare、公共src或旧readers，不读退役13s partial。
每个action和job由根独立准入，没有自动链、half、reference、20us或full。

## 精确profile与复用范围

| mode | 后端/配置 | dt | updates | native saves | post-open |
|---|---|---|---:|---:|---:|
| cpu_debug2ms | CPU DebugCPU / B | tD/1000 | 200 | 18 | 0 |
| debug2 | GPU Debug / B | tD/1000 | 2 | 2 | 0 |
| Acontrol | GPU Release / A | 原6.250143051147461us | 320 | 18 | 0 |
| window2s | GPU Release / B | tD/1000 | 199996 | 1263 | 1159 |

tD=.0100002288818359375；新dt=1.0000228881835938e-5s。2s的200000是
runner uppercap，不是实际完成数；TimeMax先在199996步终止，11590个真
排水接收检查。各自完整scalar+=dt独立回放，包括CPU200的末时刻与A320
相差1ulp也不伪造共同钟。A320及两个Debug都是forced final；2s按真实
TimeMax first crossing/plan审查，不能沿用旧1600阈值或旧1682表。

CPP从已审 `upl_tpi_gpu_full2tv_native_r1.cpp` 窄fork，保留LoadNative、
Initial、Read的22typed数组、全部1040IDs/1000soil+40fixed、原finite/
elastic/noout/geometry/P0/float excess、J/n/V/rho/恒k ledger、fixed marker、
clock/signed与真FS2/3 drainage谓词。只变四profile的dt/DrainStep/声明计数、
backend/window/source标签；CPU/GPU标签自身不证明后端，实际owner链另核。
8列plan每个已保存状态及每次加法均核对；没有interpolation或metadata重写。

Python复用原neutral-loader真实CL/link recipe和既有owned invoke，build只
编新reader TU/链接，不运行help/native/solver；原架构/系统库和runtime保留。
压力侧车公式从已审full/r5 GPU与CPU r1复制，仅将dt/profile/drain-step改为
当前job参数。GPU保持RN float+signed FTZ、独立double除/加及合法J的nonfused/
fused两路径，不加ULP；CPU保持其原RN/plain J表达式。Release B独立绑定
真实保留CUDA object/PTX证据；Debug采用同一源/flags及实际rows，不冒称另有
Debug PTX观察或CPU两步对照。没有把跨dt变化套进5Pa half或跨模型等价门。

原HG Run.out生命周期/cache与dt/tau<=.2、spin<.01照旧独立审，不使用base
DtVariable的HG成员。真正r2 policy stage为upl_tpi_m0_dt_r2，文件名仍
UplTpiM0DtR1.*；dt_policy=M0_Eq40_Rh1、R_h=1。policy和summary都要求
HG_limit_reference_available=false，每row的HGref必须为DBL_MAX unavailable
sentinel，不当成实际HG时间。pressure侧车及原22schema均不变。

## M0 interval与原signed诊断

每真实保存interval严格一行，先核完整行数（不靠会吞尾行的zip）、19列schema、
实际part/time/Step/dt、每phase增量及累计计数。真实限定Symplectic为每完整步
Pre/Cor/Endpoint各一次；不把128/199996步误说成保存了同样多逐ID状态。

非初始row按原double表达式核：selected=min(min(force,wave+AV),Rh*hydro)，
error=actualFixedDt-selected，并使error、侧车maxerror及native原clock.bin中
signed dterror逐bit相同；原<=1e-14、非空interval门保留。最终summary的所有
min/max/64位计数独立对保存interval归约，不把旧Kw wave当方法硬界。

initial empty行的DBL_MAX/-DBL_MAX是明确sentinel，不是物理极值或原生dterror。
保留原native初始0/有符号诊断并由CPP原谓词审查，不删除/置零/掩盖。初始
sentinel不参与非初始min/max汇总；最后Saved reset后仍核总summary的计数与极值。

Acontrol需新旧GPU_A_startup015按真实time bits及saved Step join，仅前17
记录共享。核original15/physical/common_j_theta/soil_n/clock五exports全payload
（clock包含初始与非初始signed）逐byte；保留18/344声明头，forced320末态
不共享。五exports不覆盖全部22raw数组，不升级成raw22全数组位证明。

## 根独立action/输入清单

入口：`python -B tests/support/upl_tpi_m0_dt_native_r1.py build|read|review
--execution-authorized --admission ROOT_JSON`。
stage=`upl_tpi_m0_dt_native_r1.{action}_admission`，passed=true、action_only=true。
read/review的job仅需tag，按真实run派生mode/config/scheme/program/plan；
接受真实root run_r1或run_r2 stage，但必须原job/program/source/owner精确绑定。
CPU可绑定实际build_r3而GPU保持已完成r2，不伪改原run或原失败。

所有action最小共同inputs：本3作者文件、upl_tpi_cpu_build_r2.py、
upl_tpi_gpu_full2tv_native_r1.py及neutral `upl_cpu_public_native_r1.cpp`。

build额外inputs由原BASE recipe列取：

- logs/upl_bigstep_native_r1.build.json、同Compile.call.json/Link.call.json。
- b.VCVARS，BASE.actual_archived_headers与runtime中每个文件，实际CL/link程序。
- 原link arguments中全部obj/lib，排除将被新reader.obj替换的那一个原obj。

build产物为 outputs/upl_tpi_m0_dt_native_r1_build、logs同标签.build.json，
一套reader.exe供四profile使用；所有PDB/ILK/obj/输出私有，原有ILK只改一个。

read/review共同额外inputs：真实tag.run/start/call及run中program/source_build/
root_admission/plan，所选实际run_r1或run_r2 script/note、3个生成seed/runtime，
实际build.prepared、该source_root/upl_tpi_m0_dt_r2.h，Run.out；GPU还要真实
console，Debug需memcheck.log。child真实Popen/Win32/creation/exe/argv/parent
和tool/target角色核对，不能只看正常结束文字。

read再绑定本reader.build.json/program/runtime、psutil模块，先查无活动/既有
reader及输出。只调用一次 `--read CPU|GPU DATA PLAN PROFILE FRESHOUT`。
输出 `<tag>_native_m0_r1`、logs/<tag>.native_m0_r1.{call.json,log,json}。

review再绑定该唯一read收据/call、全部native产品和原pressure及M0 policy/
csv/summary。A须绑定实际A.native_review_r4、A_native_r4/completion和五exports；
Release B须按原ptx_evidence绑定原PTX_BINDING、dump调用/日志/对象、真实CUDA
compile call（只读，不新cuobjdump）。最终logs/<tag>.native_review_m0_r1.json。

原run的policy_environment是意图字段，不冒充完整子进程环境dump；真正新方法
执行证据是已绑定r2源/程序、实际policy/interval及native signed表达式。失败保留
首因/partial，完成solver后仅分析问题只修离线派生，不自动重解码/重算/queue。
native通过仍不是2s压力/沉降/100层交替模态的物理/理论验收，更不是完整2Tv。
