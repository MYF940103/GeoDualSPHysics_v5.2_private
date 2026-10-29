"""One proposed fresh GPU sym-C independent peak HALF; default help, no formal admission."""
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
from cryer_start_r1 import CASE, TESTS, REPO, READER, READER_SOURCE, bound, native, utc, write_json
from cryer_grad_short_r1 import difference
from cryer_grad_peak_r1 import identity, CODEX
from cryer_preload_probe_r1 import equilibrium
from cryer_symc_gpu_short_r1 import read, seal, verify, inventory
import cryer_preload_peak_r1 as retained
import cryer_preload_peak_half_r1 as half_rules

TAG = 'cryer_symc_gpu_peak_half_r1'
DT, END, INTERVAL = 2. ** -22, .0703125, 2. ** -13
RAMP, DRAIN, STEPS, FRAMES = 2. ** -8, 2. ** -7, 294912, 577
LOGS = TESTS / 'logs'
CONFIG = TESTS / 'configs' / (TAG + '_Def.xml')
BAT = TESTS / 'configs' / ('x' + TAG + '_win64_GPU.bat')
FOLDER = TESTS / 'outputs' / TAG
PREP, RUN, STATUS, CHECK, COMPLETE, PREFIX = [LOGS / (TAG + s) for s in
    ['.inputs.json', '.run.json', '.status.json', '.check.json', '.completion.json', '.prefix.json']]
SUMMARY, PAIR = [TESTS / 'figures' / (TAG + s) for s in ['_summary.csv', '_half.csv']]
BUILD = LOGS / 'cryer_symc_gpu_build_r3_Release.build.json'
PROGRAM = TESTS / 'outputs/cryer_symc_gpu_build_r3/Release/cryer_symc_gpu_r3_Release.exe'
SHORT = 'cryer_symc_gpu_short_r1'
SHORT_CHECK = LOGS / (SHORT + '.check.json')
SHORT_REVIEW = LOGS / 'cryer_symc_gpu_short_review_r1.check.json'
SHORT_VISUAL = LOGS / 'cryer_symc_gpu_short_review_r1.visual.json'
PREFIX_REFERENCE = TESTS / 'outputs' / (SHORT + '_h')
COARSE_REFERENCE = TESTS / 'outputs/cryer_symc_gpu_peak_r1'
PEAK_REVIEW = LOGS / 'cryer_symc_gpu_peak_review_r1.check.json'
PEAK_VISUAL = LOGS / 'cryer_symc_gpu_peak_review_r1.visual.json'


def unique(records):
    result = {}
    for entry in records:
        path = str(Path(entry['path']).resolve())
        key = path.casefold()
        assert key not in result or result[key]['sha256'].lower() == entry['sha256'].lower(), ('Conflicting binding', path)
        result[key] = dict(entry, path=path)
    return list(result.values())


def reserved(include_prepare=False):
    paths = [RUN, STATUS, CHECK, COMPLETE, PREFIX, SUMMARY, PAIR, FOLDER]
    paths += [LOGS / (TAG + s) for s in ['.log', '.queue_attempt.json', '.notification.json']]
    if include_prepare:
        paths.append(PREP)
    assert not any(p.exists() for p in paths), 'Retained stage exists; never overwrite/restart'


