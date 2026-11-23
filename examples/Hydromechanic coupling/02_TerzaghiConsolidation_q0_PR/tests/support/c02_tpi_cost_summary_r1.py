"""Publish the reviewed C02 high-k short-window accuracy, timing and CPU/GPU results."""
import csv
import argparse
import json
import math
import re
from pathlib import Path
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

from c02_tpi_cost_r1 import OPTIONAL, PLAN, PREFIX, REFERENCES, TESTS, directory, need, planned_clock
from c02_tpi_cost_ref_review_r1 import against_reference
from c02_tpi_cost_review_r1 import read_native, theory

LANES=('kw10','kw125','kw25','kw40','tpi25','tpi40','tpi625','tpi100')
BACKENDS=('cpu','gpu')
LOG=TESTS/'logs'
LABELS={'kw10':'显式 1 µs','kw125':'显式 1.25 µs','kw25':'显式 2.5 µs','kw40':'显式 4 µs',
        'tpi25':'TPI 2.5 µs','tpi40':'TPI 4 µs','tpi625':'TPI 6.25 µs','tpi100':'TPI 10 µs'}
COLORS={'kw10':'#142e5b','kw125':'#3f7ab6','kw25':'#858ca6','kw40':'#a4bfcb','tpi25':'#00866b','tpi40':'#dc7c00','tpi625':'#6f4e95','tpi100':'#a93250'}
MARKERS=('o','s','P','X','^','D','<','v')
FIELDS=(('pressure_RMS_Pa','层孔压 RMS 误差 (Pa)'),('top_error_mm','顶部沉降误差 (mm)'),('bottom_error_mm','底部沉降误差 (mm)'))


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def single(lane,backend):
    tag=f'{PREFIX}_{lane}_{backend}'
    sources=[p for p in [LOG/(tag+'.json'),*sorted(LOG.glob(tag+'_vs_kw*.json'))] if p.is_file()]
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


def lane_status(lane,backend):
    folder=directory(lane,backend)
    state=dict(backend=backend,lane=lane,status='未测',exit_code=None,elapsed_wall_s=None,failed_step_index=None,
               first_error='',last_native_file='',last_original_PART_line='',receipt='')
    if not folder.exists():return state
    if not (folder/'start.json').is_file():
        return dict(state,status='已有目录，缺运行记录')
    start=read(folder/'start.json')
    need(start['lane']==lane and start['backend']==backend,'Wrong start identity')
    if not (folder/'exit.json').is_file():
        return dict(state,status='已启动，尚无退出记录')
    ex=read(folder/'exit.json')
    need(all(ex[k]==v for k,v in start.items()) and ex['program_unchanged'],'Changed run binding')
    state.update(exit_code=ex['exit'],elapsed_wall_s=ex['wall_seconds'],receipt=str(folder/'exit.json'))
    if ex['exit']==0:return dict(state,status='求解已完成')
    log=(folder/'result/Run.out').read_text(encoding='utf8',errors='replace')
    console=(folder/'console.log').read_text(encoding='utf8',errors='replace')
    lines=log.splitlines()
    error=next((s for s in lines if s.startswith('Text:')),None)
    if error is None:error=next((s for s in lines if s.startswith('*** Exception')),None)
    need(error and error in console and f"Finished execution (code={ex['exit']})" in log,'Unsupported failure identity '+lane)
    step=re.search(r'\bstep=(\d+)\b',error)
    parts=sorted((folder/'result/data').glob('Part_*.bi4'))
    saved=[s for s in lines if s.strip().startswith('Part_') and re.match(r'^Part_\d+',s.strip())]
    return dict(state,status='求解失败',failed_step_index=int(step[1]) if step else None,first_error=error,
                last_native_file=parts[-1].name if parts else '',last_original_PART_line=saved[-1] if saved else '')


def active_lanes():
    return tuple(lane for lane in LANES if lane not in OPTIONAL or
                 any((directory(lane,b)/'start.json').is_file() for b in BACKENDS))


def inputs():
    runs={};sources={};cross={};statuses=[]
    for lane in active_lanes():
        for b in BACKENDS:
            state=lane_status(lane,b)
            statuses.append(state)
            if state['status']=='求解已完成':
                runs[b,lane],sources[b,lane]=single(lane,b)
                state['status']='已审查'
            else:
                need(state['status'] in ('求解失败','未测'),
                     f'{b} {lane} {state["status"]}；等待本轮终态后发布')
        if any((b,lane) not in runs for b in BACKENDS):
            continue
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
    return runs,sources,cross,statuses


