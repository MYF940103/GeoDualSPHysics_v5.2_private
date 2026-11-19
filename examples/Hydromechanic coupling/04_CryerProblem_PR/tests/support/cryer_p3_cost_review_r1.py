"""Reproduce equal-physical-time Cryer timing and source-level operation counts."""
from pathlib import Path
import csv
import json

T=Path(__file__).resolve().parents[1]
FILES={'A128':T/'outputs/cryer_p3_gpu_default128_r1','B64':T/'outputs/cryer_p3_gpu_b64_r1'}
PHASES={'A128':2,'B64':5}
STEPS={'A128':128,'B64':64}
DTS={'A128':2.**-20,'B64':2.**-19}
MEASURED=['TSimul','TTotal','VA-Init','CF-PreForces','CF-Forces','NL-OutCheck','SU-DownData','SU-SavePart']

def count_disk_csv(path,material_ids):
    kept=0; total=0
    with path.open('rb') as stream:
        header=stream.readline();kept+=len(header)
        for entry in stream:
            total+=1
            if int(entry.split(b',',2)[1]) in material_ids:kept+=len(entry)
    return total,kept

def metrics():
    centers=set(json.loads((T/'logs/cryer_radial_layout_r1.check.json').read_text(encoding='utf8'))['native_identity']['center_ids'])
    data={}
    for key,folder in FILES.items():
        with (folder/'Run.csv').open(encoding='utf-8-sig',errors='replace') as f:
            rows=list(csv.DictReader(f,delimiter=';'))
        assert len(rows)==1 and int(rows[0]['Steps'])==STEPS[key] and int(rows[0]['PartFiles'])==2
        r=rows[0];d={name:float(r[name]) for name in MEASURED}
        d.update(steps=STEPS[key],simulated_s=STEPS[key]*DTS[key],full_force_phases=STEPS[key]*PHASES[key],
                 true_dt_phases=STEPS[key]*PHASES[key],three_round_rows=0,round_csv_bytes=0,center_only_same_data_bytes=0)
        d['dt_scale_device_reductions']=STEPS[key]*PHASES[key]*(1 if key=='A128' else 2)
        assert 'RTX 3050' in r['Hardware']
        for file in sorted(folder.glob('UplTpiP3GpuR1.round*.csv')):
            count,kept=count_disk_csv(file,centers)
            d['three_round_rows']+=count;d['round_csv_bytes']+=file.stat().st_size
            d['center_only_same_data_bytes']+=kept
        data[key]=d
    assert data['A128']['three_round_rows']==0 and data['B64']['three_round_rows']==37173*2*3
    assert data['A128']['simulated_s']==data['B64']['simulated_s']==2**-13
    return data

