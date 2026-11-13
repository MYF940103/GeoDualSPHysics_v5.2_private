"""Compile only the affine-FS CPU fixture; replace restored DebugCPU main and never run."""
import argparse, ctypes, os, shutil, subprocess
from pathlib import Path
import c08_h18_wend_matrix_r1 as matrix

T, L = matrix.T, matrix.L
S = T.parents[3] / 'src'
TAG = 'c08_fs_affine_cpu_r1'
OUT = T / 'outputs' / (TAG + '_build')
SOURCE = T / 'support' / (TAG + '.cpp')
NOTE = T / 'notes' / (TAG + '_build.md')
BASE = L / 'c08_h18_restore_DebugCPU_r1.build.json'
need, read, stat, bind, save, invoke = matrix.need, matrix.read, matrix.stat, matrix.bind, matrix.save, matrix.invoke


def arguments(line):
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW('tool.exe ' + line, ctypes.byref(count))
    need(bool(pointer), 'Cannot parse fresh authoritative command')
    try:
        return [pointer[i] for i in range(1, count.value)]
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(ctypes.cast(pointer, ctypes.c_void_p))


def blocks(path):
    result = []
    for line in path.read_text(encoding='utf-16').splitlines():
        if line.startswith('^'):
            result.append((line[1:].split('|'), []))
        elif line.strip():
            need(bool(result), 'Command text without an input block')
            result[-1][1].append(line)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until root full-read and one explicit CPU build')
    check = L / (TAG + '.build.json')
    need(not OUT.exists() and all(not (L / (TAG + q)).exists() for q in
         ('.build.json', '.compile.call.json', '.compile.log', '.link.call.json', '.link.log')),
         'Existing complete or partial fixture build protected')
    before, calls = [], []
    try:
        baseline = read(BASE)
        need(baseline['passed'] and baseline['configuration'] == 'DebugCPU' and baseline['restored_original_source']
             and baseline['actual_typed_exit_code'] == baseline['actual_Win32_exit'] == 0
             and baseline['actual_link_objects'] == 87 and baseline['consumed_stats_unchanged']
             and baseline['canonical_programs_unchanged'], 'Closed restored DebugCPU build required')
        build_call = read(bind(baseline['actual_call'])['path'])
        need(build_call['actual_Popen_wait_exit'] == build_call['actual_Win32_exit'] == 0
             and '/p:VCToolsVersion=14.36.32532' in build_call['arguments'], 'Actual restored MSVC14.36 build required')
        roots = [q.split('=', 1)[1] for q in build_call['arguments'] if q.startswith('/p:IntDir=')]
        need(len(roots) == 1, 'One actual restored IntDir required')
        intdir = Path(roots[0]).resolve()
        expected = Path(os.environ['TEMP']).resolve() / 'c08_restore_cpu_r1/DebugCPU/int'
        need(intdir == expected.resolve(), 'Restored tlog tree differs from the admitted fresh tree')
        tlog = intdir / 'DualSPHysics.tlog'
        cl_tlog, link_tlog, libraries_tlog = (tlog / q for q in
                                            ('CL.command.1.tlog', 'link.command.1.tlog', 'link.read.1.tlog'))
        mains = [q for q in blocks(cl_tlog) if len(q[0]) == 1 and Path(q[0][0]).name.lower() == 'main.cpp']
        links = blocks(link_tlog)
        need(len(mains) == len(links) == 1, 'Exactly one fresh main CL block and one link block required')
        ca, la = arguments(' '.join(mains[0][1])), arguments(' '.join(links[0][1]))
        objects = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        originals = [q for q in objects if q.name.lower() == 'main.obj']
        need(len(objects) == len(set(objects)) == 87 and len(originals) == 1
             and all(q.parent == intdir for q in objects), 'Exactly87 original public objects including one main required')
        retained = [q for q in objects if q != originals[0]]
        harness = (SOURCE.parent / '../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_p2_feedback_harness_r1.cpp').resolve()
        headers = ('JSph.h', 'JSphCpu.h', 'JSphCpuSingle.h', 'JSphCfgRun.h', 'DualSphDef.h', 'TypesDef.h',
                   'JArraysCpu.h', 'JDsTimersCpu.h', 'JDsDcellDef.h', 'JAppInfo.h', 'JLog2.h', 'FunSphKernel.h')
        before = [stat(q) for q in (BASE, SOURCE, NOTE, Path(__file__), Path(matrix.__file__),
                                   harness, cl_tlog, link_tlog, libraries_tlog)]
        before += [bind(baseline[q]) for q in ('program', 'source_capture', 'source_archive', 'actual_call')]
        before += [stat(q) for q in objects] + [stat(S / 'source' / q) for q in headers]
        libraries = [Path(q.strip('"')).resolve() for q in libraries_tlog.read_text(encoding='utf-16').splitlines()
                     if not q.startswith('^') and q.lower().endswith('.lib')]
        need(libraries and all(q.is_file() for q in libraries), 'Fresh resolved original library closure required')
        before += [stat(q) for q in libraries]
        obj, exe = OUT / 'fixture.obj', OUT / 'C08FsAffineCpuR1_win64.exe'
        source_indices = [i for i, q in enumerate(ca) if Path(q).name.lower() == 'main.cpp']
        need(len(source_indices) == 1 and '/MTd' in ca and '/Od' in ca and '/RTC1' in ca
             and '/Zi' in ca and '/fp:precise' in ca and '/openmp' in ca
             and not any('_WITHGPU' in q or q.lower().startswith('/std:') for q in ca),
             'Fresh CPU Debug ABI/FP/flags differ')
        ca[source_indices[0]] = str(SOURCE)
        for prefix, target in (('/fo', obj), ('/fd', OUT / 'fixture_compile.pdb')):
            indices = [i for i, q in enumerate(ca) if q.lower().startswith(prefix)]
            need(len(indices) == 1, 'One original compiler output token required: ' + prefix)
            ca[indices[0]] = prefix + str(target)
        ca += ['/std:c++17', '/D_HAS_STD_BYTE=0', '/I' + str(S / 'source')]
        outputs = {'/out:': exe, '/pdb:': OUT / 'fixture_link.pdb',
                   '/implib:': OUT / 'fixture.lib', '/ltcgout:': OUT / 'fixture.iobj'}
        linked, seen = [], set()
        for value in la:
            if value.lower().endswith('.obj') and Path(value).resolve() == originals[0]:
                value = str(obj)
            for prefix, target in outputs.items():
                if value.lower().startswith(prefix):
                    value = prefix + str(target)
                    seen.add(prefix)
                    break
            linked.append(value)
        final_objects = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        need(seen == set(outputs) and len(final_objects) == 87 and set(final_objects) == set(retained) | {obj.resolve()},
             'Link must contain86 public objects plus only the new fixture entry object')
        runtime_leaves = ('DsphConfig.xml', 'ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll',
                          'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
        runtime = [bind(next(q for q in baseline['runtime'] if Path(q['path']).name == leaf)) for leaf in runtime_leaves]
        before += runtime
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode == 0, 'Matching MSVC setup failed')
        env = {key.upper(): value for key, value in os.environ.items()}
        env.update(q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('='))
        env = {key.upper(): value for key, value in env.items()}
        need(env['VCTOOLSVERSION'] == '14.36.32532', 'Exact restored MSVC version required')
        for key in ('CL', '_CL_'):
            env.pop(key, None)
        env['LIB'] = ';'.join(dict.fromkeys(str(q.parent) for q in libraries))
        cl = Path(env['VCTOOLSINSTALLDIR']) / 'bin/Hostx64/x64/cl.exe'
        link = cl.with_name('link.exe')
        before += [stat(cl), stat(link)]
        matrix.verify(before)
        OUT.mkdir()
        calls.append(invoke(TAG + '.compile', [str(cl), *ca], OUT, env))
        calls.append(invoke(TAG + '.link', [str(link), *linked], S / 'VS', env))
        copied = []
        for entry in runtime:
            destination = OUT / Path(entry['path']).name
            shutil.copy2(entry['path'], destination)
            need(destination.read_bytes() == Path(entry['path']).read_bytes(), 'Restored runtime copy differs')
            copied.append(stat(destination))
        matrix.verify(before)
        save(check, dict(stage=TAG + '.build', passed=True, program=stat(exe), source=stat(SOURCE),
             retained_harness=stat(harness), note=stat(NOTE), source_build=stat(BASE),
             source_capture=baseline['source_capture'], source_archive=baseline['source_archive'],
             replaced_main=stat(originals[0]), fixture_object=stat(obj),
             retained_project_objects=[stat(q) for q in retained], retained_public_objects=86,
             actual_link_objects=87, separately_linked_retained_fixture_objects=0,
             authoritative_CL_tlog=stat(cl_tlog), authoritative_LINK_tlog=stat(link_tlog),
             resolved_library_tlog=stat(libraries_tlog), runtime=copied, calls=calls,
             actual_typed_exit_code=0, actual_Win32_exit=0, consumed=before, consumed_stats_unchanged=True,
             public_source_changed=False, GPU_actions=0, help_invocations=0, fixture_invocations=0,
             solver_invocations=0, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        actual_calls = [stat(L / (TAG + q)) for q in ('.compile.call.json', '.link.call.json')
                        if (L / (TAG + q)).is_file()]
        if not check.exists():
            save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=actual_calls,
                 consumed=before, GPU_actions=0, help_invocations=0, fixture_invocations=0,
                 solver_invocations=0, physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    main()
