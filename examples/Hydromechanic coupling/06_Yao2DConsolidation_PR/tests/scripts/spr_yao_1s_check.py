"""Native gates for one fresh 1-s CPU/GPU sequence; never starts a solver."""
import argparse
import io
import json
import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from spr_yao_short import TESTS,bound
from spr_yao_review import native
from spr_yao_step_review import exact_fields

TAG='spr_yao_cpu_gpu_1s_r1'
REFERENCE={'cpu_c':'spr_yao_grid10_r1_faces_on','gpu_c':'spr_yao_gpu_post03_r1_faces_on','gpu_h':'spr_yao_gpu_post03_r1_faces_half'}
META=TESTS/'outputs/read_meta_r1/ReadPartMetadata.exe'


def load():
    path=TESTS/'logs'/(TAG+'.status.json');r=json.loads(path.read_text())
    for item in r['inputs']:assert bound(item['path'])['sha256']==item['sha256'],('Changed sequence input',item['path'])
    return r


def output(name,value):
    path=TESTS/'logs'/(TAG+'_'+name+'.check.json');assert not path.exists()
    with path.open('x',encoding='utf8') as stream:json.dump(value,stream,indent=2)
    print(json.dumps({k:v for k,v in value.items() if k not in ('evidence','outputs')},indent=2),flush=True)


def single(key):
    r=load();entry=next(x for x in r['runs'] if x['key']==key);done=entry['completion']
    frozen=TESTS/'logs'/(TAG+'_'+key+'.run.json');saved=json.loads(frozen.read_text())
    assert saved['run']==entry and saved['inputs']==r['inputs']
    assert entry['exit_code']==0 and entry['owned_exited'] and done['completed'] and done['saved_frames']==1001 and done['native_count']==21945
    for item in entry['outputs']:assert bound(item['path'])['sha256']==item['sha256']
    dt=1e-5 if key=='gpu_h' else 2e-5
    assert done['steps']==round(1/dt) and done['dt_s']==dt and abs(done['actual_time_s']-1)<1e-10 and dt<=done['pore_dt_limit_s']
    folder=TESTS/'outputs'/(TAG+'_'+key)
    result=subprocess.run([str(META),str(folder/'data'),'1001'],capture_output=True,check=True)
    meta=pd.read_csv(io.BytesIO(result.stdout),float_precision='round_trip');active=meta[meta.part.gt(0)]
    assert len(meta)==1001 and meta.native_count.eq(21945).all() and meta.nout.eq(0).all()
    assert active.has_dterror.eq(1).all() and active.dterror_s.between(-1e100,0).all() and active.dt_min_s.eq(dt).all() and active.dt_max_s.eq(dt).all()
    initial=native(folder,0);assert len(initial)==20301 and initial.id.is_unique
    top=np.isclose(initial.z,10,atol=1e-8);core=set(initial.id[top&(abs(initial.x)<3-1e-8)]);ends={8814,14874};assert len(core)==59
    corner=(initial.z<.5)&(abs(initial.x)>9.5);rows=[];prefix=0;last_prefix=100 if key=='cpu_c' else 300
    for i in range(1001):
        a=native(folder,i);t=float(a.time_s.iloc[0]);context=(key,i,t)
        assert abs(t-i*.001)<1e-10 and np.array_equal(a.id,initial.id),(context,'Native ID/time mismatch')
        assert np.isfinite(a.to_numpy()).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.load_available.eq(1).all(),(context,'Finite/density/elastic/telemetry gate')
        assert a.x.between(-10.0001,10.0001).all() and a.z.ge(-.0001).all(),(context,'Wall geometry gate')
        loaded=set(a.id[abs(a.load_az)>0]);assert (not loaded if i==0 else core.issubset(loaded) and loaded.issubset(core|ends)),(context,'Loaded native set')
        q=5000*min(1,max(0,t-dt)/.1) if i else 0;force=float(17*a.load_az.sum());target=-17*float(np.float32(q/170))*len(loaded)
        assert abs(force-target)<.002,(context,'Discrete native force',force,target)
        drained=a.fstype.isin([2,3])&~a.x.between(-3,3);assert a.pressure[drained].eq(0).all(),(context,'Drainage gate')
        if i<=last_prefix:
            assert exact_fields(a,native(TESTS/'outputs'/REFERENCE[key],i)),(context,'Same-dt native prefix not 0 ULP')
            prefix+=1
        rows.append(dict(key=key,time_s=t,max_pressure_pa=float(a.pressure.max()),mean_pressure_pa=float(a.pressure.mean()),
            strip_settlement_mm=float(((initial.z-a.z)*1000)[top&(abs(initial.x)<3-1e-8)].mean()),
            corner_pressure_rms_pa=float(np.sqrt(np.mean(a.pressure[corner]**2))),max_total_stress_pa=float(abs(a.sigma_zz-a.pressure).max()),
            max_material_displacement_mm=float(np.linalg.norm(a[['x','z']].to_numpy()-initial[['x','z']].to_numpy(),axis=1).max()*1000),
            force_N_m=force,loaded_count=len(loaded)))
        if i%100==0:print('Native gate',key,i,'/1000',flush=True)
    assert prefix==last_prefix+1
    history=TESTS/'figures'/(TAG+'_'+key+'_history.csv');pd.DataFrame(rows).to_csv(history,index=False,mode='x')
    metapath=TESTS/'figures'/(TAG+'_'+key+'_metadata.csv');assert not metapath.exists();metapath.write_bytes(result.stdout)
    output(key,dict(passed=True,key=key,actual_final_time_s=done['actual_time_s'],samples=1001,soil_count=20301,
        same_dt_prefix_0ulp=prefix,reference=REFERENCE[key],mechanical_limit_min_s=float(dt-active.dterror_s.max()),pore_limit_s=done['pore_dt_limit_s'],
        physical_acceptance=False,evidence=[bound(__file__),bound(frozen),bound(META)],outputs=[bound(history),bound(metapath)]))