def main():
    data=metrics();a=data['A128'];b=data['B64']
    output=T/'figures/cryer_p3_cost_r1.csv'
    note=T/'notes/cryer_p3_cost_r1.md'
    if output.exists() or note.exists():raise FileExistsError('Timing report already exists')
    counts=['steps','simulated_s','full_force_phases','true_dt_phases','dt_scale_device_reductions','three_round_rows','round_csv_bytes','center_only_same_data_bytes']
    with output.open('x',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['metric','unit','default_A128','P3_B64','B_minus_A'])
        for name in [*MEASURED,*counts]:
            unit='s' if name in [*MEASURED,'simulated_s'] else 'bytes' if name.endswith('bytes') else 'count'
            w.writerow([name,unit,a[name],b[name],format(b[name]-a[name],'.12g')])
    eqtime=a['simulated_s']
    text=f'''# Cryer 同物理时间开销

当前 RTX 3050 的两次顺序运行均模拟到 {eqtime:.13g} s，初帧及末帧各保存一次。两次使用同一个 GPU Release 程序。A 每步两次力评估，P3 每步五次。P3 步数减半，但实际力评估从 256 次增加至 320 次。机器同时有一个既有 C08 GPU 进程，短窗 P3 还导出了全体三轮 CSV；这组耗时只作本机短程观察。

| Run.csv 实测秒 | A128 | B64 | B−A |
|---|---:|---:|---:|
'''
    for key in ['TTotal','TSimul','CF-Forces','SU-SavePart','NL-OutCheck']:
        text+=f'| {key} | {a[key]:.4f} | {b[key]:.4f} | {b[key]-a[key]:+.4f} |\n'
    text+=f'''
P3 总时间比 A 多 {b['TTotal']-a['TTotal']:.3f} s，循环时间比为 {b['TSimul']/a['TSimul']:.3f}。CF-Forces 包括力、孔压率和极值归约，无法拆出单个子核收益。将整个 P3 SU-SavePart 耗时视为可省项会给出偏宽的上界 {b['SU-SavePart']:.3f} s；即使把它全部扣除，B 总时间仍比 A 多 {b['TTotal']-b['SU-SavePart']-a['TTotal']:.3f} s。该计时项含必须保留的 BI4、初帧和末帧；初帧先于 TimerSim.Start，不能直接把这段时间作为循环中的 CSV 耗时。

按实际文件逐行保留同一批原始 18 个材料 ID 和三份表头，三轮 CSV 可从 {b['round_csv_bytes']:,} 字节减至 {b['center_only_same_data_bytes']:,} 字节。这里有 {b['three_round_rows']:,} 条实际压力记录，其中 {18*2*3} 条属于 18 点。当前较长任务已经使用这个缩减输出模式，全体材料仍执行运行时检验，输出额外全体极值。短窗耗时不能外推为服务器速度。

## 可验证的优化切口

1. **优先复用同一 endpoint 力评估后已有的几何场。** 每轮力计算调用 ComputeFreeSurfaceTracking，写完压力再调用 ApplyPorePressureBoundaries，后者重新求跟踪场再投影压力。C04 的该跟踪核只读几何、质量密度、J、编码和分区，不读新压力。先只复用每一轮自己的跟踪结果，仍在原时刻执行原来的 ApplyFreeSurfacePorePressure。B64 共有 3×64=192 次这样的第二次跟踪调用；节省的时间还没有单项计时。首次候选不跨轮复用，因下一轮开头的 CDBC 校正可能改写固定粒子的密度／速度／应力。
2. **当前 J 的两次步长遍历可考虑融合。** A128 的 256 次步长评估每次原有归约一次。B64 的 320 次评估各归约一次有限 Kw 波速／水力界，再归约一次相同 J 的骨架波速，共 640 次设备遍历。单 kernel 可维持每粒子的三套原公式和三组独立最大值，保留无效 ID 拒绝、真实速度／黏性、实际加速度与五相逐次记录。理论上可减少 320 次遍历，预计耗时收益尚无计时。局部候选只涵盖本 case 的常渗透率。
3. **不要将下一轮直接简化为使用旧加速度的压力遍历。** 当前压力进入总应力动量项，下一轮的 R 含压力梯度、速度散度和实际加速度散度，封闭自由表面还用到局部加速度法向分量。可以研究跳过严格证明为只写、且后续不读取的临时导数，或缓存仅依赖几何的 W、矩阵和邻域顺序；必须继续实际更新随 q 改变的动量力，并保持原逐邻居浮点加法顺序。不能通过合并相位或删除收敛、孔压、荷载、源时钟和时步检查计作提速。

**回归条件**。从已保存的同一初态进行无选择器 A 的原生 22 数组／元数据逐位核对。P3 用同一批真实保存时刻继续核对三轮 P、q、R、S、θ、J、五相界、signed dterror、原生字段和全体表面接收者；覆盖关闭阶段、tD 前状态及第一个开放步。对几何候选另比较 C、FSType、FSNormal、PosDiv 和真实加速度、黏性最大值；若已有文件没有保存该中间量，应采用有界同状态设备观测。性能比较需相同输出模式、相同存储和 GPU 负载，分开 kernel、复制、格式化及 BI4。当前不改运行程序。

**复现和源码**。使用 support/cryer_p3_cost_review_r1.py，可从两份原始 Run.csv 和三份实际 round CSV 重算表格。以下路径均相对于本 case 的 tests。

- outputs/cryer_p3_gpu_default128_r1/Run.csv 与 outputs/cryer_p3_gpu_b64_r1/Run.csv
- outputs/cryer_p3_gpu_r2_source/JSphGpuSingle.cpp，Interaction_Forces、逐轮事务与 SaveData 中的计时边界
- outputs/cryer_p3_gpu_r2_source/JSphGpu.cpp，ComputeFreeSurfaceTracking、ApplyPorePressureBoundaries、ComputeDynamicPorePressureRateGpu、GetDynamicStepScalesGpu、DtVariable
- outputs/cryer_p3_gpu_r2_source/JSphGpu_ker.cu，ComputeFreeSurfaceTrackingT、ComputePorosityWaveSpeed2、KerComputeDynamicPorePressureRate 及 CaptureRow 的实际 LP、Lx、梯度和加速度散度
- outputs/cryer_p3_gpu_r2_source/upl_tpi_cryer_gpu_r1.h 和 .cuh，源／轮次／提交和每次保存时的全体核对
'''
    with note.open('x',encoding='utf8') as f:f.write(text)
    print(output,note)

if __name__=='__main__':
    main()

