"""Publish the reviewed C02 high-k short-window accuracy, timing and CPU/GPU results."""
import csv
import json
import math
from pathlib import Path
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

from c02_tpi_cost_r1 import PLAN, PREFIX, TESTS, directory, need, planned_clock
from c02_tpi_cost_review_r1 import compare, target_budgets

LANES=tuple(PLAN['lanes'])
BACKENDS=('cpu','gpu')
LOG=TESTS/'logs'
LABELS={'kw25':'显式 2.5 µs','kw40':'显式 4 µs','tpi25':'TPI 2.5 µs','tpi40':'TPI 4 µs','tpi100':'TPI 10 µs'}
COLORS={'kw25':'#194690','kw40':'#779dc3','tpi25':'#00866b','tpi40':'#dc7c00','tpi100':'#a93250'}
MARKERS=('o','s','^','D','v')
FIELDS=(('pressure_RMS_Pa','层孔压 RMS 误差 (Pa)'),('top_error_mm','顶部沉降误差 (mm)'),('bottom_error_mm','底部沉降误差 (mm)'))


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def single(lane,backend):
    tag=f'{PREFIX}_{lane}_{backend}'
    sources=[p for p in (LOG/(tag+'.json'),LOG/(tag+'_vs_kw25.json'),LOG/(tag+'_vs_kw40.json')) if p.is_file()]
    need(sources,'Missing single-backend native review for '+tag)
    stripped=[]
    for path in sources:
        item=read(path)
        item.pop('comparison',None)
        stripped.append(item)
    result=stripped[0]
    need(all(r==result for r in stripped),'Conflicting source reviews for '+tag)
    ex=read(directory(lane,backend)/'exit.json')
    need(result['lane']==ex['lane']==lane and result['backend']==ex['backend']==backend and result['model']==PLAN['lanes'][lane]['model']
         and ex['exit']==0 and ex['program_unchanged'] and result['host']==ex['host']
         and result['program_identity']=={k:ex[k] for k in ('program','size','mtime_ns')}
         and result['wall_s']==ex['wall_seconds'],'Run/review binding '+tag)
    clocks=planned_clock(lane)
    need(len(result['rows'])==len(clocks)==13,'Expected 13 native rows '+tag)
    for i,(row,(step,t,target)) in enumerate(zip(result['rows'],clocks)):
        need(row['part']==i and row['completed']==step and row['t_s']==t and row['target_time_s']==target,'Actual scalar clock '+tag)
        for key,_ in FIELDS:
            need((math.isfinite(row[key]) if i>=3 else row[key] is None),'Unexpected theory coverage '+key)
    return result,','.join(p.name for p in sources)


def inputs():
    runs={};sources={};cross={}
    for lane in LANES:
        for b in BACKENDS:
            runs[b,lane],sources[b,lane]=single(lane,b)
        path=LOG/(f'{PREFIX}_{lane}_cpu_gpu.json')
        item=read(path);rows=item['rows']
        need(item['lane']==lane and item['configuration']==PLAN['lanes'][lane] and item['all_pair_clocks_exact']
             and item['native_pairs']==len(rows)==13 and item['fields_per_native_frame']==22
             and item['soil_count']==1000 and item['fixed_count']==40,'Incomplete same-backend lane pairing '+lane)
        for b in BACKENDS:
            run=runs[b,lane]
            need(item['host']==run['host'] and item['program_identities'][b]==run['program_identity']
                 and item['hardware'][b]==run['hardware'] and item['per_backend_saved_stress_safety'][b]==run['early_100Pa_stress_pass']
                 and all((r['part'],r['completed_step'],r['t_s'])==(s['part'],s['completed'],s['t_s']) for r,s in zip(rows,run['rows'])),
                 'Cross receipt differs from '+b+' '+lane)
        p=max(r['material_pressure_RMS_Pa'] for r in rows);u=max(r['material_max_displacement_diff_mm'] for r in rows)
        need(item['backend_pressure_RMS_limit_Pa']==5. and item['backend_displacement_limit_mm']==.005
             and p==item['max_material_pressure_RMS_Pa']['value'] and u==item['max_material_displacement_diff_mm']['value']
             and item['cross_backend_field_gate_pass']==(p<=5. and u<=.005),'Cross-backend budget '+lane)
        cross[lane]=item
    return runs,sources,cross


