"""Offline whole-history 10-s native checks, independent GPU half pair and plots."""
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
from spr_yao_10s_run import TAG

REFERENCES={'off':('spr_yao_gpu_post03_r1_faces_off',30),'on':('spr_yao_cpu_gpu_1s_r1_gpu_c',100),'half':('spr_yao_cpu_gpu_1s_r1_gpu_h',100)}


def load():
    r=json.loads((TESTS/'logs'/(TAG+'.status.json')).read_text())
    for item in r['inputs']:assert bound(item['path'])['sha256']==item['sha256'],item['path']
    return r


def output(key,value):
    with (TESTS/'logs'/(TAG+'_'+key+'.check.json')).open('x',encoding='utf8') as f:json.dump(value,f,indent=2)
    print(json.dumps({k:v for k,v in value.items() if k not in ('evidence','outputs')},indent=2),flush=True)


def single(key):
    r=load();entry=next(x for x in r['runs'] if x['key']==key);done=entry['completion']
    frozen=TESTS/'logs'/(TAG+'_'+key+'.run.json');saved=json.loads(frozen.read_text());assert saved['run']==entry and saved['inputs']==r['inputs']
    assert entry['exit_code']==0 and entry['owned_exited'] and done['completed']
    for item in entry['outputs']:assert bound(item['path'])['sha256']==item['sha256']
    dt=1e-5 if key=='half' else 2e-5
    assert done['steps']==round(10/dt) and done['dt_s']==dt and done['saved_frames']==1001 and done['native_count']==21945
    assert abs(done['actual_time_s']-10)<1e-8 and dt<=done['pore_dt_limit_s']
    folder=TESTS/'outputs'/(TAG+'_'+key);initial=native(folder,0);assert len(initial)==20301 and initial.id.is_unique
    metaexe=TESTS/'outputs/read_meta_r1/ReadPartMetadata.exe';raw=subprocess.check_output([str(metaexe),str(folder/'data'),'1001'])
    meta=pd.read_csv(io.BytesIO(raw),float_precision='round_trip');active=meta[meta.part.gt(0)]
    assert len(meta)==1001 and meta.native_count.eq(21945).all() and meta.nout.eq(0).all()
    assert active.has_dterror.eq(1).all() and active.dterror_s.between(-1e100,0).all() and active.dt_min_s.eq(dt).all() and active.dt_max_s.eq(dt).all()
    top=np.isclose(initial.z,10,atol=1e-8)&(abs(initial.x)<3-1e-8);core=set(initial.id[top]);assert len(core)==59
    corner=(initial.z<.5)&(abs(initial.x)>9.5);points=[]
    for x,z in ((2,8),(8,2)):
        mask=np.isclose(initial.x,x,atol=1e-8)&np.isclose(initial.z,z,atol=1e-8);assert mask.sum()==1;points.append(int(initial.id[mask].iloc[0]))
    reference,last=REFERENCES[key];rows=[];prefix=0
    for i in range(1001):
        a=native(folder,i);t=float(a.time_s.iloc[0]);context=(key,i,t)
        assert abs(t-i*.01)<1e-8 and np.array_equal(a.id,initial.id),context
        assert np.isfinite(a.to_numpy()).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.load_available.eq(1).all(),context
        assert a.x.between(-10.0001,10.0001).all() and a.z.ge(-.0001).all(),(context,'Original geometry gate')
        loaded=set(a.id[abs(a.load_az)>0]);assert (not loaded if i==0 else core.issubset(loaded) and loaded.issubset(core|{8814,14874})),(context,'Original loaded native set')
        q=5000*min(1,max(0,t-dt)/.1) if i else 0;force=float(17*a.load_az.sum());expected=-17*float(np.float32(q/170))*len(loaded)
        assert abs(force-expected)<.002,(context,'Discrete native force',force,expected)
        drained=a.fstype.isin([2,3])&~a.x.between(-3,3);assert a.pressure[drained].eq(0).all(),(context,'Drainage')
        if i<=last:
            b=native(TESTS/'outputs'/reference,i*10);assert exact_fields(a,b),(context,'Shared-cadence prefix not 0 ULP');prefix+=1
        at=a.set_index('id')
        rows.append(dict(time_s=t,max_pressure_pa=float(a.pressure.max()),mean_pressure_pa=float(a.pressure.mean()),
            strip_settlement_mm=float(((initial.z-a.z)*1000)[top].mean()),max_total_stress_pa=float(abs(a.sigma_zz-a.pressure).max()),
            corner_pressure_rms_pa=float(np.sqrt(np.mean(a.pressure[corner]**2))),force_N_m=force,loaded_count=len(loaded),
            A_id=points[0],B_id=points[1],A_pressure_over_q0=float(at.loc[points[0],'pressure']/5000),B_pressure_over_q0=float(at.loc[points[1],'pressure']/5000)))
        if i%100==0:print('Native gate',key,i,'/1000',flush=True)
    assert prefix==last+1
    history=TESTS/'figures'/(TAG+'_'+key+'_history.csv');pd.DataFrame(rows).to_csv(history,index=False,mode='x')
    mp=TESTS/'figures'/(TAG+'_'+key+'_metadata.csv');assert not mp.exists();mp.write_bytes(raw)
    output(key,dict(passed=True,samples=1001,soil_count=20301,actual_final_time_s=done['actual_time_s'],shared_cadence_prefix_0ulp=prefix,reference=reference,
        mechanical_limit_min_s=float(dt-active.dterror_s.max()),pore_limit_s=done['pore_dt_limit_s'],physical_acceptance=False,
        evidence=[bound(__file__),bound(frozen)],outputs=[bound(history),bound(mp)]))


