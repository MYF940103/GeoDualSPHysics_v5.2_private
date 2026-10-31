# Cryer r2：Windows / NVIDIA 服务器运行

这是独立命名的已测基线发行入口，不覆盖旧输入、r1 ZIP或已有计算。
解压 `Cryer_release_r2_Windows_RTXA6000.zip` 到服务器本地磁盘后运行；不要在ZIP内执行。
目标为Windows x64、NVIDIA RTX A6000及兼容CUDA 11.7的驱动。不需要Python、CUDA Toolkit或Visual Studio。
包内附GenCase、已验证Cryer Release及其Chrono/OpenMP/微软运行库；Windows系统UCRT和NVIDIA驱动不随包分发。

## 运行顺序

先在解压目录执行启动检查：

```bat
xCaseCryerProblem_PR_release_r2_win64_GPU.bat --smoke --unattended
```

smoke仅到2^-13 s，128步、两帧；它不包含排水开启或峰值，也不会自动启动全程。
确认启动成功、`Run.out`显卡型号正确并保留回执后，再独立执行：

```bat
xCaseCryerProblem_PR_release_r2_win64_GPU.bat --unattended
```

双击同一BAT执行全程；不带`--unattended`时结束暂停。smoke和全程分别使用
`CaseCryerProblem_PR_release_r2_smoke_out`、`CaseCryerProblem_PR_release_r2_out`。
同名目录存在即拒绝运行，没有删除菜单、覆盖、自动续算或PART重启。中断后保留整个部分输出，另行检查。

每次启动前核对清单中全部payload SHA256；每阶段写输出目录内
`execution_receipt_r2.json`，记录实际程序/运行库/配置/启动脚本/清单字节、命令、时间和退出码、
生成XML及初始BI4、控制台日志，以及nvidia-smi所观察的GPU名称/UUID/驱动。
查询失败如实留错；可用GPU清单不等于求解器已选设备，最终以`Run.out`为准。
正常stderr不会被误当作原生程序非零退出。失败保留输出；不要将退出0等同物理验收。

## 配置、输出时间与精度范围

- 原FrDraw球体R=0.05 m、dp=0.0025 m、k=1e-5 m/s、ν=0.3、q=10 kPa；原始模式2围压。
- 应力和保存位置double；孔压、孔压率、密度仍float。G1、symC开启，阻尼0.00004；SPR、HG、shifting关闭。
- 固定dt=2^-20 s=0.95367431640625 μs，与已经返回并审查的服务器全程实际步长一致。
  旧r1包和隔离峰窗粗/半步是2^-21/2^-22；不能把它们当本r2全程的独立半步验证。
- ramp结束2^-8 s，闭合持载至tD=2^-7 s。保存态t=tD仍是开排水前；t>tD的真实FSType2/3表面施加p=0。
  理论时间τ=t−tD，不以ramp结束、第一排水帧或拟合峰时重新对齐。
- TimeMax=0.9187412261962890625 s，共963370步；排水后legacy Tv约1，不是2Tv。
- special两档输出保留：闭态每2^-13 s至tD；之后按tD锚定Δlegacy Tv=0.001。
  预计1065帧；后期名义Tv刻度向上取到固定步长格，分析使用实际原生时间，不硬套名义帧时。
- 历史A6000相同设置全程循环约10.7小时，只是规划参考，不是新机器/新运行速度保证。
  建议预留至少15 GB空间；不通过减输出频率假定求解循环同比加速。

该基线固定18材料点的孔压峰为12310.520779 Pa，对有限Kw、r/a=0.05参考12439.175960 Pa，
峰幅差−1.03427%、峰时差+3.97893%；末态中心17.64299 Pa、参考18.04766 Pa。
这是“峰幅约1%”的有界方案，不是严格低于1%、全场/全曲线1%、全程半步收敛或所有密度误差已修复。
Mandel增量误差、早中期局部应力/位移散布及密度—变形一致性问题仍记录保留；没有为了贴合曲线拟合时钟、半径或压力。

## 完成后回拷

BAT只生成初态和求解，不自动绘图、导出particles或安装分析环境。
请回拷**整个全程和smoke输出目录**、其中的执行回执/日志、全部`data`原生文件，
以及原ZIP和`support/cryer_server_manifest_r2.json`。本地随后核验原生终点/ID/排水/载荷/时钟，
再生成孔压/位移/应力对比图、匹配CSV和particles；不要只拷最后一帧或图片。

## 程序来源与许可

复用已经完成CPU/GPU OFF/ON实现桥接的Cryer GPU Release，SHA256为
`652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096`。
它不是本轮从当前最新源码重新编译的程序。新清单绑定旧Release构建、实现回归及六份精确源码归档；
打包时的Git节点仅是制作节点，不冒充编译节点或所有系统依赖的完整锁定。
之前返回的服务器结果没有实际执行EXE/DLL SHA回执，不能由本地包补认；r2执行回执记录这次真正执行的路径/字节与结果。

旧r1输入、ZIP、输出和哈希记录不改写。包根`LICENSE`来自仓库LGPL许可，保留原文；
Chrono许可见https://github.com/projectchrono/chrono/blob/main/LICENSE，微软运行库许可/下载见
https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist。
打包脚本仅在原工作仓库使用；服务器无需构建或重新打包。原始BI4/EXE/ZIP不等于已由Git备份上云。
