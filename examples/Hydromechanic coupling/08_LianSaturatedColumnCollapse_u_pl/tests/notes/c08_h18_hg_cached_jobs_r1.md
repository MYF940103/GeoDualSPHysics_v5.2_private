# C08 唯一材料返回缓存候选：两项短测试

本脚本只包含 `off1` 和 `debug2` 两个独立准入的任务，没有通知器或后续任务自动启动。它从已执行保留的 `c08_h18_hg_gpu_jobs_r1.py` 机械复制；差异记录在同名 author.diff。所有旧脚本、输出和失败记录保持原样。

- `off1`：Release，候选环境变量缺省，原预载之后仅一次更新，global step 2000001。必须随后以独立原生读取确认全部 22 数组、真实时钟、layout 与 signed-clock 保留前缀逐 byte 一致。私有 OFF 仍调用旧的已编译 GPU 积分核，不分配 HG/cache，不生成 HG 侧车。
- `debug2`：Debug，显式 `C08_HG_CACHED_H18=1`，同一预载之后两次更新，global step 2000002。由 compute-sanitizer 检查实际 GPU 程序，零错误和零泄漏；独立原生及缓存侧车审查随后进行。它是实施测试，不是塑性或物理验收。

旧认证的 Wendland schema2 同材料 ψ0 10 秒 PRE、AS .3/n2.55、AV .1、dp .04、H .072、5us、固定平面、keepfalse、CompletedOnly 和 17-key material profile 均保持不变。没有 GenCase、重新预载、half 或其他 ψ。两项保存时间由原始 PRE 的实际 binary64 时钟逐步 `+=dt`，不以整数乘积替代。

构建要求：实际 111 个旧对象加两个私有 host 和一个私有 CUDA，共 114；保留原 Simpleker、力学与 Darcy 对象。缓存 producer 计算一次材料返回，consumer 原表达式写回；该写回自洽检查不是对旧独立返回求值的 0 ULP 证明。保留旧 1 ULP 失败，不放宽材料或原生安全门。

准备和运行分别需要绑定本脚本、本文、已通过构建收据的 root admission；独立 native/侧车审查另行决定。先检查已有/活动程序与读取器，任何失败保留 partial，禁止覆盖、重复运行或重复解码。求解器完成封存先于派生检查；若仅分析失败，只修派生。不依据正常退出宣布物理通过。

执行形式为 `python -X utf8 -B support/c08_h18_hg_cached_jobs_r1.py prepare|run --profile off1|debug2 --execution-authorized`。本文件不授予执行权限，root 在完整审阅冻结构建、脚本和实际准入后分别执行。当前仅作者阶段，不运行求解器。
