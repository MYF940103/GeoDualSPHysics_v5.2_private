# Lstar下一独立窗口：唯一direct-owner终态投递建议

2026-11-15。只读现有实现、旧真实queue收据与必要当前stat；仅新增本文。没有启动/停止/恢复/重挂任何owner、solver、reader、watcher或queue，没有执行Codex命令、连通性自测、Git或SHA。本文不启动Lstar物理窗口或准入后续native。

## 已实证可复用的最小实现

`support/c08_h18_rv_radial_gpu_run_r1.py:250–267` 的 `terminal_once`，以及 `support/c08_h18_storage_window_r1.py:111–140` 的 `notify_once`，均由原直接owner在最终run/status保存后调用（分别353行、232行）。无需额外轮询进程、递归任务或第二watcher。

旧真实证据为 `logs/c08_h18_rv_radial_window_GPU_r1.queue_attempt.json/.queue_result.json` 和 `logs/c08_h18_storage_window_GPU_r1.queue_attempt.json/.queue_result.json`。二者均记录attempts=1、timeout_s=45、do_not_resend=true，实际退出0、status=queued，stdout明确对应thread及message ID，stderr为空。它们已投递过，绝不重跑/重挂。

两次使用的根thread均为 `01a07683-bc64-7463-8db7-9ee6243967d8`，CLI是

`C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1106.51428-win32-x64/bin/windows-x86_64/codex.exe`

本次只读stat仍为373698352bytes、mtime_ns1794391544005116300，与两旧attempt记录一致。未用help、测试消息或任何实际queue来验证。旧rc0证明历史请求已入队，不证明未来投递或任何数值/物理验收。

## 下个Lstar owner的最小合同

1. 只为新的独立Lstar标签准备一份root运行准入及一位直接owner。准入绑定新的runner/note、已通过GPU实现资格、程序/输入/PRE/标量计划及CLI路径/stat；没有第二watcher。只声明一次新的solver运行，不复用旧owner或失败目录。
2. **根线程工具启动owner时**核其 `CODEX_THREAD_ID` 等于root准入中的thread。此次子代理工具环境实际为 `01a1db13-adee-7000-ba0b-8fef83119164`，不能拿它冒充根thread或在子代理里发送根通知。根刚确认的thread与上述历史值相同；实际启动前仍由根自己的环境核对。不要只硬编码一个未经根核实的ID。
3. 所有新start/call/run/status/queue_attempt/queue_result路径先fresh检查。长算过程中由同owner持有原真实Popen/Win32子进程句柄、exe/argv/创建时间，最后保留真实退出、首因、原样末PART行和冻结依赖。solver完成后派生失败必须仍标明solver_completed，不因通知失败重算。
4. 原run与status先完整保存并封存，再由同owner进入一次终态函数。新queue_attempt在调用前以独占新文件写入，记录最终run stat、目标thread、CLI stat、完整argv、attempts=1、timeout_s=45和do_not_resend=true；已有attempt/result/partial一律拒绝再试。
5. 唯一通知命令仍为 `codex.exe queue --thread ROOT_THREAD --message MESSAGE`，调用参数列表，cwd为case根、`CREATE_NO_WINDOW`、capture stdout/stderr，timeout=45秒。只调用一次；不在函数内调用solver、native、VTK、分析、构建、Git或另一个owner。
6. exit0记queued并保留stdout实际message ID；非零记queue_failed；TimeoutExpired记delivery_uncertain。超时可能已投递，**不得重发、重挂或添加watcher来补偿**。CLI若缺失/绑定变化，保留失败记录，不临时换另一版本试发。通知状态与已封求解结果分开，不把投递成功当物理验收。

建议新owner在实际solver前仅检查已验证CLI路径/stat仍可用，不运行连通性测试。终态使用同一绑定路径；不重新搜索“最新扩展”而无声更换CLI。源函数可复用上述一次调用结构，通知文字改成Lstar本次真实scope，不携带旧RV telemetry或旧worker标签。

## 消息与失败范围

消息只报告终态记录位置与待审状态：成功仍是pending native/physical review；失败保留真实首因与最后已保存信息，不推断未保存时刻。指示根先查已有/活动reader，再独立决定一次原生审查；不得由投递自动启动reader、下一solver、half、PRE或其他psi。旧22数组、IDs、clock/signed、ledger、边界与原安全门不因完成机制改变。

直接owner若被系统关闭或在写最终记录前异常消失，不能保证送达；缺提醒不等于solver仍活跃或完成。此限制不能以重挂旧owner或多重watcher掩盖，后续只读审实际进程/文件证据。本文没有执行或重新布防任何完成机制。
