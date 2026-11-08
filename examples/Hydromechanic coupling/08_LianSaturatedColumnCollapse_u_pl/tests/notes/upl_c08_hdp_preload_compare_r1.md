# h/dp1.2 与1.5同程序短预载：派生CSV对照

只新增同名 support Python/本说明，事前查不存在且未跟踪。作者未执行或import；不读BI4/typed22、不解码、不运行求解器/VTK/构建/队列，不修改旧输入/程序/数据。只消费**r3**已通过的两份原生诊断CSV：`outputs/upl_c08_hdp12_preload_partial_r3` 与 `outputs/upl_c08_hdp15_preload_partial_r3`，分别绑定各自同名 `.check.json`。r1链接失败和r2错误10幂ledger的partial均保留，不作为本图输入。

当前源码的变k是 `k0*exp((J−1)/[(1−n0)Ck])`。GPU rate、CPU和saved-J输出同式，k0/n0为实际float升double，Ck=double2；不是10的幂。r3只修读取器参考式，原数值门保持。脚本复用r3所有22/P0/κ0/ledger/固定marker/clock/signed等通过收据，不再扫描原始数组或SHA。

根全文审阅后一次执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_hdp_preload_compare_r1.py --execution-authorized
```

只在两边真实原生通过、绑定有效时读CSV。核相同runtime_r6程序/source_build、实际float材料系数、每帧5000soil与50层各100 ID、原生实际clock/Step；按共同part逐条要求**exact actual time及completed_step**一致，绝不近时匹配、插值或用5Pa门代替。初始材料ID/x0/z0/P0亦须相同。h12完整短控制可能比h15多最后一帧，所有实际历史及层CSV均保留，`exact_common_clock`列标识共同部分；额外末帧不伪装成h15已有结果。

输出新浅前缀 `tests/figures/upl_c08_hdp_preload_compare_r1_*`：

- `history.png`：全程实际保存时间上的DP fmax、p、速度、J、有效/总应力、FS23数量和fmax位置；另画固定材料ID7010在全部共同已导快照的p/f。初始2h边界带随H变化、并非同一材料集合，因此不把其计数当逐材料对照。
- `profiles_fields.png`：共同导出时刻的50层p/fmax/速度/J曲线，以及两共同snapshot时刻每组原5000soil f散点。实际可用的part25/50/51优先；若只剩一个正时刻，另一张采用实际part0，不发明新快照。红星仅标保存态最大f。四图共享全点真实f最小/最大色标，无平滑/裁剪/拟合。
- `history_data.csv`、`layers_data.csv`保留两组全部原CSV数值文本并加profile/hdp/共同标记；`fields_data.csv`逐点对应绘制的四张散点；`material7010_data.csv`保留固定ID7010的全部共同快照原字段。

检查写 `logs/upl_c08_hdp_preload_compare_r1.check.json`，记录实际帧数、共同时间覆盖、额外末帧、输入stat及生成文件；拒绝既有输出，不自动重试。没有共同正时刻导出snapshot则保留失败原因，不编造图。Python将OMP/OpenBLAS/MKL/NumExpr线程设为1，只有离线派生分析，不影响其他物理程序。

这是两个同runtime/law2 fresh源的**短预载空间支持敏感性**，不是半步、理论精度或平衡验收。h15实际求解已exit1，只有52个已保存安全态；h12正常退出208000/53只说明受限.52s完成。二者均非10s认证PRE。f使用有效应力与真实float-radian输入；保存态fmax不能恢复未保存被拒trial的ID、值或故障时间。FS正/负/零只作保存分类观察，不改原源positive-only表面政策、不称全零drained门或接触/反力闭合。
