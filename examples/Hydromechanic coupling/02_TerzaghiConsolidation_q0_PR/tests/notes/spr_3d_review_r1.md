# 三维固定棱边／墙角 SPR 核验与交付

2026-10-25。接续已接受的case02三组一维结果和Yao二维10 s，不重跑、不覆盖它们。本次完成的是静止凸平面、弹性、短时三维数值一致性检查，不是完整三维固结理论验收。

## 结果

共四种组合：x/z双墙棱边edge3、x/y/z三墙角corner3，各含NoSlip（2）和FreeSlip（3）；每种CPU/GPU各粗、半步，共16次全新实际生产步运行。首组edge3 FreeSlip原位沿用，后续序列仅补其余三组。后续序列在日本时间2026-10-25 12:07完成，无存活求解器、监视器，不重启一次性通知。

dt=1/0.5 µs，结束2 ms，10 µs保存，共201个实际匹配时刻。实际末时粗步0.001999999999999941 s、半步0.0020000000000001033 s。edge3有1600个土粒子，corner3有1000个；全过程按原生ID对应，不做时间／空间插值。dp=.01 m、k=1e-4 m/s，初速度三分量(-.001x,-.0007y,-.0013z) m/s均非零。HG、NoPen、阻尼、排水、外载关闭，原float孔压u-pw/Darcy和double应力不改。

| 组合 | CPU半步最大孔压RMS差 Pa | GPU半步最大孔压RMS差 Pa | 同dt CPU/GPU最大孔压RMS差 Pa | 半步最大三维材料位移差 mm |
| --- | ---: | ---: | ---: | ---: |
| edge3 NoSlip | .01447657 | .01447607 | .00004324 | 8.527e-10 |
| edge3 FreeSlip | .01485933 | .01485952 | .00004497 | 8.710e-10 |
| corner3 NoSlip | .01346559 | .01346536 | .00005722 | 1.130e-9 |
| corner3 FreeSlip | .01387537 | .01387412 | .00006490 | 1.170e-9 |

全部8个独立半步对比、8个同dt跨后端对比满足原0.5 Pa／1e-5 mm界限；跨后端最大三维位移差8.837e-10 mm。半步竖向总应力RMS最大差.0148963 Pa。近似动能+弹性应变能+孔压储能最大为初值1.020237倍，低于既定1.1门限；这不是离散能量守恒证明。有限字段、正密度、原生ID、弹性、未越固定面及自然机械／孔压时间步检查均通过。

离线[spr_3d_audit_r1.check.json](../logs/spr_3d_audit_r1.check.json)重新核验866个唯一文件哈希及完整原生样本，独立复算上述量；不是只读“passed”字段。旧CPU运行绑定的旧runner仅通过明确归档SHA解析，未改写历史清单。全部16次运行正常退出与短时门通过，不替代理论／长期物理验收。

压力峰值约171.35–196.23 Pa，反弹阶段最小表压约-133.81 Pa，末态平均表压约1.42–1.59 Pa；最大材料运动约.00035163 mm。六分量有效应力绝对值最大约9.606 Pa。没有外载和排水，不能把这些孔压波动叫作固结耗散理论误差。NoSlip初始切向速度不相容，会有启动瞬变，不能把初始仿射场当作其精确解；也没有通过增加阻尼隐藏瞬变。

## 图及对应表格

每组四张图均有同标签CSV：CPU半步、GPU半步、全程历史、y0=.005 m原生切片。切片每组100个原生点，无插值；CPU/GPU绝对场共享色阶，差图独立色阶。三组新图12张本轮逐张查看；首组4张沿用已看图的admission收据并重新核验哈希。标注、单位、实际时刻、原生点及曲线量级一致，见新visual收据，不回改旧review的visual标志。

- [edge3 FreeSlip历史](../figures/spr_3d_r1_edge3_s3_history.png) / [CSV](../figures/spr_3d_r1_edge3_s3_history.csv)
- [edge3 NoSlip历史](../figures/spr_3d_r1_edge3_s2_history.png) / [CSV](../figures/spr_3d_r1_edge3_s2_history.csv)
- [corner3 FreeSlip历史](../figures/spr_3d_r1_corner3_s3_history.png) / [CSV](../figures/spr_3d_r1_corner3_s3_history.csv)
- [corner3 NoSlip历史](../figures/spr_3d_r1_corner3_s2_history.png) / [CSV](../figures/spr_3d_r1_corner3_s2_history.csv)
- [汇总表](../figures/spr_3d_audit_r1_summary.csv)、[各原生运行量](../figures/spr_3d_audit_r1_native_summary.csv)、[半步](../figures/spr_3d_audit_r1_half_summary.csv)、[跨后端](../figures/spr_3d_audit_r1_cross_summary.csv)。完整图片/CSV白名单及SHA见visual和backup清单。

