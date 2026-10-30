"""Fresh gravity-only Stage1 startup checks; default help, no automatic long run."""
import argparse
import ast
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

TESTS = Path(__file__).resolve().parents[1]
CASE, REPO = TESTS.parent, TESTS.parents[3]
C02 = CASE.parent / '02_TerzaghiConsolidation_q0_PR/tests'
C04 = CASE.parent / '04_CryerProblem_PR/tests'
sys.path.insert(0, str(C04 / 'support'))
from cryer_start_r1 import native, bound, utc
sys.path.insert(0, str(C02 / 'support'))
from symc_1d_short_r1 import read, seal, verify, unique, inventory

TAG = 'sw_stage1_short_r1'
LOGS, CONFIGS, OUTPUTS, FIGURES = [TESTS / d for d in ['logs', 'configs', 'outputs', 'figures']]
PREP, RUN, CHECK = [LOGS / (TAG + s) for s in ['.inputs.json', '.run.json', '.check.json']]
TEMPLATE = CASE / 'CaseSelfWeightConsolidation_Stage1_Def.xml'
NOTE = TESTS / 'notes' / (TAG + '.json')
READER = CASE.parent / '05_LianFlexibleStrip2D_PR/tests/outputs/hydro_native_r1/ReadHydroNative.exe'
READER_SOURCE = CASE.parent / '05_LianFlexibleStrip2D_PR/tests/scripts/read_hydro_native.cpp'
JOBS = [('cpu_c', 'cpu', '0.000001', 2000, 40), ('gpu_c', 'gpu', '0.000001', 2000, 40),
        ('gpu_h', 'gpu', '0.0000005', 4000, 80)]
END, INTERVAL = .002, .0005


def expected(spec, program):
    suffix, backend, dt, steps, shepard = spec; name = TAG + '_' + suffix
    text = TEMPLATE.read_text(encoding='utf8')
    assert all(k not in text for k in ['PoreDarcySymmetricCorr', 'SoilHourglassXi', 'SoilBoundaryDerivativeSPR'])
    for key, value in [('SavePosDouble', '1'), ('DtIni', dt), ('DtFixed', dt), ('TimeMax', '0.002'), ('TimeOut', '0.0005')]:
        text, n = re.subn(r'(<parameter key="' + key + r'" value=")[^"]+(" comment=")[^"]+("[^\n]+)',
            lambda m: m[1] + value + m[2] + 'Fresh Stage1 short diagnostic; no equilibrium acceptance' + m[3], text)
        assert n == 1, key
    if shepard == 80:
        text, n = re.subn(r'(<PoreShepardInterval value=")40(" comment=")[^"]+("[^\n]+)',
            lambda m: m[1] + '80' + m[2] + 'Half step: retain 40 microsecond physical Shepard cadence' + m[3], text)
        assert n == 1
    exe = os.path.relpath(program, CASE).replace('\\', '/')
    bat = ('@echo off\nsetlocal\ncd /d "%~dp0\\..\\.."\n\n' + f'set name={name}\nset dirout=tests/outputs/%name%\n'
        'set dirbin=../../../bin/windows\nset gencase="%dirbin%/GenCase_win64.exe"\n' + f'set dualsphysics="{exe}"\n\n'
        'if exist "%dirout%" goto fail\n%gencase% "tests/configs/%name%_Def" "%dirout%/%name%" -save:all\n'
        'if not "%ERRORLEVEL%" == "0" goto fail\n' + f'%dualsphysics% -{backend} -ompthreads:1 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -nsteps:{steps}\n'
        'if not "%ERRORLEVEL%" == "0" goto fail\nexit /b 0\n\n:fail\necho Existing/partial data preserved.\nexit /b 1\n')
    return text, bat


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    for spec in JOBS:
        text, bat = expected(spec, CASE / 'private/solver.exe'); tree = ET.fromstring(text)
        assert Decimal(spec[2]) * spec[4] == Decimal('0.00004')
        assert tree.find('.//HydraulicConductivity').get('value') == '0' and tree.find('.//HydroMechInitMode').get('value') == '1'
        assert tree.find('.//PoreShepardInterval').get('value') == str(spec[4])
        assert 'if exist "%dirout%" goto fail' in bat
    return dict(passed=True, programs_started=False, files_written=False)


