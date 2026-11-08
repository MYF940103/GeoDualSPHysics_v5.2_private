# n4 与 n3 的真实保存态前 0.90 s 对照

只新增同名 Python 与本说明，事前已确认不存在且未被 Git 跟踪。作者只做静态 AST/接口核对，不 import 或执行，不触碰活动求解器、输入或依赖。

本脚本必须等 `upl_c08_asn4_window_GPU_r1.run.json` 及同 tag `.native_r1.json` 真正通过后，由根线程全文审阅并单次执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_asn4_compare_r1.py --execution-authorized
```

n4 通过原生收据定位 `outputs/upl_c08_asn4_window_GPU_r1/native_r1`，严格消费 90 帧、6805 IDs、22 typed 数组、AS .2/指数4、CompletedOnly、保留5床点/实际退役255及原时钟/ledger/FS/plane 数值门的实际成功记录。n3 用已完成根 r6 的真实 `.run.json` 与 `postprocess_r6.json` 定位 full3s native，复用已审 `upl_c08_n3_full_compare_r1.load`，保留原 **300** 帧头，只读实际前90记录。不是把66帧窗口外推到90，也不把 causal 观测程序替换为物理真值。

两文件各顺序读一次所需90记录，复用 `c.inspect/quantities` 与 `cluster.measures/summarize`。逐帧保留全部6805 ID/22字段有限检查，并按实际保存 time、tau、Step 精确匹配，固定 P0 全字段逐字节一致。两组真实程序/build/PRE/源时钟相同，实际 XML 除声明的指数和总时长外一致；未读取 BI4、重新解码、扫 SHA 或读取 dense trace。原生两个真实文件头始终为300与90，不改写。

输出新浅前缀 `tests/figures/upl_c08_asn4_compare_r1_*`：

- `overview.png`：5000土粒子的保存孔压最小/最大/RMS、真实 PRE 基准平均沉降和位移RMS、速度、κ、J/n/k范围、总应力RMS及粒子中心前缘/高度。
- `spacing_material.png`：唯一土粒近对 `<.5dp`、`<.7dp`，最近邻最小/5%/中位数，以及 `rNN/(dp sqrt(J))` 的描述性压缩校正；固定5944/5945/7017/6814材料的压力、速度、κ/J与位移轨迹。固定点位移相对**各自第一保存态 τ≈.01**，不是 PRE/t0；CSV保留绝对坐标。全域平均沉降仍是真实 PRE 位置基准。
- `morphology.png`：两组在实际 part49/57/65/79/89（约τ=.50/.58/.66/.80/.90）的全部5000原始土粒坐标和κ，固定边界另灰点。共享实际全范围κ色标和物理坐标窗口，图题写实际τ；不插值、滤波、平滑、拟合或改选材料点。
- 对应 `history.csv`、`cohorts.csv`、`material_points.csv`、`parameter_differences.csv`、`morphology.csv`。六个空间/κ分组沿用旧定义；坏/空组的已有描述性空值保留。新鲜输出拒绝覆盖，检查写 `logs/upl_c08_asn4_compare_r1.check.json`，结束复核必要源stat。

n3/n4是改变人工应力指数后的参数响应，不是半步误差或5 Pa等价验收。最近邻和局部各向同性sqrt(J) proxy不能排除真实剪切/滑移，不能单凭近对数断言张拉根因或已消除张拉不稳定。0.01 s 保存极值不等于 n3 稀疏/稠密阶段观测峰；本脚本不混合采样方式。固定面投影反力/J/Darcy未闭合等原模型限制仍在，结果 `physical_acceptance=false`，没有自动下一个求解器或其他ψ组。
