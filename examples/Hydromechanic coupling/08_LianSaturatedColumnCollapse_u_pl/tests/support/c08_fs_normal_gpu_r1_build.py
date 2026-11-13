"""Private normal-Taylor GPU builds: Debug controls or Release solver; no program execution."""
import argparse, os, re, shutil, subprocess
from pathlib import Path
import c08_fs_affine_cpu_r1_build as previous

m = previous.matrix
T, L, S = previous.T, previous.L, previous.S
TAG = 'c08_fs_normal_gpu_r1'
NOTE = T / 'notes' / (TAG + '_build.md')
FIXTURE = T / 'support' / (TAG + '.cpp')
CAP = T / 'outputs/c08_fs_normal_taylor_r1_source'
PREP = L / 'c08_fs_normal_taylor_r1.prepare.json'
INTERVENTION = 'free_surface_normal_taylor_projection'
CHANGED = {'src/source/JSphCpu.cpp', 'src/source/JSphGpu_ker.cu'}
RUNTIME = ('DsphConfig.xml', 'ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll',
           'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')


def actual(entry, before):
    before.append(m.bind(entry))
    call = m.read(entry['path'])
    m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
           and call['ownership_failure'] is None, 'Successful actual original tool call required')
    return call


def build(config):
    stage = 'c08_fs_normal_gpu_' + config + '_r1'
    out = T / 'outputs' / (stage + '_build')
    work = Path(os.environ['TEMP']).resolve() / TAG / config
    check = L / (stage + '.build.json')
    stages = [stage + '.gpu'] + ([stage + '.entry', stage + '.Raw.link', stage + '.Normal.link']
                                if config == 'Debug' else [stage + '.link'])
    m.need(not out.exists() and not work.exists() and not check.exists()
           and all(not (L / (q + suffix)).exists() for q in stages for suffix in ('.call.json', '.log')),
           'Existing complete or partial build protected')
    m.need(not any(q.isspace() for q in str(work)), 'Owned CUDA intermediate directory must contain no spaces')
    before, calls = [], []
    try:
        base_path = L / ('c08_preload_schema2_' + config + '_r1.build.json')
        base, prep = m.read(base_path), m.read(PREP)
        m.need(base['passed'] and base['configuration'] == config and base['consumed_stats_unchanged'],
               'Closed original schema2 configuration required')
        before = [m.stat(q) for q in (base_path, PREP, NOTE, Path(__file__), Path(previous.__file__), Path(m.__file__))]
        original_call = actual(base['actual_call'], before)
        before += [m.bind(base[q]) for q in ('program', 'source_capture', 'source_archive')]
        before += [m.bind(prep[q]) for q in ('source_capture', 'source_archive')]
        m.need(prep['passed'] and prep['intervention'] == INTERVENTION
               and set(prep['source_differences']) == CHANGED
               and Path(prep['source_capture']['path']) == CAP / 'source.json'
               and Path(prep['source_archive']['path']) == CAP / 'source.zip', 'Sealed private candidate preparation required')
        capture = m.read(prep['source_capture']['path'])
        m.need(capture['intervention'] == INTERVENTION and capture['exact_inverse_original_bytes']
               and capture['all_other_archived_bytes_identical'] and set(capture['actual_differences']) == CHANGED
               and capture['baseline_source_capture'] == base['source_capture']
               and capture['baseline_source_archive'] == base['source_archive']
               and capture['archive'] == prep['source_archive'], 'Candidate must derive only from the original schema2 archive')
        before += [m.bind(q) for q in capture['files']] + [m.bind(capture['baseline_source_build']), m.bind(capture['diff'])]
        private = CAP / 'src/source'
        cu, wall = private / 'JSphGpu_ker.cu', private / 'JSphGpu_mdbc_ker.cuh'
        m.need(all(m.stat(q) in capture['files'] for q in (cu, wall)), 'Private GPU TU and original unchanged mDBC include required')
        intdir = Path(base['intermediate']).resolve()
        m.need(intdir == (Path(os.environ['TEMP']) / 'c08_schema2_build_r1' / config / 'int').resolve(),
               'Only original schema2 objects may supply the link closure')
        ct, lt, rt, cr, cw = (intdir / 'DualSPHysics.tlog' / q for q in
            ('CL.command.1.tlog', 'link.command.1.tlog', 'link.read.1.tlog',
             'CudaCompile.read.1u.tlog', 'CudaCompile.write.1u.tlog'))
        before += [m.stat(q) for q in (ct, lt, rt, cr, cw)]
        links = previous.blocks(lt)
        m.need(len(links) == 1, 'One authoritative original link command required')
        la = previous.arguments(' '.join(links[0][1]))
        objects = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        replaced = {q.name.lower(): q for q in objects if q.name.lower() in ('main.obj', 'jsphgpu_ker.cu.obj')}
        m.need(len(objects) == len(set(objects)) == 113 and set(replaced) == {'main.obj', 'jsphgpu_ker.cu.obj'}
               and all(q.parent == intdir for q in objects), 'Exactly113 unique original schema2 objects required')
        before += [m.stat(q) for q in objects]
        log = m.bind(original_call['log']); before.append(log)
        lines = [q.split(b'>', 1)[1].strip().decode('ascii') for q in Path(log['path']).read_bytes().splitlines()
                 if b'nvcc.exe' in q.lower() and b'jsphgpu_ker.cu' in q.lower()]
        m.need(len(lines) == 1, 'One actual original GPU-TU NVCC command required')
        na = previous.arguments(lines[0]); nvcc = Path(na.pop(0))
        m.need(na.count('-ccbin') == na.count('-o') == na.count('--keep-dir') == 1
               and 'CUDA/v11.7' in nvcc.as_posix(), 'Original CUDA11.7 argv required')
        ccbin = Path(na[na.index('-ccbin') + 1])
        m.need(ccbin.parent.name.lower() == 'hostx86' and ccbin.name.lower() == 'x64'
               and '/14.36.32532/' in ccbin.as_posix(), 'Original HostX86/x64 MSVC14.36 required')
        host = ' '.join(na[i + 1] for i, q in enumerate(na[:-1]) if q == '-Xcompiler').split()
        required = ('/Od', '/MTd', '/Zi', '/RTC1') if config == 'Debug' else ('/O2', '/MT')
        m.need(all(q in host for q in required) and (('-G' in na and '-g' in na) if config == 'Debug' else '-G' not in na and '-g' not in na)
               and all(q in na for q in ('--compile', '--machine', '64', '-cudart', 'static', '-use_fast_math', '-D_WITHGPU'))
               and any('compute_86' in q and 'sm_86' in q for q in na)
               and not any('C08_STAGE_TRACE' in q or 'C08_CAUSAL_TRACE' in q or q in ('-dc', '--device-link') or 'rdc=true' in q for q in na),
               'Original GPU architecture/Debug-or-Release/FP flags required')
        includes = [q[2:] for q in na if q.startswith('-I')]
        m.need(len(includes) == 1 and Path(includes[0]).resolve() == (nvcc.parent.parent / 'include').resolve()
               and '-I' not in na and not any(q.startswith('--include-path') for q in na), 'Original CUDA-only explicit includes required')
        source_ids = [i for i, q in enumerate(na) if Path(q).name.lower() == 'jsphgpu_ker.cu']
        m.need(len(source_ids) == 1, 'One original GPU source token required')
        na[source_ids[0]] = str(cu)
        gpu_obj = work / 'JSphGpu_ker.cu.obj'
        na[na.index('-o') + 1], na[na.index('--keep-dir') + 1] = str(gpu_obj), str(work)
        pdb_count = 0
        for i, value in enumerate(na):
            if i and na[i - 1] == '-Xcompiler':
                na[i], count = re.subn(r'(?i)(?<!\S)/Fd\S+', lambda _: '/Fd' + (work / 'cuda_host.pdb').as_posix(), value)
                pdb_count += count
        m.need(pdb_count == 1, 'One original host PDB token required')
        na.insert(0, '-I' + str(private))
        libraries = [Path(q.strip('"')).resolve() for q in rt.read_text(encoding='utf-16').splitlines()
                     if not q.startswith('^') and q.lower().endswith('.lib')]
        m.need(libraries and all(q.is_file() for q in libraries), 'Original resolved CUDA/MSVC/project library closure required')
        before += [m.stat(q) for q in libraries]
        runtime = []
        for leaf in RUNTIME:
            found = [q for q in base['runtime'] if Path(q['destination']['path']).name == leaf]
            m.need(len(found) == 1, 'One original frozen companion required: ' + leaf)
            before.append(m.bind(found[0]['source']))
            runtime.append(m.bind(found[0]['destination']))
        before += runtime
        entry, ca, harness = work / 'fixture.obj', [], T / 'support/upl_cubic_component_r2.cpp'
        if config == 'Debug':
            before += [m.stat(FIXTURE), m.stat(harness)]
            mains = [q for q in previous.blocks(ct) if len(q[0]) == 1 and Path(q[0][0]).name.lower() == 'main.cpp']
            m.need(len(mains) == 1, 'One original Debug main CL command required')
            ca = previous.arguments(' '.join(mains[0][1]))
            ids = [i for i, q in enumerate(ca) if Path(q).name.lower() == 'main.cpp']
            m.need(len(ids) == 1 and all(q in ca for q in ('/MTd', '/Od', '/Zi', '/RTC1', '/fp:precise', '/openmp'))
                   and '_WITHGPU' in ca and not any(q.lower().startswith('/std:') for q in ca), 'Original GPU Debug entry ABI required')
            ca[ids[0]] = str(FIXTURE)
            for prefix, output in (('/Fo', entry), ('/Fd', work / 'entry_compile.pdb')):
                ids = [i for i, q in enumerate(ca) if q.lower().startswith(prefix.lower())]
                m.need(len(ids) == 1, 'One case-correct CL output token required')
                ca[ids[0]] = prefix + str(output)
            ca = ['/I' + str(private), *ca, '/std:c++17', '/D_HAS_STD_BYTE=0']
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Original MSVC setup failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines()
                                             if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Exact original MSVC version required')
        for key in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'): env.pop(key, None)
        env['PATH'] = str(ccbin) + os.pathsep + env.get('PATH', '')
        selected_cl = shutil.which('cl.exe', path=env['PATH'])
        m.need(selected_cl is not None and Path(selected_cl).samefile(ccbin / 'cl.exe'), 'Owned PATH cl.exe must exactly match original -ccbin')
        env['LIB'] = ';'.join(dict.fromkeys(str(q.parent) for q in libraries))
        before += [m.stat(q) for q in (nvcc, ccbin / 'cl.exe', ccbin / 'link.exe')]
        m.verify(before)
        work.mkdir(parents=True); out.mkdir()
        calls.append(m.invoke(stages[0], [str(nvcc), *na], work, env))
        m.need(gpu_obj.is_file(), 'Candidate CUDA object missing')
        before.append(m.stat(gpu_obj))
        if config == 'Debug':
            calls.append(m.invoke(stage + '.entry', [str(ccbin / 'cl.exe'), *ca], S / 'VS', env))
            m.need(entry.is_file(), 'Case-correct shared Debug entry object missing')
            before.append(m.stat(entry))
        variants = {'Raw': replaced['jsphgpu_ker.cu.obj'], 'Normal': gpu_obj} if config == 'Debug' else {'Normal': gpu_obj}
        retained = [q for q in objects if q != replaced['jsphgpu_ker.cu.obj'] and (config != 'Debug' or q != replaced['main.obj'])]
        programs, closures = {}, {}
        for label, kernel in variants.items():
            exe = out / (label + '.exe' if config == 'Debug' else 'DualSPHysics5.2_GEO_win64.exe')
            outputs = {'/out:': exe, '/pdb:': out / (label + '.pdb'),
                       '/implib:': out / (label + '.lib'), '/ltcgout:': out / (label + '.iobj')}
            linked, seen = [], set()
            for value in la:
                if value.lower().endswith('.obj'):
                    if Path(value).resolve() == replaced['jsphgpu_ker.cu.obj']: value = str(kernel)
                    elif config == 'Debug' and Path(value).resolve() == replaced['main.obj']: value = str(entry)
                for prefix, target in outputs.items():
                    if value.lower().startswith(prefix): value = prefix + str(target); seen.add(prefix); break
                linked.append(value)
            final = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
            expected = set(retained) | {kernel.resolve()} | ({entry.resolve()} if config == 'Debug' else set())
            m.need(seen == set(outputs) and len(final) == len(set(final)) == 113 and set(final) == expected,
                   'Exact113-object original-derived link closure required')
            calls.append(m.invoke(stage + ('.' + label + '.link' if config == 'Debug' else '.link'),
                                  [str(ccbin / 'link.exe'), *linked], S / 'VS', env))
            programs[label], closures[label] = m.stat(exe), [m.stat(q) for q in final]
        copied = []
        for source in runtime:
            destination = out / Path(source['path']).name
            shutil.copy2(source['path'], destination)
            m.need(destination.read_bytes() == Path(source['path']).read_bytes(), 'Frozen original companion copy differs')
            copied.append(m.stat(destination))
        m.verify(before)
        result = dict(stage=stage + '.build', passed=True, configuration=config, intervention=INTERVENTION,
            programs=programs, source_capture=prep['source_capture'], source_archive=prep['source_archive'],
            baseline_source_build=m.stat(base_path), baseline_source_capture=base['source_capture'], baseline_source_archive=base['source_archive'],
            private_gpu_source=m.stat(cu), private_wall_include=m.stat(wall), original_mdbc_include_unchanged=True,
            source_differences=capture['actual_differences'], exact_inverse_original_bytes=True,
            original_gpu_object=m.stat(replaced['jsphgpu_ker.cu.obj']), candidate_object=m.stat(gpu_obj),
            retained_project_objects=[m.stat(q) for q in retained], retained_public_objects=len(retained),
            project_objects=closures, actual_link_objects=113, runtime=copied, calls=calls,
            authoritative_CL_tlog=m.stat(ct), authoritative_LINK_tlog=m.stat(lt), resolved_library_tlog=m.stat(rt),
            authoritative_NVCC_log=log, CUDA_read_tlog=m.stat(cr), CUDA_write_tlog=m.stat(cw),
            compiler_PATH_prepended=str(ccbin), PATH_cl_matches_ccbin=True, intermediate=str(work), note=m.stat(NOTE),
            physical_objects_recompiled=1, compile_invocations=2 if config == 'Debug' else 1,
            link_invocations=len(variants), actual_typed_exit_code=0, actual_Win32_exit=0,
            consumed=before, consumed_stats_unchanged=True, public_source_changed=False, full_project_builds=0,
            help_invocations=0, fixture_invocations=0, solver_invocations=0, memcheck_invocations=0, native_decodes=0,
            physical_acceptance=False, SHA_scans=0)
        if config == 'Debug':
            result.update(fixture=m.stat(FIXTURE), fixture_object=m.stat(entry), retained_harness=m.stat(harness),
                          replaced_main=m.stat(replaced['main.obj']), shared_entry_object=True)
        else: result.update(program=programs['Normal'], original_main=m.stat(replaced['main.obj']))
        m.save(check, result)
    except Exception as error:
        found = [m.stat(L / (q + '.call.json')) for q in stages if (L / (q + '.call.json')).is_file()]
        if not check.exists():
            m.save(check, dict(stage=stage + '.build', passed=False, configuration=config, first_failure=str(error),
                calls=found, consumed=before, fixture_invocations=0, solver_invocations=0,
                memcheck_invocations=0, native_decodes=0, physical_acceptance=False))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('debug', 'release'))
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Author-only until root full-read and separate action-specific authorization')
    build('Debug' if args.action == 'debug' else 'Release')
