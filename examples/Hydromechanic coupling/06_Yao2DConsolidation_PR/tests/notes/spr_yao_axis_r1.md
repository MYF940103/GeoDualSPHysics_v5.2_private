# Yao轴对齐NoPen + SPR短窗

2026-10-24。在NoPen关闭的1 s CPU/GPU/独立GPU半步通过后，只打开已有NoPenetration=1，验证静止三面FreeSlip情形；不是修改NoPen公式。dp=.1、20301土粒子、原严格节点条带/材料/阻尼/排水、SPR开启、HG关闭不变。斜NoPen仍拒绝，不推广到运动/曲面/塑性/大转动。

## 新鲜顺序及先验门

`spr_yao_axis01_r1`：CPU8粗20us先通过全101帧单条检查，再GPU粗20us及全101帧跨后端比较，最后GPU半10us及独立全101帧半步。结束.1 s、1-ms原生保存，三条均新鲜启动。原5 Pa孔压RMS/.005 mm最大材料位移、同dt后端合力差<.002 N/m不变。每条原生ID/实际时刻、无排除/塑性、正密度、无穿墙、原严格受载集合和离散力、排水、实际机械及孔压限制须通过；不套用非均匀2D不适用的1D100 Pa应力门。

对照为保留1 s的NoPen关闭同dt前101帧；开关差只报告，不冒充半步差或理论误差。原59/61节点加载求积偏差保留，不能静默改band。0.1 s只是启动相容性证据，不自动准入1 s/长程。

## 文件和改动

- `scripts/spr_yao_axis_step.cpp`：CPU/GPU共用测试伴随，调用生产ComputeStep，整数步保存；只准入原NoPen及SPR开启、HG关闭的Yao路径，不复制积分器。
- `scripts/spr_yao_axis_build.ps1`：复用已核验权威VS对象/链接参数，生成新程序；不覆盖旧程序/构建清单。CPU旧清单枚举了两个并未包含的GPU头文件，现显式核对到后续GPU构建并记录旧/新哈希；其余原输入/对象均保持原哈希。第一次预检在创建输出前因此拒绝，未运行solver；修正只涉及构建清单选取，不降低任何物理门。
- `scripts/spr_yao_axis_run.py`、`spr_yao_axis_check.py`：浅层XML/BAT准备、单条/配对门、冻结run清单和图表；不改正式输入及生产源码。
- 配置在configs，原生结果在outputs，图及CSV在figures，日志和哈希在logs。本文件由序列绑定，运行期间不改；结果另写review记录。

默认CPU Debug构建通过，Release测试伴随单独编译并绑定当前对象；本轮无CUDA核或GPU内存实现变化，不新增GPU Debug要求。正式case02三组结果、Yao根XML/BAT不改，不重启旧worker、不重开KEEP。不删旧原生输出。
