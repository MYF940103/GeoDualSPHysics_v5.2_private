"""Six fresh actual-program 1D regressions; default help, no automatic long-run admission."""
import argparse
import ast
import hashlib
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
CRYER = CASE.parent / '04_CryerProblem_PR/tests'
sys.path.insert(0, str(CASE / 'support'))
import release_case
sys.path.insert(0, str(CRYER / 'support'))
from cryer_start_r1 import native, bound, utc

TAG = 'symc_1d_short_r1'
LOGS, CONFIGS, OUTPUTS, FIGURES = [TESTS / d for d in ['logs', 'configs', 'outputs', 'figures']]
PREP, RUN, CHECK = [LOGS / (TAG + s) for s in ['.inputs.json', '.run.json', '.check.json']]
NOTE = TESTS / 'notes' / (TAG + '.json')
TEMPLATE = CASE / 'CaseTerzaghiConsolidation_q0_PR_full_k1em4_Def.xml'
READER = CASE.parent / '05_LianFlexibleStrip2D_PR/tests/outputs/hydro_native_r1/ReadHydroNative.exe'
READER_SOURCE = CASE.parent / '05_LianFlexibleStrip2D_PR/tests/scripts/read_hydro_native.cpp'
GENCASE = REPO / 'bin/windows/GenCase_win64.exe'
DT, END, INTERVAL, STEPS, FRAMES = 1e-5, .15, .001, 15000, 151
SIGMA = ['sigma_xx', 'sigma_yy', 'sigma_zz', 'sigma_xy', 'sigma_yz', 'sigma_xz']
JOBS = [(b, v) for b in ['cpu', 'gpu'] for v in ['old', 'off', 'on']]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def seal(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def verify(records):
    for r in records:
        a = bound(r['path'])
        assert (a['sha256'].lower(), a['bytes']) == (r['sha256'].lower(), r['bytes']), r['path']


def unique(records):
    result = {}
    for r in records:
        key = str(Path(r['path']).resolve()).casefold()
        assert key not in result or result[key] == r, ('Conflicting binding', r['path'])
        result[key] = r
    return list(result.values())


def expected(backend, variant, program):
    name = TAG + '_' + backend + '_' + variant
    xml = TEMPLATE.read_text(encoding='utf8')
    assert 'PoreDarcySymmetricCorr' not in xml and '<timeout>' not in xml
    for key, value in [('TimeMax', '0.15'), ('TimeOut', '0.001')]:
        xml, n = re.subn(r'(<parameter key="' + key + r'" value=")[^"]+(" comment=")[^"]+("[^\n]+)',
            lambda m: m[1] + value + m[2] + 'Fresh symC implementation short window; not full acceptance' + m[3], xml)
        assert n == 1, key
    if variant == 'on':
        xml, n = re.subn(r'(?m)^([ ]*)(<HydroMechDrainageFixedGrid[^\n]*\n)',
            lambda m: m[0] + m[1] + '<PoreDarcySymmetricCorr value="1" comment="Symmetric soil-soil Darcy only; optional ON comparison" />\n', xml)
        assert n == 1
    relative = os.path.relpath(program, CASE).replace('\\', '/')
    bat = ('@echo off\nsetlocal\ncd /d "%~dp0\\..\\.."\n\n'
        f'set name={name}\nset dirout=tests/outputs/%name%\nset dirbin=../../../bin/windows\n'
        'set gencase="%dirbin%/GenCase_win64.exe"\n' + f'set dualsphysics="{relative}"\n\n'
        'if exist "%dirout%" goto fail\n'
        '%gencase% "tests/configs/%name%_Def" "%dirout%/%name%" -save:all\n'
        'if not "%ERRORLEVEL%" == "0" goto fail\n\n'
        f'%dualsphysics% -{backend} -ompthreads:1 -stable -mdbc "%dirout%/%name%" "%dirout%" -dirdataout data -svres -svextraparts:1 -nsteps:15000\n'
        'if not "%ERRORLEVEL%" == "0" goto fail\nexit /b 0\n\n:fail\necho Fresh test failed; existing/partial data preserved.\nexit /b 1\n')
    return xml, bat


def exact(a, b):
    assert list(a) == list(b) and len(a.columns) == 35
    bad = a.to_numpy(dtype='<f8').view('<u8') != b.to_numpy(dtype='<f8').view('<u8')
    return dict(all35_columns0ulp=not bool(bad.any()), compared_columns=list(a),
                different_fields=[a.columns[i] for i in np.flatnonzero(bad.any(axis=0))])


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    a = pd.DataFrame(np.zeros((1, 35)), columns=['f' + str(i) for i in range(35)])
    assert exact(a, a.copy())['all35_columns0ulp']
    for c in a.columns:
        b = a.copy(); b.loc[0, c] = -0.
        assert not exact(a, b)['all35_columns0ulp']
    for backend, variant in JOBS:
        xml, bat = expected(backend, variant, CASE / 'private/solver.exe')
        assert ('PoreDarcySymmetricCorr' in xml) == (variant == 'on')
        assert 'if exist "%dirout%" goto fail' in bat and '-nsteps:15000' in bat
    return dict(passed=True, source_only=True, programs_started=False)


def prepare():
    selftest()
    assert not list(LOGS.glob(TAG + '*')) and not list(OUTPUTS.glob(TAG + '*'))
    reviewpath = CRYER / 'logs/cryer_darcy_switch_native_review_r1.check.json'
    assert read(reviewpath)['implementation_regression_passed'] is True
    basepath = CRYER / 'logs/cryer_darcy_switch_r1.base.json'; base = read(basepath)
    sourcespath = CRYER / 'logs/cryer_darcy_native_sources_r1.json'; sources = read(sourcespath)
    proof = [bound(p) for p in [__file__, NOTE, TEMPLATE, reviewpath, basepath, sourcespath, READER, READER_SOURCE,
        GENCASE, CASE / 'support/release_case.py', CASE / 'support/compare_precision_q0.py', CRYER / 'support/cryer_start_r1.py']]
    proof += [r['snapshot'] for r in base['files']] + base['canonical_programs']
    proof += [dict(path=str(Path(sources['snapshot_directory']) / r['name']), bytes=r['bytes'], sha256=r['sha256']) for r in sources['files']]
    jobs = []
    for backend, variant in JOBS:
        name = TAG + '_' + backend + '_' + variant
        if variant == 'old':
            exe = 'DualSPHysics5.2CPU_win64.exe' if backend == 'cpu' else 'DualSPHysics5.2_GEO_win64.exe'
            program = next(x['snapshot'] for x in base['files'] if Path(x['snapshot']['path']).name == exe)
            runtime = [x['snapshot'] for x in base['files'] if Path(x['snapshot']['path']).name in ['ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll', 'DsphConfig.xml']]
            build = bound(basepath)
        else:
            filename = 'cryer_darcy_switch_build_r1_ReleaseCPU.build.json' if backend == 'cpu' else 'cryer_darcy_switch_build_r2_Release.build.json'
            path = CRYER / 'logs' / filename; record = read(path)
            assert record['status'] == 'built_not_run' and record['exit_code'] == 0 and record['owned_exited'] and record['protected_inputs_unchanged']
            program, runtime, build = record['program'], [p['target'] for p in record['runtime']], bound(path)
            proof += [record['log']] + record['artifacts'] + [p['source'] for p in record['runtime']]
        assert len(runtime) == 4
        cfg, bat = CONFIGS / (name + '_Def.xml'), CONFIGS / ('x' + name + '_win64_' + backend.upper() + '.bat')
        assert not cfg.exists() and not bat.exists()
        xml, text = expected(backend, variant, Path(program['path']))
        with cfg.open('x', encoding='utf8', newline='') as f: f.write(xml)
        with bat.open('x', encoding='ascii', newline='\r\n') as f: f.write(text)
        job = dict(name=name, backend=backend, variant=variant, program=program, runtime=runtime,
                   build=build, config=bound(cfg), bat=bound(bat))
        jobs.append(job); proof += [program, build, job['config'], job['bat']] + runtime
    proof = unique(proof); verify(proof)
    seal(PREP, dict(utc=utc(), inputs=proof, jobs=jobs, dt_s=DT, duration_s=END, frames=FRAMES,
        compiled_source_archive=sourcespath.as_posix(), historical_original_sources_reverified=False,
        implementation_passed=False, physical_acceptance=False, automatic_long_run_admitted=False))


def inventory():
    command = "@(Get-CimInstance Win32_Process | Where-Object {$_.Name -like 'DualSPHysics*.exe'} | Select-Object ProcessId,ParentProcessId,CommandLine) | ConvertTo-Json -Compress"
    text = subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
    if not text: return []
    data = json.loads(text); return data if isinstance(data, list) else [data]


def measure(a, initial, part, model):
    assert len(a) == 1000 and np.array_equal(a.id, np.arange(40, 1040)) and len(a.columns) == 35
    assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.nout.eq(0).all() and a.kplastic.eq(0).all() and a.rho.gt(0).all()
    assert a.position_double.eq(1).all() and a.stress_double.eq(1).all() and a.load_available.eq(1).all()
    assert np.array_equal(a[['mass', 'dp', 'h']], initial[['mass', 'dp', 'h']]) and a.native_count.eq(1040).all()
    t = float(a.time_s.iloc[0]); step = int(a.saved_step.iloc[0]) + 1 if part else 0
    assert a.time_s.eq(t).all() and a.saved_step.eq(int(a.saved_step.iloc[0])).all()
    assert abs(t - step * DT) < 1e-12 and abs(t - part * INTERVAL) <= 1.01 * DT
    if part: assert a.has_dterror.eq(1).all() and float(a.dterror_s.max()) <= 1e-14
    if t > model['tD'] + 1e-7:
        surface = a.fstype.isin([2, 3])
        assert set(a.id[surface]) == set(initial.id.iloc[99::100]) and a.pressure[surface].eq(0).all()
    # Existing formal inspector is reused unchanged; its synthetic display flag is only consumed after .1 s.
    display = a.assign(drained=((a.fstype.isin([2, 3])) & (t > model['tD'])).astype(int))
    row = release_case.inspect(display, initial, model)
    assert row['load_available'], 'Cannot claim original resultant guard without native telemetry'
    if t >= .1 - 1e-7: assert 'load_resultant_N_m' in row
    dtw = float(np.float32(1.)) * float(np.float32(model['rho_w'])) * 9.80665 * float(np.float32(model['n'])) / float(np.float32(model['Kw'])) * float(a.h.iloc[0])**2 / float(np.float32(model['k']))
    assert DT <= dtw
    row.update(part=part, saved_step=int(a.saved_step.iloc[0]), dterror_s=float(a.dterror_s.max()), pore_dt_s=dtw)
    return row


def pair(a, b, ar, br):
    assert np.array_equal(a.id, b.id) and abs(float(a.time_s.iloc[0] - b.time_s.iloc[0])) < 1e-7
    delta = a.pressure.to_numpy() - b.pressure.to_numpy()
    return dict(time_s=ar['time_s'], reference_time_s=br['time_s'], pressure_rms_pa=float(np.sqrt(np.mean(delta**2))),
        pressure_absmax_pa=float(abs(delta).max()), top_settlement_difference_mm=ar['top_settlement_mm']-br['top_settlement_mm'],
        bottom_settlement_difference_mm=ar['bottom_settlement_mm']-br['bottom_settlement_mm'],
        stress_absmax_pa=float(abs(a[SIGMA].to_numpy()-b[SIGMA].to_numpy()).max()))


def hg_check(text):
    counts = re.search(r'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)', text)
    cache = re.search(r'SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)', text)
    shape = re.search(r'max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)', text)
    assert counts and cache and shape
    assert list(map(int, counts.groups())) == [2*STEPS, STEPS, STEPS, 2*STEPS]
    assert list(map(int, cache.groups())) == [STEPS+1, STEPS-1]
    assert 0 <= float(shape[1]) <= .2 and 0 <= float(shape[2]) < .01
    return dict(force_calls=2*STEPS, rate_calls=2*STEPS, calculations=STEPS+1, cache_hits=STEPS-1,
                dt_over_tau=float(shape[1]), spin_bound=float(shape[2]))


def one_job(job, prepared):
    name, folder = job['name'], OUTPUTS / job['name']
    log, complete, receipt = [LOGS / (name + s) for s in ['.log', '.completion.json', '.receipt.json']]
    assert not inventory() and not any(p.exists() for p in [folder, log, complete, receipt])
    verify(prepared['inputs']); result = dict(name=name, passed=False, rows=[], prefix=[], option=[])
    child, initial, reference_initial, error = None, None, None, None; started = time.perf_counter()
    model = None
    try:
        with log.open('xb') as stream:
            child = subprocess.Popen([os.environ['ComSpec'], '/d', '/c', job['bat']['path']], cwd=CASE, stdout=stream,
                stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            result['owned_wrapper_pid'] = child.pid
            while True:
                code = child.poll(); count = len(list((folder / 'data').glob('Part_*.bi4')))
                available = count if code is not None else max(0, count-1)
                while len(result['rows']) < available:
                    p = len(result['rows']); a = native(folder, p)
                    if initial is None:
                        initial = a.copy(); model = release_case.model(folder / (name + '.xml'))
                    row = measure(a, initial, p, model); result['rows'].append(row)
                    if job['variant'] != 'old':
                        reference = OUTPUTS / (TAG + '_' + job['backend'] + ('_old' if job['variant'] == 'off' else '_off'))
                        b = native(reference, p)
                        if reference_initial is None: reference_initial = b.copy()
                        if job['variant'] == 'off':
                            exactness = dict(part=p, **exact(a, b)); result['prefix'].append(exactness)
                            assert exactness['all35_columns0ulp'], exactness
                        else: result['option'].append(dict(part=p, **pair(a, b, row, measure(b, reference_initial, p, model))))
                if code is not None: break
                print(name, 'checked', len(result['rows']), 'wall_s', round(time.perf_counter()-started), flush=True)
                time.sleep(3)
    except BaseException as failure:
        error = repr(failure); result['traceback'] = traceback.format_exc()
        if child is not None and child.poll() is None:
            subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            child.wait(timeout=30)
    text = (folder / 'Run.out').read_text(errors='replace') if (folder / 'Run.out').exists() else ''
    survivors = [x for x in inventory() if name in (x.get('CommandLine') or '')]
    done = dict(solver_finished=child is not None and child.returncode == 0 and 'Finished execution (code=0)' in text,
        exit_code=None if child is None else child.returncode, owned_exited=not survivors, surviving_owned=survivors,
        program=job['program'], config=job['config'], bat=job['bat'], outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()] + ([bound(log)] if log.exists() else []))
    seal(complete, done)  # Seal a completed or intentionally stopped solve before final checking/reporting.
    try:
        assert error is None, error
        assert done['solver_finished'] and done['owned_exited'] and len(result['rows']) == FRAMES
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)', text)[1]) == STEPS
        if job['variant'] != 'old': assert 'PoreDarcySymmetricCorr="' + ('SymmetricSoilPair' if job['variant']=='on' else 'Receiver') + '"' in text
        result['hourglass'] = hg_check(text)
        result['loop_seconds'] = float(re.search(r'Simulation Runtime\.*:\s*([\d.]+)', text)[1])
        verify(prepared['inputs']); result['passed'] = True
    except BaseException as failure:
        error = repr(failure); result['traceback'] = traceback.format_exc()
    result.update(error=error, sealed_completion=bound(complete), wall_seconds=time.perf_counter()-started)
    if result['rows']:
        csv = FIGURES / (name + '_history.csv')
        with csv.open('x', encoding='utf8', newline='') as stream: pd.DataFrame(result['rows']).to_csv(stream, index=False, float_format='%.17g')
        result['history'] = bound(csv)
    seal(receipt, result); return result, bound(receipt)


