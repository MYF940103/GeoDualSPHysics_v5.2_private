# AS ε=.2 与文献 ε=.5 的固定态比较

Bui2008在Cubic、h=1.2dp的黏聚弹塑性试验中建议ε=.5、n=2.55；当前C08使用相同核比例，但u-pl/自由面/软化与变J权重使这不是可直接替换的通用默认。先进行一个小规模离线比较，不调指数、不扫描许多参数、不改原运行。

复用已通过的8个压力子矩阵及AS独立增量，只将AS项乘实际float参数比float32(.5)/float32(.2)，raw/LP/几何/σ/p/J/n/k/FS/材料变量全部保持。AS谱投影对固定σ和p不随ε改变，故连续代理按ε线性；这不是GPU浮点逐位重放或真实非线性轨迹预测。已有原状态主应力exact-zero计数原样写出，不增阈值或新物理门。

图只展示两个FS0主子块；CSV另保留含FS的全patch结果。块外扰动固定，未模拟FS投影和速度/σ/几何响应，不是完整耦合谱。若局部谱变好，只支持受控参数试验；若仍有增长，则不能把增加AS当作已解决问题。原AS0/AS.2及全部失败数据不改。

单次命令：`python -X utf8 -B tests/support/upl_c08_as_epsilon_frozen_r1.py --execution-authorized`。新图CSV/check位于tests/figures同名前缀，无solver/build/decoder或正式输入变更。
