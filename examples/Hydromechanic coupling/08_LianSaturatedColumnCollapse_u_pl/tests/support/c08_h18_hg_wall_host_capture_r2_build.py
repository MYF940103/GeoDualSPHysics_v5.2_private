"""Author-only host-exception inputs capture; one original mDBC CL TU and link, no CUDA."""
import argparse
import ctypes
import difflib
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
import c08_h18_wend_matrix_r1 as m

T, C, L = m.T, m.C, m.L
S = T.parents[3] / 'src'
TAG = 'c08_h18_hg_wall_host_capture_r2'
SCRIPT = Path(__file__).resolve()
HEADER = T / 'support' / (TAG + '.hpp')
NOTE = T / 'notes' / (TAG + '.md')
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
PRE = T / 'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'
CALL = r'''
      // Failure only: actual aborted-substage inputs, never rejected fitted registers.
      c08wallhost::TryCapture(DirOut,
        {Np,Npb,NpbOk,stage,invalid,static_cast<unsigned long long>(Nstep),TimeStep,DivData,
         unsigned(TKernel),unsigned(MGDIV_Z),DomCellCode,unsigned(Simulate2D),unsigned(PeriActive),unsigned(SlipMode),
         DomPosMin.x,DomPosMin.y,DomPosMin.z,Dp,
         MdbcThreshold,float(MassFluid),RhopZero,KernelH,KernelSize2,PosCellSize,Scell,KWend.awen,KWend.bwen,
         Gravity.x,Gravity.y,Gravity.z,SoilCte.Porosity,SoilCte.PoreWaterRho,1.-double(SoilCte.Porosity),
         SigmaPreg!=NULL,PorePressPreg!=NULL,PoroJPreg!=NULL},
        {Idpg,Codeg,Posxyg,Poszg,PosCellg,Dcellg,PoroJg,CorrMatg,BoundNormalg,BoundModeg});
'''


def windows_args(line):
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    pointer = shell.CommandLineToArgvW('tool.exe ' + line, ctypes.byref(count))
    m.need(bool(pointer), 'Cannot parse original Windows project command')
    try:
        return [pointer[i] for i in range(1, count.value)]
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes, free.restype = [ctypes.c_void_p], ctypes.c_void_p
        free(ctypes.cast(pointer, ctypes.c_void_p))


def private_source(raw):
    original = raw.decode('utf-8')
    nl = '\r\n' if '\r\n' in original else '\n'
    declaration = '#include <cfloat>'
    rejection = '      Run_Exceptioon("GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.");'
    # This exact source suffix proves that the call is after the old host log,
    # within the owned invalid<Np branch and before its unchanged original throw.
    suffix = ('      Log->Printf("DynamicPoreWall rejected: stage=%u sorted_slot=%u native_id=%u step_start=%.17g step=%u B=(%.17g,%.17g,%.17g) normal=(%.9g,%.9g,%.9g)."' + nl
              + '        ,stage,invalid,id,TimeStep,unsigned(Nstep),posxy.x,posxy.y,posz,normal.x,normal.y,normal.z);' + nl + rejection)
    m.need(original.count(suffix) == 1, 'Unique original owned rejection/log suffix absent')
    changes = [
        (declaration, '#include "' + HEADER.name + '"' + nl + declaration),
        (rejection, CALL.strip('\n').replace('\n', nl) + nl + rejection),
    ]
    changed, proof = original, []
    for old, new in changes:
        m.need(changed.count(old) == 1 and new not in changed, 'Unique original host source anchor absent')
        changed = changed.replace(old, new, 1)
        proof.append(dict(original_text=old, replacement_text=new, matches=1))
    inverse = changed
    for old, new in reversed(changes):
        m.need(inverse.count(new) == 1, 'Inverse host source anchor ambiguous')
        inverse = inverse.replace(new, old, 1)
    m.need(inverse.encode('utf-8') == raw, 'Removing include/failure call did not restore every original mDBC byte')
    return changed.encode('utf-8'), proof


