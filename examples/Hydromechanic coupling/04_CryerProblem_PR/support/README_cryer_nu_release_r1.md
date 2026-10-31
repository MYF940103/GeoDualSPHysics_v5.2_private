# Cryer 三组Poisson比：Windows / NVIDIA 独立候选入口

新增nu=0.10、0.20、0.45三组，不覆盖保留的nu=0.30 release_r2、旧输入或任何输出。
这三组仅沿用已验证程序及基线开关；目前没有它们的完整、峰值、半步或A6000实机物理验收。
本机便携启动检查不能代替目标服务器检查或完整结果审阅，不把文件准备完成写成数值通过。

## 环境和运行顺序

目标为Windows x64、NVIDIA RTX A6000及兼容CUDA 11.7的驱动。
包内沿用GenCase、Cryer GPU Release及Chrono/OpenMP/微软运行库；Windows系统UCRT和NVIDIA驱动不随包分发。
服务器不需要Python、CUDA Toolkit或Visual Studio。先将完整发行ZIP解压到本地磁盘，不在ZIP内运行。

各BAT只运行自己的Poisson比。例如nu=0.10先独立启动检查：

```bat
xCaseCryerProblem_PR_release_nu010_r1_win64_GPU.bat --smoke --unattended
```

确认该组Run.out实际显卡、128步/两帧和执行回执，再另行手动运行该组全程：

```bat
xCaseCryerProblem_PR_release_nu010_r1_win64_GPU.bat --unattended
```

nu=0.20、0.45分别使用同名的nu020、nu045 BAT，均须独立smoke后再决定是否启动full。
smoke终点仅2^-13 s，不包含排水开启或峰值，不自动接着运行full或另一组。
不带--unattended时结束暂停。全程/短检查分别输出到各自stem加`_out`/`_smoke_out`；
同名目录存在即拒绝，没有删除菜单、覆盖、PART重启、自动批跑或自动后处理。

## 参数和实际时间

除PRvs及其legacy Tv=1所需TimeMax/TimeOut、tD后special timeout外，其余数值设置与nu=0.30 release_r2相同。
保留FrDraw球体R=.05 m、dp=.0025 m、k=1e-5 m/s、围压q=10 kPa、G1和Darcy symC开启、
SPR/HG/shifting关闭、阻尼.00004；应力和保存位置double，孔压/孔压率/密度仍float。
ramp结束2^-8 s，排水在tD=2^-7 s后开启；t=tD保存态仍是开排水前。
所有组固定dt=2^-20 s=.95367431640625微秒；这只是沿用基线的候选步长，尚待各组startup和自然/孔隙步长审阅，
不把nu=.30的通过状态推广成三组都已通过。

| nu_tag | PRvs | tD后输出间隔/s | TimeMax/s | 全程步数 |
| --- | ---: | ---: | ---: | ---: |
| 010 | .10 | .001199 | 1.20681285858154296875 | 1265435 |
| 020 | .20 | .001103625 | 1.11143779754638671875 | 1165427 |
| 045 | .45 | .00032328409090909091 | .331096649169921875 | 347180 |

闭态每2^-13 s保存至tD，随后以tD锚定Delta legacy Tv=.001；预计各全程1065帧。
实际保存时间由固定步长格和最终上限决定，分析必须读取原生时间/步数，不硬套名义帧时或插值制造相同状态。
理论时间tau=t-tD。有限Kw参考按各nu单独计算，尤其nu=.45不能直接套论文不可压水参考；
legacy Tv刻度也不等于有限存储的衰减时钟。没有拟合半径、时钟或压力。
建议每组至少预留15 GB空间。nu=.30的旧耗时/峰幅约1%不能作为这三组的速度或精度保证。

## 清单、回执及回拷

共用`support/run_cryer_nu_release_r1.ps1`从`support/cryer_nu_server_manifest_r1.json`选择variant。
manifest的files恰为18项：9个程序/运行库、3 XML、3 BAT、launcher、本文和LICENSE；
manifest自身不作自引用SHA。每次启动核全payload，已有输出即拒绝。
每阶段写输出根`execution_receipt_nu_r1.json`及.previous，记录选定variant、实际程序/运行库/输入/清单字节、
命令、UTC时间、退出码、生成XML/初始BI4及控制台日志。
生成XML的PRvs/DtFixed/TimeMax/TimeOut与variant核对；smoke有效终点另由已记录的-tmax CLI覆盖。
nvidia-smi记录可用GPU/UUID/驱动，不冒充solver实际选卡证明；以Run.out核实际设备。
正常stderr不等于非零exit；exit0也不等于原生终点、峰值或物理准入，native_completion_verified保持false待独立审阅。

BAT只做GenCase和solver，不自动绘图、导出particles或安装分析环境。
请回拷每组整个smoke/full输出目录、全部data/原生文件、执行回执和日志，以及原ZIP和清单；
不要只拷末帧或图片。每组服务器结果均为pending review，未自动准入新的全程/峰窗/半步或重启能力。

## 程序来源和许可

复用既有Cryer GPU Release，SHA256：
`652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096`。
不是本轮从当前HEAD新编译；旧构建、原生桥接和六源码字节归档的证据范围不升级成全依赖锁定。
旧服务器缺实际EXE/DLL SHA回执的事实不改变，新执行回执只记录此次实际字节，不补认过去。
nu=.30 release_r2和历史结果原位保留；三组未做密度修复或新方程。
保留包根LICENSE及第三方许可：Chrono https://github.com/projectchrono/chrono/blob/main/LICENSE；
微软运行库 https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist。
原生BI4、EXE和ZIP不等于已通过Git备份上云。
