"""Build one private GPU storage observer; never prepare source or execute a program."""
import argparse
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import c08_fs_normal_gpu_r1_build as prior

m, parser_tools = prior.m, prior.previous
T, L, S = prior.T, prior.L, prior.S
TAG = 'c08_h18_storage_trace_r1'
NOTE = T / 'notes/c08_h18_storage_trace_build_r1.md'
CAP = T / 'outputs/c08_h18_storage_trace_source_r1'
PREP = L / (TAG + '.prepare.json')
MODIFIED = {'src/source/JSphGpu.cpp'}
ADDED = {'src/source/C08StorageTrace.cu', 'src/source/C08StorageTrace.h'}
MACRO = 'C08_STORAGE_TRACE'
OLD_MACROS = ('C08_STAGE_TRACE', 'C08_CAUSAL_TRACE')
RUNTIME = {'gencase_win64.exe', 'partvtk_win64.exe', 'dsphconfig.xml',
           'chronoengine.dll', 'dsphchrono.dll', 'vcomp140.dll', 'msvcp140.dll',
           'vcruntime140.dll', 'vcruntime140_1.dll'}


def identity(path):
    return str(Path(path).resolve()).casefold()


def actual(entry, consumed):
    consumed.append(m.bind(entry))
    call = m.read(entry['path'])
    m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and
           call['ownership_failure'] is None, 'Actual successful original tool call required')
    return call


