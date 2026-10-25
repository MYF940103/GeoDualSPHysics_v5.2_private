# case02 tests 清理：保留结论与可恢复原始数据

2026-10-25，用户明确授权先同步Git，再清理已得结论的大型输出。清理前代码／工程已在本地和远端u-pw一致，节点04b5982479611ea362190596e1bed093826013b0；274项无关算例／编辑器历史变更和删除不混入本轮提交、不恢复、不清理。源码／VS工程干净，本轮不改方程和生产代码。

## 范围和处理

清点outputs共1133个直接子目录、约99.78 GiB；其中CSV约56.43 GiB、BI4约30.78 GiB。本轮精确白名单为36个已结束／退役的逐粒子CSV（每个至少64 MiB），合计49.93155 GiB，不是figures中的紧凑图表数据。主要是历史边界／KEEP密度诊断、CPU合入／GPU同步15 s原生轨迹，以及可由保留BI4导出的CPU/GPU完整周期state.csv。

不因文件名含failed/formal就整目录删除。保留全部配置、BAT、脚本、图／图表CSV、结论、历史原始日志、哈希清单、BI4、PartExtra、读取器、源码和程序快照、ZIP。正式case根、其他case完全不在删除目标中。未改写历史检查为“现在通过”，也没有重启solver或旧通知器。

| 试验族 | 当前性质 | 本次处理 |
| --- | --- | --- |
| hg_bd密度／KEEP／边界诊断 | 已分析或退役，含中断／未准入记录，不能统称通过 | 只压缩白名单大型原生CSV，图表、结论和失败记录保留 |
| hg_release、gpu_spr_15 | 已完成CPU合入／GPU实现回归 | 原始CSV无损归档，需要再做逐帧回归时先恢复 |
| gpu_full_2tv | 已完成CPU/GPU一维工程范围对比 | state导出CSV压缩；原生BI4和正式发布数据不动 |
| traction、stress、pore_double | 历史扰动／精度排查已结束或退役 | 仅归档明确列出的CSV，读取器和源码／程序快照保留 |
| 最新spr_3d／spr_planes | 当前边界证据 | 不在本轮白名单，不动 |

每个原始CSV在同一路径旁生成`.csv.zst`，zstd level1、两压缩线程、内置校验；流式读原数据计算SHA-256，完整解压归档重新计算长度／SHA，再计算归档SHA。全部一致且源文件大小／修改时间未变，才由PowerShell用LiteralPath删除精确白名单内的未压缩CSV。原路径必须在case02 tests/outputs内，拒绝重解析点／Git跟踪文件。移除的只是冗余未压缩副本，不是丢弃唯一原始信息。

## 依赖和恢复

旧运行／分析清单仍引用原始CSV路径，故本轮不是“所有旧脚本无准备即可继续运行”。需要历史重查时，先按logs/cleanup_r1.plan.json中的index解压：

```powershell
& 'D:\Anaconda3\python.exe' -B tests/support/cleanup_archive_r1.py --restore 0
```

此命令从case02目录运行，0替换为目标index；默认不覆盖现有文件，恢复后重验原SHA并恢复原修改时间。原路径0号已经实际解压、SHA与长度校验通过，再移除测试恢复的未压缩副本，归档保留。证据：logs/cleanup_r1.restore_test.json。日后恢复需要足够磁盘空间；当前Anaconda已安装zstandard，无新增安装。

旧分析默认不自动识别zst，本轮不修改已绑定哈希的旧脚本，不把归档恢复当HG精确重启，也不声称数据已上传云端。若不恢复，历史全原生重新核验会报告文件缺失；这属于归档状态，不是原求解失败。

## 新增／修改文件

- tests/support/cleanup_outputs_r1.ps1：只读分目录／扩展名空间清点。
- tests/support/cleanup_archive_r1.py：单文件无损压缩、完整解压验证与按index恢复，不删除原文件。
- tests/support/cleanup_apply_r1.ps1：精确路径／重解析点／Git／元数据保护与验证后的LiteralPath移除，逐项记录实际进展。
- tests/logs/cleanup_r1*：清点、白名单、逐文件原SHA／归档SHA、恢复测试、进度与Git交付；失败／中断不伪装完整成功。
- tests/README.md、本记录：当前归档入口、恢复方式和旧依赖边界。
- tests/.gitignore：仅忽略outputs内本地csv.zst，防止把大型归档误塞进Git；恢复脚本／清单不忽略。
- tests/outputs中白名单CSV的同名zst归档；不重新排列或深套目录。

所有操作无C++/CUDA、VS、正式参数或默认值变化，因此无需改XML参数指导或重编GPU。默认CPU Debug构建在收尾检查一次；本次Git只保存上述代码／索引／紧凑记录，不纳入原生BI4、大CSV或zst。

实际已处理数量、压缩后大小、净释放空间与最终备份节点以logs/cleanup_r1.status.json、cleanup_r1.final.json和cleanup_r1.git_complete.json为准，不把计划49.93 GiB误称已全部释放。

## 完成结果

| 项目 | 大小／数量 |
| --- | ---: |
| 已归档原始CSV | 36个，49.93155 GiB |
| 同名可恢复zst归档 | 36个，13.57788 GiB |
| 净释放磁盘空间 | 36.35367 GiB（39,034,453,803字节，约39.03 GB） |
| outputs清理前／后 | 99.77946／63.42579 GiB |

1133个输出子目录的文件数逐一不变，原文件用同名zst替代；逐目录的BI4、IBI4、EXE、DLL、OBJ、PDB、BIN、OUT、VTK数量和总字节逐项保持。原生数据和程序／读取器快照未删除。清理仅移除可恢复的未压缩CSV副本，不是移入回收站；恢复应使用上述脚本和同目录归档。

原始data约30.78 GiB的BI4及冻结构建、正式输出不作进一步永久删除。归档留在本地，Git只同步工具／结论／哈希／空间清单，不是这些13.58 GiB数据的云备份。剩余63.43 GiB不是全都无用，不能为了减少目录体积而默认删除。
