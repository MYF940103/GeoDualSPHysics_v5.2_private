"""Compare completed same-physics CPU/GPU native 3-D pulse trajectories."""
import argparse
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from spr_planes_run import TESTS,bound


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--geometry',choices=['edge3','corner3'],default='edge3');p.add_argument('--slip',type=int,choices=[2,3],default=3);a=p.parse_args()
    tag=f'spr_3d_r1_{a.geometry}_s{a.slip}';receipt=TESTS/'logs'/(tag+'.review.json');assert not receipt.exists()
    snapshot=TESTS/'logs/spr_3d_precleanup_r1.snapshot.json'
    archived=json.loads(snapshot.read_text())['files']
    evidence=[bound(__file__),bound(snapshot)];frames={};histories=[];energy_ratios={};cross=[]
    def verify(item):
        if bound(item['path'])['sha256']==item['sha256']:return
        old=[x for x in archived if x['original_path']==item['path'] and x['sha256']==item['sha256']]
        assert len(old)==1 and bound(old[0]['archive_path'])['sha256']==item['sha256'],item['path']
    for backend in ['cpu','gpu']:
        status=TESTS/'logs'/(tag+'_'+backend+'.status.json');r=json.loads(status.read_text());assert r['passed'] and len(r['runs'])==2
        evidence.append(bound(status))
        for item in r['inputs']+r['outputs']:verify(item)
        for run in r['runs']:
            assert run['exit_code']==0 and run['owned_exited']
            for item in run['outputs']+run['generated_inputs']+[run['definition'],run['log'],run['gencase_log']]:assert bound(item['path'])['sha256']==item['sha256'],item['path']
            phase=run['name'][-1];folder=TESTS/'outputs'/run['name'];f=pd.read_csv(folder/'pulse.csv',float_precision='round_trip').sort_values(['step','id']).reset_index(drop=True)
            frames[backend,phase]=f;energy=pd.read_csv(folder/'energy.csv',float_precision='round_trip');energy_ratios[backend+'_'+phase]=float(energy.total_J.max()/energy.total_J.iloc[0])
            n=int(f.step.eq(0).sum());initial=f.iloc[:n];pos=f[['x','y','z']].to_numpy().reshape(201,n,3)
            h=pd.DataFrame(dict(time_s=f.time_s.to_numpy()[::n],pressure_mean_pa=f.pressure.to_numpy().reshape(201,n).mean(axis=1),pressure_max_pa=f.pressure.to_numpy().reshape(201,n).max(axis=1),
                movement_max_mm=np.linalg.norm(pos-pos[0],axis=2).max(axis=1)*1000,energy_over_initial=energy.total_J/energy.total_J.iloc[0],backend=backend,phase=phase))
            histories.append(h)
    for phase in ['c','h']:
        c,g=frames['cpu',phase],frames['gpu',phase];assert np.array_equal(c.id,g.id) and abs(c.time_s-g.time_s).max()<1e-11
        n=int(c.step.eq(0).sum());dp=(c.pressure.to_numpy()-g.pressure.to_numpy()).reshape(201,n)
        move=np.linalg.norm(c[['x','y','z']].to_numpy()-g[['x','y','z']].to_numpy(),axis=1).reshape(201,n)*1000
        t=pd.DataFrame(dict(time_s=c.time_s.to_numpy()[::n],phase=phase,pressure_rms_pa=np.sqrt(np.mean(dp*dp,axis=1)),material_max_mm=move.max(axis=1)))
        assert t.pressure_rms_pa.le(.5).all() and t.material_max_mm.le(1e-5).all();cross.append(t)
    cross=pd.concat(cross,ignore_index=True);histories=pd.concat(histories,ignore_index=True);outputs=[]
    for name,f in [('cross',cross),('history',histories)]:
        path=TESTS/'figures'/(tag+'_'+name+'.csv');f.to_csv(path,index=False,mode='x');outputs.append(bound(path))
    fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
    for (backend,phase),f in histories.groupby(['backend','phase']):
        color='#2166a5' if backend=='cpu' else '#b18b2b';style='-' if phase=='c' else '--'
        for ax,col,label in zip(axes.flat[:4],['pressure_mean_pa','pressure_max_pa','movement_max_mm','energy_over_initial'],['Mean pressure (Pa)','Maximum pressure (Pa)','3-D displacement max (mm)','Approximate energy / initial']):
            ax.plot(f.time_s*1000,f[col],color=color,ls=style,label=backend+' '+phase);ax.set(xlabel='Actual time (ms)',ylabel=label);ax.grid(alpha=.2)
    for phase,f in cross.groupby('phase'):
        for ax,col,label in zip(axes.flat[4:],['pressure_rms_pa','material_max_mm'],['CPU/GPU pressure RMS (Pa)','CPU/GPU 3-D displacement difference (mm)']):
            ax.plot(f.time_s*1000,f[col],ls='-' if phase=='c' else '--',color='#2166a5' if phase=='c' else '#b18b2b',label=phase);ax.set(xlabel='Actual time (ms)',ylabel=label);ax.grid(alpha=.2)
    for ax in axes.flat:ax.legend(fontsize=8)
    fig.suptitle(f'3-D {a.geometry}, SlipMode={a.slip}: bounded 2-ms production-step check; HG/NoPen off')
    path=TESTS/'figures'/(tag+'_history.png');assert not path.exists();fig.savefig(path,dpi=150);plt.close(fig);outputs.append(bound(path))
    initial=frames['cpu','c'].query('step==0').sort_values('id');last={k:v[v.step.eq(v.step.max())].sort_values('id') for k,v in frames.items()}
    field=initial[['id','x','y','z']].copy().rename(columns={c:c+'0_m' for c in ['x','y','z']})
    for (backend,phase),f in last.items():field[backend+'_'+phase+'_pressure_pa']=f.pressure.to_numpy()
    slice_=field[np.isclose(field.y0_m,.005,atol=1e-10)].copy();assert len(slice_)==100
    path=TESTS/'figures'/(tag+'_slice.csv');slice_.to_csv(path,index=False,mode='x');outputs.append(bound(path))
    fig,axes=plt.subplots(1,3,figsize=(11,3.7),layout='constrained');values=[slice_.cpu_c_pressure_pa,slice_.gpu_c_pressure_pa,slice_.gpu_c_pressure_pa-slice_.cpu_c_pressure_pa]
    for i,(ax,v,title) in enumerate(zip(axes,values,['CPU coarse','GPU coarse','GPU minus CPU'])):
        kw=dict(cmap='viridis',vmin=min(values[0].min(),values[1].min()),vmax=max(values[0].max(),values[1].max())) if i<2 else dict(cmap='PuOr',vmin=-max(abs(v).max(),1e-10),vmax=max(abs(v).max(),1e-10))
        dots=ax.scatter(slice_.x0_m,slice_.z0_m,c=v,s=25,marker='s',**kw);fig.colorbar(dots,ax=ax,label='Pressure (Pa)');ax.set(title=title,xlabel='Initial x (m)',ylabel='Initial z (m)',aspect='equal')
    fig.suptitle('Native material slice y0=0.005 m, actual t=2 ms; no interpolation')
    path=TESTS/'figures'/(tag+'_slice.png');assert not path.exists();fig.savefig(path,dpi=150);plt.close(fig);outputs.append(bound(path))
    result=dict(passed=True,visual_inspected=False,physical_acceptance=False,samples_per_pair=201,cross_pressure_rms_max_pa=float(cross.pressure_rms_pa.max()),cross_material_max_mm=float(cross.material_max_mm.max()),
        energy_ratios=energy_ratios,evidence=evidence,outputs=outputs,limitations=['2-ms static planar elastic only; not full 3D consolidation or theory reference','No HG/NoPen/plasticity/curves/motion/restart acceptance'])
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','outputs')},indent=2))


if __name__=='__main__':main()
