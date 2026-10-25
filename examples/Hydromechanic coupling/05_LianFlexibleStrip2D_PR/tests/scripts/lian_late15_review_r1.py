"""Offline native late-window review. No solver, interpolation or retained edits."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lian_release_r1 import CASE,TESTS,REPO,READER,bound,native,write_json,utc
from lian_drained_review_r1 import describe,verify

TAG='lian_late15_review_r1'
CURRENT=TESTS/'outputs/lian_late15_r1'
OLD=CASE/'CaseLianFlexibleStrip2D_PR_out'


def row(a,initial,dt):
    d=describe(a,initial)
    t=float(a.time_s.iloc[0]);d['prior_source_time_s']=max(0,t-dt)
    assert d['drainage_evaluated_active']==(t-dt>=1 and t>0)
    f=a.fstype.isin([2,3]);strip=a.x.between(0,1.25);symmetric=a.x.abs().le(1.25)
    surface=a.z.between(9.95,10.05)
    length=np.linalg.norm(a[['normal_x','normal_y','normal_z']],axis=1)
    upward=a.normal_z.to_numpy()/np.maximum(length,1e-30)>.35
    selected=(f&upward)|(~f&surface)
    original_load=strip&selected;symmetric_load=symmetric&selected
    watch=a.loc[a.id.eq(1744)].iloc[0]
    d.update(id1744_fstype=int(watch.fstype),id1744_load_az=float(watch.load_az),
        id1744_original_contact=bool(0<=watch.x<=1.25),id1744_symmetric_contact=bool(abs(watch.x)<=1.25),
        frozen_original_loaded_count=int(original_load.sum()),frozen_symmetric_loaded_count=int(symmetric_load.sum()),
        frozen_load_changed_ids=a.id[original_load^symmetric_load].astype(int).tolist(),
        frozen_drain_changed_ids=a.id[f&(strip^symmetric)].astype(int).tolist(),
        native_applied_loaded_count=int(a.load_az.abs().gt(0).sum()),
        pressure_rms_pa=float(np.sqrt(np.mean(a.pressure**2))),
        sigma_xx_rms_pa=float(np.sqrt(np.mean(a.sigma_xx**2))),
        id1744_vx_m_s=float(watch.vx),id1744_vz_m_s=float(watch.vz))
    return d


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json');assert not receipt.exists()
    status=TESTS/'logs/lian_late15_r1.status.json';s=json.loads(status.read_text());verify(s)
    assert s['status']=='completed_pending_review' and s['owned_exited'] and s['solver_exit_code']==0
    assert s['saved_frames']==301 and s['native_prefix0ulp_frames']==61
    assert abs(s['actual_final_time_s']-15)<2e-5
    assert 'Device default: 0 "NVIDIA GeForce RTX 3050"' in (CURRENT/'Run.out').read_text(errors='replace')
    assert 'Finished execution (code=0)' in (CURRENT/'Run.out').read_text(errors='replace')
    build=json.loads((TESTS/'logs/hydro_native_r1.build.json').read_text(encoding='utf-8-sig'));verify(build)
    assert bound(READER)['sha256'].lower()==build['executable_sha256'].lower()
    sources=[bound(__file__),bound(status),bound(TESTS/'logs/lian_late15_r1.run.json'),bound(READER),
        bound(TESTS/'scripts/lian_drained_review_r1.py'),bound(TESTS/'scripts/lian_release_r1.py')]
    starts={k:native(v,0) for k,v in [('current',CURRENT),('old',OLD)]}
    assert len(starts['current'])==20301 and np.array_equal(starts['current'].id,starts['old'].id)
    assert np.array_equal(starts['current'][['x','y','z']].to_numpy(dtype=np.float32),starts['old'][['x','y','z']].to_numpy(dtype=np.float32))
    rows=[];pairs=[];prefix=[];final={}
    def read_pair(i):return native(CURRENT,i),native(OLD,i)
    for first in range(0,301,20):
        indices=range(first,min(first+20,301))
        with ThreadPoolExecutor(max_workers=2) as pool:
            for i,(a,o) in zip(indices,pool.map(read_pair,indices)):
                mismatch=abs(float(a.time_s.iloc[0]-o.time_s.iloc[0]));assert mismatch<=1.01e-5
                assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.load_available.eq(1).all()
                for name,data in [('current',a),('old',o)]:
                    d=row(data,starts[name],1e-5);d.update(run=name,part=i);rows.append(d)
                    sources.append(bound((CURRENT if name=='current' else OLD)/'data'/f'Part_{i:04d}.bi4'))
                if i<=60:
                    control=native(TESTS/'outputs/lian_release_r1_drained_gpu_c',i)
                    assert np.array_equal(a.to_numpy(),control.to_numpy()),('Shared exact-time/step prefix',i)
                    prefix.append(dict(part=i,time_s=float(a.time_s.iloc[0]),all_native_fields_0ulp=True))
                top=starts['current'].z.gt(9.99).to_numpy()
                pairs.append(dict(part=i,current_time_s=float(a.time_s.iloc[0]),old_time_s=float(o.time_s.iloc[0]),
                    time_mismatch_s=mismatch,pressure_rms_difference_pa=float(np.sqrt(np.mean((a.pressure-o.pressure)**2))),
                    stress_zz_rms_difference_pa=float(np.sqrt(np.mean((a.sigma_zz-o.sigma_zz)**2))),
                    top_material_max_difference_mm=float(1000*np.max(abs(a.z.to_numpy()[top]-o.z.to_numpy()[top])))))
                if i==300:final={'current':a,'old':o}
        print('Reviewed native parts through',min(first+19,300),flush=True)
    data=pd.DataFrame(rows);paired=pd.DataFrame(pairs);artifacts=[]
    def csv(name,frame):
        path=TESTS/'figures'/(TAG+'_'+name+'.csv');assert not path.exists()
        frame.to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
    def image(name,figure):
        path=TESTS/'figures'/(TAG+'_'+name+'.png');assert not path.exists()
        figure.savefig(path,dpi=160);plt.close(figure);artifacts.append(bound(path))
    csv('history',data);csv('pairs',paired);csv('prefix',pd.DataFrame(prefix))
    events=[]
    for key in ['current','old']:
        d=data[data.run.eq(key)].copy()
        changed=d.id1744_original_contact.astype(int).diff().fillna(0).ne(0)
        events+=d[changed].to_dict('records')
    csv('events',pd.DataFrame(events))
    columns=['A_pressure_pa','B_pressure_pa','A_settlement_mm','B_settlement_mm','pressure_mean_pa','sigma_zz_rms_pa']
    labels=['A native pressure (kPa)','B native pressure (kPa)','A native settlement (mm)',
        'B native settlement (mm)','Soil mean pressure (kPa)','Vertical stress RMS (kPa)']
    fig,axes=plt.subplots(2,3,figsize=(14,7.5),layout='constrained')
    for key,color,style in [('old','#555555',':'),('current','#215a8a','-')]:
        d=data[data.run.eq(key)]
        for ax,c,label in zip(axes.flat,columns,labels):
            scale=1 if 'settlement' in c else .001
            ax.plot(d.time_s,d[c]*scale,style,color=color,label=key)
            ax.set(xlabel='Actual saved time (s)',ylabel=label,xlim=(0,15));ax.grid(alpha=.2)
    axes[0,0].legend();fig.suptitle('Lian original strict strip / mixed slip: current vs legacy (not precision-only A/B)')
    image('history',fig)
    columns=['id1744_x_m','id1744_pressure_pa','saved_nodal_force_N_m','vmax_m_s','pressure_min_pa','frozen_symmetric_loaded_count']
    labels=['Native1744 x (micrometres)','Native1744 pressure (kPa)','Observed applied force (kN/m)',
        'Maximum soil speed (m/s)','Minimum soil pressure (kPa)','Frozen symmetric-extension load-node count']
    fig,axes=plt.subplots(3,2,figsize=(12,10),layout='constrained')
    for key,color,style in [('old','#555555',':'),('current','#215a8a','-')]:
        d=data[data.run.eq(key)]
        for ax,c,label in zip(axes.flat,columns,labels):
            if key=='old' and c=='saved_nodal_force_N_m':continue
            scale=1e6 if c=='id1744_x_m' else (.001 if c in ['id1744_pressure_pa','saved_nodal_force_N_m','pressure_min_pa'] else 1)
            ax.plot(d.time_s,d[c]*scale,style,color=color,label=key)
            ax.set(xlabel='Actual saved time (s)',ylabel=label,xlim=(0,15));ax.grid(alpha=.2)
    axes[0,0].axhline(0,color='.5',lw=.8);axes[0,0].legend()
    fig.suptitle('Contact diagnostic: saved force is current-only; symmetric extension is frozen/offline, NOT a repaired solve')
    image('contact',fig)
    a,o=final['current'],final['old'];origin=starts['current']
    fields=pd.DataFrame(dict(id=origin.id,x0_m=origin.x,z0_m=origin.z,current_pressure_pa=a.pressure,
        old_pressure_pa=o.pressure,difference_pa=a.pressure-o.pressure,current_sigma_zz_pa=a.sigma_zz,
        old_sigma_zz_pa=o.sigma_zz,current_settlement_mm=1000*(origin.z-a.z),old_settlement_mm=1000*(starts['old'].z-o.z)))
    csv('fields',fields)
    fig,axes=plt.subplots(1,3,figsize=(14,4.7),layout='constrained')
    for ax,col,title in zip(axes,['old_pressure_pa','current_pressure_pa','difference_pa'],['Legacy actual15.00001s','Current actual15.00001s','Current minus legacy (not theory error)']):
        limit=max(abs(fields[col].min()),abs(fields[col].max()))
        if col!='difference_pa':limit=max(abs(fields[['old_pressure_pa','current_pressure_pa']].min().min()),abs(fields[['old_pressure_pa','current_pressure_pa']].max().max()))
        artist=ax.tricontourf(origin.x,origin.z,fields[col]/1000,levels=np.linspace(-limit/1000,limit/1000,31),cmap='RdBu_r',extend='both')
        ax.set(title=title,xlabel='Initial material x (m)',ylabel='Initial material z (m)',aspect='equal')
        fig.colorbar(artist,ax=ax,label='Pressure (kPa)',shrink=.8)
    fig.suptitle('Native-ID matched pressure at15s; original strict contact geometry')
    image('fields',fig)
    summary={}
    for key in ['current','old']:
        d=data[data.run.eq(key)];e=[r for r in events if r['run']==key]
        summary[key]=dict(actual_final_time_s=float(d.time_s.iloc[-1]),final=d.iloc[-1].to_dict(),
            first_sampled_contact_loss_time_s=float(e[0]['time_s']) if e else None,contact_transitions=len(e),
            minimum_pressure_pa=float(d.pressure_min_pa.min()),maximum_speed_m_s=float(d.vmax_m_s.max()),
            frozen_symmetric_changed_load_ids=sorted(set(v for ids in d.frozen_load_changed_ids for v in ids)),
            frozen_symmetric_changed_drain_ids=sorted(set(v for ids in d.frozen_drain_changed_ids for v in ids)),
            frozen_symmetric_node_counts=sorted(d.frozen_symmetric_loaded_count.unique().astype(int).tolist()))
    result=dict(passed=True,visual_review_passed=False,physical_full_cycle_accepted=False,utc=utc(),native_pairs=301,
        prefix0ulp_frames=len(prefix),max_saved_time_mismatch_s=float(paired.time_mismatch_s.max()),summary=summary,
        final_pressure_rms_difference_pa=float(paired.pressure_rms_difference_pa.iloc[-1]),
        original_guards='All saved native IDs, finite/positive density/elastic/no exclusions/geometry/natural-step and all-active FSType2/3 drainage rechecked, unchanged.',
        conclusion='Strict x>=0 membership toggles one symmetry-edge node, its load and drained state. Current double stress shifts but does not remove this event; a frozen mirrored-footprint check is not a coupled repair.',
        limitations=['Only3s independent half-step evidence;15s single-dt review is not100s/FEM accuracy.',
            'Legacy load telemetry is zero but physical load was not zero. Frozen geometry is not an old force measurement.',
            'Legacy initial coordinates are float; native IDs and float-representable initial geometry match.',
            'Old/current is not an isolated precision A/B. Frozen mirrored footprint is only a proposed boundary-consistent diagnostic.',
            'Original13-node load quadrature remains+4percent versus ideal1.25m width; no rescaling performed.'],
        sources=sources,artifacts=artifacts)
    write_json(receipt,result)
    print(json.dumps({k:result[k] for k in ['passed','prefix0ulp_frames','max_saved_time_mismatch_s','final_pressure_rms_difference_pa']},indent=2),flush=True)


if __name__=='__main__':main()
