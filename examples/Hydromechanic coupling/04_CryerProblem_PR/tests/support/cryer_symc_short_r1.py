"""Fresh CPU raw/symmetric-C preload short sequence; no peak/formal admission."""
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
from cryer_start_r1 import CASE, TESTS, REPO, native, bound, utc, write_json
from cryer_grad_short_r1 import difference
from cryer_grad_peak_r1 import identity, CODEX
from cryer_preload_probe_r1 import equilibrium
import cryer_preload_peak_r1 as coarse_rules
import cryer_preload_peak_half_r1 as half_rules

TAG = 'cryer_symc_short_r1'
LOG = TESTS / 'logs'
PREP = LOG / (TAG + '.inputs.json')
RUN = LOG / (TAG + '.run.json')
STATUS = LOG / (TAG + '.status.json')
CHECK = LOG / (TAG + '.check.json')
BUILD = LOG / 'cryer_symc_release_r1.build.json'
STEP = LOG / 'cryer_symc_step_screen_r1.check.json'
SUMMARY = TESTS / 'figures' / (TAG + '_summary.csv')
PAIRS = TESTS / 'figures' / (TAG + '_comparisons.csv')
END = .00830078125
INTERVAL = 2. ** -13
JOBS = [(TAG + '_' + v, 2. ** (-22 if v.endswith('_h') else -21), v.startswith('on'))
        for v in ['off_c', 'off_h', 'on_c', 'on_h']]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def seal(path, obj):
    with Path(path).open('x', encoding='utf8') as f:
        json.dump(obj, f, indent=2, allow_nan=False)


def verify(entries):
    for e in entries:
        a = bound(e['path'])
        assert a['sha256'].lower() == e['sha256'].lower(), e['path']
        if 'bytes' in e:
            assert a['bytes'] == e['bytes'], e['path']


def inventory():
    cmd = "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'DualSPHysics*' -or $_.Name -eq 'cryer_symc_release_r1.exe' } | Select-Object ProcessId,ParentProcessId,Name,CommandLine) | ConvertTo-Json -Compress"
    raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True).strip()
    return json.loads(raw) if raw else []


def selftest():
    source = (TESTS / 'configs/cryer_preload_probe_r1_Def.xml').read_text(encoding='utf8')
    source = source.replace('GPU preload probe through 17*2^-11 seconds; not a full validation',
                            'CPU raw/symmetric-C short diagnostic; 69 frames, not a full validation')
    entry = (TESTS / 'configs/xcryer_grad_fine_r1_c_win64_CPU.bat').read_text(encoding='utf8')
    for name, dt, candidate in JOBS:
        expected = source if dt == 2. ** -21 else source.replace('0.000000476837158203125', '0.0000002384185791015625')
        cfg = TESTS / 'configs' / (name + '_Def.xml')
        bat = TESTS / 'configs' / ('x' + name + '_win64_CPU.bat')
        assert cfg.read_text(encoding='utf8').rstrip() == expected.rstrip()
        text = bat.read_text(encoding='utf8')
        expected_bat = entry.replace('cryer_grad_fine_r1_c', name)
        if candidate:
            expected_bat = expected_bat.replace('"%dirbin%/DualSPHysics5.2CPU_win64.exe"',
                                               '"tests/outputs/cryer_symc_release_r1/cryer_symc_release_r1.exe"')
        assert text.rstrip() == expected_bat.rstrip(), 'Only name and candidate program may differ from the existing CPU BAT'
        assert '-cpu -ompthreads:8 -stable' in text and 'if exist "%dirout%" goto fail' in text
        assert ('tests/outputs/cryer_symc_release_r1/cryer_symc_release_r1.exe' in text) == candidate
        assert END / dt in [17408, 34816] and END / INTERVAL + 1 == 69
    return dict(passed=True, physical_solver_started=False, xml_difference='Only dt for halves and diagnostic comment; OFF/ON inputs identical.')


