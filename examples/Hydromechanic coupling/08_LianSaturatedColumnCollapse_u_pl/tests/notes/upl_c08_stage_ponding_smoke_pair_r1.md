# 2 ms 三组 native 的功能配对

仅新增同名 support Python / 本说明，事前确认不存在且未跟踪；作者不执行或 import。输入准确为 CPUdebug_r1.native、GPUdebug_r2.native、Release_r2.native 三收据；CPU 的有效 source_run 为独立 adoption，原 r1 failed postcheck 仍保留。

只消费已通过的各自 native / 实际 reader 出口 / completion / ReleasedSubstages metadata，绑定同一 source_r2 / 原 PRE / 实际源时钟和各输出 stat。dtype 由实际22行 typed_layout 构造，三组各只 mmap 两条原记录（合约8.7MB），不重解码、不重跑全部22安全扫描或历史 SHA。实际6805 IDs一致，5000土粒固定 ID 2060..7059；原 PRE相同，因此两位置之差即对应材料位移之差，不将第一保存帧当初始位置。

比较 CPU Debug→GPU Debug、CPU Debug→GPU Release 的两个实际保存时刻：原功能门 p RMS≤5Pa、每材料 XYZ 位移差范数最大≤.005mm、时钟差≤1e-14s。J / n / k / κ / 速度和有效应力减当前p后的总应力差只描述，不新增阈值。Debug / Release 的编译差异明确保留；这套预算可作接口功能对齐 screen，不能把它说成单一误差归因、跨配置0ULP、half收敛或物理精度验收。

root 全文审阅且三组 native 真通过后一次显式执行：

```powershell
D:/anaconda3/python.exe -X utf8 -B tests/support/upl_c08_stage_ponding_smoke_pair_r1.py --execution-authorized
```

只输出 `logs/upl_c08_stage_ponding_smoke_pair_r1.check.json` 和 `figures/upl_c08_stage_ponding_smoke_pair_r1.csv` 四行；失败也保留已观测行 / 首因，不放宽门。无 solver / reader / build / queue 或自动窗口准入，physical=false。
