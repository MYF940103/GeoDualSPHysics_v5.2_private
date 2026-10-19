# GPU G3：设备端弹性沙漏（算子及真实短轨迹通过）

## 2026-10-18 短轨迹场量审查完成

`logs/hg_gpu_g3_fields_r1.check.json`核验六条保留轨迹的输入/输出哈希、原生ID和21个实际时间，比较三后端HG开启及同后端开/关结果。新图`figures/hg_gpu_g3_fields_r1.png`已逐面查看，审图记录`logs/hg_gpu_g3_fields_r1.visual.json`。GPU相对CPU最大孔压差3.05176e-5 Pa、六分量double应力最大差2.53906e-7 Pa；保存位置的顶部/底部材料沉降差为零，仅代表输出分辨率。HG开启相对关闭的最大孔压差约0.00667 Pa，三后端响应相近。两组GPU关闭HG仍与各自G2控制逐位相同。

本轮只有20步/0.0002 s，不是半步、长程或物理验收。G3可冻结后进入GPU向量SPR与固定格点事件同步；长程CPU/GPU精度及速度比较继续执行。正式XML/BAT及Git未修改。

## 当前状态：2026-10-17

真实GPU工程Debug/Release全量重建通过（Release 0警告；Debug已有第三方PDB/运行库及Gm警告54项，0错误）。CPU Debug亦通过。`hg_gpu_hourglass_{Debug,Release}_r1`分别完成42项算子检查，退出码0、所属进程已结束；GPU缓存开/关的H、R、实际Ace及统计逐位一致。CPU/GPU最大率差`1.73472348e-18 m/s^3`、历史差`9.92616735e-24 m/s^2`；独立pair虚功误差最大`6.93889390e-16`。这些是制造场数值，不是固结误差或整机加速比。

收据为`logs/hg_gpu_hourglass_r1.check.json`及两个配置的build/run/check。核验完成后，仅删除`JSph.cpp`的GPU HG禁用检查并修改日志的CPU/GPU标记，设备配置约束仍生效；SPR和固定排水事件继续锁定。下一步真实20步xi=0对G2逐位回归与xi=.1三后端短跑，尚未启动长程或发布正式输入。下文“入口先关闭”的描述保留为执行顺序说明。

随后`hg_gpu_g3_short_r1`五次真实短跑正常完成，终时0.0002 s，dt=1e-5 s，1040原生粒子、各21个PART，无排除。关闭HG的两组GPU各自与G2同后端输出逐位一致。开启HG的三后端均40次施力、20次预测/20次校正历史更新、40次率调用=21次实际计算+19次缓存复用；最大dt/tau约0.00796108，小于原0.2限制。收据`logs/hg_gpu_g3_short_r1.check.json`；独立场量/图审查尚待完成，不能把该短时长理解为半步或2Tv验收。

## 生产代码位置（本轮G3，后续行号可能随SPR移植移动）

| 文件:行 | 功能与目的 |
| --- | --- |
| `source/JSphHourglassGpu.h:18`（新增） | GPU对象、原生ID历史/率、阶段和缓存状态；复用CPU统计定义。 |
| `source/JSphHourglassGpu.cpp:36`（新增） | 分配/释放设备存储；`:85`独立邻域与率缓存；`:147`起四阶段和两次半步历史。 |
| `source/JSphHourglassGpu_ker.h:17`（新增） | 设备粒子、网格和固定大小汇总数据接口。 |
| `source/JSphHourglassGpu_ker.cu:48`（新增） | 原生ID映射/输入核验；`:135` LS，`:171`两端残差率，`:211`施力，`:236`双精度半步累加。 |
| `source/JSphGpuSingle.h:29,40` | 对象声明，仅xi>0时实例化。 |
| `source/JSphGpuSingle.cpp:22,61,70,92,145` | include、初始化、析构、显存统计和与CPU一致的适用范围检查。 |
| `source/JSphGpuSingle.cpp:613,755,766,773,1186` | 力循环与积分四阶段接入、非固定步长HG上限、运行统计。 |
| `source/JSph.cpp:595,1771` | 移除仅HG的GPU禁用分支，日志区分CPU/GPU；SPR/事件禁用仍保留。 |
| `VS/DualSPHysics5Re.vcxproj:459,721,878`及`.filters` | 编译/工程可见性；GPU单元对CPU配置排除。 |
| `doc/xml_format/_FmtXML_ElastoplasticSoil.xml:102` | 同步CPU/GPU算子支持与未完成耦合验收边界。 |

