"""Prepare/review one frozen CPU fused-loop observation; never a physical solve."""
import argparse
import json
import struct
import subprocess
import time
import numpy as np
import pandas as pd
from cryer_radial_consistency_r1 import Reference
from cryer_load_pair_r1 import TESTS, REPO, native, bound, write_json

TAG='cryer_radial_force_r1'
TAU=.0420518020252
FOLDER=TESTS/'outputs/cryer_preload_peak_r1'
DATA=TESTS/'outputs'/(TAG+'_fields.bin')
PREP=TESTS/'logs'/(TAG+'.inputs.json')
OUT=TESTS/'outputs'/(TAG+'_observation')
BUILD=TESTS/'logs'/(TAG+'.build.json')


def prepare():
    assert not DATA.exists() and not PREP.exists()
    prior=TESTS/'logs/cryer_radial_consistency_r1.check.json'
    receipt=json.loads(prior.read_text()); assert receipt['analysis_checks_passed']
    for b in receipt['inputs']+receipt['artifacts']:
        assert bound(b['path'])['sha256']==b['sha256'],b['path']
    a=native(FOLDER,0); x=a[['x','y','z']].to_numpy(); r=np.linalg.norm(x,axis=1)
    f=Reference().field(r,TAU); surface=a.fstype.isin([2,3]).to_numpy(); f['p'][surface]=0
    er=x/r[:,None]; tensor=f['st'][:,None,None]*np.eye(3)+(f['sr']-f['st'])[:,None,None]*er[:,:,None]*er[:,None,:]
    values=np.column_stack([x,f['p'],x*f['v_over_r'][:,None],tensor[:,0,0],tensor[:,1,1],tensor[:,2,2],tensor[:,0,1],tensor[:,1,2],tensor[:,0,2]])
    assert values.shape==(37173,13) and np.isfinite(values).all()
    dtype=np.dtype([('id','<u4'),('values','<f8',(13,))]); records=np.empty(len(a),dtype=dtype)
    records['id']=a.id.to_numpy(); records['values']=values
    with DATA.open('xb') as out:
        out.write(struct.pack('<IId',0x43524631,len(a),TAU));out.write(records.tobytes())
    write_json(PREP,dict(scope='One frozen quasistatic field, four fused-loop queries, zero integrated steps.',
        tau_s=TAU,source_clock_s=.0078125+TAU,inputs=[bound(prior),bound(__file__),bound(DATA),
            bound(FOLDER/'cryer_preload_peak_r1.xml'),bound(FOLDER/'cryer_preload_peak_r1.bi4')],
        storage='Actual float pressure/velocity, double stress; harness-only PorePress0 assigned as inert scratch.',
        physical_acceptance=False,solver_admitted=False))
    print('Prepared one frozen field; no executable was launched.',flush=True)


def run():
    target=TESTS/'logs'/(TAG+'.check.json'); runtime=TESTS/'logs'/(TAG+'.run.json')
    assert not target.exists() and not runtime.exists() and not OUT.exists()
    prep=json.loads(PREP.read_text()); build=json.loads(BUILD.read_text(encoding='utf-8-sig'))
    assert build['status']=='built_not_run' and build['configuration']=='DebugCPU'
    for entry in prep['inputs']+build['inputs']+build['runtime']:
        assert bound(entry['path'])['sha256'].lower()==entry['sha256'].lower(),entry['path']
    exe=TESTS/'outputs'/ (TAG+'_dbg')/(TAG+'.exe')
    command=[str(exe),str(DATA),'-cpu','-omp:8',str(FOLDER/'cryer_preload_peak_r1'),str(OUT),'-dirdataout','data']
    started=time.perf_counter(); log=TESTS/'logs'/(TAG+'.stdout.log')
    with log.open('xb') as output:
        process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
        write_json(runtime,dict(status='nonintegrating_observer_running',owned_pid=process.pid,
            command=command,program=bound(exe),prepared=bound(PREP),build=bound(BUILD),physical_solver=False))
        code=process.wait()
    runrecord=json.loads(runtime.read_text());runrecord.update(exit_code=code,owned_exited=True,
        wall_seconds=time.perf_counter()-started,status='observer_exited')
    write_json(runtime,runrecord)
    assert code==0,'Frozen companion failed; inspect retained stdout/Run.out, do not rerun this label'
    review()


