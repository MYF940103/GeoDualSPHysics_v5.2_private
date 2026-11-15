"""Pack one real failed-input fixture and compile/link one host component; never execute."""
import argparse
import ctypes
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path
import c08_h18_wend_matrix_r1 as m

T, C, L = m.T, m.C, m.L
S = T.parents[3] / 'src'
TAG = 'c08_h18_hg_wall_packet_component_r1'
SCRIPT = Path(__file__).resolve()
CPP = T / 'support' / (TAG + '.cpp')
NOTE = T / 'notes' / (TAG + '.md')
FAULT = T / 'support/c08_h18_hg_wall_fault_review_r1.py'
BASE = L / 'c08_h18_hg_opt_Release_r1.build.json'
RUN = L / 'c08_h18_hg_wall_host_replay_GPU_r1.run.json'
REVIEW = L / 'c08_h18_hg_wall_fault_review_r1.check.json'
OUT = T / 'outputs' / (TAG + '_build')
CHECK = L / (TAG + '.build.json')
ADMISSION = L / (TAG + '.root_build_admission.json')
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
FLOATS = ('MassFluid', 'RhopZero', 'KernelH', 'KernelSize2', 'PosCellSize', 'Scell',
          'KWend.awen', 'KWend.bwen', 'Gravity.x', 'Gravity.y', 'Gravity.z',
          'SoilCte.PoreWaterRho', 'MdbcThreshold', 'dp.upload_float')
DOUBLES = ('DomPosMin.x', 'DomPosMin.y', 'DomPosMin.z', 'actual_solid0_argument', 'TimeStep')
ARRAYS = (('Idp', 3, 1), ('Code', 2, 1), ('Posxy', 6, 2), ('Posz', 6, 1), ('PosCell', 5, 4),
          ('Dcell', 3, 1), ('PoroJ', 6, 1), ('CorrMat', 6, 9), ('BoundNormal', 5, 3),
          ('BoundMode', 1, 1), ('FluidCells', 4, 2))


def windows_args(line):
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    n = ctypes.c_int(); ptr = shell.CommandLineToArgvW('tool.exe ' + line, ctypes.byref(n))
    m.need(bool(ptr), 'Original Windows command parse failed')
    try: return [ptr[i] for i in range(1, n.value)]
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes, free.restype = [ctypes.c_void_p], ctypes.c_void_p
        free(ctypes.cast(ptr, ctypes.c_void_p))


def pack(before):
    # Deliberately called exactly once, after root admission. This is the already
    # reviewed raw-hex CSV input decoder only, never the review main/reader/plot.
    import c08_h18_hg_wall_fault_review_r1 as fault
    run, schema, meta, arrays, fluid, fixed, target, constants, audit = fault.inputs(before)
    m.need(target == 690 and schema['npbok'] == 940 and schema['DivData']['logical_Nct'] == 608
           and schema['Nstep_actual_uint64'] == 2196678 and schema['sizeof']['typecode'] == 2,
           'Only actual original failed wall894 packet scope is admitted')
    d = schema['DivData']; n, npb, nb = schema['np'], schema['npb'], schema['npbok']
    fixture = OUT / 'fixture.bin'
    header = [1, n, npb, nb, d['logical_Nct'], d['cellfluid'], target, schema['sizeof']['typecode'],
              schema['stage'], schema['kernel'], schema['host_upload_axis'], schema['simulate2d'],
              schema['periactive'], schema['slipmode'], schema['host_cellcode'], d['scelldiv']]
    blocks = []
    with fixture.open('xb') as f:
        f.write(b'C08WPK1\0'); f.write(struct.pack('<16I', *header))
        f.write(struct.pack('<Q', schema['Nstep_actual_uint64']))
        f.write(struct.pack('<4i3i3I', *d['nc'], *d['cellzero'], *d['ncells']))
        f.write(struct.pack('<14f', *(meta[key] for key in FLOATS)))
        f.write(struct.pack('<5d', *(meta[key] for key in DOUBLES))); f.write(struct.pack('<I', len(ARRAYS)))
        for name, kind, components in ARRAYS:
            a = arrays[name]
            count = d['logical_Nct'] if name == 'FluidCells' else nb if name in ('BoundNormal', 'BoundMode') else n
            payload = a.tobytes(order='C')
            scalar_bytes = {1: 1, 2: 2, 3: 4, 4: 4, 5: 4, 6: 8}[kind]
            m.need(a.shape == (count, components) and len(payload) == count * components * scalar_bytes,
                   'Actual fixture array extent differs: ' + name)
            m.need(len(name.encode('ascii')) < 16, 'Closed array name exceeds fixture field')
            f.write(name.encode('ascii').ljust(16, b'\0'))
            f.write(struct.pack('<IIQQ', kind, components, count, len(payload))); f.write(payload)
            blocks.append(dict(array=name, scalar_kind=kind, components=components, count=count,
                               payload_bytes=len(payload), raw_array_bytes_unchanged=True))
    description = OUT / 'fixture.json'
    m.save(description, dict(schema=1, magic='C08WPK1\\0', fixture=m.stat(fixture),
        actual_failed_run=m.stat(RUN), actual_capture_directory=schema['directory'],
        raw_hex_input_decoder=m.stat(FAULT), raw_hex_input_calls=1, native_reader_invocations=0,
        stage=1, Np=n, Npb=npb, NpbOk=nb, target_sorted_slot=target, target_native_ID=894,
        original_step=schema['Nstep_actual_uint64'], original_host_time=meta['TimeStep'],
        header_uint32_names=['version', 'Np', 'Npb', 'NpbOk', 'Nct', 'cellfluid', 'target', 'typecode_bytes',
                            'stage', 'kernel', 'axis', 'simulate2d', 'periactive', 'slipmode', 'cellcode', 'scelldiv'],
        header_all_fields_explicit_little_endian_no_struct_padding=True,
        float32_names=list(FLOATS), float64_names=list(DOUBLES), arrays=blocks,
        actual_DivData=d, raw_hex_primary_including_PosCell_w=True, source_csv_unchanged=True,
        host_mapping_not_direct_original_device_CTE_snapshot=True,
        stage1_per_mk_slip_not_read_due_to_stage0_short_circuit=True,
        original_wall_C_registers_not_captured=True, physical_acceptance=False, solver_invocations=0))
    return m.stat(fixture), m.stat(description)