def build(configuration):
    stage = 'c08_h18_storage_trace_' + configuration + '_r1'
    out, check = T / 'outputs' / stage, L / (stage + '.build.json')
    work = Path(os.environ['TEMP']).resolve() / TAG / configuration
    stages = tuple(stage + suffix for suffix in ('.host', '.gpu', '.link'))
    m.need(not out.exists() and not work.exists() and not check.exists() and
           all(not (L / (tag + suffix)).exists() for tag in stages
               for suffix in ('.call.json', '.log')), 'Existing complete/partial build protected')
    m.need(not any(c.isspace() for c in str(work)), 'NVCC owned intermediate must have no spaces')
    before, calls = [], []
    try:
        base_path = L / ('c08_preload_schema2_' + configuration + '_r1.build.json')
        seal_path = L / ('c08_fs_normal_gpu_' + configuration + '_r1.build.json')
        base, seal, prep = map(m.read, (base_path, seal_path, PREP))
        m.need(base['passed'] and base['configuration'] == configuration and
               base['consumed_stats_unchanged'], 'Successful authoritative schema2 build required')
        before = [m.stat(p) for p in (Path(__file__), NOTE, Path(prior.__file__),
                  Path(parser_tools.__file__), Path(m.__file__), base_path, seal_path, PREP)]
        original_call = actual(base['actual_call'], before)
        before += [m.bind(base[k]) for k in ('program', 'source_capture', 'source_archive')]
        m.need('/p:VCToolsVersion=14.36.32532' in original_call['arguments'],
               'Original MSVC14.36 authoritative build required')
        m.need(prep['passed'] and prep['consumed_stats_unchanged'] and
               prep['stage'] == TAG + '.prepare' and
               Path(prep['source_capture']['path']).resolve() == (CAP / 'source.json').resolve()
               and Path(prep['source_archive']['path']).resolve() == (CAP / 'source.zip').resolve(),
               'Separately reviewed source preparation required')
        before += [m.bind(prep[k]) for k in ('source_capture', 'source_archive')]
        sc = m.read(prep['source_capture']['path'])
        m.need(sc['stage'] == TAG + '.source' and sc['passed'] and sc['prepared_only'] and
               sc['consumed_stats_unchanged'] and sc['archive'] == prep['source_archive'] and
               sc['baseline_source_capture'] == base['source_capture'] and
               sc['baseline_source_archive'] == base['source_archive'] and
               Path(sc['baseline_source_build']['path']).resolve() ==
               (L / 'c08_preload_schema2_Release_r1.build.json').resolve() and
               sc['modified_original_members'] == sorted(MODIFIED) and
               sc['added_members'] == sorted(ADDED) and sc['exact_inverse_original_bytes'] and
               sc['all_other_archived_bytes_identical'] and sc['primary_expression_bytes_retained'] and
               sc['macro'] == MACRO and not sc['class_layout_changed'] and
               not sc['public_interfaces_changed'] and not sc['physical_equations_changed'],
               'Only the reversible host hook and new observer CU/header are admitted')
        before += [m.bind(sc[k]) for k in ('baseline_source_build', 'diff')]
        private = {Path(q['path']).name: m.bind(q) for q in sc['files']}
        m.need(len(sc['files']) == 3 and
               set(private) == {'JSphGpu.cpp', 'C08StorageTrace.cu', 'C08StorageTrace.h'} and
               all(Path(q['path']).resolve().parent == (CAP / 'src/source').resolve()
                   for q in private.values()),
               'Exactly three private source/include files required')
        before += list(private.values())

        intdir = Path(base['intermediate']).resolve()
        m.need(intdir == (Path(os.environ['TEMP']).resolve() /
                         'c08_schema2_build_r1' / configuration / 'int').resolve(),
               'Only the original isolated schema2 object directory is admitted')
        tlog = intdir / 'DualSPHysics.tlog'
        ct, lt, rt, cr, cw = [tlog / leaf for leaf in
            ('CL.command.1.tlog', 'link.command.1.tlog', 'link.read.1.tlog',
             'CudaCompile.read.1u.tlog', 'CudaCompile.write.1u.tlog')]
        before += [m.stat(p) for p in (ct, lt, rt, cr, cw)]
        host_blocks = [q for q in parser_tools.blocks(ct) if len(q[0]) == 1 and
                       Path(q[0][0]).name.casefold() == 'jsphgpu.cpp']
        link_blocks = parser_tools.blocks(lt)
        m.need(len(host_blocks) == len(link_blocks) == 1,
               'One authoritative JSphGpu host compile and link block required')
        ca = parser_tools.arguments(' '.join(host_blocks[0][1]))
        la = parser_tools.arguments(' '.join(link_blocks[0][1]))
        objects = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        replaced = {p.name.casefold(): p for p in objects if p.name.casefold() == 'jsphgpu.obj'}
        m.need(len(objects) == len(set(objects)) == 113 and len(replaced) == 1 and
               all(p.parent == intdir for p in objects) and
               sum(p.name.casefold() == 'main.obj' for p in objects) == 1 and
               sum(p.name.casefold() == 'jsphgpu_ker.cu.obj' for p in objects) == 1,
               'Exactly113 original full-program objects, including untouched main, required')
        m.need(seal['passed'] and seal['consumed_stats_unchanged'] and
               seal['baseline_source_build'] == m.stat(base_path) and
               seal['baseline_source_archive'] == base['source_archive'] and
               seal['actual_link_objects'] == 113,
               'The previous successful same-backend original-object seal is required')
        sealed = {identity(q['path']): q for q in seal['consumed']}
        object_entries = []
        for p in objects:
            m.need(identity(p) in sealed, 'An original object lacks its existing stat seal')
            entry = m.bind(sealed[identity(p)])
            m.need(entry == m.stat(p), 'Original object changed since its successful seal')
            object_entries.append(entry)
        before += object_entries
        log = m.bind(original_call['log']); before.append(log)
        lines = [q.split(b'>', 1)[1].strip().decode('ascii')
                 for q in Path(log['path']).read_bytes().splitlines()
                 if b'nvcc.exe' in q.lower() and b'jsphgpu_ker.cu' in q.lower()]
        m.need(len(lines) == 1, 'One actual original CUDA-TU command required')
        na = parser_tools.arguments(lines[0]); nvcc = Path(na.pop(0)).resolve()
        m.need(na.count('-ccbin') == na.count('-o') == na.count('--keep-dir') == 1 and
               'CUDA/v11.7' in nvcc.as_posix(), 'Original CUDA11.7 argument layout required')
        ccbin = Path(na[na.index('-ccbin') + 1]).resolve()
        m.need(ccbin.parent.name.lower() == 'hostx86' and ccbin.name.lower() == 'x64' and
               '/14.36.32532/' in ccbin.as_posix(), 'Original HostX86/x64 MSVC14.36 required')
        required = ('/Od', '/MTd', '/Zi', '/RTC1') if configuration == 'Debug' else ('/O2', '/MT')
        host_flags = ' '.join(na[i + 1] for i, q in enumerate(na[:-1]) if q == '-Xcompiler').split()
        m.need(all(q in host_flags for q in required) and
               (('-G' in na and '-g' in na) if configuration == 'Debug' else '-G' not in na and '-g' not in na)
               and all(q in na for q in ('--compile', '--machine', '64', '-cudart',
                                        'static', '-use_fast_math', '-D_WITHGPU')) and
               any('compute_86' in q and 'sm_86' in q for q in na) and
               not any(any(name in q for name in (*OLD_MACROS, MACRO)) or
                       q in ('-dc', '--device-link') or 'rdc=true' in q for q in na),
               'Original CUDA architecture/FP/configuration/macros required')
        explicit_includes = [q[2:] for q in na if q.startswith('-I')]
        m.need(len(explicit_includes) == 1 and
               Path(explicit_includes[0]).resolve() == (nvcc.parent.parent / 'include').resolve()
               and '-I' not in na and not any(q.startswith('--include-path') for q in na),
               'Original explicit CUDA include layout differs')
        m.need(all(q in ca for q in (*required, '/fp:precise', '/openmp')) and
               any('_WITHGPU' in q for q in ca) and
               not any(q.lower().startswith(('/yu', '/yc', '/gl', '/sourcedependencies')) or
                       any(name in q for name in (*OLD_MACROS, MACRO)) for q in ca),
               'Original host ABI/FP/macros required')
        libraries = [Path(q.strip('"')).resolve() for q in rt.read_text(encoding='utf-16').splitlines()
                     if not q.startswith('^') and q.lower().endswith('.lib')]
        m.need(libraries and all(p.is_file() for p in libraries), 'Original resolved library closure required')
        before += [m.stat(p) for p in libraries]
        runtime = [m.bind(q.get('destination', q)) for q in base['runtime']]
        m.need(len(runtime) == 9 and {Path(q['path']).name.casefold() for q in runtime} == RUNTIME,
               'Original complete nine-file runtime required')
        before += runtime
        m.verify(before)

        work.mkdir(parents=True); out.mkdir()
        frozen, archived = out / 'frozen/src/source', []
        with zipfile.ZipFile(sc['archive']['path']) as z:
            members = z.infolist()
            m.need(len({q.filename for q in members}) == len(members), 'Duplicate private archive member')
            for name, entry in private.items():
                m.need(z.read('src/source/' + name) == Path(entry['path']).read_bytes(),
                       'Private input and prepared archive differ')
            for member in members:
                relative = Path(member.filename)
                m.need(not relative.is_absolute() and '..' not in relative.parts,
                       'Private archive path escapes output')
                if member.is_dir() or relative.parts[:2] != ('src', 'source'):
                    continue
                m.need(relative.suffix.lower() not in ('.obj', '.o', '.pdb', '.exe', '.dll', '.lib'),
                       'Source archive unexpectedly contains binaries')
                destination = out / 'frozen' / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as f:
                    f.write(z.read(member))
                archived.append(m.stat(destination))
        m.need(sum(Path(q['path']).suffix.lower() in ('.h', '.cuh') for q in archived) == 161,
               'Original160 headers plus one observer header required')
        before += archived
        host_source, cuda_source = frozen / 'JSphGpu.cpp', frozen / 'C08StorageTrace.cu'
        host_obj, gpu_obj = work / 'JSphGpu.obj', work / 'C08StorageTrace.cu.obj'
        ids = [i for i, q in enumerate(ca) if Path(q).name.casefold() == 'jsphgpu.cpp']
        m.need(len(ids) == 1, 'One original host source token required')
        ca[ids[0]] = str(host_source)
        for prefix, target in (('/Fo', host_obj), ('/Fd', work / 'host_compile.pdb')):
            ids = [i for i, q in enumerate(ca) if q.lower().startswith(prefix.lower())]
            m.need(len(ids) == 1, 'One original compiler output token required: ' + prefix)
            ca[ids[0]] = prefix + str(target)  # MSVC switch case is significant.
        dependencies = out / 'host.dependencies.json'
        ca = ['/I' + str(frozen), *ca, '/D' + MACRO + '=1',
              *('/U' + name for name in OLD_MACROS), '/sourceDependencies', str(dependencies)]
        ids = [i for i, q in enumerate(na) if Path(q).name.casefold() == 'jsphgpu_ker.cu']
        m.need(len(ids) == 1, 'One original CUDA source token required')
        na[ids[0]] = str(cuda_source)
        na[na.index('-o') + 1], na[na.index('--keep-dir') + 1] = str(gpu_obj), str(work)
        pdb_count = 0
        for i, value in enumerate(na):
            if i and na[i - 1] == '-Xcompiler':
                na[i], count = re.subn(r'(?i)(?<!\S)/Fd\S+',
                    lambda _: '/Fd' + (work / 'cuda_host.pdb').as_posix(), value)
                pdb_count += count
        m.need(pdb_count == 1, 'One original CUDA-host PDB switch required')
        na = ['-I' + str(frozen), *na, '-D' + MACRO + '=1', *('-U' + name for name in OLD_MACROS)]
        exe = out / Path(base['program']['path']).name
        targets = {'/out:': exe, '/pdb:': out / (exe.stem + '.pdb'),
                   '/implib:': out / (exe.stem + '.lib'), '/ltcgout:': out / (exe.stem + '.iobj')}
        linked, seen = [], set()
        for value in la:
            if value.lower().endswith('.obj'):
                p = Path(value).resolve()
                if p == replaced['jsphgpu.obj']: value = str(host_obj)
            for prefix, target in targets.items():
                if value.lower().startswith(prefix):
                    value = prefix + str(target); seen.add(prefix); break
            linked.append(value)
        linked.append(str(gpu_obj))
        retained = [p for p in objects if p not in replaced.values()]
        final = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        m.need(seen == set(targets) and len(final) == len(set(final)) == 114 and
               len(retained) == 112 and set(final) == set(retained) | {host_obj.resolve(), gpu_obj.resolve()} and
               any(p.name.casefold() == 'jsphgpu_ker.cu.obj' for p in retained),
               'Link must retain112 original objects/all CUDA/main, replace host and add observer CU')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Original MSVC environment setup failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in
            setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Exact original compiler version required')
        for key in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'):
            env.pop(key, None)
        env['PATH'] = str(ccbin) + os.pathsep + env.get('PATH', '')
        selected_cl = shutil.which('cl.exe', path=env['PATH'])
        m.need(selected_cl is not None and Path(selected_cl).samefile(ccbin / 'cl.exe'),
               'Compiler PATH must select actual original -ccbin cl.exe')
        env['LIB'] = ';'.join(dict.fromkeys(str(p.parent) for p in libraries))
        cl, link = ccbin / 'cl.exe', ccbin / 'link.exe'
        before += [m.stat(p) for p in (nvcc, cl, link)]
        m.verify(before)
        calls.append(m.invoke(stages[0], [str(cl), *ca], work, env))
        m.need(host_obj.is_file(), 'Private host object missing')
        dependency = m.read(dependencies)['Data']
        includes = {Path(q).resolve() for q in dependency['Includes']}
        names = {Path(q['path']).name.lower() for q in archived}
        m.need(Path(dependency['Source']).resolve() == host_source.resolve() and
               all((frozen / name).resolve() in includes for name in ('JSph.h', 'JSphGpu.h', 'C08StorageTrace.h'))
               and all(p.is_relative_to(frozen.resolve()) for p in includes if p.name.lower() in names)
               and all(not p.is_relative_to((S / 'source').resolve()) for p in includes),
               'Actual host includes leaked current public headers or missed observer header')
        before += [m.stat(host_obj), m.stat(dependencies)]
        calls.append(m.invoke(stages[1], [str(nvcc), *na], work, env))
        m.need(gpu_obj.is_file(), 'Private CUDA object missing')
        before.append(m.stat(gpu_obj))
        calls.append(m.invoke(stages[2], [str(link), *linked], work, env))
        copied = []
        for entry in runtime:
            src, dest = Path(entry['path']), out / Path(entry['path']).name
            m.need(not dest.exists(), 'Private companion output already exists')
            shutil.copy2(src, dest)
            m.need(dest.read_bytes() == src.read_bytes(), 'Original runtime companion copy differs')
            copied.append(m.stat(dest))
        m.verify(before)
        m.save(check, dict(stage=stage + '.build', passed=True, configuration=configuration,
            allowed_runtime_backend='GPU', program=m.stat(exe),
            preparation=m.stat(PREP), source_capture=prep['source_capture'], source_archive=prep['source_archive'],
            base_original_source_capture=base['source_capture'], base_original_source_archive=base['source_archive'],
            baseline_source_build=m.stat(base_path), base_program=base['program'],
            original_object_seal=m.stat(seal_path), retained_physical_objects=[m.stat(p) for p in retained],
            original_replaced_objects=[m.stat(p) for p in replaced.values()],
            replacement_objects=[m.stat(host_obj)], new_observer_objects=[m.stat(gpu_obj)],
            actual_link_objects=114, original_physical_CUDA_recompiled=0,
            physical_host_TUs_recompiled=1, new_observer_CUDA_TUs=1, original_main_unchanged=True,
            private_sources=[m.stat(p) for p in (host_source, cuda_source, frozen / 'C08StorageTrace.h')],
            archived_source_files=archived, host_dependencies=m.stat(dependencies),
            authoritative_CL_tlog=m.stat(ct), authoritative_LINK_tlog=m.stat(lt),
            resolved_library_tlog=m.stat(rt), authoritative_NVCC_log=log,
            CUDA_read_tlog=m.stat(cr), CUDA_write_tlog=m.stat(cw),
            intermediate=str(work), compiler_PATH_prepended=str(ccbin), PATH_cl_matches_ccbin=True,
            runtime=copied, calls=calls, macro=MACRO, macro_enabled_in_host_and_observer_TUs=True,
            undefined_old_macros=list(OLD_MACROS), primary_expression_bytes_retained=True,
            original_physical_CUDA_objects_retained=True,
            class_layout_changed=False, public_interfaces_changed=False, production_source_changed=False,
            source_note=m.stat(NOTE), consumed=before, consumed_stats_unchanged=True,
            CL_compile_invocations=1, CUDA_compile_invocations=1, link_invocations=1,
            full_project_builds=0, help_invocations=0, solver_invocations=0, native_decodes=0,
            VTK_invocations=0, physical_acceptance=False, SHA_scans=0))
        print('STORAGE_OBSERVER_BUILD_PASSED', configuration, str(exe), flush=True)
    except Exception as error:
        if not check.exists():
            found = [m.stat(L / (tag + '.call.json')) for tag in stages if (L / (tag + '.call.json')).exists()]
            m.save(check, dict(stage=stage + '.build', passed=False, configuration=configuration,
                first_failure=str(error), calls=found, consumed=before, partial_outputs_preserved=True,
                full_project_builds=0, help_invocations=0, solver_invocations=0, native_decodes=0,
                VTK_invocations=0, physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('configuration', choices=('Debug', 'Release'))
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Root full-read and separate configuration-specific build admission required')
    build(args.configuration)