def hydraulic_margin(run,cfg):
    if cfg['model']!=2:
        return {}
    dt=cfg['dt_s'];factor=cfg['R']
    rows=run['rows']
    # JDsFixedDt stores the maximum of (fixed - composite) in each output interval.
    closed=rows[1:]
    worst=min(closed,key=lambda r:dt-r['signed_dterror_s'])
    saved=min(rows,key=lambda r:r['saved_hydraulic_bound_s'])
    composite=dt-worst['signed_dterror_s'];raw=saved['saved_hydraulic_bound_s']/factor
    need(composite>0 and raw>0,'Invalid hydraulic bound')
    return dict(nonempty_signed_intervals=len(closed),composite_bound_min_s=composite,
                composite_min_interval_part=worst['part'],composite_min_interval_end_s=worst['t_s'],
                R_required_upper_from_composite=factor*dt/composite,saved_hydraulic_raw_min_s=raw,
                saved_hydraulic_min_part=saved['part'],saved_hydraulic_min_time_s=saved['t_s'],
                R_required_lower_at_saved_states=dt/raw)


def summarize(runs,sources,cross):
    history=[];cost=[]
    for backend in BACKENDS:
        anchor=runs.get((backend,'kw10'))
        eligible=[lane for lane in REFERENCES['lanes'] if anchor and (backend,lane) in runs
                  and against_reference(anchor,runs[backend,lane],anchor)['predeclared_target_noninferiority_pass']]
        ref=min(eligible,key=lambda l:runs[backend,l]['wall_s']) if eligible else None
        reference=runs[backend,ref] if ref else None
        for lane in LANES:
            if (backend,lane) not in runs:continue
            run=runs[backend,lane];cfg=PLAN['lanes'][lane];cross_lane=cross.get(lane)
            theory='finite_Kw' if cfg['model']==1 else 'M0'
            for row in run['rows']:
                target=round((row['part']-2)*PLAN['save_delta_Tv'],12) if row['part']>=3 else None
                history.append(dict(backend=backend,lane=lane,reference_theory=theory,dt_us=1e6*cfg['dt_s'],hydraulic_R=cfg.get('R'),
                                    target_Tv=target,predeclared_accuracy_target=target in (.005,.05),
                                    unamplified_saved_hydraulic_s=row['saved_hydraulic_bound_s']/cfg.get('R',1.),
                                    interval_min_composite_s=cfg['dt_s']-row['signed_dterror_s'] if row['part'] else None,**row))
            match=against_reference(reference,run,anchor)['predeclared_target_noninferiority_pass'] if ref else False
            cross_ok=cross_lane['cross_backend_field_gate_pass'] if cross_lane else None
            paired=ref in cross and cross_lane is not None
            eligible_ratio=match and paired and cross_ok and cross[ref]['cross_backend_field_gate_pass']
            if not ref: reason='无合格的显式参考'
            elif not match: reason='未通过同端预设精度门'
            elif not paired: reason='缺完整跨端对照'
            elif not eligible_ratio: reason='跨端复现门未通过'
            elif ref==lane: reason='显式计时基准'
            elif run['wall_s']>=reference['wall_s']: reason='精度合格，壁钟未加快'
            else: reason='短窗精度合格，壁钟较短'
            cost.append(dict(backend=backend,lane=lane,reference_theory=theory,dt_us=cfg['dt_s']*1e6,hydraulic_R=cfg.get('R'),
                             host=run['host'],hardware=run['hardware'],driver=run['cuda_driver_runtime'],steps=run['steps'],frames=len(run['rows']),
                             wall_s=run['wall_s'],loop_s=run['loop_s'],run_total_s=run['total_s'],save_timer_s=run['save_timer_s'],native_bytes=run['io_bytes'],
                             explicit_reference=ref,reference_wall_s=reference['wall_s'] if ref else None,reference_loop_s=reference['loop_s'] if ref else None,
                             target_noninferiority_pass=match,saved_stress_pass=run['early_100Pa_stress_pass'],max_layer_stress_error_Pa=run['post01_max_layer_Pa'],
                             max_topgap_Pa=run['post01_max_topgap_Pa'],cross_field_pass=cross_ok,
                             cross_pressure_RMS_max_Pa=cross_lane['max_material_pressure_RMS_Pa']['value'] if cross_lane else None,
                             cross_displacement_max_mm=cross_lane['max_material_displacement_diff_mm']['value'] if cross_lane else None,
                             qualified_wall_ratio=reference['wall_s']/run['wall_s'] if eligible_ratio else None,
                             qualified_loop_ratio=reference['loop_s']/run['loop_s'] if eligible_ratio else None,interpretation=reason,
                             single_receipts=sources[backend,lane],cross_receipt=f'{PREFIX}_{lane}_cpu_gpu.json' if cross_lane else '',
                             **hydraulic_margin(run,cfg)))
    return history,cost


