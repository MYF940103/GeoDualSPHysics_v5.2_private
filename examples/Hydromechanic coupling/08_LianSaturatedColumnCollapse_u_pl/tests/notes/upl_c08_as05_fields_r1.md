# ε=.2/.5的两个保存态场图（作者稿，未执行）

仅新增同名support脚本及本note，先要求已完成compare check通过，再复用其纯load/inspect。各组typed22只打开一次，核原6805/22/66头后seek part22和65，共读取4个完整record；不扫其他62帧，不BI4解码、重做VTK、运行solver/build或读取dense trace。实际native目录继续来自封口receipt，不能猜r2 owner的输出名。

2×4八axes固定顺序为part22 ε.2、part22 ε.5、part65 ε.2、part65 ε.5；上排孔压，下排κ。实际tau与Step严格配对，标题用真实tau，CSV保留完整double clock。5000个原土粒逐点raw scatter，无平滑、插值、裁剪或拟合；FS2/3土粒用三角，其余土粒圆点，1805个保留fixed markers另画灰色方点，不把墙值加入色标。

四态全部20000个土粒样本共同确定压力色标（kPa、保留负值），以0为白色中心、两侧分段线性；κ另用共同线性色标，均为完整实际min/max。所有axes相同物理窗口、等比坐标；窗口取四态全部soil范围再加2dp=.08m显示墙层，远端长床可在视窗外，所有soil场点均在视窗内。CSV只4行各态土粒范围、p/κ极值与FS计数，check明确显示范围/全局norm。

输出fresh `tests/figures/upl_c08_as05_fields_r1.png/.csv` 及同名logs check，不改旧compare图或数据。part22可用于观察新保存态负压变化，但不能把0.01秒采样极值叫作dense峰；这是ε参数对照，不是理论/半步长验收或物理精度结论。PNG仍需根视觉审查。

root全文审后唯一调用（本稿未import/运行）：

```powershell
D:/anaconda3/python.exe -B tests/support/upl_c08_as05_fields_r1.py --execution-authorized
```
