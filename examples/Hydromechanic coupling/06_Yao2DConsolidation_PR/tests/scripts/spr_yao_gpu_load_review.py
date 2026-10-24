"""Post-telemetry GPU review: original physical fields stay exact, load is now observable."""
from pathlib import Path
import argparse
import io
import json
import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import Normalize
from spr_yao_short import TESTS,REPO,bound
from spr_yao_review import native
from spr_yao_step_review import exact_fields

VARIANTS=('faces_off','faces_on','faces_half')
META=TESTS/'outputs/read_meta_r1/ReadPartMetadata.exe'


def verify_input(item):
    if bound(item['path'])['sha256']==item['sha256']:return
    pinned=REPO/'examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR/tests/outputs/spr_gpu_planes_preload_verified'/Path(item['path']).name
    assert pinned.is_file() and bound(pinned)['sha256']==item['sha256'],('Historical input unavailable',item['path'])


def load_state(tag):
    path=TESTS/'logs'/(tag+'.status.json');r=json.loads(path.read_text());assert r['status']=='completed_pending_review'
    for item in r['inputs']:verify_input(item)
    for run in r['runs']:
        assert run['exit_code']==0 and run['owned_exited']
        for item in run['outputs']:assert bound(item['path'])['sha256']==item['sha256']
    return r


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',choices=['spr_yao_gpu_load_grid02_r2','spr_yao_gpu_load_grid10_r2'],required=True);args=parser.parse_args()
    tag=args.tag;receipt=TESTS/'logs'/(tag+'.review.json');assert not receipt.exists()
    run=load_state(tag);duration=float(run['duration_s']);count=round(duration/.001)+1
    cpu_tag='spr_yao_grid02_r1' if duration==.02 else 'spr_yao_grid10_r1';cpu=load_state(cpu_tag)
    ref_tag='spr_yao_gpu_load_raw02_r2' if duration==.02 else 'spr_yao_gpu_load_grid02_r2';reference=load_state(ref_tag)
    old_tag='spr_yao_gpu_grid02_r1' if duration==.02 else None
    if old_tag:old=load_state(old_tag)
    evidence=[bound(__file__),bound(META)]+[bound(TESTS/'logs'/(x+'.status.json')) for x in (tag,cpu_tag,ref_tag)]
    initial=native(TESTS/'outputs'/(tag+'_faces_off'),0);assert len(initial)==20301
    top=np.isclose(initial.z,10,atol=1e-8);strip=abs(initial.x)<3-1e-8;core=set(initial.id[top&strip]);ends=set(initial.id[top&(abs(abs(initial.x)-3)<1e-8)])
    assert len(core)==59 and ends=={8814,14874}
    metadata={};ref_times={};prefix={v:0 for v in VARIANTS};hist=[];comparison=[];finals={};outputs=[];old_physical_0ulp={v:0 for v in VARIANTS}
    for variant in VARIANTS:
        folder=TESTS/'outputs'/(tag+'_'+variant);r=subprocess.run([str(META),str(folder/'data'),str(count)],capture_output=True,check=True)
        a=pd.read_csv(io.BytesIO(r.stdout),float_precision='round_trip');assert len(a)==count and a.nout.eq(0).all() and a.native_count.eq(21945).all()
        dt=1e-5 if variant=='faces_half' else 2e-5;active=a[a.part.gt(0)]
        assert active.has_dterror.eq(1).all() and active.dterror_s.between(-1e100,0).all() and active.dt_min_s.eq(dt).all() and active.dt_max_s.eq(dt).all()
        metadata[variant]=dict(frames=count,mechanical_min_dt_s=float(dt-active.dterror_s.max()),pore_limit_s=9.53206462560066e-5)
        path=TESTS/'figures'/(tag+'_'+variant+'_metadata.csv');assert not path.exists();path.write_bytes(r.stdout);outputs.append(path)
        reference_folder=TESTS/'outputs'/(ref_tag+'_'+variant);nref=len(list((reference_folder/'data').glob('Part_*.bi4')))
        r=subprocess.run([str(META),str(reference_folder/'data'),str(nref)],capture_output=True,check=True);a=pd.read_csv(io.BytesIO(r.stdout),float_precision='round_trip')
        ref_times[variant]={round(float(x.time_s),10):(int(x.part),float(x.time_s)) for x in a.itertuples()}
    for i in range(count):
        frame={}
        for variant in VARIANTS:
            folder=TESTS/'outputs'/(tag+'_'+variant);a=native(folder,i);frame[variant]=a;t=float(a.time_s.iloc[0])
            assert abs(t-i*.001)<1e-10 and np.array_equal(a.id,initial.id)
            assert np.isfinite(a.to_numpy()).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.load_available.eq(1).all()
            assert a.x.between(-10.0001,10.0001).all() and a.z.ge(-.0001).all()
            if i==0:assert np.array_equal(a[['x','y','z']],initial[['x','y','z']])
            loaded=set(a.id[abs(a.load_az)>0]);assert not loaded if i==0 else core.issubset(loaded) and loaded.issubset(core|ends)
            dt=1e-5 if variant=='faces_half' else 2e-5;q=5000*min(1,max(0,t-dt)/.1) if i else 0
            force=float(17*a.load_az.sum());target=-17*float(np.float32(q/170))*len(loaded);assert abs(force-target)<.002
            drained=a.fstype.isin([2,3])&~a.x.between(-3,3);assert a.pressure[drained].eq(0).all()
            displacement=a[['x','z']].to_numpy()-initial[['x','z']].to_numpy();u=(initial.z-a.z)*1000;corner=(initial.z<.5)&(abs(initial.x)>9.5)
            hist.append(dict(variant=variant,time_s=t,max_pressure_pa=float(a.pressure.max()),mean_pressure_pa=float(a.pressure.mean()),strip_settlement_mm=float(u[top&strip].mean()),
                max_material_displacement_mm=float(np.linalg.norm(displacement,axis=1).max()*1000),corner_pressure_rms_pa=float(np.sqrt(np.mean(a.pressure[corner]**2))),
                max_total_stress_pa=float(abs(a.sigma_zz-a.pressure).max()),force_N_m=force,loaded_count=len(loaded)))
            reference_slot=ref_times[variant].get(round(t,10))
            if reference_slot:
                j,tr=reference_slot;assert abs(t-tr)<1e-11 and exact_fields(a,native(TESTS/'outputs'/(ref_tag+'_'+variant),j)),(variant,'same-backend prefix',i,j)
                prefix[variant]+=1
            b=native(TESTS/'outputs'/(cpu_tag+'_'+variant),i);assert np.array_equal(a.id,b.id) and abs(t-b.time_s.iloc[0])<1e-10
            if i==0:assert np.array_equal(a[['x','y','z']],b[['x','y','z']])
            comparison.append(dict(kind='CPU_GPU',variant=variant,time_s=t,pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
                max_material_displacement_mm=float(np.linalg.norm(a[['x','z']].to_numpy()-b[['x','z']].to_numpy(),axis=1).max()*1000),
                total_stress_rms_pa=float(np.sqrt(np.mean(((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure))**2))),force_difference_N_m=float(force-17*b.load_az.sum())))
            if old_tag:
                previous=native(TESTS/'outputs'/(old_tag+'_'+variant),i)
                fields=a.columns.difference(['time_s','saved_step','load_az'])
                assert np.array_equal(a.id,previous.id) and abs(t-previous.time_s.iloc[0])<1e-11
                assert a[fields].to_numpy(dtype='<f8').tobytes()==previous[fields].to_numpy(dtype='<f8').tobytes(),(variant,i,'Output-only physical regression')
                assert previous.load_az.eq(0).all()
                old_physical_0ulp[variant]+=1
            if i==count-1:finals[variant]=a
        a,b=frame['faces_on'],frame['faces_half']
        comparison.append(dict(kind='GPU_half',variant='faces_on_vs_half',time_s=float(a.time_s.iloc[0]),pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
            max_material_displacement_mm=float(np.linalg.norm(a[['x','z']].to_numpy()-b[['x','z']].to_numpy(),axis=1).max()*1000),total_stress_rms_pa=float(np.sqrt(np.mean(((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure))**2))),force_difference_N_m=float(17*(a.load_az.sum()-b.load_az.sum()))))
        if i%10==0:print('Reviewed native frame',i,'of',count-1,flush=True)
    history=pd.DataFrame(hist);compare=pd.DataFrame(comparison)
    passed=bool(compare.pressure_rms_pa.le(5).all() and compare.max_material_displacement_mm.le(.005).all())
    assert all(n>1 for n in prefix.values())
    if duration==.1:assert all(n==21 for n in prefix.values())
    stem=TESTS/'figures'/tag
    for suffix,data in [('_history.csv',history),('_comparison.csv',compare)]+[('_'+k+'_final.csv',v) for k,v in finals.items()]:
        path=Path(str(stem)+suffix);data.to_csv(path,index=False,mode='x');outputs.append(path)
    fig,axes=plt.subplots(2,2,figsize=(12,8));colors={'faces_off':'#696969','faces_on':'#2166a5','faces_half':'#b18b2b'}
    for variant,h in history.groupby('variant'):
        for ax,key in zip(axes[0],['max_pressure_pa','strip_settlement_mm']):ax.plot(h.time_s,h[key],label='GPU '+variant,color=colors[variant],ls='--' if variant=='faces_half' else '-')
    for (kind,variant),h in compare.groupby(['kind','variant']):
        for ax,key in zip(axes[1],['pressure_rms_pa','max_material_displacement_mm']):
            ax.plot(h.time_s,h[key],label=kind+' '+variant,color=colors.get(variant,'#66743a'),ls=':' if kind=='GPU_half' else '-')
    for ax,title in zip(axes.flat,['Maximum pore pressure (Pa)','Material strip settlement (mm)','Matched pressure RMS difference (Pa)','Maximum matched material displacement (mm)']):
        ax.set(title=title,xlabel='Actual saved time (s)');ax.xaxis.set_major_locator(MaxNLocator(5));ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[1,0].axhline(5,color='.3',ls=':',lw=1);axes[1,1].axhline(.005,color='.3',ls=':',lw=1)
    fig.suptitle('GPU multi-plane Yao %.2f s: CPU comparison and independent GPU half step'%duration)
    fig.tight_layout(rect=(0,.05,1,.95));fig.text(.5,.015,'HG/NoPen off; existing 59/61-node strict strip. Short numerical checks, not 2-D theory/long-cycle acceptance.',ha='center',fontsize=9)
    path=Path(str(stem)+'_history.png');assert not path.exists();fig.savefig(path,dpi=170);plt.close(fig);outputs.append(path)
    result=dict(passed=passed,frames_per_variant=count,actual_final_times_s={k:float(v.time_s.iloc[0]) for k,v in finals.items()},
        same_backend_reference=ref_tag,matching_native_samples_0ulp=prefix,metadata=metadata,
        comparison_maxima=compare.groupby(['kind','variant'])[['pressure_rms_pa','max_material_displacement_mm','total_stress_rms_pa','force_difference_N_m']].max().reset_index().to_dict('records'),
        loop_seconds={r['variant']:r['completion']['loop_seconds'] for r in run['runs']},cpu_control=cpu_tag,cpu_loop_seconds={r['variant']:r['completion']['loop_seconds'] for r in cpu['runs']},
        output_only_pre_telemetry_reference=old_tag,pre_telemetry_nonload_fields_0ulp=old_physical_0ulp,
        controlled_speed_benchmark=False,physical_acceptance=False,visual_inspected=False,evidence=evidence,outputs=[bound(p) for p in outputs])
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','outputs')},indent=2));assert passed,'Original comparison/half limits failed'


if __name__=='__main__':main()
