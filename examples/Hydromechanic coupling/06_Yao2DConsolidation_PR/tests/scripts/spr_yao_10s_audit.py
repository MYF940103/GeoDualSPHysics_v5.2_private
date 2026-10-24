"""Offline provenance, material fields/profiles and bounded 10-s SPR review."""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from spr_yao_short import TESTS,REPO,bound
from spr_yao_review import native
from spr_yao_step_review import exact_fields
from spr_yao_10s_check import TAG,REFERENCES,load

KEYS=('off','on','half')
COLORS={'off':'#696969','on':'#2166a5','half':'#b18b2b'}


def main():
    receipt=TESTS/'logs'/(TAG+'.audit_r1.json');assert not receipt.exists()
    r=load();assert r['status']=='completed_pending_review';verified=set();evidence=[bound(__file__),bound(TESTS/'logs'/(TAG+'.status.json'))]
    def verify(item):
        if item['path'] not in verified:
            assert bound(item['path'])['sha256']==item['sha256'],item['path'];verified.add(item['path'])
    for item in r['inputs']:verify(item)
    for run in r['runs']:
        assert run['exit_code']==0 and run['owned_exited'] and run['completion']['completed']
        path=TESTS/'logs'/(TAG+'_'+run['key']+'.run.json');frozen=json.loads(path.read_text())
        assert frozen['run']==run and frozen['inputs']==r['inputs'];evidence.append(bound(path))
        for item in run['outputs']+[run['log']]:verify(item)
        print('Raw run hashes verified:',run['key'],flush=True)
    checks={}
    for key in (*KEYS,'pair','final'):
        path=TESTS/'logs'/(TAG+'_'+key+'.check.json');c=json.loads(path.read_text());assert c['passed'];checks[key]=c
        for item in c['evidence']+c['outputs']:verify(item)
        evidence.append(bound(path))
    histories={k:pd.read_csv(TESTS/'figures'/(TAG+'_'+k+'_history.csv'),float_precision='round_trip') for k in KEYS}
    comparison=pd.read_csv(TESTS/'figures'/(TAG+'_comparison.csv'),float_precision='round_trip');half=comparison[comparison.kind.eq('half')]
    assert len(half)==1001 and half.pressure_rms_pa.le(5).all() and half.material_max_mm.le(.005).all()
    for col,field in [('pressure_rms_pa','pressure_rms_max_pa'),('material_max_mm','material_max_mm'),('total_stress_rms_pa','total_stress_rms_max_pa')]:assert float(half[col].max())==checks['pair'][field]
    offon=comparison[comparison.kind.eq('SPR_on_off')];assert len(offon)==1001 and abs(offon.force_difference_N_m).max()<.002
    prefixes={};metadata={}
    for key in KEYS:
        folder=TESTS/'outputs'/(TAG+'_'+key);reference,last=REFERENCES[key];prefixes[key]=0
        for i in range(last+1):
            assert exact_fields(native(folder,i),native(TESTS/'outputs'/reference,i*10)),(key,i,'Shared-cadence native prefix')
            prefixes[key]+=1
        assert prefixes[key]==checks[key]['shared_cadence_prefix_0ulp']
        path=TESTS/'figures'/(TAG+'_'+key+'_metadata.csv');a=pd.read_csv(path,float_precision='round_trip');active=a[a.part.gt(0)]
        dt=1e-5 if key=='half' else 2e-5
        assert len(a)==1001 and a.nout.eq(0).all() and a.native_count.eq(21945).all()
        assert active.has_dterror.eq(1).all() and active.dterror_s.between(-1e100,0).all() and active.dt_min_s.eq(dt).all() and active.dt_max_s.eq(dt).all()
        metadata[key]=dict(mechanical_limit_min_s=float(dt-active.dterror_s.max()),pore_limit_s=checks[key]['pore_limit_s'])
        assert metadata[key]['mechanical_limit_min_s']>dt and metadata[key]['pore_limit_s']>=dt
        evidence.append(bound(path));print('Prefix/metadata verified:',key,prefixes[key],flush=True)
    initial=native(TESTS/'outputs'/(TAG+'_on'),0);assert len(initial)==20301 and initial.id.is_unique
    bottom=np.isclose(initial.z,0,atol=1e-8);side=np.isclose(abs(initial.x),10,atol=1e-8);top=np.isclose(initial.z,10,atol=1e-8)&(abs(initial.x)<3-1e-8)
    assert bottom.sum()==201 and side.sum()==202 and top.sum()==59
    regions=dict(all=np.ones(len(initial),dtype=bool),near_fixed_wall=(initial.z<.200001)|(abs(initial.x)>9.799999),
        bottom_corner=(initial.z<.5)&(abs(initial.x)>9.5),loaded_top_band=(abs(initial.x)<2.000001)&initial.z.ge(8))
    frames={};region_rows=[];boundary=[];profiles=[];selected=(10,100,300,500,800,1000)
    for part in selected:
        pack={key:native(TESTS/'outputs'/(TAG+'_'+key),part) for key in KEYS};frames[part]=pack
        for a in pack.values():assert np.array_equal(a.id,initial.id) and abs(a.time_s.iloc[0]-part*.01)<1e-8
        for kind,other in [('SPR_on_off','off'),('half','half')]:
            a,b=pack['on'],pack[other];dp=(a.pressure-b.pressure).to_numpy();ds=((a.pressure-a.sigma_zz)-(b.pressure-b.sigma_zz)).to_numpy()
            du=(b.z-a.z).to_numpy()*1000;movement=np.linalg.norm(a[['x','z']].to_numpy()-b[['x','z']].to_numpy(),axis=1)*1000
            for region,mask in regions.items():region_rows.append(dict(time_s=float(a.time_s.iloc[0]),part=part,kind=kind,region=region,native_count=int(mask.sum()),
                pressure_rms_pa=float(np.sqrt(np.mean(dp[mask]**2))),pressure_abs_max_pa=float(abs(dp[mask]).max()),
                total_compression_rms_pa=float(np.sqrt(np.mean(ds[mask]**2))),settlement_abs_max_mm=float(abs(du[mask]).max()),movement_max_mm=float(movement[mask].max())))
        for key,a in pack.items():
            total=(a.pressure-a.sigma_zz).to_numpy();coefficients=[]
            for x in np.arange(-20,21)*.1:
                ids=np.flatnonzero(np.isclose(initial.x,x,atol=1e-8)&initial.z.between(7.999999,9.800001))
                ids=ids[np.argsort(initial.z.iloc[ids])];assert len(ids)==19
                zz=initial.z.iloc[ids].to_numpy();design=np.column_stack([np.ones(len(ids)),zz]);parity=(-1.)**np.arange(len(ids))
                parity-=design@np.linalg.lstsq(design,parity,rcond=None)[0]
                coefficients.append(float(parity@total[ids]/(parity@parity)))
            boundary.append(dict(key=key,time_s=float(a.time_s.iloc[0]),bottom_material_count=int(bottom.sum()),side_material_count=int(side.sum()),
                bottom_settlement_mean_mm=float(((initial.z-a.z)*1000)[bottom].mean()),bottom_normal_displacement_abs_max_mm=float(abs((initial.z-a.z)*1000)[bottom].max()),
                side_normal_displacement_abs_max_mm=float(abs((a.x-initial.x)*1000)[side].max()),bottom_normal_velocity_abs_max_m_s=float(abs(a.vz[bottom]).max()),
                side_normal_velocity_abs_max_m_s=float(abs(a.vx[side]).max()),loaded_band_alternating_stress_rms_pa=float(np.sqrt(np.mean(np.square(coefficients))))))
            if part==1000:
                for x in (0,2,8):
                    mask=np.isclose(initial.x,x,atol=1e-8);assert mask.sum()==101
                    for j in np.flatnonzero(mask):profiles.append(dict(key=key,time_s=float(a.time_s.iloc[0]),id=int(a.id.iloc[j]),x0_m=float(initial.x.iloc[j]),z0_m=float(initial.z.iloc[j]),
                        pressure_pa=float(a.pressure.iloc[j]),settlement_mm=float((initial.z.iloc[j]-a.z.iloc[j])*1000),total_compression_pa=float(total[j])))
        print('Selected material fields:',part,flush=True)
    final=frames[1000];on,off,fine=final['on'],final['off'],final['half']
    field=pd.DataFrame(dict(id=initial.id,x0_m=initial.x,z0_m=initial.z,pressure_pa=on.pressure,pressure_on_off_pa=on.pressure-off.pressure,
        pressure_coarse_half_pa=on.pressure-fine.pressure,settlement_mm=(initial.z-on.z)*1000,settlement_on_off_mm=(off.z-on.z)*1000,
        settlement_coarse_half_mm=(fine.z-on.z)*1000,total_compression_pa=on.pressure-on.sigma_zz,
        total_compression_on_off_pa=(on.pressure-on.sigma_zz)-(off.pressure-off.sigma_zz),total_compression_coarse_half_pa=(on.pressure-on.sigma_zz)-(fine.pressure-fine.sigma_zz)))
    outputs=[]
    def csv(suffix,frame):
        path=TESTS/'figures'/(TAG+suffix);frame.to_csv(path,index=False,mode='x');outputs.append(bound(path));return path
    csv('_fields_r1.csv',field);csv('_regions_r1.csv',pd.DataFrame(region_rows));csv('_boundary_r1.csv',pd.DataFrame(boundary));csv('_profiles_r1.csv',pd.DataFrame(profiles))
    fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained');columns=['GPU SPR on','SPR on minus off','GPU coarse minus half dt']
    names=[['pressure_pa','pressure_on_off_pa','pressure_coarse_half_pa'],['settlement_mm','settlement_on_off_mm','settlement_coarse_half_mm'],
        ['total_compression_pa','total_compression_on_off_pa','total_compression_coarse_half_pa']]
    labels=['Pore pressure (kPa)','Material settlement (mm)','Vertical total compression (kPa)']
    for row in range(3):
        for col in range(3):
            ax=axes[row,col];v=field[names[row][col]]/(1 if row==1 else 1000);kw=dict(cmap='viridis')
            if col:
                limit=max(float(abs(v).max()),1e-14);kw=dict(cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit))
            dots=ax.scatter(initial.x,initial.z,c=v,s=3,marker='s',linewidths=0,rasterized=True,**kw);fig.colorbar(dots,ax=ax,pad=.04,shrink=.82)
            ax.set(xlabel='Initial material x (m)',ylabel='Initial material z (m)',xlim=(-10.1,10.1),ylim=(-.1,10.1),aspect='equal');ax.set_title(columns[col]+'\n'+labels[row],fontsize=10)
    fig.suptitle('Yao native fields at actual t = 10 s\nIndependent colorbar ranges; HG/NoPen off. On/off changes are not theory errors.',fontsize=13)
    def png(suffix,figure):
        path=TESTS/'figures'/(TAG+suffix);assert not path.exists();figure.savefig(path,dpi=150);plt.close(figure);outputs.append(bound(path))
    png('_fields_r1.png',fig)
    profiles_frame=pd.DataFrame(profiles);fig,axes=plt.subplots(3,3,figsize=(13,10),layout='constrained')
    for col,x in enumerate((0,2,8)):
        for row,(variable,scale,label) in enumerate(zip(['pressure_pa','settlement_mm','total_compression_pa'],[1000,1,1000],labels)):
            ax=axes[row,col]
            for key in KEYS:
                a=profiles_frame[profiles_frame.key.eq(key)&np.isclose(profiles_frame.x0_m,x)].sort_values('z0_m')
                ax.plot(a[variable]/scale,a.z0_m,color=COLORS[key],ls='--' if key=='half' else '-',label=key)
            ax.set(title='Initial x = '+str(x)+' m',xlabel=label,ylabel='Initial material z (m)',ylim=(0,10));ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Yao native vertical profiles at actual t = 10 s; no interpolation',fontsize=14);png('_profiles_r1.png',fig)
    evolution=[];fig,axes=plt.subplots(3,3,figsize=(15,10),layout='constrained');absmax=max(float(frames[p][k].pressure.max()/1000) for p in (100,500,1000) for k in ('off','on'))
    delta=max(float(abs(frames[p]['on'].pressure-frames[p]['off'].pressure).max()/1000) for p in (100,500,1000))
    for row,part in enumerate((100,500,1000)):
        a,b=frames[part]['on'],frames[part]['off'];evolution.append(pd.DataFrame(dict(time_s=float(a.time_s.iloc[0]),id=initial.id,x0_m=initial.x,z0_m=initial.z,off_pressure_pa=b.pressure,on_pressure_pa=a.pressure,change_pressure_pa=a.pressure-b.pressure)))
        for col,v in enumerate((b.pressure/1000,a.pressure/1000,(a.pressure-b.pressure)/1000)):
            ax=axes[row,col];kw=dict(cmap='viridis',vmin=0,vmax=absmax) if col<2 else dict(cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-delta,vcenter=0,vmax=delta))
            dots=ax.scatter(initial.x,initial.z,c=v,s=3,marker='s',linewidths=0,rasterized=True,**kw);fig.colorbar(dots,ax=ax,pad=.04,shrink=.82)
            ax.set(title=('SPR off','SPR on','On minus off')[col]+'; t = '+str(part*.01)+' s',xlabel='Initial material x (m)',ylabel='Initial material z (m)',aspect='equal')
    fig.suptitle('Yao pressure evolution (kPa); common absolute/difference scales across times',fontsize=14);png('_evolution_r1.png',fig);csv('_evolution_r1.csv',pd.concat(evolution,ignore_index=True))
    late={};final_history={}
    for key,h in histories.items():
        assert len(h)==1001 and abs(h.time_s-np.arange(1001)*.01).max()<1e-8
        a=final[key];at=a.set_index('id');assert float(h.max_pressure_pa.iloc[-1])==float(a.pressure.max())
        assert abs(h.strip_settlement_mm.iloc[-1]-float(((initial.z-a.z)*1000)[top].mean()))<1e-15
        for name,pid,point in [('A',13844,(2,8)),('B',19844,(8,2))]:
            mask=initial.id.eq(pid);assert mask.sum()==1 and np.allclose(initial.loc[mask,['x','z']].to_numpy()[0],point,atol=1e-10,rtol=0)
            assert h[name+'_id'].eq(pid).all() and float(h[name+'_pressure_over_q0'].iloc[-1])==float(at.loc[pid,'pressure']/5000)
        assert h[h.time_s.gt(.100001)].loaded_count.eq(61).all();final_history[key]=h.iloc[-1].to_dict()
        window=h[h.time_s.ge(8)]
        late[key]=dict(max_pressure_drop_5_to_10_percent=float(100*(1-h.max_pressure_pa.iloc[-1]/h.max_pressure_pa.iloc[500])),
            mean_pressure_drop_5_to_10_percent=float(100*(1-h.mean_pressure_pa.iloc[-1]/h.mean_pressure_pa.iloc[500])),
            max_pressure_slope_8_to_10_pa_s=float(np.polyfit(window.time_s,window.max_pressure_pa,1)[0]))
    loops=checks['final']['loops_s'];result=dict(passed=True,physical_acceptance=False,visual_inspected=False,verified_unique_hashes=len(verified),samples_each=1001,soil_count=20301,
        actual_final_times_s={x['key']:x['completion']['actual_time_s'] for x in r['runs']},shared_cadence_prefix_0ulp=prefixes,metadata=metadata,
        half_max=dict(pressure_rms_pa=float(half.pressure_rms_pa.max()),material_mm=float(half.material_max_mm.max()),stress_rms_pa=float(half.total_stress_rms_pa.max())),
        off_on_max=dict(pressure_rms_pa=float(offon.pressure_rms_pa.max()),material_mm=float(offon.material_max_mm.max()),stress_rms_pa=float(offon.total_stress_rms_pa.max()),force_abs_N_m=float(abs(offon.force_difference_N_m).max())),
        final_histories=final_history,late_decay=late,selected_region_times_only=[.1,1,3,5,8,10],final_boundary_metrics=[x for x in boundary if x['time_s']>9.9],
        loops_s=loops,observed_on_vs_off_loop_increase_percent=100*(loops['on']/loops['off']-1),controlled_speed_benchmark=False,
        limitations=['Original 59/61 nodal quadrature; same-dt saved force agrees, not all force-stage telemetry','No 10-s CPU control or independent theory reference',
            'Half evidence at .01-s samples plus retained dense startup, not every internal step','Alternating stress fit is a descriptive grid diagnostic, not proof of hourglass or physical error',
            'Static convex planar elastic, HG/NoPen off; no curves/motion/plastic/large-rotation/exact-HG-restart acceptance'],evidence=evidence,outputs=outputs)
    with receipt.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','outputs','final_histories')},indent=2),flush=True)


if __name__=='__main__':main()
