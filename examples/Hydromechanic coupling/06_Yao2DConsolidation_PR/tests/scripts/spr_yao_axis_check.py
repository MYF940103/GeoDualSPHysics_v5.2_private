"""Whole-history native gates for axis-NoPen; never starts a physical solver."""
import argparse
import io
import json
import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from spr_yao_short import TESTS,bound
from spr_yao_review import native
from spr_yao_axis_run import TAG


def load():
    r=json.loads((TESTS/'logs'/(TAG+'.status.json')).read_text())
    for item in r['inputs']:assert bound(item['path'])['sha256']==item['sha256'],item['path']
    return r


def output(key,value):
    with (TESTS/'logs'/(TAG+'_'+key+'.check.json')).open('x',encoding='utf8') as f:json.dump(value,f,indent=2)
    print(json.dumps({k:v for k,v in value.items() if k not in ('evidence','outputs')},indent=2),flush=True)


def single(key):
    r=load();entry=next(x for x in r['runs'] if x['key']==key);done=entry['completion']
    frozen=TESTS/'logs'/(TAG+'_'+key+'.run.json');saved=json.loads(frozen.read_text())
    assert saved['run']==entry and saved['inputs']==r['inputs']
    assert entry['exit_code']==0 and entry['owned_exited'] and done['completed'] and done['no_penetration'] and done['spr']
    for item in entry['outputs']:assert bound(item['path'])['sha256']==item['sha256']
    dt=1e-5 if key=='gpu_h' else 2e-5
    assert done['saved_frames']==101 and done['native_count']==21945 and done['steps']==round(.1/dt) and done['dt_s']==dt
    assert abs(done['actual_time_s']-.1)<1e-10 and dt<=done['pore_dt_limit_s']
    folder=TESTS/'outputs'/(TAG+'_'+key);initial=native(folder,0);assert len(initial)==20301 and initial.id.is_unique
    log=(folder/'Run.out').read_text(errors='replace');assert 'No Penetration' in log and 'SPR stationary wall planes (one per mk): 3' in log
    reader=TESTS/'outputs/read_meta_r1/ReadPartMetadata.exe'
    raw=subprocess.check_output([str(reader),str(folder/'data'),'101']);meta=pd.read_csv(io.BytesIO(raw),float_precision='round_trip');active=meta[meta.part.gt(0)]
    assert len(meta)==101 and meta.native_count.eq(21945).all() and meta.nout.eq(0).all()
    assert active.has_dterror.eq(1).all() and active.dterror_s.between(-1e100,0).all() and active.dt_min_s.eq(dt).all() and active.dt_max_s.eq(dt).all()
    top=np.isclose(initial.z,10,atol=1e-8)&(abs(initial.x)<3-1e-8);core=set(initial.id[top]);assert len(core)==59
    corner=(initial.z<.5)&(abs(initial.x)>9.5);rows=[]
    for i in range(101):
        a=native(folder,i);t=float(a.time_s.iloc[0]);context=(key,i,t)
        assert abs(t-i*.001)<1e-10 and np.array_equal(a.id,initial.id),context
        assert np.isfinite(a.to_numpy()).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.load_available.eq(1).all(),context
        assert a.x.between(-10.0001,10.0001).all() and a.z.ge(-.0001).all(),(context,'Wall geometry')
        loaded=set(a.id[abs(a.load_az)>0]);assert (not loaded if i==0 else core.issubset(loaded) and loaded.issubset(core|{8814,14874})),(context,'Loaded native set')
        q=5000*min(1,max(0,t-dt)/.1) if i else 0;force=float(17*a.load_az.sum());target=-17*float(np.float32(q/170))*len(loaded)
        assert abs(force-target)<.002,(context,'Original discrete force',force,target)
        drained=a.fstype.isin([2,3])&~a.x.between(-3,3);assert a.pressure[drained].eq(0).all(),(context,'Drainage')
        control=native(TESTS/'outputs'/('spr_yao_cpu_gpu_1s_r1_'+key),i)
        assert np.array_equal(a.id,control.id) and abs(t-control.time_s.iloc[0])<1e-10
        dp=a.pressure-control.pressure;ds=(a.sigma_zz-a.pressure)-(control.sigma_zz-control.pressure)
        rows.append(dict(time_s=t,max_pressure_pa=float(a.pressure.max()),strip_settlement_mm=float(((initial.z-a.z)*1000)[top].mean()),
            max_total_stress_pa=float(abs(a.sigma_zz-a.pressure).max()),corner_pressure_rms_pa=float(np.sqrt(np.mean(a.pressure[corner]**2))),
            force_N_m=force,loaded_count=len(loaded),nopen_change_pressure_rms_pa=float(np.sqrt(np.mean(dp**2))),
            nopen_change_stress_rms_pa=float(np.sqrt(np.mean(ds**2))),
            nopen_change_material_max_mm=float(np.linalg.norm(a[['x','z']].to_numpy()-control[['x','z']].to_numpy(),axis=1).max()*1000)))
    history=TESTS/'figures'/(TAG+'_'+key+'_history.csv');pd.DataFrame(rows).to_csv(history,index=False,mode='x')
    mp=TESTS/'figures'/(TAG+'_'+key+'_metadata.csv');assert not mp.exists();mp.write_bytes(raw)
    output(key,dict(passed=True,actual_final_time_s=done['actual_time_s'],samples=101,soil_count=20301,physical_acceptance=False,
        mechanical_limit_min_s=float(dt-active.dterror_s.max()),pore_limit_s=done['pore_dt_limit_s'],
        evidence=[bound(__file__),bound(frozen)],outputs=[bound(history),bound(mp)]))


