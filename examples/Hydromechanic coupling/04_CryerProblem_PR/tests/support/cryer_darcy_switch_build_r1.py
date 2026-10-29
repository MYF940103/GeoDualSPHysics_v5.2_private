"""Fresh authoritative VS builds only; default help, no program execution or regression."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

TAG = 'cryer_darcy_switch_build_r1'
TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]
VS, BIN, LOGS = REPO / 'src/VS', REPO / 'bin/windows', TESTS / 'logs'
ROOT = TESTS / 'outputs' / TAG
TEMP = Path(r'C:\Users\syosh\AppData\Local\Temp') / TAG
NOTE, BASE = TESTS / 'notes/cryer_darcy_switch_r1.json', LOGS / 'cryer_darcy_switch_r1.base.json'
PREP, START, CHECK = [LOGS / (TAG + suffix) for suffix in ['.inputs.json', '.started.json', '.check.json']]
REVIEW, VISUAL = [LOGS / ('cryer_symc_gpu_peak_half_review_r1' + suffix) for suffix in ['.check.json', '.visual.json']]
MSBUILD = Path(r'D:\Program Files\VS2022\MSBuild\Current\Bin\amd64\MSBuild.exe')
VC = Path(r'D:\Program Files\VS2022\VC\Tools\MSVC\14.36.32532')
CUDA = Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7')
TOOLS = [MSBUILD, VC / 'bin/Hostx64/x64/cl.exe', VC / 'bin/Hostx64/x64/link.exe', CUDA / 'bin/nvcc.exe']
SOURCES = [REPO / 'src/source' / n for n in ['JSph.h', 'JSph.cpp', 'JSphCpu.cpp', 'JSphGpu_ker.h', 'JSphGpu_ker.cu', 'JSphGpu.cpp']]
SOURCES += [REPO / 'doc/xml_format/_FmtXML_ElastoplasticSoil.xml']
SOLUTIONS = [VS / 'DualSPHysics5ReCpu_vs2022.sln', VS / 'DualSPHysics5Re.sln']
PROJECTS = [VS / 'DualSPHysics5ReCpu.vcxproj', VS / 'DualSPHysics5Re.vcxproj']
RUNTIME = [BIN / n for n in ['ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll', 'DsphConfig.xml']]
CONFIGS = [('DebugCPU', 0, 'DualSPHysics5.2CPU_win64_debug.exe'), ('ReleaseCPU', 0, 'DualSPHysics5.2CPU_win64.exe'),
           ('Debug', 1, 'DualSPHysics5.2_win64_debug.exe'), ('Release', 1, 'DualSPHysics5.2_GEO_win64.exe')]


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bound(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def verify(records):
    for item in records:
        actual = bound(item['path'])
        assert actual['sha256'].lower() == item['sha256'].lower(), ('Changed bound input', item['path'])
        assert 'bytes' not in item or actual['bytes'] == item['bytes'], ('Changed input size', item['path'])


def seal(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def command(config, index):
    folder = ROOT / config
    return [str(MSBUILD), str(SOLUTIONS[index]), '/m:1', '/nr:false', '/t:Build', '/v:minimal',
            '/p:Configuration=' + config, '/p:Platform=x64', '/p:PlatformToolset=v143',
            '/p:VCToolsVersion=14.36.32532', '/p:BuildProjectReferences=false', '/p:PostBuildEventUseInBuild=false',
            '/p:OutDir=' + (folder / 'out').as_posix() + '/', '/p:IntDir=' + (folder / 'int').as_posix() + '/',
            '/bl:' + str(LOGS / (TAG + '_' + config + '.binlog'))]


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    assert len(bound(__file__)['sha256']) == 64
    assert len(CONFIGS) == 4 and [c[0] for c in CONFIGS] == ['DebugCPU', 'ReleaseCPU', 'Debug', 'Release']
    for solution, project in zip(SOLUTIONS, PROJECTS):
        text = solution.read_text(encoding='utf-8-sig')
        assert len(re.findall(r'^Project\(', text, re.M)) == 1 and project.name in text
        assert not ET.parse(project).getroot().findall('.//{*}ProjectReference')
    for config, index, name in CONFIGS:
        argv = command(config, index)
        assert all(str(BIN).casefold() not in arg.casefold() for arg in argv)
        assert (ROOT / config / 'out' / name).is_relative_to(ROOT) and '/t:Build' in argv
    assert ' ' not in str(TEMP) and len(SOURCES) == 7
    print(json.dumps(dict(selftest_passed=True, files_written=False, processes_started=False)))


def prepare():
    selftest()
    reserved = [PREP, START, CHECK, ROOT, TEMP] + [LOGS / (TAG + s) for s in ['.queue_attempt.json', '.notification.json']]
    assert not any(p.exists() for p in reserved) and not list(LOGS.glob(TAG + '*')), 'Fresh stage only; never overwrite/restart'
    review, visual, base = read(REVIEW), read(VISUAL), read(BASE)
    assert review['analysis_checks_passed'] and visual['analysis_checks_passed'] and visual['visual_review_passed']
    assert visual['review_check'] == bound(REVIEW)
    snapshots = [row['snapshot'] for row in base['files']]
    assert {str(p.resolve()).casefold() for p in SOURCES} <= {str(Path(row['original']['path']).resolve()).casefold() for row in base['files']}
    assert all(row['snapshot']['sha256'].lower() == row['original']['sha256'].lower() for row in base['files'])
    assert base['canonical_programs'], 'Pre-edit canonical programs must be explicitly bound'
    verify(snapshots + base['canonical_programs'])  # Original source paths intentionally change after the archived base.
    from cryer_grad_peak_r1 import identity, CODEX
    paths = SOURCES + SOLUTIONS + PROJECTS + TOOLS + RUNTIME + [NOTE, BASE, REVIEW, VISUAL, Path(__file__), CODEX,
             TESTS / 'support/cryer_grad_peak_r1.py']
    records = [bound(p) for p in paths] + snapshots + base['canonical_programs']
    seal(PREP, dict(status='prepared_not_built', utc=utc(), thread=identity(), inputs=records,
         commands=[dict(configuration=c, argv=command(c, i), expected_program=str(ROOT / c / 'out' / n)) for c, i, n in CONFIGS],
         tools=dict(vctools_version='14.36.32532', platform_toolset='v143', cuda='11.7', gpu_codegen='compute_86,sm_86',
                    sdk_from_projects=['8.1', '10.0']),
         child_environment=dict(TEMP=str(TEMP), TMP=str(TEMP), CUDA_PATH_V11_7=str(CUDA)),
         historical_original_paths_reverified=False, programs_executed=False, physical_acceptance=False))
    print(str(PREP))


def notify(prepared, status):
    from cryer_grad_peak_r1 import identity, CODEX
    assert identity() == prepared['thread']
    message = (f'User-authorized same-thread {TAG}: {status}. Read {CHECK} and its immutable per-configuration build receipts. '
               'This stage builds only: no program/help, solver, native regression or physical/formal acceptance. '
               'Inspect tool exits, source/base snapshot/canonical-program hashes and copied runtime. '
               'On failure preserve evidence and diagnose; never rerun/rearm this worker. On build pass continue reviewed '
               'OFF-vs-original and ON-vs-isolated CPU/GPU native implementation regressions before any server package/formal run. '
               'Do not alter physical gates, launch duplicate solvers or send connectivity tests. Report Chinese proactively.')
    seal(LOGS / (TAG + '.queue_attempt.json'), dict(utc=utc(), thread=prepared['thread'], message=message))
    try:
        proc = subprocess.run([str(CODEX), 'queue', '--thread', prepared['thread'], '--message', message],
                              capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        answer = dict(exit_code=proc.returncode, status='queued' if proc.returncode == 0 else 'failed_no_retry',
                      reply=(proc.stdout + proc.stderr).decode(errors='replace'))
    except Exception as error:
        answer = dict(status='exception_no_retry', error=repr(error))
    seal(LOGS / (TAG + '.notification.json'), answer)


def build():
    prepared = read(PREP)
    from cryer_grad_peak_r1 import identity
    assert identity() == prepared['thread'] and not any(p.exists() for p in [START, CHECK, ROOT, TEMP])
    assert not [p for p in LOGS.glob(TAG + '*') if p != PREP], 'Orphan/retained build evidence: never overwrite/restart'
    verify(prepared['inputs'])
    ROOT.mkdir(); TEMP.mkdir()
    seal(START, dict(utc=utc(), worker_pid=os.getpid(), prepared=bound(PREP), no_program_execution=True))
    env = os.environ.copy(); env.update(prepared['child_environment'])
    stages, error = [], None
    try:
        for config, index, name in CONFIGS:
            verify(prepared['inputs'])
            folder, logfile = ROOT / config, LOGS / (TAG + '_' + config + '.log')
            (folder / 'out').mkdir(parents=True); (folder / 'int').mkdir()
            argv = command(config, index)
            assert argv == next(row['argv'] for row in prepared['commands'] if row['configuration'] == config)
            started, clock = utc(), time.perf_counter()
            with logfile.open('xb') as stream:
                child = subprocess.Popen(argv, cwd=VS, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                seal(LOGS / (TAG + '_' + config + '.process.json'), dict(utc=started, parent=os.getpid(), pid=child.pid, argv=argv))
                exit_code = child.wait()
            elapsed, protection_error = time.perf_counter() - clock, None
            try:
                verify(prepared['inputs'])
            except Exception as failure:
                protection_error = repr(failure)
            program, runtime, runtime_error = folder / 'out' / name, [], None
            try:
                if exit_code == 0 and not protection_error and program.is_file():
                    for source in RUNTIME:
                        target = folder / 'out' / source.name
                        assert not target.exists(), 'Runtime copy must not overwrite build products'
                        shutil.copy2(source, target)
                        assert bound(source)['sha256'] == bound(target)['sha256']
                        runtime.append(dict(source=bound(source), target=bound(target)))
            except Exception as failure:
                runtime_error = repr(failure)
            try:
                verify(prepared['inputs'])
            except Exception as failure:
                protection_error = repr(failure)
            text = logfile.read_bytes().decode('utf-16' if logfile.read_bytes().startswith(b'\xff\xfe') else 'utf8', errors='replace')
            warnings = [line for line in text.splitlines() if re.search(r'warning|警告', line, re.I)]
            passed = exit_code == 0 and protection_error is None and runtime_error is None and program.is_file() and len(runtime) == 4
            result = dict(configuration=config, status='built_not_run' if passed else 'build_rejected', utc=utc(),
                          started_utc=started, elapsed_seconds=elapsed, exit_code=exit_code, owned_exited=True,
                          protected_inputs_unchanged=protection_error is None, protection_error=protection_error,
                          argv=argv, log=bound(logfile), program=bound(program) if program.is_file() else None,
                          runtime=runtime, runtime_error=runtime_error, warning_line_count=len(warnings), warning_excerpt=warnings[:30],
                          artifacts=[bound(p) for p in [LOGS / (TAG + '_' + config + '.binlog')] if p.is_file()], programs_executed=False)
            receipt = LOGS / (TAG + '_' + config + '.build.json'); seal(receipt, result); stages.append(bound(receipt))
            assert passed, ('Build failed; no retry/later configuration', config, exit_code, protection_error, runtime_error)
    except Exception as failure:
        error = repr(failure)
    status = 'four_builds_passed_pending_implementation_regression' if error is None and len(stages) == 4 else 'build_rejected_or_interrupted'
    seal(CHECK, dict(status=status, utc=utc(), passed=error is None and len(stages) == 4, error=error,
         prepared=bound(PREP), stages=stages, programs_executed=False, solver_executed=False,
         implementation_regression_passed=False, physical_acceptance=False, formal_admitted=False))
    notify(prepared, status)
    print(str(CHECK))
    return 0 if error is None else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--selftest', action='store_true', help='Read-only source/argv checks; no prepare/build/queue')
    actions.add_argument('--prepare', action='store_true', help='After root review/patch: freeze inputs only')
    actions.add_argument('--build', action='store_true', help='After separate authorization: four sequential builds; one terminal queue')
    args = parser.parse_args()
    if args.selftest: selftest()
    elif args.prepare: prepare()
    elif args.build: raise SystemExit(build())
    else: parser.print_help()