def layer_errors(runs):
    """Compare pressure at the same 100 material layers used for target RMS."""
    records=[]
    for (backend,lane),run in runs.items():
        cfg=PLAN['lanes'][lane]
        data=directory(lane,backend)/'result/data'
        def saved(part):
            _,meta,fields,_=read_native(data/f'Part_{part:04d}.bi4',part,run['model'],cfg.get('R',1.))
            need(meta['TimeStep']==run['rows'][part]['t_s'] and
                 meta['Step']==max(0,run['rows'][part]['completed']-1),'Reviewed PART clock')
            order=np.argsort(fields['Idp'])
            need(np.array_equal(fields['Idp'][order],np.arange(1040)),'Material labels')
            return fields,order[40:]
        initial,soil=saved(0)
        z=initial['Posd'][soil,2]
        layer=np.rint(z/.01-.5).astype(int)
        need(np.array_equal(np.bincount(layer),np.full(100,10)),'Native 100-layer column')
        zmean=np.bincount(layer,z)/10
        for part in (3,12):
            fields,soil=saved(part)
            row=run['rows'][part]
            p=np.bincount(layer,fields['PorePress'][soil])/10
            ref,_=theory(row['t_s'],zmean,run['model'])
            error=p-ref
            need(np.isclose(np.sqrt(np.mean(error**2)),row['pressure_RMS_Pa'],atol=1e-8,rtol=0),'Reproduced pressure RMS')
            for i in range(100):
                records.append(dict(backend=backend,lane=lane,part=part,target_Tv=(part-2)*PLAN['save_delta_Tv'],
                                    time_s=row['t_s'],actual_Tv=row['actual_Tv'],initial_layer=i,initial_z_m=zmean[i],
                                    material_particles=10,pressure_Pa=p[i],theory_Pa=ref[i],error_Pa=error[i]))
    return records


def figures(history,cost,statuses):
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
                if not sel:continue
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
        sel={row['lane']:row for row in cost if row['backend']==b}
        states={row['lane']:row for row in statuses if row['backend']==b}
        legend_added=False
        visible=[lane for lane in LANES if lane in states]
        for i,lane in enumerate(visible):
            if lane not in sel:
                st=states[lane]
                label='未测' if st['status']=='未测' else '失败'
                if st.get('failed_step_index') is not None:label+=f"\n步 {st['failed_step_index']}"
                ax.text(i,.06,label,transform=ax.get_xaxis_transform(),ha='center',va='bottom',color='#78504a',fontsize=8)
                continue
            r=sel[lane]
            ax.bar(i-.18,r['wall_s'],width=.34,color=COLORS[lane],label='进程壁钟' if not legend_added else None)
            ax.bar(i+.18,r['loop_s'],width=.34,facecolor='white',edgecolor=COLORS[lane],hatch='//',label='求解主循环' if not legend_added else None)
            legend_added=True
        ax.set_xticks(range(len(visible)),[LABELS[l].replace(' ','\n',1) for l in visible])
        ax.set_title(b.upper());ax.set_ylabel('实际用时 (s)');ax.grid(axis='y',alpha=.22);ax.set_axisbelow(True);ax.legend()
    timing.suptitle('相同输出计划下的实际计算用时',fontsize=14)
    return fig,timing


def write_csv(path,records):
    with path.open('x',encoding='utf-8-sig',newline='') as f:
        keys=list(dict.fromkeys(k for row in records for k in row))
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(records)


