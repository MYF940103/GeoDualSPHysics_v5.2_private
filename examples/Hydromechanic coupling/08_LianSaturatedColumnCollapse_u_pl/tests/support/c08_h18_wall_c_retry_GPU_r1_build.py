"""Private Release build only: one original CUDA TU with the reviewed C-quality retry."""
import argparse
import ctypes
import difflib
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
import c08_h18_wend_matrix_r1 as m

T, L = m.T, m.L
S = T.parents[3] / 'src'
TAG = 'c08_h18_wall_c_retry_GPU_r1'
SCRIPT = Path(__file__).resolve()
NOTE = T / 'notes' / (TAG + '.md')
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
BASE = L / 'c08_h18_hg_wall_host_capture_r2_Release.build.json'
SOURCE = L / 'c08_h18_wall_c_retry_r1.source.json'
PRE = T / 'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'
MEMBERS = ('JSphCpu_mdbc.cpp', 'JSphGpu_mdbc_ker.cuh')


def windows_args(line):
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW('tool.exe ' + line, ctypes.byref(count))
    m.need(bool(pointer), 'Cannot parse authoritative original Windows NVCC command')
    try:
        return [pointer[i] for i in range(1, count.value)]
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes, free.restype = [ctypes.c_void_p], ctypes.c_void_p
        free(ctypes.cast(pointer, ctypes.c_void_p))


def candidate_sources(before, old_physical):
    """Consume the root-applied two-member record, not a second transformation."""
    source = m.read(SOURCE)
    m.need(source['stage'] == 'c08_h18_wall_c_retry_r1.source' and source['candidate_applied']
           and source['requires_build_and_component_validation'] and not source['physical_acceptance']
           and source['public_modified_files'] == list(MEMBERS) and source['original_guards_unchanged']
           and not source['new_XML_parameters'] and len(source['files']) == 2,
           'Exact root-applied two-member numerical candidate required')
    for key in ('transform_script', 'transform_note', 'root_original_kernel_proof'):
        before.append(m.bind(source[key]))
    original_check = m.read(source['root_original_kernel_proof']['path'])
    m.need(original_check['passed'] and original_check['memcheck_zero_errors_and_leaks']
           and original_check['baseline_aggregate_invalid'] == 690
           and original_check['baseline_native_ID'] == 894
           and original_check['identity_aggregate_invalid'] == 6805
           and original_check['target_failure_depends_on_C_field']
           and original_check['geometry_and_J_inputs_unchanged']
           and not original_check['physical_acceptance'], 'Actual original-kernel A/I causal component required')
    modified, proofs = {}, []
    for row, expected_count in zip(source['files'], (7, 1)):
        name = row['filename']
        m.need(name in MEMBERS and name not in modified, 'Unique admitted candidate member required')
        for key in ('original_source_copy', 'candidate_source', 'diff', 'current_public_stat'):
            before.append(m.bind(row[key]))
        public = Path(row['current_public_stat']['path'])
        m.need(public.resolve() == (S / 'source' / name).resolve(), 'Public candidate identity changed')
        original = Path(row['original_source_copy']['path']).read_bytes()
        changed = Path(row['candidate_source']['path']).read_bytes()
        m.need(public.read_bytes() == changed and (old_physical / name).read_bytes() == original,
               'Candidate/current-public/base-frozen original byte binding differs: ' + name)
        proof = row['inverse_proof']
        m.need(proof['filename'] == name and proof['exact_inverse_original_bytes']
               and proof['replacement_count'] == expected_count
               and len(proof['replacements']) == expected_count
               and proof['candidate_is_numerical_change'] and not proof['output_only']
               and proof['original_geometry_threshold_unchanged'] and proof['original_positive_C_gate_unchanged']
               and not proof['third_fit_added'] and not proof['identity_or_centroid_fallback_added']
               and not proof['nonfinite_reconstructed_Cdet_retry_added']
               and not proof['nonfinite_component_retry_added'] and not proof['invalid_J_retry_added'],
               'Closed inverse/guard derivation required: ' + name)
        restored = changed.decode('utf-8')
        for edit in reversed(proof['replacements']):
            m.need(restored.count(edit['candidate']) == 1, 'Unique inverse replacement absent: ' + name)
            restored = restored.replace(edit['candidate'], edit['original'], 1)
        m.need(restored.encode('utf-8') == original, 'Inverse must restore all actual original bytes: ' + name)
        modified[name] = changed
        proofs.append(dict(filename=name, original_source_copy=row['original_source_copy'],
                          candidate_source=row['candidate_source'], current_public_stat=row['current_public_stat'],
                          inverse_proof=proof))
    m.need(set(modified) == set(MEMBERS), 'Both and only the reviewed members must be overlaid')
    return modified, proofs