def prepare():
    selftest()
    assert not any(p.exists() for p in [PREP, RUN, STATUS, CHECK, SUMMARY, PAIRS])
    assert not any((TESTS / 'outputs' / name).exists() for name, _, _ in JOBS)
    gate = read(STEP)
    assert gate['analysis_checks_passed'] and gate['coarse_dt_admitted'] and gate['half_dt_admitted']
    verify(gate['inputs'])
    build = read(BUILD)
    assert build['configuration'] == 'ReleaseCPU' and build['status'] == 'built_not_run'
    assert build['protected_inputs_unchanged'] and build['canonical_main_object_retained'] and not build['harness_object_added']
    assert build['source_comparison']['exact_normalized_source_is_single_Darcy_replacement']
    assert build['compiled_header_dependency_set_matches_authoritative']
    verify(build['inputs'] + build['runtime'] + build['artifacts'] + [build['program']])
    assert Path(build['program']['path']).resolve() == (TESTS / 'outputs/cryer_symc_release_r1/cryer_symc_release_r1.exe').resolve()
    prior = LOG / 'cryer_preload_peak_half_review_r1.visual.json'
    assert read(prior)['analysis_checks_passed'] and read(prior)['visual_review_passed']
    proof = [bound(p) for p in [Path(__file__), TESTS / 'notes' / (TAG + '.json'), BUILD, STEP, prior,
             TESTS / 'support/cryer_symc_step_screen_r1.py', REPO / 'bin/windows/GenCase_win64.exe']]
    proof += build['inputs'] + build['runtime'] + build['artifacts'] + gate['inputs']
    proof += [bound(TESTS / 'support' / n) for n in ['cryer_start_r1.py', 'cryer_grad_short_r1.py',
              'cryer_preload_probe_r1.py', 'cryer_preload_peak_r1.py', 'cryer_preload_peak_half_r1.py']]
    raw = bound(REPO / 'bin/windows/DualSPHysics5.2CPU_win64.exe')
    jobs = []
    for name, dt, candidate in JOBS:
        cfg = TESTS / 'configs' / (name + '_Def.xml')
        bat = TESTS / 'configs' / ('x' + name + '_win64_CPU.bat')
        jobs.append(dict(name=name, dt_s=dt, candidate=candidate, config=bound(cfg), bat=bound(bat),
                         program=build['program'] if candidate else raw))
        proof += [bound(cfg), bound(bat)]
    for tag in ['cryer_preload_peak_r1', 'cryer_preload_peak_half_r1']:
        completion = LOG / (tag + '.completion.json')
        old = read(completion)
        assert old['solver_finished'] and old['owned_exited'] and old['exit_code'] == 0
        proof.append(bound(completion))
        initial = [e for e in old['outputs'] if re.fullmatch(r'Part_\d{4}\.bi4', Path(e['path']).name)
                   and int(Path(e['path']).stem.split('_')[-1]) < 69]
        assert len(initial) == 69
        proof += initial
    verify(proof + [raw, build['program']])
    assert shutil.disk_usage(TESTS).free > 5 * 1024 ** 3
    seal(PREP, dict(thread=identity(), utc=utc(), inputs=proof, jobs=jobs,
                    scalar_step_only_prerequisite=bound(STEP), build=bound(BUILD),
                    half_and_same_physics_backend_limits=dict(pressure_rms_pa=5., material_displacement_max_mm=.005),
                    peak_admitted=False, formal_admitted=False))
    print('PREPARED', PREP, flush=True)


def acceptable(m):
    return (m['pressure_rms_pa'] <= 5 and m['material_displacement_max_mm'] <= .005
            and m['fstype_mismatches'] == m['drained_mask_mismatches'] == 0)


