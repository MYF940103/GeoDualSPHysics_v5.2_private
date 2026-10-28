"""Build one isolated full ReleaseCPU solver; no physical run or canonical writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import traceback
from datetime import datetime, timezone

TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]
SRC = REPO / 'src'
VS = SRC / 'VS'
TAG = 'cryer_symc_release_r1'
OUT = TESTS / 'outputs' / TAG
EXE = OUT / (TAG + '.exe')
LOG = TESTS / 'logs' / (TAG + '.build.log')
MANIFEST = TESTS / 'logs' / (TAG + '.build.json')
INPUTS = TESTS / 'logs' / (TAG + '.inputs.json')
CANDIDATE = TESTS / 'outputs/cryer_symc_cpu_build_r1/JSphCpu.cpp'
SEALED = TESTS / 'logs/cryer_symc_cpu_r1_seal_r2.build.json'
TLOG = VS / 'Intermediate/DualSPHysics_ReleaseCPU_x64/DualSPHysics.tlog'
CANONICAL = SRC / 'source/JSphCpu.cpp'


def utc():
    return datetime.now(timezone.utc).isoformat()


def bound(path):
    p = Path(path).resolve()
    with p.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(p), bytes=p.stat().st_size, sha256=digest)


def seal(path, data):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)


def tokens(text):
    # Tlog quoting is ordinary MSVC quoting; preserve quoted arguments as one item.
    return [x.replace('"', '') for x in re.findall(r'(?:[^\s"]|"[^"]*")+', text)]


def lines(name):
    return [x for x in (TLOG / name).read_text(encoding='utf-16').splitlines() if x]


def key(path):
    return str(Path(path).resolve()).lower()


def snapshot(paths):
    unique = {key(p): Path(p).resolve() for p in paths}
    return [bound(unique[k]) for k in sorted(unique)]


def build():
    assert not any(p.exists() for p in [OUT, LOG, MANIFEST, INPUTS]), 'Retained build label; never overwrite or restart'
    started = utc()
    record = dict(status='build_failed_preserved', configuration='ReleaseCPU', started_utc=started,
                  solver_launched=False, physical_acceptance=False, stages=[], inputs=[], runtime=[], artifacts=[])
    OUT.mkdir()
    (OUT / 'tmp').mkdir()
    try:
        old = json.loads(SEALED.read_text(encoding='utf8'))
        comparison = old['source_comparison']
        assert comparison['exact_normalized_source_is_single_Darcy_replacement']
        assert bound(CANDIDATE)['sha256'] == comparison['candidate']['sha256']
        assert bound(CANONICAL)['sha256'] == comparison['canonical']['sha256']
        original = CANONICAL.read_text(encoding='utf8')
        candidate = CANDIDATE.read_text(encoding='utf8')
        assert original.count(comparison['removed']) == 1
        assert candidate == original.replace(comparison['removed'], comparison['inserted'])
        record['source_comparison'] = comparison
        command_lines = lines('CL.command.1.tlog')
        matches = [i for i, s in enumerate(command_lines) if s.startswith('^') and s.upper().endswith('\\JSPHCPU.CPP')]
        assert len(matches) == 1
        actual_compile = command_lines[matches[0] + 1]
        compile_args = tokens(actual_compile)
        assert all(flag in compile_args for flag in ['/O2', '/MT', '/fp:precise', '/openmp'])
        assert '/GL' not in compile_args
        source_args = [s for s in compile_args if s.lower().endswith('\\jsphcpu.cpp')]
        assert len(source_args) == 1
        obj = OUT / 'JSphCpu_symc.obj'
        dependencies = OUT / 'JSphCpu.dependencies.json'
        compile_args = [s for s in compile_args if not s.lower().startswith(('/fo', '/fd')) and s not in source_args]
        compile_args += ['/Fo' + str(obj), '/Fd' + str(OUT / 'compile.pdb'), '/I' + str(SRC / 'source'),
                         '/sourceDependencies', str(dependencies), str(CANDIDATE)]
        link_lines = lines('link.command.1.tlog')
        assert sum(s.startswith('^') for s in link_lines) == 1
        actual_link = ' '.join(s for s in link_lines if not s.startswith('^'))
        link_args = tokens(actual_link)
        tracked_link = [Path(s) for s in lines('link.read.1.tlog') if not s.startswith('^')]
        libraries = {p.name.lower(): p for p in tracked_link if p.suffix.lower() == '.lib'}
        original_objects = [(VS / s).resolve() for s in link_args if s.lower().endswith('.obj')]
        assert len(original_objects) == len(set(map(key, original_objects))) == 86
        assert sum(p.name.lower() == 'jsphcpu.obj' for p in original_objects) == 1
        assert sum(p.name.lower() == 'main.obj' for p in original_objects) == 1
        isolated_link = []
        for arg in link_args:
            if arg.lower().startswith(('/out:', '/pdb:', '/implib:', '/ltcgout:')):
                continue
            if arg.lower().startswith('/libpath:'):
                arg = '/LIBPATH:' + str((VS / arg.split(':', 1)[1]).resolve())
            elif arg.lower().endswith('.obj'):
                p = (VS / arg).resolve()
                arg = str(obj if p.name.lower() == 'jsphcpu.obj' else p)
            elif arg.lower().endswith('.lib'):
                arg = str(libraries[Path(arg).name.lower()])
            isolated_link.append(arg)
        isolated_link += ['/OUT:' + str(EXE), '/PDB:' + str(OUT / (TAG + '.pdb')),
                          '/IMPLIB:' + str(OUT / (TAG + '.lib')),
                          '/LTCGOUT:' + str(OUT / (TAG + '.iobj')), '/ILK:' + str(OUT / (TAG + '.ilk'))]
        # Capture VS environment only; pin the SDK/UCRT used by the authoritative tlogs.
        vsdev = Path(r'D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat')
        env_command = '"' + os.environ['ComSpec'] + '" /d /c call "' + str(vsdev) + '" -arch=x64 -host_arch=x64 -winsdk=8.1 >nul && set'
        env_result = subprocess.run(env_command, capture_output=True, check=True)
        env = {name.upper(): value for name, value in os.environ.items()}
        for line in env_result.stdout.decode('mbcs').splitlines():
            if '=' in line and not line.startswith('='):
                name, value = line.split('=', 1)
                env[name.upper()] = value
        msvc = Path(r'D:\Program Files\VS2022\VC\Tools\MSVC\14.36.32532')
        kits = Path(r'C:\Program Files (x86)\Windows Kits')
        include = [msvc / 'include', kits / '10/include/10.0.10240.0/ucrt', kits / '8.1/include/shared', kits / '8.1/include/um']
        libdirs = [SRC / 'lib/vs2022', msvc / 'lib/x64', kits / '8.1/lib/winv6.3/um/x64', kits / '10/lib/10.0.10240.0/ucrt/x64']
        assert all(p.is_dir() for p in include + libdirs)
        env.update(INCLUDE=';'.join(map(str, include)), LIB=';'.join(map(str, libdirs)),
                   TEMP=str(OUT / 'tmp'), TMP=str(OUT / 'tmp'), VSCMD_SKIP_SENDTELEMETRY='1')
        assert not any(env.get(name) for name in ['CL', '_CL_', 'LINK', '_LINK_']), 'Unrecorded native-tool environment flags'
        compiler = msvc / 'bin/Hostx64/x64/cl.exe'
        linker = msvc / 'bin/Hostx64/x64/link.exe'
        reads = [Path(s) for s in lines('CL.read.1.tlog') if not s.startswith('^')]
        canonical_bin = REPO / 'bin/windows'
        runtime_sources = [canonical_bin / s for s in ['ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll', 'DsphConfig.xml']]
        protected_programs = [p for p in canonical_bin.iterdir() if p.is_file() and
                              (p.name.startswith('DualSPHysics') and p.suffix.lower() == '.exe' or p.suffix.lower() == '.dll' or p.name == 'DsphConfig.xml')]
        protected = [Path(__file__), SEALED, CANDIDATE, CANONICAL, compiler, linker, vsdev,
                     VS / 'DualSPHysics5ReCpu.vcxproj', VS / 'DualSPHysics5ReCpu_vs2022.sln',
                     *TLOG.glob('*.tlog'), *reads, *tracked_link, *original_objects, *runtime_sources, *protected_programs]
        before = snapshot(protected)
        record.update(inputs=before, original_object_count=86, replacement_object=str(obj),
                      authoritative_compile_command=actual_compile, authoritative_link_command=actual_link,
                      compile=[str(compiler), *compile_args], link=[str(linker), *isolated_link],
                      build_environment={k: env[k] for k in ['INCLUDE', 'LIB', 'TEMP', 'TMP']},
                      canonical_main_object_retained=True, harness_object_added=False)
        seal(INPUTS, dict(utc=utc(), inputs=before, compile=record['compile'], link=record['link'],
                          source_comparison=comparison, physical_acceptance=False))
        with LOG.open('xb') as log:
            for name, args in [('compile', record['compile']), ('link', record['link'])]:
                log.write(('STAGE ' + name + '\n').encode()); log.flush()
                tick = time.perf_counter()
                result = subprocess.run(args, cwd=OUT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
                record['stages'].append(dict(stage=name, exit_code=result.returncode, seconds=time.perf_counter() - tick))
                assert result.returncode == 0, name + ' failed; retain this label and inspect build.log'
        dependency_record = json.loads(dependencies.read_text(encoding='utf-8-sig'))['Data']
        actual_headers = {key(p) for p in dependency_record['Includes']}
        clread = lines('CL.read.1.tlog')
        start = next(i for i, s in enumerate(clread) if s.startswith('^') and s.upper().endswith('\\JSPHCPU.CPP'))
        tracked_headers = []
        for s in clread[start + 1:]:
            if s.startswith('^'):
                break
            if Path(s).suffix.lower() != '.exe':
                tracked_headers.append(s)
        assert actual_headers == {key(p) for p in tracked_headers}, 'Compiled header dependency set drifted from authoritative JSphCpu'
        record['compiled_header_dependency_set_matches_authoritative'] = True
        record['compiled_header_count'] = len(actual_headers)
        for source in runtime_sources:
            target = OUT / source.name
            assert not target.exists()
            shutil.copy2(source, target)
            assert bound(source)['sha256'] == bound(target)['sha256']
        record['runtime'] = [dict(**bound(OUT / p.name), source=bound(p)) for p in runtime_sources]
        record['program'] = bound(EXE)
        record['status'] = 'built_not_run'
    except BaseException as error:
        record.update(error=repr(error), traceback=traceback.format_exc())
    finally:
        changed = []
        for before in record['inputs']:
            if not Path(before['path']).is_file():
                changed.append(dict(before=before, after=None))
                continue
            now = bound(before['path'])
            if (now['sha256'], now['bytes']) != (before['sha256'], before['bytes']):
                changed.append(dict(before=before, after=now))
        record.update(protected_inputs_unchanged=not changed, changed_protected=changed, finished_utc=utc())
        if changed:
            record['status'] = 'build_failed_preserved'
        if LOG.exists():
            text = LOG.read_bytes().decode('mbcs', errors='replace')
            record['warnings'] = sorted(set(re.findall(r'^.*warning (?:C|D|LNK)\d+.*$', text, re.M)))
        record['artifacts'] = [bound(p) for p in sorted(OUT.rglob('*')) if p.is_file()]
        record['artifacts'] += [bound(p) for p in [INPUTS, LOG] if p.exists()]
        seal(MANIFEST, record)
    assert record['status'] == 'built_not_run', record.get('error', 'Protected file changed')
    print(json.dumps(dict(status=record['status'], program=record['program'], manifest=bound(MANIFEST),
                          warnings=record.get('warnings', [])), indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    if args.build:
        build()
    else:
        parser.print_help()
