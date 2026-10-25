"""Independent 3-s native review; no solver, restart, interpolation or old-file edits."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lian_release_r1 import CASE,TESTS,REPO,READER,TAG,bound,native,write_json,utc

NAME='lian_drained_review_r1'
STATE=TESTS/'logs'/f'{TAG}_drained.status.json'


def verify(record):
    for key in ('sources','artifacts','inputs','outputs'):
        for item in record.get(key,[]):
            assert bound(item['path'])['sha256'].lower()==item['sha256'].lower(),item['path']


def describe(a,initial):
    t=float(a.time_s.iloc[0]);step=int(a.saved_step.iloc[0])
    dt=t/step if step else 0.
    top=initial.z.gt(9.99).to_numpy()
    # Exact production membership: both FSType2 and3, any normal direction.
    mask=a.fstype.isin([2,3]) & ~a.x.between(0,1.25)
    active=(step>0 and t-dt>=1.)
    if active:
        assert mask.any(),('Vacuous drainage mask',t)
        assert a.pressure[mask].eq(0).all(),('Native drained-node pressure',t)
    assert np.array_equal(a.id,initial.id) and np.isfinite(a.to_numpy()).all()
    assert a.nout.eq(0).all() and a.kplastic.eq(0).all() and a.rho.gt(0).all()
    assert a.x.between(-.1,20.1).all() and a.z.between(-.1,10.1).all()
    if step and a.has_dterror.iloc[0]:assert a.dterror_s.iloc[0]<=1e-14,('Natural step',t)
    watch=a[a.id.eq(1744)].iloc[0]
    row=dict(time_s=t,step=step,prior_step_time_estimate_s=t-dt,drainage_evaluated_active=active,
        all_orientation_drained_nodes=int(mask.sum()),isolated_drained_nodes=int((mask&a.fstype.eq(3)).sum()),
        drained_abs_pressure_max_pa=float(a.pressure[mask].abs().max()) if mask.any() else 0.,
        pressure_mean_pa=float(a.pressure.mean()),pressure_max_pa=float(a.pressure.max()),pressure_min_pa=float(a.pressure.min()),
        top_material_mean_settlement_mm=1000*float((initial.z.to_numpy()[top]-a.z.to_numpy()[top]).mean()),
        vmax_m_s=float(np.linalg.norm(a[['vx','vy','vz']],axis=1).max()),
        sigma_zz_rms_pa=float(np.sqrt(np.mean(a.sigma_zz**2))),
        id1744_x_m=float(watch.x),id1744_pressure_pa=float(watch.pressure),
        strip_geometric_nodes=int((a.x.between(0,1.25)&a.z.between(9.95,10.05)).sum()),
        load_observation_present=bool(a.load_available.iloc[0]),
        load_az_max_abs=float(a.load_az.abs().max()),saved_nodal_force_N_m=float(-(a.mass*a.load_az).sum()),
        position_double=bool(a.position_double.iloc[0]),stress_double=bool(a.stress_double.iloc[0]))
    for label,point in [('A',(.1,10)),('B',(1.25,8.75))]:
        k=int(np.argmin((initial.x-point[0])**2+(initial.z-point[1])**2))
        row[label+'_native_id']=int(a.id.iloc[k]);row[label+'_pressure_pa']=float(a.pressure.iloc[k])
        row[label+'_settlement_mm']=1000*float(initial.z.iloc[k]-a.z.iloc[k])
    return row


def main():
    receipt=TESTS/'logs'/(NAME+'.check.json');assert not receipt.exists()
    state=json.loads(STATE.read_text());assert state['status']=='completed_pending_review' and state['half_passed']
    verify(state)
    build=json.loads((TESTS/'logs/hydro_native_r1.build.json').read_text(encoding='utf-8-sig'))
    verify(build);assert bound(READER)['sha256'].lower()==build['executable_sha256'].lower()
    paths={'coarse':TESTS/'outputs'/f'{TAG}_drained_gpu_c',
           'half':TESTS/'outputs'/f'{TAG}_drained_gpu_h',
           'old':CASE/'CaseLianFlexibleStrip2D_PR_out'}
    arrays={};sources=[bound(__file__),bound(STATE),bound(READER),bound(TESTS/'scripts/lian_release_r1.py')]
    for key,folder in paths.items():
        if key!='old':
            run=next(r for r in state['runs'] if r['name'].endswith('_gpu_'+('c' if key=='coarse' else 'h')))
            assert run['exit_code']==0 and run['owned_exited'] and run['saved_frames']==61
            verify(run)
            assert 'NVIDIA GeForce RTX 3050' in (folder/'Run.out').read_text(errors='replace')
        print('Reading',key,'61 native frames',flush=True)
        with ThreadPoolExecutor(max_workers=2) as pool:arrays[key]=list(pool.map(lambda i:native(folder,i),range(61)))
        sources.extend(bound(folder/'data'/f'Part_{i:04d}.bi4') for i in range(61))
        sources.append(bound(folder/'Run.out'))
    origin=arrays['coarse'][0];top=origin.z.gt(9.99).to_numpy()
    assert len(origin)==20301
    for key in ('half','old'):
        assert np.array_equal(origin.id,arrays[key][0].id)
        assert np.array_equal(origin[['x','y','z']].to_numpy(dtype=np.float32),arrays[key][0][['x','y','z']].to_numpy(dtype=np.float32))
    rows=[];pairs=[]
    for i in range(61):
        a,b,o=[arrays[k][i] for k in ('coarse','half','old')]
        assert abs(float(a.time_s.iloc[0]-b.time_s.iloc[0]))<=1.01e-5
        assert abs(float(a.time_s.iloc[0]-o.time_s.iloc[0]))<=1.01e-5
        p=float(np.sqrt(np.mean((a.pressure-b.pressure)**2)))
        settlement=1000*float(np.max(abs(a.z.to_numpy()[top]-b.z.to_numpy()[top])))
        assert p<=5 and settlement<=.005,('Original independent half limits',i,p,settlement)
        for key in paths:
            row=describe(arrays[key][i],arrays[key][0]);row.update(run=key,part=i);rows.append(row)
        pairs.append(dict(part=i,coarse_time_s=float(a.time_s.iloc[0]),half_time_s=float(b.time_s.iloc[0]),old_time_s=float(o.time_s.iloc[0]),
            half_pressure_rms_pa=p,half_top_material_max_mm=settlement,
            new_minus_old_pressure_rms_pa=float(np.sqrt(np.mean((a.pressure-o.pressure)**2))),
            new_minus_old_sigma_zz_rms_pa=float(np.sqrt(np.mean((a.sigma_zz-o.sigma_zz)**2))),
            new_minus_old_top_mean_settlement_mm=1000*float((o.z.to_numpy()[top]-a.z.to_numpy()[top]).mean())))
    data=pd.DataFrame(rows);paired=pd.DataFrame(pairs)
    history=TESTS/'figures'/(NAME+'_history.csv');comparison=TESTS/'figures'/(NAME+'_pairs.csv')
    data.to_csv(history,index=False,float_format='%.17g');paired.to_csv(comparison,index=False,float_format='%.17g')
    fig,axes=plt.subplots(2,3,figsize=(14,7.5),layout='constrained')
    fields=['A_pressure_pa','B_pressure_pa','pressure_mean_pa','A_settlement_mm','B_settlement_mm','id1744_x_m']
    labels=['A native pore pressure (kPa)','B native pore pressure (kPa)','Soil mean pore pressure (kPa)',
            'A native settlement (mm)','B native settlement (mm)','Native1744 x (micrometres)']
    for key,color,style in [('old','#555555',':'),('coarse','#215a8a','-'),('half','#b56b28','--')]:
        d=data[data.run.eq(key)]
        for ax,col,label in zip(axes.flat,fields,labels):
            scale=1e-3 if col.endswith('_pressure_pa') or col=='pressure_mean_pa' else (1e6 if col=='id1744_x_m' else 1)
            ax.plot(d.time_s,d[col]*scale,style,color=color,label=key)
            ax.set(xlabel='Actual saved time (s)',ylabel=label);ax.grid(alpha=.2)
            ax.axvline(1,color='.75',lw=.7)
    axes[0,0].legend();fig.suptitle('Lian 3-s original mixed-slip / strict-strip control - old vs current is NOT stress-precision-only')
    png=TESTS/'figures'/(NAME+'_history.png');fig.savefig(png,dpi=160);plt.close(fig)
    a,o=arrays['coarse'][-1],arrays['old'][-1]
    point=origin[['x','z']].to_numpy();field=pd.DataFrame(dict(id=origin.id,x0_m=point[:,0],z0_m=point[:,1],old_pa=o.pressure,current_pa=a.pressure,difference_pa=a.pressure-o.pressure))
    field_csv=TESTS/'figures'/(NAME+'_fields.csv');field.to_csv(field_csv,index=False,float_format='%.17g')
    fig,axes=plt.subplots(1,3,figsize=(14,4.7),layout='constrained')
    maximum=max(float(a.pressure.max()),float(o.pressure.max()))/1000
    for ax,key,title in zip(axes,['old_pa','current_pa','difference_pa'],
                             [f'Old actual t={float(o.time_s.iloc[0]):.8f}s',f'Current t={float(a.time_s.iloc[0]):.8f}s','Current minus old (not theory error)']):
        if key=='difference_pa':
            v=max(abs(field[key].min()),abs(field[key].max()));levels=np.linspace(-v,v,31);values=field[key];cmap='RdBu_r';unit='Pressure difference (Pa)'
        else:levels=np.linspace(0,maximum,31);values=field[key]/1000;cmap='viridis';unit='Pore pressure (kPa)'
        artist=ax.tricontourf(point[:,0],point[:,1],values,levels=levels,cmap=cmap,extend='both')
        ax.set(title=title,xlabel='Initial material x (m)',ylabel='Initial material z (m)',aspect='equal');fig.colorbar(artist,ax=ax,label=unit,shrink=.75)
    fig.suptitle('Native-ID aligned 3-s pressure on initial material coordinates; max time mismatch10us')
    field_png=TESTS/'figures'/(NAME+'_fields.png');fig.savefig(field_png,dpi=160);plt.close(fig)
    event=data[data.time_s.between(.99999,1.00002)].to_dict('records')
    active=data[data.drainage_evaluated_active]
    assert active.all_orientation_drained_nodes.gt(0).all() and active.drained_abs_pressure_max_pa.eq(0).all()
    subprocess.run(['git','diff','--exit-code','--','src/source','src/VS'],cwd=REPO,check=True,capture_output=True)
    result=dict(passed=True,visual_review_passed=False,utc=utc(),scope='3-s safety/comparison admission, not late-cycle or FEM acceptance',
        sample_pairs=61,native_soil_count=20301,actual_final_times_s={k:float(v[-1].time_s.iloc[0]) for k,v in arrays.items()},
        half_max_pressure_rms_pa=float(paired.half_pressure_rms_pa.max()),half_max_top_material_mm=float(paired.half_top_material_max_mm.max()),
        new_old_final_pressure_rms_pa=float(paired.new_minus_old_pressure_rms_pa.iloc[-1]),
        new_old_final_top_mean_settlement_mm=float(paired.new_minus_old_top_mean_settlement_mm.iloc[-1]),
        final_rows=data[data.part.eq(60)].to_dict('records'),true_drained_node_sample_count=int(active.all_orientation_drained_nodes.sum()),
        true_drained_max_abs_pressure_pa=float(active.drained_abs_pressure_max_pa.max()),event_rows=event,
        event_policy='Source tests TimeStep>=1 at the prior integration-stage time. The near1s saved state can precede the first active boundary evaluation; no fixed-grid event alignment is enabled. All active samples including FSType2/3 and all normals are checked.',
        limitations=['Old initial positions are float; later PARTs may be double. Native IDs and old-representable geometry match.',
            'Old load telemetry is present but zero; its saved_nodal_force must not be interpreted as physically zero force.',
            'Old/current production versions differ beyond persistent stress precision; this is not an isolated precision A/B.',
            'No sampled1744 dropout occurs through3s; the first retained late dropout was near14.1s.',
            'Force quadrature remains13 nodes *0.1m, not the ideal1.25m strip width.',
            'A and B are nearest native material nodes, not exact FEM sample locations.'],
        sources=sources,artifacts=[bound(p) for p in (history,comparison,png,field_csv,field_png)])
    write_json(receipt,result)
    print(json.dumps({k:result[k] for k in ('passed','sample_pairs','half_max_pressure_rms_pa','half_max_top_material_mm','new_old_final_pressure_rms_pa','new_old_final_top_mean_settlement_mm','true_drained_node_sample_count')},indent=2))


if __name__=='__main__':main()