def prepare():
    selftest(); assert not list(LOGS.glob(TAG+'*')) and not list(OUTPUTS.glob(TAG+'*'))
    checkpath = C02 / 'logs/symc_1d_short_r1.check.json'; check = read(checkpath); assert check['passed'] and len(check['jobs']) == 6
    previous = read(check['run']['path']); prior = read(previous['prepared']['path'])
    proof = [bound(p) for p in [__file__, NOTE, TEMPLATE, TESTS/'notes/selfweight_readiness_r1.md', checkpath, READER, READER_SOURCE,
        C02/'support/symc_1d_short_r1.py', C02.parent/'support/release_case.py', C02.parent/'support/compare_precision_q0.py', C04/'support/cryer_start_r1.py', REPO/'bin/windows/GenCase_win64.exe']]
    proof += [check['run'], previous['prepared']]; jobs = []
    for folder in [LOGS, CONFIGS, OUTPUTS, FIGURES]: folder.mkdir(exist_ok=True)
    for spec in JOBS:
        suffix, backend, dt, steps, shepard = spec; name = TAG+'_'+suffix
        old = next(j for j in prior['jobs'] if j['backend'] == backend and j['variant'] == 'off')
        build = read(old['build']['path']); assert build['exit_code'] == 0 and build['owned_exited'] and build['protected_inputs_unchanged']
        proof += [old['build'], old['program']] + old['runtime'] + [build['log']] + build['artifacts']
        cfg, bat = CONFIGS/(name+'_Def.xml'), CONFIGS/('x'+name+'_win64_'+backend.upper()+'.bat')
        assert not cfg.exists() and not bat.exists(); text, command = expected(spec, Path(old['program']['path']))
        with cfg.open('x', encoding='utf8', newline='') as stream: stream.write(text)
        with bat.open('x', encoding='ascii', newline='\r\n') as stream: stream.write(command)
        jobs.append(dict(name=name, suffix=suffix, backend=backend, dt=float(dt), steps=steps, shepard=shepard,
            program=old['program'], runtime=old['runtime'], build=old['build'], config=bound(cfg), bat=bound(bat)))
        proof += [bound(cfg), bound(bat)]
    proof = unique(proof); verify(proof)
    seal(PREP, dict(utc=utc(), inputs=proof, jobs=jobs, storage_precision_change='SavePosDouble0->1 output only',
        pressure_reference_array_observed=False, physical_acceptance=False, automatic_long_run_admitted=False))


def model():
    tree = ET.parse(TEMPLATE); value = lambda p: float(tree.find(p).get('value'))
    E, nu = value('.//soils/ModulusE'), value('.//soils/PRvs'); M = E*(1-nu)/((1+nu)*(1-2*nu))
    storage = value('.//PoreWaterBulkModulus')/value('.//Porosity')
    return dict(H=float(tree.find('.//newvarcte[@sizefz]').get('sizefz')), rho=float(tree.find('.//constantsdef/rhop0').get('value')),
        rho_w=value('.//PoreWaterRho'), g=abs(float(tree.find('.//constantsdef/gravity').get('z'))), B=storage/(M+storage))