def supplemental_checks(cost):
    lines=['','## 固定 4 µs 的 R 检查','','把 R 从 1 调至 2.25，两组使用相同的实际步长。比较初始、开排水前最后一步及其后第一步。',
           '','| 后端 | 共同帧／末步 | 材料孔压、顶部沉降 | 区间最小复合上限，R=1／2.25 (µs) | R=2.25 壁钟 (s) |','|---|---|---|---:|---:|']
    for b in BACKENDS:
        path=LOG/f'c02_tpi_r_fixed4_r1_{b}.json'
        if not path.is_file():
            lines.append(f'| {b.upper()} | 待原生审查 | — | — | — |');continue
        r=read(path);rows=r['rows'];run=r['run']
        need(r['passed'] and run['exit']==0 and run['backend']==b and r['candidate_cap']==2501
             and [x['completed'] for x in rows]==[0,2500,2501] and r['omitted_reference_saves']==10
             and all(x['exact_native_arrays']==22 and x['native_ids']==1040 and x['typed_R']['candidate']==2.25 for x in rows)
             and [x['exact_previous_pressure_ids'] for x in rows]==[0,1000,1000], 'Independent fixed-dt R receipt '+b)
        limits=[min(x['interval_min_composite_limit_s'][k] for x in rows[1:])*1e6 for k in ('baseline','candidate')]
        lines.append(f"| {b.upper()} | [3／2501](../../logs/{path.name}) | 两者均逐位相同 | {limits[0]:.6f}／{limits[1]:.6f} | {run['wall_s']:.3f} |")
    lines+=['','这三帧检验了 R 对步长上限的作用。两端各自以本端 R=1 的相同步号为基准；此项不含 Tv=.005、.05 的精度或计时比较。',
            '','## 同一步长的显式与三轮 TPI 对照','','首目标为 Tv=.005，达到后才评估本端是否进入 13 帧全窗。表中分别列同一步长显式与 TPI 对各自解析解的误差；顶部沉降误差保留符号。',
            '','| 后端 | Δt (µs) | 实测范围／目标 Tv | 层孔压 RMS，显式／TPI (Pa) | 顶部误差，显式／TPI (mm) | TPI 壁钟／主循环 (s) | 判定 |','|---|---:|---|---:|---:|---:|---|']
    full={}
    for b in BACKENDS:
        ref=next((r['explicit_reference'] for r in cost if r['backend']==b and r['explicit_reference']),None)
        if not ref:
            lines.append(f'| {b.upper()} | — | 无合格显式参考 | — | — | — | — |');continue
        for window,count in [('first',4),('full',13)]:
            path=LOG/f'c02_tpi_same_dt_r1_{b}_{ref}_{window}.json'
            if not path.is_file():
                work=directory(f'tpi_same_{ref}_{window}',b)
                reason='全窗未启动' if window=='full' else '首目标未启动'
                if (work/'exit.json').is_file():
                    code=read(work/'exit.json')['exit']
                    reason='求解完成，待原生审查' if code==0 else f'求解退出码 {code}'
                elif (work/'start.json').is_file():reason='已启动，暂无退出记录'
                lines.append(f"| {b.upper()} | {1e6*PLAN['lanes'][ref]['dt_s']:g} | {reason} | — | — | — | — |");break
            r=read(path);t=r['tpi'];same=r['explicit_at_shared_saves'];pairs=r['matched_material_rows'];rows=t['rows']
            need(r['window']==window and r['explicit_reference']==ref and r['independent_anchor']==REFERENCES['anchor']
                 and r['backend']==t['backend']==b and t['model']==2 and t['lane']==f'tpi_same_{ref}_{window}'
                 and r['dt_s']==PLAN['lanes'][ref]['dt_s'] and r['R']==1. and t['steps']==rows[-1]['completed']
                 and len(same)==len(pairs)==len(rows)==count and all(x['completed']==y['completed'] and x['t_s']==y['t_s']==z['t_s']
                    for x,y,z in zip(rows,same,pairs)) and r['post_point1s_guard_evaluated']==(window=='full'), 'Matched-dt coverage '+path.name)
            if window=='first':
                misses=[label for key,label in [('pressure_ok','孔压'),('top_ok','顶层沉降'),('bottom_ok','底层沉降')]
                        if not all(r[field][0][key] for field in ('first_vs_same_dt','first_vs_anchor'))]
                need(r['first_target_pass']==(not misses),'First target flags '+b)
                verdict='首目标通过' if not misses else '首目标未过（'+'、'.join(misses)+'）'
            else:
                need(r['first_target_pass'] and r['shared_short_prefix_frames']==4,'Full same-dt admission '+b)
                full[b]=r
                verdict='全窗同端精度通过' if r['full_accuracy']['predeclared_target_noninferiority_pass'] else '全窗同端精度未过'
            for i in ([3] if window=='first' else [3,12]):
                e,m=same[i],rows[i];tv=(i-2)*PLAN['save_delta_Tv']
                times=f"{t['wall_s']:.3f}／{t['loop_s']:.3f}" if i==count-1 else '—'
                lines.append(f"| {b.upper()} | {r['dt_s']*1e6:g} | [{count} 帧／{tv:g}](../../logs/{path.name}) | "
                             f"{e['pressure_RMS_Pa']:.3f}／{m['pressure_RMS_Pa']:.3f} | {e['top_error_mm']:+.6f}／{m['top_error_mm']:+.6f} | {times} | {verdict} |")
            if not r['first_target_pass']:
                need(not (LOG/f'c02_tpi_same_dt_r1_{b}_{ref}_full.json').exists(),'Unexpected later full-window review '+b)
                break
    lines+=['','4 帧行的耗时仅覆盖首目标。13 帧行的耗时覆盖两个目标及后段应力检查。']
    paired=False
    if len(full)==len(BACKENDS) and len({r['tpi']['lane'] for r in full.values()})==1:
        lane=full['cpu']['tpi']['lane'];p=LOG/f'{PREFIX}_{lane}_cpu_gpu.json'
        if p.is_file():
            c=read(p)
            need(c['lane']==lane and c['all_pair_clocks_exact'] and c['native_pairs']==len(c['rows'])==13
                 and c['fields_per_native_frame']==22 and c['soil_count']==1000 and c['fixed_count']==40
                 and c['backend_pressure_RMS_limit_Pa']==5. and c['backend_displacement_limit_mm']==.005
                 and c['cross_backend_field_gate_pass']==(max(row['material_pressure_RMS_Pa'] for row in c['rows'])<=5.
                                                          and max(row['material_max_displacement_diff_mm'] for row in c['rows'])<=.005)
                 and all(c['program_identities'][b]==full[b]['tpi']['program_identity'] and c['hardware'][b]==full[b]['tpi']['hardware']
                         and c['host']==full[b]['tpi']['host'] and all(x['t_s']==y['t_s'] and x['completed_step']==y['completed']
                         for x,y in zip(c['rows'],full[b]['tpi']['rows'])) for b in BACKENDS),'Matched-dt cross receipt')
            paired=c['cross_backend_field_gate_pass'] and all(r['full_accuracy']['predeclared_target_noninferiority_pass'] for r in full.values())
    if paired:
        lines.append('')
        for b,r in full.items():
            lines.append(f"- {b.upper()} 同端合格全窗壁钟比（显式／TPI）{r['equal_accuracy_wall_ratio_explicit_over_tpi']:.3f}，主循环比 {r['equal_accuracy_loop_ratio_explicit_over_tpi']:.3f}。")
    else:
        lines.append('同一步长辅助组尚无同时满足两端全窗精度与跨端场一致性的耗时比。')
    return lines


