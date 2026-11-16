# C02 GPU 2Tv：单主机TU Release构建作者稿

新增support/upl_tpi_gpu_full2tv_build_r1.py和本文，尚未执行。
只为passed窗口准入prepare编译1个JSphGpuSingle.cpp并链接；没有NVCC、help、solver、
reader、VTK、Git或自动后续。prepared h/cuh、kernel、数值/物理代码均保持原字节。

采用真实passed upl_tpi_gpu_Release_r3.build.json完整111对象及原顺序，其中110原对象
原位只读保留，包括相同JSphGpu_ker.cu.obj/PTX、JSphGpu.obj和JSphHourglassGpu.obj。
其余旧对象以及两个Functions*.h.obj完整名称不改，不清理/移动任何依赖。
新单host替换旧Single host；没有class/header token或ABI变化，ODR定义同源。
旧/r3 vc143.pdb均作为只读依赖保护，新CL PDB独立输出。

真实CL recipe来自upl_tpi_gpu_Release_r3.JSphGpuSingle.call.json：
仅source、/Fo、/Fd和/sourceDependencies路径重定向，原MSVC14.36 flags/MT/FP/defines/include不变。
sourceDependencies实际检查不能读live src/source或旧r2 source目录的header。
私有完整269新源保证quoted include首先读新同字节header/helper。

真实link recipe来自upl_tpi_gpu_Release_r3.link.call.json：
完整111顺序中只替Single obj；/OUT/PDB/IMPLIB/LTCGOUT/ILK各准确一次改到新目录。
保留原libs/全部其它flags；实际库搜索从真实vcvars LIB和原显式/LIBPATH核对，
不覆盖CRT目录。复用已审gpu_build_r1.environment/validate_library_search/invoke函数，
不改helper源、不monkeypatch函数，不调用旧4TU编译/107retain link入口。

新输出：tests/outputs/upl_tpi_gpu_full2tv_Release_r1/out，
新无空格IntDir为Temp/upl_tpi_gpu_full2tv_build_r1/Release/int。
CL/link调用记录、stdout/stderr log和真实Popen/Win32出口均由既有invoke保留。
新EXE仅一次SHA身份，旧源/obj/BI4无hash扫描。所有runtime从r3实际destination复制，
旧程序和全部source/runtime/object stat在结束重核；不把SHA附加字段作字典整体相等。

root独立admission为stage=upl_tpi_gpu_full2tv_build_r1.build_admission、passed/build_only=true、
configuration=Release；inputs含本script/note、共同CPU build_r2和GPU build_r1 helper、
VCVARS/cmd/实际CL/link工具、window prepare及base source/build/diff，全部新269及旧269源stat，
原r3 program/111objs/两compiler PDB、真实CL/link calls、库、runtime destinations。
命令需--execution-authorized --admission，不自动寻找/重试旧失败路径。

新receipt为logs/upl_tpi_gpu_full2tv_Release_r1.build.json。
passed只表示真实1CL+1link/111闭包及输入来源正确，不表示2Tv求解/收敛/理论或物理验收。
构建时所有新路径必须不存在；失败保留partial/真实首因，不重跑原任务或覆盖旧收据。
后续root另审唯一freshB full runner/native；旧A full复用，C full不自动准入。