def summarize(runs,sources,cross):
    history=[];cost=[]
    for b in BACKENDS:
        a=runs[b,'kw25']
        valid={l:target_budgets(a,runs[b,l])['passed'] for l in ('kw25','kw40')}
        eligible=[l for l in valid if valid[l]]
        ref=min(eligible,key=lambda l:runs[b,l]['wall_s']) if eligible else None
        for l in LANES:
            r=runs[b,l];cfg=PLAN['lanes'][l];c=cross[l]
            scheme='finite_Kw' if cfg['model']==1 else 'M0'
            for x in r['rows']:
                nominal=round((x['part']-2)*PLAN['save_delta_Tv'],12) if x['part']>=3 else None
                history.append(dict(backend=b,lane=l,reference_theory=scheme,dt_us=1e6*cfg['dt_s'],hydraulic_R=cfg.get('R'),
                                    target_Tv=nominal,predeclared_accuracy_target=nominal in (.005,.05),**x))
            if ref is None:
                qualified=False
            elif ref==l:
                qualified=valid[ref]
            else:
                qualified=compare(runs[b,ref],r,a)['predeclared_target_noninferiority_pass']
            if not ref:
                reason='无合格的显式参考'
            elif not qualified:
                reason='未通过同端预设精度门'
            elif not (c['cross_backend_field_gate_pass'] and cross[ref]['cross_backend_field_gate_pass']):
                reason='跨端复现门未通过'
            elif l==ref:
                reason='显式计时基准'
            elif r['wall_s']>=runs[b,ref]['wall_s']:
                reason='精度合格，壁钟未加快'
            else:
                reason='短窗精度合格，壁钟较短'
            refwall=runs[b,ref]['wall_s'] if ref else None
            refloop=runs[b,ref]['loop_s'] if ref else None
            same_dt={'tpi25':'kw25','tpi40':'kw40'}.get(l)
            eligible_ratio=qualified and c['cross_backend_field_gate_pass'] and cross[ref]['cross_backend_field_gate_pass']
            cost.append(dict(backend=b,lane=l,reference_theory=scheme,dt_us=cfg['dt_s']*1e6,hydraulic_R=cfg.get('R'),host=r['host'],
                             hardware=r['hardware'],driver=r['cuda_driver_runtime'],steps=r['steps'],frames=len(r['rows']),
                             wall_s=r['wall_s'],loop_s=r['loop_s'],run_total_s=r['total_s'],save_timer_s=r['save_timer_s'],native_bytes=r['io_bytes'],
                             explicit_reference=ref,reference_wall_s=refwall,reference_loop_s=refloop,
                             measured_wall_ratio=(refwall/r['wall_s'] if ref else None),measured_loop_ratio=(refloop/r['loop_s'] if ref else None),
                             same_dt_reference=same_dt,same_dt_observed_loop_ratio=(runs[b,same_dt]['loop_s']/r['loop_s'] if same_dt else None),
                             target_noninferiority_pass=qualified,saved_stress_pass=r['early_100Pa_stress_pass'],max_layer_stress_error_Pa=r['post01_max_layer_Pa'],
                             max_topgap_Pa=r['post01_max_topgap_Pa'],cross_field_pass=c['cross_backend_field_gate_pass'],
                             cross_pressure_RMS_max_Pa=c['max_material_pressure_RMS_Pa']['value'],
                             cross_displacement_max_mm=c['max_material_displacement_diff_mm']['value'],
                             qualified_wall_ratio=(refwall/r['wall_s'] if eligible_ratio else None),interpretation=reason,
                             single_receipts=sources[b,l],cross_receipt=f'{PREFIX}_{l}_cpu_gpu.json'))
    return history,cost


