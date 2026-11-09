# H1.8 compare r2：显式区分bedroles与旧Keep5（作者稿，未执行）

仅新建 `support/c08_h18_compare_r2.py` 和本说明。r1脚本、已完成63帧分析/PNG/check、source与中央profiles完全不动。r2入口为 `D:/anaconda3/python.exe -B tests/support/c08_h18_compare_r2.py --manifest MANIFEST.json --execution-authorized`；manifest及load_bundle/read22/reference_from/analyze_case/plot_results接口沿r1，仍须Root全文审后独立执行或由新正式post import。基础参数格式、单位、限制见保留的 `notes/c08_h18_compare_r1.md`。

与当前r1恰9个锚定修改：①stage分类显式接受旧/new source与receiver；②completion按new stage核geometry_profile=bedroles、target1805/255、keepfalse，无kept字段；③receiver metadata stage选旧/new；④分别核新连续fixed0..1804/退休1805..2059与旧Keep5 metadata，不能互相冒名；⑤new receiver ExpectedIDs为0..1804加2060..7059，old仍原非连续五ID；⑥bundle附geometry_profile描述；⑦自身note绑定改r2；⑧结果stage改c08_h18_compare_r2；⑨manifest receiver/source_reference必须同几何profile。

已核新build实际生成的三个文件，new source stage为 `c08_h18_bedroles_native_r1.source`，receiver为 `c08_h18_bedroles_native_r1.receiver`，metadata为 `c08_h18_bedroles_native_r1.metadata`。source仍7060全ID/22数组；new receiver仍6805/5000soil/1805fixed，仅ID身份变为连续固定段。new source completion必须targetBegin1805/count255/keepfalse；new receiver还须actualRetired255连续、retainedFixedBegin0/count1805及相应metadata，无虚构KeepBedOverlap/keptIDs。若case额外给geometry_profile，必须与stage一致；省略则从明确stage确定，兼容旧manifest。

静态证明：9项替换逐项逆还原后与当前r1全文完全一致；SCHEMA原文完全一致；除load_bundle/main外，need/path/stat/read/table/bind/write_csv/f32/read22/reference_from/analyze_case/history_plot/plot_results十三个函数的完整原文均一致。全部pressure/P0参考/J/NN/真实clock/signed/5e−13预算、数值计算与图逻辑未改。源partial仍实际count且不宣称平衡；old/new source可描述性对照，receiver不混PRE几何。

输出依旧由manifest独占新tag决定，不覆写旧tag；新check stage为r2，不能重写旧receipt冒名。没有执行分析、build、reader、solver、VTK、SHA或queue；当前源正在运行，其依赖均未触及。
