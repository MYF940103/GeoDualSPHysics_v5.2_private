"""Native-ID, actual-time four-way short review. No interpolation or solver calls."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import re
import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from spr_yao_short import TESTS,CASE,REPO,TAG,VARIANTS,bound

READER=TESTS/'outputs/read_native_spr_r1/ReadHydroMechPart.exe'


def native(folder,i):
    run=subprocess.run([str(READER),str(folder/'data'),str(i)],capture_output=True,check=True)
    return pd.read_csv(io.BytesIO(run.stdout),float_precision='round_trip')


def vtkpoints(path):
    data=Path(path).read_bytes();match=re.search(rb'POINTS (\d+) float\n',data);assert match
    return np.frombuffer(data,dtype='>f4',count=3*int(match[1]),offset=match.end()).reshape(-1,3).astype(float)


def pointset(a):
    return np.asarray(sorted(map(tuple,a)),dtype='<f8').tobytes()


def main():
    receipt=TESTS/'logs'/(TAG+'.review.json');assert not receipt.exists()
    state=json.loads((TESTS/'logs'/(TAG+'.status.json')).read_text());assert state['status']=='completed_pending_review'
    for x in state['inputs']:assert bound(x['path'])['sha256']==x['sha256']
    arrays={};rows=[];evidence=[bound(READER),bound(__file__),bound(TESTS/'logs'/(TAG+'.status.json'))]
    for variant in VARIANTS:
        folder=TESTS/'outputs'/(TAG+'_'+variant);record=next(x for x in state['runs'] if x['variant']==variant)
        assert record['exit_code']==0 and record['owned_exited']
        for x in record['outputs']:assert bound(x['path'])['sha256']==x['sha256']
        count=len(list((folder/'data').glob('Part_*.bi4')));assert count==21
        with ThreadPoolExecutor(max_workers=2) as pool:arrays[variant]=list(pool.map(lambda i:native(folder,i),range(count)))
        initial=arrays[variant][0];ids=initial.id.to_numpy();top=np.isclose(initial.z,initial.z.max(),atol=1e-8)
        # The two nodal endpoints move outside the strict Eulerian strip before
        # the first positive-load sample. Record that existing quadrature bias;
        # do not count an endpoint from binary64 initial-coordinate roundoff.
        strip=abs(initial.x)<3-1e-8
        for i,a in enumerate(arrays[variant]):
            assert np.array_equal(a.id,ids) and a.load_available.eq(1).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all()
            assert np.isfinite(a.to_numpy()).all()
            assert a.x.ge(-10-.0001).all() and a.x.le(10+.0001).all() and a.z.ge(-.0001).all()
            assert np.array_equal(a[['x','y','z']].to_numpy(),initial[['x','y','z']].to_numpy()) if i==0 else True
            t=float(a.time_s.iloc[0]);dt=1e-5 if variant=='faces_half' else 2e-5
            loaded=abs(a.load_az.to_numpy())>0
            assert not loaded.any() if i==0 else np.array_equal(np.flatnonzero(loaded),np.flatnonzero(top&strip))
            q=5000*max(0,t-dt)/.1 if i else 0
            expected=np.float32(q/(1700*.1));force=float(17*a.load_az.sum())
            assert abs(force+17*expected*loaded.sum())<.002
            drained=a.fstype.isin([2,3])&~((a.x>=-3)&(a.x<=3));assert a.pressure[drained].eq(0).all()
            u=(initial.z-a.z)*1000;corner=(initial.z<.5)&(abs(initial.x)>9.5)
            rows.append(dict(variant=variant,native_part=i,time_s=t,actual_step=0 if i==0 else int(a.saved_step.iloc[0])+1,native_count=len(a),
                mean_pressure_pa=float(a.pressure.mean()),max_pressure_pa=float(a.pressure.max()),strip_settlement_mm=float(u[top&strip].mean()),
                max_material_displacement_mm=float(np.sqrt((a.x-initial.x)**2+(a.z-initial.z)**2).max()*1000),corner_pressure_rms_pa=float(np.sqrt(np.mean(a.pressure[corner]**2))),
                max_total_stress_abs_pa=float(abs(a.sigma_zz-a.pressure).max()),load_N_m=force,loaded_particles=int(loaded.sum()),drained_count=int(drained.sum())))
    baseline=TESTS/'outputs'/(TAG+'_auto_off')
    points=vtkpoints(baseline/(TAG+'_auto_off_Bound.vtk'))
    for variant in VARIANTS[1:]:
        folder=TESTS/'outputs'/(TAG+'_'+variant)
        assert pointset(points)==pointset(vtkpoints(folder/(TAG+'_'+variant+'_Bound.vtk')))
        assert np.array_equal(arrays['auto_off'][0].id,arrays[variant][0].id)
        assert np.array_equal(arrays['auto_off'][0][['x','y','z']],arrays[variant][0][['x','y','z']])
    comparison=[]
    for left,right in [('auto_off','faces_off'),('faces_off','faces_on'),('faces_on','faces_half')]:
        matched=0
        for a in arrays[left]:
            t=float(a.time_s.iloc[0]);options=[b for b in arrays[right] if abs(float(b.time_s.iloc[0])-t)<1e-11]
            if not options:continue
            assert len(options)==1;b=options[0];matched+=1
            comparison.append(dict(left=left,right=right,time_s=t,pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))),
                material_displacement_max_mm=float(np.sqrt((a.x-b.x)**2+(a.z-b.z)**2).max()*1000),stress_zz_rms_pa=float(np.sqrt(np.mean((a.sigma_zz-b.sigma_zz)**2)))))
        assert matched>1
    history=pd.DataFrame(rows);compare=pd.DataFrame(comparison)
    half=compare[compare.right.eq('faces_half')]
    assert half.pressure_rms_pa.le(5).all() and half.material_displacement_max_mm.le(.005).all()
    prefix=TESTS/'figures'/TAG;outputs=[]
    for suffix,data in [('_history.csv',history),('_comparison.csv',compare)]:
        path=Path(str(prefix)+suffix);data.to_csv(path,index=False,mode='x');outputs.append(path)
    fig,axes=plt.subplots(2,2,figsize=(12,8));colors=dict(zip(VARIANTS,['.3','#9b7440','#24649b','#8b803e']))
    for variant,h in history.groupby('variant'):
        for ax,key in zip(axes.flat,['max_pressure_pa','strip_settlement_mm','corner_pressure_rms_pa','load_N_m']):
            ax.plot(h.time_s,h[key],label=variant,color=colors[variant],ls='--' if variant=='faces_half' else '-')
    for ax,title,unit in zip(axes.flat,['Maximum pore pressure','Material top-strip settlement','Bottom-corner pressure RMS','Observed strip-load resultant'],['Pa','mm','Pa','N/m']):
        ax.set(title=title,xlabel='Actual saved time (s)',ylabel=unit);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Yao 2-D CPU 0.02-s startup: load front has not tested late consolidation')
    fig.tight_layout(rect=(0,.05,1,.94));fig.text(.5,.02,'Same native particle point sets; HG/NoPen off. Half differences use actual matching times only; later shifted output frames are excluded.',ha='center',fontsize=9)
    path=Path(str(prefix)+'_history.png');assert not path.exists();fig.savefig(path,dpi=170);plt.close(fig);outputs.append(path)
    result=dict(native_saved_safety_passed=True,geometry_point_sets_equal=True,full_half_window_passed=False,matched_half_samples=len(half),
        matched_half_last_actual_time_s=float(half.time_s.max()),half_pressure_rms_max_pa=float(half.pressure_rms_pa.max()),
        half_material_displacement_max_mm=float(half.material_displacement_max_mm.max()),finals=history.groupby('variant').tail(1).to_dict('records'),
        comparison_maxima=compare.groupby(['left','right'])[['pressure_rms_pa','material_displacement_max_mm','stress_zz_rms_pa']].max().reset_index().to_dict('records'),
        reason='Normal output scheduling overshoots some coarse times by20us/half by10us. No interpolation or whole-window half claim. Next fresh 0.1-s stage uses production-step companion with integer-step sampling.',
        ideal_strip_width_m=6,actual_loaded_nodes=59,discrete_loaded_width_m=5.9,load_width_relative_difference_pct=-100/60,
        endpoint_native_ids=initial.loc[top&(abs(abs(initial.x)-3)<1e-8),'id'].astype(int).tolist(),
        visual_inspected=False,physical_acceptance=False,evidence=evidence,outputs=[bound(p) for p in outputs])
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print({k:v for k,v in result.items() if k not in ('evidence','outputs','finals')})


if __name__=='__main__':main()
