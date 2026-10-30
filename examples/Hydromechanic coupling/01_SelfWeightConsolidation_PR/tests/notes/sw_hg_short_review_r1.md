# 自重单底面：HG=.1 的 2 ms 短窗

## 范围与结论

三个 fresh 短窗完成并通过原实现/安全筛查，可以支持下一项有界 .3 s 诊断；不等于静力平衡、理论精度或正式固结验收。

唯一配置差为在保留的 SPR1/G1/ShepardOFF 输入上增加 SoilHourglassXi=.1。k=0、阻尼 .02、mDBC vel=0、NoPen 关闭、材料、粒距 .01、周期宽 .1、积分与黏性不变。没有修改 C++/CUDA、正式 XML/BAT、旧 helper、程序、默认值或 Cryer 服务器。

CPU8/GPU 粗步 dt=1 us、2000 步；GPU 独立半步 .5 us、4000 步。每组保存五个对齐实际时刻，TimeOut=.0004999，未插值或重写 metadata。三个作业按 CPU→GPU→半步逐一通过后才准入下一组，无 held jobs。

## 原门槛与独立审计

| 比较 | 五样本最大孔压 RMS 差 / Pa | 最大材料位移差 / mm |
| --- | ---: | ---: |
| 同步长 CPU/GPU | .007237464568 | 1.333129116e-8 |
| 独立 GPU 粗/半步 | .065673972998 | 1.080632787e-8 |

原 5 Pa/.005 mm 门槛不变。每组与其同后端、同 dt 的 HG0/SPR1/G1 控制组比较全部五个状态，初始 38 字段逐位相同；后续 HG 选项差异只描述，不应用半步门限。

全部 1040 ID/38 原生字段的有限性、正密度、零塑性、无排除、double 位置/应力、固定 p0、float32(p-p0)、几何、顶部十点排水、顺序 binary64 时钟及 signed dterror 通过。并未强制 rho=2100；本短窗实际仍为 2100。

独立只读审计复读 15 个新状态和 15 个保留控制状态，1500 行剖面、25 对比较及 HG CSV 均重算一致；621 个去重文件共 215821646 B 的 SHA/大小全部匹配。三个退出码均为 0，无自有残留进程。

## HG 实际运行记录

| 计数/量 | CPU 粗步 | GPU 粗步 | GPU 半步 |
| --- | ---: | ---: | ---: |
| forcecalls = ratecalls | 4000 | 4000 | 8000 |
| predictorupdates = correctorupdates | 2000 | 2000 | 4000 |
| ratecalculations | 2001 | 2001 | 4001 |
| endpoint rate reuses | 1999 | 1999 | 3999 |
| max(dt/tau) | .000796116 | .000796116 | .000398058 |
| 累积 spin bound / rad | 2.6345e-10 | 4.5922e-10 | 4.14825e-10 |

阶段计数满足每 N 步 force/rate=2N、两类 update 各 N，计算次数加复用数等于 2N。没有把复用数硬设为 N-1；本次恰好是该值。原 dt/tau<=.2、spin<.01 和源码内有限性、LS、虚功等检查保持不变。

理想 history 力的净和最大约 1.59e-15（GPU 粗组），但转换并加到 float Ace 后的实际净增量最大约 8.21e-6，CPU 约 2.00e-5。两者均原样记录，不把浮点加法净和称为精确零，也没有新造力学验收门槛。

## 短窗效应及耗时

GPU 粗组在 2 ms，HG0→HG.1：底层沉降 .000579238→.000541466 mm，近底第二层上移 -.000263581→-.000219268 mm，顶层沉降 .010273651→.010249671 mm，R990 RMS .0201432→.0196971 Pa。变化尚小，不能由这段启动瞬态宣称交错已消除。

Simulation Runtime 分别为 CPU8 5.990548 s、GPU 粗步 8.219831 s、GPU 半步 28.698874 s。不是隔离后端基准，半步耗时也不能直接外推为严格 2 倍。下一项采用单个 GPU .3 s，是为使用已完成的同 GPU HG0 控制，避免同时改变后端或额外补算 CPU 控制；不是宣称 GPU 更快。

## 来源与交付限制

本轮使用同一冻结程序作数值选项诊断。六个当前 HG 源码 SHA 已绑定，既有 Lian 构建记录保存的六项 SHA 及归档 GPU header 与当前一致；e28650c3→f9cb4349 的六个 Git 路径无提交变更，当前工作树也未修改。原 CPU/GPU build 日志确实列出 HG 编译且程序哈希对应。

然而，这两份旧 build 清单未在编译当时逐项捕获完整六个 HG 源码；新输入如实保留 exact_HG_source_at_build_time_proven=false，不用当前 SHA 伪造历史归档。因此本阶段不是新的 HG 源码实现或正式发布验收。若后续选中 HG 作交付方案，须补齐冻结源码构建及开关原生回归。

HG 和 SPR 都仍禁止 PartBegin；HG history/rate/cache 不能用现有 PART 精确恢复。本轮不绕过入口，不把短窗支持推广为塑性、大转动、任意重启或正式长程能力。

证据位于 logs/sw_hg_short_r1.check.json、三份 receipt/completion、configs 的 XML/BAT，以及 figures 的 frames/history/profiles/pairs/differences/hg CSV。原始 BI4、程序本地保留；Git 仅备份配置、脚本、记录和分析数据，不等于原始数据云备份。下一步仅准入 fresh GPU .3 s，并单独复核全层沉降、交错、孔压和末窗响应。
