"""One isolated symmetric-C frozen-field CPU observation; no integration or admission."""
import argparse
import json
import subprocess
import time
from pathlib import Path
import numpy as np
import pandas as pd
from cryer_load_pair_r1 import TESTS, native, bound, write_json
from cryer_radial_consistency_r1 import Reference
from cryer_radial_force_r1 import TAU, FOLDER, DATA, PREP as OLD_PREP, BUILD as OLD_BUILD

TAG='cryer_symc_cpu_r1'
BUILD=TESTS/'logs/cryer_symc_cpu_r1_seal_r2.build.json'
EXE=TESTS/'outputs/cryer_symc_cpu_build_r1/cryer_symc_cpu_r1.exe'
PATCH=EXE.parent/'JSphCpu.cpp'
HARNESS=TESTS/'support/cryer_symc_cpu_r1.cpp'
OLD=TESTS/'outputs/cryer_radial_force_r2_observation'
OLD_CHECK=TESTS/'logs/cryer_radial_force_r2.check.json'
OPEN_CHECK=TESTS/'logs/cryer_darcy_open_screen_r1.check.json'
OPEN_CSV=TESTS/'figures/cryer_darcy_open_screen_r1_regions.csv'
RADIAL=TESTS/'logs/cryer_radial_consistency_r1.check.json'
OUT=TESTS/'outputs'/(TAG+'_observation')
INPUTS=TESTS/'logs'/(TAG+'.inputs.json')
RUN=TESTS/'logs'/(TAG+'.run.json')
COMPLETE=TESTS/'logs'/(TAG+'.completion.json')
CHECK=TESTS/'logs'/(TAG+'.check.json')
STDOUT=TESTS/'logs'/(TAG+'.stdout.log')
TABLE=TESTS/'figures'/(TAG+'_regions.csv')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def verify(entries):
    for entry in entries:
        actual=bound(entry['path'])
        assert actual['sha256'].lower()==entry['sha256'].lower(),entry['path']
        assert actual['bytes']==entry['bytes'],entry['path']


def seal(path,record):
    with path.open('x',encoding='utf8') as stream:
        json.dump(record,stream,indent=2,allow_nan=False)


def no_owned_observer():
    command="@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cryer_symc_cpu_r1.exe' } | Select-Object ProcessId,ExecutablePath) | ConvertTo-Json -Compress"
    result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,check=True)
    assert not result.stdout.strip() or json.loads(result.stdout)==[],'An observer with this executable name is alive'


def prerequisites():
    old=read(OLD_CHECK);build=read(BUILD);prepared=read(OLD_PREP);screen=read(OPEN_CHECK)
    assert old['analysis_checks_passed'] and screen['analysis_checks_passed']
    assert build['status']=='built_not_run' and build['configuration']=='DebugCPU'
    assert build['source_comparison']['exact_normalized_source_is_single_Darcy_replacement']
    assert build['protected_frozen_inputs_verified'] and build['canonical_programs_unchanged_during_offline_seal']
    assert build['Lian_runtime_verified'] and not build['probe_executed'] and not build['solver_launched']
    verify(prepared['inputs']+old['inputs']+old['artifacts']+build['inputs']+build['runtime']+[build['program']])
    assert Path(build['program']['path']).resolve()==EXE.resolve()
    expected={str(Path(x['path']).resolve()).lower() for x in build['inputs']}
    assert str(PATCH.resolve()).lower() in expected and str(HARNESS.resolve()).lower() in expected
    verify([x for x in screen['artifacts'] if Path(x['path']).resolve()==OPEN_CSV.resolve()])
    assert any(Path(x['path']).resolve()==OPEN_CSV.resolve() for x in screen['artifacts'])
    paths=[Path(__file__),OLD_PREP,OLD_BUILD,BUILD,EXE,PATCH,HARNESS,DATA,
        OLD_CHECK,OLD/'radial_rates.csv',OLD/'radial_summary.json',OPEN_CHECK,OPEN_CSV,RADIAL,
        TESTS/'support/cryer_load_pair_r1.py',TESTS/'support/cryer_radial_force_r1.py',
        TESTS/'support/cryer_radial_consistency_r1.py',FOLDER/'data/Part_0000.bi4',
        FOLDER/'cryer_preload_peak_r1.xml',FOLDER/'cryer_preload_peak_r1.bi4']
    return [bound(path) for path in paths]