def build(configuration):
    label = TAG + '_' + configuration
    basepath = L / ('c08_h18_hg_opt_' + configuration + '_r1.build.json')
    check, admission = L / (label + '.build.json'), L / (label + '.root_build_admission.json')
    cap, out = T / 'outputs' / (label + '_source'), T / 'outputs' / (label + '_build')
    intdir = Path(os.environ['TEMP']) / TAG / configuration
    m.need(' ' not in str(intdir) and not intdir.exists() and not cap.exists() and not out.exists()
           and all(not (L / (label + suffix)).exists() for suffix in
                   ('.build.json', '.compile.call.json', '.compile.log', '.link.call.json', '.link.log')),
           'Existing complete or partial host capture build is protected')
    before, calls = [], []
    try:
        ad = m.read(admission)
        m.need(ad['authorized'] and ad['configuration'] == configuration and ad['allowed_stage'] == label
               and ad['execution_script'] == m.stat(SCRIPT) and ad['header'] == m.stat(HEADER)
               and ad['note'] == m.stat(NOTE) and ad['source_build'] == m.stat(basepath)
               and ad['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == THREAD
               and ad['build_only'] and not ad['automatic_solver'] and not ad['automatic_reader'],
               'Separate exact current-root host-only build admission required')
        b = m.read(basepath)
        m.need(b['passed'] and b['configuration'] == configuration and b['consumed_stats_unchanged']
               and b['actual_link_objects'] == 114 and b['retained_original_objects'] == 111
               and b['private_objects'] == 3 and b['NodeKernel_source_bytes_exact']
               and b['optimization_scope'] == 'block_error_snapshot_and_summary_reuse'
               and b['original_physical_CUDA_objects_retained'] and not b['public_source_changed'],
               'Actual frozen optimized114-object baseline required, never rejected CUDA observer')
        before = [m.stat(q) for q in (SCRIPT, HEADER, NOTE, admission, basepath)]
        before += [m.bind(b[key]) for key in ('program', 'source_capture', 'source_archive',
                    'baseline_source_capture', 'base_cached_source_capture', 'original_host_recipe')]
        before += [m.bind(q) for q in b['private_sources'].values()]
        before += [m.bind(q) for q in b['runtime'] + b['frozen_sources']]
        before.append(m.stat(PRE))
        for entry in b['calls']:
            before.append(m.bind(entry)); actual = m.read(entry['path'])
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0
                   and actual['ownership_failure'] is None, 'Actual optimized build tool exits required')
        link_call = m.read(b['calls'][-1]['path'])
        original_link = link_call['child']['argv']
        m.need(original_link == [link_call['program'], *link_call['arguments']], 'Actual optimized link argv differs')
        link, link_args = Path(original_link[0]), original_link[1:]
        objects = [Path(q).resolve() for q in link_args if q.lower().endswith('.obj')]
        m.need(objects == [Path(q).resolve() for q in b['actual_link_inputs']] and len(set(objects)) == 114,
               'Original optimized114 ordered object closure required')
        replaced = [q for q in objects if q.name.lower() == 'jsphgpu_mdbc.obj']
        private = {Path(q['path']).resolve() for q in b['new_private_objects']}
        m.need(len(replaced) == 1 and len(private) == 3 and private.issubset(objects) and replaced[0] not in private,
               'Replace the separate original mDBC host object only; retain all3opt objects')
        retained = [q for q in objects if q != replaced[0]]
        cuda_objects = [q for q in objects if q.name.lower().endswith('.cu.obj')]
        m.need(len(retained) == 113 and len(set(retained) - private) == 110
               and cuda_objects and all(q in retained for q in cuda_objects), 'All original CUDA objects must be retained')
        before += [m.stat(q) for q in objects]
        cllog = Path(b['original_host_recipe']['path'])
        lines = cllog.read_text(encoding='utf-16').splitlines()
        matches = [i for i, q in enumerate(lines) if q.startswith('^') and Path(q[1:]).name.lower() == 'jsphgpu_mdbc.cpp']
        m.need(len(matches) == 1, 'One authoritative original mDBC CL.tlog block required')
        original_compile = windows_args(lines[matches[0] + 1])
        old_host_call = m.read(b['calls'][1]['path'])
        cl = Path(old_host_call['child']['exe'])
        m.need(cl.name.lower() == 'cl.exe' and '/14.36.32532/' in cl.as_posix()
               and '/14.36.32532/' in link.as_posix(), 'Original actual MSVC14.36 tools required')
        m.need(original_compile.count('/c') == 1 and '/fp:precise' in original_compile
               and sum(q.lower().startswith('/fo') for q in original_compile) == 1
               and sum(q.lower().startswith('/fd') for q in original_compile) == 1
               and sum(Path(q).name.lower() == 'jsphgpu_mdbc.cpp' for q in original_compile) == 1
               and not any(q.lower().startswith(('/yu', '/yc', '/gl')) for q in original_compile),
               'Exact original one-source/nonPCH/nonGL mDBC CL recipe required')
        old_frozen = Path(b['OutDir']) / 'frozen'
        m.need(all(Path(q['path']).resolve().is_relative_to(old_frozen.resolve()) for q in b['frozen_sources']),
               'Frozen source leaf outside declared original root')
        original_mdbc = old_frozen / 'src/source/JSphGpu_mdbc.cpp'
        raw = original_mdbc.read_bytes(); changed, derivation = private_source(raw)
        frozen, archive, diff = out / 'frozen', cap / 'source.zip', cap / 'host_exception_only.diff'
        physical = frozen / 'src/source'
        m.verify(before)
        cap.mkdir(); out.mkdir(); intdir.mkdir(parents=True)
        copied_sources = []
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for entry in b['frozen_sources']:
                origin = Path(entry['path']); rel = origin.relative_to(old_frozen); target = frozen / rel
                m.need(not rel.is_absolute() and '..' not in rel.parts and not target.exists(), 'Invalid or existing private source leaf')
                data = changed if rel.as_posix() == 'src/source/JSphGpu_mdbc.cpp' else origin.read_bytes()
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
                m.need(target.read_bytes() == data, 'Frozen private source copy differs')
                z.writestr(rel.as_posix(), data); copied_sources.append(m.stat(target))
            header = physical / HEADER.name
            m.need(not header.exists(), 'Private header would overwrite an old member')
            header.write_bytes(HEADER.read_bytes()); copied_sources.append(m.stat(header))
            z.writestr('src/source/' + HEADER.name, header.read_bytes())
        diff.write_text(''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True), changed.decode('utf-8').splitlines(True),
            fromfile='actual_opt/JSphGpu_mdbc.cpp', tofile='host_failure_capture/JSphGpu_mdbc.cpp')), encoding='utf-8')
        capture = cap / 'source.json'
        m.save(capture, dict(stage=label + '.source', original_build=m.stat(basepath),
            original_source_capture=b['source_capture'], original_source_archive=b['source_archive'],
            original_frozen_sources=b['frozen_sources'], archive=m.stat(archive), diff=m.stat(diff),
            modified_members=['JSphGpu_mdbc.cpp'], added_members=[HEADER.name], derivation=derivation,
            exact_inverse_original_mdbc_bytes=True, host_failure_branch_only=True,
            original_GPU_TU_bytes_changed=False, public_source_changed=False, class_ABI_changed=False,
            generated_mdbc=m.stat(physical / 'JSphGpu_mdbc.cpp'), capture_header=m.stat(header), source_files=copied_sources,
            normal_path_allocations_or_D2H=False, fault_directory='WallFaultCaptureHostR1',
            failed_fitted_M_C_registers_not_captured=True, actual_slot_C_may_be_unwritten_or_stale=True,
            host_bound_constants_not_direct_GPU_CTE_snapshot=True,
            solver_invocations=0, reader_invocations=0, physical_acceptance=False, SHA_scans=0))
        before += [m.stat(capture), m.stat(archive), m.stat(diff), *copied_sources]
        obj = intdir / 'JSphGpu_mdbc.obj'
        cl_args = ['/I' + str(physical)] + [
            '/Fo' + str(obj) if q.lower().startswith('/fo') else
            '/Fd' + str(intdir / 'mdbc.pdb') if q.lower().startswith('/fd') else
            str(physical / 'JSphGpu_mdbc.cpp') if Path(q).name.lower() == 'jsphgpu_mdbc.cpp' else q
            for q in original_compile]
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
               and len(set(actual_objects)) == 114, 'Only the ordered original mDBC host replacement is permitted')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Original MSVC environment setup failed')
        env = {key.upper(): value for key, value in os.environ.items()}
        env.update((key.upper(), value) for key, value in
                   (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Actual original MSVC14.36 environment required')
        env['PATH'] = str(cl.parent) + os.pathsep + env.get('PATH', '')
        actual_cl = shutil.which('cl.exe', path=env['PATH'])
        m.need(actual_cl is not None and Path(actual_cl).resolve() == cl.resolve(), 'Actual PATH cl.exe must match the original actual host tool')
        for key in list(env):
            if key.upper() in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'): env.pop(key)
        before += [m.stat(cl), m.stat(link)]
        libdirs = [S / 'VS'] + [(Path(q.split(':', 1)[1]) if Path(q.split(':', 1)[1]).is_absolute()
                   else S / 'VS' / q.split(':', 1)[1]) for q in linked if q.lower().startswith('/libpath:')]
        libdirs += [Path(q) for q in env.get('LIB', '').split(';') if q]
        for arg in linked:
            if arg.lower().endswith('.lib') and not arg.startswith('/'):
                candidates = [Path(arg)] if Path(arg).is_absolute() else [q / arg for q in libdirs]
                library = next((q for q in candidates if q.is_file()), None)
                m.need(library is not None, 'Original explicit link library absent: ' + arg); before.append(m.stat(library))
        m.verify(before)
        for phase, argv, cwd in [('compile', [str(cl), *cl_args], intdir), ('link', [str(link), *linked], S / 'VS')]:
            entry = m.invoke(label + '.' + phase, argv, cwd, env=env); calls.append(entry); actual = m.read(entry['path'])
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None,
                   'Actual owned CL/link exits must pass')
        runtime = []
        for entry in b['runtime']:
            origin = Path(entry['path']); target = out / origin.name
            m.need(not target.exists(), 'Existing private runtime leaf protected'); shutil.copy2(origin, target)
            m.need(target.read_bytes() == origin.read_bytes(), 'Runtime companion copy differs'); runtime.append(m.stat(target))
        m.verify(before)
        m.save(check, dict(stage=label + '.build', passed=True, configuration=configuration, program=m.stat(program),
            root_admission=m.stat(admission), header_author=m.stat(HEADER), original_optimized_build=m.stat(basepath),
            original_source_capture=b['source_capture'], original_source_archive=b['source_archive'],
            original_actual_link_call=b['calls'][-1], original_mdbc_CL_recipe=b['original_host_recipe'],
            source_capture=m.stat(capture), source_archive=m.stat(archive), source_diff=m.stat(diff),
            generated_mdbc=m.stat(physical / 'JSphGpu_mdbc.cpp'), capture_header=m.stat(header), frozen_sources=copied_sources,
            original_CL_arguments=[str(cl), *original_compile], actual_CL_arguments=[str(cl), *cl_args],
            original_link_arguments=original_link, actual_link_arguments=[str(link), *linked],
            retained_objects=[m.stat(q) for q in retained], original_replaced_host_object=m.stat(replaced[0]),
            replacement_host_object=m.stat(obj), original_CUDA_objects=[m.stat(q) for q in cuda_objects],
            retained_original_objects=110, retained_private_opt_objects=3, recompiled_host_objects=1,
            actual_link_objects=114, compile_invocations=1, link_invocations=1, CUDA_compile_invocations=0,
            all_original_CUDA_objects_retained=True, physical_GPU_kernels_recompiled=False,
            original_opt_HG_material_objects_retained=True, host_failure_branch_only=True,
            exact_inverse_original_mdbc_bytes=True, public_source_changed=False, class_ABI_changed=False,
            original_GPU_TU_bytes_changed=False, normal_path_allocations_or_D2H=False,
            fault_directory='WallFaultCaptureHostR1', no_GPU_printf=True, calls=calls, runtime=runtime,
            consumed=before, consumed_stats_unchanged=True, full_project_builds=0, help_invocations=0,
            smoke_invocations=0, solver_invocations=0, reader_invocations=0, VTK_invocations=0,
            new_binary_no_feedback_not_yet_proven=True, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        if not check.exists():
            actual_calls = [m.stat(L / (label + '.' + phase + '.call.json')) for phase in ('compile', 'link')
                            if (L / (label + '.' + phase + '.call.json')).is_file()]
            m.save(check, dict(stage=label + '.build', passed=False, configuration=configuration, first_failure=str(error),
                calls=actual_calls, consumed=before, partial_artifacts_preserved=True, automatic_retry=False,
                full_project_builds=0, CUDA_compile_invocations=0, solver_invocations=0,
                reader_invocations=0, physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', choices=('Debug', 'Release'), required=True)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Author-only until an exact separate root build admission')
    build(args.configuration)
