# AS.25 原生读器 r2：严格CSV片段修复（作者稿）

只新增同stem CPP/build/run与本说明；保留 r1 的程序、源码、失败call/log/check及全部物理输出。本说明生成时尚未构建/执行 r2，不能将计划当实际解码成功。

物理窗口已真实 solver0/30帧完成。r1唯一reader进程真实Popen/Win32=1，错误为 `part=4294967295 ID=4294967295 Unrecognized embedded Run.csv separator; raw file is not changed`，native_r1目录未建立。实际r1 core的 `RunSamples` 调用在PRE load、mkdir与数组读取之前；故零数组/零PRE是冻结源码控制流证明，不是运行计数器。adapter此前可能完成30次lazy metadata头读取，不能称零header读，亦不重写原Run.csv或将失败记为成功。

本r2的生成core保留原4个明确替换及逆向相等证明：`left="AS_Bui2008(0.2"`→`.25`、rightpart→`3)`、完整marker→`AS_Bui2008(0.25;3)`、stage→新tag。后三项与r1相同，新增修复仅left片段。所有22数组/6805 IDs/30帧、AS.25f/n3、CompletedOnly、keep5/fixed-plane、ShepardOFF、PRE资格、P0/κ/ledger/FS/clock/signed及原数值预算保持。仍为封口6utility对象加本main，不链接solver对象。

新program `tests/outputs/upl_c08_as025_native_r2_build/C08AS025Native_win64.exe`，build receipt `tests/logs/upl_c08_as025_native_r2.build.json`；11参数CLI不变：`--read psi0 GPU DATA PRE 4120000 30 1 PLAN FRESHOUT`。新normal completion stage `upl_c08_as025_native_r2`，metadata同stage加`.metadata`，其余schema不变。

wrapper沿已核实际owner接口，先要求原r1 failed receipt/call/log及native_r1不存在，再独立复核正常physical run、source/input/program/PRE/plan/owned出口及无active/existing读取；只在根全文审并另行授权后一次调用。新输出 `outputs/upl_c08_as025_window_GPU_r1/native_r2`，收据 `logs/upl_c08_as025_window_GPU_r1.native_r2.json`。成功意味着本次首次实际数组读取全部原门通过，不是重复solver或放宽物理准入；失败保存新partial，不重复/自动后续。

根可独立审后分别决定：`python -B tests/support/upl_c08_as025_native_r2_build.py --execution-authorized`，然后 `python -B tests/support/upl_c08_as025_native_r2_run.py --execution-authorized`。本作者任务未执行这两个入口，不调用solver/VTK/queue，也不修改任何r1文件。