def build():
    check, admission = L / (TAG + '.build.json'), L / (TAG + '.root_build_admission.json')
    cap, out = T / 'outputs' / (TAG + '_source'), T / 'outputs' / (TAG + '_build')
    intdir = Path(os.environ['TEMP']) / TAG
    m.need(' ' not in str(intdir) and not intdir.exists() and not cap.exists() and not out.exists()
           and all(not (L / (TAG + suffix)).exists() for suffix in
                   ('.build.json', '.compile.call.json', '.compile.log', '.link.call.json', '.link.log')),
           'Existing complete/partial build protected; no automatic retry')
    before, calls = [], []
    try:
        ad = m.read(admission)
        m.need(ad['authorized'] and ad['configuration'] == 'Release' and ad['allowed_stage'] == TAG
               and ad['execution_script'] == m.stat(SCRIPT) and ad['note'] == m.stat(NOTE)
               and ad['source_build'] == m.stat(BASE) and ad['candidate_source'] == m.stat(SOURCE)
               and ad['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == THREAD
               and ad['build_only'] and not ad['automatic_component'] and not ad['automatic_solver']
               and not ad['automatic_reader'], 'Separate exact current-root build-only admission required')
        b = m.read(BASE)
        m.need(b['passed'] and b['configuration'] == 'Release' and b['consumed_stats_unchanged']
               and b['actual_link_objects'] == 114 and b['retained_original_objects'] == 110
               and b['retained_private_opt_objects'] == 3 and b['recompiled_host_objects'] == 1
               and b['all_original_CUDA_objects_retained'] and b['original_opt_HG_material_objects_retained']
               and b['host_failure_branch_only'] and b['no_GPU_printf']
               and b['exact_inverse_original_mdbc_bytes'] and not b['original_GPU_TU_bytes_changed'],
               'Actual host-capture r2 Release114-object baseline required')
        before = [m.stat(q) for q in (SCRIPT, NOTE, admission, BASE, SOURCE, PRE)]
        before += [m.bind(b[key]) for key in ('program', 'source_capture', 'source_archive', 'source_diff',
                                             'generated_mdbc', 'capture_header', 'original_optimized_build')]
        before += [m.bind(q) for q in b['frozen_sources'] + b['runtime']]
        m.need(len(b['frozen_sources']) == 276 and len(b['runtime']) == 9,
               'Closed276-source and9-runtime baseline extent required')
        for ref in b['calls']:
            before.append(m.bind(ref)); call = m.read(ref['path'])
            m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
                   and call['ownership_failure'] is None, 'Actual owned baseline compile/link exits required')
        original_link = m.read(b['calls'][-1]['path'])
        actual_link_argv = original_link['child']['argv']
        m.need(actual_link_argv == [original_link['program'], *original_link['arguments']]
               == b['actual_link_arguments'], 'Baseline actual argv/receipt link closure differs')
        link, link_args = Path(actual_link_argv[0]), actual_link_argv[1:]
        objects = [Path(q).resolve() for q in link_args if q.lower().endswith('.obj')]
        m.need(len(objects) == len(set(objects)) == 114, 'Exactly114 original ordered unique objects required')
        expected_objects = [Path(q).resolve() for q in b['original_link_arguments'][1:] if q.lower().endswith('.obj')]
        old_mdbc = Path(b['original_replaced_host_object']['path']).resolve()
        capture_obj = Path(b['replacement_host_object']['path']).resolve()
        m.need(expected_objects.count(old_mdbc) == 1
               and objects == [capture_obj if q == old_mdbc else q for q in expected_objects],
               'Actual baseline must be original optimized closure with only its captured mDBC replacement')
        before.append(m.bind(b['replacement_host_object']))
        opt = m.read(b['original_optimized_build']['path'])
        m.need(opt['passed'] and opt['configuration'] == 'Release' and opt['actual_link_objects'] == 114
               and opt['NodeKernel_source_bytes_exact'] and opt['single_material_producer']
               and opt['consumed_stats_unchanged'] and len(opt['new_private_objects']) == 3,
               'Actual unchanged optimized Node/material producer required')
        before.append(m.bind(opt['original_CUDA_recipe_log']))
        before += [m.bind(q) for q in opt['new_private_objects']]
        private = {Path(q['path']).resolve() for q in opt['new_private_objects']}
        replaced = [q for q in objects if q.name.lower() == 'jsphgpu_ker.cu.obj']
        m.need(len(replaced) == 1 and private.issubset(objects) and len(private) == 3
               and replaced[0] not in private and capture_obj in objects and capture_obj not in private,
               'One physicalCUDA replacement; three optimized objects and captured mDBC must remain')
        original_cuda = [q for q in b['original_CUDA_objects']
                         if Path(q['path']).resolve() == replaced[0]]
        m.need(len(original_cuda) == 1, 'Replaced CUDA must be the actual baseline original physical object')
        before.append(m.bind(original_cuda[0]))
        retained = [q for q in objects if q != replaced[0]]
        m.need(len(retained) == 113 and len(set(retained) - private - {capture_obj}) == 109,
               'Required109 original+3optimized+1capture-host retained closure differs')
        before += [m.stat(q) for q in objects]
        old_frozen = Path(b['generated_mdbc']['path']).parents[2]
        old_physical = old_frozen / 'src/source'
        m.need(all(Path(q['path']).resolve().is_relative_to(old_frozen.resolve()) for q in b['frozen_sources']),
               'Baseline frozen member leaves its declared original root')
        modified, derivation = candidate_sources(before, old_physical)
        raw = {name: (old_physical / name).read_bytes() for name in MEMBERS}
        original_log = Path(opt['original_CUDA_recipe_log']['path'])
        nvcc_lines = [q.split(b'>', 1)[1].strip().decode('ascii') for q in original_log.read_bytes().splitlines()
                      if b'nvcc.exe' in q.lower() and b'jsphgpu_ker.cu' in q.lower()]
        m.need(len(nvcc_lines) == 1, 'One authoritative original physical NVCC recipe required')
        original_compile = windows_args(nvcc_lines[0]); nvcc = Path(original_compile[0])
        compile_args = list(original_compile[1:])
        m.need(compile_args.count('-o') == compile_args.count('--keep-dir') == compile_args.count('-ccbin') == 1
               and sum(Path(q).name.lower() == 'jsphgpu_ker.cu' for q in compile_args) == 1
               and all(q in compile_args for q in ('--compile', '--machine', '64', '-cudart', 'static', '-use_fast_math', '-D_WITHGPU'))
               and any('compute_86' in q and 'sm_86' in q for q in compile_args)
               and not any('C08_STAGE_TRACE' in q or 'C08_CAUSAL_TRACE' in q or 'rdc=true' in q
                           or q in ('-dc', '--device-link') for q in compile_args),
               'Original macro-off CUDA11.7/sm86/fast-math single-TU recipe required')
        m.verify(before)
        cap.mkdir(); out.mkdir(); intdir.mkdir(parents=True)
        frozen = out / 'frozen'; physical = frozen / 'src/source'
        copied_sources, archive = [], cap / 'source.zip'
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for ref in b['frozen_sources']:
                origin = Path(ref['path']); rel = origin.relative_to(old_frozen); target = frozen / rel
                m.need(not rel.is_absolute() and '..' not in rel.parts and not target.exists(),
                       'Private frozen leaf is invalid or already exists')
                data = modified[origin.name] if rel.parent.as_posix() == 'src/source' and origin.name in modified else origin.read_bytes()
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
                m.need(target.read_bytes() == data, 'Frozen private member copy differs')
                z.writestr(rel.as_posix(), data); copied_sources.append(m.stat(target))
        m.need(len(copied_sources) == 276
               and (physical / 'JSphGpu_ker.cu').read_bytes() == (old_physical / 'JSphGpu_ker.cu').read_bytes()
               and (physical / 'JSphGpu_mdbc.cpp').read_bytes() == (old_physical / 'JSphGpu_mdbc.cpp').read_bytes()
               and (physical / Path(b['capture_header']['path']).name).read_bytes() == Path(b['capture_header']['path']).read_bytes(),
               'Original GPU main TU, captured host member/header and276-member extent must remain exact')
        diff = cap / 'candidate.diff'
        diff.write_text(''.join(''.join(difflib.unified_diff(raw[name].decode('utf-8').splitlines(True),
            modified[name].decode('utf-8').splitlines(True), fromfile='host_capture_r2/' + name,
            tofile='C_quality_retry/' + name)) for name in MEMBERS), encoding='utf-8')
        capture = cap / 'source.json'
        m.save(capture, dict(stage=TAG + '.source', original_build=m.stat(BASE),
            original_source_capture=b['source_capture'], original_source_archive=b['source_archive'],
            candidate_source_record=m.stat(SOURCE), archive=m.stat(archive), diff=m.stat(diff),
            original_frozen_sources=b['frozen_sources'], source_files=copied_sources, modified_members=list(MEMBERS),
            compiled_changed_member='JSphGpu_mdbc_ker.cuh', uncompiled_CPU_provenance_member='JSphCpu_mdbc.cpp',
            exact_inverse_original_member_bytes=True, derivation=derivation,
            GPU_main_TU_bytes_unchanged=True, captured_host_member_and_header_bytes_unchanged=True,
            public_source_written_by_builder=False, numerical_C_quality_retry=True, output_only=False,
            new_XML_parameters=False, class_or_CTE_ABI_changed=False, threshold_changed=False,
            private_HG_Node_material_source_changed=False, solver_invocations=0, reader_invocations=0,
            physical_acceptance=False, SHA_scans=0))
        before += [m.stat(capture), m.stat(archive), m.stat(diff), *copied_sources]
        obj = intdir / 'JSphGpu_ker.cu.obj'
        pdb_changes = 0
        for index, arg in enumerate(compile_args):
            if index and compile_args[index - 1] == '-Xcompiler':
                compile_args[index], hits = re.subn(r'(?i)(?<!\S)/Fd[^\s]+', lambda _: '/Fd' + str(intdir / 'physical.pdb'), arg)
                pdb_changes += hits
        m.need(pdb_changes == 1, 'Exactly one original host-PDB token required')
        compile_args[compile_args.index('-o') + 1] = str(obj)
        compile_args[compile_args.index('--keep-dir') + 1] = str(intdir)
        compile_args = [str(physical / 'JSphGpu_ker.cu') if Path(q).name.lower() == 'jsphgpu_ker.cu' else q for q in compile_args]
        compile_args.insert(0, '-I' + str(physical))
        program = out / Path(b['program']['path']).name
        outputs = {'/out:': program, '/pdb:': out / (program.stem + '.pdb'),
                   '/implib:': out / (program.stem + '.lib'), '/ltcgout:': intdir / (program.stem + '.iobj')}
        linked, seen = [], set()
        for arg in link_args:
            if arg.lower().endswith('.obj') and Path(arg).resolve() == replaced[0]: arg = str(obj)
            for prefix, target in outputs.items():
                if arg.lower().startswith(prefix): arg = prefix + str(target); seen.add(prefix); break
            linked.append(arg)
        actual_objects = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        m.need(seen == set(outputs) and actual_objects == [obj.resolve() if q == replaced[0] else q for q in objects]
               and len(set(actual_objects)) == 114, 'Only one ordered physicalCUDA replacement plus113 retained is allowed')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'MSVC environment setup failed')
        env = {key.upper(): value for key, value in os.environ.items()}
        env.update((key.upper(), value) for key, value in
                   (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Original MSVC14.36 required')
        ccbin = Path(compile_args[compile_args.index('-ccbin') + 1]); host_cl = ccbin / 'cl.exe'
        m.need(host_cl.is_file() and '/14.36.32532/bin/hostx86/x64/' in host_cl.as_posix().lower(),
               'Unchanged authoritative NVCC HostX86/x64 compiler required')
        env['PATH'] = str(ccbin) + os.pathsep + env.get('PATH', '')
        resolved_cl = shutil.which('cl.exe', path=env['PATH'])
        m.need(resolved_cl is not None and Path(resolved_cl).resolve() == host_cl.resolve(),
               'Actual PATH cl.exe must equal original -ccbin/cl.exe')
        for key in list(env):
            if key in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'): env.pop(key)
        m.need('cuda/v11.7' in nvcc.as_posix().lower() and '/14.36.32532/' in link.as_posix(),
               'Original CUDA/MSVC tools required')
        before += [m.stat(q) for q in (nvcc, link, host_cl)]
        libdirs = [S / 'VS'] + [(Path(q.split(':', 1)[1]) if Path(q.split(':', 1)[1]).is_absolute()
                   else S / 'VS' / q.split(':', 1)[1]) for q in linked if q.lower().startswith('/libpath:')]
        libdirs += [Path(q) for q in env.get('LIB', '').split(';') if q]
        for arg in linked:
            if arg.lower().endswith('.lib') and not arg.startswith('/'):
                candidates = [Path(arg)] if Path(arg).is_absolute() else [q / arg for q in libdirs]
                library = next((q for q in candidates if q.is_file()), None)
                m.need(library is not None, 'Original explicit library missing: ' + arg); before.append(m.stat(library))
        m.verify(before)
        for phase, argv, cwd in [('compile', [str(nvcc), *compile_args], intdir), ('link', [str(link), *linked], S / 'VS')]:
            entry = m.invoke(TAG + '.' + phase, argv, cwd, env=env); calls.append(entry); actual = m.read(entry['path'])
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None,
                   'Actual owned NVCC/link normal exit required')
            if phase == 'compile':
                before.append(m.stat(obj))  # Bind the actual produced object before the link consumes it.
                m.verify(before)
        runtime = []
        for ref in b['runtime']:
            origin = Path(ref['path']); target = out / origin.name
            m.need(not target.exists(), 'Existing private runtime leaf protected'); shutil.copy2(origin, target)
            m.need(target.read_bytes() == origin.read_bytes(), 'Runtime companion copy differs'); runtime.append(m.stat(target))
        m.verify(before)
        m.save(check, dict(stage=TAG + '.build', passed=True, configuration='Release', program=m.stat(program),
            root_admission=m.stat(admission), original_host_capture_build=m.stat(BASE), original_optimized_build=b['original_optimized_build'],
            original_actual_link_call=b['calls'][-1], original_source_capture=b['source_capture'], original_source_archive=b['source_archive'],
            candidate_source_record=m.stat(SOURCE), source_capture=m.stat(capture), source_archive=m.stat(archive), source_diff=m.stat(diff),
            frozen_sources=copied_sources, original_NVCC_recipe=opt['original_CUDA_recipe_log'], original_NVCC_arguments=original_compile,
            actual_compile_arguments=[str(nvcc), *compile_args], original_link_arguments=actual_link_argv, actual_link_arguments=[str(link), *linked],
            actual_link_inputs=[str(q) for q in actual_objects], retained_objects=[m.stat(q) for q in retained],
            original_replaced_physical_object=m.stat(replaced[0]), replacement_physical_object=m.stat(obj),
            retained_capture_host_object=m.stat(capture_obj), retained_private_opt_objects=opt['new_private_objects'],
            retained_original_schema2_objects=109, retained_optimized_objects=3, retained_host_capture_objects=1,
            retained_objects_count=113, recompiled_physical_CUDA_objects=1, actual_link_objects=114,
            compile_invocations=1, link_invocations=1, full_project_builds=0, calls=calls, runtime=runtime,
            unchanged_authoritative_ccbin=m.stat(host_cl), PATH_compiler_equals_ccbin=True,
            GPU_main_TU_bytes_unchanged=True, compiled_changed_member='JSphGpu_mdbc_ker.cuh',
            CPU_candidate_frozen_for_provenance_not_compiled=True, private_HG_Node_material_recompiled=False,
            host_fault_capture_retained=True, no_GPU_printf_added=True, numerical_C_quality_retry=True, output_only=False,
            original_guards_unchanged=True, exact_inverse_original_member_bytes=True, public_source_written_by_builder=False,
            class_or_CTE_ABI_changed=False, new_XML_parameters=False, threshold_changed=False,
            consumed=before, consumed_stats_unchanged=True, helper_program_invocations=0, component_invocations=0,
            help_invocations=0, smoke_invocations=0, solver_invocations=0, reader_invocations=0, VTK_invocations=0,
            original_program_and_PRE_protected=True, candidate_component_and_physical_review_pending=True,
            new_binary_no_feedback_not_yet_proven=True, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        if not check.exists():
            actual_calls = [m.stat(L / (TAG + '.' + phase + '.call.json')) for phase in ('compile', 'link')
                            if (L / (TAG + '.' + phase + '.call.json')).is_file()]
            m.save(check, dict(stage=TAG + '.build', passed=False, configuration='Release', first_failure=str(error),
                calls=actual_calls, consumed=before, partial_artifacts_preserved=True, automatic_retry=False,
                full_project_builds=0, component_invocations=0, help_invocations=0, solver_invocations=0,
                reader_invocations=0, physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Author-only until separate exact root build admission')
    build()
