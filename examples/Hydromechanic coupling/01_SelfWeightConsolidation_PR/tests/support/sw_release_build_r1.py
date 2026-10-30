"""Freeze current sources, then isolated authoritative builds; never run target programs."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]
TAG = 'sw_release_build_r1'
VS, SOURCE, BIN = REPO/'src/VS', REPO/'src/source', REPO/'bin/windows'
ROOT, LOGS = TESTS/'outputs'/TAG, TESTS/'logs'
TEMP = Path(r'C:\Users\syosh\AppData\Local\Temp')/TAG
NOTE = TESTS/'notes'/(TAG+'.json')
PREP, START, CHECK = [LOGS/(TAG+s) for s in ['.inputs.json', '.started.json', '.check.json']]
MSBUILD = Path(r'D:\Program Files\VS2022\MSBuild\Current\Bin\amd64\MSBuild.exe')
VC = Path(r'D:\Program Files\VS2022\VC\Tools\MSVC\14.36.32532')
CUDA = Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7')
TOOLS = [MSBUILD, VC/'bin/Hostx64/x64/cl.exe', VC/'bin/Hostx64/x64/link.exe', CUDA/'bin/nvcc.exe']
SOLUTIONS = [VS/'DualSPHysics5ReCpu_vs2022.sln', VS/'DualSPHysics5Re.sln']
PROJECTS = [VS/'DualSPHysics5ReCpu.vcxproj', VS/'DualSPHysics5Re.vcxproj']
RUNTIME = [BIN/n for n in ['ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll', 'DsphConfig.xml']]
CANONICAL = [BIN/n for n in ['DualSPHysics5.2CPU_win64_debug.exe', 'DualSPHysics5.2CPU_win64.exe',
                            'DualSPHysics5.2_win64_debug.exe', 'DualSPHysics5.2_GEO_win64.exe']]
HG = [SOURCE/n for n in ['JSphHourglassCpu.cpp', 'JSphHourglassCpu.h', 'JSphHourglassGpu.cpp',
                         'JSphHourglassGpu.h', 'JSphHourglassGpu_ker.cu', 'JSphHourglassGpu_ker.h']]
CONFIGS = [('DebugCPU', 0, CANONICAL[0].name), ('ReleaseCPU', 0, CANONICAL[1].name), ('Release', 1, CANONICAL[3].name)]


def utc(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def bound(path):
    path = Path(path).resolve()
    with path.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)
def verify(records):
    for record in records: assert bound(record['path']) == record, ('Changed frozen input', record['path'])
def seal(path, value):
    with Path(path).open('x', encoding='utf8') as stream: json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
def inventory():
    source = sorted(p for p in SOURCE.rglob('*') if p.is_file() and p.suffix.lower() in {'.c', '.cpp', '.cu', '.h', '.hpp', '.cuh', '.inl', '.inc'})
    projects = sorted(p for p in VS.rglob('*') if p.is_file() and p.suffix.lower() in {'.sln', '.vcxproj', '.props', '.targets'})
    return source + projects
def command(config, index):
    return [str(MSBUILD), str(SOLUTIONS[index]), '/m:1', '/nr:false', '/t:Build', '/v:minimal',
            '/p:Configuration='+config, '/p:Platform=x64', '/p:PlatformToolset=v143', '/p:VCToolsVersion=14.36.32532',
            '/p:BuildProjectReferences=false', '/p:PostBuildEventUseInBuild=false',
            '/p:OutDir='+(ROOT/config/'out').as_posix()+'/', '/p:IntDir='+(TEMP/config/'int').as_posix()+'/',
            '/bl:'+str(LOGS/(TAG+'_'+config+'.binlog'))]
def frozen(prepared):
    assert [str(p.resolve()) for p in inventory()] == prepared['compilation_inventory'], 'Compilation inventory changed'
    verify(prepared['inputs'])
    verify([row['snapshot'] for row in prepared['snapshots']])


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8'))
    assert ' ' not in str(TEMP) and set(HG) <= set(inventory())
    for solution, project in zip(SOLUTIONS, PROJECTS):
        assert project.name in solution.read_text(encoding='utf-8-sig')
        assert not ET.parse(project).getroot().findall('.//{*}ProjectReference')
    for config, index, name in CONFIGS:
        argv = command(config, index)
        assert '/m:1' in argv and '/p:BuildProjectReferences=false' in argv and '/p:PostBuildEventUseInBuild=false' in argv
        assert (ROOT/config/'out'/name).is_relative_to(ROOT) and str(SOLUTIONS[index]) in argv
        assert not any(str(BIN).casefold() in arg.casefold() for arg in argv)
    print('SELFTEST PASSED: no files written, no child processes, no prepare/build/program/queue')


def prepare():
    selftest()
    assert not ROOT.exists() and not TEMP.exists() and not list(LOGS.glob(TAG+'*')), 'Fresh tag only; no retry/overwrite'
    files = inventory()
    libraries = sorted((REPO/'src/lib/vs2022').glob('*.lib')) + [CUDA/'lib/x64/cudart_static.lib', CUDA/'lib/x64/cudadevrt.lib']
    userprops = Path(r'C:\Users\syosh\AppData\Local\Microsoft\MSBuild\v4.0\Microsoft.Cpp.x64.user.props')
    inputs = [bound(p) for p in files+TOOLS+RUNTIME+CANONICAL+libraries+[NOTE, Path(__file__)]+([userprops] if userprops.is_file() else [])]
    ROOT.mkdir(); snapshots = []
    for path in files:
        target = ROOT/path.relative_to(REPO/'src'); target.parent.mkdir(parents=True, exist_ok=True)
        captured = utc(); shutil.copy2(path, target)
        original, snapshot = bound(path), bound(target)
        assert original['sha256'] == snapshot['sha256'] and original['bytes'] == snapshot['bytes']
        snapshots.append(dict(original=original, snapshot=snapshot, captured_utc=captured))
    prepared = dict(status='prepared_not_built', utc=utc(), inputs=inputs, snapshots=snapshots,
        compilation_inventory=[str(p.resolve()) for p in files],
        hg_before_build_capture=[r for r in snapshots if Path(r['original']['path']) in HG],
        canonical_before=[bound(p) for p in CANONICAL],
        commands=[dict(configuration=c, argv=command(c, i), expected_program=str(ROOT/c/'out'/n)) for c, i, n in CONFIGS],
        child_environment=dict(TEMP=str(TEMP), TMP=str(TEMP), CUDA_PATH_V11_7=str(CUDA)),
        source_scope='All local src/source C/C++/CUDA/include files and src/VS build files captured before building. Build reads ORIGINAL paths, not snapshot. Library/tool/runtime inputs hashed; external SDK headers/import graph not a hermetic snapshot.',
        programs_executed=False, solver_executed=False, physical_acceptance=False)
    assert len(prepared['hg_before_build_capture']) == 6
    frozen(prepared); seal(PREP, prepared); print(PREP)


def build():
    prepared = read(PREP)
    assert ROOT.is_dir() and not TEMP.exists() and not START.exists() and not CHECK.exists()
    assert not [p for p in LOGS.glob(TAG+'*') if p != PREP], 'Retained/orphan build; never retry'
    frozen(prepared); TEMP.mkdir()
    seal(START, dict(utc=utc(), worker_pid=os.getpid(), prepared=bound(PREP), programs_executed=False))
    env = os.environ.copy(); env.update(prepared['child_environment']); stages = []; error = None
    try:
        for config, index, name in CONFIGS:
            frozen(prepared); folder = ROOT/config/'out'; folder.mkdir(parents=True)
            (TEMP/config/'int').mkdir(parents=True)
            log, binlog = [LOGS/(TAG+'_'+config+s) for s in ['.log', '.binlog']]
            argv = command(config, index); assert argv == next(x['argv'] for x in prepared['commands'] if x['configuration'] == config)
            started, clock = utc(), time.perf_counter()
            with log.open('xb') as stream:
                child = subprocess.Popen(argv, cwd=VS, env=env, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                seal(LOGS/(TAG+'_'+config+'.process.json'), dict(utc=started, parent=os.getpid(), pid=child.pid, argv=argv))
                code = child.wait()
            program, runtime, freeze_error, runtime_error = folder/name, [], None, None
            try: frozen(prepared)
            except Exception as failure: freeze_error = repr(failure)
            try:
                if code == 0 and freeze_error is None and program.is_file():
                    for source in RUNTIME:
                        target = folder/source.name; assert not target.exists(), 'Never overwrite runtime'
                        shutil.copy2(source, target); assert bound(source)['sha256'] == bound(target)['sha256']
                        runtime.append(dict(source=bound(source), target=bound(target)))
            except Exception as failure: runtime_error = repr(failure)
            try: frozen(prepared)
            except Exception as failure: freeze_error = repr(failure)
            passed = code == 0 and freeze_error is None and runtime_error is None and program.is_file() and binlog.is_file() and len(runtime) == 4
            receipt = LOGS/(TAG+'_'+config+'.build.json')
            seal(receipt, dict(status='built_not_run' if passed else 'build_rejected', configuration=config, utc=utc(),
                started_utc=started, elapsed_seconds=time.perf_counter()-clock, exit_code=code, owned_exited=child.poll() is not None,
                argv=argv, protection_error=freeze_error, runtime_error=runtime_error, protected_inputs_unchanged=freeze_error is None,
                program=bound(program) if program.is_file() else None, log=bound(log), binlog=bound(binlog) if binlog.is_file() else None,
                runtime=runtime, prepared=bound(PREP), canonical_after=[bound(p) for p in CANONICAL],
                hg_before_build_capture=prepared['hg_before_build_capture'], exact_HG_sources_captured_before_build=True,
                all_captured_inputs_unchanged_before_after=freeze_error is None, compiled_from_snapshot=False, programs_executed=False))
            stages.append(bound(receipt)); assert passed, ('Build rejected; later configurations held', config, code, freeze_error, runtime_error)
    except Exception as failure: error = repr(failure)
    passed = error is None and len(stages) == len(CONFIGS)
    seal(CHECK, dict(status='builds_passed_pending_implementation_regression' if passed else 'build_rejected_or_interrupted',
        utc=utc(), passed=passed, error=error, prepared=bound(PREP), stages=stages, programs_executed=False,
        solver_executed=False, implementation_regression_passed=False, physical_acceptance=False, formal_admitted=False))
    print(CHECK); return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); group = parser.add_mutually_exclusive_group()
    for flag in ['selftest', 'prepare', 'build']: group.add_argument('--'+flag, action='store_true')
    args = parser.parse_args()
    if args.selftest: selftest()
    elif args.prepare: prepare()
    elif args.build: raise SystemExit(build())
    else: parser.print_help()