def prerequisites():
    short, review, visual = read(SHORT_CHECK), read(SHORT_REVIEW), read(SHORT_VISUAL)
    assert short['passed'] and len(short['runs']) == 3
    assert review['analysis_checks_passed'] and visual['analysis_checks_passed'] and visual['visual_review_passed']
    assert visual['review_check'] == bound(SHORT_REVIEW)
    runs = short['runs']
    assert [r['name'] for r in runs] == [SHORT + '_' + s for s in ['dbg', 'c', 'h']]
    assert all(r['passed'] and r['owned_exited'] and r['exit_code'] == 0 and not r['observed_surviving_solvers'] for r in runs)
    assert runs[0]['memcheck_zero_errors']
    assert runs[2]['independent_half']['passed'] and runs[2]['independent_half']['samples'] == 69
    for pair in [runs[1]['cpu_gpu'], runs[2]['cpu_gpu'], runs[2]['independent_half']]:
        assert pair['passed'] and pair['samples'] == 69
        assert pair['max_pressure_rms_pa'] <= 5 and pair['max_displacement_mm'] <= .005
    assert all(r['equilibrium']['equilibrium_diagnostic_passed'] for r in runs[1:])
    proof = [bound(p) for p in [SHORT_CHECK, SHORT_REVIEW, SHORT_VISUAL]]
    proof += review['sources'] + review['artifacts'] + [visual['review_check']]
    proof += short['artifacts'] + [short['run']]
    run = read(short['run']['path'])
    assert run['status'] == 'gpu_short_passed_pending_physical_review' and not run['observed_terminal_solvers']
    proof += [run['prepared_inputs']]
    prepared = read(run['prepared_inputs']['path'])
    proof += prepared['inputs']
    for r in runs:
        proof += [r['sealed_completion'], r['program']]
        done = read(r['sealed_completion']['path'])
        assert done['solver_finished'] and done['owned_exited'] and done['exit_code'] == 0
        proof += [done['program'], done['config'], done['bat']] + done['outputs']
    build = read(BUILD)
    assert build['status'] == 'built_not_run' and build['configuration'] == 'Release'
    assert build['protected_inputs_unchanged'] and build['canonical_main_object_retained']
    assert build['compiled_dependencies_all_bound_before_compile'] and all(s['exit_code'] == 0 for s in build['stages'])
    delta = build['source_comparison']
    assert delta['exact_normalized_source_is_declared_delta'] and delta['signature_additions'] == 1
    assert delta['existing_call_additions'] == 4 and delta['darcy_block_replacements'] == 1
    assert delta['cpu_candidate_Darcy_algebra_exact_ignoring_indentation_and_CTE_prefix']
    assert build['program'] == runs[1]['program'] == runs[2]['program'] == bound(PROGRAM)
    proof += [bound(BUILD), build['program'], build['plan']]
    proof += build['protected_inputs'] + build['compiled_dependencies'] + build['artifacts']
    proof += [x[k] for x in build['runtime'] for k in ['source', 'target']]
    # Adopt the completed candidate coarse, never rerun it or treat raw as half truth.
    coarse_path = LOGS / 'cryer_symc_gpu_peak_r1.check.json'
    coarse = read(coarse_path)
    assert coarse['passed'] and coarse['checked_frames'] == FRAMES and coarse['prefix_samples'] == 69
    assert coarse['closed_equilibrium_diagnostics']['equilibrium_diagnostic_passed']
    prefix = read(coarse['prefix_receipt']['path'])
    assert prefix['checked_samples'] == 69 and prefix['all35_columns0ulp_passed'] and prefix['excluded_columns'] == []
    assert len(prefix['samples']) == 69 and all(x['all_35_columns0ulp'] and not x['differences'] for x in prefix['samples'])
    peak_review, peak_visual = read(PEAK_REVIEW), read(PEAK_VISUAL)
    assert peak_review['analysis_checks_passed'] and peak_visual['analysis_checks_passed'] and peak_visual['visual_review_passed']
    assert peak_visual['review_check'] == bound(PEAK_REVIEW)
    coarse_done = read(coarse['sealed_completion']['path'])
    assert coarse_done['solver_finished'] and coarse_done['owned_exited'] and coarse_done['exit_code'] == 0
    coarse_run = read(coarse['run_manifest']['path'])
    assert coarse_run['actual_last_saved_time_s'] == END and coarse_run['owned_exited'] and coarse_run['exit_code'] == 0
    assert not coarse_run['observed_terminal_solvers']
    coarse_prepared = read(coarse_run['prepared_inputs']['path'])
    assert coarse_done['program'] == coarse_prepared['program'] == bound(PROGRAM)
    assert sum(bool(re.fullmatch(r'Part_\d{4}\.bi4', Path(x['path']).name)) for x in coarse_done['outputs']) == FRAMES
    proof += [bound(coarse_path), coarse['run_manifest'], coarse['sealed_completion'], coarse['prefix_receipt'],
              coarse_run['prepared_inputs'], coarse_done['program'], coarse_prepared['build'],
              bound(PEAK_REVIEW), bound(PEAK_VISUAL), peak_visual['review_check']]
    proof += coarse_prepared['inputs'] + coarse_done['outputs'] + coarse_run['artifacts']
    proof += peak_review['sources'] + peak_review['artifacts']

    # The caller hashes the complete deduplicated chain once, including its own inputs.
    return unique(proof)