def summary_text(cost,statuses):
    lines=['# C02 高渗透率短窗精度与成本','',
           'k=10⁻³ m/s，排水从 0.01 s 开始。每组 13 帧，排水后的输出间隔 ΔTv=.005，终点 Tv≈.05。显式 u-pl 对应有限 Kw 解析解，三轮 TPI 对应 M0 解析解。孔压取 100 个材料层的 RMS，顶部和底部取各自初始材料层的沉降误差。','',
           '同端精度按 Tv=.005、.05 的原误差带和 t≥.1 s 各保存帧的总应力限值评定。跨端另按同一材料、同一步号的孔压 RMS ≤5 Pa 与最大位移差 ≤.005 mm 评定。以显式 1 µs 为独立参考。1.25 µs 必须直接满足相对 1 µs 的原门槛才可作为更快参考组；候选同时相对选定组及 1 µs 独立判定。','',
           '| 后端 | 配置 | 参考 | 主循环 (s) | 壁钟 (s) | 合格壁钟比¹ | 判定 |','|---|---|---|---:|---:|---:|---|']
    for r in cost:
        ratio='—' if r['qualified_wall_ratio'] is None else f"{r['qualified_wall_ratio']:.3f}"
        lines.append(f"| {r['backend'].upper()} | {LABELS[r['lane']]} | {LABELS.get(r['explicit_reference'],'—')} | {r['loop_s']:.3f} | {r['wall_s']:.3f} | {ratio} | {r['interpretation']} |")
    hydro=[r for r in cost if r.get('nonempty_signed_intervals')]
    if hydro:
        lines.extend(['','## 实测水力步长余量','','| 后端 | 组 | 保存态未放大水力界最小 (µs) | 非空区间复合界最小 (µs) | 保存态所见 R 下界 | 复合约束给出的 R 上界 |','|---|---|---:|---:|---:|---:|'])
        for row in hydro:
            lines.append(f"| {row['backend'].upper()} | {LABELS[row['lane']]} | {row['saved_hydraulic_raw_min_s']*1e6:.5f} | {row['composite_bound_min_s']*1e6:.5f} | {row['R_required_lower_at_saved_states']:.5f} | {row['R_required_upper_from_composite']:.5f} |")
        lines.extend(['','每个非空输出区间的 dterror 为固定步长减复合上限的最大值；Δt−dterror 给出该区间观测到的最小复合上限。复合上限也受到力学及黏性限制，HG 另行检查。此表只描述本次轨迹上的水力需求。'])
    missing=[s for s in statuses if s['status']!='已审查']
    if missing:
        lines.extend(['','## 未计入精度与成本比的组',''])
        for s in missing:
            extra=f"。退出码 {s['exit_code']}。{s['first_error']}。最后原生文件 {s['last_native_file']}。" if s['first_error'] else '。'
            lines.append(f"- {s['backend'].upper()} {LABELS[s['lane']]}，{s['status']}{extra}")
    lines.extend(['','¹ 壁钟比为参考耗时除以本组耗时；大于 1 表示本次测量较快。每组一次计时，包含实际写盘开销。跨端门和同端精度门都通过才列合格比。'])
    lines.extend(supplemental_checks(cost))
    lines.extend(['','各时刻及三个误差量见 [history.csv](history.csv)。两个目标时刻各 100 层的材料高度、孔压、理论值和带符号误差见 [pressure_layers.csv](pressure_layers.csv)。各端硬件、程序收据、跨端最大差、主循环和输出开销见 [timing.csv](timing.csv)。每个后端的状态、退出码、首因及最后保存记录见 [status.csv](status.csv)。'])
    return '\n'.join(lines)+'\n'


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--publish',action='store_true',help='Generate reviewed artifacts; default prints current status only')
    if not cli.parse_args().publish:
        for b in BACKENDS:
            for lane in active_lanes():
                st=lane_status(lane,b)
                print(b,lane,st['status'],st['exit_code'],st['first_error'])
        return
    dest=TESTS/'figures'/PREFIX
    need(not dest.exists(),'Existing published summary is preserved')
    runs,sources,cross,statuses=inputs()
    history,cost=summarize(runs,sources,cross)
    need(history and cost,'No completed lane reviews')
    with tempfile.TemporaryDirectory(prefix=PREFIX+'_',dir=dest.parent) as tmp:
        bundle=Path(tmp)/PREFIX;bundle.mkdir()
        write_csv(bundle/'history.csv',history);write_csv(bundle/'timing.csv',cost);write_csv(bundle/'status.csv',statuses)
        write_csv(bundle/'pressure_layers.csv',layer_errors(runs))
        a,b=figures(history,cost,statuses)
        try:
            a.savefig(bundle/'accuracy.png',dpi=175);b.savefig(bundle/'timing.png',dpi=175)
        finally:
            plt.close(a);plt.close(b)
        (bundle/'summary.md').write_text(summary_text(cost,statuses),encoding='utf8')
        bundle.rename(dest)
    print(dest)


if __name__=='__main__':main()
