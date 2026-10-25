"""Independent offline audit of all retained 3-D boundary pulse results."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from spr_planes_run import TESTS,bound


def main():
    receipt=TESTS/'logs/spr_3d_audit_r1.check.json';assert not receipt.exists()
    snapshot=TESTS/'logs/spr_3d_precleanup_r1.snapshot.json';archives=json.loads(snapshot.read_text())['files']
    seen={};resolved=[];evidence=[bound(__file__),bound(snapshot)]
    def verify(item):
        key=(item['path'],item['sha256'])
        if key in seen:return
        path=Path(item['path'])
        if bound(path)['sha256']!=item['sha256']:
            found=[x for x in archives if x['original_path']==str(path) and x['sha256']==item['sha256']]
            assert len(found)==1,(str(path),'Hash changed without a matching frozen archive')
            path=Path(found[0]['archive_path']);assert bound(path)['sha256']==item['sha256']
            resolved.append(dict(original_path=item['path'],archive_path=str(path),sha256=item['sha256']))
        seen[key]=str(path)
    state=TESTS/'logs/spr_3d_next_r1.status.json';sequence=json.loads(state.read_text());assert sequence['status']=='completed_pending_visual_review'
    evidence.append(bound(state))
    for item in sequence['inputs']:verify(item)
    for stage in sequence['stages']:
        if 'exit_code' in stage:assert stage['exit_code']==0 and stage['owned_exited']
        for key in ['status','review','log']:
            if key in stage:verify(stage[key])
    cleanup=TESTS/'logs/spr_3d_cleanup_r1.check.json';fix=json.loads(cleanup.read_text());assert fix['passed'] and fix['new_memcheck_errors_each']==0 and fix['nonzero_observer_native_fields_0ulp']
    for item in fix['evidence']:verify(item)
    evidence.append(bound(cleanup));summary=[];details=[];halves=[];crosses=[]
    for geometry in ['edge3','corner3']:
        for slip in [2,3]:
            tag=f'spr_3d_r1_{geometry}_s{slip}';frames={};metrics={};configurations={}
            review_path=TESTS/'logs'/(tag+'.review.json');review=json.loads(review_path.read_text());assert review['passed']
            evidence.append(bound(review_path))
            for item in review['evidence']+review['outputs']:verify(item)
            for backend in ['cpu','gpu']:
                status_path=TESTS/'logs'/(tag+'_'+backend+'.status.json');r=json.loads(status_path.read_text());assert r['passed'] and len(r['runs'])==2
                evidence.append(bound(status_path))
                for item in r['inputs']+r['outputs']:verify(item)
                build_item=next(x for x in r['inputs'] if x['path'].endswith('.build.json'));build=json.loads(Path(build_item['path']).read_text(encoding='utf-8-sig'))
                assert bound(build['executable'])['sha256']==build['executable_sha256']
                for item in build['inputs']+build.get('runtime',[]):verify(item)
                for run in r['runs']:
                    assert run['exit_code']==0 and run['owned_exited'];done=run['completion'];phase=run['name'][-1];dt=1e-6 if phase=='c' else 5e-7
                    assert done['completed'] and done['steps']==(2000 if phase=='c' else 4000) and done['dt_s']==dt and abs(done['actual_time_s']-.002)<1e-11
                    assert done['max_fixed_dt_minus_mechanical_limit_s']<=0 and done['pore_dt_limit_s']>=dt
                    assert done['native_count']==(2704 if geometry=='edge3' else 2107)
                    for item in run['outputs']+run['generated_inputs']+[run['definition'],run['log'],run['gencase_log']]:verify(item)
                    configuration=ET.parse(run['definition']['path']).getroot();configurations[backend,phase]=configuration
                    params={x.get('key'):x.get('value') for x in configuration.findall('execution/parameters/parameter')}
                    assert params['SlipMode']==str(slip) and params['NoPenetration']=='0' and params['SoilBoundaryDerivativeSPR']=='1' and params['SoilHourglassXi']=='0'
                    assert params['SoilDamping']=='0' and params['DPCtes']=='1'
                    folder=TESTS/'outputs'/run['name'];f=pd.read_csv(folder/'pulse.csv',float_precision='round_trip').sort_values(['step','id']).reset_index(drop=True)
                    n=1600 if geometry=='edge3' else 1000;assert len(f)==201*n and f.id.nunique()==n and not f.duplicated(['step','id']).any()
                    assert np.isfinite(f.to_numpy()).all() and f.rho.gt(0).all() and f.kplastic.eq(0).all()
                    ids=f.id.to_numpy().reshape(201,n);assert np.array_equal(ids,np.tile(ids[0],(201,1)))
                    times=f.time_s.to_numpy().reshape(201,n);assert abs(times-np.arange(201)[:,None]*1e-5).max()<1e-11
                    assert f.x.gt(0).all() and f.z.gt(0).all() and (geometry!='corner3' or f.y.gt(0).all())
                    initial=f.iloc[:n];expected=np.column_stack([-.001*initial.x,-.0007*initial.y,-.0013*initial.z]).astype('float32').astype('float64')
                    assert np.array_equal(initial[['vx','vy','vz']].to_numpy(),expected)
                    energy=pd.read_csv(folder/'energy.csv',float_precision='round_trip');assert len(energy)==201 and np.isfinite(energy.to_numpy()).all()
                    energy_ratio=float(energy.total_J.max()/energy.total_J.iloc[0]);assert energy_ratio<=1.1 and abs(energy_ratio-run['energy_ratio_max'])<1e-14
                    last=f.iloc[-n:];positions=f[['x','y','z']].to_numpy().reshape(201,n,3)
                    details.append(dict(geometry=geometry,slip=slip,backend=backend,phase=phase,soil_count=n,actual_time_s=done['actual_time_s'],energy_ratio_max=energy_ratio,
                        pressure_peak_pa=float(f.pressure.max()),pressure_min_pa=float(f.pressure.min()),pressure_final_mean_pa=float(last.pressure.mean()),
                        motion_max_mm=float(np.linalg.norm(positions-positions[0],axis=2).max()*1000),
                        sigma_component_abs_max_pa=float(abs(f[['sxx','syy','szz','sxy','syz','sxz']]).to_numpy().max()),
                        minimum_fixed_plane_distance_m=float(min(f.x.min(),f.z.min(),f.y.min() if geometry=='corner3' else float('inf'))),observed_wall_s=run['observed_wall_s']))
                    frames[backend,phase]=f
                c,h=frames[backend,'c'],frames[backend,'h'];assert np.array_equal(c.id,h.id)
                n=int(c.step.eq(0).sum());p=(c.pressure.to_numpy()-h.pressure.to_numpy()).reshape(201,n)
                u=(c[['x','y','z']].to_numpy()-h[['x','y','z']].to_numpy()).reshape(201,n,3)
                pressure=np.sqrt(np.einsum('ij,ij->i',p,p)/n);motion=np.sqrt(np.sum(u*u,axis=2)).max(axis=1)*1000
                assert np.all(pressure<=.5) and np.all(motion<=1e-5)
                old=pd.read_csv(TESTS/'figures'/(tag+'_'+backend+'_half.csv'),float_precision='round_trip')
                assert np.allclose(pressure,old.pressure_rms_pa,rtol=1e-12,atol=1e-13) and np.allclose(motion,old.material_max_mm,rtol=1e-12,atol=1e-15)
                vertical=((c.pressure-c.szz)-(h.pressure-h.szz)).to_numpy().reshape(201,n)
                vertical_rms=np.sqrt(np.mean(vertical*vertical,axis=1))
                halves.append(dict(geometry=geometry,slip=slip,backend=backend,pressure_rms_max_pa=float(pressure.max()),material_max_mm=float(motion.max()),vertical_total_stress_rms_max_pa=float(vertical_rms.max())))
                metrics[backend]=(float(pressure.max()),float(motion.max()))
            cross_rows=[]
            for phase in ['c','h']:
                a,b=frames['cpu',phase],frames['gpu',phase];assert np.array_equal(a.id,b.id) and abs(a.time_s-b.time_s).max()<1e-11
                n=int(a.step.eq(0).sum());p=(a.pressure.to_numpy()-b.pressure.to_numpy()).reshape(201,n)
                u=(a[['x','y','z']].to_numpy()-b[['x','y','z']].to_numpy()).reshape(201,n,3)
                pp=np.sqrt(np.einsum('ij,ij->i',p,p)/n);uu=np.sqrt(np.sum(u*u,axis=2)).max(axis=1)*1000
                assert np.all(pp<=.5) and np.all(uu<=1e-5)
                cross_rows.append((float(pp.max()),float(uu.max())));crosses.append(dict(geometry=geometry,slip=slip,phase=phase,pressure_rms_max_pa=float(pp.max()),material_max_mm=float(uu.max())))
            summary.append(dict(geometry=geometry,slip=slip,cpu_half_p_pa=metrics['cpu'][0],gpu_half_p_pa=metrics['gpu'][0],half_movement_max_mm=max(x[1] for x in metrics.values()),
                cross_p_pa=max(x[0] for x in cross_rows),cross_movement_max_mm=max(x[1] for x in cross_rows)))
            print('Rehashed and independently recomputed:',tag,flush=True)
    outputs=[]
    for name,rows in [('summary',summary),('native_summary',details),('half_summary',halves),('cross_summary',crosses)]:
        path=TESTS/'figures'/('spr_3d_audit_r1_'+name+'.csv');pd.DataFrame(rows).to_csv(path,index=False,mode='x');outputs.append(bound(path))
    result=dict(passed=True,visual_inspected=False,physical_acceptance=False,raw_runs=16,independent_half_pairs=8,cross_pairs=8,samples_each=201,
        reverified_unique_hashes=len(seen),frozen_archive_resolutions=resolved,summary=summary,energy_ratio_max=max(x['energy_ratio_max'] for x in details),
        final_times_s=sorted(set(x['actual_time_s'] for x in details)),evidence=evidence,outputs=outputs,
        limitations=['Static planar edge/corner, 2ms elastic with XYZ velocities only','NoSlip startup tangential mismatch is not an affine theory solution','HG/NoPen/damping/drainage/load off','No full 3D consolidation/plastic/curved/moving/large-rotation/exact-HG-restart acceptance'])
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','outputs','frozen_archive_resolutions')},indent=2))


if __name__=='__main__':main()