def run():
    assert not any(path.exists() for path in [OUT,INPUTS,RUN,COMPLETE,CHECK,TABLE,STDOUT]),'Never restart or overwrite this label'
    links=prerequisites();no_owned_observer()
    seal(INPUTS,dict(inputs=links,integrated_steps=0,physical_acceptance=False,fields_regenerated=False))
    command=[str(EXE),str(DATA),'-cpu','-ompthreads:8',str(FOLDER/'cryer_preload_peak_r1'),str(OUT),'-dirdataout','data']
    started=time.perf_counter()
    with STDOUT.open('xb') as output:
        process=subprocess.Popen(command,cwd=TESTS,stdout=output,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        record=dict(status='nonintegrating_observer_running',owned_pid=process.pid,command=command,
            program=bound(EXE),inputs=bound(INPUTS),physical_solver=False,integrated_steps=0)
        write_json(RUN,record);print('OBSERVING',process.pid,flush=True);code=process.wait()
    record.update(status='observer_exited',exit_code=code,owned_exited=True,wall_seconds=time.perf_counter()-started)
    write_json(RUN,record)
    # Preserve normal/failed execution before any new numerical review.
    outputs=[bound(path) for path in sorted(OUT.rglob('*')) if path.is_file()] if OUT.exists() else []
    seal(COMPLETE,dict(exit_code=code,owned_exited=True,integrated_steps=0,
        inputs=[bound(INPUTS),bound(RUN),bound(STDOUT)],outputs=outputs))
    assert code==0,'Retain failed observer evidence; do not rerun this label'
    review()


def review():
    assert not CHECK.exists() and not TABLE.exists(),'Never overwrite a retained review'
    complete=read(COMPLETE);record=read(RUN)
    assert complete['exit_code']==record['exit_code']==0 and complete['owned_exited'] and record['owned_exited']
    verify(read(INPUTS)['inputs']);verify(complete['inputs']+complete['outputs']);no_owned_observer()
    summary=read(OUT/'radial_summary.json')
    assert summary['completed'] and summary['isolated_symc_candidate'] and summary['integrated_steps']==0
    assert summary['geometry_unchanged'] and summary['actual_drainage_active'] and summary['drained_count']==5153
    assert summary['native_soil_count']==37173 and summary['tau_s']==TAU
    oldsummary=read(OLD/'radial_summary.json')
    assert all(summary[key]==oldsummary[key] for key in ['source_clock_s','tau_s','original_viscosity'])
    a=native(FOLDER,0).sort_values('id').reset_index(drop=True)
    b=pd.read_csv(OUT/'radial_rates.csv',float_precision='round_trip').sort_values('id').reset_index(drop=True)
    old=pd.read_csv(OLD/'radial_rates.csv',float_precision='round_trip').sort_values('id').reset_index(drop=True)
    assert list(b.columns)==list(old.columns) and len(a)==len(b)==len(old)==37173
    assert a.id.nunique()==37173 and np.array_equal(a.id,b.id) and np.array_equal(b.id,old.id)
    assert np.isfinite(a.to_numpy()).all() and np.isfinite(b.to_numpy()).all() and np.isfinite(old.to_numpy()).all()
    assert a.nout.eq(0).all() and a.position_double.eq(1).all() and a.stress_double.eq(1).all()
    assert a.rho.eq(2100).all() and (a[['mass','h','dp']].to_numpy()>0).all()
    assert np.array_equal(a[['x','y','z']].to_numpy().view('<u8'),b[['x','y','z']].to_numpy().view('<u8'))
    assert np.array_equal(a.fstype,b.fstype) and np.array_equal(b.fstype,old.fstype)
    geometry=['x','y','z']
    assert np.array_equal(b[geometry].to_numpy().view('<u8'),old[geometry].to_numpy().view('<u8'))
    unchanged=['compression_rate_pa_s','ax','ay','az','raw_ax','raw_ay','raw_az']
    for column in unchanged:
        assert np.array_equal(b[column].to_numpy('<f4').view('<u4'),old[column].to_numpy('<f4').view('<u4')),column+' changed'
    ratecols=['pressure_rate_pa_s','compression_rate_pa_s','darcy_rate_pa_s','novisc_pressure_rate_pa_s']
    rates=b[ratecols].to_numpy();oldrates=old[ratecols].to_numpy()
    assert np.array_equal(rates[:,0].astype('<f4').view('<u4'),rates[:,3].astype('<f4').view('<u4'))
    surface=a.fstype.isin([2,3]).to_numpy();assert surface.sum()==5153 and not np.count_nonzero(rates[surface])
    identity=rates[:,0]-rates[:,1]-rates[:,2]
    budget=2*np.finfo(np.float32).eps*np.abs(rates[:,:3]).sum(axis=1)+1e-5
    assert np.all(abs(identity)<=budget),'Original float decomposition budget failed'
    radius=np.linalg.norm(a[['x','y','z']].to_numpy(),axis=1);h=float(a.h.iloc[0])
    exact=Reference().field(radius,TAU);ctes=read(RADIAL)['constants'];cpu=ctes['backends']['CPU'];gpu=ctes['backends']['GPU']
    cpuk=cpu['kwn_pa']*ctes['conductivity_float_m_s']/(ctes['water_rho_float_kg_m3']*cpu['ghyd_m_s2'])
    gpuk=gpu['kwn_pa']*ctes['conductivity_float_m_s']/(ctes['water_rho_float_kg_m3']*gpu['ghyd_m_s2'])
    center=a.id.isin(read(TESTS/'logs/cryer_preload_peak_r1.run.json')['center_fixed_material_ids']).to_numpy()
    groups=dict(center18=center,full_support_core=radius<.05-2*h,
        near_surface_interior=(radius>=.05-2*h)&~surface,nondrained=~surface,drained=surface)
    assert center.sum()==18
    openrows=pd.read_csv(OPEN_CSV);volume=(a.mass/a.rho).to_numpy();rows=[]
    for region,mask in groups.items():
        row=dict(region=region,count=int(mask.sum()),tau_s=TAU,volume_m3=float(volume[mask].sum()))
        measures=dict(exact_rate_pa_s=exact['pt'],actual_net_pa_s=rates[:,0],actual_comp_pa_s=rates[:,1],
            actual_darcy_pa_s=rates[:,2],actual_net_error_pa_s=rates[:,0]-exact['pt'],
            actual_comp_error_pa_s=rates[:,1]+cpu['kwn_pa']*exact['div'],
            actual_darcy_error_pa_s=rates[:,2]-cpuk*exact['lap'],old_net_pa_s=oldrates[:,0],
            old_comp_pa_s=oldrates[:,1],old_darcy_pa_s=oldrates[:,2],old_net_error_pa_s=oldrates[:,0]-exact['pt'],
            new_minus_old_net_pa_s=rates[:,0]-oldrates[:,0],new_minus_old_darcy_pa_s=rates[:,2]-oldrates[:,2],
            rounding_identity_pa_s=identity)
        for key,value in measures.items():
            row.update({key+'_mean':float(np.average(value[mask],weights=volume[mask])),
                key+'_rms':float(np.sqrt(np.average(value[mask]**2,weights=volume[mask]))),
                key+'_absmax':float(abs(value[mask]).max())})
        observed=openrows[(openrows.stencil=='symmetric_C')&(openrows.denominator=='r2_plus_eta2')&
            (openrows.region==region)&np.isclose(openrows.tau_s,TAU,rtol=0,atol=1e-14)]
        if not observed.empty:
            assert len(observed)==1 and int(observed.iloc[0]['count'])==int(mask.sum())
            op=observed.iloc[0];row['open_screen_gpu_scalar_darcy_mean_pa_s']=float(op.darcy_pa_s_mean)
            row['open_screen_cpu_rescaled_darcy_mean_pa_s']=float(op.darcy_pa_s_mean*cpuk/gpuk)
            row['actual_minus_open_cpu_rescaled_darcy_mean_pa_s']=row['actual_darcy_pa_s_mean']-row['open_screen_cpu_rescaled_darcy_mean_pa_s']
        rows.append(row)
    pd.DataFrame(rows).to_csv(TABLE,index=False,float_format='%.17g')
    result=dict(analysis_checks_passed=True,physical_acceptance=False,production_implemented=False,
        physical_solver_executed=False,integrated_steps=0,actual_drainage_active=True,
        compression_and_all_six_acceleration_float_bits_0ulp=True,geometry_and_fstype_unchanged=True,
        viscosity_pressure_0ulp=True,drained_count=5153,drained_all_four_rates_zero=True,
        original_float_decomposition_budget_passed=True,rows=rows,
        inputs=[bound(INPUTS),bound(RUN),bound(COMPLETE),bound(__file__)],
        artifacts=[bound(TABLE),bound(OUT/'radial_rates.csv'),bound(OUT/'radial_summary.json'),bound(STDOUT)],
        limitations=['One sealed manufactured field on original geometry; zero integrated steps and no formal or peak admission.',
            'Only isolated soil-soil Darcy uses symmetric C. Unchanged compression and momentum must be bitwise identical to actual r2 control.',
            'Quasistatic exact rates are operator references, not an exact dynamic trajectory.',
            'Drained receiver rates are clamped to zero; their unmodified continuum derivative is not an evolved operator target.',
            'Open-screen comparison uses GPU scalar offline double sums; CPU-rescaled mean is diagnostic, not a new physical error gate or backend replay.',
            'Old build wrapper interruption and offline seal repair are retained in the bound build record; this driver does not relabel that wrapper as normal.',
            'The seal has no recovered prebuild SHA for a previously relinked canonical CPU Debug program. That executable is not this probe input; candidate and all actual probe dependencies are separately bound.'])
    seal(CHECK,result);print('REVIEW_PASSED',str(CHECK),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    actions=parser.add_mutually_exclusive_group();actions.add_argument('--run',action='store_true');actions.add_argument('--review',action='store_true')
    args=parser.parse_args()
    if args.run:run()
    elif args.review:review()
    else:parser.print_help()
