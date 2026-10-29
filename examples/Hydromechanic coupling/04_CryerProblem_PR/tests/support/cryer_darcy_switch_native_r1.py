"""Draft implementation regressions only; default help, no automatic physical/formal admission."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import time
import traceback
import numpy as np
import pandas as pd
from cryer_start_r1 import CASE, TESTS, REPO, READER, READER_SOURCE, native, bound, utc, write_json
from cryer_grad_peak_r1 import identity, CODEX
from cryer_preload_probe_r1 import equilibrium
from cryer_preload_peak_r1 import inspect, prefix_compare
from cryer_symc_gpu_short_r1 import read, seal, verify, inventory, memcheck_clean

TAG = 'cryer_darcy_switch_native_r1'
LOGS, CONFIGS, OUTPUTS = [TESTS / p for p in ['logs', 'configs', 'outputs']]
PREP, RUN, STATE, CHECK = [LOGS / (TAG + s) for s in ['.inputs.json', '.run.json', '.status.json', '.check.json']]
BASE = LOGS / 'cryer_darcy_switch_r1.base.json'
BUILD, BUILD_REVIEW = [LOGS / n for n in ['cryer_darcy_switch_build_r2.check.json', 'cryer_darcy_switch_build_review_r1.check.json']]
NOTE = TESTS / 'notes' / (TAG + '.json')
DT, INTERVAL, END = 2. ** -21, 2. ** -13, .00830078125
SANITIZER = Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7\compute-sanitizer\compute-sanitizer.exe')
SOURCES = [REPO / 'src/source' / n for n in ['JSph.h', 'JSph.cpp', 'JSphCpu.cpp', 'JSphGpu_ker.h', 'JSphGpu_ker.cu', 'JSphGpu.cpp']]
SOURCES += [REPO / 'doc/xml_format/_FmtXML_ElastoplasticSoil.xml']
JOBS = [('cpu_dbg', 'CPU', 'DebugCPU', True, 2, None), ('gpu_dbg', 'GPU', 'Debug', True, 2, None),
        ('cpu_off', 'CPU', 'ReleaseCPU', False, 69, 'cryer_symc_short_r1_off_c'),
        ('cpu_on', 'CPU', 'ReleaseCPU', True, 69, 'cryer_symc_short_r1_on_c'),
        ('gpu_off', 'GPU', 'Release', False, 69, 'cryer_preload_peak_r1'),
        ('gpu_on', 'GPU', 'Release', True, 69, 'cryer_symc_gpu_short_r1_c')]
PROGRAMS = {c: OUTPUTS / ('cryer_darcy_switch_build_r1' if c.endswith('CPU') else 'cryer_darcy_switch_build_r2') / c / 'out' / n
            for c, n in [('DebugCPU', 'DualSPHysics5.2CPU_win64_debug.exe'), ('ReleaseCPU', 'DualSPHysics5.2CPU_win64.exe'),
                         ('Debug', 'DualSPHysics5.2_win64_debug.exe'), ('Release', 'DualSPHysics5.2_GEO_win64.exe')]}


def unique(records):
    result = {}
    for row in records:
        key = str(Path(row['path']).resolve()).casefold()
        assert key not in result or result[key]['sha256'].lower() == row['sha256'].lower(), ('Conflicting input', key)
        result[key] = row
    return list(result.values())


def support_files():
    pending, seen = [Path(__file__)], set()
    roots = [TESTS / 'support', CASE.parent / '05_LianFlexibleStrip2D_PR/tests/scripts']
    while pending:
        path = pending.pop().resolve()
        if path in seen: continue
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
            for name in names:
                for root in roots:
                    other = root / (name.split('.')[0] + '.py')
                    if other.is_file(): pending.append(other); break
    return sorted(seen)


def templates(backend):
    tag = 'cryer_symc_short_r1_off_c' if backend == 'CPU' else 'cryer_symc_gpu_short_r1_c'
    return tag, CONFIGS / (tag + '_Def.xml'), CONFIGS / ('x' + tag + '_win64_' + backend + '.bat')


def expected_files(job):
    suffix, backend, config, on, frames, _ = job
    name = TAG + '_' + suffix; old, xmlpath, batpath = templates(backend)
    xml = xmlpath.read_text(encoding='utf8')
    description = backend + ' explicit Darcy switch implementation regression; not physical validation'
    xml, count = re.subn(r'(<parameter key="TimeMax" value=")[^"]+(" comment=")[^"]+(" units_comment="seconds" />)',
                        lambda m: m[1] + str(INTERVAL if frames == 2 else END) + m[2] + description + m[3], xml)
    assert count == 1
    if frames == 2: xml = xml.replace('69 frames', '2 frames')
    if on:
        xml, count = re.subn(r'(?m)^([ ]*)(<HydroMechDrainageFixedGrid[^\n]*\n)',
            lambda m: m[0] + m[1] + '<PoreDarcySymmetricCorr value="1" comment="Explicit symmetric soil-soil Darcy contraction; default is OFF" />\n', xml)
        assert count == 1
    bat = batpath.read_text(encoding='utf8').replace(old, name)
    oldprogram = '"%dirbin%/DualSPHysics5.2CPU_win64.exe"' if backend == 'CPU' else '"tests/outputs/cryer_symc_gpu_build_r3/Release/cryer_symc_gpu_r3_Release.exe"'
    assert bat.count(oldprogram) == 1
    bat = bat.replace(oldprogram, '"' + PROGRAMS[config].relative_to(CASE).as_posix() + '"')
    if suffix == 'gpu_dbg':
        bat = bat.replace('%dualsphysicsgpu% -gpu', '"' + str(SANITIZER) + '" --tool memcheck --error-exitcode 86 --leak-check full --log-file "%dirout%\\memcheck.log" %dualsphysicsgpu% -gpu')
    return xml, bat


def selftest():
    columns = read(LOGS / 'cryer_preload_peak_r1.prefix.json')['samples'][0]['compared_columns']
    assert len(columns) == 35 and 'dterror_s' in columns
    a = pd.DataFrame(np.zeros((2, 35), dtype='<f8'), columns=columns)
    assert prefix_compare(a, a.copy(), 0)['all_35_columns0ulp']
    for col in columns:
        b = a.copy(); b.loc[0, col] = 1.
        assert not prefix_compare(a, b, 0)['all_35_columns0ulp'], col
        b = a.copy(); b.loc[0, col] = -0.
        assert not prefix_compare(a, b, 0)['all_35_columns0ulp'], ('Signed-zero check', col)
    for job in JOBS:
        name = TAG + '_' + job[0]; xml, bat = expected_files(job)
        assert (CONFIGS / (name + '_Def.xml')).read_text(encoding='utf8').rstrip() == xml.rstrip()
        assert (CONFIGS / ('x' + name + '_win64_' + job[1] + '.bat')).read_text(encoding='utf8').rstrip() == bat.rstrip()
        assert ('PoreDarcySymmetricCorr' in xml) == job[3] and 'if exist "%dirout%" goto fail' in bat
    return dict(passed=True, programs_started=False, files_written=False, exact_columns=35, jobs=6)


def fresh(prepared=False):
    allowed = [PREP] if prepared else []
    assert not [p for p in LOGS.glob(TAG + '*') if p not in allowed], 'Retained/orphan stage evidence; never restart'
    assert not any((OUTPUTS / (TAG + '_' + j[0])).exists() for j in JOBS), 'Output exists; never overwrite'


def prepare():
    selftest(); fresh()
    final, audit, base = read(BUILD), read(BUILD_REVIEW), read(BASE)
    assert final['passed'] and len(final['stages']) == 4 and audit['build_acceptance'] is True
    assert bound(BUILD_REVIEW)['sha256'] == 'fb22f576826072a01c42406f84dd8bde4190163cb570013a2e0f22ea41408f04'
    proof = [bound(p) for p in [BUILD, BUILD_REVIEW, BASE]] + [final['prepared']]
    proof += read(final['prepared']['path'])['inputs']
    proof += [row['snapshot'] for row in base['files']] + base['canonical_programs']
    archive = {str(Path(row['original']['path']).resolve()).casefold(): row['snapshot'] for row in base['files']}
    builds = {}
    for record in final['stages']:
        receipt = read(record['path']); c = receipt['configuration']
        assert receipt['status'] == 'built_not_run' and receipt['exit_code'] == 0 and receipt['owned_exited'] and receipt['protected_inputs_unchanged']
        assert receipt['program'] == bound(PROGRAMS[c]) and len(receipt['runtime']) == 4
        proof += [record, receipt['program'], receipt['log']] + receipt['artifacts']
        proof += [x[k] for x in receipt['runtime'] for k in ['source', 'target']]
        builds[c] = dict(build=record, program=receipt['program'], runtime=[x['target'] for x in receipt['runtime']])
    for tag in ['cryer_symc_short_r1', 'cryer_symc_gpu_short_r1', 'cryer_preload_peak_r1']:
        path = LOGS / (tag + '.check.json'); check = read(path); assert check['passed']
        proof += [bound(path), check.get('run', check.get('run_manifest'))]
    prefix = LOGS / 'cryer_preload_peak_r1.prefix.json'; old = read(prefix)
    assert old['checked_samples'] == 69 and old['all35_columns0ulp_passed'] and old['excluded_columns'] == []
    proof.append(bound(prefix)); jobs = []
    for spec in JOBS:
        suffix, backend, config, on, frames, control = spec; name = TAG + '_' + suffix
        cfg, bat = CONFIGS / (name + '_Def.xml'), CONFIGS / ('x' + name + '_win64_' + backend + '.bat')
        job = dict(name=name, suffix=suffix, backend=backend, configuration=config, on=on, frames=frames,
                   config=bound(cfg), bat=bound(bat), end_s=INTERVAL if frames == 2 else END, **builds[config])
        if control:
            path = LOGS / (control + '.completion.json'); done = read(path)
            assert done['solver_finished'] and done['owned_exited'] and done['exit_code'] == 0
            parts = sorted([x for x in done['outputs'] if re.fullmatch(r'Part_\d{4}\.bi4', Path(x['path']).name)
                            and int(Path(x['path']).stem[5:]) < 69], key=lambda x: x['path'])
            assert len(parts) == 69
            program = archive.get(str(Path(done['program']['path']).resolve()).casefold(), done['program'])
            assert program['sha256'] == done['program']['sha256']
            job.update(control=str(OUTPUTS / control), control_parts=parts, control_completion=bound(path))
            proof += [bound(path), program] + parts + [bound(OUTPUTS / control / 'Run.out')]
        jobs.append(job); proof += [bound(cfg), bound(bat)]
    imports = support_files()
    critical = [bound(p) for p in SOURCES + imports + [READER, READER_SOURCE, CODEX, SANITIZER, REPO / 'bin/windows/GenCase_win64.exe', NOTE]]
    proof = unique(proof + critical); verify(proof)
    seal(PREP, dict(utc=utc(), thread=identity(), inputs=proof, critical=critical, jobs=jobs,
                   archived_original_sources_not_recursively_reverified=True, programs_started=False,
                   implementation_regression_passed=False, physical_acceptance=False, formal_admitted=False))


def publish(state):
    for path, value in [(RUN, state), (STATE, {k: state.get(k) for k in ['status', 'current_job', 'worker_pid', 'checked_frames', 'actual_last_saved_time_s']})]:
        temporary = path.with_suffix('.tmp'); write_json(temporary, value); os.replace(temporary, path)


def stop_owned(child, owned, name):
    if child is not None and child.poll() is None:
        owned.add(child.pid)
    for pid in owned:
        cmd = f"Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' | Select-Object CommandLine | ConvertTo-Json -Compress"
        raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
        if raw and name in json.loads(raw)['CommandLine']:
            subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if child is not None and child.poll() is None: child.wait(timeout=30)


def one_job(job, prepared, state):
    name, folder = job['name'], OUTPUTS / job['name']; log = LOGS / (name + '.log')
    complete, receipt = LOGS / (name + '.completion.json'), LOGS / (name + '.receipt.json')
    result = dict(name=name, passed=False, rows=[], prefix_samples=[], program=job['program'])
    child, owned = None, set()
    try:
        assert not inventory(), 'Existing solver; no duplicate admitted'
        verify(prepared['critical'] + [job['program'], job['build'], job['config'], job['bat']] + job['runtime'])
        assert not any(p.exists() for p in [folder, log, complete, receipt])
        started = time.perf_counter()
        with log.open('xb') as stream:
            child = subprocess.Popen([os.environ['ComSpec'], '/d', '/c', job['bat']['path']], cwd=CASE,
                                     stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
            result['owned_wrapper_pid'] = child.pid; report, observed = started, started - 30
            state.update(owned_wrapper_pid=child.pid, owned_solver_pids=[]); publish(state)
            while child.poll() is None:
                if time.perf_counter() - observed >= 30:
                    for row in inventory():
                        if name in (row.get('CommandLine') or ''): owned.add(row['ProcessId'])
                    state['owned_solver_pids'] = sorted(owned); publish(state)
                    observed = time.perf_counter()
                if time.perf_counter() - report >= 30:
                    print('RUNNING', name, 'wall_s', round(time.perf_counter() - started), flush=True); report = time.perf_counter()
                time.sleep(1)
        survivors = inventory(); text = (folder / 'Run.out').read_text(errors='replace') if (folder / 'Run.out').exists() else ''
        finished = child.returncode == 0 and 'Finished execution (code=0)' in text and not survivors
        result.update(exit_code=child.returncode, owned_exited=not survivors, survivors=survivors, wall_seconds=time.perf_counter() - started)
        seal(complete, dict(solver_finished=finished, owned_exited=not survivors, observed_surviving_solvers=survivors,
             exit_code=child.returncode, program=job['program'], config=job['config'], bat=job['bat'],
             outputs=[bound(p) for p in sorted(folder.rglob('*')) if p.is_file()] + [bound(log)]))
        result['sealed_completion'] = bound(complete)
        assert finished, ('Physical program exit failure', name, child.returncode, survivors)
        assert int(re.search(r'Steps of simulation\.*:\s*(\d+)', text)[1]) == (job['frames'] - 1) * 256
        assert len(list((folder / 'data').glob('Part_*.bi4'))) == job['frames']
        mode = 'SymmetricSoilPair' if job['on'] else 'Receiver'
        assert 'PoreDarcySymmetricCorr="' + mode + '"' in text
        assert 'HydroMechDrainageFixedGrid=True' in text and 'SoilStressRateGradCorr="KernelGradient"' in text
        assert 'BuiFukagawa2013' in text
        assert 'RunMode="Stable - Pos-Double - OpenMP(Threads:8)"' in text if job['backend'] == 'CPU' else 'Single-GPU' in text
        result['observed_loop_seconds'] = float(re.search(r'Simulation Runtime\.*:\s*([\d.]+)', text)[1])
        if job['suffix'] == 'gpu_dbg':
            result['memcheck_zero_errors'] = memcheck_clean((folder / 'memcheck.log').read_text(errors='replace'))
            assert result['memcheck_zero_errors'], 'Debug memcheck/leak failure'
        initial = native(folder, 0)
        assert np.array_equal(initial.id.to_numpy(), np.arange(8, 37181)), 'Unexpected native soil ID set'
        for part in range(job['frames']):
            data = initial if part == 0 else native(folder, part)
            row = inspect(data, initial, part); assert row['true_surface_count'] == 5153 and row['changed_fstype_count'] == 0
            result['rows'].append(row)
            if job.get('control'):
                verify([job['control_parts'][part]])
                record = prefix_compare(data, native(Path(job['control']), part), part)
                result['prefix_samples'].append(record)
                assert record['all_35_columns0ulp'], ('Implementation changed native field', record)
            state.update(checked_frames=part + 1, actual_last_saved_time_s=row['time_s']); publish(state)
        if job['frames'] == 69:
            result['equilibrium'] = equilibrium(result['rows']); assert result['equilibrium']['equilibrium_diagnostic_passed']
            assert len(result['prefix_samples']) == 69
            if job['on']:
                off = OUTPUTS / (TAG + '_' + job['backend'].lower() + '_off')
                changes = [float(np.abs(native(folder, p).pressure.to_numpy() - native(off, p).pressure.to_numpy()).max()) for p in range(65, 69)]
                result['post_drain_on_off_pressure_absmax_pa'] = changes
                assert max(changes) > 0., 'ON/OFF branch not demonstrated after drainage'
        verify(prepared['critical'] + [job['program']] + job['runtime'])
        verify([x for x in read(complete)['outputs'] if re.fullmatch(r'Part_\d{4}\.bi4', Path(x['path']).name)])
        result['passed'] = True
    except BaseException as error:
        result.update(error=repr(error), traceback=traceback.format_exc()); stop_owned(child, owned, name)
        result['observed_after_failure'] = inventory()
    seal(receipt, result)
    return result, bound(receipt)


def notify(state):
    assert identity() == state['thread']
    message = (f'User-authorized same-thread {TAG}: {state["status"]}. Read {STATE}, {CHECK} and immutable job completion/receipt JSON. '
               'Six fresh jobs only: CPU/GPU Debug ON2frame smoke (GPU memcheck), then four Release69frames CPU/GPU defaultOFF/ON. '
               'Verify exits/build/runtime/source/archive/control hashes and all35 native columns0ULP incl dterror; no exclusions or interpolation. '
               'Keep original safety, closedPart61-64 limits and actual source-clock drainage. New branch must change postdrain pressure; ON/OFF is not a half comparison. '
               'Completed-solver check failure needs offline diagnosis, not rerun. No automatic physical/full/server/formal acceptance. '
               'Report Chinese proactively and decide next delivery stage only after review. Never restart/rearm this worker, old workers or connectivity tests.')
    seal(LOGS / (TAG + '.queue_attempt.json'), dict(utc=utc(), thread=state['thread'], message=message))
    try:
        p = subprocess.run([str(CODEX), 'queue', '--thread', state['thread'], '--message', message], capture_output=True,
                           timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        answer = dict(status='queued' if p.returncode == 0 else 'failed_no_retry', exit_code=p.returncode, reply=(p.stdout + p.stderr).decode(errors='replace'))
    except Exception as error: answer = dict(status='exception_no_retry', error=repr(error))
    seal(LOGS / (TAG + '.notification.json'), answer)


def run():
    prepared = read(PREP); fresh(prepared=True); assert identity() == prepared['thread']
    verify(prepared['inputs']); assert not inventory()
    state = dict(status='running', utc=utc(), worker_pid=os.getpid(), thread=prepared['thread'], prepared=bound(PREP), jobs=[])
    publish(state)
    try:
        for job in prepared['jobs']:
            state.update(current_job=job['name'], checked_frames=0); publish(state)
            result, record = one_job(job, prepared, state); state['jobs'].append(record)
            assert result['passed'], result.get('error', 'Job rejected')
        state['status'] = 'implementation_native_regressions_passed_pending_review'
    except BaseException as error: state.update(status='implementation_regression_rejected_or_interrupted', error=repr(error))
    state['finished_utc'] = utc(); publish(state)
    seal(CHECK, dict(passed=state['status'] == 'implementation_native_regressions_passed_pending_review', status=state['status'],
         run=bound(RUN), jobs=state['jobs'], error=state.get('error'), physical_acceptance=False, full_cycle_acceptance=False, formal_admitted=False))
    notify(state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--selftest', action='store_true'); actions.add_argument('--prepare', action='store_true'); actions.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if args.selftest: print(json.dumps(selftest()))
    elif args.prepare: prepare()
    elif args.run: run()
    else: parser.print_help()
