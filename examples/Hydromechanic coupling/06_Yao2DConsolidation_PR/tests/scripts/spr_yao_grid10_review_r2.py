"""Revised offline 0.1-s review: expose Eulerian endpoint switches, keep original half limits."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import Normalize
from spr_yao_short import TESTS,TAG as ORIGINAL,bound
from spr_yao_review import native
from spr_yao_step_run import VARIANTS


def exact_fields(a,b):
    assert np.array_equal(a.id,b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-11
    fields=a.columns.difference(['time_s','saved_step'])
    return a[fields].to_numpy(dtype='<f8').tobytes()==b[fields].to_numpy(dtype='<f8').tobytes()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);parser.add_argument('--reference',default=ORIGINAL);args=parser.parse_args()
    tag=args.tag;assert tag=='spr_yao_grid10_r1'
    artifact=tag+'_review_r2';receipt=TESTS/'logs'/(artifact+'.check.json');assert not receipt.exists()
    statepath=TESTS/'logs'/(tag+'.status.json');state=json.loads(statepath.read_text());assert state['status']=='completed_pending_review'
    referencepath=TESTS/'logs'/(args.reference+'.status.json');reference=json.loads(referencepath.read_text());assert reference['status']=='completed_pending_review'
    evidence=[bound(__file__),bound(statepath),bound(referencepath)]
    for record in (state,reference):
        for item in record['inputs']:assert bound(item['path'])['sha256']==item['sha256']
        for run in record['runs']:
            assert run['exit_code']==0 and run['owned_exited']
            for item in run['outputs']:assert bound(item['path'])['sha256']==item['sha256']
    rows=[];comparison=[];prefixes=[];finals={};endpoints=[];duration=float(state['duration_s']);frames=round(duration/.001)+1
    for variant in VARIANTS:
        folder=TESTS/'outputs'/(tag+'_'+variant);run=next(x for x in state['runs'] if x['variant']==variant);done=run['completion']
        assert done['saved_frames']==frames and done['max_fixed_dt_minus_mechanical_limit_s']<=0 and done['dt_s']<=done['pore_dt_limit_s']
        initial=native(folder,0);assert len(initial)==20301
        top=np.isclose(initial.z,10,atol=1e-8);strip=abs(initial.x)<3-1e-8;loadedids=initial.id[top&strip].to_numpy();assert len(loadedids)==59
        endids=initial.id[top&(abs(abs(initial.x)-3)<1e-8)].to_numpy();assert set(endids)=={8814,14874}
        ref_folder=TESTS/'outputs'/(args.reference+'_'+variant)
        # Read only matching saved endpoints; an event that was saved late in
        # the ordinary program is not manufactured by interpolating two states.
        ref_times={}
        for j in range(len(list((ref_folder/'data').glob('Part_*.bi4')))):
            a=native(ref_folder,j);ref_times[round(float(a.time_s.iloc[0]),10)]=(j,float(a.time_s.iloc[0]))
        prefix=0
        for i in range(frames):
            a=native(folder,i);t=float(a.time_s.iloc[0]);assert abs(t-i*.001)<1e-10
            assert np.array_equal(a.id,initial.id) and np.isfinite(a.to_numpy()).all()
            assert a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.load_available.eq(1).all()
            assert a.x.between(-10.0001,10.0001).all() and a.z.ge(-.0001).all()
            loaded=abs(a.load_az)>0
            if i==0:assert not loaded.any()
            else:
                assert set(loadedids).issubset(set(a.id[loaded]))
                assert set(a.id[loaded]).issubset(set(loadedids)|set(endids))
            # Only the original two strip endpoints may switch. The saved
            # coordinates are corrected endpoints, not exact force-stage points.
            for row in a[a.id.isin(endids)].itertuples():
                endpoints.append(dict(variant=variant,time_s=t,id=int(row.id),x_m=row.x,z_m=row.z,loaded=bool(abs(row.load_az)>0),load_az_m_s2=row.load_az,pressure_pa=row.pressure))
            q=5000*min(1,max(0,t-done['dt_s'])/.1) if i else 0
            force=float(17*a.load_az.sum());target=-17*float(np.float32(q/170))*int(loaded.sum())
            assert abs(force-target)<.002
            drained=a.fstype.isin([2,3])&~a.x.between(-3,3);assert a.pressure[drained].eq(0).all()
            delta=a[['x','z']].to_numpy()-initial[['x','z']].to_numpy();u=(initial.z-a.z)*1000
            near=(initial.z<.5)&(abs(initial.x)>9.5)
            rows.append(dict(variant=variant,time_s=t,actual_step=i*done['stride'],mean_pressure_pa=float(a.pressure.mean()),
                max_pressure_pa=float(a.pressure.max()),min_pressure_pa=float(a.pressure.min()),strip_settlement_mm=float(u[top&strip].mean()),
                max_displacement_mm=float(np.linalg.norm(delta,axis=1).max()*1000),corner_pressure_rms_pa=float(np.sqrt(np.mean(a.pressure[near]**2))),
                max_total_stress_abs_pa=float(abs(a.sigma_zz-a.pressure).max()),force_N_m=force,force_target_N_m=target,
                rho_min=float(a.rho.min()),loaded_count=int(loaded.sum()),drained_count=int(drained.sum()),discrete_loaded_width_m=.1*int(loaded.sum()),ideal_force_N_m=-6*q))
            if round(t,10) in ref_times:
                j,tr=ref_times[round(t,10)];assert abs(tr-t)<1e-11
                assert exact_fields(a,native(ref_folder,j)),(variant,'native prefix differs',i,j);prefix+=1
            if variant!='faces_off':
                other='faces_off' if variant=='faces_on' else 'faces_on';b=native(TESTS/'outputs'/(tag+'_'+other),i)
                assert np.array_equal(a.id,b.id) and abs(t-b.time_s.iloc[0])<1e-10
                comparison.append(dict(left=other,right=variant,time_s=t,pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
                    material_displacement_max_mm=float(np.linalg.norm(a[['x','z']].to_numpy()-b[['x','z']].to_numpy(),axis=1).max()*1000),
                    total_stress_rms_pa=float(np.sqrt(np.mean(((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure))**2)))))
            if i==frames-1:finals[variant]=a
        assert prefix>1;prefixes.append(dict(variant=variant,reference=args.reference,matched_samples=prefix,all_native_fields_0ulp=True))
    history=pd.DataFrame(rows);compare=pd.DataFrame(comparison);half=compare[compare.right.eq('faces_half')]
    half_ok=bool(half.pressure_rms_pa.le(5).all() and half.material_displacement_max_mm.le(.005).all() and len(half)==frames)
    prefix=TESTS/'figures'/artifact;outputs=[]
    for suffix,data in [('_history.csv',history),('_comparison.csv',compare),('_endpoints.csv',pd.DataFrame(endpoints))]+[('_'+key+'_final.csv',value) for key,value in finals.items()]:
        path=Path(str(prefix)+suffix);data.to_csv(path,index=False,mode='x');outputs.append(path)
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    history['rho_min_change']=history.rho_min-1700
    keys=['max_pressure_pa','strip_settlement_mm','corner_pressure_rms_pa','max_total_stress_abs_pa','force_N_m','rho_min_change']
    titles=['Maximum pore pressure (Pa)','Material strip settlement (mm)','Bottom-corner pressure RMS (Pa)','Maximum |total zz stress| (Pa)','Observed strip-load resultant (N/m)','Minimum density minus 1700 (kg/m3)']
    colors={'faces_off':'#696969','faces_on':'#2166a5','faces_half':'#b18b2b'}
    for variant,h in history.groupby('variant'):
        for ax,key in zip(axes.flat,keys):ax.plot(h.time_s,h[key],label=variant,color=colors[variant],ls='--' if variant=='faces_half' else '-')
    for ax,title in zip(axes.flat,titles):
        ax.set(title=title,xlabel='Actual saved time (s)');ax.grid(alpha=.2);ax.legend(fontsize=8)
        ax.xaxis.set_major_locator(MaxNLocator(5));ax.tick_params(labelsize=9)
    fig.suptitle('Yao CPU fixed-face SPR: integer-step matched diagnostic, HG/NoPen off')
    fig.tight_layout(rect=(0,.05,1,.95));fig.text(.5,.015,'Original nodal grid: 59 interior nodes plus 2 switching endpoints; actual load width changes from 5.9 to 6.1 m.',ha='center',fontsize=9)
    path=Path(str(prefix)+'_history.png');assert not path.exists();fig.savefig(path,dpi=160);plt.close(fig);outputs.append(path)
    fig,axes=plt.subplots(1,3,figsize=(14,5),layout='constrained');a=finals['faces_on'];b=finals['faces_off']
    for ax,values,title in zip(axes,[a.pressure,a.pressure-b.pressure,(a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure)],
                              ['SPR-on pore pressure (Pa)','SPR on - off pore pressure (Pa)','SPR on - off total zz stress (Pa)']):
        scale=max(float(abs(values).max()),1e-12)
        sc=ax.scatter(a.x,a.z,c=values,s=3,cmap='viridis' if ax is axes[0] else 'coolwarm',norm=None if ax is axes[0] else Normalize(-scale,scale));fig.colorbar(sc,ax=ax,shrink=.75)
        ax.set(title=title,xlabel='x (m)',ylabel='z (m)',aspect='equal')
    fig.suptitle('Final actual time %.8f s; all %d native soil particles'%(float(a.time_s.iloc[0]),len(a)))
    path=Path(str(prefix)+'_fields.png');assert not path.exists();fig.savefig(path,dpi=160);plt.close(fig);outputs.append(path)
    result=dict(saved_native_safety_passed=True,whole_window_half_passed=half_ok,half_samples=len(half),prefixes=prefixes,
        half_pressure_rms_max_pa=float(half.pressure_rms_pa.max()),half_material_displacement_max_mm=float(half.material_displacement_max_mm.max()),
        maxima=compare.groupby(['left','right'])[['pressure_rms_pa','material_displacement_max_mm','total_stress_rms_pa']].max().reset_index().to_dict('records'),
        finals=history.groupby('variant').tail(1).to_dict('records'),loop_seconds={r['variant']:r['completion']['loop_seconds'] for r in state['runs']},
        actual_loaded_width_range_m=[float(history.discrete_loaded_width_m.min()),float(history.discrete_loaded_width_m.max())],ideal_loaded_width_m=6,
        load_membership_policy='59 fixed interior plus only the two original strict-footprint endpoint IDs; exact force-stage positions were not saved',
        first_61_sample_s={v:float(h.loc[h.loaded_count.eq(61),'time_s'].min()) for v,h in history.groupby('variant')},
        comparison_not_equal_force_after_endpoint_switch=True,
        actual_final_times_s={key:float(value.time_s.iloc[0]) for key,value in finals.items()},
        physical_acceptance=False,visual_inspected=False,evidence=evidence,outputs=[bound(x) for x in outputs])
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print({k:v for k,v in result.items() if k not in ('finals','evidence','outputs')});assert half_ok,'Original half limits failed'


if __name__=='__main__':main()