def review():
    target=TESTS/'logs'/(TAG+'.check.json'); runtime=TESTS/'logs'/(TAG+'.run.json')
    log=TESTS/'logs'/(TAG+'.stdout.log')
    assert not target.exists(),'Do not overwrite a retained review'
    runrecord=json.loads(runtime.read_text())
    assert runrecord['exit_code']==0 and runrecord['owned_exited']
    summary=json.loads((OUT/'radial_summary.json').read_text())
    assert summary['completed'] and summary['integrated_steps']==0 and summary['drained_count']==5153
    a=native(FOLDER,0).sort_values('id').reset_index(drop=True)
    b=pd.read_csv(OUT/'radial_rates.csv',float_precision='round_trip').sort_values('id').reset_index(drop=True)
    assert len(a)==len(b)==37173 and np.array_equal(a.id,b.id)
    assert np.isfinite(b.to_numpy()).all() and np.array_equal(a[['x','y','z']],b[['x','y','z']])
    assert np.array_equal(a.fstype,b.fstype)
    surface=b.fstype.isin([2,3]).to_numpy(); assert int(surface.sum())==5153
    rates=b[['pressure_rate_pa_s','compression_rate_pa_s','darcy_rate_pa_s','novisc_pressure_rate_pa_s']].to_numpy()
    assert np.array_equal(rates[:,0].astype('<f4').view('<u4'),rates[:,3].astype('<f4').view('<u4')),'Viscosity unexpectedly changed the pressure operator'
    assert np.count_nonzero(rates[surface])==0
    identity=rates[:,0]-rates[:,1]-rates[:,2]
    # Bound only final binary32 rounding and double summation; not a physical half-step criterion.
    arithmetic_bound=2*np.finfo(np.float32).eps*np.abs(rates[:,:3]).sum(axis=1)+1e-5
    assert np.all(abs(identity)<=arithmetic_bound)
    offline=json.loads((TESTS/'logs/cryer_radial_consistency_r1.check.json').read_text())
    fields=np.load(TESTS/'figures/cryer_radial_consistency_r1.npz')
    lookup=np.argsort(fields['id']); exact=fields['t2_exact_pt'][lookup]
    comp=fields['t2_comp_error'][lookup]; darcy=fields['t2_darcy_error'][lookup]
    ref=Reference(); r=np.linalg.norm(a[['x','y','z']].to_numpy(),axis=1); f=ref.field(r,TAU)
    cpu=offline['constants']['backends']['CPU']; mf=cpu['kwn_pa']
    kap=offline['constants']['conductivity_float_m_s']/(offline['constants']['water_rho_float_kg_m3']*cpu['ghyd_m_s2'])
    gpu=offline['constants']['backends']['GPU']; mg=gpu['kwn_pa']
    kg=offline['constants']['conductivity_float_m_s']/(offline['constants']['water_rho_float_kg_m3']*gpu['ghyd_m_s2'])
    # NPZ stores GPU-scalar errors. Reconstruct the actual shared offline div/lap first.
    div=f['div']-comp/mg; lap=f['lap']+darcy/(mg*kg)
    offcomp=-mf*div; offdarcy=mf*kap*lap
    center=a.id.isin(json.loads((TESTS/'logs/cryer_preload_peak_r1.run.json').read_text())['center_fixed_material_ids']).to_numpy()
    h=float(a.h.iloc[0]); groups=dict(center18=center,full_support_core=r<.05-2*h,
        near_surface_interior=(r>=.05-2*h)&~surface,nondrained=~surface)
    rows=[]
    for region,mask in groups.items():
        row=dict(region=region,count=int(mask.sum()))
        measures=dict(exact_rate_pa_s=exact,actual_net_pa_s=rates[:,0],actual_comp_pa_s=rates[:,1],
            actual_darcy_pa_s=rates[:,2],actual_net_error_pa_s=rates[:,0]-exact,
            actual_minus_offline_net_pa_s=rates[:,0]-offcomp-offdarcy,
            actual_minus_offline_comp_pa_s=rates[:,1]-offcomp,
            actual_minus_offline_darcy_pa_s=rates[:,2]-offdarcy,rounding_identity_pa_s=identity,
            actual_raw_force_m_s2=np.linalg.norm(b[['raw_ax','raw_ay','raw_az']].to_numpy(),axis=1),
            viscosity_contribution_m_s2=np.linalg.norm(b[['ax','ay','az']].to_numpy()-b[['raw_ax','raw_ay','raw_az']].to_numpy(),axis=1))
        for key,value in measures.items():
            row[key+'_mean']=float(value[mask].mean());row[key+'_rms']=float(np.sqrt(np.mean(value[mask]**2)))
        rows.append(row)
    table=TESTS/'figures'/(TAG+'_regions.csv');pd.DataFrame(rows).to_csv(table,index=False,float_format='%.17g')
    result=dict(analysis_checks_passed=True,physical_acceptance=False,solver_executed=False,
        production_implemented=False,integrated_steps=0,actual_drainage_active=True,
        viscosity_pressure_0ulp=True,drained_rate_pressure_zero=True,rows=rows,
        inputs=[bound(PREP),bound(BUILD),bound(runtime),bound(__file__),bound(TESTS/'logs/cryer_radial_consistency_r1.check.json')],
        artifacts=[bound(OUT/'radial_rates.csv'),bound(OUT/'radial_summary.json'),bound(table),bound(log)],
        limitations=['One initial-geometry manufactured tau; not actual evolving geometry or a time-integrated solution.',
            'CPU Debug fused kernel with original viscosity; damping is outside this observed kernel.',
            'Fourth call disables viscosity only to separate raw momentum; it is not a physical trajectory.',
            'Separate float outputs need not sum bitwise; arithmetic rounding bound is not a physical error gate.',
            'Offline double distance/cell-order differences remain. No new boundary, operator or formal run admitted.'])
    write_json(target,result)
    print(json.dumps(dict(analysis_checks_passed=True,integrated_steps=0,wall_seconds=runrecord['wall_seconds'],center=rows[0])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');p.add_argument('--run',action='store_true');p.add_argument('--review',action='store_true')
    args=p.parse_args()
    if args.prepare: prepare()
    elif args.run: run()
    elif args.review: review()
    else:p.print_help()