def measure(a, initial, part, job, m):
    assert len(a.columns) == 35 and len(a) == 1000 and np.array_equal(a.id, np.arange(40, 1040))
    assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.nout.eq(0).all()
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.native_count.eq(1040).all()
    assert np.array_equal(a[['mass','dp','h']], initial[['mass','dp','h']])
    t=float(a.time_s.iloc[0]); step=int(a.saved_step.iloc[0])+1 if part else 0
    assert a.time_s.eq(t).all() and a.saved_step.eq(int(a.saved_step.iloc[0])).all()
    assert abs(t-step*job['dt']) < 1e-12 and abs(t-part*INTERVAL) <= 1.01e-6
    if part: assert a.has_dterror.eq(1).all() and float(a.dterror_s.max()) <= 1e-14
    x=a[['x','y','z']].to_numpy(); x0=initial[['x','y','z']].to_numpy(); displacement=x-x0
    dx=(displacement[:,0]+.05)%.1-.05; span=float(np.ptp(a.z.to_numpy().reshape(10,100),axis=0).max()*1000)
    assert (a.z>0).all() and abs(dx).max()*1000 < .5 and span < .5
    surface=a.fstype.isin([2,3])
    assert set(a.id[surface]) == set(initial.id.iloc[99::100]) and a.pressure[surface].eq(0).all()
    depth=m['H']-initial.z.to_numpy(); hydro=m['rho_w']*m['g']*depth
    target_p=hydro+m['B']*(m['rho']-m['rho_w'])*m['g']*depth; target_total=-m['rho']*m['g']*depth
    total=a.sigma_zz.to_numpy()-a.pressure.to_numpy()
    row=dict(part=part,time_s=t,saved_step=int(a.saved_step.iloc[0]),native_soil_count=len(a),true_drained_count=int(surface.sum()),
        true_drained_pressure_absmax_pa=float(abs(a.pressure[surface]).max()),dterror_s=float(a.dterror_s.max()),rho_min=float(a.rho.min()),rho_max=float(a.rho.max()),
        pressure_min_pa=float(a.pressure.min()),pressure_max_pa=float(a.pressure.max()),speed_max_m_s=float(np.linalg.norm(a[['vx','vy','vz']],axis=1).max()),
        material_displacement_max_mm=float(np.linalg.norm(displacement,axis=1).max()*1000),periodic_dx_max_mm=float(abs(dx).max()*1000),layer_span_max_mm=span,
        nominal_undrained_pressure_rms_residual_pa=float(np.sqrt(np.mean((a.pressure-target_p)**2))),nominal_total_stress_rms_residual_pa=float(np.sqrt(np.mean((total-target_total)**2))),
        pressure_reference_p0_observed=False,pore_dt_limit_applicable=False)
    layers=[]
    for z in range(100):
        ids=np.arange(z,1000,100)
        layers.append(dict(part=part,time_s=t,initial_layer=z,z0_m=float(initial.z.iloc[ids].mean()),pressure_pa=float(a.pressure.iloc[ids].mean()),
            effective_sigma_zz_pa=float(a.sigma_zz.iloc[ids].mean()),total_sigma_zz_pa=float(total[ids].mean()),
            nominal_hydrostatic_pa=float(hydro[ids].mean()),nominal_undrained_pressure_pa=float(target_p[ids].mean()),nominal_total_sigma_zz_pa=float(target_total[ids].mean())))
    return row,layers


def one_job(job, prepared):
    folder=OUTPUTS/job['name']; log=LOGS/(job['name']+'.log'); complete=LOGS/(job['name']+'.completion.json')
    receipt=LOGS/(job['name']+'.receipt.json'); assert not inventory() and not any(p.exists() for p in [folder,log,complete,receipt])
    verify(prepared['inputs']); child=None; initial=None; rows=[]; profiles=[]; error=None; started=time.perf_counter(); m=model()
    try:
        with log.open('xb') as stream:
            child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',job['bat']['path']],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            while True:
                code=child.poll(); count=len(list((folder/'data').glob('Part_*.bi4'))); available=count if code is not None else max(0,count-1)
                while len(rows)<available:
                    p=len(rows); a=native(folder,p)
                    if initial is None: initial=a.copy()
                    row,profile=measure(a,initial,p,job,m); rows.append(row); profiles+=profile
                if code is not None: break
                time.sleep(2)
    except BaseException as failure:
        error=repr(failure); failure_traceback=traceback.format_exc()
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW); child.wait(timeout=30)
    text=(folder/'Run.out').read_text(errors='replace') if (folder/'Run.out').exists() else ''
    survivors=[p for p in inventory() if job['name'] in (p.get('CommandLine') or '')]
    done=dict(solver_finished=child is not None and child.returncode==0 and 'Finished execution (code=0)' in text,
        exit_code=None if child is None else child.returncode,owned_exited=not survivors,surviving_owned=survivors,
        program=job['program'],config=job['config'],bat=job['bat'],outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]+([bound(log)] if log.exists() else []))
    seal(complete,done)
    try:
        assert error is None,error
        assert done['solver_finished'] and done['owned_exited'] and len(rows)==5
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==job['steps']
        assert 'SlipMode="DBC vel=0"' in text and 'HydroMechInitMode="FreeSurface"' in text and 'PoreDarcySymmetricCorr="Receiver"' in text
        assert int(re.search(r'PoreShepardInterval:\s*(\d+)',text)[1])==job['shepard']
        assert 'SoilHourglass: forcecalls=' not in text and 'SoilDampingCoef=0.02' in text
        verify(prepared['inputs'])
    except BaseException as failure: error=repr(failure); failure_traceback=traceback.format_exc()
    artifacts=[]
    for kind,data in [('summary',rows),('profiles',profiles)]:
        if data:
            path=FIGURES/(job['name']+'_'+kind+'.csv')
            with path.open('x',encoding='utf8',newline='') as stream: pd.DataFrame(data).to_csv(stream,index=False,float_format='%.17g')
            artifacts.append(bound(path))
    result=dict(passed=error is None,error=error,rows=rows,artifacts=artifacts,sealed_completion=bound(complete),
        owned_wrapper_pid=None if child is None else child.pid,wall_seconds=time.perf_counter()-started,
        loop_seconds=float(re.search(r'Simulation Runtime\.*:\s*([\d.]+)',text)[1]) if done['solver_finished'] else None,
        pressure_reference_p0_observed=False,physical_acceptance=False)
    if error: result['traceback']=failure_traceback
    seal(receipt,result); return result,bound(receipt)