测试支持新增`hg_gpu_hourglass_test.cpp`、`hg_gpu_hourglass_build.ps1`、`hg_gpu_hourglass_run.ps1`、`hg_gpu_g3_short_run.ps1`，均在`tests/support`，不加入求解器工程。新输入仅在`tests/configs`，未修改正式XML/BAT。

基线为`outputs/gpu_g2_verified`，716个文件及源/副本哈希见`logs/gpu_g2_verified.snapshot.json`。G2已通过旧模式0–4精确回归、来源/空间载荷审查及三次真实20步检查；短程场图为`figures/hg_gpu_band_fields_r1.png`，独立审计为`logs/hg_gpu_band_r1.audit.json`。不将其视为2Tv或物理精度验收，原64 eps失败仍保留。

## 本轮修改与数值边界

- 新增`JSphHourglassGpu.h/.cpp`和`JSphHourglassGpu_ker.h/.cu`，仅移植已选CPU的matched-LS弹性HG。double历史/率按原生ID持久存储，GPU自身从当前double位置建立HG邻域，不使用校正后尚未刷新的主cell网格，也不每步整场下载到CPU计算。
- `JSphGpuSingle.h/.cpp`持有对象并接入四阶段：预测施力加Hn、预测位置更新后加半步Rn、校正施力加Hhalf、校正位置更新后计算端点率再加另半步。保留两次累加，不合并算术；HG加速度在最终AceMax和步长评估前完成。
- `VS/DualSPHysics5Re.vcxproj`及filters添加新编译单元；CPU配置排除GPU类和CUDA核。不更换构建系统，不改CPU HG公式。
- 沿用CPU的2D Wendland、Symplectic、X周期、固定原生弹性粒子、小转动及鲜启动限制。不支持塑性/软化、一般3D、大转动、运动体、shifting、流入流出或HG重启。`JSph.cpp`输入保护先保留，独立GPU夹具通过后才另行开放真实输入检查。
- CPU/GPU邻域累加顺序不同，不要求跨架构0 ULP。设备内部每对固定lo/hi方向、对端反号，避免用非确定double原子加法。与CPU一样按位验证端点状态才能复用率；变化就重算。内部缓存开关仅供夹具OFF/ON检查，不新增XML选项。

## 运行前验收约定

1. 真实CPU类、真实GPU类及独立无向pair公式互检；平移/相容仿射、交错速度恢复、周期接缝/负坐标、nx=2重复列、严格支持域及多block。
2. GPU缓存OFF/ON在同状态/阶段要求率、历史和实际加速度逐位相同；覆盖重排、周期副本、各输入位变化、signed zero、变化dt和移动端点。CPU/GPU率/历史容差预定为`1e-8*(1+max(abs(reference)))`，float加速度为`64*FLT_EPSILON*max(1,abs(reference))`；失败定位，不事后调门。
3. 沿用CPU的完整原生集合、有限值、弹性、LS秩/条件、阶段/dt、`dt<=0.2*tau`、累计spin<0.01和虚功`abs(power+2form)<=1e-9*(1+abs(power)+2form)`约束。统计和/平方和含义与CPU一致。
4. 独立算子通过后开放HG GPU XML，检查真实短跑和关闭路径相对G2精确回归，再接SPR/事件；后续5 Pa/0.005 mm、0.1 s后100 Pa原关卡及完整2Tv仍独立验证。

测试统一`support/hg_gpu_hourglass_*`，程序/中间物在`outputs/hg_gpu_hourglass_{Debug,Release}_r1`，构建/检查在`logs`；不覆盖G2/旧结果、不改正式XML/BAT、不提交Git。源码变更后CPU Debug已执行；GPU构建和夹具尚待完成。

## 夹具执行前的审查补充

- 独立只读审查核对了两端LS、统一原生ID方向、成对反号、独立端点网格、缓存、四阶段及边界索引，未发现阻断项；这不是执行验收。
- `maxactualnetforce`由最终float加速度相减后求和，不能当作内部double统计施加`1e-8`跨后端阈值。首次执行前即约定：逐粒子实际加速度仍按上文64 eps检查，该合力统计另行报告CPU/GPU值与差；GPU缓存开/关对该统计仍要求逐位相同。内部double历史、率、虚功与合力标准不变。
- 夹具含累计spin拒绝试验，并检查拒绝原因，避免把其他保护触发误认为小转动保护通过。独立CPU/GPU比较与同GPU缓存比较分开记录。
- 正常缓存步约7次168字节汇总D2H同步；没有全粒子下载，但小算例延迟不能从字节数推断，需后续实际计时。逐ID的`GetRate/GetHistory`只用于夹具，不进入生产主循环。
