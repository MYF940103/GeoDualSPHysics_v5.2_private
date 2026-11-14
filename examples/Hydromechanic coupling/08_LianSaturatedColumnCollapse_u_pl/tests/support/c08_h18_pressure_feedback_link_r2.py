"""Adopt the sealed successful r1 CL output, correct only its include audit, and link once."""
import argparse
import os
import shutil
import subprocess
from pathlib import Path
import c08_h18_pressure_feedback_r1_build as first

m, T, L, S = first.m, first.T, first.L, first.S
TAG = 'c08_h18_pressure_feedback_link_r2'
OLD = T / 'outputs/c08_h18_pressure_feedback_r1_build'
OUT = T / 'outputs' / (TAG + '_build')
NOTE = T / 'notes' / (TAG + '.md')
FAILED = L / 'c08_h18_pressure_feedback_r1.build.json'
COMPILE = L / 'c08_h18_pressure_feedback_r1.compile.call.json'
BASE = L / 'c08_h18_as03_rhs_r1.build.json'
LINK_RECIPE = L / 'c08_h18_as03_rhs_r1.link.call.json'
AUDIT = L / 'c08_h18_pressure_feedback_r1.build_failure_audit_r1.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    m.need(parser.parse_args().execution_authorized,
           'Root admission required; this helper links only and never executes the component')
    check = L / (TAG + '.build.json'); stage = TAG + '.link'
    m.need(not OUT.exists() and not check.exists() and
           all(not (L / (stage + suffix)).exists() for suffix in ('.call.json', '.log')),
           'Existing failed/partial/complete r2 artifacts protected')
    before, calls = [], []
    try:
        failed, cl, base, link, audit = map(m.read, (FAILED, COMPILE, BASE, LINK_RECIPE, AUDIT))
        m.need(audit['passed'] and audit['failure_kind'] == 'postcompile_expectation_of_unused_material_header' and
            audit['actual_compile_exit'] == 0 and audit['link_has_not_run'] and audit['component_has_not_run'] and
            m.bind(audit['failed_build']) == m.stat(FAILED) and
            m.bind(audit['actual_compile']) == m.stat(COMPILE), 'Root postcompile adoption audit required')
        m.need(failed['stage'] == 'c08_h18_pressure_feedback_r1.build' and not failed['passed'] and
            failed['first_failure'] == 'Actual compilation missed frozen fragments or leaked public headers' and
            failed['component_invocations'] == failed['solver_invocations'] == failed['GPU_actions'] == 0 and
            len(failed['calls']) == 1 and m.bind(failed['calls'][0]) == m.stat(COMPILE),
            'Only the preserved post-CL dependency-audit failure may be adopted')
        m.need(cl['stage'] == 'c08_h18_pressure_feedback_r1.compile' and
            cl['actual_Popen_wait_exit'] == cl['actual_Win32_exit'] == 0 and
            cl['ownership_failure'] is None and Path(cl['child']['exe']).resolve() == Path(cl['program']).resolve() and
            cl['child']['argv'] == [cl['program'], *cl['arguments']] and
            cl['child']['parent_pid'] == cl['owner']['pid'], 'Sealed owned CL0 receipt required')
        m.need(base['passed'] and base['configuration'] == 'DebugCPU' and
            base['consumed_stats_unchanged'] and base['original_Single_no_hook'] and
            base['physical_objects_compiled'] == 0 and base['actual_link_objects'] == 87 and
            link['actual_Popen_wait_exit'] == link['actual_Win32_exit'] == 0 and
            link['ownership_failure'] is None, 'Original87-object frozen ABI/link recipe required')
        # Retain every original protected source/header/object/native/CSV/receipt stat.
        before = [m.bind(q) for q in failed['consumed']]
        before += [m.stat(q) for q in (Path(__file__), NOTE, FAILED, COMPILE, LINK_RECIPE, AUDIT, Path(first.__file__))]
        before.append(m.bind(cl['log']))
        fragments, proof = first.fragments()
        includes = []
        for name, content in fragments.items():
            path = OLD / name
            original_binding = next(q for q in failed['consumed'] if Path(q['path']).resolve() == path.resolve())
            includes.append(m.bind(original_binding))
            m.need(path.read_bytes() == content, 'Original generated fragment changed: ' + name)
        deps_path, entry, pdb, idb = [OLD / q for q in
            ('dependencies.json', 'entry.obj', 'entry_compile.pdb', 'entry_compile.idb')]
        # Object/dependencies use the root's explicit post-failure stat seal, not a compile-time claim.
        # Compiler PDB/IDB are first bound for adoption here; no compiler is invoked.
        adopted = [m.bind(audit['actual_dependencies']), m.bind(audit['adoptable_object_stat_now']),
                   m.stat(pdb), m.stat(idb)]
        m.need(Path(adopted[0]['path']).resolve() == deps_path.resolve() and
               Path(adopted[1]['path']).resolve() == entry.resolve(), 'Root adoption products differ')
        m.need(all(q['bytes'] > 0 for q in adopted), 'Successful compiler products must be nonempty')
        before += adopted
        deps = m.read(deps_path)['Data']
        actual = {Path(q).resolve() for q in deps['Includes']}
        roots = [Path(q[2:]).resolve() for q in cl['arguments'] if q.startswith('/I')]
        m.need(len(roots) == 1 and str(first.CPP) in cl['arguments'] and
            '/Fo' + str(entry) in cl['arguments'] and '/Fd' + str(pdb) in cl['arguments'] and
            '/sourceDependencies' in cl['arguments'] and str(deps_path) in cl['arguments'] and
            all(q in cl['arguments'] for q in ('/Od', '/MTd', '/RTC1', '/fp:precise', '/openmp', '/std:c++17')),
            'Actual compiled entry/output/header ABI differs')
        headerroot = roots[0]
        objects = [m.bind(q) for q in base['retained_physical_objects']]
        headers = [m.bind(q) for q in base['archived_headers']]
        runtime = [m.bind(q) for q in base['runtime']]
        names = {Path(q['path']).name.lower() for q in headers}
        needed = ('JSph.h', 'JSphCpu.h', 'JSphCpuSingle.h', 'FunSphKernel.h')
        # Only the unused FunSoilMaterial.h obligatory-presence assertion is removed.
        # Its archived inventory/stat is still protected, like all other original headers.
        m.need(Path(deps['Source']).resolve() == first.CPP.resolve() and
            all(Path(q['path']).resolve() in actual for q in includes) and
            all((headerroot / q).resolve() in actual for q in needed) and
            all(q.is_relative_to(headerroot) for q in actual if q.name.lower() in names) and
            all(not q.is_relative_to((S / 'source').resolve()) for q in actual) and
            (headerroot / 'FunSoilMaterial.h').resolve() not in actual,
            'The original remaining dependency gates must all pass; sole absent header is unused material')
        m.need(len(objects) == 86 and len(headers) == 160 and len(runtime) == 7,
               'Unchanged86-object/160-header/7-runtime closure required')
        object_list = m.read(m.bind(base['original_object_list'])['path'])
        lib_tlog = m.bind(object_list['resolved_library_tlog']); before.append(lib_tlog)
        libraries = [Path(q.strip('"')).resolve() for q in Path(lib_tlog['path']).read_text(encoding='utf-16').splitlines()
                     if not q.startswith('^') and q.lower().endswith('.lib')]
        before += [m.stat(q) for q in libraries]
        oldroot = Path(base['program']['path']).parent
        exe = OUT / 'C08H18PressureFeedbackR1.exe'
        arguments = []
        for q in link['arguments']:
            if q.lower().endswith('.obj') and Path(q).resolve() == (oldroot / 'entry.obj').resolve():
                arguments.append(str(entry))
            else:
                arguments.append(q.replace(str(oldroot), str(OUT)).replace(Path(base['program']['path']).name, exe.name))
        linked = [Path(q).resolve() for q in arguments if q.lower().endswith('.obj')]
        m.need(len(linked) == len(set(linked)) == 87 and
            set(linked) == {Path(q['path']).resolve() for q in objects} | {entry.resolve()},
            'Only the adopted CL0 entry plus86 original physical objects may link')
        m.need(not (L / 'c08_h18_pressure_feedback_r1.link.call.json').exists(),
               'Original r1 must have stopped before any linker invocation')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        m.need(setup.returncode == 0, 'Matching original MSVC environment setup failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in
            setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        m.need(env['VCTOOLSVERSION'] == '14.36.32532' and libraries, 'Same original compiler/library ABI required')
        env.pop('CL', None); env.pop('_CL_', None)
        env['LIB'] = ';'.join(dict.fromkeys(str(q.parent) for q in libraries))
        before.append(m.stat(link['program'])); m.verify(before); OUT.mkdir()
        calls.append(m.invoke(stage, [link['program'], *arguments], S / 'VS', env))
        copied = []
        for q in runtime:
            dest = OUT / Path(q['path']).name; shutil.copy2(q['path'], dest)
            m.need(dest.read_bytes() == Path(q['path']).read_bytes(), 'Runtime copy differs')
            copied.append(m.stat(dest))
        m.verify(before)
        m.save(check, dict(stage=TAG + '.build', passed=True, configuration='DebugCPU',
            source=m.stat(first.CPP), note=m.stat(NOTE), program=m.stat(exe),
            source_build=base['source_build'], source_capture=base['source_capture'], source_archive=base['source_archive'],
            original_object_list=base['original_object_list'], retained_physical_objects=objects,
            archived_headers=headers, runtime=copied, generated_includes=includes, entry_derivation=proof,
            adopted_compile=m.stat(COMPILE), adopted_compile_log=m.bind(cl['log']),
            adopted_compiler_products_stat_now=adopted, root_postfailure_adoption_audit=m.stat(AUDIT),
            entry_first_sealed_in_failed_build_audit=True, compiler_PDB_IDB_first_bound_for_adoption_here=True, adopted_entry_object=m.stat(entry),
            dependencies=m.stat(deps_path), original_failed_build=m.stat(FAILED),
            only_removed_obligatory_header='FunSoilMaterial.h', actual_required_headers=list(needed),
            unused_material_header_still_stat_protected=True, calls=calls,
            actual_link_objects=87, new_entry_objects=0, adopted_entry_objects=1,
            physical_objects_compiled=0, compile_invocations=0, adopted_original_compile_invocations=1,
            link_invocations=1, original_Single_no_hook=True, original_CPP_and_includes_unchanged=True,
            original_main_stamps_failed_r1_receipt_without_interpreting_pass=True,
            component_stage='c08_h18_pressure_feedback_r1', component_max_actual_force_calls=34,
            consumed=before, consumed_stats_unchanged=True, component_invocations=0,
            solver_invocations=0, GPU_actions=0, SHA_scans=0, public_source_changed=False,
            canonical_programs_changed=False, no_automatic_component=True, physical_acceptance=False))
    except Exception as error:
        if not check.exists():
            m.save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=calls,
                consumed=before, original_r1_failure_preserved=True, partial_outputs_preserved=True,
                compile_invocations=0, component_invocations=0, solver_invocations=0,
                GPU_actions=0, SHA_scans=0, physical_acceptance=False))
        raise


if __name__ == '__main__': main()