def build():
    intdir = Path(os.environ['TEMP']) / TAG
    m.need(' ' not in str(intdir) and not intdir.exists() and not OUT.exists() and not CHECK.exists()
           and all(not (L / (TAG + suffix)).exists() for suffix in
                   ('.compile.call.json', '.compile.log', '.link.call.json', '.link.log')),
           'Existing complete/partial component or fixture protected')
    before, calls = [], []
    try:
        ad = m.read(ADMISSION)
        m.need(ad['authorized'] and ad['allowed_stage'] == TAG and ad['execution_script'] == m.stat(SCRIPT)
               and ad['component_source'] == m.stat(CPP) and ad['note'] == m.stat(NOTE)
               and ad['source_build'] == m.stat(BASE) and ad['packet_run'] == m.stat(RUN)
               and ad['packet_review'] == m.stat(REVIEW)
               and ad['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == THREAD
               and ad['pack_and_build_only'] and not ad['automatic_component'] and not ad['automatic_solver'],
               'Exact separate current-root pack/build-only admission required')
        b = m.read(BASE); review = m.read(REVIEW)
        m.need(b['passed'] and b['configuration'] == 'Release' and b['consumed_stats_unchanged']
               and b['actual_link_objects'] == 114 and b['original_physical_CUDA_objects_retained']
               and review['analysis_complete'] and review['consumed_stats_unchanged'],
               'Actual original Release object closure and completed packet review required')
        before = [m.stat(q) for q in (SCRIPT, CPP, NOTE, FAULT, ADMISSION, BASE, REVIEW)]
        before += [m.bind(b[key]) for key in ('program', 'source_capture', 'source_archive', 'baseline_source_capture',
                                             'original_link_recipe', 'original_host_recipe')]
        before += [m.bind(q) for q in b['frozen_sources'] + b['runtime'] + b['fresh_original_objects']]
        # The replay's actual compiled CUDA must be the same retained original
        # object, not a Debug kernel or either rejected printf object.
        replay = m.read(RUN); actual_replay_build = m.read(replay['source_build']['path'])
        m.need(actual_replay_build['passed'] and actual_replay_build['all_original_CUDA_objects_retained']
               and not actual_replay_build['physical_GPU_kernels_recompiled']
               and actual_replay_build['original_optimized_build'] == m.stat(BASE),
               'Actual replay must retain this exact original Release CUDA object')
        before += [m.bind(replay['source_build'])]
        physical = [q for q in b['fresh_original_objects'] if Path(q['path']).name.lower() == 'jsphgpu_ker.cu.obj']
        replay_physical = [q for q in actual_replay_build['original_CUDA_objects'] if Path(q['path']).name.lower() == 'jsphgpu_ker.cu.obj']
        m.need(len(physical) == len(replay_physical) == 1 and physical[0] == replay_physical[0],
               'Physical CUDA original/replay path/stat identity differs')
        tlog = Path(b['original_link_recipe']['path'])
        lines = tlog.read_text(encoding='utf-16').splitlines()
        m.need(sum(q.startswith('^') for q in lines) == 1, 'One authoritative original113 link block required')
        link_args = windows_args(' '.join(q for q in lines if q and not q.startswith('^')))
        objects = [Path(q).resolve() for q in link_args if q.lower().endswith('.obj')]
        declared = {Path(q['path']).resolve() for q in b['fresh_original_objects']}
        main = [q for q in objects if q.name.lower() == 'main.obj']
        m.need(len(objects) == len(set(objects)) == 113 and set(objects) == declared and len(main) == 1
               and Path(physical[0]['path']).resolve() in objects,
               'Actual schema2 original113/main/object closure required')
        retained = [q for q in objects if q != main[0]]
        source_root = Path(b['OutDir']) / 'frozen/src/source'
        cl_call = m.read(b['calls'][1]['path']); link_call = m.read(b['calls'][-1]['path'])
        for entry, actual in [(b['calls'][1], cl_call), (b['calls'][-1], link_call)]:
            before.append(m.bind(entry))
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0
                   and actual['ownership_failure'] is None, 'Actual optimized host tool recipe must pass')
        cl, link = Path(cl_call['child']['exe']), Path(link_call['child']['exe'])
        m.need(cl.name.lower() == 'cl.exe' and link.name.lower() == 'link.exe'
               and '/14.36.32532/' in cl.as_posix() and '/14.36.32532/' in link.as_posix(),
               'Original MSVC14.36 host tools required')
        host_args = list(b['original_GPU_host_command'])
        m.need('/MT' in host_args and '/Zi' in host_args and '/fp:precise' in host_args
               and sum(Path(q).name.lower() == 'jsphgpu.cpp' for q in host_args) == 1
               and not any(q.lower().startswith(('/yu', '/yc', '/gl')) for q in host_args),
               'Original Release /MT /Zi precise nonPCH host recipe required')
        m.verify(before); OUT.mkdir(); intdir.mkdir()
        fixture, fixture_meta = pack(before)
        before += [fixture, fixture_meta]
        obj, program = intdir / 'component.obj', OUT / (TAG + '.exe')
        cl_args = ['/I' + str(source_root)] + [
            '/Fo' + str(obj) if q.lower().startswith('/fo') else
            '/Fd' + str(intdir / 'component.pdb') if q.lower().startswith('/fd') else
            str(CPP) if Path(q).name.lower() == 'jsphgpu.cpp' else q for q in host_args]
        dependencies = OUT / 'compile.dependencies.json'
        cl_args += ['/sourceDependencies', str(dependencies)]
        targets = {'/out:': program, '/pdb:': OUT / (TAG + '.pdb'), '/implib:': OUT / (TAG + '.lib'),
                   '/ltcgout:': intdir / (TAG + '.iobj')}
        linked, seen = [], set()
        for arg in link_args:
            if arg.lower().endswith('.obj') and Path(arg).resolve() == main[0]: arg = str(obj)
            for prefix, target in targets.items():
                if arg.lower().startswith(prefix): arg = prefix + str(target); seen.add(prefix); break
            linked.append(arg)
        actual_objects = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        m.need(seen == set(targets) and actual_objects == [obj.resolve() if q == main[0] else q for q in objects],
               'Only original main object may be replaced in the113 object component')
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
            if key.upper() in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'): env.pop(key)
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
        expected_headers = {Path(q['path']).resolve(): q for q in b['frozen_sources']}
        for leaf in m.read(dependencies)['Data']['Includes']:
            path = Path(leaf).resolve()
            if path.is_relative_to(source_root.resolve()):
                m.need(path in expected_headers, 'Unsealed frozen include used'); before.append(m.bind(expected_headers[path]))
        before.append(m.stat(dependencies))
        runtime = []
        for entry in b['runtime']:
            origin = Path(entry['path']); target = OUT / origin.name
            m.need(not target.exists(), 'Existing component runtime leaf protected'); shutil.copy2(origin, target)
            m.need(target.read_bytes() == origin.read_bytes(), 'Runtime copy differs'); runtime.append(m.stat(target))
        m.verify(before)
        m.save(CHECK, dict(stage=TAG + '.build', passed=True, program=m.stat(program), source=m.stat(CPP),
            root_admission=m.stat(ADMISSION), source_build=m.stat(BASE), original_source_capture=b['source_capture'],
            original_source_archive=b['source_archive'], source_root=str(source_root), actual_replay_build=replay['source_build'],
            exact_original_physical_CUDA_object=physical[0], exact_replay_physical_CUDA_object=replay_physical[0],
            fixture=fixture, fixture_metadata=fixture_meta, raw_hex_input_decoder=m.stat(FAULT), raw_hex_input_calls=1,
            component_host_debug_symbols=True, original_Release_CUDA_retained=True, Debug_CUDA_program_claimed=False,
            original_main_object=m.stat(main[0]), retained_original_non_main_objects=[m.stat(q) for q in retained],
            new_host_main_object=m.stat(obj), actual_link_objects=113, original_non_main_objects=112,
            compile_invocations=1, link_invocations=1, CUDA_compile_invocations=0, device_link_invocations=0,
            calls=calls, runtime=runtime, source_dependencies=m.stat(dependencies),
            consumed=before, consumed_stats_unchanged=True, component_invocations=0, help_invocations=0,
            solver_invocations=0, native_reader_invocations=0, physical_acceptance=False, SHA_scans=0))
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
    m.need(args.execution_authorized, 'Separate current-root pack/build admission required')
    build()
