# NoPen正式源码同步及准入结果

用户要求在有效短窗基础上继续源码同步和正式计算。本轮将既有NoPen分步法向速度/位移投影作为受限u-pl选项接入，未另造反力/压力迭代；默认NoPen=0、其他u-pw/u-pl算子和NoPen公式保持。此前审计的同阶段反力限制是该分裂算法的已知范围，不作为无限阻止用户选择该方案开展完整验证的前置条件。

生产改动：`src/source/JSph.cpp`保存正式NoPen policy/active/ReactionClosed元数据，接收源合同中仅将NoPen两个字段映射到原弹性PRE的Std/false，并只对已认证PRE接收的固定轴向重力容器、AS0组合放行；`JSphCpu.cpp`、`JSphGpu.cpp`同步该受限准入。其他组合的门不变，不支持因此开启任意墙/运动/通用PART重启。`doc/xml_format/_FmtXML_ElastoplasticSoil.xml`同步默认值及边界范围。没有修改邻居核、返回算法、J/孔压积分、Darcy或原NoPen投影表达式。

CPU Debug、CPU Release、GPU Release均由原权威VS2022 solution实际MSBuild退出0完成（CPU各87、GPU113对象），源快照与构建收据为 `upl_c08_nopen_public_*_r1`。旧canonical及runtime_r3不覆盖，新正式程序和独立C08Native/PartVTK/运行库安装到 `support/runtime_r4`。

一次新GPU0.15秒回归 `upl_c08_nopen_public_reg_r1` 使用根ψ0 r4配置、原r2 PRE、真实runtime_r4程序、AS0/NoPen1、dt2.5us/输出.01。正常完成global4060000，随后实际调用r4后处理：新C08Native对15帧/6800IDs/22数组、P0/κ/FS/J-ledger/时钟/dterror及新policy全门通过；逐帧全部time+22数组的完整导出文件、布局文件及完整signed-clock CSV与保留隔离NoPen结果逐字节相同。旧BI4元数据不修改，新policy不是用旧字符串伪装。Fluid5000、Bound1800各15帧分别导出，PNG/CSV流程成功。唯一准入收据 `logs/upl_c08_nopen_public_review_r1.check.json`。

根目录新增三组r4 XML、六个CPU/GPU BAT、r4共用启动器/后处理和README。GPU明确复用原r2_GPU Part1000；CPU保持自有认证CPU PRE要求（本机未计算该源）。三组NoPen1/AS0，其他材料、dp、Ck2和边界滑移分组不变。完整GPU入口从真实10秒源继续到TimeMax13，不占用或覆盖r3失败out。自动后处理保留原生数据，分别导出全部Fluid/Bound，再写各组r4图及匹配CSV；三个完成后形成三组共同对比。

正式ψ0将由新单次owner调用实际根BAT，终态自动同根线程汇报，并据实际完整结果推进其他ψ组。0.15秒回归是实现等价准入，不是完整3秒或论文精度验收。NoPen输出 `LegacyOperatorSplitReleaseOnly`、Active=true、ReactionClosed=false，明确本步投影反力未显式回馈同阶段Darcy/J；不将其说成严格闭合接触。