def selftest():
    source = TESTS / 'configs/cryer_preload_peak_r1_Def.xml'
    old = 'GPU preload peak diagnostic through drainage plus 0.0625 seconds; not full validation'
    new = 'Isolated symmetric-C GPU peak half diagnostic through drainage plus 0.0625 seconds; not full validation'
    text = source.read_text(encoding='utf8')
    assert text.count(old) == 1 and text.count('0.000000476837158203125') == 2
    expected_xml = text.replace(old, new).replace('0.000000476837158203125', '0.0000002384185791015625')
    assert CONFIG.read_text(encoding='utf8') == expected_xml
    template = TESTS / 'configs/xcryer_preload_peak_r1_win64_GPU.bat'
    expected = template.read_text(encoding='utf8').replace('cryer_preload_peak_r1', TAG).replace(
        '"%dirbin%/DualSPHysics5.2_GEO_win64.exe"',
        '"tests/outputs/cryer_symc_gpu_build_r3/Release/cryer_symc_gpu_r3_Release.exe"')
    assert BAT.read_text(encoding='utf8') == expected
    assert END / DT == STEPS and END / INTERVAL + 1 == FRAMES and INTERVAL / DT == 512
    assert DRAIN / INTERVAL == 64 and DRAIN / DT == 32768 and RAMP / DT == 16384
    assert half_rules.DT == DT and half_rules.INTERVAL == INTERVAL and half_rules.FRAMES == FRAMES
    assert 'assert a.saved_step.eq(part*512-1 if part else 0).all()' in Path(half_rules.__file__).read_text(encoding='utf8')
    assert np.array_equal(np.r_[0, np.arange(1, 69) * 512 - 1], np.array([0] + [part * 512 - 1 for part in range(1, 69)]))
    assert np.r_[0, np.arange(1, FRAMES) * 512 - 1][-1] == STEPS - 1
    assert half_rules.half_screen(dict(pressure_rms_pa=5., material_displacement_max_mm=.005))
    assert not half_rules.half_screen(dict(pressure_rms_pa=np.nextafter(5., np.inf), material_displacement_max_mm=0.))
    assert not half_rules.half_screen(dict(pressure_rms_pa=0., material_displacement_max_mm=np.nextafter(.005, np.inf)))
    # Exercise every native bit-comparison field, including signed/interval metadata.
    columns = read(LOGS / 'cryer_preload_peak_r1.prefix.json')['samples'][0]['compared_columns']
    assert len(columns) == 35 and 'dterror_s' in columns
    a = pd.DataFrame(np.zeros((2, 35), dtype='<f8'), columns=columns)
    a['id'] = [8., 9.]
    assert retained.prefix_compare(a, a.copy(), 0)['all_35_columns0ulp']
    for col in columns:
        b = a.copy(); b.loc[0, col] = np.nextafter(float(a.loc[0, col]), np.inf)
        assert not retained.prefix_compare(a, b, 0)['all_35_columns0ulp'], col
    assert len(notification('symc_gpu_peak_half_rejected_or_interrupted')) < 2000
    return dict(passed=True, xml_changes='Only DtIni/DtFixed half and explanatory comment; same physical parameters',
                bat_changes='New tag and isolated r3 Release selection only',
                inspect='Retained pure half_rules.inspect used directly; actual saved_step512factor, no mutation or replacement',
                prefix_samples=69, prefix_columns=35, prefix_exceptions=[],
                expected_steps=STEPS, expected_frames=FRAMES,
                prepared=False, solver_started=False, files_written=False, notification_sent=False)


