# H1.8 共用离线比较与绘图（作者稿，未执行）

只新增 `support/c08_h18_compare_r1.py` 与本说明。脚本/AST已准备，未导入或执行分析，不改active源、中央profiles、原生reader或已有结果。入口：从C08根目录运行 `D:/anaconda3/python.exe -B tests/support/c08_h18_compare_r1.py --manifest MANIFEST.json --execution-authorized`，须Root全文审后独立准入。

可import的轻量接口：`load_bundle(spec, consumed)`读取现有completion/typed-call/实际XML/22-layout并memmap；`read22(bundle, part)`读取一条原记录、核全22有限值/原ID/实际clock；`reference_from(source_bundle)`仅取已认证full源native的真实首/末两条；`analyze_case(bundle, reference=None, snapshots_tau_s=None)`不写文件，返回history/extrema/layers/tracks/选中raw字段及summary；`plot_results(results, prefix)`只写新PNG。正式post可复用函数，由调用者处理solver/owner/PartVTK和后续物理决定。

manifest最小结构如下（路径可为绝对路径或相对C08根目录；示例路径须替换为真实已封口产物，不能预填passed）：

```json
{
  "schema": 1,
  "tag": "c08_h18_source63_review_r1",
  "mode": "source",
  "cases": [{
    "tag": "H18source",
    "native_dir": "tests/outputs/ACTUAL_NATIVE_DIR",
    "source": "c08_h18_pre_r2",
    "group": "psi0",
    "actualAS": null,
    "H": 0.072,
    "input_xml": "tests/outputs/ACTUAL_JOB/ACTUAL_JOB.xml",
    "native_call": "tests/logs/ACTUAL_READER.call.json",
    "run": "tests/logs/ACTUAL_JOB.run.json"
  }]
}
```

receiver模式每case的actualAS为 `{"coefficient":0.3,"exponent":3.825}`（按实际值），group为psi0/psi2p5/psim5；另需 `source_reference` 对象，格式同source case、指向已通过full源native、实际generated XML和typed reader-call，source标签须与receiver case一致。源double PRE位置与固定P0由该已解码native的末条获取，不读BI4。可选 `reference_tag` 仅指定同实际step/time对照；未共同保存的状态不插值、不补行。可选 `snapshots_tau_s` 指定绘图名义时刻，选择最近的真实保存条并标实际part/time/τ；无精确时刻插值，默认仅最后保存态。case可附 `evidence` 文件路径或stat Entry绑定；runtime `run` 可选，正常receiver/full源若给run则要求真实0且passed，partial源允许真实失败1。source标签是显式出处标签，不替代程序/输入所有权证明；本工具不颁发runtime或物理准入。

支持shared native真实source partial（1至1001实际帧）/full、receiver91/301头，不改header。所有样本逐次处理5000固定材料ID、22有限值、P0 bit和native float(p−P0)定义；消费原completion的ledger≤5e−13和signed≤1e−14，**signed不取abs，也不提高为精确0门**。source63失败仅分析已保存0→约.620005，末1s窗口截到实际首条；不硬要求10s、不以κ0或证书代替平衡，也不推断未保存trial的ID/time。

逐保存态CSV包含绝对p、原生float(p−固定初始P0)、有效/总应力、速度、当前混合物KE与压力storage二次量、κ/J/n/ρ/k、中心粒子front/runout/height、固定材料位移沉降、saved FS符号和x/z几何gap。p−P0的固定参考不等于已证实的论文“excessive pressure”定义，两者不得混名。KE与pressure quadratic按V为2D单位厚度面积标J/m，不称完整u-pl能量或守恒。receiver逐全部保存态计算NN分位及严格r<.7dp近对；rNN/sqrtJ仅描述性压缩参考，非各向异性F校正或张拉根因证明。source不重复做全程NN。

材料reference：source以实际part0初始double坐标；receiver以同H认证PRE末条double坐标，top/bottom各100ID及50个材料层按源part0的初始z固定，绝不按变形后位置重选。保留7010/7011/7012/6230/6231固定材料轨迹。source复用native summary的真实生产DP f观察，不当历史trial重构。summary对source末1s、receiver末.3s（window）或1s（formal）给实际窗口、全范围、端点差与secant、不做拟合或新增停滞/平衡门。

新浅层前缀由manifest.tag决定：history/extrema/layers/tracks CSV、可选exact-clock matched CSV，history/tail PNG；source另layers PNG，receiver另选中时刻raw5000散点PNG。压力/应力曲线单位与负压symlog仅为显示；NN与近对计数分面，色按case、线型按panel标题顺序。scatter全部选中状态共用完整min/max及显式范围内ticks，保留负压、固定边界灰点和等比全域坐标，无quantile clip、平滑、过滤或自动winner。TwoSlopeNorm正负色带半条尺度不同，图注明示。

成功/失败均仅新 `logs/<tag>.check.json`；拒已有完整或partial同tag结果，失败保留部分产物。统计passed只说明本次离线处理/绑定，不证明平衡、论文精度、接触反力/J/Darcy闭合或修复早停。没有SHA、额外PRE/BI4解码、native/solver/build/VTK/queue和自动下一任务；PNG仍需Root视觉审查。
