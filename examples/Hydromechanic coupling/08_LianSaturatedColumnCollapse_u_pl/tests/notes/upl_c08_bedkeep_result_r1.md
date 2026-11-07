# 保留底面重叠粒子：短窗结论与后续范围

本轮修正的是撤墙后的实际底面几何。原右墙MK中含5个z=−dp/2的浅床点，整体退休260点后，浅床x中心从3.98跳到4.22 m。新增`gravitypreload keep_bed_overlap`默认false；仅在原认证PRE接收且启用固定平面NoPen时，可在唯一撤墙事件保留原ID 1800、1852、1904、1956、2008及坐标/固定Code，改为上向raw normal=(0,0,float(dp))和逐粒子NoSlip，实际退休其余255点。活动集合明确为6805=1805固定+5000土粒，未重新编号；原PRE的7060/2060注册、260点来源资格及合同不变。

源码只涉及`JSph.h`、`JSph.cpp`、`JSphCpuSingle.cpp`、`JSphGpuSingle.cpp`；参数文档同步在`doc/xml_format/_FmtXML_ElastoplasticSoil.xml`。没有改Darcy/材料/AS/积分公式、MLS阈值或邻域半径。复用原r2 GPU Part1000，未重算10 s。根目录runtime_r4及正式XML/BAT保持原样。

CPU Debug、GPU Debug和GPU Release已分别构建通过，程序/源码快照保存在`tests/outputs/upl_c08_bedkeep_*_r1`。CPU/GPU Debug各40更新、1个真实post帧，原22数组/6805 ID/ledger/P0/FS/时钟/signed/平面门通过，GPU memcheck 0错误和0泄漏。跨后端土粒孔压RMS差0.00172332919435464 Pa、各材料XYZ最大差1.252067893808828e−9 mm，符合既有5 Pa/.005 mm实现预算。这不是Release精度或物理验收。

新选项关闭、AS仍开启的GPU Release 0.03 s/3帧，与保留`upl_c08_asplane_short_GPU_r1`逐文件比较：`typed22.bin`、layout、clocks全部原始byte相同，包含全部22数组/time/signed诊断，无字段排除。该默认关闭回归不比较原BI4文件本身。

开启后的GPU Release 0.03 s/3帧，全部原生门通过。实际相同step/time与旧短窗的末帧描述性对比如下：

|末帧τ≈.03 s|旧keep=false|新keep=true|
|---|---:|---:|
|孔压RMS (Pa)|11247.668565|11269.515390|
|最小孔压 (Pa)|−4841.841309|−4169.466309|
|总应力Frobenius RMS (Pa)|34075.618115|34154.967000|
|全土材料平均沉降 (mm，原double PRE)|.4537362864|.4391643637|
|最大速度 (m/s)|.1911517780|.1365647906|
|最小土粒z (m)|.01740428366|.01998335734|
|最大塑性历史κ|.04105855897|.02253262326|

同末帧土粒孔压RMS差242.2893301 Pa、XYZ最大差2.645281148 mm。它们是不同边界算子的变化，不套用CPU/GPU或half误差门，也不能据此宣称论文更准确。未新增half链。

三阶段收据、CSV和PNG：`tests/figures/upl_c08_bedkeep_short_review_r1_{smoke,off,short}*`。另存的`upl_c08_bedkeep_short_display_r1*`仅改善单点数值显示及横坐标刻度，不改旧数据/图或重复native分析。

已据明确几何缺口与短窗结果准入一个新0.6 s窗口`upl_c08_bedkeep_window_GPU_r1`，dt仍2.5 us，AS ε=.2/exp2.55，NoPen=`FixedPlaneStageProjectionReleaseOnly`、ReactionClosed=false；根准入、原始start和owner_admission在logs。目标是检验能否越过旧约.53 s失败段，最多60帧；当前只处于运行中，不是3 s塌陷或三组正式验收。仅有该direct owner一次终态通知，旧worker均不重启。

上一AS组合的53帧失败数据已经一次partial解码，图CSV见`upl_c08_asplane_partial_review_r1*`。τ=.49负压极值从AS0−973054.5改善为AS1−50429.8 Pa，但AS1在τ=.53仍有ID7014负压−168014.3 Pa/速度5.915 m/s，并在之后未保存力阶段报wall828拟合错误。局部已保存态的现有nearest重试det=.27498，不能将其视作重放失败阶段或盲加重试。保留底面缺口的修正有独立几何依据，但尚未证实它是所有后期问题的唯一原因。

原始BI4/NBI4、PRE、程序及源码归档原位保留；Git保存代码、配置、脚本和必要审查图CSV，不把原始数据/可执行程序当作已经云备份。无塑性任意PART重启、反力同阶段Darcy闭合、完整3 s或论文精度结论。