def run():
    p = read(PREP)
    assert identity() == p['thread']
    assert not any(x.exists() for x in [RUN, STATUS, CHECK, SUMMARY, PAIRS])
    verify(p['inputs'] + [j['program'] for j in p['jobs']])
    assert not inventory(), 'An existing solver is active; no duplicate admitted'
    state = dict(status='running', stage='admission', thread=p['thread'], owned_sequence_pid=os.getpid(),
                 prepared_inputs=bound(PREP), started_utc=utc(), runs=[], physical_accepted=False,
                 peak_window_admitted=False, formal_admitted=False)
    summaries, comparisons = [], []
    child = None
    current = None
    initial = None

    def publish():
        for path, obj in [(RUN, state), (STATUS, {k: state.get(k) for k in
                          ['status', 'stage', 'owned_sequence_pid', 'current_job', 'checked_frames', 'actual_last_saved_time_s']})]:
            tmp = path.with_suffix('.tmp')
            write_json(tmp, obj)
            os.replace(tmp, path)

    def compare(folder, other, kind, guarded):
        records = []
        for part in range(69):
            a, b = native(folder, part), native(other, part)
            assert float(a.time_s.iloc[0]) == float(b.time_s.iloc[0]) == part * INTERVAL
            m = difference(a, b)
            m.update(part=part, time_s=part * INTERVAL, comparison=kind, guarded=guarded)
            comparisons.append(m)
            records.append(m)
            if guarded:
                assert acceptable(m), (kind, part, m)
        return dict(passed=True if guarded else None, samples=69, meaning=kind,
                    max_pressure_rms_pa=max(x['pressure_rms_pa'] for x in records),
                    max_displacement_mm=max(x['material_displacement_max_mm'] for x in records))

    publish()
    try:
        for job in p['jobs']:
            assert not inventory()
            verify([job['program'], job['config'], job['bat'], p['build'], p['scalar_step_only_prerequisite']])
            name = job['name']
            folder = TESTS / 'outputs' / name
            log = LOG / (name + '.log')
            complete = LOG / (name + '.completion.json')
            assert not any(x.exists() for x in [folder, log, complete])
            current = dict(name=name, dt_s=job['dt_s'], candidate=job['candidate'], program=job['program'], passed=False)
            state['runs'].append(current)
            state.update(stage='solver', current_job=name, checked_frames=0)
            started = time.perf_counter()
            with log.open('xb') as stream:
                child = subprocess.Popen([os.environ['ComSpec'], '/d', '/c', job['bat']['path']], cwd=CASE,
                                         stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                current['owned_wrapper_pid'] = child.pid
                publish()
                report = started
                while child.poll() is None:
                    time.sleep(1)
                    if time.perf_counter() - report >= 30:
                        print('RUNNING', name, 'wall_s', round(time.perf_counter() - started), flush=True)
                        report = time.perf_counter()
            survivors = inventory()
            current.update(exit_code=child.returncode, owned_exited=not survivors,
                           observed_surviving_solvers=survivors, wall_seconds=time.perf_counter() - started)
            text = (folder / 'Run.out').read_text(errors='replace') if (folder / 'Run.out').exists() else ''
            finished = child.returncode == 0 and 'Finished execution (code=0)' in text and not survivors
            seal(complete, dict(solver_finished=finished, owned_exited=not survivors,
                               observed_surviving_solvers=survivors, exit_code=child.returncode,
                               program=job['program'], config=job['config'], bat=job['bat'],
                               outputs=[bound(q) for q in sorted(folder.rglob('*')) if q.is_file()] + [bound(log)]))
            current['sealed_completion'] = bound(complete)
            publish()
            assert finished, ('Solver failed', name, child.returncode)
            assert not inventory(), 'Unexpected surviving solver after wrapper exit'
            assert int(re.search(r'Steps of simulation\.*:\s*(\d+)', text)[1]) == int(END / job['dt_s'])
            assert len(list((folder / 'data').glob('Part_*.bi4'))) == 69
            assert 'HydroMechDrainageFixedGrid=True' in text and 'SoilStressRateGradCorr="KernelGradient"' in text
            assert 'BuiFukagawa2013' in text
            current['observed_loop_seconds'] = float(re.search(r'Simulation Runtime\.*:\s*([\d.]+)', text)[1])
            state['stage'] = 'offline_review'
            a0 = native(folder, 0)
            if initial is None:
                initial = a0
            cols = ['id', 'x', 'y', 'z', 'rho', 'pressure', 'mass', 'dp', 'h']
            assert np.array_equal(a0[cols], initial[cols]), 'Fresh initial native fields changed'
            rows = []
            inspect = coarse_rules.inspect if job['dt_s'] == 2. ** -21 else half_rules.inspect
            for part in range(69):
                row = inspect(a0 if part == 0 else native(folder, part), initial, part)
                assert row['true_surface_count'] == 5153 and row['changed_fstype_count'] == 0
                rows.append(row)
                summaries.append(dict(run=name, candidate=job['candidate'], dt_s=job['dt_s'], **row))
                state.update(checked_frames=part + 1, actual_last_saved_time_s=row['time_s'])
                publish()
            current['equilibrium'] = equilibrium(rows)
            assert current['equilibrium']['equilibrium_diagnostic_passed'], ('Closed-state equilibrium', name)
            suffix = '_h' if job['dt_s'] == 2. ** -22 else '_c'
            if not job['candidate']:
                old = TESTS / 'outputs' / ('cryer_preload_peak_half_r1' if suffix == '_h' else 'cryer_preload_peak_r1')
                current['same_physics_cpu_gpu'] = compare(folder, old, name + ':CPU_vs_retained_GPU', True)
            else:
                current['option_change'] = compare(folder, TESTS / 'outputs' / (TAG + '_off' + suffix), name + ':symmetric_vs_receiver_C', False)
            if suffix == '_h':
                current['independent_half'] = compare(folder, TESTS / 'outputs' / (name[:-1] + 'c'), name + ':own_half', True)
            current['passed'] = True
            publish()
        verify(p['inputs'] + [j['program'] for j in p['jobs']])
        state.update(status='short_pairs_passed_pending_physical_review', stage='terminal')
    except BaseException as error:
        state.update(status='short_rejected_or_interrupted', stage='terminal', error=repr(error), traceback=traceback.format_exc())
        publish()
        if child is not None and child.poll() is None:
            # The PID comes only from this worker's own Popen. Verify its command still names this exact BAT.
            cmd = f"Get-CimInstance Win32_Process -Filter 'ProcessId={child.pid}' | Select-Object CommandLine | ConvertTo-Json -Compress"
            alive = subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True).strip()
            assert alive and Path(current['name']).name in json.loads(alive)['CommandLine'], 'Owned-stop identity mismatch; do not stop another process'
            stop = subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
            state['owned_stop_exit_code'] = stop.returncode
            child.wait(timeout=30)
    finally:
        if summaries:
            pd.DataFrame(summaries).to_csv(SUMMARY, index=False, float_format='%.17g')
        if comparisons:
            pd.DataFrame(comparisons).to_csv(PAIRS, index=False, float_format='%.17g')
        state.update(finished_utc=utc(), artifacts=[bound(q) for q in [SUMMARY, PAIRS] if q.exists()])
        publish()
        seal(CHECK, dict(passed=state['status'] == 'short_pairs_passed_pending_physical_review',
                         status=state['status'], run=bound(RUN), runs=state['runs'], error=state.get('error'),
                         artifacts=state['artifacts'], physical_accepted=False, peak_or_formal_admitted=False))
        message = (f'User-authorized same-thread {TAG}: {state["status"]}. Read {STATUS}, {RUN}, {CHECK} and tests/notes/{TAG}.json. '
                   'Four fresh CPU8 Release raw/symC coarse2^-21/half2^-22 short jobs, .00830078125s/69frames each, gated in order. '
                   'Verify earlier safety/equilibrium/rawCPU-GPU/independent-half5Pa .005mm gates before later data. '
                   'On/off differences are not half errors. Review exact exits/times/IDs/source-build-input-output hashes and all-active drainage. '
                   'No automatic peak/formal admission; diagnose without guard relaxation, duplicate solver or old restart. '
                   'If completed solver analysis failed, repair offline only. Report Chinese proactively and continue authorized bounded diagnosis. '
                   'This worker queues once, never restart/rearm or send self-tests.')
        assert len(message) < 2000
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
    action.add_argument('--selftest', action='store_true')
    action.add_argument('--prepare', action='store_true')
    action.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.selftest:
        print(json.dumps(selftest()))
    elif args.prepare:
        prepare()
    elif args.run:
        run()
    else:
        parser.print_help()