def prepare():
    reserved(include_prepare=True); selftest()
    proof = prerequisites()
    files = [Path(__file__), TESTS / 'notes' / (TAG + '.json'), CONFIG, BAT, READER, READER_SOURCE, CODEX,
             REPO / 'bin/windows/GenCase_win64.exe', TESTS / 'configs/cryer_preload_peak_r1_Def.xml',
             TESTS / 'configs/xcryer_preload_peak_r1_win64_GPU.bat']
    files += [TESTS / 'support' / n for n in ['cryer_start_r1.py', 'cryer_gpu_base_r1.py',
        'cryer_grad_peak_r1.py', 'cryer_grad_short_r1.py', 'cryer_preload_probe_r1.py',
        'cryer_preload_half_r1.py', 'cryer_preload_peak_r1.py', 'cryer_preload_peak_half_r1.py',
        'cryer_symc_gpu_short_r1.py', 'cryer_symc_gpu_peak_r1.py']]
    proof = unique(proof + [bound(p) for p in files]); verify(proof)
    observed = sum(p.stat().st_size for p in PREFIX_REFERENCE.rglob('*') if p.is_file())
    estimated = int(observed * FRAMES / 69)
    free = shutil.disk_usage(TESTS).free; required = 2 * estimated + 2 * 1024 ** 3
    assert free >= required, ('Insufficient disk for retained native outputs and review margin', free, required)
    seal(PREP, dict(status='prepared_not_started', utc=utc(), thread=identity(), inputs=proof,
        config=bound(CONFIG), bat=bound(BAT), program=bound(PROGRAM), build=bound(BUILD),
        dt_s=DT, end_s=END, expected_steps=STEPS, expected_frames=FRAMES,
        reviewed_short=bound(SHORT_REVIEW), reviewed_short_visual=bound(SHORT_VISUAL),
        reviewed_peak=bound(PEAK_REVIEW), reviewed_peak_visual=bound(PEAK_VISUAL),
        prefix_reference=str(PREFIX_REFERENCE), candidate_coarse_reference=str(COARSE_REFERENCE),
        disk_budget=dict(free_bytes=free, short_bytes=observed, estimated_output_bytes=estimated, required_free_bytes=required),
        physical_accepted=False, peak_half_accepted=False, full_cycle_accepted=False, automatic_formal_run_admitted=False))
    print('PREPARED ONLY', PREP, flush=True)


def notification(status):
    return (f'User-authorized same-thread {TAG}: {status}. Read {STATUS}; case-relative tests/logs/{TAG}.run.json,.check.json,.completion.json,.prefix.json and tests/notes/{TAG}.json. '
        'Only one fresh isolated symC GPU HALF dt2^-22,end.0703125=tD+.0625,294912steps/577frames; source/physics unchanged, no PART restart. '
        'Adopt completed candidate coarse cryer_symc_gpu_peak_r1; no coarse/raw rerun. Verify owned exits, actual times/steps/native37173IDs and all frozen source-build-runtime-input-output hashes. '
        'All577 original native safety/active drainage/load/elastic/geometry/natural/pore-step checks remain. Part64 at tD is pre-open; true FSType2/3 p=0 only at t>tD; closed equilibrium diagnostics remain separate. '
        'Require own GPUshort_h69-frame prefix all35 columns0ULP including dterror with no exceptions. Half saved_step=part*512-1, coarse=part*256-1; never rewrite native metadata. '
        'Require all577 independent candidate coarse/half pressureRMS<=5Pa and material-displacement-max<=.005mm at exact saved times, no interpolation. '
        'Review full startup and Mandel peak against unchanged finite-Kw finite-r18 reference. Half agreement/normal exit are not physical/full/formal acceptance. '
        'If analysis fails after sealed completion repair offline only, never rerun; runtime failure needs exact reason/time/survivors. Preserve evidence, no relaxed gates/duplicates/old-worker restart. '
        'Report Chinese proactively and continue reviewed diagnosis. This new one-shot queues once; never restart/rearm or self-test; no automatic formal run.')