def pair():
    load();evidence=[]
    for key in ('off','on','half'):
        path=TESTS/'logs'/(TAG+'_'+key+'.check.json');assert json.loads(path.read_text())['passed'];evidence.append(bound(path))
    rows=[]
    for i in range(1001):
        frames={k:native(TESTS/'outputs'/(TAG+'_'+k),i) for k in ('off','on','half')}
        for kind,key in [('SPR_on_off','off'),('half','half')]:
            a,b=frames['on'],frames[key];assert np.array_equal(a.id,b.id) and abs(a.time_s.iloc[0]-b.time_s.iloc[0])<1e-8
            p=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)));u=float(np.linalg.norm(a[['x','z']].to_numpy()-b[['x','z']].to_numpy(),axis=1).max()*1000)
            force=float(17*(a.load_az.sum()-b.load_az.sum()))
            if kind=='half':assert p<=5 and u<=.005,(i,float(a.time_s.iloc[0]),p,u,'Original half bounds')
            else:assert abs(force)<.002,(i,'SPR off/on same-dt force differs',force)
            rows.append(dict(kind=kind,time_s=float(a.time_s.iloc[0]),pressure_rms_pa=p,material_max_mm=u,
                total_stress_rms_pa=float(np.sqrt(np.mean(((a.sigma_zz-a.pressure)-(b.sigma_zz-b.pressure))**2))),force_difference_N_m=force))
        if i%100==0:print('Pair gate',i,'/1000',flush=True)
    a=pd.DataFrame(rows);half=a[a.kind.eq('half')];csv=TESTS/'figures'/(TAG+'_comparison.csv');a.to_csv(csv,index=False,mode='x')
    output('pair',dict(passed=True,half_samples=1001,pressure_rms_max_pa=float(half.pressure_rms_pa.max()),material_max_mm=float(half.material_max_mm.max()),
        total_stress_rms_max_pa=float(half.total_stress_rms_pa.max()),physical_acceptance=False,evidence=evidence,outputs=[bound(csv)]))


def final():
    r=load();evidence=[]
    for key in ('off','on','half','pair'):
        path=TESTS/'logs'/(TAG+'_'+key+'.check.json');a=json.loads(path.read_text());assert a['passed'];evidence.append(bound(path))
        for item in a['outputs']:assert bound(item['path'])['sha256']==item['sha256']
    hist={k:pd.read_csv(TESTS/'figures'/(TAG+'_'+k+'_history.csv'),float_precision='round_trip') for k in ('off','on','half')}
    comparisons=pd.read_csv(TESTS/'figures'/(TAG+'_comparison.csv'),float_precision='round_trip');h=comparisons[comparisons.kind.eq('half')]
    fig,axes=plt.subplots(4,2,figsize=(12,13));colors={'off':'#696969','on':'#2166a5','half':'#b18b2b'}
    for key,a in hist.items():
        for ax,col,scale in zip(axes[:3].flat,['max_pressure_pa','strip_settlement_mm','max_total_stress_pa','corner_pressure_rms_pa','A_pressure_over_q0','B_pressure_over_q0'],[1000,1,1000,1000,1,1]):
            ax.plot(a.time_s,a[col]/scale,label=key,color=colors[key],ls='--' if key=='half' else '-')
    for ax,col in zip(axes[3],['pressure_rms_pa','material_max_mm']):ax.plot(h.time_s,h[col],label='GPU on vs half',color='#2166a5')
    for ax,title in zip(axes.flat,['Maximum pore pressure (kPa)','59 original materials: settlement (mm)','Maximum vertical total stress (kPa)',
        'Bottom-corner pressure RMS (kPa)','A (2,8 m): native material pressure / q0','B (8,2 m): native material pressure / q0','Half pressure RMS (Pa); limit = 5','Half material movement (mm); limit = 0.005']):
        ax.set(title=title,xlabel='Actual saved time (s)',xlim=(0,10));ax.axvline(.1,color='.65',ls=':',lw=1);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Yao 10-s GPU SPR same-physics comparison');fig.tight_layout(rect=(0,.04,1,.97))
    fig.text(.5,.012,'Original nodal quadrature retained; HG/NoPen off. Sampled .01 s; initial dense controls retained. Not an independent theory reference.',ha='center',fontsize=9)
    png=TESTS/'figures'/(TAG+'_history.png');assert not png.exists();fig.savefig(png,dpi=150);plt.close(fig)
    output('final',dict(passed=True,physical_acceptance=False,visual_inspected=False,loops_s={x['key']:x['completion']['loop_seconds'] for x in r['runs']},
        final_histories={k:a.iloc[-1].to_dict() for k,a in hist.items()},evidence=evidence,outputs=[bound(png)]))


if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--single',choices=['off','on','half']);g.add_argument('--pair',action='store_true');g.add_argument('--final',action='store_true');a=p.parse_args()
    if a.single:single(a.single)
    elif a.pair:pair()
    else:final()
