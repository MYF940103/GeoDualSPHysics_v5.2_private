# 二维发行程序接轨回归

2026-10-25，基线d428380。三维棱边／墙角短窗与资源退出修复已备份；本轮不改生产代码和正式根输入。下一步先验证实际GPU发行程序而非伴随，避免把已有伴随10 s数据直接改名当作发行程序新结果。

新增scripts/spr_yao_release_smoke.py；configs中三对同标签XML/GPU BAT，保持已有格式，拒绝覆盖。XML逐字复用已保留spr_yao_gpu_load_raw02_r2的发行程序0.02 s配置；SPR关、开及半步，每组在执行下一组前必须通过21个保存帧对同dt旧发行程序的全原生字段0 ULP，以及原生ID、几何、载荷、排水、弹性和自然步长检查。任何失败保留输出并停止，不放宽原门限，不重跑旧worker。

当前真实GEO程序只比已验证生产候选多GaugeSystem析构顺序修复；物理不改。原普通输出／停止可能晚一个dt，逐帧比较实际时刻，不移帧、不插值，不把21个错开时刻粗／半步冒称全窗独立时间收敛。旧整数保存0.1/1/10 s证据另保留。本轮只是发行程序回归，不是完整二维理论验收或新10 s计算。

正式根配置目前缺分mk平面法向、SoilStressRateGradCorr=1、PoreCompressionGradCorr=1及显式SPR开关；SavePosDouble=0，输出.05 s，与验证用双精度位置/.01 s不同。数值等价的dt和TimeMax字符串差异不当物理差异。只打开SPR不足以成为正式多平面输入。回归通过后可准备独立命名的发行输入，不覆盖原默认版本；新输入和已完成10 s图/CSV必须明确区别。

结果入口：logs/spr_yao_release_smoke_r1.status.json及figures/spr_yao_release_smoke_r1_native.csv。如全0 ULP，无需新画重合曲线来冒充物理改善，沿用已审阅Yao10 s PNG/CSV，保留本轮逐帧回归表。原正式三组一维、Yao10 s、旧三维数据均不动。

## 完成与新发行入口

三条实际GEO Release程序均正常退出：SPR关／开末时0.02001999999999952 s，半步0.020009999999999355 s；各21帧、共63帧对旧发行程序的同dt实际轨迹全原生字段0 ULP。逐组安全门通过后才运行下一组，无活跃遗留进程。没有用错时刻帧计算新的半步指标，原整数保存的半步证据照旧。源码／方程未改变。

新增根目录`CaseYao2DConsolidation_PR_SPR_Def.xml`和`xCaseYao2DConsolidation_PR_SPR_win64_GPU.bat`。XML以已审阅10 s开启配置为准，仅改说明文字：底／左／右墙分mk并给完整法向，显式SoilStressRateGradCorr=1、PoreCompressionGradCorr=1、PairDivergence、SPR=1，双精度位置输出，HG/NoPen=0；dt20 µs、TimeMax=10 s、TimeOut=.01 s。E、nu、k、n、Kw、节点荷载、阻尼、排水与已验配置相同。普通发行程序保存／末时仍可能晚一个dt，不用新的epsilon或重复timeout掩盖这一事实。

BAT沿用原case变量、程序路径、GenCase／求解／PartVTK字段格式，补从自身目录定位及非零退出；不删除已有输出、不回退Debug。新输出应为根`CaseYao2DConsolidation_PR_SPR_out`；目前未启动该10 s入口，不因名字变“正式”而重复已有计算。新入口不自动绘制理论图，也不把伴随10 s目录迁来冒充新输出。原默认XML/BAT和根结果不改。

二维当前达到的是固定平面弹性数值接轨及已保留10 s有界比较；缺独立二维理论沉降真值，不声称完整理论验收。三维下一物理回归可选SPR关闭的Cryer球体，但应先核查现有理论后处理参数和成本；Selborne缺多材料／局部压力边界，不启用其禁用BAT。没有重开KEEP/u-pl/TPI或扩大三维HG支持。

新增发行XML去除纯说明属性后，全部可执行节点／属性／文本与已验证10 s XML完全相同；GenCase在tests/outputs/spr_yao_release_formal_input_r1检查正常退出，全部21945点、20301土点、1644墙点的有序VTK坐标及文件SHA与已有10 s初始化相同。零重力导致自动水深和B为零的原有警告保留。PartVTK已用本轮开启组首／末原生帧检查流体和边界，正式BAT所列变量可正常导出。没有改输出调度，也未把GenCase通过当作完整物理验收。

本轮逐文件修改：上述一个新scripts脚本；configs中三个XML和三个同名GPU BAT；logs中的三组运行日志、status、GenCase／PartVTK／准备与备份记录；figures中63行原生回归CSV；本说明和spr_delivery_index_r1.md；根新SPR XML/BAT及README。没有新增C++/CUDA修改。默认CPU Debug再构建通过，备份节点／白名单在logs/spr_yao_release_backup_r1.complete.json。删除／移动0；原生数据／程序留在本地，不声称云备份。
