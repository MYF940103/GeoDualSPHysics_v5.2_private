# SPR当前交付索引与保留范围

2026-10-25更新。仅整理入口与证据状态，不移动或删除历史文件，正式根输入/输出不改。

| 试验标签 | 状态与用途 | 主要入口 |
| --- | --- | --- |
| spr_yao_grid02_r1 / grid10_r1 | CPU .02/.1 s，相同步长原生前缀与半步通过 | spr_yao_r1.md |
| spr_yao_gpu_load_grid10_r2 / gpu_post03_r1 | GPU .1/.3 s，输出诊断修复后检查通过；旧r1保留但不作当前控制 | spr_yao_r1.md |
| spr_yao_cpu_gpu_1s_r1 | 全1001跨后端/独立半步及图表通过；已备份759d34a | spr_yao_1s_r1.md |
| spr_yao_axis01_r1 | .1 s NoPen开启相容性通过，但未触发修正，开关0 ULP | spr_yao_axis_review_r1.md |
| spr_yao_10s_r1 | GPU关/开/半步10 s已完成；1001保存时刻安全/半步、前缀及场图通过，有界数值验证 | spr_yao_10s_review_r1.md |
| case02 spr_3d_r1 / spr_3d_next_r1 | 三维棱边/墙角、NoSlip/FreeSlip共16次2 ms运行；8半步及8跨后端对比通过，不是完整三维理论验收 | [三维核验](../../../02_TerzaghiConsolidation_q0_PR/tests/notes/spr_3d_review_r1.md) |

各标签对应configs/XML及同名可点击BAT、outputs原生结果、figures/PNG及CSV、logs/运行与检查清单。沿用已有scripts，不新建同义support或把文件再套深层目录。生产多平面候选是八文件7fda9ffe检查点，后续未再改生产方程。三维检查额外修复JSphGpu析构时GaugeSystem晚于cudaDeviceReset释放的问题：仅资源生命周期调整，Debug内存检查由1错降至0错，前后原生字段0 ULP；范围见上述三维核验。

## 清理检查与依赖

- 已完成10 s核验引用1 s/轴NoPen visual收据、既有GPU生产步伴随、其构建清单和两种原生BI4读取器，因此这些目录不能清理。旧原始BI4、当时程序/源码快照、带哈希历史清单继续保护；Git中的输入/脚本/PNG/CSV不是原始数据云备份。
- `scripts/__pycache__`未发现；没有确认可安全删除的本轮临时缓存。原子状态临时文件无遗留，失败构建预检未生成程序输出。实际删除/移动数量0，避免用“目录大”作为删除依据。
- 原case02三组正式结果与图表数据、Yao旧10 s不同滑移/阻尼对照是独有历史材料，不重复跑、不覆盖、不当当前SPR单因素控制。
- 10 s终态已复核，6116个唯一文件哈希通过；本轮依赖核查未发现可安全删除的缓存，删除/移动0。选择性Git只备份本轮脚本、图表、CSV、收据和说明，不纳入原始BI4/程序。完成状态见logs中的spr_yao_10s_backup_r1.complete.json，不改写旧备份清单。

## 尚未完成的物理范围

10 s二维数值对照已完成：近墙法向残余明显下降，5–10 s孔压继续耗散，加载区上部层间锯齿未消失。本轮没有独立二维解析沉降真值、完整长周期或10 s CPU控制。斜NoPen旋转不一致、曲面/运动墙、塑性、大转动和精确HG重启没有准入；不因静止凸平面的有界结果扩大这些范围。不重开已停止的KEEP/u-pl/TPI开发。
