"""One separately admitted before-mDBC CPU TU compile and link; no program run.

Author asset: importing this file performs no filesystem or subprocess action.
The actual baseline reuses the current Debug project's other 86 objects, including
main. It changes no public source, canonical executable, numerical gate or input.
"""
import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess


TAG = 'c08_h18_wall_c_before_CPU_Debug_r2'
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
T = Path(__file__).resolve().parents[1]
R = T.parents[3]
S, L = R / 'src', T / 'logs'
SCRIPT = Path(__file__).resolve()
NOTE = T / 'notes' / (TAG + '.md')
BASE = L / 'c08_h18_wall_c_retry_CPU_Debug_r1.build.json'
SOURCE = L / 'c08_h18_wall_c_retry_r1.source.json'
ADMISSION = L / (TAG + '.root_build_admission.json')
OUT = T / 'outputs' / TAG
CHECK = L / (TAG + '.build.json')
VC = Path(r'D:/Program Files/VS2022/VC')
BIN = VC / 'Tools/MSVC/14.36.32532/bin/Hostx64/x64'
UCRT_VERSION = '10.0.10240.0'
PRIOR_FAILED_BUILD = L / 'c08_h18_wall_c_before_CPU_Debug_r1.build.json'


def need(ok, why):
    if not ok:
        raise RuntimeError(why)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def stat(path):
    path = Path(path).resolve()
    value = path.stat()
    need(path.is_file(), 'Expected file: ' + str(path))
    return dict(path=str(path), bytes=value.st_size, mtime_ns=value.st_mtime_ns)


def bind(entry):
    need(stat(entry['path']) == entry, 'Changed bound file: ' + entry['path'])
    return entry


def save(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def key(path):
    return os.path.normcase(os.path.abspath(path))


def windows_args(text):
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW('tool.exe ' + text, ctypes.byref(count))
    need(bool(pointer), 'Cannot parse the authoritative Windows command')
    try:
        return [pointer[i] for i in range(1, count.value)]
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes, free.restype = [ctypes.c_void_p], ctypes.c_void_p
        free(ctypes.cast(pointer, ctypes.c_void_p))


def invoke(label, argv, cwd, env, capture_stdout=False):
    """Preserve Popen and the same native process-handle exit separately."""
    log, receipt = L / (label + '.log'), L / (label + '.call.json')
    need(not log.exists() and not receipt.exists(), 'Existing tool call protected')
    value = dict(stage=label, program=argv[0], arguments=argv[1:], cwd=str(cwd),
                 started_utc=datetime.now(timezone.utc).isoformat(),
                 owner_pid=os.getpid(), child=None, actual_Popen_wait_exit=None,
                 actual_Win32_exit=None, invocation_failure=None,
                 stdout_not_persisted=capture_stdout)
    payload, process, kernel = b'', None, None
    try:
        with log.open('xb') as stream:
            process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE if capture_stdout else stream,
                stderr=stream if capture_stdout else subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_ulonglong)] * 4
            kernel.GetProcessTimes.restype = ctypes.c_int
            kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
            kernel.GetExitCodeProcess.restype = ctypes.c_int
            kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
            kernel.QueryFullProcessImageNameW.restype = ctypes.c_int
            times = [ctypes.c_ulonglong() for _ in range(4)]
            need(kernel.GetProcessTimes(int(process._handle), *(ctypes.byref(q) for q in times)),
                 'Cannot capture original tool creation time')
            image, length = ctypes.create_unicode_buffer(32768), ctypes.c_ulong(32768)
            need(kernel.QueryFullProcessImageNameW(int(process._handle), 0, image, ctypes.byref(length)),
                 'Cannot capture original tool executable')
            value['child'] = dict(pid=process.pid, creation_filetime_100ns=times[0].value,
                exe=image.value, launched_argv=argv, parent_pid_expected=os.getpid(),
                argv_source='the exact direct Popen argv, not an OS command-line query')
            need(key(image.value) == key(argv[0]), 'Actual tool executable identity differs')
            if capture_stdout:
                payload = process.communicate()[0]
                popen_exit = process.returncode
            else:
                popen_exit = process.wait()
            value['actual_Popen_wait_exit'] = popen_exit
            code = ctypes.c_ulong()
            need(kernel.GetExitCodeProcess(int(process._handle), ctypes.byref(code)),
                 'Original process handle exit unavailable')
            value['actual_Win32_exit'] = code.value
            value['captured_stdout_bytes'] = len(payload)
    except BaseException as error:
        value['invocation_failure'] = repr(error)
        # Never abandon an already created build tool merely because identity
        # observation failed. Preserve its actual exits without another launch.
        if process is not None:
            try:
                if capture_stdout and process.stdout is not None:
                    payload = process.communicate()[0]
                    value['actual_Popen_wait_exit'] = process.returncode
                else:
                    value['actual_Popen_wait_exit'] = process.wait()
                if kernel is not None:
                    code = ctypes.c_ulong()
                    if kernel.GetExitCodeProcess(int(process._handle), ctypes.byref(code)):
                        value['actual_Win32_exit'] = code.value
            except BaseException as exit_error:
                value['exit_capture_failure'] = repr(exit_error)
    value['ended_utc'] = datetime.now(timezone.utc).isoformat()
    value['log'] = stat(log) if log.is_file() else None
    save(receipt, value)
    need(value['invocation_failure'] is None and value['actual_Popen_wait_exit'] ==
         value['actual_Win32_exit'] == 0, 'Actual tool failed; preserve ' + str(receipt))
    return stat(receipt), payload


