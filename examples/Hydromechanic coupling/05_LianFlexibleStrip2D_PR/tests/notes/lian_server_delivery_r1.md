# Lian服务器交付，2026-10-27

用户取消新的HG+SPR 3 s半步；100 s改在Windows/RTX A6000服务器执行。
本机不重启旧半步/旧100 s，不等待服务器计算才进入Cryer。

## 交付文件与具体修改

- 根 `CaseLianFlexibleStrip2D_PR_release_Def.xml`：沿用已完成3 s的HG=.1、SPR=1、应力率梯度修正=1；右墙单独mkbound2，三个显式向内平面法向；左/右FreeSlip，底NoSlip。100 s、10us、0.05 s保存及其余材料、加载、排水保持既定设置。
- 根 `xCaseLianFlexibleStrip2D_PR_release_win64_GPU.bat`：程序改为相对`support/bin`；新`...release_HGSPR_out`防止覆盖旧正式结果；仅GenCase/求解，不强制VTK/Python；旧输出存在时退出1。
- `support/bin`：与3 s测试同一GPU Release、GenCase、两项Chrono依赖、OpenMP、配置和三项有微软签名的应用本地CRT。程序SHA256为`260c3d4c845db380f93257f96fba77034b1c6e2047d6780702b2483b974c933c`。
- `support/pack_lian_server.ps1`：白名单打包和逐项SHA核验；不含原始输出/tests/Debug，不运行求解器。包已存在时拒绝覆盖。
- `support/server_manifest.json`：16项实际输入/程序的来源、大小、SHA；源码节点指生产代码未变化的`e28650c3c26b53ee20c91bbfa7305909c47f32ac`，本轮新正式输入由其自身SHA定义，不冒充已在该旧节点中。
- `support/README_server.md`、`support/paper_observables.json`：服务器运行/回拷和Fig10/11/12观测量定义。回拷后按固定初始ID/权重分析A/B，100 s输出x0=1.25m整条竖向材料线的有符号水平位移；生成PNG和对应CSV。
- 根README及case/tests的`.gitattributes`：区分新入口与历史；保留所绑定交付输入字节。
- `tests/logs/lian_hg3_half_r1.user_stop.json`：用户停止记录。原status原样保留且SHA不变；约0.15 s部分结果不算3 s半步通过。
- `tests/scripts/lian_server_check_r1.py`及`tests/logs/lian_server_check_r1*`：新包实际启动/禁止覆盖验收；首次仅新脚本编码名拼写导致的预检查失败记录保留，求解器当时未启动。修正新脚本后只启动一次物理smoke，最终结果看`.r2.check.json`。
- `doc/xml_format/_FmtXML_ElastoplasticSoil.xml`：同步用户取消半步/服务器100 s待验范围；补充现有固定步长绕过自动渗流限值的行为说明，无方程/接口修改。
- 跨case排程更新为`validation/poromech_next_r3.json`：Lian服务器等待，主线Cryer→1D自重，Yao/滑坡/u-pl/TPI仍暂缓。

## 已核验结果

ZIP：根`Lian_HGSPR_Windows_RTXA6000.zip`，15168723字节。
SHA256：`9426799182eb71815573c4f481fcbaabed602c3fde831ad9639d593c9b69680c`。
ZIP逐项读回16文件+manifest均匹配。原BAT在带空格的移动目录、不同调用cwd运行；只有解压副本XML的TimeMax改为0.15，其余物理设置未改。

实际RTX3050完成0.15000000000000924 s，15000步，4个原生帧、每帧20301土粒子ID。
4帧实际时间/步数均与保留3 s结果共享，全部35列原始native数据0 ULP。
HG守卫通过：30000 force/rate calls，15001次计算+14999次端点复用，
max(dt/tau)=0.00255685，spin=0.000118914。三项CRT实际由包内加载。
再次调用原BAT退出1，输出文件所有SHA不变，无存活owned进程。
默认CPU Debug增量构建成功，见`tests/logs/lian_server_cpu_debug.build.log`；本轮没有生产源码改动。

限制：该启动检查未激活1 s后的排水，不是新的半步/100 s或A6000实机验收。
100 s物理/论文SPH-FEM比较等待服务器数据，0.05 s保存不覆盖论文0.01–0.05 s初段。
Git只备份配置、脚本、清单和证据；ZIP/程序/原生BI4另存，不等于云Git原始数据备份。

旧正式XML/BAT可从上一节点恢复；旧正式输出及测试原始结果均未覆盖或删除。
