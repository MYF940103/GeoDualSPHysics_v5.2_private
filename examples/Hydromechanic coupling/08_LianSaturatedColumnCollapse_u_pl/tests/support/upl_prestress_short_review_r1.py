"""Actual400-update implementation comparison; no half-step or equilibrium claim."""
import struct,json
from pathlib import Path
from upl_plastic_periodic_pair_r1 import np,plt,SCHEMA,TYPES,need,js,stat,write,table,frob
T=Path(__file__).resolve().parents[1];P=T/'figures/upl_prestress_short_review_r1'
paths={k:Path(str(P)+s) for k,s in dict(metrics='_metrics.csv',timing='_timing.csv',png='.png',check='.check.json').items()}
need(not any(p.exists() for p in paths.values()),'Existing short review protected')
tags=('upl_prestress_check_CPU_r1','upl_prestress_check_release_CPU_r1','upl_prestress_check_GPU_r1')
data={};inputs=[stat(Path(__file__))]
for label,tag in zip(('DebugCPU','ReleaseCPU','ReleaseGPU'),tags):
    cp=T/'logs'/(tag+'_native_r1.check.json');rp=T/'logs'/(tag+'.run.json');c,r=js(cp),js(rp)
    need(c['passed'] and r['passed'] and r['actual_exit']==0 and r['actual_steps']==400,'Closed400-update native run required')
    d=T/'outputs'/(tag+'_native_r1');completion=js(d/'completion.json');n,samples=completion['total_native_IDs'],completion['samples'];frames=[];times=[]
    need(n==7060 and completion['typed_arrays']==22 and samples==r['saved_frames'],'Actual native profile differs')
    with (d/'typed22.bin').open('rb') as f:
        need(struct.unpack('<III',f.read(12))==(n,22,samples),'Actual export header differs')
        for part in range(samples):
            times.append(struct.unpack('<d',f.read(8))[0]);a={}
            for name,kind,nc in SCHEMA:
                v=np.fromfile(f,dtype=TYPES[kind],count=n*nc);need(v.size==n*nc,'Incomplete typed record');a[name]=v.reshape(n,nc) if nc>1 else v
            need(np.array_equal(a['Idp'],np.arange(n)),'Native IDs not aligned');frames.append(a)
        need(not f.read(1),'Extra typed payload')
    inputs += [stat(p) for p in (cp,rp,d/'completion.json',d/'typed22.bin',d/'history.csv',d/'clocks.csv')]
    data[label]=dict(frames=frames,times=times,run=r,history=[x for x in table(d/'history.csv') if x['initial_material_band']=='all'])
metrics=[];soil=slice(2060,7060)
for left,right in (('DebugCPU','ReleaseCPU'),('ReleaseCPU','ReleaseGPU')):
    a,b=data[left],data[right];need(a['times']==b['times'],'All actual saved clocks must match without interpolation')
    for part,(fa,fb) in enumerate(zip(a['frames'],b['frames'])):
        dp=fb['PorePress'][soil].astype(float)-fa['PorePress'][soil].astype(float)
        du=(fb['Posd'][soil]-fa['Posd'][soil])*1000
        sa=np.column_stack((fa['SigmaState_kk'][soil]-fa['PorePress'][soil,None],fa['SigmaState_ij'][soil]))
        sb=np.column_stack((fb['SigmaState_kk'][soil]-fb['PorePress'][soil,None],fb['SigmaState_ij'][soil]))
        metrics.append(dict(pair=left+'_vs_'+right,part=part,actual_time_s=a['times'][part],soil_IDs=5000,
            pressure_difference_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),pressure_difference_max_Pa=float(np.abs(dp).max()),
            material_XYZ_displacement_difference_max_mm=float(np.linalg.norm(du,axis=1).max()),
            total_stress_difference_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(sb-sa)**2))),
            J_difference_max=float(np.abs(fb['PoroVolumeRatio'][soil]-fa['PoroVolumeRatio'][soil]).max()),
            kappa_difference_max=float(np.abs(fb['Kplastic'][soil]-fa['Kplastic'][soil]).max())))
write(paths['metrics'],metrics)
timing=[]
for label,d in data.items():
    run=d['run']['summary'];loop=float(run['TSimul'])
    timing.append(dict(program=label,steps=400,actual_physical_end_s=d['times'][-1],loop_s=loop,steps_per_loop_second=400/loop,
        linear5s_loop_estimate_hours=loop*5000/3600,hardware=run['Hardware'],short_observed_timing_not_controlled_benchmark=True))
write(paths['timing'],timing)
fig,axes=plt.subplots(2,2,figsize=(11.7,8.2));colors=('#888888','#1767a2','#d47a18')
for label,color in zip(data,colors):
    d=data[label];x=np.array(d['times'])*1000
    for ax,key,scale,title,ylabel in ((axes[0,0],'p_RMS_Pa',.001,'Actual pore pressure','pressure RMS (kPa)'),(axes[0,1],'native_excess_mean_Pa',.001,'Native excess: p minus initial material p0','excess mean (kPa)'),(axes[1,0],'sigma_eff_Frobenius_RMS_Pa',1.,'Effective stress develops from zero','Frobenius RMS (Pa)'),(axes[1,1],'velocity_XYZ_RMS_m_s',1.,'Actual gravity startup with damping','velocity RMS (m/s)')):
        y=[float(r[key])*scale for r in d['history']]
        ax.plot(x,y,color=color,label=label,lw=1.6 if label!='DebugCPU' else 1.,ls='none' if label=='ReleaseGPU' else '--' if label=='DebugCPU' else '-',marker='o' if label=='ReleaseGPU' else None,mfc='none',ms=5)
        ax.set(title=title,xlabel='actual physical time (ms)',ylabel=ylabel);ax.grid(alpha=.22)
axes[0,0].legend(fontsize=8);fig.suptitle('Case08: hydrostatic pressure, damping0.02 and Shepard40 / 400 real updates',fontsize=13)
fig.text(.5,.018,'Same400 updates and11 actual saves; no interpolation, half-step or equilibrium claim.\nInitial effective stress is zero. Initial surface excess near -196 Pa comes from the existing positive-pressure surface policy, not plastic dilation.',ha='center',fontsize=8.5)
fig.tight_layout(rect=(0,.07,1,.95));fig.savefig(paths['png'],dpi=180);plt.close(fig)
passed=all(r['pressure_difference_RMS_Pa']<=5 and r['material_XYZ_displacement_difference_max_mm']<=.005 for r in metrics)
need(all(stat(e['path'])==e for e in inputs),'Consumed completed data changed')
result=dict(stage='upl_prestress_short_review_r1',short_implementation_comparison_passed=passed,original_pressure_RMS_bound_Pa=5,original_material_XYZ_bound_mm=.005,
    same_dt_comparison_not_half=True,all_actual_clocks_matched=True,pairs=len(metrics),
    maxima={k:max(r[k] for r in metrics) for k in metrics[0] if 'difference_' in k},
    timing=timing,recommended_local_backend='CPU8' if timing[1]['loop_s']<timing[2]['loop_s'] else 'GPU',
    physical_acceptance=False,figure_visual_QA_pending=True,source_inputs=inputs,outputs=[stat(p) for k,p in paths.items() if k!='check'],SHA_scans=0)
with paths['check'].open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=passed,maxima=result['maxima'],recommended_local_backend=result['recommended_local_backend'])),flush=True)
need(passed,'Keep failed comparison; do not admit extended run')