def section(path, source):
    lines = path.read_text(encoding='utf-16').splitlines()
    positions = [i for i, line in enumerate(lines) if line.startswith('^') and
                 key(line[1:]) == key(source)]
    need(len(positions) == 1, 'One authoritative mDBC tlog section required')
    start = positions[0] + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith('^')), len(lines))
    return lines[start:end]


def replace_option(argv, prefix, replacement):
    slots = [i for i, arg in enumerate(argv) if arg.lower().startswith(prefix.lower())]
    need(len(slots) == 1, 'One authoritative option required: ' + prefix)
    revised = list(argv)
    revised[slots[0]] = prefix + str(replacement)
    return revised


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Root review and exact build-only admission required')
    need(os.name == 'nt', 'This authoritative MSVC builder is Windows-only')
    ad, base, source = read(ADMISSION), read(BASE), read(SOURCE)
    need(ad['authorized'] and ad['allowed_stage'] == TAG and ad['root_thread_id'] == THREAD
         and ad['build_only'] and not ad['automatic_solver'] and not ad['automatic_reader']
         and ad['execution_script'] == stat(SCRIPT) and ad['note'] == stat(NOTE)
         and ad['source_build'] == stat(BASE) and ad['source_candidate'] == stat(SOURCE),
         'Exact current-root single-TU build-only admission required')
    need(base['passed'] and base['configuration'] == 'DebugCPU' and base['canonical_unchanged']
         and base['consumed_stats_unchanged'] and base['source_candidate'] == stat(SOURCE),
         'Current isolated authoritative CPU Debug build required')
    call = read(bind(base['call'])['path'])
    need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
         and call.get('ownership_failure') is None, 'Actual default Debug build exits required')
    need('/p:VCToolsVersion=14.36.32532' in base['arguments']
         and call['child']['argv'] == base['arguments'],
         'Actual authoritative Debug build argv/toolset differs')
    base_admission = L / 'c08_h18_wall_c_retry_CPU_Debug_r1.admission.json'
    admission = read(base_admission)
    canonical = bind(admission['canonical_before'])
    original_program = bind(base['program'])
    intdir = Path(base['intermediate']).resolve()
    need(intdir == Path(r'C:/Users/syosh/AppData/Local/Temp/c08_wall_c_retry_cpu_debug_r1'),
         'Only the reviewed new Debug IntDir is admitted')
    tlog = intdir / 'DualSPHysics.tlog'
    cl_tlog, link_tlog, reads_tlog, link_reads = [tlog / f for f in
        ('CL.command.1.tlog', 'link.command.1.tlog', 'CL.read.1.tlog', 'link.read.1.tlog')]
    original_cpu = S / 'source/JSphCpu_mdbc.cpp'
    cl_lines = section(cl_tlog, original_cpu)
    need(len(cl_lines) == 1, 'One original CL recipe required')
    ca_original = windows_args(cl_lines[0])
    link_lines = link_tlog.read_text(encoding='utf-16').splitlines()
    need(link_lines[0].startswith('^') and not any(q.startswith('^') for q in link_lines[1:]),
         'One original link invocation required')
    la_original = windows_args(' '.join(link_lines[1:]))
    original_objects = [Path(q).resolve() for q in la_original if q.lower().endswith('.obj')]
    anchor_objects = link_lines[0][1:].split('|')
    need(len(original_objects) == len(set(map(key, original_objects))) == 87
         and set(map(key, original_objects)) == set(map(key, anchor_objects))
         and sum(q.name.lower() == 'main.obj' for q in original_objects) == 1,
         'Exactly87 original objects including public main required')
    replaced = [q for q in original_objects if q.name.lower() == 'jsphcpu_mdbc.obj']
    need(len(replaced) == 1 and replaced[0].parent == intdir, 'One original mDBC object required')
    retained = [q for q in original_objects if q != replaced[0]]
    need(all(q.parent == intdir for q in original_objects), 'No external object substitution allowed')
    need(all(q in ca_original for q in ['/c', '/Od', '/MTd', '/fp:precise', '/openmp', '/RTC1'])
         and not any(q.lower().startswith(('/i', '/fi')) for q in ca_original)
         and sum(key(q) == key(original_cpu) for q in ca_original) == 1,
         'Original precise Debug CL options/source/include search changed')
    setup_dir = Path(os.environ['TEMP']).resolve() / TAG
    need(' ' not in str(setup_dir), 'The single environment command directory must have no spaces')
    paths = [OUT, CHECK, setup_dir] + [L / (TAG + suffix) for suffix in
        ('.environment.call.json', '.environment.log', '.compile.call.json', '.compile.log',
         '.link.call.json', '.link.log')]
    need(not any(q.exists() for q in paths), 'Existing complete or partial baseline protected')
    consumed = [stat(q) for q in (SCRIPT, NOTE, ADMISSION, BASE, SOURCE, base_admission,
        cl_tlog, link_tlog, reads_tlog, link_reads, BIN / 'cl.exe', BIN / 'link.exe',
        VC / 'Auxiliary/Build/vcvarsall.bat')]
    consumed += [original_program, canonical, base['call']] + [stat(q) for q in original_objects]
    proofs = []
    before_cpu = None
    for member in source['files']:
        entries = [bind(member[k]) for k in
                   ('original_source_copy', 'candidate_source', 'current_public_stat')]
        consumed += entries
        before = Path(entries[0]['path']).read_bytes()
        candidate = Path(entries[1]['path']).read_bytes()
        public = Path(entries[2]['path']).read_bytes()
        need(candidate == public, 'Current public member differs from admitted candidate')
        inverse = candidate.decode('utf-8')
        edits = member['inverse_proof']['replacements']
        for edit in reversed(edits):
            need(inverse.count(edit['candidate']) == 1, 'Unique member inverse missing')
            inverse = inverse.replace(edit['candidate'], edit['original'], 1)
        need(inverse.encode('utf-8') == before, 'Inverse does not restore all before member bytes')
        proofs.append(dict(filename=member['filename'], candidate_public_bytes_equal=True,
                           exact_inverse_before_bytes=True, replacements=len(edits)))
        if member['filename'] == 'JSphCpu_mdbc.cpp':
            before_cpu = before
    need(len(proofs) == 2 and {q['filename'] for q in proofs} ==
         {'JSphCpu_mdbc.cpp', 'JSphGpu_mdbc_ker.cuh'} and before_cpu is not None,
         'Exactly two admitted member proofs required')
    # The project targets SDK8.1 and uses UCRT10.0.10240.0. Do not let vcvars
    # silently select a newer, different header/library closure for this TU.
    original_headers = [Path(q).resolve() for q in section(reads_tlog, original_cpu)]
    need(original_headers and len(set(map(key, original_headers))) == len(original_headers),
         'One unique original header-read set required')
    consumed += [stat(q) for q in original_headers]
    libraries = []
    for line in link_reads.read_text(encoding='utf-16').splitlines():
        if not line.startswith('^') and line.lower().endswith('.lib'):
            libraries.append(stat(line))
    libraries = list({key(q['path']): q for q in libraries}.values())
    need(libraries and any(Path(q['path']).name.lower() == 'dsphchrono.lib' for q in libraries),
         'Actual original linker library-read closure required')
    consumed += libraries
    dependency_text = '\n'.join([str(q) for q in original_headers] + [q['path'] for q in libraries])
    versions = set(re.findall(r'(?i)windows kits[\\/]10[\\/](?:include|lib)[\\/](10\.[0-9]+\.[0-9]+\.[0-9]+)', dependency_text))
    need(versions == {UCRT_VERSION} and 'windows kits\\8.1\\' in dependency_text.lower(),
         'Original read/link closure must retain SDK8.1 plus the unique old UCRT')
    msvc = VC / 'Tools/MSVC/14.36.32532'
    kits = Path(os.environ['ProgramFiles(x86)']) / 'Windows Kits'
    sdk81, ucrt = kits / '8.1', kits / '10'
    atl_headers = any('\\atlmfc\\' in str(q).lower() for q in original_headers)
    atl_libraries = any('\\atlmfc\\' in q['path'].lower() for q in libraries)
    include_roots = [msvc / 'include'] + ([msvc / 'atlmfc/include'] if atl_headers else [])
    include_roots += [sdk81 / 'Include/shared', sdk81 / 'Include/um', sdk81 / 'Include/winrt',
                      ucrt / 'Include' / UCRT_VERSION / 'ucrt']
    lib_roots = [msvc / 'lib/x64'] + ([msvc / 'atlmfc/lib/x64'] if atl_libraries else [])
    lib_roots += [sdk81 / 'Lib/winv6.3/um/x64', ucrt / 'Lib' / UCRT_VERSION / 'ucrt/x64']
    need(all(q.is_dir() for q in include_roots + lib_roots),
         'The original mixed SDK8.1/UCRT10240 roots must exist; no alternative SDK search')
    system_headers = [q for q in original_headers if not key(q).startswith(key(S / 'source') + os.sep)]
    need(all(any(key(q).startswith(key(root) + os.sep) for root in include_roots)
             for q in system_headers), 'An original system header is outside the declared mixed roots')
    library_by_name = {}
    for entry in libraries:
        library_by_name.setdefault(Path(entry['path']).name.lower(), []).append(entry)
    prior = read(PRIOR_FAILED_BUILD)
    need(prior['passed'] is False and prior['compile_invocations'] == 0
         and prior['link_invocations'] == 0 and len(prior['calls']) == 1,
         'Original r1 was an environment-only failure, not a compiler or solver result')
    prior_call_entry = bind(prior['calls'][0])
    prior_call = read(prior_call_entry['path'])
    need(prior_call['actual_Popen_wait_exit'] == prior_call['actual_Win32_exit'] == 1
         and prior_call['invocation_failure'] is None,
         'Preserve the genuine r1 cmd parsing exit1/1')
    prior_failure = dict(build=stat(PRIOR_FAILED_BUILD), environment_call=prior_call_entry,
        environment_log=bind(prior_call['log']), actual_exits=[1, 1],
        compiler_or_linker_started=False, original_r1_unchanged=True)
    consumed += [prior_failure[k] for k in ('build', 'environment_call', 'environment_log')]
    consumed = list({key(q['path']): q for q in consumed}.values())
    calls, compile_count, link_count = [], 0, 0
    try:
        OUT.mkdir()
        frozen = OUT / 'frozen'
        frozen.mkdir()
        private = frozen / 'JSphCpu_mdbc.cpp'
        private.write_bytes(before_cpu)
        need(private.read_bytes() == before_cpu, 'Private before source copy differs')
        obj, compiler_pdb = OUT / 'JSphCpu_mdbc.before.obj', OUT / 'vc143.before.pdb'
        exe = OUT / 'DualSPHysics5.2CPU_win64_debug.exe'
        ca = [str(private) if key(q) == key(original_cpu) else q for q in ca_original]
        ca = replace_option(ca, '/Fo', obj)
        ca = replace_option(ca, '/Fd', compiler_pdb)
        ca.append('/I' + str(S / 'source'))
        source_dependencies = OUT / 'before.sourceDependencies.json'
        ca += ['/sourceDependencies', str(source_dependencies)]
        la = [str(obj) if key(q) == key(replaced[0]) else q for q in la_original]
        for prefix, path in [('/OUT:', exe), ('/PDB:', OUT / 'baseline.pdb'),
                             ('/IMPLIB:', OUT / 'baseline.lib'),
                             ('/LTCGOUT:', OUT / 'baseline.iobj')]:
            la = replace_option(la, prefix, path)
        library_redirects = []
        for index, arg in enumerate(la):
            if not arg.startswith('/') and arg.lower().endswith('.lib'):
                matches = library_by_name.get(Path(arg).name.lower(), [])
                need(len(matches) == 1, 'Original library token has no unique read-bound file: ' + arg)
                la[index] = matches[0]['path']
                library_redirects.append(dict(original_token=arg, actual_file=matches[0],
                    purpose='Same read-bound library identity; remove ambiguous bare-name search'))
        linked = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        need(linked == [obj if q == replaced[0] else q for q in original_objects]
             and len(linked) == 87, 'Original link order or one-object substitution changed')
        need(all(stat(q['path']) == q for q in consumed), 'Input changed before tool calls')
        setup = str(VC / 'Auxiliary/Build/vcvarsall.bat')
        setup_dir.mkdir()
        setup_cmd = setup_dir / 'env.cmd'
        command = ('@echo off\r\ncall "' + setup + '" x64 -vcvars_ver=14.36 >nul\r\n'
                   'if errorlevel 1 exit /b %errorlevel%\r\nset\r\n')
        with setup_cmd.open('xb') as stream:
            stream.write(command.encode('ascii'))
        consumed.append(stat(setup_cmd))
        setup_argv = [str(Path(os.environ['SystemRoot']) / 'System32/cmd.exe'),
                      '/d', '/c', str(setup_cmd)]
        environment_call, payload = invoke(TAG + '.environment', setup_argv, S / 'VS',
                                           os.environ.copy(), capture_stdout=True)
        calls.append(environment_call)
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in
            (q.split('=', 1) for q in payload.decode('mbcs').splitlines()
             if '=' in q and not q.startswith('=')))
        need(env.get('VCTOOLSVERSION') == '14.36.32532', 'Exact original MSVC toolset required')
        for name in ('CL', '_CL_', 'LINK', '_LINK_'):
            env.pop(name, None)
        env.update(INCLUDE=';'.join(map(str, include_roots)), LIB=';'.join(map(str, lib_roots)),
            WINDOWSSDKDIR=str(sdk81) + '\\', WINDOWSSDKVERSION='8.1\\',
            WINDOWSSDKLIBVERSION='winv6.3\\', UNIVERSALCRTSDKDIR=str(ucrt) + '\\',
            UCRTVERSION=UCRT_VERSION)
        need(env['INCLUDE'].split(';') == list(map(str, include_roots))
             and env['LIB'].split(';') == list(map(str, lib_roots))
             and env['WINDOWSSDKVERSION'] == '8.1\\' and env['UCRTVERSION'] == UCRT_VERSION,
             'Explicit mixed header/library environment differs')
        compile_count = 1
        entry, _ = invoke(TAG + '.compile', [str(BIN / 'cl.exe'), *ca], S / 'VS', env)
        calls.append(entry)
        dependencies = read(source_dependencies)
        data = dependencies.get('Data')
        need(isinstance(data, dict) and key(data['Source']) == key(private)
             and isinstance(data['Includes'], list)
             and not data.get('ImportedModules') and not data.get('ImportedHeaderUnits'),
             'Actual sourceDependencies must describe this one native before TU')
        actual_headers = [Path(q).resolve() for q in data['Includes']]
        header_check = dict(original_count=len(original_headers), actual_count=len(actual_headers),
            original_headers=[stat(q) for q in original_headers],
            actual_headers=[stat(q) for q in actual_headers],
            missing=sorted(set(map(key, original_headers)) - set(map(key, actual_headers))),
            extra=sorted(set(map(key, actual_headers)) - set(map(key, original_headers))),
            only_source_location_changed=True, original_cpp=str(original_cpu), actual_cpp=str(private),
            original_include_search_order_recovered=False,
            search_order_note='Explicit roots follow the declared mixed policy; original environment order is not stored in tlog. Actual full include set, not an invented old search order, is checked.')
        header_check['passed'] = not header_check['missing'] and not header_check['extra']
        save(OUT / 'before.header_closure.json', header_check)
        need(header_check['passed'], 'Actual system/project header set differs; preserve the one compile and do not link or retry')
        link_count = 1
        entry, _ = invoke(TAG + '.link', [str(BIN / 'link.exe'), *la], S / 'VS', env)
        calls.append(entry)
        need(obj.is_file() and exe.is_file(), 'New before object/executable missing')
        need(all(stat(q['path']) == q for q in consumed), 'Input/object changed during baseline build')
        save(CHECK, dict(stage=TAG, passed=True, build_only=True, configuration='DebugCPU',
            base_build=stat(BASE), source_candidate=stat(SOURCE), root_admission=stat(ADMISSION),
            prior_failed_environment_setup=prior_failure, environment_command_script=stat(setup_cmd),
            program=stat(exe), private_before_source=stat(private), new_before_object=stat(obj),
            original_replaced_object=stat(replaced[0]), retained_objects=[stat(q) for q in retained],
            original_CL_arguments=ca_original, actual_CL_arguments=ca,
            original_link_arguments=la_original, actual_link_arguments=la,
            member_byte_proofs=proofs, actual_link_objects=87, retained_objects_count=86,
            original_main_retained=True, public_source_written=False, canonical_unchanged=True,
            actual_link_library_stats=libraries,
            actual_library_path_redirects=library_redirects,
            header_closure=stat(OUT / 'before.header_closure.json'),
            source_dependencies=stat(source_dependencies),
            mixed_environment={k: env[k] for k in ('INCLUDE', 'LIB', 'WINDOWSSDKDIR',
                'WINDOWSSDKVERSION', 'WINDOWSSDKLIBVERSION', 'UNIVERSALCRTSDKDIR', 'UCRTVERSION')},
            selected_tool_host='Hostx64/x64', original_MSBuild_CL_host_architecture_proven=False,
            tool_host_caveat='Same14.36.32532 target toolset is declared; original MSBuild CL host binary was not captured, so exact host compiler identity is not claimed. Native before/after byte comparison remains separate.',
            source_and_original_objects_stat_unchanged=True, consumed=consumed, calls=calls,
            environment_stdout_not_persisted=True, compile_invocations=1, link_invocations=1,
            program_invocations=0, help_invocations=0, solver_invocations=0, reader_invocations=0,
            SHA_scans=0, physical_acceptance=False, automatic_next_job=False))
    except BaseException as error:
        actual = [stat(L / (TAG + suffix)) for suffix in
                  ('.environment.call.json', '.compile.call.json', '.link.call.json')
                  if (L / (TAG + suffix)).is_file()]
        if not CHECK.exists():
            save(CHECK, dict(stage=TAG, passed=False, first_failure=repr(error), calls=actual,
                prior_failed_environment_setup=prior_failure,
                consumed=consumed, partial_outputs_preserved=True, compile_invocations=compile_count,
                link_invocations=link_count, program_invocations=0, solver_invocations=0,
                reader_invocations=0, SHA_scans=0, physical_acceptance=False,
                automatic_retry=False, automatic_next_job=False))
        raise


if __name__ == '__main__':
    main()
