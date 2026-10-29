"""Fresh GPU builds with no-space intermediates; adopt sealed r1 CPU builds, never run programs."""
import argparse
import ast
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import cryer_darcy_switch_build_r1 as old
from cryer_grad_peak_r1 import identity, CODEX

TAG = 'cryer_darcy_switch_build_r2'
ROOT, TEMP, LOGS = old.TESTS / 'outputs' / TAG, old.TEMP.parent / TAG, old.LOGS
NOTE = old.TESTS / 'notes' / (TAG + '.json')
PREP, START, CHECK = [LOGS / (TAG + s) for s in ['.inputs.json', '.started.json', '.check.json']]
GPU = old.CONFIGS[2:]
read, bound, verify, seal, utc = old.read, old.bound, old.verify, old.seal, old.utc


def command(config, index):
    argv = old.command(config, index)
    replacements = {'/p:OutDir=': (ROOT / config / 'out').as_posix() + '/',
                    '/p:IntDir=': (TEMP / config / 'int').as_posix() + '/',
                    '/bl:': str(LOGS / (TAG + '_' + config + '.binlog'))}
    return [next((prefix + value for prefix, value in replacements.items() if arg.startswith(prefix)), arg) for arg in argv]


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    assert ' ' not in str(TEMP) and [c[0] for c in GPU] == ['Debug', 'Release']
    for config, index, name in GPU:
        before, after = old.command(config, index), command(config, index)
        changes = [(a, b) for a, b in zip(before, after) if a != b]
        assert len(changes) == 3 and all(a.startswith(('/p:OutDir=', '/p:IntDir=', '/bl:')) for a, _ in changes)
        assert '/t:Build' in after and str(old.SOLUTIONS[1]) in after
        assert '/p:IntDir=' + (TEMP / config / 'int').as_posix() + '/' in after
        assert (ROOT / config / 'out' / name).is_relative_to(ROOT)
    print('SELFTEST PASSED; no prepare/build/program/queue')


def prepare():
    selftest()
    assert not any(p.exists() for p in [PREP, START, CHECK, ROOT, TEMP]) and not list(LOGS.glob(TAG + '*')), 'Fresh label only'
    prior, failed = read(old.PREP), read(old.CHECK)
    assert prior['status'] == 'prepared_not_built' and not failed['passed'] and failed['status'] == 'build_rejected_or_interrupted'
    assert failed['prepared'] == bound(old.PREP) and len(failed['stages']) == 3
    records = prior['inputs'] + [bound(p) for p in [old.PREP, old.START, old.CHECK, old.__file__, Path(__file__), NOTE]]
    adopted = []
    for config, _, _ in old.CONFIGS[:3]:
        receipt = LOGS / (old.TAG + '_' + config + '.build.json')
        item = read(receipt)
        assert item['configuration'] == config and item['owned_exited'] and item['protected_inputs_unchanged']
        assert bound(receipt) in failed['stages']
        records += [bound(receipt), item['log']] + item['artifacts']
        records.append(bound(LOGS / (old.TAG + '_' + config + '.process.json')))
        if config.endswith('CPU'):
            assert item['status'] == 'built_not_run' and item['exit_code'] == 0 and len(item['runtime']) == 4
            records += [item['program']] + [x[k] for x in item['runtime'] for k in ['source', 'target']]
            adopted.append(bound(receipt))
        else:
            assert item['status'] == 'build_rejected' and item['exit_code'] != 0 and item['program'] is None
            text = Path(item['log']['path']).read_bytes().decode('utf8', errors='replace')
            assert 'A single input file is required' in text and '/Fd' in text and 'Hydromechanic coupling' in text
    records += [bound(p) for p in old.SOURCES + old.TOOLS + [old.BASE, old.REVIEW, old.VISUAL, CODEX]]
    verify(records)  # Prior inputs bind current seven sources and archived snapshots, not pre-edit original source paths.
    seal(PREP, dict(status='prepared_not_built', utc=utc(), thread=identity(), inputs=records,
        adopted_cpu_builds=adopted, prior_failure=bound(old.CHECK),
        commands=[dict(configuration=c, argv=command(c, i), expected_program=str(ROOT / c / 'out' / n)) for c, i, n in GPU],
        child_environment=dict(TEMP=str(TEMP), TMP=str(TEMP), CUDA_PATH_V11_7=str(old.CUDA)),
        programs_executed=False, physical_acceptance=False))
    print(PREP)