## 源码修改及原因

相对本轮基线7b3e4a5，唯一生产源码改动是src/source/JSphGpu.cpp中JSphGpu::~JSphGpu()：在cudaDeviceReset之前增加说明和`delete GaugeSystem; GaugeSystem=NULL;`两行。原代码初始CalculeGpu即可分配测量辅助GPU缓冲，先重置CUDA、后由基类析构GaugeSystem会触发cudaFree错误。现在提前释放，NULL使基类再次delete安全；无方程、核函数、边界映射、积分或参数改变。

[spr_3d_cleanup_r1.check.json](../logs/spr_3d_cleanup_r1.check.json)保留原失败证据：非零三维伴随和真实生产Debug程序原各1个memcheck错误，修复后各0个。修复前后伴随3帧18原生字段、真实程序3帧24字段全部0 ULP。原源文件／runner／程序保存在outputs/spr_3d_precleanup_r1，不改旧哈希。CPU Debug/Release与GPU Debug/Release均已构建；原D9035、LNK4099/LNK4098警告保留，不声称已修复。

## 所有新增／修改位置

1. src/source/JSphGpu.cpp，析构函数上述两行：修复CUDA退出时资源释放顺序，不影响物理数值。
2. tests/support/spr_3d_test.cpp：CPU/GPU伴随链接VS项目对象，调用唯一生产ComputeStep_Sym；只设初速度、采样与记录，不复制积分器。
3. tests/support/spr_3d_build.ps1：CPU伴随构建；现有gpu_fixture_build.ps1复用不改。
4. tests/support/spr_3d_run.py：全新GenCase、粗／半步执行及原生安全检查、PNG/CSV；GPU构建标签更新为修复后r2；旧runner已归档。
5. tests/support/spr_3d_review.py：完成运行的同dt CPU/GPU、历史和原生切片；不反馈求解。
6. tests/support/spr_3d_cleanup_check.py：退出错误修复的memcheck与0 ULP证据复核；tests/support/spr_3d_audit.py：独立完整样本与哈希复算。
7. tests/support/spr_3d_continue.py：仅补之前未运行三组合的一次性序列，已结束，不再启动／重设。
8. tests/configs/spr_3d_r1_{edge3,corner3}_s{2,3}_{c,h}_Def.xml（8份）、xspr_3d_r1_{edge3,corner3}_s{2,3}_win64_{CPU,GPU}.bat（8份）：浅层可执行测试入口，拒绝覆盖；正式根XML/BAT不改。
9. tests/figures/spr_3d* PNG/CSV、tests/logs/spr_3d*构建／运行／检查／状态／visual／backup记录、tests/notes/spr_3d*：完整证据和说明。逐文件清单由backup记录列明；旧失败日志同样保留，不冒充成功。
10. doc/xml_format/_FmtXML_ElastoplasticSoil.xml的SPR注释：补已验证三维范围与数值，不改默认值；case06 tests/notes/spr_delivery_index_r1.md补入口和资源修复说明。

## 清理、备份和下一步准入

最终默认CPU Debug再次构建通过（退出码0，本次增量构建无错误／警告），日志为logs/spr_3d_final_cpu_debug_r1.build.log。没有再次修改已通过GPU内存检查的源码。

未发现可安全删除的本轮__pycache__／原子临时文件，删除／移动0。原生pulse/BI4、执行程序、源码快照与历史依赖均保留；选择性Git仅含代码、输入、说明、紧凑图表和收据，不是原始数据云备份。原始数据在本机，不声称已上传云端。Git实际节点及白名单见logs/spr_3d_backup_r1.complete.json。

| 后续对象 | 当前判断 | 执行边界 |
| --- | --- | --- |
| Yao二维SPR | 已完成10 s关/开/半步和图/CSV，无需为“正式”标签重跑 | 下一步核对正式入口与已验证配置的差异，再用真实发行程序做最小接轨；不能将伴随运行直接改名成正式程序结果 |
| 三维固定平面弹性 | 本次棱边/墙角短时一致性通过，可作为正式平面算例的边界准入证据 | 仍需目标算例自身的加载、排水、网格、理论和时长验证，不直接外推完整3D |
| Cryer球体 | 既有SPR关闭的三维u-pw理论回归候选 | 球体外表面不是固定平面SPR；先核参数／成本，不能开启SPR来冒充曲面验收 |
| Selborne三维 | 不可正式启动 | 缺多材料／局部随时压力边界；保留禁用BAT，不绕过，也不在交付阶段顺便扩物理 |

不继续把所有边界问题作为无限前置门。本阶段的静止凸平面有界证据可收尾，后续优先二维发行程序接轨；倾斜NoPen、曲面／运动墙、塑性、大转动及精确HG重启仍未验收。HG独立且仅限原二维范围；不重开KEEP、u-pl、TPI。