def notify(state):
    assert identity() == state['thread']
    message = notification(state['status']); assert len(message) < 2000
    seal(LOGS / (TAG + '.queue_attempt.json'), dict(utc=utc(), thread=state['thread'], message=message, message_chars=len(message)))
    try:
        result = subprocess.run([str(CODEX), 'queue', '--thread', state['thread'], '--message', message],
            capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        answer = dict(status='queued' if result.returncode == 0 else 'failed_no_retry', exit_code=result.returncode,
                      reply=(result.stdout + result.stderr).decode(errors='replace'))
    except Exception as error:
        answer = dict(status='exception_no_retry', error=repr(error))
    seal(LOGS / (TAG + '.notification.json'), answer)


def run():
    prepared = read(PREP); reserved()
    assert identity() == prepared['thread'], 'Wrong conversation; do not queue another thread'
    state = dict(status='running', stage='admission', thread=prepared['thread'], owned_sequence_pid=os.getpid(),
        started_utc=utc(), prepared_inputs=bound(PREP), program=prepared['program'], checked_frames=0,
        physical_accepted=False, peak_half_accepted=False, automatic_formal_run_admitted=False)
    child = None; rows, pairs, prefix = [], [], []
    log = LOGS / (TAG + '.log'); started = time.perf_counter()

    def publish():
        tmp = RUN.with_suffix('.tmp'); write_json(tmp, state); os.replace(tmp, RUN)
        item = {k: state.get(k) for k in ['status', 'stage', 'owned_sequence_pid', 'owned_wrapper_pid', 'checked_frames', 'actual_last_saved_time_s']}
        item['run_manifest'] = bound(RUN)
        tmp = STATUS.with_suffix('.tmp'); write_json(tmp, item); os.replace(tmp, STATUS)

    publish()
    try:
        verify(prepared['inputs'] + [prepared['program'], prepared['build']]); prerequisites(); selftest()
        assert not inventory(), 'An existing solver is active; never duplicate'
        assert shutil.disk_usage(TESTS).free >= prepared['disk_budget']['required_free_bytes']
        state['stage'] = 'solver'; publish()
        with log.open('xb') as stream:
            child = subprocess.Popen([os.environ['ComSpec'], '/d', '/c', prepared['bat']['path']], cwd=CASE,
                stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_wrapper_pid'] = child.pid; publish(); report = started
            while child.poll() is None:
                time.sleep(1)
                if time.perf_counter() - report >= 30:
                    print('RUNNING', TAG, 'wall_s', round(time.perf_counter() - started), flush=True); report = time.perf_counter()
        survivors = inventory()
        state.update(exit_code=child.returncode, owned_exited=not survivors, observed_surviving_solvers=survivors,
                     solver_wall_seconds=time.perf_counter() - started)
        text = (FOLDER / 'Run.out').read_text(errors='replace') if (FOLDER / 'Run.out').exists() else ''
        finished = child.returncode == 0 and 'Finished execution (code=0)' in text and not survivors
        # Seal raw solver outcome and output hashes BEFORE any offline native check.
        seal(COMPLETE, dict(solver_finished=finished, owned_exited=not survivors, observed_surviving_solvers=survivors,
            exit_code=child.returncode, owned_wrapper_pid=child.pid, utc=utc(), prepared_inputs=bound(PREP),
            program=prepared['program'], config=prepared['config'], bat=prepared['bat'],
            outputs=[bound(p) for p in sorted(FOLDER.rglob('*')) if p.is_file()] + [bound(log)]))
        state.update(sealed_completion=bound(COMPLETE), stage='offline_analysis'); publish()
        assert finished, 'Solver exit, completion text or survivor check failed'
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)', text)[1]) == STEPS
        assert len(list((FOLDER / 'data').glob('Part_*.bi4'))) == FRAMES
        for flag in ['SoilStressRateGradCorr="KernelGradient"', 'HydroMechDrainageFixedGrid=True',
                     'PoreCompressionSourceMode="PairDivergence"', 'PoreCompressionGradCorr="KernelGradient"', 'BuiFukagawa2013']:
            assert flag in text, flag
        for label, value in [('HydroMechTopLoadQ0', retained.Q), ('HydroMechTopLoadRampTime', RAMP), ('HydroMechDrainageStartTime', DRAIN)]:
            found = re.search(re.escape(label) + r':\s*([^\r\n]+)', text)
            assert found and float(found[1]) == float(format(value, '.6g'))
        assert float(re.search(r'^\s*SoilDampingCoef=([^\r\n]+)', text, re.M)[1]) == .00004
        state['actual_gpu'] = re.search(r'Device default:\s*([^\r\n]+)', text)[1]
        state['observed_loop_seconds'] = float(re.search(r'Simulation Runtime\.*:\s*([\d.]+)', text)[1])
        initial = native(FOLDER, 0)
        assert np.array_equal(initial.id.to_numpy(), np.arange(8, 37181))
        state['center_fixed_material_ids'] = list(map(int, initial.id[np.linalg.norm(initial[['x', 'y', 'z']], axis=1) <= .0025 + 1e-12]))
        assert len(state['center_fixed_material_ids']) == 18
        for part in range(FRAMES):
            a = initial if part == 0 else native(FOLDER, part)
            row = half_rules.inspect(a, initial, part)  # Existing half helper; actual 512-factor metadata checked, never rewritten.
            assert row['true_surface_count'] == 5153 and row['changed_fstype_count'] == 0
            rows.append(row)
            if part < 69:
                record = retained.prefix_compare(a, native(PREFIX_REFERENCE, part), part); prefix.append(record)
                assert record['all_35_columns0ulp'], ('Own short prefix changed', record)
            coarse = native(COARSE_REFERENCE, part)
            assert coarse.time_s.eq(part * INTERVAL).all() and coarse.saved_step.eq(part * 256 - 1 if part else 0).all()
            assert float(a.time_s.iloc[0]) == float(coarse.time_s.iloc[0])
            item = difference(a, coarse)
            item.update(part=part, time_s=row['time_s'], coarse_time_s=float(coarse.time_s.iloc[0]),
                        comparison='independent_candidate_half', screen_passed=half_rules.half_screen(item), is_theory_error=False)
            pairs.append(item)
            state.update(checked_frames=part + 1, actual_last_saved_time_s=row['time_s']); publish()
            if part % 32 == 0:
                print('CHECKED', part + 1, '/', FRAMES, flush=True)
        state['closed_equilibrium_diagnostics'] = equilibrium(rows)
        assert state['closed_equilibrium_diagnostics']['equilibrium_diagnostic_passed']
        assert len(rows) == len(pairs) == FRAMES and len(prefix) == 69 and rows[-1]['time_s'] == END
        state['half_screen_passed'] = all(p['screen_passed'] for p in pairs)
        state['half_failures'] = [p for p in pairs if not p['screen_passed']]
        verify(prepared['inputs'] + [prepared['program'], prepared['build']])
        assert state['half_screen_passed'], ('Original all577 5Pa/.005mm half gate failed', state['half_failures'])
        state.update(status='symc_gpu_peak_half_passed_pending_physical_review', stage='terminal')
    except BaseException as error:
        if child is not None and child.poll() is None:
            cmd = f"Get-CimInstance Win32_Process -Filter 'ProcessId={child.pid}' | Select-Object CommandLine | ConvertTo-Json -Compress"
            alive = subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            assert alive and BAT.name in json.loads(alive)['CommandLine'], 'Owned-stop identity mismatch; never stop another process'
            stop = subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            state['owned_stop_exit_code'] = stop.returncode; child.wait(timeout=30)
        state.update(status='symc_gpu_peak_half_rejected_or_interrupted', stage='terminal', error=repr(error), traceback=traceback.format_exc())
    finally:
        artifacts = []
        for path, data in [(SUMMARY, rows), (PAIR, pairs)]:
            if data:
                with path.open('x', encoding='utf8', newline='') as stream:
                    pd.DataFrame(data).to_csv(stream, index=False, float_format='%.17g')
                artifacts.append(bound(path))
        seal(PREFIX, dict(checked_samples=len(prefix), all35_columns0ulp_passed=len(prefix) == 69 and all(p['all_35_columns0ulp'] for p in prefix),
                         excluded_columns=[], samples=prefix)); artifacts.append(bound(PREFIX))
        state.update(finished_utc=utc(), wall_seconds=time.perf_counter() - started, observed_terminal_solvers=inventory(), artifacts=artifacts)
        publish()
        seal(CHECK, dict(passed=state['status'] == 'symc_gpu_peak_half_passed_pending_physical_review', status=state['status'],
            run_manifest=bound(RUN), sealed_completion=state.get('sealed_completion'), checked_frames=len(rows), paired_samples=len(pairs), half_screen_passed=state.get('half_screen_passed'),
            prefix_samples=len(prefix), prefix_receipt=bound(PREFIX), error=state.get('error'),
            closed_equilibrium_diagnostics=state.get('closed_equilibrium_diagnostics'), physical_accepted=False,
            peak_half_accepted=False, full_cycle_accepted=False, automatic_formal_run_admitted=False))
        notify(state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    for name in ['selftest', 'prepare', 'run']:
        action.add_argument('--' + name, action='store_true')
    args = parser.parse_args()
    if args.selftest:
        print(json.dumps(selftest(), indent=2))
    elif args.prepare:
        prepare()
    elif args.run:
        run()
    else:
        parser.print_help()
