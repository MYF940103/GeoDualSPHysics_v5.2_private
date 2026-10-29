"""Author-only GPU sym-C short sequence; explicit preparation/run, never peak admission."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE, TESTS, REPO, READER, READER_SOURCE, native, bound, utc, write_json
from cryer_grad_short_r1 import difference
from cryer_grad_peak_r1 import identity, CODEX
from cryer_preload_probe_r1 import equilibrium
import cryer_preload_peak_r1 as coarse_rules
import cryer_preload_peak_half_r1 as half_rules

TAG = 'cryer_symc_gpu_short_r1'
LOG = TESTS / 'logs'
PREP, RUN, STATUS, CHECK = [LOG / (TAG + s) for s in ['.inputs.json', '.run.json', '.status.json', '.check.json']]
SUMMARY, PAIRS = [TESTS / 'figures' / (TAG + s) for s in ['_summary.csv', '_comparisons.csv']]
BUILD_TAG = 'cryer_symc_gpu_build_r3'
PLAN = LOG / (BUILD_TAG + '.inputs.json')
END, INTERVAL = .00830078125, 2. ** -13
JOBS = [('dbg', 'Debug', 2. ** -21, INTERVAL, 2), ('c', 'Release', 2. ** -21, END, 69),
        ('h', 'Release', 2. ** -22, END, 69)]
SANITIZER = Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe')
MEMCHECK_FIXTURE = TESTS / 'outputs/cryer_gpu_base_r1_dbg/memcheck.log'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def seal(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def verify(entries):
    seen = {}
    for e in entries:
        key = str(Path(e['path']).resolve()).casefold()
        if key in seen:
            assert seen[key] == e['sha256'].lower(), 'Conflicting frozen hashes: ' + key
            continue
        a = bound(e['path'])
        assert a['sha256'].lower() == e['sha256'].lower(), e['path']
        assert 'bytes' not in e or a['bytes'] == e['bytes'], e['path']
        seen[key] = a['sha256']


def inventory():
    cmd = "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'DualSPHysics*' -or $_.Name -like 'cryer_symc_gpu_r*.exe' -or $_.Name -eq 'cryer_symc_release_r1.exe' } | Select-Object ProcessId,ParentProcessId,Name,CommandLine) | ConvertTo-Json -Compress"
    text = subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True).strip()
    value = json.loads(text) if text else []
    return [value] if isinstance(value, dict) else value


def memcheck_clean(text):
    errors = re.findall(r'ERROR SUMMARY: ([^\r\n]*)', text)
    leaks = re.findall(r'LEAK SUMMARY: ([^\r\n]*)', text)
    return bool(errors and leaks) and all(s.strip() == '0 errors' for s in errors) and all(
        s.strip() == '0 bytes leaked in 0 allocations' for s in leaks)


def selftest():
    xml = (TESTS / 'configs/cryer_preload_probe_r1_Def.xml').read_text(encoding='utf8')
    bat = (TESTS / 'configs/xcryer_preload_probe_r1_win64_GPU.bat').read_text(encoding='utf8')
    for suffix, config, dt, end, frames in JOBS:
        name = TAG + '_' + suffix
        comment = 'GPU symmetric-C ' + ('Debug memory' if suffix == 'dbg' else 'Release short') + ' diagnostic; not a full validation'
        expected = xml.replace('GPU preload probe through 17*2^-11 seconds; not a full validation', comment)
        if suffix == 'dbg':
            expected = expected.replace('key="TimeMax" value="0.00830078125"', 'key="TimeMax" value="0.0001220703125"')
            expected = expected.replace('native save interval; 69 frames including t=0', 'native save interval; 2 frames including t=0')
        if suffix == 'h':
            expected = expected.replace('0.000000476837158203125', '0.0000002384185791015625')
        assert (TESTS / 'configs' / (name + '_Def.xml')).read_text(encoding='utf8').rstrip() == expected.rstrip()
        expected_bat = bat.replace('cryer_preload_probe_r1', name).replace(
            '"%dirbin%/DualSPHysics5.2_GEO_win64.exe"',
            f'"tests/outputs/{BUILD_TAG}/{config}/cryer_symc_gpu_r3_{config}.exe"')
        if suffix == 'dbg':
            expected_bat = expected_bat.replace('%dualsphysicsgpu% -gpu', '"' + str(SANITIZER) +
                '" --tool memcheck --error-exitcode 86 --leak-check full --log-file "%dirout%\\memcheck.log" %dualsphysicsgpu% -gpu')
        assert (TESTS / 'configs' / ('x' + name + '_win64_GPU.bat')).read_text(encoding='utf8').rstrip() == expected_bat.rstrip()
        assert int(end / dt) == (256 if suffix == 'dbg' else 34816 if suffix == 'h' else 17408)
        assert end / INTERVAL + 1 == frames
    assert len(notification('terminal_status')) < 2000
    fixture = MEMCHECK_FIXTURE.read_text(errors='replace')
    assert memcheck_clean(fixture)
    assert not memcheck_clean(fixture.replace('0 errors', '1 errors'))
    assert not memcheck_clean(fixture.replace('0 bytes leaked in 0 allocations', '4 bytes leaked in 1 allocations'))
    assert not memcheck_clean(fixture.replace('0 allocations', '1 allocations'))
    assert not memcheck_clean(fixture + '\nERROR SUMMARY: 1 errors\n')
    assert not memcheck_clean('ERROR SUMMARY: 0 errors\n')
    return dict(passed=True, physical_solver_started=False, jobs=3, expected_native_frames=140, comparison_rows=345)


def prepare():
    selftest()
    reserved = [PREP, RUN, STATUS, CHECK, SUMMARY, PAIRS] + [LOG / (TAG + s) for s in ['.queue_attempt.json', '.notification.json']]
    for suffix, _, _, _, _ in JOBS:
        name = TAG + '_' + suffix
        reserved += [TESTS / 'outputs' / name, LOG / (name + '.log'), LOG / (name + '.completion.json')]
    assert not any(p.exists() for p in reserved), 'Retained evidence exists; no overwrite/restart'
    cpu_check, cpu_review, visual = [LOG / n for n in ['cryer_symc_short_r1.check.json',
        'cryer_symc_short_review_r1.check.json', 'cryer_symc_short_review_r1.visual.json']]
    old = read(cpu_check)
    assert old['passed'] and all(r['passed'] and r['owned_exited'] and r['exit_code'] == 0 for r in old['runs'])
    assert read(cpu_review)['analysis_checks_passed']
    v = read(visual)
    assert v['analysis_checks_passed'] and v['visual_review_passed']
    proof = [bound(p) for p in [cpu_check, cpu_review, visual, PLAN]]
    proof += read(cpu_review)['sources'] + read(cpu_review)['artifacts'] + [v['review_check']]
    cpu_run = read(old['run']['path'])
    proof += [old['run'], cpu_run['prepared_inputs']]
    proof += read(cpu_run['prepared_inputs']['path'])['inputs']
    step = LOG / 'cryer_symc_step_screen_r1.check.json'
    screen = read(step)
    assert screen['analysis_checks_passed'] and screen['coarse_dt_admitted'] and screen['half_dt_admitted']
    proof += [bound(step)] + screen['inputs']
    plan = read(PLAN)
    assert plan['status'] == 'prepared_not_built' and plan['no_solver_launched']
    builds = {}
    for config in ['Debug', 'Release']:
        path = LOG / (BUILD_TAG + '_' + config + '.build.json')
        b = read(path)
        assert b['status'] == 'built_not_run' and b['configuration'] == config
        assert b['protected_inputs_unchanged'] and b['canonical_main_object_retained']
        assert b['compiled_dependencies_all_bound_before_compile'] and all(s['exit_code'] == 0 for s in b['stages'])
        delta = b['source_comparison']
        assert delta['exact_normalized_source_is_declared_delta'] and delta['darcy_block_replacements'] == 1
        assert delta['signature_additions'] == 1 and delta['existing_call_additions'] == 4
        assert delta['cpu_candidate_Darcy_algebra_exact_ignoring_indentation_and_CTE_prefix']
        assert b['plan'] == bound(PLAN)
        expected = TESTS / 'outputs' / BUILD_TAG / config / ('cryer_symc_gpu_r3_' + config + '.exe')
        assert Path(b['program']['path']).resolve() == expected.resolve()
        proof += [bound(path), b['program']] + b['protected_inputs'] + b['compiled_dependencies'] + b['artifacts']
        proof += [x[k] for x in b['runtime'] for k in ['source', 'target']]
        builds[config] = dict(receipt=bound(path), program=b['program'])
    controls = {}
    for suffix in ['c', 'h']:
        cpu = 'cryer_symc_short_r1_on_' + suffix
        gpu = 'cryer_preload_peak_' + ('half_r1' if suffix == 'h' else 'r1')
        controls[suffix] = dict(cpu=str(TESTS / 'outputs' / cpu), raw_gpu=str(TESTS / 'outputs' / gpu))
        for tag in [cpu, gpu]:
            path = LOG / (tag + '.completion.json')
            done = read(path)
            assert done['solver_finished'] and done['owned_exited'] and done['exit_code'] == 0
            proof += [bound(path), done['program']]
            if tag == cpu:
                proof += [done['config'], done['bat']]
            else:
                ref = read(done['prepared_inputs']['path'])
                assert ref['program'] == done['program']
                proof += [done['prepared_inputs'], ref['config'], ref['bat'], ref['build']]
            selected = [e for e in done['outputs'] if not re.fullmatch(r'Part_\d{4}\.bi4', Path(e['path']).name)
                        or int(Path(e['path']).stem.split('_')[-1]) < 69]
            assert sum(bool(re.fullmatch(r'Part_\d{4}\.bi4', Path(e['path']).name)) for e in selected) == 69
            proof += selected
    files = [Path(__file__), TESTS / 'notes' / (TAG + '.json'), READER, READER_SOURCE, SANITIZER, MEMCHECK_FIXTURE,
             REPO / 'bin/windows/GenCase_win64.exe']
    files += [TESTS / 'support' / n for n in ['cryer_start_r1.py', 'cryer_grad_short_r1.py', 'cryer_grad_peak_r1.py',
              'cryer_preload_probe_r1.py', 'cryer_preload_peak_r1.py', 'cryer_preload_peak_half_r1.py']]
    jobs = []
    for suffix, config, dt, end, frames in JOBS:
        name = TAG + '_' + suffix
        cfg, bat = TESTS / 'configs' / (name + '_Def.xml'), TESTS / 'configs' / ('x' + name + '_win64_GPU.bat')
        jobs.append(dict(name=name, suffix=suffix, configuration=config, dt_s=dt, end_s=end, frames=frames,
                         config=bound(cfg), bat=bound(bat), **builds[config]))
        files += [cfg, bat]
    proof += [bound(p) for p in files]
    verify(proof)
    assert shutil.disk_usage(TESTS).free > 5 * 1024 ** 3
    seal(PREP, dict(utc=utc(), thread=identity(), inputs=proof, jobs=jobs, controls=controls,
                   original_limits=dict(pressure_rms_pa=5., material_displacement_max_mm=.005),
                   physical_accepted=False, peak_or_formal_admitted=False))
    print('PREPARED ONLY', PREP, flush=True)


def acceptable(m):
    return (m['pressure_rms_pa'] <= 5 and m['material_displacement_max_mm'] <= .005
            and m['fstype_mismatches'] == m['drained_mask_mismatches'] == 0)


def notification(status):
    return (f'User-authorized same-thread {TAG}: {status}. Read {STATUS}; case-relative tests/logs/{TAG}.run.json and .check.json; tests/notes/{TAG}.json. '
            'New isolated symC GPU only: Debug2frame memcheck then Release69frame coarse/half; require each prior gate. '
            'Verify owned exits, actual times/steps/native37173IDs, frozen source-build-program-runtime-input-output hashes, original safety, load and active drainage. '
            'Both Release closed Parts61-64 five equilibrium diagnostics, same-dt CPU-symC comparisons and independent GPU half must satisfy original5Pa/.005mm. '
            'Raw-GPU option differences are not half/theory errors. Debug is not Release0ULP truth. No automatic peak/full/formal acceptance. '
            'If completed solver analysis failed repair offline only; otherwise inspect exact stop reason/time/survivors. No relaxed gates, duplicate solver or old-worker restart. '
            'Report Chinese proactively and continue authorized bounded diagnosis. This new worker queues once: never restart/rearm or send connectivity tests.')


def run():
    p = read(PREP)
    assert identity() == p['thread']
    assert not any(x.exists() for x in [RUN, STATUS, CHECK, SUMMARY, PAIRS, LOG / (TAG + '.queue_attempt.json')])
    verify(p['inputs'])
    assert not inventory(), 'An existing solver is active; no duplicate admitted'
    state = dict(status='running', stage='admission', thread=p['thread'], owned_sequence_pid=os.getpid(),
                 prepared_inputs=bound(PREP), started_utc=utc(), runs=[], physical_accepted=False, peak_or_formal_admitted=False)
    summaries, comparisons = [], []
    child = current = None

    def publish():
        tmp = RUN.with_suffix('.tmp'); write_json(tmp, state); os.replace(tmp, RUN)
        s = {k: state.get(k) for k in ['status', 'stage', 'owned_sequence_pid', 'current_job', 'checked_frames', 'actual_last_saved_time_s']}
        s['run_manifest'] = bound(RUN)
        tmp = STATUS.with_suffix('.tmp'); write_json(tmp, s); os.replace(tmp, STATUS)

    def compare(folder, other, label, guarded):
        records = []
        for part in range(69):
            a, b = native(folder, part), native(other, part)
            assert np.array_equal(a.id, b.id) and a.time_s.eq(part * INTERVAL).all() and b.time_s.eq(part * INTERVAL).all()
            m = dict(**difference(a, b), part=part, time_s=part * INTERVAL, comparison=label, guarded=guarded)
            records.append(m); comparisons.append(m)
            if guarded:
                assert acceptable(m), (label, part, m)
        return dict(passed=True if guarded else None, samples=69, meaning=label,
                    max_pressure_rms_pa=max(x['pressure_rms_pa'] for x in records),
                    max_displacement_mm=max(x['material_displacement_max_mm'] for x in records))

    publish()
    try:
        for job in p['jobs']:
            assert not inventory()
            verify([job[k] for k in ['program', 'config', 'bat', 'receipt']])
            name, suffix = job['name'], job['suffix']
            folder, log, complete = TESTS / 'outputs' / name, LOG / (name + '.log'), LOG / (name + '.completion.json')
            assert not any(x.exists() for x in [folder, log, complete])
            current = dict(name=name, dt_s=job['dt_s'], program=job['program'], passed=False)
            state['runs'].append(current); state.update(stage='solver', current_job=name, checked_frames=0)
            tick = time.perf_counter()
            with log.open('xb') as stream:
                child = subprocess.Popen([os.environ['ComSpec'], '/d', '/c', job['bat']['path']], cwd=CASE,
                    stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                current['owned_wrapper_pid'] = child.pid; publish(); report = tick
                while child.poll() is None:
                    time.sleep(1)
                    if time.perf_counter() - report >= 30:
                        print('RUNNING', name, 'wall_s', round(time.perf_counter() - tick), flush=True); report = time.perf_counter()
            survivors = inventory()
            current.update(exit_code=child.returncode, owned_exited=not survivors, observed_surviving_solvers=survivors,
                           wall_seconds=time.perf_counter() - tick)
            text = (folder / 'Run.out').read_text(errors='replace') if (folder / 'Run.out').exists() else ''
            finished = child.returncode == 0 and 'Finished execution (code=0)' in text and not survivors
            seal(complete, dict(solver_finished=finished, owned_exited=not survivors, observed_surviving_solvers=survivors,
                exit_code=child.returncode, program=job['program'], config=job['config'], bat=job['bat'],
                outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()] + [bound(log)]))
            current['sealed_completion'] = bound(complete); state['stage'] = 'offline_review'; publish()
            assert finished, ('Solver failed', name, child.returncode)
            assert int(re.search(r'Steps of simulation\.*:\s*(\d+)', text)[1]) == int(job['end_s'] / job['dt_s'])
            assert len(list((folder / 'data').glob('Part_*.bi4'))) == job['frames']
            assert 'HydroMechDrainageFixedGrid=True' in text and 'SoilStressRateGradCorr="KernelGradient"' in text and 'BuiFukagawa2013' in text
            current['observed_loop_seconds'] = float(re.search(r'Simulation Runtime\.*:\s*([\d.]+)', text)[1])
            if suffix == 'dbg':
                mem = (folder / 'memcheck.log').read_text(errors='replace')
                assert memcheck_clean(mem), 'Expected CUDA zero-error and zero-byte/zero-allocation leak summaries'
                current['memcheck_zero_errors'] = True
            initial = native(folder, 0)
            assert np.array_equal(initial.id.to_numpy(), np.arange(8, 37181)), 'Unexpected initial native soil ID set'
            inspect = half_rules.inspect if suffix == 'h' else coarse_rules.inspect
            rows = []
            for part in range(job['frames']):
                row = inspect(initial if part == 0 else native(folder, part), initial, part)
                assert row['true_surface_count'] == 5153 and row['changed_fstype_count'] == 0
                rows.append(row); summaries.append(dict(run=name, dt_s=job['dt_s'], **row))
                state.update(checked_frames=part + 1, actual_last_saved_time_s=row['time_s']); publish()
            if suffix != 'dbg':
                current['equilibrium'] = equilibrium(rows)
                assert current['equilibrium']['equilibrium_diagnostic_passed'], ('Closed-state equilibrium', name)
                current['cpu_gpu'] = compare(folder, Path(p['controls'][suffix]['cpu']), name + ':GPU_vs_CPU_symC', True)
                current['raw_option'] = compare(folder, Path(p['controls'][suffix]['raw_gpu']), name + ':symC_vs_raw_GPU', False)
                if suffix == 'h':
                    current['independent_half'] = compare(folder, TESTS / 'outputs' / (TAG + '_c'), name + ':GPU_half', True)
            current['passed'] = True; publish()
        verify(p['inputs'])
        assert len(summaries) == 140 and len(comparisons) == 345
        state.update(status='gpu_short_passed_pending_physical_review', stage='terminal')
    except BaseException as error:
        state.update(status='gpu_short_rejected_or_interrupted', stage='terminal', error=repr(error), traceback=traceback.format_exc())
        publish()
        if child is not None and child.poll() is None:
            cmd = f"Get-CimInstance Win32_Process -Filter 'ProcessId={child.pid}' | Select-Object CommandLine | ConvertTo-Json -Compress"
            alive = subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True).strip()
            assert alive and current['name'] in json.loads(alive)['CommandLine'], 'Owned-stop identity mismatch; do not stop another process'
            stop = subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
            state['owned_stop_exit_code'] = stop.returncode; child.wait(timeout=30)
    finally:
        if summaries:
            pd.DataFrame(summaries).to_csv(SUMMARY, index=False, float_format='%.17g')
        if comparisons:
            pd.DataFrame(comparisons).to_csv(PAIRS, index=False, float_format='%.17g')
        state.update(finished_utc=utc(), observed_terminal_solvers=inventory(),
                     artifacts=[bound(q) for q in [SUMMARY, PAIRS] if q.exists()])
        publish()
        seal(CHECK, dict(passed=state['status'] == 'gpu_short_passed_pending_physical_review', status=state['status'],
            run=bound(RUN), runs=state['runs'], error=state.get('error'), artifacts=state['artifacts'],
            physical_accepted=False, peak_or_formal_admitted=False))
        message = notification(state['status']); assert len(message) < 2000
        seal(LOG / (TAG + '.queue_attempt.json'), dict(thread=p['thread'], utc=utc(), message=message))
        try:
            reply = subprocess.run([str(CODEX), 'queue', '--thread', p['thread'], '--message', message],
                capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
            note = dict(status='queued' if reply.returncode == 0 else 'failed_no_retry', exit_code=reply.returncode,
                        reply=(reply.stdout + reply.stderr).decode(errors='replace'))
        except Exception as error:
            note = dict(status='exception_no_retry', error=repr(error))
        seal(LOG / (TAG + '.notification.json'), note)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    for name in ['selftest', 'prepare', 'run']:
        action.add_argument('--' + name, action='store_true')
    args = parser.parse_args()
    if args.selftest:
        print(json.dumps(selftest()))
    elif args.prepare:
        prepare()
    elif args.run:
        run()
    else:
        parser.print_help()

