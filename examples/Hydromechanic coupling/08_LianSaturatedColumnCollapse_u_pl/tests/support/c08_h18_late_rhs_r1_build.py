"""Build the three late-state RHS entry + 86 original DebugCPU objects; never run it."""
import argparse, os, shutil, subprocess, zipfile
from pathlib import Path
import c08_fs_affine_cpu_r1_build as old

m, T, L, S = old.matrix, old.T, old.L, old.S
TAG = 'c08_h18_late_rhs_r1'
OUT = T / 'outputs' / (TAG + '_build')
CPP, NOTE = T / 'support' / (TAG + '.cpp'), T / 'notes' / (TAG + '.md')
BASE = L / 'c08_fs_matrix_cpu_r2.build.json'
RUN = L / 'c08_h18_n255_full3_r1.run.json'
NATIVE = L / 'c08_h18_n255_full3_native_r1.check.json'
REVIEW = L / 'c08_h18_n255_full3_review_r1.check.json'
ORIGINAL_CPP = T / 'support/c08_h18_storage_rhs_r2.cpp'
ORIGINAL_BUILDER = T / 'support/c08_h18_storage_rhs_r1_build.py'
ORIGINAL_BUILD = L / 'c08_h18_storage_rhs_r2.build.json'


def entry_proof():
    original = ORIGINAL_CPP.read_bytes()
    changes = [('C08H18StorageRhs', 'C08H18LateRhs', 1), ('Samples=91', 'Samples=301', 1), ('Parts[3]={30,60,90},Steps[3]={2060001,2120001,2180000}', 'Parts[3]={200,250,300},Steps[3]={2400001,2500001,2600000}', 1), ('full91', 'full301', 2), ('c08_h18_storage_rhs_r2', 'c08_h18_late_rhs_r1', 3), ('\\"source_parts\\":[30,60,90],\\"source_samples\\":91', '\\"source_parts\\":[200,250,300],\\"source_samples\\":301', 1), ('c08_h18_as05_n255_r1', 'c08_h18_n255_full3_r1', 5), ('c08_h18_n255_native_run_r1.check.json', 'c08_h18_n255_full3_native_r1.check.json', 1), ('c08_h18_n255_review_r1.check.json', 'c08_h18_n255_full3_review_r1.check.json', 1)]
    derived = original
    for old_token, new_token, count in changes:
        old_bytes, new_bytes = old_token.encode('utf-8'), new_token.encode('utf-8')
        m.need(derived.count(old_bytes) == count, 'Original entry mapping count differs: ' + old_token)
        derived = derived.replace(old_bytes, new_bytes)
    m.need(CPP.read_bytes() == derived, 'Late entry differs from the exact narrow original-r2 derivation')
    return dict(original_entry=m.stat(ORIGINAL_CPP), new_entry=m.stat(CPP), exact_replacements=changes,
                numerical_force_and_decomposition_body_unchanged=True, physical_steps=0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized', action='store_true')
    a = p.parse_args()
    m.need(a.execution_authorized, 'Author-only until root full-read; build permission does not admit execution')
    check = L / (TAG + '.build.json')
    stages = (TAG + '.compile', TAG + '.link')
    m.need(not OUT.exists() and not check.exists() and all(not (L / (q + s)).exists()
           for q in stages for s in ('.call.json', '.log')), 'Existing complete or partial build protected')
    before, calls = [], []
    try:
        prior = m.read(ORIGINAL_BUILD)
        m.need(prior['passed'] and prior['consumed_stats_unchanged'] and prior['configuration'] == 'DebugCPU'
               and prior['original_Single_no_hook'] and prior['actual_link_objects'] == 87
               and prior['source'] == m.stat(ORIGINAL_CPP), 'Original built r2 entry binding differs')
        old_builder = [q for q in prior['consumed'] if Path(q['path']).resolve() == ORIGINAL_BUILDER.resolve()]
        m.need(len(old_builder) == 1 and m.bind(old_builder[0]) == m.stat(ORIGINAL_BUILDER),
               'Original built r1 recipe binding differs')
        derivation = entry_proof()
        base, run, native, review = (m.read(q) for q in (BASE, RUN, NATIVE, REVIEW))
        m.need(base['passed'] and base['consumed_stats_unchanged'] and base['actual_link_objects'] == 87
               and base['retained_public_objects'] == 85 and base['GPU_actions'] == 0,
               'Closed original Raw CPU object list required')
        restored = m.read(m.bind(base['restored_source_build'])['path'])
        m.need(restored['passed'] and restored['configuration'] == 'DebugCPU' and restored['restored_original_source']
               and restored['consumed_stats_unchanged'] and restored['canonical_programs_unchanged']
               and restored['actual_typed_exit_code'] == restored['actual_Win32_exit'] == 0,
               'Successful restored original DebugCPU closure required')
        m.need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged']
               and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit'] == 0
               and run['actual_steps'] == 2600000 and run['saved_frames'] == 301 and run['geometry_profile'] == 'bedroles'
               and not run['keep_bed_overlap'] and run['AS_coefficient'] == .5 and run['AS_exponent'] == 2.55
               and run['fixed_dt_s'] == .000005 and run['hdp'] == 1.8
               and run['source_archive'] == restored['source_archive'] == base['raw_source_archive'],
               'Only completed original raw-FS Wendland AS05 n255 input admitted')
        m.need(native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations'] == 1
               and native['stage'] == 'c08_h18_n255_full3_native_r1' and not native['physical_acceptance']
               and review['stage'] == 'c08_h18_n255_full3_review_r1' and review['analysis_complete']
               and review['consumed_stats_unchanged'] and not review['physical_acceptance'],
               'Already-qualified full301 native and offline input seal required; no physical pass is implied')
        done = m.read(m.bind(native['native_completion'])['path'])
        folder = T / 'outputs/c08_h18_n255_full3_r1/native_r1'
        m.need(Path(native['native_completion']['path']).resolve() == (folder / 'completion.json').resolve()
               and done['passed'] and done['samples'] == 301 and done['completed_steps'] == 2600000
               and done['typed_arrays'] == 22 and done['typed_bytes_per_particle'] == 212
               and done['actual_native_IDs_per_frame'] == 6805 and done['soil_IDs'] == 5000
               and done['actual_fixed_IDs'] == 1805 and done['source_completed_step'] == 2000000
               and done['geometry_profile'] == 'bedroles' and not done['keep_bed_overlap']
               and done['ledger_checks'] == done['rho_cache_bits_checks'] == done['kappa_nondecreasing_from_PRE_checks'] == 1505000
               and done['P0_bits_checks'] == 2048305 and done['fixed_marker_checks'] == 543305
               and done['nonempty_signed_intervals'] == 301 and done['max_scalar_clock_error_s'] == 0
               and done['max_ledger_relative_error'] == 0 and not done['physical_acceptance'], 'Precise native layout/roles differ')
        before = [m.stat(q) for q in (Path(__file__), CPP, NOTE, ORIGINAL_CPP, ORIGINAL_BUILDER, ORIGINAL_BUILD,
                                    Path(old.__file__), Path(m.__file__), BASE, RUN, NATIVE, REVIEW)]
        before += [m.bind(base[q]) for q in ('restored_source_build', 'raw_source_capture', 'raw_source_archive',
                                           'authoritative_CL_tlog', 'authoritative_LINK_tlog', 'resolved_library_tlog', 'original_cpu_object')]
        before += [m.bind(restored[q]) for q in ('program', 'source_capture', 'source_archive', 'actual_call')]
        before += [m.bind(run[q]) for q in ('program', 'source_build', 'source_capture', 'source_archive',
                                          'source_pre_file', 'input_xml', 'actual_call', 'planned_steps', 'native_profile')]
        before += [m.bind(q) for q in run['seed']] + [m.bind(native[q]) for q in ('actual_call', 'native_completion', 'metadata', 'reader_build')]
        for receipt, entry in ((RUN, run['actual_call']), (NATIVE, native['actual_call'])):
            c = m.read(entry['path'])
            m.need(c['actual_Popen_wait_exit'] == c['actual_Win32_exit'] == 0, 'Actual owned source call failed: ' + str(receipt))
        for leaf in ('typed22.bin', 'typed22_layout.csv', 'clocks.csv'):
            matches = [q for q in review['consumed'] if Path(q['path']).resolve() == (folder / leaf).resolve()]
            m.need(len(matches) == 1, 'One sealed full301 review input required: ' + leaf)
            before.append(m.bind(matches[0]))
        raw = [m.bind(q) for q in base['project_objects']['Raw'] if q != base['fixture_object']]
        ct, lt, rt = (Path(base[q]['path']) for q in ('authoritative_CL_tlog', 'authoritative_LINK_tlog', 'resolved_library_tlog'))
        mains = [q for q in old.blocks(ct) if len(q[0]) == 1 and Path(q[0][0]).name.lower() == 'main.cpp']
        links = old.blocks(lt)
        m.need(len(mains) == len(links) == 1, 'One authoritative original main compile/link block required')
        ca, la = old.arguments(' '.join(mains[0][1])), old.arguments(' '.join(links[0][1]))
        original = {Path(q).resolve() for q in la if q.lower().endswith('.obj')}
        physical = {Path(q['path']).resolve() for q in raw}
        mainobjs = {q for q in original if q.name.lower() == 'main.obj'}
        m.need(len(raw) == len(physical) == 86 and len(original) == 87 and len(mainobjs) == 1
               and original == physical | mainobjs and any(q.name.lower() == 'jsphcpusingle.obj' for q in physical)
               and Path(base['original_cpu_object']['path']).resolve() in physical,
               'Exactly86 original physical objects, including original Single and JSphCpu, required')
        before += raw + [m.stat(q) for q in mainobjs]
        libraries = [Path(q.strip('"')).resolve() for q in rt.read_text(encoding='utf-16').splitlines()
                     if not q.startswith('^') and q.lower().endswith('.lib')]
        runtime = [m.bind(q) for q in base['runtime']]
        m.need(libraries and len(runtime) == 7, 'Retained resolved libraries/runtime required')
        before += runtime + [m.stat(q) for q in libraries]
        sourceids = [i for i, q in enumerate(ca) if Path(q).name.lower() == 'main.cpp']
        m.need(len(sourceids) == 1 and all(q in ca for q in ('/MTd', '/Od', '/RTC1', '/Zi', '/fp:precise', '/openmp'))
               and not any('_WITHGPU' in q or q.lower().startswith(('/std:', '/i')) for q in ca), 'Original CPU ABI and clean include recipe required')
        obj, exe = OUT / 'entry.obj', OUT / 'C08H18LateRhsR1.exe'
        ca[sourceids[0]] = str(CPP)
        for prefix, target in (('/Fo', obj), ('/Fd', OUT / 'entry_compile.pdb')):
            ids = [i for i, q in enumerate(ca) if q.lower().startswith(prefix.lower())]
            m.need(len(ids) == 1, 'One compiler output token required: ' + prefix)
            ca[ids[0]] = prefix + str(target)
        ca += ['/std:c++17', '/D_HAS_STD_BYTE=0', '/I' + str(OUT / 'headers/src/source'), '/sourceDependencies', str(OUT / 'dependencies.json')]
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Matching MSVC setup failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines()
                                             if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532', 'Exact retained ABI compiler required')
        for key in ('CL', '_CL_'): env.pop(key, None)
        env['LIB'] = ';'.join(dict.fromkeys(str(q.parent) for q in libraries))
        cl = Path(env['VCTOOLSINSTALLDIR']) / 'bin/Hostx64/x64/cl.exe'
        before += [m.stat(cl), m.stat(cl.with_name('link.exe'))]
        m.verify(before)
        OUT.mkdir()
        headers = []
        with zipfile.ZipFile(restored['source_archive']['path']) as z:
            for name in z.namelist():
                relative = Path(name)
                if relative.suffix.lower() not in ('.h', '.cuh'): continue
                m.need(name.startswith('src/source/') and not relative.is_absolute() and '..' not in relative.parts, 'Archive include escaped source tree')
                destination = OUT / 'headers' / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                content = z.read(name)
                destination.write_bytes(content)
                m.need(destination.read_bytes() == content, 'Archived header copy differs')
                headers.append(m.stat(destination))
        m.need(len(headers) == 160, 'Exact schema2 archived header inventory required')
        calls.append(m.invoke(stages[0], [str(cl), *ca], S / 'VS', env))
        deps = m.read(OUT / 'dependencies.json')['Data']
        include_root = (OUT / 'headers/src/source').resolve()
        includes = {Path(q).resolve() for q in deps['Includes']}
        names = {Path(q['path']).name.lower() for q in headers}
        m.need(Path(deps['Source']).resolve() == CPP.resolve() and all(include_root / q in includes
               for q in ('JSph.h', 'JSphCpu.h', 'JSphCpuSingle.h', 'JCellSearch_inline.h', 'FunSphKernel.h'))
               and all(q.is_relative_to(include_root) for q in includes if q.name.lower() in names)
               and all(not q.is_relative_to(S / 'source') for q in includes), 'Actual compilation used a nonarchived public header')
        outputs = {'/out:': exe, '/pdb:': OUT / 'entry.pdb', '/implib:': OUT / 'entry.lib', '/ltcgout:': OUT / 'entry.iobj'}
        linked, seen = [], set()
        for value in la:
            if value.lower().endswith('.obj') and Path(value).name.lower() == 'main.obj': value = str(obj)
            for prefix, target in outputs.items():
                if value.lower().startswith(prefix): value = prefix + str(target); seen.add(prefix); break
            linked.append(value)
        final = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        m.need(seen == set(outputs) and len(final) == len(set(final)) == 87 and set(final) == physical | {obj.resolve()}, 'Exact new-entry plus86-original link required')
        calls.append(m.invoke(stages[1], [str(cl.with_name('link.exe')), *linked], S / 'VS', env))
        copied = []
        for entry in runtime:
            destination = OUT / Path(entry['path']).name
            shutil.copy2(entry['path'], destination)
            m.need(destination.read_bytes() == Path(entry['path']).read_bytes(), 'Frozen runtime copy differs')
            copied.append(m.stat(destination))
        m.verify(before + headers)
        m.save(check, dict(stage=TAG + '.build', passed=True, configuration='DebugCPU', program=m.stat(exe), source=m.stat(CPP), note=m.stat(NOTE),
            source_build=base['restored_source_build'], source_capture=restored['source_capture'], source_archive=restored['source_archive'],
            original_object_list=m.stat(BASE), retained_physical_objects=raw, actual_link_objects=87, original_Single_no_hook=True,
            new_entry_objects=1, physical_objects_compiled=0, archived_headers=headers, dependencies=m.stat(OUT / 'dependencies.json'),
            source_run=m.stat(RUN), source_native=m.stat(NATIVE), source_review=m.stat(REVIEW),
            entry_derivation=derivation, source_PRE=run['source_pre_file'],
            input_xml=run['input_xml'], runtime=copied, calls=calls, consumed=before, consumed_stats_unchanged=True,
            compile_invocations=1, link_invocations=1, component_invocations=0, solver_invocations=0, GPU_actions=0,
            public_source_changed=False, canonical_programs_changed=False, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        if not check.exists():
            m.save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=calls, consumed=before,
                component_invocations=0, solver_invocations=0, GPU_actions=0, physical_acceptance=False, partial_outputs_preserved=True))
        raise


if __name__ == '__main__': main()