def figures(history,cost):
    available={f.name for f in font_manager.fontManager.ttflist}
    names=[f for f in ('Microsoft YaHei','Noto Sans CJK SC','SimHei','Yu Gothic') if f in available]
    need(names,'Chinese publication font unavailable')
    plt.rcParams.update({'font.family':names+['DejaVu Sans'],'axes.unicode_minus':False,'font.size':9})
    fig,axes=plt.subplots(2,3,figsize=(13.0,7.1),sharex=True,layout='constrained')
    for i,b in enumerate(BACKENDS):
        for j,(key,title) in enumerate(FIELDS):
            ax=axes[i,j]
            for k,l in enumerate(LANES):
                sel=[r for r in history if r['lane']==l and r['backend']==b and r['target_Tv'] is not None]
                ax.plot([r['actual_Tv'] for r in sel],[r[key] for r in sel],color=COLORS[l],marker=MARKERS[k],markersize=4.7,
                        linewidth=1.25,markerfacecolor='none',label=LABELS[l],linestyle='--' if l.startswith('kw') else '-')
            ax.set_title(f'{b.upper()}　{title}');ax.grid(alpha=.22)
            ax.set_xticks([.005,.015,.025,.035,.05]);ax.tick_params(labelsize=8)
            if i:ax.set_xlabel('实际排水后 Tv')
            if j:ax.axhline(0,color='#59636f',linewidth=.7)
    fig.suptitle('C02 高渗透率固结　各自解析参考下的短窗误差',fontsize=15)
    axes[0,0].legend(fontsize=8)
    timing,axs=plt.subplots(1,2,figsize=(11.8,4.5),layout='constrained')
    for ax,b in zip(axs,BACKENDS):
        sel=[r for r in cost if r['backend']==b]
        for i,r in enumerate(sel):
            ax.bar(i-.18,r['wall_s'],width=.34,color=COLORS[r['lane']],label='进程壁钟' if i==0 else None)
            ax.bar(i+.18,r['loop_s'],width=.34,facecolor='white',edgecolor=COLORS[r['lane']],hatch='//',label='求解主循环' if i==0 else None)
        ax.set_xticks(range(len(sel)),[LABELS[r['lane']].replace(' ','\n',1) for r in sel])
        ax.set_title(b.upper());ax.set_ylabel('实际用时 (s)');ax.grid(axis='y',alpha=.22);ax.set_axisbelow(True);ax.legend()
    timing.suptitle('相同输出计划下的实际计算用时',fontsize=14)
    return fig,timing


def write_csv(path,records):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)


def summary_text(cost):
    lines=['# C02 高渗透率短窗精度与成本','',
           'k=10⁻³ m/s，排水从 0.01 s 开始。每组 13 帧，排水后的输出间隔 ΔTv=.005，终点 Tv≈.05。显式 u-pl 对应有限 Kw 解析解，三轮 TPI 对应 M0 解析解。孔压取 100 个材料层的 RMS，顶部和底部取各自初始材料层的沉降误差。','',
           '同端精度按 Tv=.005、.05 的原误差带和 t≥.1 s 各保存帧的总应力限值评定。跨端另按同一材料、同一步号的孔压 RMS ≤5 Pa 与最大位移差 ≤.005 mm 评定。每个后端独立选择达到精度要求且实测壁钟最短的显式组作计时参考。','',
           '| 后端 | 配置 | 参考 | 主循环 (s) | 壁钟 (s) | 合格壁钟比¹ | 判定 |','|---|---|---|---:|---:|---:|---|']
    for r in cost:
        ratio='—' if r['qualified_wall_ratio'] is None else f"{r['qualified_wall_ratio']:.3f}"
        lines.append(f"| {r['backend'].upper()} | {LABELS[r['lane']]} | {LABELS.get(r['explicit_reference'],'—')} | {r['loop_s']:.3f} | {r['wall_s']:.3f} | {ratio} | {r['interpretation']} |")
    lines.extend(['','¹ 壁钟比为参考耗时除以本组耗时；大于 1 表示本次测量较快。每组一次计时，包含实际写盘开销。跨端门和同端精度门都通过才列合格比。','',
                  '各时刻及三个误差量见 history.csv，各端硬件、程序收据、跨端最大差、同计算步长对照、主循环和输出开销见 timing.csv。'])
    return '\n'.join(lines)+'\n'


def main():
    dest=TESTS/'figures'/PREFIX
    need(not dest.exists(),'Existing published summary is preserved')
    runs,sources,cross=inputs()
    history,cost=summarize(runs,sources,cross)
    with tempfile.TemporaryDirectory(prefix=PREFIX+'_',dir=dest.parent) as tmp:
        bundle=Path(tmp)/PREFIX;bundle.mkdir()
        write_csv(bundle/'history.csv',history);write_csv(bundle/'timing.csv',cost)
        a,b=figures(history,cost)
        try:
            a.savefig(bundle/'accuracy.png',dpi=175);b.savefig(bundle/'timing.png',dpi=175)
        finally:
            plt.close(a);plt.close(b)
        (bundle/'summary.md').write_text(summary_text(cost),encoding='utf8')
        bundle.rename(dest)
    print(dest)


if __name__=='__main__':main()