def run():
    assert not RUN.exists() and not CHECK.exists() and not inventory(); prepared=read(PREP); verify(prepared['inputs'])
    state=dict(status='running',utc=utc(),worker_pid=os.getpid(),prepared=bound(PREP),jobs=[]); results={}
    def publish():
        tmp=RUN.with_suffix('.tmp'); tmp.write_text(json.dumps(state,indent=2,allow_nan=False),encoding='utf8'); os.replace(tmp,RUN)
    publish(); pairs=[]
    try:
        for job in prepared['jobs']:
            state['current_job']=job['name']; publish(); result,record=one_job(job,prepared); state['jobs'].append(record); publish()
            assert result['passed'],result['error']; results[job['suffix']]=result
        for label,left,right,tolerance in [('CPU_GPU','gpu_c','cpu_c',1e-12),('GPU_half','gpu_h','gpu_c',1.01e-6)]:
            af,bf=OUTPUTS/(TAG+'_'+left),OUTPUTS/(TAG+'_'+right); a0,b0=native(af,0),native(bf,0)
            for p in range(5):
                a,b=native(af,p),native(bf,p); delta_t=float(a.time_s.iloc[0]-b.time_s.iloc[0]); assert abs(delta_t)<=tolerance
                assert np.array_equal(a.id,b.id)
                du=(a[['x','y','z']].to_numpy()-a0[['x','y','z']].to_numpy())-(b[['x','y','z']].to_numpy()-b0[['x','y','z']].to_numpy())
                pressure=float(np.sqrt(np.mean((a.pressure-b.pressure)**2))); displacement=float(np.linalg.norm(du,axis=1).max()*1000)
                pairs.append(dict(comparison=label,part=p,time_s=float(a.time_s.iloc[0]),reference_time_s=float(b.time_s.iloc[0]),actual_time_difference_s=delta_t,
                    saved_step=int(a.saved_step.iloc[0]),reference_saved_step=int(b.saved_step.iloc[0]),pressure_rms_pa=pressure,material_displacement_max_difference_mm=displacement))
                assert pressure<=5 and displacement<=.005
        path=FIGURES/(TAG+'_pairs.csv')
        with path.open('x',encoding='utf8',newline='') as stream: pd.DataFrame(pairs).to_csv(stream,index=False,float_format='%.17g')
        state.update(status='short_safety_and_near_time_screens_passed_pending_review',pairs=bound(path))
    except BaseException as failure: state.update(status='rejected_or_interrupted',error=repr(failure),traceback=traceback.format_exc())
    state['finished_utc']=utc(); publish()
    seal(CHECK,dict(passed=state['status']=='short_safety_and_near_time_screens_passed_pending_review',run=bound(RUN),jobs=state['jobs'],error=state.get('error'),
        half_is_near_time_diagnostic=True,exact_matched_time_convergence_claimed=False,pressure_reference_p0_observed=False,physical_acceptance=False,automatic_long_run_admitted=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); group=parser.add_mutually_exclusive_group()
    for flag in ['selftest','prepare','run']: group.add_argument('--'+flag,action='store_true')
    args=parser.parse_args()
    if args.selftest: print(json.dumps(selftest()))
    elif args.prepare: prepare()
    elif args.run: run()
    else: parser.print_help()
