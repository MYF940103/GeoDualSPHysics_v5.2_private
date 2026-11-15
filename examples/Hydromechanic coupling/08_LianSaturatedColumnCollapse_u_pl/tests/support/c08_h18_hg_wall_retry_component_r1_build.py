"""Build only the ten-fixture host component with the separately sealed retry CUDA object."""
import argparse
import ctypes
import os
import shutil
import subprocess
from pathlib import Path
import c08_h18_wend_matrix_r1 as m

T, L = m.T, m.L
S = T.parents[3] / 'src'
TAG = 'c08_h18_hg_wall_retry_component_r1'
SCRIPT = Path(__file__).resolve()
CPP = T / 'support' / (TAG + '.cpp')
NOTE = T / 'notes' / (TAG + '_build.md')
COMPONENT_NOTE = T / 'notes' / (TAG + '.md')
BASE = L / 'c08_h18_hg_opt_Release_r1.build.json'
KERNEL = L / 'c08_h18_wall_c_retry_GPU_r1.build.json'
SOURCE = L / 'c08_h18_wall_c_retry_r1.source.json'
OLD_COMPONENT = L / 'c08_h18_hg_wall_packet_component_r2.build.json'
ORIGINAL_PROOF = L / 'c08_h18_hg_wall_packet_component_r2.memcheck.check.json'
OUT = T / 'outputs' / (TAG + '_build')
CHECK = L / (TAG + '.build.json')
ADMISSION = L / (TAG + '.root_build_admission.json')
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'


def windows_args(line):
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    n = ctypes.c_int(); ptr = shell.CommandLineToArgvW('tool.exe ' + line, ctypes.byref(n))
    m.need(bool(ptr), 'Authoritative original Windows command parse failed')
    try: return [ptr[i] for i in range(1, n.value)]
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes, free.restype = [ctypes.c_void_p], ctypes.c_void_p
        free(ctypes.cast(ptr, ctypes.c_void_p))


def copy_fixture(old, before):
    """Copy the sealed902394-byte r2 fixture. Never import/call a rawhex decoder."""
    before += [m.bind(old[key]) for key in ('fixture', 'fixture_metadata')]
    d = m.read(old['fixture_metadata']['path'])
    m.need(d['fixture'] == old['fixture'] and d['Np'] == 6805 and d['NpbOk'] == 940
           and d['stage'] == 1 and d['target_native_ID'] == 894 and d['raw_hex_input_calls'] == 0
           and d['original_fixture_raw_hex_input_calls'] == 1 and not d['new_packet_decode']
           and old['fixture']['bytes'] == 902394, 'Closed original r2 fixture extent/provenance required')
    original = Path(old['fixture']['path']); target = OUT / 'fixture.bin'
    m.need(not target.exists(), 'Existing new fixture protected'); shutil.copy2(original, target)
    m.need(target.read_bytes() == original.read_bytes(), 'Copied original fixture bytes differ')
    metadata = OUT / 'fixture.json'
    m.save(metadata, dict(stage=TAG + '.fixture_copy', fixture=m.stat(target),
        adopted_fixture=old['fixture'], adopted_description=old['fixture_metadata'], adopted_build=m.stat(OLD_COMPONENT),
        original_actual_failed_run=d['actual_failed_run'], original_raw_hex_decoder=d['raw_hex_input_decoder'],
        raw_hex_input_calls=0, new_packet_decode=False, original_fixture_raw_hex_input_calls=1,
        Np=6805, Npb=1805, NpbOk=940, target_native_ID=894, stage1_only=True,
        fixture_parameters_defined_in_CPP=True, fixture_parameters_changed_by_builder=False,
        physical_acceptance=False, SHA_scans=0))
    return m.stat(target), m.stat(metadata)


