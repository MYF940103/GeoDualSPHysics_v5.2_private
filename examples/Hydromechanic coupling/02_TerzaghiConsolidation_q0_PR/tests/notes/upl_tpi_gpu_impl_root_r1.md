# TPI GPU 实现阶段根审查 r1

2026-11-17。此记录只采纳有实际结果的实施资格，不作物理发行验收。公共源码和正式 XML/BAT 未改变。

## 实际改动与构建

私有 r2 源树保持 r1 的全部方程、API 和类布局，只修正 source-pressure/owner-role 守卫并增加独立 device fixture。Debug r2 实际重编一个 CUDA TU，采用已成功 r1 的三个 host TU；Release r3 重新编译四个 TU、保留匹配基线107个对象，111对象链接。新 Release 入口只兼容实际历史 call.log_stat 字段和独立标签，不改源码。

原 build_r3 note 因写入编码不完整；以本记录及实际作者脚本、调用/构建收据为准。不得为修正文档而改动活动任务绑定的旧文件。

## 原已完成 Debug 的离线恢复

原 Debug_B_debug2steps_r1 求解器及 sanitizer 真实退出均0，memcheck0。原wrapper误用了Pos-Double，而实际GPU使用Pos-Cell；Hardware实际为Gpu_0标识，需不区分大小写。两次中间离线审查的失败也保留：第一次比较了带额外sha256字段的字典，第二次仍受Hardware大小写误判。独立audit_r3只修上述分类/三stat比较，原run/status和失败审计从未改写或重新求解。

只有首次实际native read使用既有r1读取器；新reviewer_r4保持原5个科学函数。两帧、1040 IDs、22数组、实际dt/Step/有符号时钟和原ledger门通过；真实侧车2000行，1000个非初始J计算逐bit符合原CUDA允许算序，无新增ULP容差。原HG4/2/2/4、cache3/1、dt/tau和spin门通过。16个真实device fixture全部成功。该两步窗无排水后覆盖，也不是Release位真值或完整理论精度。

## Release默认A实际资格

24000步、344原生帧，actualend=.1500034332275618s；全部原native、排水、时钟、HG门通过。独立raw22工具在真实共享的旧150帧中比较33072000数组字节和4200有符号clock字节，差异均0；保留旧150/新344头，未改原生记录。旧控制仅到.010200233459472378s，不把它说成旧.15s控制；新后194帧不属于该位比较。

B/C各自同算法CPU/GPU差界、完整科学图表/100Pa应力门、完整周期与Cryer峰值/衰减仍需后续实际结果。任何源码/程序构建或正常出口均不能替代这些验收。无新增half链、无C08塑性HG恢复，无旧worker重启/重挂。原暂停C08和全部正式结果仍保护。