def run():
    assert not RUN.exists() and not CHECK.exists() and not inventory()
    prepared = read(PREP); verify(prepared['inputs'])
    state = dict(status='running', utc=utc(), worker_pid=os.getpid(), prepared=bound(PREP), jobs=[])
    def publish():
        temp = RUN.with_suffix('.tmp'); temp.write_text(json.dumps(state, indent=2, allow_nan=False), encoding='utf8'); os.replace(temp, RUN)
    publish(); comparison = []
    try:
        results = {}
        for job in prepared['jobs']:
            state['current_job'] = job['name']; publish()
            result, receipt = one_job(job, prepared); state['jobs'].append(receipt); publish()
            assert result['passed'], result['error']; results[job['name']] = result
            comparison += [dict(comparison=job['name']+'_minus_OFF', **r) for r in result['option']]
        cpu, gpu = [OUTPUTS / (TAG + '_' + b + '_on') for b in ['cpu', 'gpu']]
        for p in range(FRAMES):
            a, b = native(gpu, p), native(cpu, p)
            ar, br = [results[TAG+'_'+backend+'_on']['rows'][p] for backend in ['gpu', 'cpu']]
            q = dict(part=p, comparison='GPU_ON_minus_CPU_ON', **pair(a, b, ar, br)); comparison.append(q)
            assert q['pressure_rms_pa'] <= 5. and abs(q['top_settlement_difference_mm']) <= .005
        csv = FIGURES / (TAG + '_comparisons.csv')
        with csv.open('x', encoding='utf8', newline='') as stream: pd.DataFrame(comparison).to_csv(stream, index=False, float_format='%.17g')
        state.update(status='short_implementation_and_cross_gates_passed_pending_review', comparisons=bound(csv))
    except BaseException as failure: state.update(status='rejected_or_interrupted', error=repr(failure), traceback=traceback.format_exc())
    state['finished_utc'] = utc(); publish()
    seal(CHECK, dict(passed=state['status']=='short_implementation_and_cross_gates_passed_pending_review', status=state['status'],
        run=bound(RUN), jobs=state['jobs'], error=state.get('error'), physical_acceptance=False, half_step_test=False, automatic_long_run_admitted=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); group = parser.add_mutually_exclusive_group()
    for flag in ['selftest', 'prepare', 'run']: group.add_argument('--'+flag, action='store_true')
    args = parser.parse_args()
    if args.selftest: print(json.dumps(selftest()))
    elif args.prepare: prepare()
    elif args.run: run()
    else: parser.print_help()