def pair(kind):
    load();ka,kb=('cpu_c','gpu_c') if kind=='cross' else ('gpu_c','gpu_h');evidence=[]
    for key in (ka,kb):
        path=TESTS/'logs'/(TAG+'_'+key+'.check.json');assert json.loads(path.read_text())['passed'];evidence.append(bound(path))
    rows=[]
    for i in range(101):
        a,b=[native(TESTS/'outputs'/(TAG+'_'+key),i) for key in (ka,kb)]
        assert np.array_equal(a.id,b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-10
        p=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)));u=float(np.linalg.norm(a[['x','z']].to_numpy()-b[['x','z']].to_numpy(),axis=1).max()*1000)
        force=float(17*(a.load_az.sum()-b.load_az.sum()));assert p<=5 and u<=.005,(kind,i,p,u)
        if kind=='cross':assert abs(force)<.002,(kind,i,'Same-dt backend force',force)
        rows.append(dict(time_s=float(a.time_s.iloc[0]),pressure_rms_pa=p,material_max_mm=u,total_stress_rms_pa=float(np.sqrt(np.mean(((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure))**2))),force_difference_N_m=force))
    a=pd.DataFrame(rows);csv=TESTS/'figures'/(TAG+'_'+kind+'.csv');a.to_csv(csv,index=False,mode='x')
    output(kind,dict(passed=True,samples=101,pressure_rms_max_pa=float(a.pressure_rms_pa.max()),material_max_mm=float(a.material_max_mm.max()),
        total_stress_rms_max_pa=float(a.total_stress_rms_pa.max()),force_difference_abs_max_N_m=float(abs(a.force_difference_N_m).max()),physical_acceptance=False,evidence=evidence,outputs=[bound(csv)]))


def final():
    r=load();evidence=[]
    for key in ('cpu_c','gpu_c','gpu_h','cross','half'):
        path=TESTS/'logs'/(TAG+'_'+key+'.check.json');a=json.loads(path.read_text());assert a['passed'];evidence.append(bound(path))
        for item in a['outputs']:assert bound(item['path'])['sha256']==item['sha256']
    hist={key:pd.read_csv(TESTS/'figures'/(TAG+'_'+key+'_history.csv'),float_precision='round_trip') for key in ('cpu_c','gpu_c','gpu_h')}
    fig,axes=plt.subplots(3,2,figsize=(12,10));colors={'cpu_c':'#696969','gpu_c':'#2166a5','gpu_h':'#b18b2b'}
    for key,h in hist.items():
        for ax,column,scale in zip(axes[:2].flat,['max_pressure_pa','strip_settlement_mm','max_total_stress_pa','corner_pressure_rms_pa'],[1000,1,1000,1000]):ax.plot(h.time_s,h[column]/scale,label=key,color=colors[key],ls='--' if key=='gpu_h' else '-')
    for key in ('cross','half'):
        a=pd.read_csv(TESTS/'figures'/(TAG+'_'+key+'.csv'),float_precision='round_trip')
        for ax,column in zip(axes[2],['pressure_rms_pa','material_max_mm']):ax.plot(a.time_s,a[column],label=key,ls='-' if key=='cross' else '--')
    for ax,title in zip(axes.flat,['Maximum pore pressure (kPa)','59 original top materials: settlement (mm)','Maximum vertical total stress (kPa)',
        'Bottom-corner pressure RMS (kPa)','Matched pressure RMS (Pa); limit = 5','Matched material movement (mm); limit = 0.005']):
        ax.set(title=title,xlabel='Actual saved time (s)',xlim=(0,.1));ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Yao axis-NoPen + SPR 0.1-s bounded review');fig.tight_layout(rect=(0,.04,1,.96))
    fig.text(.5,.015,'Original load unchanged; HG off. NoPen-off differences in CSV are not theory errors. Not long-cycle acceptance.',ha='center',fontsize=9)
    png=TESTS/'figures'/(TAG+'_history.png');assert not png.exists();fig.savefig(png,dpi=150);plt.close(fig)
    output('final',dict(passed=True,physical_acceptance=False,visual_inspected=False,loops_s={x['key']:x['completion']['loop_seconds'] for x in r['runs']},
        evidence=evidence,outputs=[bound(png)]))


if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--single',choices=['cpu_c','gpu_c','gpu_h']);g.add_argument('--pair',choices=['cross','half']);g.add_argument('--final',action='store_true');a=p.parse_args()
    if a.single:single(a.single)
    elif a.pair:pair(a.pair)
    else:final()