def notify(prepared, status):
    assert identity() == prepared['thread']
    message = (f'User-authorized same-thread {TAG}: {status}. Read {CHECK}. '
        'Build only: adopted sealed r1 CPU Debug/Release; fresh GPU Debug/Release use authoritative solution with no-space IntDir. '
        'No program/help, solver, regression, physical or formal acceptance. Verify source/base/canonical/runtime and tool exit hashes. '
        'r1 remains retired; do not retry/rearm it or this worker. On pass continue reviewed OFF-vs-original and ON-vs-isolated '
        'CPU/GPU native regressions before installation/server packaging. On failure preserve evidence and diagnose. '
        'Report Chinese proactively; no duplicate solvers, relaxed gates or connectivity self-tests.')
    assert len(message) < 2000
    seal(LOGS / (TAG + '.queue_attempt.json'), dict(utc=utc(), thread=prepared['thread'], message=message))
    try:
        result = subprocess.run([str(CODEX), 'queue', '--thread', prepared['thread'], '--message', message],
            capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        answer = dict(status='queued' if result.returncode == 0 else 'failed_no_retry', exit_code=result.returncode,
                      reply=(result.stdout + result.stderr).decode(errors='replace'))
    except Exception as error:
        answer = dict(status='exception_no_retry', error=repr(error))
    seal(LOGS / (TAG + '.notification.json'), answer)


def build():
    prepared = read(PREP)
    assert identity() == prepared['thread'] and not any(p.exists() for p in [START, CHECK, ROOT, TEMP])
    assert not [p for p in LOGS.glob(TAG + '*') if p != PREP], 'Retained/orphan evidence; never restart'
    verify(prepared['inputs'])
    ROOT.mkdir(); TEMP.mkdir()
    seal(START, dict(utc=utc(), worker_pid=os.getpid(), prepared=bound(PREP), no_program_execution=True))
    env = os.environ.copy(); env.update(prepared['child_environment'])
    stages, error = [], None
    try:
        for config, index, name in GPU:
            verify(prepared['inputs'])
            folder, logfile = ROOT / config, LOGS / (TAG + '_' + config + '.log')
            (folder / 'out').mkdir(parents=True); (TEMP / config / 'int').mkdir(parents=True)
            argv = command(config, index)
            assert argv == next(x['argv'] for x in prepared['commands'] if x['configuration'] == config)
            clock, started = time.perf_counter(), utc()
            with logfile.open('xb') as stream:
                child = subprocess.Popen(argv, cwd=old.VS, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                seal(LOGS / (TAG + '_' + config + '.process.json'), dict(utc=started, parent=os.getpid(), pid=child.pid, argv=argv))
                exit_code = child.wait()
            elapsed = time.perf_counter() - clock
            protection_error = runtime_error = None
            try: verify(prepared['inputs'])
            except Exception as failure: protection_error = repr(failure)
            program, runtime = folder / 'out' / name, []
            try:
                if exit_code == 0 and protection_error is None and program.is_file():
                    for source in old.RUNTIME:
                        target = folder / 'out' / source.name
                        assert not target.exists(), 'Never overwrite runtime/build output'
                        shutil.copy2(source, target)
                        assert bound(source)['sha256'] == bound(target)['sha256']
                        runtime.append(dict(source=bound(source), target=bound(target)))
            except Exception as failure: runtime_error = repr(failure)
            try: verify(prepared['inputs'])
            except Exception as failure: protection_error = repr(failure)
            raw = logfile.read_bytes()
            text = raw.decode('utf16' if raw.startswith(b'\xff\xfe') else 'utf8', errors='replace')
            warnings = [line for line in text.splitlines() if re.search(r'warning|警告', line, re.I)]
            passed = exit_code == 0 and protection_error is None and runtime_error is None and program.is_file() and len(runtime) == 4
            receipt = LOGS / (TAG + '_' + config + '.build.json')
            seal(receipt, dict(configuration=config, status='built_not_run' if passed else 'build_rejected', utc=utc(), started_utc=started,
                elapsed_seconds=elapsed, exit_code=exit_code, owned_exited=True, argv=argv,
                protected_inputs_unchanged=protection_error is None, protection_error=protection_error, runtime_error=runtime_error,
                program=bound(program) if program.is_file() else None, runtime=runtime, log=bound(logfile),
                artifacts=[bound(p) for p in [LOGS / (TAG + '_' + config + '.binlog')] if p.is_file()], warning_line_count=len(warnings),
                warning_excerpt=warnings[:30], programs_executed=False))
            stages.append(bound(receipt))
            assert passed, ('Build failed; preserve label and stop before later configuration', config, exit_code)
    except Exception as failure: error = repr(failure)
    passed = error is None and len(stages) == 2
    status = 'four_builds_passed_pending_implementation_regression' if passed else 'build_rejected_or_interrupted'
    seal(CHECK, dict(status=status, utc=utc(), passed=passed, error=error, prepared=bound(PREP),
        adopted_cpu_stages=prepared['adopted_cpu_builds'], fresh_gpu_stages=stages,
        stages=prepared['adopted_cpu_builds'] + stages, programs_executed=False, solver_executed=False,
        implementation_regression_passed=False, physical_acceptance=False, formal_admitted=False))
    notify(prepared, status)
    print(CHECK)
    return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    for flag in ['selftest', 'prepare', 'build']: group.add_argument('--' + flag, action='store_true')
    args = parser.parse_args()
    if args.selftest: selftest()
    elif args.prepare: prepare()
    elif args.build: raise SystemExit(build())
    else: parser.print_help()

