"""Offline axis-NoPen provenance, native equivalence and proximity/field review."""
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from scipy.spatial import cKDTree
from spr_yao_short import TESTS,bound
from spr_yao_review import native
from spr_yao_axis_check import TAG,load
from spr_yao_step_review import exact_fields


def wall_geometry(path):
    data=path.read_bytes();m=re.search(rb'POINTS (\d+) double\n',data);assert m
    count=int(m[1]);pos=np.frombuffer(data,dtype='>f8',count=count*3,offset=m.end()).reshape(-1,3).astype(float)
    m=re.search(rb'Normal 3 '+str(count).encode()+rb' float\n',data);assert m
    normal=np.frombuffer(data,dtype='>f4',count=count*3,offset=m.end()).reshape(-1,3).astype(np.float32)
    return pos,normal


def main():
    receipt=TESTS/'logs'/(TAG+'.audit_r1.json');assert not receipt.exists()
    r=load();assert r['status']=='completed_pending_review';verified=set();evidence=[bound(__file__),bound(TESTS/'logs'/(TAG+'.status.json'))]
    def verify(item):
        if item['path'] not in verified:
            assert bound(item['path'])['sha256']==item['sha256'],item['path'];verified.add(item['path'])
    checks={};keys=('cpu_c','gpu_c','gpu_h')
    for run in r['runs']:
        assert run['exit_code']==0 and run['owned_exited'] and run['completion']['completed']
        path=TESTS/'logs'/(TAG+'_'+run['key']+'.run.json');frozen=json.loads(path.read_text())
        assert frozen['inputs']==r['inputs'] and frozen['run']==run;evidence.append(bound(path))
        for item in run['outputs']+[run['log']]:verify(item)
    for key in (*keys,'cross','half','final'):
        path=TESTS/'logs'/(TAG+'_'+key+'.check.json');a=json.loads(path.read_text());assert a['passed'];checks[key]=a
        for item in a['evidence']+a['outputs']:verify(item)
        evidence.append(bound(path))
    for key in keys:
        path=TESTS/'logs'/('spr_yao_cpu_gpu_1s_r1_'+key+'.run.json');control=json.loads(path.read_text())
        # Bind all control raw fields used here, not an unexamined 1-s tail.
        for item in control['run']['outputs']:
            name=item['path'].replace('\\','/').split('/')[-1]
            m=re.fullmatch(r'(?:Part|PartExtra)_(\d+)\.bi4',name)
            if m and int(m[1])<=100:verify(item)
        evidence.append(bound(path))
    histories={k:pd.read_csv(TESTS/'figures'/(TAG+'_'+k+'_history.csv'),float_precision='round_trip') for k in keys}
    pair_stats={}
    for kind in ('cross','half'):
        a=pd.read_csv(TESTS/'figures'/(TAG+'_'+kind+'.csv'),float_precision='round_trip')
        assert len(a)==101 and a.pressure_rms_pa.le(5).all() and a.material_max_mm.le(.005).all()
        assert abs(a.time_s-np.arange(101)*.001).max()<1e-10
        for col,field in [('pressure_rms_pa','pressure_rms_max_pa'),('material_max_mm','material_max_mm'),('total_stress_rms_pa','total_stress_rms_max_pa')]:assert float(a[col].max())==checks[kind][field]
        force=float(abs(a.force_difference_N_m).max());assert kind!='cross' or force<.002
        pair_stats[kind]=dict(pressure_rms_max_pa=float(a.pressure_rms_pa.max()),material_max_mm=float(a.material_max_mm.max()),
            total_stress_rms_max_pa=float(a.total_stress_rms_pa.max()),force_difference_abs_max_N_m=force)
    folder=TESTS/'outputs'/(TAG+'_cpu_c');initial=native(folder,0);assert len(initial)==20301 and initial.id.is_unique
    walls_path=folder/'CfgInit_Normals.vtk';wall,norm=wall_geometry(walls_path);assert len(wall)==1644
    normlen=np.sqrt(np.sum(norm*norm,axis=1));unit=norm/normlen[:,None];tree=cKDTree(wall)
    regions=dict(all=np.ones(len(initial),dtype=bool),near_fixed_wall=(initial.z<.200001)|(abs(initial.x)>9.799999),bottom_corner=(initial.z<.5)&(abs(initial.x)>9.5))
    rows=[];geometry=[];zero={};finals={};offfinal={}
    for key in keys:
        count=0
        for i in range(101):
            a=native(TESTS/'outputs'/(TAG+'_'+key),i);b=native(TESTS/'outputs'/('spr_yao_cpu_gpu_1s_r1_'+key),i)
            assert len(a)==20301 and np.array_equal(a.id,initial.id) and abs(a.time_s.iloc[0]-i*.001)<1e-10
            assert exact_fields(a,b),(key,i,'NoPen on/off native fields differ');count+=1
            if key=='cpu_c':
                pos=a[['x','y','z']].to_numpy();neighbours=tree.query_ball_point(pos,.125001)
                pairs=[(p,q) for p,ns in enumerate(neighbours) for q in ns]
                assert pairs;pi,qi=np.asarray(pairs).T
                dr=(pos[pi]-wall[qi]).astype(np.float32);rr=np.sqrt(np.sum(dr*dr,axis=1));distance=np.sum(dr*unit[qi],axis=1)
                eligible=(rr<np.float32(.125))&(normlen[qi]<np.float32(.175))
                margin=distance-np.float32(.75)*normlen[qi]
                active=eligible&(margin<0)
                geometry.append(dict(time_s=float(a.time_s.iloc[0]),eligible_pairs=int(eligible.sum()),geometrically_active_pairs=int(active.sum()),
                    minimum_proximity_margin_m=float(margin[eligible].min())))
            if i in (0,20,50,100):
                dp=(a.pressure-b.pressure).to_numpy();ds=((a.pressure-a.sigma_zz)-(b.pressure-b.sigma_zz)).to_numpy()
                for region,mask in regions.items():rows.append(dict(key=key,time_s=float(a.time_s.iloc[0]),region=region,native_count=int(mask.sum()),
                    pressure_on_off_rms_pa=float(np.sqrt(np.mean(dp[mask]**2))),total_compression_on_off_rms_pa=float(np.sqrt(np.mean(ds[mask]**2))),
                    settlement_on_off_abs_max_mm=float(abs((b.z-a.z).to_numpy()[mask]).max()*1000)))
            if i==100:finals[key]=a;offfinal[key]=b
        zero[key]=count;print('Full native NoPen on/off 0 ULP:',key,count,flush=True)
    proximity=pd.DataFrame(geometry);assert proximity.geometrically_active_pairs.eq(0).all() and proximity.minimum_proximity_margin_m.gt(0).all()
    regions_csv=TESTS/'figures'/(TAG+'_regions_r1.csv');pd.DataFrame(rows).to_csv(regions_csv,index=False,mode='x')
    geometry_csv=TESTS/'figures'/(TAG+'_proximity_r1.csv');proximity.to_csv(geometry_csv,index=False,mode='x')
    on,off,fine=finals['gpu_c'],offfinal['gpu_c'],finals['gpu_h']
    field=pd.DataFrame(dict(id=initial.id,x0_m=initial.x,z0_m=initial.z,pressure_pa=on.pressure,
        pressure_on_off_pa=on.pressure-off.pressure,pressure_coarse_half_pa=on.pressure-fine.pressure,
        settlement_mm=(initial.z-on.z)*1000,settlement_on_off_mm=(off.z-on.z)*1000,settlement_coarse_half_mm=(fine.z-on.z)*1000,
        total_compression_pa=on.pressure-on.sigma_zz,total_compression_on_off_pa=(on.pressure-on.sigma_zz)-(off.pressure-off.sigma_zz),
        total_compression_coarse_half_pa=(on.pressure-on.sigma_zz)-(fine.pressure-fine.sigma_zz)))
    fields_csv=TESTS/'figures'/(TAG+'_fields_r1.csv');field.to_csv(fields_csv,index=False,mode='x')
    fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained')
    variables=[['pressure_pa','pressure_on_off_pa','pressure_coarse_half_pa'],['settlement_mm','settlement_on_off_mm','settlement_coarse_half_mm'],
        ['total_compression_pa','total_compression_on_off_pa','total_compression_coarse_half_pa']]
    columns=['GPU NoPen + SPR','NoPen on minus off','GPU coarse minus half dt'];labels=['Pore pressure (kPa)','Material settlement (mm)','Vertical total compression (kPa)']
    for row in range(3):
        for col in range(3):
            ax=axes[row,col];v=field[variables[row][col]]/(1 if row==1 else 1000)
            if np.any(v):
                kw=dict(cmap='viridis')
                if col:
                    limit=float(abs(v).max());kw=dict(cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit))
                dots=ax.scatter(field.x0_m,field.z0_m,c=v,s=3,marker='s',linewidths=0,rasterized=True,**kw);fig.colorbar(dots,ax=ax,pad=.04,shrink=.82)
            else:
                ax.scatter(field.x0_m,field.z0_m,color='.85',s=3,marker='s',linewidths=0,rasterized=True)
                ax.text(.5,.5,'0 (bit-identical)',ha='center',va='center',transform=ax.transAxes)
            ax.set(xlabel='Initial material x (m)',ylabel='Initial material z (m)',xlim=(-10.1,10.1),ylim=(-.1,10.1),aspect='equal')
            ax.set_title(columns[col]+'\n'+labels[row],fontsize=10)
    fig.suptitle('Yao axis-NoPen native fields at actual t = 0.1 s\nIndependent colorbars. Original load; HG off; NoPen proximity guard inactive at all 101 saved states.',fontsize=13)
    png=TESTS/'figures'/(TAG+'_fields_r1.png');assert not png.exists();fig.savefig(png,dpi=150);plt.close(fig)
    for key,h in histories.items():
        assert len(h)==101 and h[['nopen_change_pressure_rms_pa','nopen_change_stress_rms_pa','nopen_change_material_max_mm']].eq(0).all().all()
        f=finals[key];top=np.isclose(initial.z,10,atol=1e-8)&(abs(initial.x)<3-1e-8)
        assert h.max_pressure_pa.iloc[-1]==float(f.pressure.max())
        assert abs(h.strip_settlement_mm.iloc[-1]-float(((initial.z-f.z)*1000)[top].mean()))<1e-15
    result=dict(passed=True,physical_acceptance=False,visual_inspected=False,verified_unique_hashes=len(verified),samples_each=101,soil_count=20301,
        actual_final_times_s={x['key']:x['completion']['actual_time_s'] for x in r['runs']},native_nopen_on_off_0ulp_frames=zero,pair_stats=pair_stats,
        proximity_guard_active_saved_samples=int(proximity.geometrically_active_pairs.gt(0).sum()),proximity_margin_min_m=float(proximity.minimum_proximity_margin_m.min()),
        sampled_proximity_is_not_all_force_stage_telemetry=True,final_histories={k:h.iloc[-1].to_dict() for k,h in histories.items()},loops_s=checks['final']['loops_s'],
        limitations=['Compatibility/inactive-NoPen regression only, not evidence of improved wall response','No new active-NoPen or long-cycle acceptance',
            'Original 59/61-node strip quadrature retained; no 1D100Pa gate','Static axis-aligned FreeSlip, elastic, HG off'],
        evidence=evidence+[bound(walls_path),bound(TESTS.parents[3]/'src/source/JSphCpu.cpp'),bound(TESTS.parents[3]/'src/source/JDsInitialize.cpp')],
        outputs=[bound(p) for p in (regions_csv,geometry_csv,fields_csv,png)])
    with receipt.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','outputs','final_histories')},indent=2))


if __name__=='__main__':main()