def pair(kind):
    r=load();ka,kb=('cpu_c','gpu_c') if kind=='cross' else ('gpu_c','gpu_h')
    evidence=[bound(__file__)]
    for key in (ka,kb):
        path=TESTS/'logs'/(TAG+'_'+key+'.check.json');check=json.loads(path.read_text());assert check['passed']
        for item in check['outputs']:assert bound(item['path'])['sha256']==item['sha256']
        evidence.append(bound(path))
    rows=[]
    for i in range(1001):
        a,b=[native(TESTS/'outputs'/(TAG+'_'+key),i) for key in (ka,kb)]
        assert np.array_equal(a.id,b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-10
        p=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
        u=float(np.linalg.norm(a[['x','z']].to_numpy()-b[['x','z']].to_numpy(),axis=1).max()*1000)
        force=float(17*(a.load_az.sum()-b.load_az.sum()))
        assert p<=5 and u<=.005,(kind,i,float(a.time_s.iloc[0]),p,u,'Original 5-Pa/.005-mm gate')
        if kind=='cross':assert abs(force)<.002,(kind,i,'Same-dt cross-backend load differs',force)
        rows.append(dict(time_s=float(a.time_s.iloc[0]),pressure_rms_pa=p,material_max_mm=u,
            total_stress_rms_pa=float(np.sqrt(np.mean(((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure))**2))),force_difference_N_m=force))
        if i%100==0:print('Pair',kind,i,'/1000',flush=True)
    frame=pd.DataFrame(rows);csv=TESTS/'figures'/(TAG+'_'+kind+'.csv');frame.to_csv(csv,index=False,mode='x')
    output(kind,dict(passed=True,kind=kind,samples=1001,pressure_rms_max_pa=float(frame.pressure_rms_pa.max()),
        material_max_mm=float(frame.material_max_mm.max()),total_stress_rms_max_pa=float(frame.total_stress_rms_pa.max()),
        physical_acceptance=False,evidence=evidence,outputs=[bound(csv)]))


def final():
    r=load();checks=[]
    for key in ('cpu_c','gpu_c','gpu_h','cross','half'):
        path=TESTS/'logs'/(TAG+'_'+key+'.check.json');a=json.loads(path.read_text());assert a['passed'];checks.append(bound(path))
        for item in a['outputs']:assert bound(item['path'])['sha256']==item['sha256']
    hist={key:pd.read_csv(TESTS/'figures'/(TAG+'_'+key+'_history.csv'),float_precision='round_trip') for key in ('cpu_c','gpu_c','gpu_h')}
    pairs={key:pd.read_csv(TESTS/'figures'/(TAG+'_'+key+'.csv'),float_precision='round_trip') for key in ('cross','half')}
    fig,axes=plt.subplots(3,2,figsize=(12,10));colors={'cpu_c':'#696969','gpu_c':'#2166a5','gpu_h':'#b18b2b'}
    for key,h in hist.items():
        for ax,column,scale in zip(axes[:2].flat,['max_pressure_pa','strip_settlement_mm','max_total_stress_pa','corner_pressure_rms_pa'],[1000,1,1000,1000]):
            ax.plot(h.time_s,h[column]/scale,label=key,color=colors[key],ls='--' if key=='gpu_h' else '-')
    for key,a in pairs.items():
        for ax,column in zip(axes[2],['pressure_rms_pa','material_max_mm']):ax.plot(a.time_s,a[column],label=key,color='#2166a5' if key=='cross' else '#b18b2b',ls='-' if key=='cross' else '--')
    for ax,title in zip(axes.flat,['Maximum pore pressure (kPa)','59 original top materials: mean settlement (mm)',
        'Maximum absolute vertical total stress (kPa)','Bottom-corner pore-pressure RMS (kPa)',
        'Matched pressure RMS (Pa); original limit = 5','Matched material movement (mm); limit = 0.005']):
        ax.set(title=title,xlabel='Actual saved time (s)',xlim=(0,1));ax.axvline(.1,color='.65',ls=':',lw=1);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Yao 1-s CPU/GPU same-physics and independent GPU half-step review');fig.tight_layout(rect=(0,.05,1,.96))
    fig.text(.5,.015,'HG/NoPen off; original nodal load retained. Error panels zoomed; all 1001 samples tested. Not full 2-D theory acceptance.',ha='center',fontsize=9)
    png=TESTS/'figures'/(TAG+'_history.png');assert not png.exists();fig.savefig(png,dpi=150);plt.close(fig)
    output('final',dict(passed=True,physical_acceptance=False,visual_inspected=False,evidence=checks,outputs=[bound(png)],
        loops_s={x['key']:x['completion']['loop_seconds'] for x in r['runs']},controlled_speed_benchmark=False,
        limitations=['Original strict strip quadrature, no silent load change','Static convex planes, elastic startup only','No inclined NoPen/curves/motion/plasticity/large rotation/exact HG restart acceptance']))


if __name__=='__main__':
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--run',choices=list(REFERENCE));group.add_argument('--pair',choices=['cross','half']);group.add_argument('--final',action='store_true')
    args=parser.parse_args()
    if args.run:single(args.run)
    elif args.pair:pair(args.pair)
    else:final()
