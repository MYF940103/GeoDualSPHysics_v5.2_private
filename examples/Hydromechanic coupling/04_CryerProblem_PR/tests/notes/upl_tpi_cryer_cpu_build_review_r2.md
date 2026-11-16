# C04 完成构建的 r2 纯离线采纳审查

作者稿，尚未执行。本轮只新增同名 support Python 和本说明。
不重编、不重新链接、不启动 help/solver/reader/native/VTK，不运行 Git、
SHA 或后续任务。原 r1 false 收据、实际程序、日志、tlog、objects、deps、
新旧源码与全部历史证据均不改。

## 真实首因

原 `upl_tpi_cryer_cpu_DebugCPU_r1` 的 environment 与 MSBuild 真实
Popen wait/Win32 handle 出口均为 0；全 86 obj、86 sourceDependencies
和 EXE 已产生。r1 wrapper 随后失败于
`Actual CL source or dependency argument malformed`，仍保持 failed。

真实 MSVC `CL.command.1.tlog` 的 `^` header 保存完整绝对 source，
但命令正文末尾 source 路径含 `Hydromechanic coupling` 的空格却不带
引号。直接对整行用 CommandLineToArgvW，末尾 source 被误拆为两个
token；它不是实际编译失败或缺少 sourceDependencies。

本 r2 仅先以每个真实 `^` source header 核完整尾部拼写（大小写、slash
可规范化），要求 token 前的空白边界，再精确剥离这个尾部。随后才对剩余
flags 调用 Windows parser。支持真正带引号或未带引号的 source，拒绝
多源 header/尾部不匹配；不猜测“最后两个词”或丢掉不认识的 flags。

## 独立复核范围

新 root review-only admission 的 `stage` 为
`upl_tpi_cryer_cpu_build_review_r2.review_admission`，`passed=true`、
`offline_only=true`、`configuration=DebugCPU`、
`adopt_completed_failed_postcheck=true`。inputs 绑定所消费实际 stat。

必须原样检查旧 root build admission 的所有冻结 inputs，另绑定新两作者
文件、旧失败收据、实际两工具 call/log、完整新86 obj/deps、tlog、
编译 Includes、EXE、私有库副本和实际 binlog/targets/environment batch。
不将旧“passed=false”改写，不发明旧 CL/link 单独句柄或退出值。

r2 保留原有全部构建门：真实 owner/child/exe/argv/parent/native创建时刻、
两个工具双出口；权威恢复项目有效86 TU和实际 evaluated list/object
集合；每 TU dependency.Source；全部 compiler Includes 排除公共或其他
仓库源；原数值 flags 只允许 source/Fo/Fd 路径与新增 sourceDependencies
差异；原5项目库私有副本＋18系统/工具链库的真实 link.read 闭包。
C04/GPU/C02旧对象均不复用，不因 parser 修复放宽数值编译参数。

工具仍是原 14.36.32532，目标 SDK8.1。`WINDOWSSDKVERSION` 环境字段
本身可能同时显示 installed Windows10 版本，不以它覆盖原实际库选择；
原 vcvars 8.1 `WINDOWSSDKDIR`、明确 MSBuild target8.1、原18实际系统库
与全部原 CL flags 共同确定本轮编译环境。

## 仅新目录补运行时

原 wrapper 在 runtime copy 前报错，所以这次只在新目录
`tests/outputs/upl_tpi_cryer_cpu_DebugCPU_r1_review_r2/runtime/`
复制原4 runtime 与真实 DebugOpenMP `vcomp140d.dll`，逐字节核副本。
根线程另明确允许把已完成 exe 复制到同一新目录，逐字节核副本；这不是
重编或 relink。原 exe、PDB 和旧 build 目录中的任何文件均不修改。

新 receipt：
`logs/upl_tpi_cryer_cpu_DebugCPU_r1.build_review_r2.json`，
`stage=upl_tpi_cryer_cpu_build_review_r2`。成功时
`passed=true,adopted_completed_build=true,original_build_passed=false`，
`source_program` 绑定实际旧 exe，`program` 指向同目录新副本，
`program_copy_byte_equal=true,program_relinked=false`；另外保留新 runtime
的 source/destination、原 failed build、两 actual tool receipts 和完整
离线复核证据。

后续 runner 必须显式采纳新 review，不能要求旧 r1 变成 passed。
后续 runner 直接使用新绝对 program 路径，确保程序按 argv0 定位到同目录
`DsphConfig.xml` 和 runtime。仅换 cwd 不能改变程序配置查找位置；此次
已经得到根线程明确允许的可逆 program copy，不能冒称新 link 或重算。

新目录或新 receipt 已存在即拒绝，不覆盖、不自动换标签。任何失败保留
新 runtime partial 和第一原因，不重跑已完成构建；成功也只允许下一次
独立 root 准入的极短程序资格，不代表 native 或物理验收。
