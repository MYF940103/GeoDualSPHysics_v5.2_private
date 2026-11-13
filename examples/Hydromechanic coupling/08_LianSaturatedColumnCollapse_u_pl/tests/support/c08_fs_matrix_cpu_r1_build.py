"""Build one CPU matrix entry and two closed-object controls; never execute either program."""
import argparse, os, shutil, subprocess
from pathlib import Path
import c08_fs_affine_cpu_r1_build as previous

m = previous.matrix
T, L, S = previous.T, previous.L, previous.S
TAG = 'c08_fs_matrix_cpu_r1'
OUT = T / 'outputs' / (TAG + '_build')
FIXTURE = T / 'support' / (TAG + '.cpp')
NOTE = T / 'notes' / (TAG + '_build.md')
BASE = L / 'c08_fs_normal_taylor_cpu_r1.build.json'
INTERVENTION = 'free_surface_normal_taylor_projection'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Author-only until root full-read of both entry and builder')
    check = L / (TAG + '.build.json')
    stages = (TAG + '.compile', TAG + '.Raw.link', TAG + '.Normal.link')
    m.need(not OUT.exists() and not check.exists() and all(not (L / (q + suffix)).exists()
           for q in stages for suffix in ('.call.json', '.log')), 'Existing complete or partial matrix build protected')
    before, calls = [], []
    try:
        base = m.read(BASE)
        m.need(base['passed'] and base['intervention'] == INTERVENTION and base['consumed_stats_unchanged']
               and base['actual_typed_exit_code'] == base['actual_Win32_exit'] == 0
               and base['retained_public_objects'] == 85 and base['actual_link_objects'] == 87,
               'Completed closed normal-Taylor CPU component build required')
        restored_path = Path(m.bind(base['restored_source_build'])['path'])
        restored = m.read(restored_path)
        m.need(restored['passed'] and restored['configuration'] == 'DebugCPU' and restored['restored_original_source']
               and restored['consumed_stats_unchanged'] and restored['actual_link_objects'] == 87
               and restored['actual_typed_exit_code'] == restored['actual_Win32_exit'] == 0,
               'Closed restored original DebugCPU build required')
        before = [m.stat(q) for q in (BASE, FIXTURE, NOTE, Path(__file__), Path(previous.__file__), Path(m.__file__))]
        before += [m.bind(base[q]) for q in ('program', 'source_capture', 'source_archive', 'baseline_source_build',
                                            'restored_source_build', 'candidate_object')]
        for entry in base['calls']:
            before.append(m.bind(entry))
            actual = m.read(entry['path'])
            m.need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0
                   and actual['ownership_failure'] is None, 'Actual candidate compile/link ownership required')
        before += [m.bind(restored[q]) for q in ('program', 'source_capture', 'source_archive', 'actual_call')]
        build_call = m.read(restored['actual_call']['path'])
        roots = [q.split('=', 1)[1] for q in build_call['arguments'] if q.startswith('/p:IntDir=')]
        m.need(build_call['actual_Popen_wait_exit'] == build_call['actual_Win32_exit'] == 0
               and '/p:VCToolsVersion=14.36.32532' in build_call['arguments'] and len(roots) == 1,
               'Actual restored MSVC14.36 build recipe required')
        intdir = Path(roots[0]).resolve()
        m.need(intdir == (Path(os.environ['TEMP']) / 'c08_restore_cpu_r1/DebugCPU/int').resolve(), 'Unexpected restored tlog tree')
        ct, lt, rt = (intdir / 'DualSPHysics.tlog' / q for q in
                      ('CL.command.1.tlog', 'link.command.1.tlog', 'link.read.1.tlog'))
        for path in (ct, lt, rt):
            entries = [q for q in base['consumed'] if Path(q['path']).resolve() == path.resolve()]
            m.need(len(entries) == 1, 'One candidate-bound authoritative tlog required')
            before.append(m.bind(entries[0]))
        mains = [q for q in previous.blocks(ct) if len(q[0]) == 1 and Path(q[0][0]).name.lower() == 'main.cpp']
        links = previous.blocks(lt)
        m.need(len(mains) == len(links) == 1, 'One authoritative main CL block and link block required')
        ca, la = previous.arguments(' '.join(mains[0][1])), previous.arguments(' '.join(links[0][1]))
        original = {Path(q).resolve() for q in la if q.lower().endswith('.obj')}
        retained_entries = [m.bind(q) for q in base['retained_project_objects']]
        replaced_entries = [m.bind(q) for q in base['replaced_original_objects']]
        retained = {Path(q['path']).resolve() for q in retained_entries}
        replaced = {Path(q['path']).name.lower(): Path(q['path']).resolve() for q in replaced_entries}
        m.need(len(original) == 87 and len(retained) == 85 and set(replaced) == {'main.obj', 'jsphcpu.obj'}
               and original == retained | set(replaced.values()) and all(q.parent == intdir for q in original),
               'Exactly85 shared originals plus original main and JSphCpu required')
        before += retained_entries + replaced_entries
        capture = m.read(base['source_capture']['path'])
        capture_root = Path(base['source_capture']['path']).parent / 'src'
        headers = [m.stat(S / Path(q['path']).relative_to(capture_root)) for q in capture['files']
                   if Path(q['path']).suffix.lower() in ('.h', '.cuh')]
        harness = (FIXTURE.parent / '../../../02_TerzaghiConsolidation_q0_PR/tests/support/upl_p2_feedback_harness_r1.cpp').resolve()
        before += headers + [m.stat(harness)]
        libraries = [Path(q.strip('"')).resolve() for q in rt.read_text(encoding='utf-16').splitlines()
                     if not q.startswith('^') and q.lower().endswith('.lib')]
        m.need(headers and libraries and all(q.is_file() for q in libraries), 'Current headers and resolved library closure required')
        before += [m.stat(q) for q in libraries]
        leaves = ('DsphConfig.xml', 'ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll',
                  'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
        runtime = []
        for leaf in leaves:
            found = [q for q in base['runtime'] if Path(q['path']).name == leaf]
            m.need(len(found) == 1, 'One frozen runtime companion required: ' + leaf)
            runtime.append(m.bind(found[0]))
        before += runtime
        source_ids = [i for i, q in enumerate(ca) if Path(q).name.lower() == 'main.cpp']
        m.need(len(source_ids) == 1 and all(q in ca for q in ('/MTd', '/Od', '/RTC1', '/Zi', '/fp:precise', '/openmp'))
               and not any('_WITHGPU' in q or q.lower().startswith('/std:') for q in ca), 'Original CPU Debug ABI/FP flags required')
        obj = OUT / 'fixture.obj'
        ca[source_ids[0]] = str(FIXTURE)
        for prefix, target in (('/Fo', obj), ('/Fd', OUT / 'fixture_compile.pdb')):
            ids = [i for i, q in enumerate(ca) if q.lower().startswith(prefix.lower())]
            m.need(len(ids) == 1, 'One case-correct compiler output token required')
            ca[ids[0]] = prefix + str(target)
        ca += ['/std:c++17', '/D_HAS_STD_BYTE=0', '/I' + str(S / 'source')]
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Matching MSVC setup failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines()
                                             if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Exact closed Debug ABI compiler required')
        for key in ('CL', '_CL_'): env.pop(key, None)
        env['LIB'] = ';'.join(dict.fromkeys(str(q.parent) for q in libraries))
        cl = Path(env['VCTOOLSINSTALLDIR']) / 'bin/Hostx64/x64/cl.exe'
        before += [m.stat(cl), m.stat(cl.with_name('link.exe'))]
        cpu = {'Raw': replaced['jsphcpu.obj'], 'Normal': Path(base['candidate_object']['path']).resolve()}
        m.verify(before)
        OUT.mkdir()
        calls.append(m.invoke(stages[0], [str(cl), *ca], S / 'VS', env))
        m.need(obj.is_file(), 'Actual case-correct /Fo entry output missing')
        before.append(m.stat(obj))
        programs, closures = {}, {}
        for label, cpu_object in cpu.items():
            exe = OUT / (label + '.exe')
            outputs = {'/out:': exe, '/pdb:': OUT / (label + '.pdb'),
                       '/implib:': OUT / (label + '.lib'), '/ltcgout:': OUT / (label + '.iobj')}
            linked, seen = [], set()
            for value in la:
                if value.lower().endswith('.obj'):
                    leaf = Path(value).name.lower()
                    if leaf == 'main.obj': value = str(obj)
                    elif leaf == 'jsphcpu.obj': value = str(cpu_object)
                for prefix, target in outputs.items():
                    if value.lower().startswith(prefix): value = prefix + str(target); seen.add(prefix); break
                linked.append(value)
            final = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
            m.need(seen == set(outputs) and len(final) == len(set(final)) == 87
                   and set(final) == retained | {cpu_object.resolve(), obj.resolve()}, 'Exact87-object ' + label + ' closure required')
            calls.append(m.invoke(TAG + '.' + label + '.link', [str(cl.with_name('link.exe')), *linked], S / 'VS', env))
            programs[label], closures[label] = m.stat(exe), [m.stat(q) for q in final]
        copied = []
        for entry in runtime:
            destination = OUT / Path(entry['path']).name
            shutil.copy2(entry['path'], destination)
            m.need(destination.read_bytes() == Path(entry['path']).read_bytes(), 'Frozen runtime copy differs')
            copied.append(m.stat(destination))
        m.verify(before)
        m.save(check, dict(stage=TAG + '.build', passed=True, configuration='DebugCPU', intervention=INTERVENTION,
            programs=programs, fixture=m.stat(FIXTURE), fixture_object=m.stat(obj), note=m.stat(NOTE), candidate_build=m.stat(BASE),
            source_capture=base['source_capture'], source_archive=base['source_archive'], restored_source_build=base['restored_source_build'],
            raw_source_capture=restored['source_capture'], raw_source_archive=restored['source_archive'],
            original_cpu_object=m.stat(cpu['Raw']), candidate_object=base['candidate_object'], retained_project_objects=retained_entries,
            retained_public_objects=85, project_objects=closures, actual_link_objects=87, shared_entry_object=True,
            authoritative_CL_tlog=m.stat(ct), authoritative_LINK_tlog=m.stat(lt), resolved_library_tlog=m.stat(rt),
            retained_harness=m.stat(harness), current_headers=headers, runtime=copied, calls=calls,
            actual_typed_exit_code=0, actual_Win32_exit=0, consumed=before, consumed_stats_unchanged=True,
            public_source_changed=False, GPU_actions=0, GPU_stage_held=True, help_invocations=0, fixture_invocations=0,
            solver_invocations=0, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        actual_calls = [m.stat(L / (q + '.call.json')) for q in stages if (L / (q + '.call.json')).is_file()]
        if not check.exists():
            m.save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=actual_calls,
                consumed=before, fixture_invocations=0, solver_invocations=0, GPU_actions=0, physical_acceptance=False))
        raise


if __name__ == '__main__': main()
