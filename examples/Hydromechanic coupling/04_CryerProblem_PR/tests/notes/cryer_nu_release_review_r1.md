# Cryer nu=.10/.20/.45：独立正式输入与Windows服务器包

日期：2026-11-01。新增三组，不覆盖nu=.30 r2或任何已有输出。
本轮没有额外数值修正，因此不要求重跑已返回的nu=.30数据；
若以后有新的有效修正，全部四组必须新建版本重新准备和验证。

## 文件与运行

包为根目录 `Cryer_release_nu010_020_045_r1_Windows_RTXA6000.zip`，
SHA256为 `d5ef9a6c309c622104e32716d5ac92743ce43958743230e6fa553418eb5ab319`。
19个ZIP条目逐个核SHA；18项payload加一份manifest。
其中9个程序/运行库沿用已验证Cryer程序，不是从当前HEAD重新编译；
EXE SHA为 `652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096`。
编译来源、六源码归档范围及旧服务器实际EXE身份缺口不作追认。

根目录新增三个`CaseCryerProblem_PR_release_nu{010,020,045}_r1_Def.xml`
和对应`x..._win64_GPU.bat`；共用support下launcher、README、manifest和原已核运行库。
各BAT双击运行自身全程；`--smoke --unattended`只检查128步，两者使用不同输出目录，
不覆盖、不删除、不PART续算，也不自动从smoke衔接full。服务器不需要Python/VS/CUDA Toolkit。
须解压后运行，并在目标A6000上先确认自己的smoke和Run.out设备信息。

| nu | ΔlegacyTv=.001对应秒 | TimeMax/s（包含tD） | 步数 |
| --- | ---: | ---: | ---: |
| .10 | .001199 | 1.20681285858154296875 | 1265435 |
| .20 | .001103625 | 1.11143779754638671875 | 1165427 |
| .45 | .00032328409090909091 | .331096649169921875 | 347180 |

共同dt=2^-20 s、ramp=2^-8 s、tD=2^-7 s、闭态保存间隔2^-13 s；
各组期望1065帧、终点legacy Tv≈1，而非2。只改变PRvs和相应TimeMax/TimeOut及排水后timeout；
E、Kw/n、k、几何、G1/symC和其他开关不变。每组K/G/H、声速和有限Kw参考均不同，
尤其nu=.45闭态p目标应为Bq≈9900.99Pa，不能照搬10000Pa或nu=.30参考。

## 实际便携检查

新目录 `tests/outputs/cryer_nu_portable_r1` 从实际ZIP解压，未借仓库外相对路径。
三个真实GenCase和GPU程序均正常退出，实际设备均为本机RTX3050，不冒称A6000实测。
每组128步、终点2^-13 s、两帧；6帧原始安全检查通过，37173土粒子IDs保持。
三个初态与保留nu=.30初态的全部35字段逐位相同；其他nu的末帧没有被要求等于nu=.30，
也没有Debug/Release、跨nu或smoke/full等价的泛化。

实际Cs为31.20938885、32.53000263、60.10389814m/s；
候选dt均低于孔压budget≈2.97877μs，保存dterror分别约
-2.78837e-5、-2.67130e-5、-1.40204e-5 s，原有signed guard通过。
这些是启动两帧的观察，不能证明整个时间段的自然步长限制或独立半步收敛。

原生检查见 `../logs/cryer_nu_portable_r1.check.json`，六帧数据在匹配summary.csv。
三个实际执行回执逐字节复制到logs的`cryer_nu_portable_r1_{010,020,045}.execution.json`；
原执行回执的native_completion_verified=false保留不变，独立review另记已核smoke。
每次新服务器执行会记录实际EXE、运行库、配置、清单、命令、生成XML/BI4、时间和退出码。
nvidia-smi库存不是实际选卡证明，实际设备须以Run.out核实。

已有输出、未知参数和被破坏payload三种负向启动均exit1、未启动新求解器；
便携目录82个文件的前后SHA保持一致，坏配置仅存在独立negative测试目录。
见 `../logs/cryer_nu_negative_r1.check.json`。

## 准备完成不等于物理通过

没有启动三组本机全程，也没有闭窗平衡、Mandel峰、全程半步或新材料物理验收。
包是可执行的正式输入/程序交付，其数值精度仍等待服务器完整数据审阅；
nu=.30峰幅约1%的结论不能推广到另外三组。
回拷整个smoke和full目录（含全部data、回执、Run.out/Run.csv/控制台日志）及原manifest/ZIP，
再按各nu有限Kw和实际保存时刻分析。不要只回拷图片或末态。

本轮新增/改变仅为正式输入、BAT/PS启动、发包与离线审计支持文件、README、字节属性和证据。
生产C++/CUDA没有改变，不发生新生产构建；旧EXE通过实际启动复用而非宣称新编译。
原始BI4/EXE/ZIP仅本地保留，不算Git云端备份；配置、脚本、图/CSV、清单和摘要收据选择性备份。
