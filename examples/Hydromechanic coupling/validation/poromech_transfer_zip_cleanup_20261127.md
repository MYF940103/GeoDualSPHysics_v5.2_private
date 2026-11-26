# 2026-11-27 传输 ZIP 去重

结果包按已有展开文件逐成员核对。移机包按配套的实际工作目录与冻结输入核对。旧版本保留程序、输入、材料或失败证据时，源路径与收据仍按[归档策略](poromech_archive_policy.md)管理。

| 对象 | 处理 | 证据和恢复入口 |
|---|---|---|
| C08 r1、r2 和预载 CSV 热修复 | 删除 3 份本地移机包，40,091,181 逻辑 B | 三个完整 ZIP 与提交 `63be0dd` 中对应 Git blob 一致。需要原包时可从该提交检出指定路径。当前 TPI 的运行依赖在 `support/runtime_tpi_r1` 与正式输入中。 |
| C04 公共 SPH TPI、C05 Lian HGSPR 两个移机包 | 删除 2 份传输包，38,486,253 逻辑 B | 两包各 17/17 成员均有相同保留副本。C04 使用实际展开目录。C05 正式 XML 的确切副本在 `support/frozen_xml`，其余在 `tests/outputs/lian_server_smoke_r1`。 |
| C03 预载结果传输包 | 删除 1 份包，69,337,979 逻辑 B | 真实展开根内 224/224 文件长度与 CRC32 一致。共享重启所需的原展开目录保留原位。 |
| C03 滑坡结果传输包 | 删除 1 份包，456,527,349 逻辑 B | 真实展开根内 1225/1225 文件长度与 CRC32 一致。历史滑坡原生输出原位保留。 |
| C04 空的失败打包占位 | 删除 1 份空包，0 B | 失败收据和旧程序仍在。 |
| C04 已迁到 C 盘的峰窗结果传输包 | 删除 1 份包，3,429,948,105 逻辑 B | D 盘双层同名展开目录的 597/597 文件长度与 CRC32 一致，合计 4,564,122,730 B。前一轮迁移收据描述当时状态，本次退役收据描述 C 盘副本现状。 |

[成员对应清单](server_transfer_zip_unpacked_20261127.check.json) · [C04/C05 清理](server_transfer_zip_removed_20261127.check.json) · [C08 清理](../08_LianSaturatedColumnCollapse_u_pl/tests/logs/c08_transfer_zip_cleanup_20261127.check.json) · [C03 预载清理](../03_RetrogressiveSlopeFailure_u_pw/tests/logs/retroslope_prestress_transfer_zip_cleanup_20261127.check.json) · [C03 滑坡清理](../03_RetrogressiveSlopeFailure_u_pw/tests/logs/retroslope_failure_transfer_zip_cleanup_20261127.check.json) · [峰窗清理](cryer_peak_transfer_zip_removed_20261127.check.json)

五个 Cryer 冻结 ZIP 为正式 BAT 输入，保留原位。C03 的旧 `CaseRetroSlope_u_pw_failure_Def.zip` 封存了不同数值配置，包括旧 h/dp、人工应力和正式时长，作为历史输入保留。按用户确认保留 C08 r3 和 Cryer weak-full 两个服务器包。其他源码包、唯一恢复档和在用资料继续保留。