def build():
    intdir = Path(os.environ['TEMP']) / TAG
    m.need(' ' not in str(intdir) and not intdir.exists() and not OUT.exists() and not CHECK.exists()
           and all(not (L / (TAG + suffix)).exists() for suffix in
                   ('.compile.call.json', '.compile.log', '.link.call.json', '.link.log')),
           'Existing complete/partial component or fixture protected; no retry')
    before, calls = [], []
    try:
        ad = m.read(ADMISSION)
        m.need(ad['authorized'] and ad['allowed_stage'] == TAG and ad['execution_script'] == m.stat(SCRIPT)
               and ad['component_source'] == m.stat(CPP) and ad['component_note'] == m.stat(COMPONENT_NOTE)
               and ad['note'] == m.stat(NOTE) and ad['source_build'] == m.stat(BASE)
               and ad['candidate_build'] == m.stat(KERNEL) and ad['candidate_source'] == m.stat(SOURCE)
               and ad['original_component_build'] == m.stat(OLD_COMPONENT) and ad['original_kernel_proof'] == m.stat(ORIGINAL_PROOF)
               and ad['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == THREAD
               and ad['pack_and_build_only'] and not ad['automatic_component'] and not ad['automatic_solver']
               and not ad['automatic_reader'], 'Exact separate current-root component-build-only admission required')
        b, g, source, old, proof = [m.read(q) for q in (BASE, KERNEL, SOURCE, OLD_COMPONENT, ORIGINAL_PROOF)]
        m.need(b['passed'] and b['configuration'] == 'Release' and b['consumed_stats_unchanged']
               and b['actual_link_objects'] == 114 and b['original_physical_CUDA_objects_retained'],
               'Actual original schema2 object source required')
        m.need(g['passed'] and g['configuration'] == 'Release' and g['consumed_stats_unchanged']
               and g['actual_link_objects'] == 114 and g['retained_objects_count'] == 113
               and g['recompiled_physical_CUDA_objects'] == 1 and g['compile_invocations'] == g['link_invocations'] == 1
               and g['candidate_source_record'] == m.stat(SOURCE) and g['exact_inverse_original_member_bytes']
               and g['GPU_main_TU_bytes_unchanged'] and g['compiled_changed_member'] == 'JSphGpu_mdbc_ker.cuh'
               and g['numerical_C_quality_retry'] and g['original_guards_unchanged']
               and g['host_fault_capture_retained'] and g['no_GPU_printf_added']
               and not g['private_HG_Node_material_recompiled'] and not g['physical_acceptance'],
               'Separate sealed candidate CUDA build required; not old/Debug/printf CUDA')
        m.need(source['candidate_applied'] and source['requires_build_and_component_validation']
               and source['root_original_kernel_proof'] == m.stat(ORIGINAL_PROOF)
               and source['public_modified_files'] == ['JSphCpu_mdbc.cpp', 'JSphGpu_mdbc_ker.cuh']
               and source['original_guards_unchanged'] and not source['physical_acceptance']
               and proof['passed'] and proof['memcheck_zero_errors_and_leaks']
               and proof['build'] == m.stat(OLD_COMPONENT) and proof['baseline_native_ID'] == 894
               and proof['baseline_aggregate_invalid'] == 690 and proof['identity_aggregate_invalid'] == 6805
               and proof['target_failure_depends_on_C_field'] and proof['geometry_and_J_inputs_unchanged'],
               'Root two-source inverse provenance and original-kernel causal proof required')
        m.need(old['passed'] and old['consumed_stats_unchanged'] and old['raw_hex_input_calls'] == 0
               and old['adopted_fixture'] and old['actual_link_objects'] == 113
               and old['original_Release_CUDA_retained'] and not old['physical_acceptance'],
               'Original completed r2 component fixture source required')
        before = [m.stat(q) for q in (SCRIPT, CPP, NOTE, COMPONENT_NOTE, ADMISSION, BASE, KERNEL, SOURCE, OLD_COMPONENT, ORIGINAL_PROOF)]
        before += [m.bind(b[key]) for key in ('program', 'source_capture', 'source_archive', 'baseline_source_capture',
                                             'original_link_recipe', 'original_host_recipe')]
        before += [m.bind(q) for q in b['fresh_original_objects']]
        before += [m.bind(g[key]) for key in ('program', 'source_capture', 'source_archive', 'source_diff',
                                             'replacement_physical_object', 'original_replaced_physical_object')]
        before += [m.bind(q) for q in g['frozen_sources'] + g['runtime']]
        before += [m.bind(old['program']), m.bind(proof['actual_call']), m.bind(proof['completion'])]
        before += [m.bind(source[key]) for key in ('transform_script', 'transform_note')]
        for row in source['files']:
            m.need(row['inverse_proof']['exact_inverse_original_bytes'], 'Both source inverse proofs required')
            before += [m.bind(row[key]) for key in ('original_source_copy', 'candidate_source', 'current_public_stat', 'diff')]
            m.need(Path(row['candidate_source']['path']).read_bytes() == Path(row['current_public_stat']['path']).read_bytes(),
                   'Root-applied public/captured candidate bytes differ')
        m.need(len(g['frozen_sources']) == 276 and len(g['runtime']) == 9, 'Candidate276-source/9runtime extent required')
        for ref in g['calls'] + old['calls']:
            before.append(m.bind(ref)); actual = m.read(ref['path'])
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0
                   and actual['ownership_failure'] is None, 'Actual owned candidate/original-component build exits required')
        physical = [q for q in b['fresh_original_objects'] if Path(q['path']).name.lower() == 'jsphgpu_ker.cu.obj']
        m.need(len(physical) == 1 and physical[0] == g['original_replaced_physical_object'],
               'Candidate object must replace this exact original schema2 physical CUDA')
        newcu = Path(g['replacement_physical_object']['path']).resolve()
        actual_gpu_link = m.read(g['calls'][-1]['path'])
        m.need(actual_gpu_link['child']['argv'] == [actual_gpu_link['program'], *actual_gpu_link['arguments']]
               == g['actual_link_arguments'] and g['actual_link_inputs'].count(str(newcu)) == 1,
               'Actual candidate link must consume the exact new CUDA object once')
        tlog = Path(b['original_link_recipe']['path']); lines = tlog.read_text(encoding='utf-16').splitlines()
        m.need(sum(q.startswith('^') for q in lines) == 1, 'One authoritative original113 link block required')
        link_args = windows_args(' '.join(q for q in lines if q and not q.startswith('^')))
        objects = [Path(q).resolve() for q in link_args if q.lower().endswith('.obj')]
        declared = {Path(q['path']).resolve() for q in b['fresh_original_objects']}
        main = [q for q in objects if q.name.lower() == 'main.obj']; oldcu = Path(physical[0]['path']).resolve()
        m.need(len(objects) == len(set(objects)) == 113 and set(objects) == declared and len(main) == 1
               and objects.count(oldcu) == 1 and newcu not in objects,
               'Actual schema2 original113/main/CUDA object closure required')
        retained = [newcu if q == oldcu else q for q in objects if q != main[0]]
        m.need(len(retained) == 112 and len(set(retained)) == 112 and newcu in retained,
               'Component requires111 original non-main plus1candidate CUDA object')
        source_root = Path(g['program']['path']).parent / 'frozen/src/source'
        cl_call, link_call = [m.read(q['path']) for q in (b['calls'][1], b['calls'][-1])]
        for ref, actual in [(b['calls'][1], cl_call), (b['calls'][-1], link_call)]:
            before.append(m.bind(ref))
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None,
                   'Actual optimized original host tool recipe must pass')
        cl, link = Path(cl_call['child']['exe']), Path(link_call['child']['exe'])
        m.need(cl.name.lower() == 'cl.exe' and link.name.lower() == 'link.exe'
               and '/14.36.32532/' in cl.as_posix() and '/14.36.32532/' in link.as_posix(), 'Original MSVC14.36 host tools required')
        host_args = list(b['original_GPU_host_command'])
        m.need('/MT' in host_args and '/Zi' in host_args and '/fp:precise' in host_args
               and sum(Path(q).name.lower() == 'jsphgpu.cpp' for q in host_args) == 1
               and not any(q.lower().startswith(('/yu', '/yc', '/gl')) for q in host_args),
               'Original Release /MT /Zi precise nonPCH host recipe required')
        m.verify(before); OUT.mkdir(); intdir.mkdir()
        fixture, fixture_meta = copy_fixture(old, before); before += [fixture, fixture_meta]
        obj, program = intdir / 'component.obj', OUT / (TAG + '.exe')
        cl_args = ['/I' + str(source_root)] + [
            '/Fo' + str(obj) if q.lower().startswith('/fo') else
            '/Fd' + str(intdir / 'component.pdb') if q.lower().startswith('/fd') else
            str(CPP) if Path(q).name.lower() == 'jsphgpu.cpp' else q for q in host_args]
        dependencies = OUT / 'compile.dependencies.json'; cl_args += ['/sourceDependencies', str(dependencies)]
        targets = {'/out:': program, '/pdb:': OUT / (TAG + '.pdb'), '/implib:': OUT / (TAG + '.lib'), '/ltcgout:': intdir / (TAG + '.iobj')}
        linked, seen = [], set()
        for arg in link_args:
            if arg.lower().endswith('.obj'):
                path = Path(arg).resolve()
                if path == main[0]: arg = str(obj)
                elif path == oldcu: arg = str(newcu)
            for prefix, target in targets.items():
                if arg.lower().startswith(prefix): arg = prefix + str(target); seen.add(prefix); break
            linked.append(arg)
        actual_objects = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        m.need(seen == set(targets) and actual_objects == [obj.resolve() if q == main[0] else newcu if q == oldcu else q for q in objects]
               and len(set(actual_objects)) == 113, 'Only main and the unique original CUDA object may be replaced')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'MSVC environment setup failed')
        env = {key.upper(): value for key, value in os.environ.items()}
        env.update((key.upper(), value) for key, value in
                   (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Original MSVC14.36 environment required')
        env['PATH'] = str(cl.parent) + os.pathsep + env.get('PATH', '')
        found = shutil.which('cl.exe', path=env['PATH'])
        m.need(found is not None and Path(found).resolve() == cl.resolve(), 'Actual PATH host compiler differs')
        for key in list(env):
            if key in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'): env.pop(key)
        before += [m.stat(cl), m.stat(link)]
        libdirs = [S / 'VS'] + [(Path(q.split(':', 1)[1]) if Path(q.split(':', 1)[1]).is_absolute()
                   else S / 'VS' / q.split(':', 1)[1]) for q in linked if q.lower().startswith('/libpath:')]
        libdirs += [Path(q) for q in env.get('LIB', '').split(';') if q]
        for arg in linked:
            if arg.lower().endswith('.lib') and not arg.startswith('/'):
                candidates = [Path(arg)] if Path(arg).is_absolute() else [q / arg for q in libdirs]
                leaf = next((q for q in candidates if q.is_file()), None)
                m.need(leaf is not None, 'Original explicit link library absent: ' + arg); before.append(m.stat(leaf))
        m.verify(before)
        for phase, argv, cwd in [('compile', [str(cl), *cl_args], intdir), ('link', [str(link), *linked], S / 'VS')]:
            entry = m.invoke(TAG + '.' + phase, argv, cwd, env=env); calls.append(entry); actual = m.read(entry['path'])
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0
                   and actual['ownership_failure'] is None, 'Actual owned component CL/link exits required')
            if phase == 'compile': before.append(m.stat(obj)); m.verify(before)
        expected_headers = {Path(q['path']).resolve(): q for q in g['frozen_sources']}
        for leaf in m.read(dependencies)['Data']['Includes']:
            path = Path(leaf).resolve()
            if path.is_relative_to(source_root.resolve()):
                m.need(path in expected_headers, 'Unsealed candidate frozen include used'); before.append(m.bind(expected_headers[path]))
        before.append(m.stat(dependencies))
        runtime = []
        for ref in g['runtime']:
            origin = Path(ref['path']); target = OUT / origin.name
            m.need(not target.exists(), 'Existing component runtime leaf protected'); shutil.copy2(origin, target)
            m.need(target.read_bytes() == origin.read_bytes(), 'Runtime copy differs'); runtime.append(m.stat(target))
        m.verify(before)
        m.save(CHECK, dict(stage=TAG + '.build', passed=True, program=m.stat(program), source=m.stat(CPP),
            root_admission=m.stat(ADMISSION), source_build=m.stat(BASE), candidate_build=m.stat(KERNEL),
            candidate_source_record=m.stat(SOURCE), original_component_build=m.stat(OLD_COMPONENT), original_kernel_proof=m.stat(ORIGINAL_PROOF),
            original_source_capture=b['source_capture'], candidate_source_capture=g['source_capture'], candidate_source_archive=g['source_archive'],
            source_root=str(source_root), exact_original_physical_CUDA_object=physical[0], exact_candidate_physical_CUDA_object=g['replacement_physical_object'],
            fixture=fixture, fixture_metadata=fixture_meta, adopted_original_fixture=old['fixture'], raw_hex_input_calls=0, new_packet_decode=False,
            component_host_debug_symbols=True, Release_candidate_CUDA_retained=True, Debug_CUDA_program_claimed=False,
            original_main_object=m.stat(main[0]), retained_non_main_objects=[m.stat(q) for q in retained], new_host_main_object=m.stat(obj),
            original_non_main_objects=111, retained_candidate_CUDA_objects=1, actual_link_objects=113,
            original_host_compile_arguments=host_args, actual_compile_arguments=[str(cl), *cl_args],
            original_link_arguments=[str(link), *link_args], actual_link_arguments=[str(link), *linked],
            fixture_count=10, fixture_parameters_defined_in_CPP=True, fixture_parameters_changed_by_builder=False,
            compile_invocations=1, link_invocations=1, CUDA_compile_invocations=0, device_link_invocations=0,
            calls=calls, runtime=runtime, source_dependencies=m.stat(dependencies), consumed=before, consumed_stats_unchanged=True,
            component_invocations=0, help_invocations=0, solver_invocations=0, native_reader_invocations=0,
            candidate_component_and_physical_review_pending=True, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        if not CHECK.exists():
            actual_calls = [m.stat(L / (TAG + '.' + phase + '.call.json')) for phase in ('compile', 'link')
                            if (L / (TAG + '.' + phase + '.call.json')).exists()]
            m.save(CHECK, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=actual_calls,
                consumed=before, partial_preserved=True, automatic_retry=False, CUDA_compile_invocations=0,
                component_invocations=0, solver_invocations=0, physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Separate current-root copy/build admission required')
    build()
