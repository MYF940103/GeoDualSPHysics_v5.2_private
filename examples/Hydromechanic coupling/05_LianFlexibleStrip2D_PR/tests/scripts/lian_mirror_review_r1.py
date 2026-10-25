"""Independent native short review, with actual-time/ID comparisons and PNG/CSV."""
from concurrent.futures import ThreadPoolExecutor
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lian_release_r1 import CASE,TESTS,READER,bound,native,write_json,utc
from lian_drained_review_r1 import verify

TAG='lian_mirror_review_r1'


def sample(a,initial,dt,mirror):
    assert len(a)==20301 and np.array_equal(a.id,initial.id) and np.isfinite(a.to_numpy()).all()
    assert a.rho.gt(0).all() and a.nout.eq(0).all() and a.kplastic.eq(0).all()
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.load_available.eq(1).all()
    assert a.x.between(-.1,20.1).all() and a.z.between(-.1,10.1).all()
    t=float(a.time_s.iloc[0]);active=t-dt>=1 and t>0
    if t:assert a.has_dterror.eq(1).all() and a.dterror_s.le(1e-14).all()
    contact=a.x.abs().le(1.25) if mirror else a.x.between(0,1.25)
    drained=a.fstype.isin([2,3])&~contact
    if active:assert drained.any() and a.pressure[drained].eq(0).all()
    force=float(-(a.mass*a.load_az).sum());expected=13000*min(1,max(0,t-dt))
    if mirror:assert abs(force-expected)<.002
    w=a[a.id.eq(1744)].iloc[0]
    row=dict(time_s=t,source_prior_time_s=max(0,t-dt),drainage_active=active,
        potential_drained_count=int(drained.sum()),drained_abs_max_pa=float(a.pressure[drained].abs().max()) if active else None,
        force_N_m=force,expected13_node_force_N_m=expected,loaded_count=int(a.load_az.abs().gt(0).sum()),
        id1744_x_m=float(w.x),id1744_pressure_pa=float(w.pressure),id1744_load_az=float(w.load_az),
        pressure_mean_pa=float(a.pressure.mean()),pressure_min_pa=float(a.pressure.min()),
        sigma_zz_rms_pa=float(np.sqrt(np.mean(a.sigma_zz**2))),vmax_m_s=float(np.linalg.norm(a[['vx','vy','vz']],axis=1).max()))
    for key,(x,z) in [('A',(.1,10)),('B',(1.25,8.75))]:
        k=int(np.argmin((initial.x-x)**2+(initial.z-z)**2))
        row[key+'_id']=int(a.id.iloc[k]);row[key+'_pressure_pa']=float(a.pressure.iloc[k])
        row[key+'_settlement_mm']=1000*float(initial.z.iloc[k]-a.z.iloc[k])
    return row


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json');assert not receipt.exists()
    status=TESTS/'logs/lian_mirror_short_r2.status.json';s=json.loads(status.read_text());verify(s)
    assert s['status']=='short_gates_passed_pending_physical_review' and all(p['passed'] for p in s['pairs'])
    assert [r['name'].split('r2_')[-1] for r in s['runs']]==['gpu_debug','smoke_c','smoke_h','drained_c','drained_h']
    sources=[bound(__file__),bound(status),bound(READER),bound(TESTS/'scripts/lian_release_r1.py')]
    for r in [s['adopted_CPU_Debug']]+s['runs']:
        assert r['exit_code']==0 and r['owned_exited'];verify(r)
        assert bound(r['log']['path'])['sha256']==r['log']['sha256']
        assert bound(r['history']['path'])['sha256']==r['history']['sha256']
        folder=TESTS/'outputs'/r['name'];assert 'Finished execution (code=0)' in (folder/'Run.out').read_text(errors='replace')
        sources.append(bound(folder/'Run.out'))
    assert 'ERROR SUMMARY: 0 errors' in (TESTS/'logs/lian_mirror_short_r2_gpu_debug.log').read_text(errors='replace')
    build=json.loads((TESTS/'logs/lian_mirror_build_r1.json').read_text(encoding='utf-8-sig'));verify(build)
    for e in build['programs']:assert bound(e['path'])['sha256'].lower()==e['sha256'].lower()
    runtime=json.loads((TESTS/'logs/lian_mirror_runtime_r1.json').read_text(encoding='utf-8-sig'))
    for e in runtime['files']:assert bound(e['path'])['sha256'].lower()==e['sha256'].lower()
    rows=[];metrics=[];final={};origins={}
    for stage,count in [('smoke',31),('drained',61)]:
        folders={k:TESTS/'outputs'/name for k,name in {
            'mirror_c':'lian_mirror_short_r2_'+stage+'_c','mirror_h':'lian_mirror_short_r2_'+stage+'_h',
            'strict_c':'lian_release_r1_'+stage+'_gpu_c','strict_h':'lian_release_r1_'+stage+'_gpu_h'}.items()}
        origin=native(folders['mirror_c'],0);origins[stage]=origin;top=origin.z.gt(9.99).to_numpy()
        with ThreadPoolExecutor(max_workers=2) as pool:
            for i in range(count):
                data=dict(zip(folders,pool.map(lambda folder:native(folder,i),folders.values())))
                for name,a in data.items():
                    row=sample(a,origin,5e-6 if name.endswith('_h') else 1e-5,name.startswith('mirror'))
                    row.update(stage=stage,run=name,part=i);rows.append(row)
                c,h=data['mirror_c'],data['mirror_h'];old=data['strict_c']
                assert abs(float(c.time_s.iloc[0]-h.time_s.iloc[0]))<=1.01e-5
                assert abs(float(c.time_s.iloc[0]-old.time_s.iloc[0]))<=1.01e-5
                pressure=float(np.sqrt(np.mean((c.pressure-h.pressure)**2)))
                displacement=float(1000*np.max(abs(c.z.to_numpy()[top]-h.z.to_numpy()[top])))
                assert pressure<=5 and displacement<=.005
                metrics.append(dict(stage=stage,part=i,coarse_time_s=float(c.time_s.iloc[0]),half_time_s=float(h.time_s.iloc[0]),
                    half_pressure_rms_pa=pressure,half_top_material_mm=displacement,
                    strict_pressure_rms_difference_pa=float(np.sqrt(np.mean((c.pressure-old.pressure)**2))),
                    strict_top_material_max_difference_mm=float(1000*np.max(abs(c.z.to_numpy()[top]-old.z.to_numpy()[top])))))
                if stage=='drained' and i==60:final=data
                if i%20==0:print(stage,'native frame',i,flush=True)
    history=pd.DataFrame(rows);paired=pd.DataFrame(metrics);artifacts=[]
    def csv(name,data):
        p=TESTS/'figures'/(TAG+'_'+name+'.csv');assert not p.exists()
        data.to_csv(p,index=False,float_format='%.17g');artifacts.append(bound(p))
    def png(name,fig):
        p=TESTS/'figures'/(TAG+'_'+name+'.png');assert not p.exists()
        fig.savefig(p,dpi=160);plt.close(fig);artifacts.append(bound(p))
    csv('history',history);csv('pairs',paired)
    columns=['A_pressure_pa','B_pressure_pa','A_settlement_mm','B_settlement_mm','force_N_m','id1744_x_m']
    labels=['A pressure (kPa)','B pressure (kPa)','A material settlement (mm)','B material settlement (mm)','Actual applied force (kN/m)','Native1744 x (micrometres)']
    styles=[('strict_c','#555555',':'),('mirror_c','#215a8a','-'),('mirror_h','#b56b28','--')]
    fig,axes=plt.subplots(2,3,figsize=(14,7.5),layout='constrained')
    for name,color,line in styles:
        d=history[history.stage.eq('drained')&history.run.eq(name)]
        for ax,c,label in zip(axes.flat,columns,labels):
            scale=1e6 if c=='id1744_x_m' else (.001 if c.endswith('_pa') or c=='force_N_m' else 1)
            ax.plot(d.time_s,d[c]*scale,line,color=color,label=name)
            ax.set(xlabel='Actual saved time (s)',ylabel=label,xlim=(0,3),xticks=[0,1,2,3]);ax.grid(alpha=.2)
    axes[0,0].legend();fig.suptitle('Lian mirrored contact:3s native short comparison, NOT late/FEM acceptance');png('history',fig)
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for name,color,line in styles:
        d=history[history.stage.eq('smoke')&history.run.eq(name)]
        for ax,c,label,scale in zip(axes.flat,['id1744_x_m','force_N_m','id1744_pressure_pa','A_settlement_mm'],
            ['Native1744 x (micrometres)','Actual applied force (N/m)','Native1744 pressure (Pa)','A material settlement (mm)'],[1e6,1,1,1]):
            ax.plot(d.time_s,d[c]*scale,line,color=color,label=name)
            ax.set(xlabel='Actual saved time (s)',ylabel=label,xlim=(0,.15),xticks=[0,.05,.1,.15]);ax.grid(alpha=.2)
    axes[0,0].axhline(0,color='.6',lw=.7);axes[0,0].legend();fig.suptitle('Dense startup: mirror retains the intended corner load; q/quadrature unchanged');png('startup',fig)
    c,o=final['mirror_c'],final['strict_c'];origin=origins['drained']
    fields=pd.DataFrame(dict(id=origin.id,x0_m=origin.x,z0_m=origin.z,pressure_difference_pa=c.pressure-o.pressure,
        settlement_difference_mm=1000*(o.z-c.z),mirror_pressure_pa=c.pressure,strict_pressure_pa=o.pressure))
    csv('fields',fields)
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),layout='constrained')
    for ax,column,title in zip(axes,['pressure_difference_pa','settlement_difference_mm'],['Mirror minus strict pressure (Pa)','Mirror minus strict settlement (mm)']):
        maximum=max(abs(fields[column].min()),abs(fields[column].max()))
        artist=ax.tricontourf(origin.x,origin.z,fields[column],levels=np.linspace(-maximum,maximum,31),cmap='RdBu_r',extend='both')
        ax.set(title=title,xlabel='Initial material x (m)',ylabel='Initial material z (m)',aspect='equal');fig.colorbar(artist,ax=ax,shrink=.8)
    fig.suptitle('Native-ID differences at actual3.000000000011186s; these are NOT theory errors');png('fields',fig)
    summary={}
    for stage in ['smoke','drained']:
        p=paired[paired.stage.eq(stage)];d=history[history.stage.eq(stage)&history.run.str.startswith('mirror')]
        summary[stage]=dict(native_pairs=len(p),half_pressure_rms_max_pa=float(p.half_pressure_rms_pa.max()),
            half_top_material_max_mm=float(p.half_top_material_mm.max()),strict_pressure_rms_max_pa=float(p.strict_pressure_rms_difference_pa.max()),
            strict_top_material_max_mm=float(p.strict_top_material_max_difference_mm.max()),positive_load_node_counts=sorted(d[d.part.gt(0)].loaded_count.unique().astype(int).tolist()),
            max_force_error_N_m=float(abs(d.force_N_m-d.expected13_node_force_N_m).max()))
        inherited=next(e for e in s['pairs'] if e['stage']==stage)
        assert abs(summary[stage]['half_pressure_rms_max_pa']-inherited['max_pressure_RMS_Pa'])<1e-12
        assert abs(summary[stage]['half_top_material_max_mm']-inherited['max_top_material_mm'])<1e-12
    active=history[history.stage.eq('drained')&history.run.str.startswith('mirror')&history.drainage_active]
    assert len(active)>0 and active.drained_abs_max_pa.eq(0).all()
    result=dict(passed=True,visual_review_passed=False,physical_full_cycle_accepted=False,utc=utc(),summary=summary,
        active_drained_node_samples=int(active.potential_drained_count.sum()),active_drained_abs_pressure_max_pa=float(active.drained_abs_max_pa.max()),
        sources=sources,artifacts=artifacts,limits=['Debug is not a Release0ULP control; only independent safety and memcheck are claimed.',
            'Mirror/strict changes are causal same-dt differences, not half-step or theory errors.',
            '3s has not crossed the strict12.4/14.1s switching window. No late/full/FEM/general-contact acceptance.',
            'Original13-node quadrature is still+4percent versus ideal1.25m width; no rescaling.',
            'All active FSType2/3 drainage checked at prior configured-dt source clock; no fixed-grid alignment.'])
    write_json(receipt,result);print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
