# 已停止B长算的前2s原生观察适配器

仅新增同名 `support/*.cpp`、`support/*.py` 和本文。作者没有构建、解码、运行求解器、
调用队列、Git、哈希或改写任何旧证据。每个build/read/review动作仍须根完整阅读后独立准入。

## 原数据身份和停止事实

固定来源为 `upl_tpi_gpu_Release_B_full2tv_r1`。原start记录owner38740、GPU41920，
程序为原 `upl_tpi_gpu_full2tv_Release_r1`，输入为原full seed，原时间步
6.250143051147461e-6s，B alpha=.5/M0，原HG/SPR/AV/边界均不变。

原 `timestep_retirement_r1.request/result.json` 记录用户要求改用大步长后，
先退役owner、再退役GPU；两个已取得句柄的实际Win32出口均为C000013A，
之前均为STILL_ACTIVE=259。这是外部intentional stop，不是原求解器正常返回或失败时刻。
原 `.call.json`、`.run.json`、queue attempt没有形成，继续保持缺失；本适配器不制造它们。
原console最后PART行与Run.out最后PART行各自原样保留，不能据其中之一推断未保存停止时刻。

停止审计保留1353个BI4原文件。本次只观察第0至1291，共1292个文件；后61帧保持原样，
不解码、不验证其科学字段，也不声称已经认证。原完整计划1682行和所有原始头/clock均不修改。

## 明确选择原prefix

原full计划row1291的真实值为：completed320001、saved Step320000、
time=2.0000520265024098s、forced_final=0。它不是旧2s候选的forced320000保存态。
原row1292已到2.1822374462992715s，故选择1292帧覆盖所需前2s即可。
排水事件part117/completed1600仍preopen；part118/completed1601首post。
所选prefix含1174个post保存态、11740个真实排水接收者检查。

C++先逐行/逐scalar +=dt验证完整原1682计划、原11661219更新和72.88428689946836s计划末点，
再仅在新读取器内选择前1292行；原CSV不改、不缩放、不用n*dt冒充真实clock。
`ObservedPrefixSequence`只要求这1292个原文件各自存在，不因后面原文件仍在而拒绝，
也不把原目录裁剪成1292个文件。原Load/Initial/Read的22typed/1040IDs、ledger、
P0/float excess/几何/全部有符号dterror<=1e-14/排水/HG相关原生字段门保持原样。
没有把初始signed诊断或fixed字段改写为零。

新导出仍为原五二进制布局及ledger/历史/IDs/columns等标准产物，只有新头的记录数为1292。
completion明确 `partial_observation=true`、`source_full_completed=false`、
`observed_prefix_complete=true`、`declared_window_complete=false`，并保留原full计划声明。
该completion仅表示所选已保存原生prefix读取成功，不表示旧full求解完成或物理验收。

## 时层和侧车审查

只读取原 `UplTpiGpuR1.policy.json` 与CSV的前1292*1000行，即1292000个实际保存材料行。
后续CSV行允许存在，但不调用next检查/解读它们，不认证未读行。没有full summary时不能补造；
本稿明确要求它继续不存在，不从部分CSV虚构全程HG summary或全程时间积分计数。

压力预测、输入/输出RN-float及保符号FTZ、raw q+R/S、真Dirichlet+0和J的两种合法CUDA
末级算术路径直接保留已审GPU r5/full reviewer的公式，不放宽ULP或5Pa等价门。
PTX证明仍来自原真实CUDA对象与实际cuobjdump记录；只把其source-build绑定改为原start的
已通过build，避免读取不存在的原full.run.json。新观察没有额外solver或新的GPU kernel调用。
每个所选侧车行的实际ID、clock、step、七字段位检查和HG快照计数逐一审查。
未保存历史不被当作独立观测；PorePressRate仍是旧缩放endpoint residual而非M0真实dp/dt。

不新增343短窗字节prefix证明链；旧.15s真实资格继续保留，仅作既有实施来源。
本稿不跑CPU、新A、新half、20us、full2Tv或其他物理参考。

## 构建、唯一读取及路径

构建复用原已通过纯reader的真实结构化CL/link call.argv、归档头/loader/runtime，
不使用带未quote源路径的CL.command.tlog。严格要求原完整source token恰一个，
只移除该完整token并加入新CPP；sourceDependencies.Source必须等于本新CPP，
不接受stray source覆盖依赖的情形。新obj/PDB/ILK/exe均在独立目录，旧工具和loader不改。
`pin_reader`严格核新build stage、固定程序路径、runtime及原依赖未变。

- 新工具目录：`tests/outputs/upl_tpi_gpu_partial2s_native_r1_build`。
- 新解码目录：`tests/outputs/upl_tpi_gpu_Release_B_full2tv_r1_observed_partial_2s_native_r1`。
- 收据：`tests/logs/upl_tpi_gpu_partial2s_native_r1.{build,read,review}.json`。
- 每个动作的root admission为 `stage=upl_tpi_gpu_partial2s_native_r1.<action>_admission`，
  passed/action_only=true，inputs列全部实际消费stat。

build输入包括新三稿、复用full-native/CPU-build helper、原纯reader recipe/工具/归档头/库/runtime。
read/review还包括原start/run_admission/stop request/result、原program/build/prepare/runtime/seed、
完整原plan及所选1292原文件stat；原log和Run.out仅按停止审计绑定，不重写。
review另绑定唯一新read/call/全部新导出、原policy/CSV及原PTX实际证据。
只核必要stat，不重扫原源码、objects或BI4 SHA。

已有新receipt、read call/log或输出目录任一存在即拒绝；读取前检查已有/活动reader，
不重复解码、不自动恢复旧worker、不追加watcher或队列。
失败保留新partial和真实首因，已完成solver永不重跑；不从停止通知推断物理状态。

```text
python -B tests/support/upl_tpi_gpu_partial2s_native_r1.py build --execution-authorized --admission ROOT_JSON
python -B tests/support/upl_tpi_gpu_partial2s_native_r1.py read --execution-authorized --admission ROOT_JSON
python -B tests/support/upl_tpi_gpu_partial2s_native_r1.py review --execution-authorized --admission ROOT_JSON
```
