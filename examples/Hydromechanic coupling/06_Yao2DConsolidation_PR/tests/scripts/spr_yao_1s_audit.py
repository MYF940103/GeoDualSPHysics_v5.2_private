"""Offline 1-s evidence/CSV audit and native material fields; no solver calls."""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from spr_yao_short import TESTS,bound
from spr_yao_review import native
from spr_yao_1s_check import TAG,load


def main():
    receipt=TESTS/'logs'/(TAG+'.audit_r1.json');assert not receipt.exists()
    state=load();assert state['status']=='completed_pending_review'
    evidence=[bound(__file__),bound(TESTS/'logs'/(TAG+'.status.json'))];verified=set()
    def verify(item):
        if item['path'] not in verified:
            assert bound(item['path'])['sha256']==item['sha256'],item['path']
            verified.add(item['path'])
    for item in state['inputs']:verify(item)
    for run in state['runs']:
        assert run['exit_code']==0 and run['owned_exited'] and run['completion']['completed']
        path=TESTS/'logs'/(TAG+'_'+run['key']+'.run.json');frozen=json.loads(path.read_text())
        assert frozen['run']==run and frozen['inputs']==state['inputs'];evidence.append(bound(path))
        for item in run['outputs']+[run['log']]:verify(item)
        print('Verified raw output hashes:',run['key'],flush=True)
    checks={}
    for key in ('cpu_c','gpu_c','gpu_h','cross','half','final'):
        path=TESTS/'logs'/(TAG+'_'+key+'.check.json');c=json.loads(path.read_text());assert c['passed'];checks[key]=c
        for item in c['evidence']+c['outputs']:verify(item)
        evidence.append(bound(path))
    keys=('cpu_c','gpu_c','gpu_h')
    histories={k:pd.read_csv(TESTS/'figures'/(TAG+'_'+k+'_history.csv'),float_precision='round_trip') for k in keys}
    pair_stats={}
    for key in ('cross','half'):
        path=TESTS/'figures'/(TAG+'_'+key+'.csv');a=pd.read_csv(path,float_precision='round_trip')
        assert len(a)==1001 and np.max(abs(a.time_s-np.arange(1001)*.001))<1e-10
        assert a.pressure_rms_pa.le(5).all() and a.material_max_mm.le(.005).all()
        for column,target in [('pressure_rms_pa','pressure_rms_max_pa'),('material_max_mm','material_max_mm'),('total_stress_rms_pa','total_stress_rms_max_pa')]:
            assert float(a[column].max())==checks[key][target]
        force=float(abs(a.force_difference_N_m).max());assert key!='cross' or force<.002
        pair_stats[key]=dict(pressure_rms_max_pa=float(a.pressure_rms_pa.max()),material_max_mm=float(a.material_max_mm.max()),
            total_stress_rms_max_pa=float(a.total_stress_rms_pa.max()),saved_force_difference_max_N_m=force,
            pressure_rms_final_pa=float(a.pressure_rms_pa.iloc[-1]))
    initial=native(TESTS/'outputs'/(TAG+'_gpu_c'),0);assert len(initial)==20301 and initial.id.is_unique
    regions=dict(all=np.ones(len(initial),dtype=bool),near_fixed_wall=(initial.z<.200001)|(abs(initial.x)>9.799999),
        bottom_corner=(initial.z<.5)&(abs(initial.x)>9.5))
    selected=[];finals={}
    for part in (0,100,300,500,750,1000):
        frames={k:native(TESTS/'outputs'/(TAG+'_'+k),part) for k in keys}
        for a in frames.values():assert np.array_equal(a.id,initial.id) and abs(a.time_s.iloc[0]-part*.001)<1e-10
        for kind,ka,kb in (('cross','gpu_c','cpu_c'),('half','gpu_c','gpu_h')):
            a,b=frames[ka],frames[kb]
            for region,mask in regions.items():
                dp=(a.pressure-b.pressure).to_numpy();ds=((a.pressure-a.sigma_zz)-(b.pressure-b.sigma_zz)).to_numpy()
                du=(b.z-a.z).to_numpy()*1000;movement=np.linalg.norm(a[['x','z']].to_numpy()-b[['x','z']].to_numpy(),axis=1)*1000
                selected.append(dict(time_s=float(a.time_s.iloc[0]),part=part,kind=kind,region=region,native_count=int(mask.sum()),
                    pressure_rms_pa=float(np.sqrt(np.mean(dp[mask]**2))),pressure_abs_max_pa=float(abs(dp[mask]).max()),
                    total_compression_rms_pa=float(np.sqrt(np.mean(ds[mask]**2))),settlement_abs_max_mm=float(abs(du[mask]).max()),
                    movement_max_mm=float(movement[mask].max())))
        if part==1000:finals=frames
    regions_csv=TESTS/'figures'/(TAG+'_regions_r1.csv');pd.DataFrame(selected).to_csv(regions_csv,index=False,mode='x')
    on,cpu,fine=[finals[k] for k in ('gpu_c','cpu_c','gpu_h')]
    field=pd.DataFrame(dict(id=initial.id,x0_m=initial.x,z0_m=initial.z,pressure_pa=on.pressure,
        pressure_gpu_cpu_pa=on.pressure-cpu.pressure,pressure_coarse_half_pa=on.pressure-fine.pressure,
        settlement_mm=(initial.z-on.z)*1000,settlement_gpu_cpu_mm=(cpu.z-on.z)*1000,settlement_coarse_half_mm=(fine.z-on.z)*1000,
        total_compression_pa=on.pressure-on.sigma_zz,
        total_compression_gpu_cpu_pa=(on.pressure-on.sigma_zz)-(cpu.pressure-cpu.sigma_zz),
        total_compression_coarse_half_pa=(on.pressure-on.sigma_zz)-(fine.pressure-fine.sigma_zz)))
    fields_csv=TESTS/'figures'/(TAG+'_fields_r1.csv');field.to_csv(fields_csv,index=False,mode='x')
    fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained')
    columns=['GPU coarse','GPU minus CPU (same dt)','GPU coarse minus half dt']
    variables=[['pressure_pa','pressure_gpu_cpu_pa','pressure_coarse_half_pa'],['settlement_mm','settlement_gpu_cpu_mm','settlement_coarse_half_mm'],
        ['total_compression_pa','total_compression_gpu_cpu_pa','total_compression_coarse_half_pa']]
    labels=['Pore pressure (kPa)','Material settlement (mm)','Vertical total compression (kPa)']
    for row in range(3):
        for col in range(3):
            ax=axes[row,col];v=field[variables[row][col]]/(1 if row==1 else 1000);kwargs=dict(cmap='viridis')
            if col:
                limit=max(float(abs(v).max()),1e-14);kwargs=dict(cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit))
            dots=ax.scatter(field.x0_m,field.z0_m,c=v,s=3,marker='s',linewidths=0,rasterized=True,**kwargs)
            ax.set(xlabel='Initial material x (m)',ylabel='Initial material z (m)',xlim=(-10.1,10.1),ylim=(-.1,10.1),aspect='equal')
            ax.set_title(columns[col]+'\n'+labels[row],fontsize=10);fig.colorbar(dots,ax=ax,pad=.04,shrink=.82)
    fig.suptitle('Yao native fields at actual t = 1 s\nIndependent colorbar ranges; same 20301 IDs; HG/NoPen off; not theory-error maps.',fontsize=13)
    fields_png=TESTS/'figures'/(TAG+'_fields_r1.png');assert not fields_png.exists();fig.savefig(fields_png,dpi=150);plt.close(fig)
    metadata={};final_history={}
    for key,h in histories.items():
        assert len(h)==1001 and np.max(abs(h.time_s-np.arange(1001)*.001))<1e-10
        assert h[h.time_s.gt(.1000001)].loaded_count.eq(61).all()
        f=finals[key];top=np.isclose(initial.z,10,atol=1e-8)&(abs(initial.x)<3-1e-8)
        assert np.isclose(h.strip_settlement_mm.iloc[-1],float(((initial.z-f.z)*1000)[top].mean()),rtol=0,atol=1e-15)
        assert h.max_pressure_pa.iloc[-1]==float(f.pressure.max())
        final_history[key]=h.iloc[-1].to_dict()
        path=TESTS/'figures'/(TAG+'_'+key+'_metadata.csv');a=pd.read_csv(path,float_precision='round_trip');active=a[a.part.gt(0)]
        dt=1e-5 if key=='gpu_h' else 2e-5
        assert len(a)==1001 and a.nout.eq(0).all() and a.native_count.eq(21945).all()
        assert active.dt_min_s.eq(dt).all() and active.dt_max_s.eq(dt).all() and active.dterror_s.between(-1e100,0).all()
        metadata[key]=dict(mechanical_limit_min_s=float(dt-active.dterror_s.max()),pore_limit_s=checks[key]['pore_limit_s'])
    loops=checks['final']['loops_s'];ratio=loops['cpu_c']/loops['gpu_c']
    result=dict(passed=True,physical_acceptance=False,visual_inspected=False,verified_unique_hashes=len(verified),
        actual_final_times_s={r['key']:r['completion']['actual_time_s'] for r in state['runs']},native_samples_each=1001,soil_count=20301,
        same_dt_prefix_0ulp={k:checks[k]['same_dt_prefix_0ulp'] for k in keys},pair_stats=pair_stats,final_histories=final_history,
        selected_region_times_only=[0,.1,.3,.5,.75,1],metadata=metadata,loops_s=loops,observed_cpu_gpu_loop_ratio=ratio,
        controlled_speed_benchmark=False,post_ramp_force_N_m=float(histories['gpu_c'].force_N_m.iloc[-1]),
        post_ramp_force_bias_percent=100*(abs(histories['gpu_c'].force_N_m.iloc[-1])/30000-1),
        limitations=['No 1-s SPR-off control (off stops at .3 s)','Original strict 59/61-node load quadrature retained',
            'Static convex planes, elastic, HG/NoPen off; not full 2D theory/long-cycle acceptance'],
        evidence=evidence,outputs=[bound(p) for p in (regions_csv,fields_csv,fields_png)])
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','outputs')},indent=2))


if __name__=='__main__':main()
