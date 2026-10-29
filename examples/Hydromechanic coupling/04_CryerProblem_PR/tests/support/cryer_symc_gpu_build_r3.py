"""PROPOSAL: isolated GPU sym-C Debug/Release build; never launch the program.

Default/help has no writes. --prepare freezes commands/inputs only; --build needs
that reviewed plan and writes one fresh configuration below the isolated tag.
No canonical MSBuild target, postbuild action, physical solver or notifier runs.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import traceback

TESTS = Path(__file__).resolve().parents[1]
REPO = TESTS.parents[3]
SRC = REPO / 'src'
VS = SRC / 'VS'
TAG = 'cryer_symc_gpu_build_r3'
OUT = TESTS / 'outputs' / TAG
CANDIDATE = OUT / 'JSphGpu_ker.cu'
CANONICAL = SRC / 'source/JSphGpu_ker.cu'
PROJECT = VS / 'DualSPHysics5Re.vcxproj'
PLAN = TESTS / 'logs' / (TAG + '.inputs.json')
NOTE = TESTS / 'notes/cryer_symc_gpu_r3.json'
CPU_BUILD = TESTS / 'logs/cryer_symc_release_r1.build.json'
CPU_SOURCE = TESTS / 'outputs/cryer_symc_cpu_build_r1/JSphCpu.cpp'
LIAN = REPO / 'examples/Hydromechanic coupling/05_LianFlexibleStrip2D_PR/tests'
CUDA = Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7')
MSVC = Path(r'D:\Program Files\VS2022\VC\Tools\MSVC\14.36.32532')
VSDEV = Path(r'D:\Program Files\VS2022\Common7\Tools\VsDevCmd.bat')
SDK = Path(r'C:\Program Files (x86)\Windows Kits\10')
EXPECTED_SOURCE_SHA = '0a2d2cde05f18f6ad7a8e8a929e742a0b07ec31ca3c8cdfebd786d21753764c6'
EXPECTED_PROJECT_SHA = 'a719dae2496ede01177d6fa5674daf8319cc49000c729c5804ebe80419cab320'
EXPECTED_CPU_SOURCE_SHA = '99c7c445db16bcd8d25e5599012e9129f2a2523e458c55d4192432649c8c9fb8'

SIGNATURE = ',const float *porepress,const tmatrix3d &porecorr,bool poreratep1,const float pwp1,double &pore_ratep1,const float3 *boundderivativevel)'
CALL = 'porepress,porecorr,poreratep1,pwp1,pore_ratep1,boundderivativevel);'
REMOVED = '''              const double lapw=vol2*(double(pwp1)-pwp2seep)*pdotgrad/double(prr2+CTE.eta2);
              const double lapz=vol2*pdrz*pdotgrad/double(prr2+CTE.eta2);'''
INSERTED = '''              //-Isolated Cryer probe: symmetric soil-soil Darcy contraction only.
              double lapdotgrad=pdotgrad;
              if(!boundp2 && corrmat && CODE_IsFluid(code[p2])){
                const tmatrix3d cj=corrmat[p2];
                const double jfrx=cj.a11*pfrx+cj.a12*pfry+cj.a13*pfrz;
                const double jfry=cj.a21*pfrx+cj.a22*pfry+cj.a23*pfrz;
                const double jfrz=cj.a31*pfrx+cj.a32*pfry+cj.a33*pfrz;
                lapdotgrad=.5*(pdotgrad+pdrx*jfrx+pdry*jfry+pdrz*jfrz);
              }
              const double lapw=vol2*(double(pwp1)-pwp2seep)*lapdotgrad/double(prr2+CTE.eta2);
              const double lapz=vol2*pdrz*lapdotgrad/double(prr2+CTE.eta2);'''


def utc():
    return datetime.now(timezone.utc).isoformat()


def bound(path):
    p = Path(path).resolve()
    with p.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(p), bytes=p.stat().st_size, sha256=digest)


def key(path):
    return str(Path(path).resolve()).casefold()


def seal(path, data):
    with Path(path).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')


def snapshot(paths):
    unique = {key(p): Path(p).resolve() for p in paths}
    return [bound(unique[k]) for k in sorted(unique)]


def inventories(paths):
    return {str(Path(d).resolve()): sorted(str(p.relative_to(d)).casefold()
            for p in Path(d).rglob('*') if p.is_file()) for d in paths}


def verify(records):
    changes = []
    for old in records:
        new = bound(old['path']) if Path(old['path']).is_file() else None
        if new is None or (old['sha256'], old['bytes']) != (new['sha256'], new['bytes']):
            changes.append(dict(before=old, after=new))
    return changes


def split_command(command):
    # Windows argv parsing handles nvcc's escaped gencode quotes and spaces.
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    count = ctypes.c_int()
    ptr = shell.CommandLineToArgvW('placeholder.exe ' + command, ctypes.byref(count))
    assert ptr, 'CommandLineToArgvW failed'
    try:
        return [ptr[i] for i in range(1, count.value)]
    finally:
        kernel.LocalFree(ctypes.cast(ptr, ctypes.c_void_p))


def tlog_lines(path):
    return [line for line in Path(path).read_text(encoding='utf16').splitlines() if line]


def source_comparison():
    assert bound(CANONICAL)['sha256'] == EXPECTED_SOURCE_SHA
    assert bound(PROJECT)['sha256'] == EXPECTED_PROJECT_SHA
    assert bound(CPU_SOURCE)['sha256'] == EXPECTED_CPU_SOURCE_SHA
    original = CANONICAL.read_text(encoding='utf8')
    candidate = CANDIDATE.read_text(encoding='utf8')
    assert original.count(SIGNATURE) == original.count(REMOVED) == 1
    assert original.count(CALL) == 4
    expected = original.replace(SIGNATURE, SIGNATURE[:-1] + ',const tmatrix3d* corrmat)')
    expected = expected.replace(CALL, CALL[:-2] + ',corrmat);').replace(REMOVED, INSERTED)
    assert candidate == expected, 'Unexpected source, comment, encoding or whitespace delta after newline normalization'
    cpu = json.loads(CPU_BUILD.read_text(encoding='utf8'))
    assert cpu['status'] == 'built_not_run' and cpu['protected_inputs_unchanged']
    assert cpu['source_comparison']['candidate']['sha256'] == EXPECTED_CPU_SOURCE_SHA
    cpu_block = cpu['source_comparison']['inserted'].replace('Eta2', 'CTE.eta2')
    assert [s.strip() for s in cpu_block.splitlines()] == [s.strip() for s in INSERTED.splitlines()]
    return dict(canonical=bound(CANONICAL), candidate=bound(CANDIDATE), cpu_candidate=bound(CPU_SOURCE),
                exact_normalized_source_is_declared_delta=True, signature_additions=1,
                existing_call_additions=4, darcy_block_replacements=1,
                comments_and_encoding_preserved=True, candidate_newlines='LF; canonical mixed bytes untouched',
                cpu_candidate_Darcy_algebra_exact_ignoring_indentation_and_CTE_prefix=True,
                removed=REMOVED, inserted=INSERTED,
                unchanged=['compression', 'stress/pressure force', 'load', 'boundary handling', 'integration', 'main'])


def configuration_plan(cfg):
    folder = OUT / cfg
    tdir = VS / f'Intermediate/DualSPHysics_{cfg}_x64/DualSPHysics.tlog'
    production_log = LIAN / f'logs/lian_mirror_build_r1_{cfg}.log'
    commands = []
    log_bytes = production_log.read_bytes()
    log_encoding = 'utf16' if log_bytes.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    for line in log_bytes.decode(log_encoding).splitlines():
        match = re.search(r'("[^"\r\n]*nvcc\.exe".*)$', line, re.I)
        if match and 'JSphGpu_ker.cu' in match[1]:
            commands.append(match[1].strip())
    assert len(commands) == 1, 'Missing/ambiguous authoritative GPU compile command'
    compile_args = split_command(commands[0])
    assert key(compile_args[0]) == key(CUDA / 'bin/nvcc.exe')
    assert compile_args.count('--compile') == 1
    assert not any(s in compile_args for s in ['--device-c', '-dc', '--device-link', '-dlink', '-rdc=true'])
    assert compile_args.count('--keep-dir') == compile_args.count('-o') == 1
    assert sum(key(s) == key(CANONICAL) for s in compile_args if s.lower().endswith('.cu')) == 1
    gencode = [s for s in compile_args if s.startswith('-gencode=')]
    assert gencode == ['-gencode=arch=compute_86,code="sm_86,compute_86"']
    assert ('-G' in compile_args) == (cfg == 'Debug')
    compile_args[compile_args.index('--keep-dir') + 1] = 'keep'
    compile_args[compile_args.index('-o') + 1] = 'JSphGpu_ker.cu.obj'
    old_xcompiler = [i + 1 for i, x in enumerate(compile_args[:-1]) if x == '-Xcompiler' and '/Fd' in compile_args[i + 1]]
    assert len(old_xcompiler) == 1
    i = old_xcompiler[0]
    compile_args[i], replacements = re.subn(r'/Fd[^\s]+', lambda _: '/Fdcuda_host.pdb', compile_args[i])
    assert replacements == 1
    compile_args = [str(CANDIDATE) if s.lower().endswith('.cu') and key(s) == key(CANONICAL) else s for s in compile_args]
    # Same header resolution as canonical source, whose relative includes now need this -I.
    compile_args += ['-I' + str(SRC / 'source'), '--generate-dependencies-with-compile',
                     '--dependency-output', 'JSphGpu_ker.dependencies.d']
    actual_link_lines = tlog_lines(tdir / 'link.command.1.tlog')
    assert sum(s.startswith('^') for s in actual_link_lines) == 1
    raw_link = ' '.join(s for s in actual_link_lines if not s.startswith('^'))
    old_link = split_command(raw_link)
    assert not any('dlink' in s.lower() or 'device-link' in s.lower() for s in old_link)
    objects = [(VS / s).resolve() for s in old_link if s.lower().endswith('.obj')]
    assert len(objects) == len(set(map(key, objects))) == 111
    assert sum(p.name.lower() == 'main.obj' for p in objects) == 1
    assert sum(p.name.lower() == 'jsphgpu_ker.cu.obj' for p in objects) == 1
    tracked = [Path(s) for s in tlog_lines(tdir / 'link.read.1.tlog') if not s.startswith('^')]
    libraries = {p.name.casefold(): p for p in tracked if p.suffix.lower() == '.lib'}
    assert all(p.is_file() for p in objects)
    assert all(p.is_file() for p in libraries.values())
    executable = folder / f'cryer_symc_gpu_r3_{cfg}.exe'
    link = [str(MSVC / 'bin/Hostx64/x64/link.exe')]
    for arg in old_link:
        lower = arg.lower()
        if lower.startswith(('/out:', '/pdb:', '/implib:', '/ltcgout:', '/ilk:', '/manifestfile:', '/pgd:')):
            continue
        if lower.startswith('/libpath:'):
            arg = '/LIBPATH:' + str((VS / arg.split(':', 1)[1]).resolve())
        elif lower.endswith('.obj'):
            p = (VS / arg).resolve()
            arg = str(folder / 'JSphGpu_ker.cu.obj' if p.name.lower() == 'jsphgpu_ker.cu.obj' else p)
        elif lower.endswith('.lib'):
            arg = str(libraries[Path(arg).name.casefold()])
        link.append(arg)
    link += ['/OUT:' + str(executable), '/PDB:' + str(folder / 'link.pdb'),
             '/IMPLIB:' + str(folder / 'link.lib'), '/LTCGOUT:' + str(folder / 'link.iobj'),
             '/ILK:' + str(folder / 'link.ilk'), '/MANIFESTFILE:' + str(folder / 'link.intermediate.manifest')]
    reads = [Path(s) for name in ['CL.read.1.tlog', 'CudaCompile.read.1u.tlog']
             for s in tlog_lines(tdir / name) if not s.startswith('^')]
    # Protect all canonical objects and existing writable link sidecars too.
    outputs = [p for d in [VS / f'Intermediate/DualSPHysics_{cfg}_x64', VS / f'x64/{cfg}']
               for p in d.iterdir() if p.is_file()]
    paths = [production_log, *tdir.glob('*.tlog'), *reads, *tracked, *objects, *outputs]
    assert all(p.is_file() for p in paths), 'Missing authoritative dependency; do not silently omit it'
    return dict(configuration=cfg, directory=str(folder), executable=str(executable),
                compile=compile_args, link=link, authoritative_nvcc_command=commands[0],
                authoritative_link_command=raw_link, original_object_count=111,
                canonical_main_object_retained=True, harness_object_added=False,
                device_link_required=False, no_rdc_authoritative_compile=True,
                header_dependency_output=str(folder / 'JSphGpu_ker.dependencies.d'),
                original_objects=[str(p) for p in objects], libraries=[str(p) for p in libraries.values()]), paths


def prepare():
    assert not PLAN.exists(), 'Retained plan; never overwrite or reprepare'
    assert OUT.is_dir() and sorted(p.name for p in OUT.iterdir()) == ['JSphGpu_ker.cu']
    for cfg in ['Debug', 'Release']:
        assert not (TESTS / 'logs' / f'{TAG}_{cfg}.build.json').exists()
        assert not (TESTS / 'logs' / f'{TAG}_{cfg}.build.log').exists()
    comparison = source_comparison()
    configurations, paths = {}, [Path(__file__), NOTE, CPU_BUILD, CPU_SOURCE, CANONICAL, CANDIDATE,
                                 PROJECT, VS / 'DualSPHysics5Re.sln', VSDEV,
                                 LIAN / 'scripts/lian_spr_mix_gpu_build.ps1', CUDA / 'bin/nvcc.profile']
    for cfg in ['Debug', 'Release']:
        configurations[cfg], more = configuration_plan(cfg)
        paths += more
    # Bind the compiler pipeline, linker/runtime tools and NVVM libdevice, not just nvcc.exe.
    for directory in [CUDA / 'bin', CUDA / 'nvvm/bin', MSVC / 'bin/Hostx64/x64']:
        paths += [p for p in directory.rglob('*') if p.is_file() and p.suffix.lower() in ['.exe', '.dll']]
    paths += list((CUDA / 'nvvm/libdevice').glob('*.bc'))
    # Bootstrap from real r2 compile dependencies; these are frozen BEFORE r3 compilation.
    paths += [TESTS / 'logs/cryer_symc_gpu_build_r2_Debug.build.json',
              TESTS / 'outputs/cryer_symc_gpu_build_r2/Debug/JSphGpu_ker.dependencies.d']
    for include_root in [CUDA / 'include', MSVC / 'include']:
        assert include_root.is_dir()
        paths += [p for p in include_root.rglob('*') if p.is_file()]
    canonical_bin = REPO / 'bin/windows'
    runtime = [canonical_bin / s for s in ['ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll', 'DsphConfig.xml']]
    paths += [p for p in canonical_bin.iterdir() if p.is_file() and p.suffix.lower() in ['.exe', '.dll', '.pdb', '.lib', '.exp', '.ilk']]
    paths += runtime
    inputs = snapshot(paths)
    protected_dirs = [SRC / 'source', canonical_bin]
    protected_dirs += [p for cfg in ['Debug', 'Release']
                       for p in [VS / f'Intermediate/DualSPHysics_{cfg}_x64', VS / f'x64/{cfg}']]
    seal(PLAN, dict(status='prepared_not_built', utc=utc(), tag=TAG, source_comparison=comparison,
                    configurations=configurations, protected_inputs=inputs,
                    protected_directory_inventories=inventories(protected_dirs),
                    runtime=[bound(p) for p in runtime],
                    toolkit='CUDA11.7; MSVC14.36.32532; WindowsSDK10.0.22000.0; sm86+compute86',
                    no_solver_launched=True, no_build_executed=True, physical_acceptance=False,
                    limitations=['Unbuilt GPU candidate; no memcheck or CPU/GPU evidence yet',
                                 'Only canonical CUDA TU is rebuilt; other authoritative objects reused',
                                 'No rDC/device-link in actual project; fail closed on its appearance']))
    print(json.dumps(dict(status='prepared_not_built', plan=bound(PLAN), protected_count=len(inputs)), indent=2))


def environment(folder):
    command = '"' + os.environ['ComSpec'] + '" /d /c call "' + str(VSDEV) + '" -arch=x64 -host_arch=x64 -winsdk=10.0.22000.0 -vcvars_ver=14.36 >nul && set'
    result = subprocess.run(command, capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    env = {name.upper(): value for name, value in os.environ.items()}
    for line in result.stdout.decode('mbcs').splitlines():
        if '=' in line and not line.startswith('='):
            name, value = line.split('=', 1)
            env[name.upper()] = value
    assert not any(env.get(k) for k in ['CL', '_CL_', 'LINK', '_LINK_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'])
    include = [MSVC / 'include', SDK / 'include/10.0.22000.0/ucrt', SDK / 'include/10.0.22000.0/shared', SDK / 'include/10.0.22000.0/um', SDK / 'include/10.0.22000.0/winrt']
    libs = [MSVC / 'lib/x64', SDK / 'lib/10.0.22000.0/ucrt/x64', SDK / 'lib/10.0.22000.0/um/x64', CUDA / 'lib/x64', SRC / 'lib/vs2022']
    assert all(p.is_dir() for p in include + libs)
    env.update(INCLUDE=';'.join(map(str, include)), LIB=';'.join(map(str, libs)),
               TEMP='tmp', TMP='tmp',
               VSCMD_SKIP_SENDTELEMETRY='1', CUDA_CACHE_PATH='cuda_cache')
    return env


def dependencies(path):
    text = re.sub(r'\\\r?\n', ' ', Path(path).read_text(encoding='utf8'))
    match = re.search(r':(?=\s)', text)
    assert match, 'Unknown nvcc make-dependency syntax; preserve evidence for review'
    words = re.findall(r'(?:\\.|[^\s])+', text[match.end():])
    return [Path(s.replace('\\ ', ' ').replace('\\#', '#').replace('\\:', ':').strip('"')).resolve() for s in words]


def build(cfg):
    plan = json.loads(PLAN.read_text(encoding='utf8'))
    assert plan['status'] == 'prepared_not_built'
    assert not verify(plan['protected_inputs']), 'Frozen dependency/program/source drift before build'
    assert inventories(plan['protected_directory_inventories']) == plan['protected_directory_inventories']
    source_comparison()
    settings = plan['configurations'][cfg]
    folder = Path(settings['directory'])
    logfile = TESTS / 'logs' / f'{TAG}_{cfg}.build.log'
    manifest = TESTS / 'logs' / f'{TAG}_{cfg}.build.json'
    assert not any(p.exists() for p in [folder, logfile, manifest]), 'Retained configuration; never overwrite/restart'
    record = dict(status='build_failed_preserved', started_utc=utc(), configuration=cfg,
                  plan=bound(PLAN), source_comparison=plan['source_comparison'], stages=[],
                  protected_inputs=plan['protected_inputs'], no_solver_launched=True,
                  physical_acceptance=False, canonical_main_object_retained=True,
                  device_link_required=False, artifacts=[])
    folder.mkdir()
    for sub in ['tmp', 'keep', 'cuda_cache']:
        (folder / sub).mkdir()
    try:
        env = environment(folder)
        record['environment'] = {k: env[k] for k in ['INCLUDE', 'LIB', 'TEMP', 'TMP', 'CUDA_CACHE_PATH', 'PATH']}
        with logfile.open('xb') as log:
            for name in ['compile', 'link']:
                command = settings[name]
                record[name] = command
                log.write(('STAGE ' + name + '\n').encode()); log.flush()
                tick = time.perf_counter()
                result = subprocess.run(command, cwd=folder, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                record['stages'].append(dict(stage=name, exit_code=result.returncode, seconds=time.perf_counter() - tick))
                assert result.returncode == 0, name + ' failed; preserve label and inspect log'
                if name == 'compile':
                    headers = dependencies(settings['header_dependency_output'])
                    known = {key(p['path']) for p in plan['protected_inputs']}
                    assert headers and all(key(p) in known for p in headers), 'Unbound compiled dependency; do not link'
                    record['compiled_dependencies'] = snapshot(headers)
                    record['compiled_dependencies_all_bound_before_compile'] = True
        runtime = []
        for old in plan['runtime']:
            target = folder / Path(old['path']).name
            assert not target.exists()
            shutil.copy2(old['path'], target)
            assert bound(target)['sha256'] == old['sha256']
            runtime.append(dict(source=old, target=bound(target)))
        record.update(status='built_not_run', program=bound(settings['executable']), runtime=runtime)
    except BaseException as error:
        record.update(error=repr(error), traceback=traceback.format_exc())
    finally:
        changes = verify(plan['protected_inputs'])
        directories_after = inventories(plan['protected_directory_inventories'])
        directory_changes = {d: dict(before=files, after=directories_after[d])
                             for d, files in plan['protected_directory_inventories'].items()
                             if files != directories_after[d]}
        record.update(protected_inputs_unchanged=not changes and not directory_changes,
                      changed_protected=changes, changed_canonical_inventories=directory_changes,
                      finished_utc=utc())
        if changes or directory_changes:
            record['status'] = 'build_failed_preserved'
        record['artifacts'] = [bound(p) for p in sorted(folder.rglob('*')) if p.is_file()]
        if logfile.exists():
            record['artifacts'].append(bound(logfile))
            text = logfile.read_bytes().decode('mbcs', errors='replace')
            record['warnings'] = sorted(set(re.findall(r'^.*(?:warning |ptxas warning).*$', text, re.M)))
        seal(manifest, record)
    assert record['status'] == 'built_not_run', record.get('error', 'Protected input drift')
    print(json.dumps(dict(status='built_not_run', program=record['program'], manifest=bound(manifest)), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--prepare', action='store_true', help='Freeze source, all input hashes and proposed commands; no build')
    group.add_argument('--build', choices=['Debug', 'Release'], help='Explicit later-authorized isolated build; never run program')
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.build:
        build(args.build)
    else:
        parser.print_help()
