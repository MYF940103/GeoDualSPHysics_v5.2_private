# C02 GPU B full2Tv：独立原生build/read/review作者稿

新增support/upl_tpi_gpu_full2tv_native_r1.cpp、.py及本note，未构建、解码或分析。
三个动作独立根准入，无solver、half、reference、VTK、Git或自动下一动作。
已进行的C04 Release peerreview另行完成，本稿不操作任何活动或暂停计算。

## 原C++读取器与唯一full profile

从已真实构建/读取通过的support/upl_tpi_gpu_native_r1.cpp复制。
原中性upl_cpu_public_native_r1.cpp仍仅为BI4/type loader，不是CPU求解器。
只改profile/stage/backend为full2tv、1682帧/11661219更新、scalar end72.88428689946836，
preopen event1600/part117、firstpost1601/part118、1564post/15640真receiver检查。
原LoadNative/Read/Initial全部22typed数组、原15、6double、floatPosDiv、1040IDs/40fixed/
1000soil、真实Step/dt/scalar clock、signeddterror<=1e-14、ledger/排水/几何/弹性门原样。
不接受debug/startup或其他full标签，不n*dt替代native时钟；乘法终点仅描述字段。
C++沿原volatile scalar+=dt逐步核时钟，实际保存target crossing及forcedfinal不改。

五个二进制导出原布局保持：original15.bin stride166408、physical.bin208008、
common_j_theta.bin16648、soil_n.bin8008（12B各自声明头），clock.bin stride28/8B头。
头部必须保本次1682，不能改成短窗344；common26列21仍ExcessPorePress，非PosDiv。
fixed marker和真正PosDiv/V/rho/k由原22数据另核，不用common26伪造全部raw数组。

## 分离的动作与路径

Python action为build/read/review；根admission stage分别
upl_tpi_gpu_full2tv_native_r1.build_admission/read_admission/review_admission，
passed/action_only=true及完整inputs stat。每个动作单独运行，互不自动接续。

build复用原已通过native r1/原bigstep reader的真实CL/link/runtime recipe，
新唯一outputs/upl_tpi_gpu_full2tv_native_r1_build及logs同tag.build.json；
旧CPP/loader/程序和结果不动，不从公共live源码读header，不扫旧obj/BI4 SHA。
只允许原neutral loader的真实archive header/library/runtime依赖，不改solver任何源。

read只准单一真实job upl_tpi_gpu_Release_B_full2tv_r1：原freshB source/build/program/
input/output/run/start/call、actualselector、真Win32/Popen出口和normalRun必须一致。
物理program须实际passed的one-host full-window build（111/retain110），原helper/CU不变。
新reader只调用一次`--read GPU DATA PLAN full2tv NEWOUT`，先检查已有/活动reader，
任何既有output/check/call/log使重复调用拒绝，不覆盖partial或重跑物理solver。

新导出为outputs/upl_tpi_gpu_Release_B_full2tv_r1_native_full_r1，
read receipt为logs/<fulltag>.native_full_r1.json。
completion stage为upl_tpi_gpu_full2tv_native_r1/backendGPU_full2Tv_private。
不存在把CLI GPU字样本身当后端/物理证据的说法，真正所有权由Python单独核。

## full review和保留B短窗

review消费已passed独立native及全部新导出，输出
logs/<fulltag>.native_review_full_r1.json，不调用读取器。
保留已通过r5的压力float输入/输出RN+signedFTZ精确重放，原Double预测/J两精确FMA路径、
Dirichlet+0/IDhistory/回写/counters/真实原PTX proof不改，不加ULP或物理容差。
HG原调用/cache/stiffness/spin门保留。Python仅保所需n/n-1稀疏clock，但仍单次scalar+=dt
遍历，不建11M Pythonfloat列表、不改变实际clock算法。

B startup保留344帧。通过真实timebits+nativeStep join，只能343个共同记录：
0..342，末common completed23691/t=.14807213902475963。
短窗part343为forced24000/.1500034332275618，不共享；fullpart343是24004/.15002843379976635。
五binary分别保持344/1682原头，只比共同完整records（包括所有clock/signed字节），
不插值、不删initial、不把partial字段证据宣称全部22 rawbit。
原native guards证明各自22数组；若需要22rawprefix，须另独立raw22compare。

旧A full是不同finiteKw算子控制，后续科学比较需相同实际时刻/材料ID，并披露M0差异；
本review不加5Pa跨模型/half gate，不以oldA代替真实同B prefix，不启动新A/C。
完整孔压/固定材料沉降/Jnρ/应力/100层模态/晚期floor及理论精度仍待后续图CSV科学审查。
reader/review通过不等于物理、理论、完整restart或正式发行验收。

## 复现输入

必须实际核所有作者文件、公用b helper、中性loader/编译与链接base receipts及headers/lib/runtime，
新reader build/program、完整run/start/call/程序/fullprepare/seed冻结来源/plan/Run.out/console及1682BI4。
review另需全部native leaves、侧车policy/CSV/summary、实际原PTX tool/call/obj/compile证据、
保留B短窗native_review_r5/completion及五binary。只用必要stat，不重复hash扫描。
根完整审后依动作单独传--execution-authorized --admission ROOT_JSON；本作者没有执行任何动作。

未绑定作者稿的reader身份复核补充：read和review都调用与已通过r5同口径pin_reader，
不只检查build.passed；还核build精确stage、无solver/reader调用、旧reader/loader未改、
依赖stat未变、built.program的实际stat与常量PROGRAM路径一致，及全部runtime destination stat。
这只补来源身份绑定，不改任何原生数组、数值条件或导出布局。作者没有执行。
