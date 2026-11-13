"""Adopt sealed r1 printf source; repair only compiler PATH and compile/link to fresh r2 outputs."""
import argparse, os, shutil, subprocess
from pathlib import Path
import c08_h18_wall_fail_gpu_r1_build as old

T, S, L = old.T, old.S, old.L
TAG = 'c08_h18_wall_fail_gpu_r2'
OUT = T / 'outputs' / (TAG + '_build')
PROGRAM = OUT / 'DualSPHysics5.2_GEO_win64.exe'
NOTE = T / 'notes' / (TAG + '.md')
FAILED = L / 'c08_h18_wall_fail_gpu_r1.build.json'
FAILED_CALL = L / 'c08_h18_wall_fail_gpu_r1.compile.call.json'
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke


def build():
    check = L / (TAG + '.build.json')
    need(not OUT.exists() and all(not (L / (TAG + q)).exists() for q in
         ('.build.json', '.compile.call.json', '.compile.log', '.link.call.json', '.link.log')),
         'Existing complete or partial r2 artifacts are protected')
    before = []
    try:
        failed, call = read(FAILED), read(FAILED_CALL)
        need(failed['passed'] is False and call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 1
             and call['typed_returncode_captured_before_postchecks'] and call['ownership_failure'] is None,
             'Closed original r1 compiler failure required')
        need(Path(bind(call['log'])['path']).read_text(encoding='utf-8').strip()
             == "nvcc fatal   : Compiler 'cl.exe' in PATH different than the one specified with -ccbin",
             'Only the recorded pre-compilation compiler-PATH failure is admitted')
        need(not (old.OUT / 'JSphGpu_ker.cu.obj').exists() and not old.PROGRAM.exists()
             and not (L / 'c08_h18_wall_fail_gpu_r1.link.call.json').exists(),
             'R1 must have no object, link call or program')
        before = [bind(q) for q in failed['consumed']]
        before += [stat(FAILED), stat(FAILED_CALL), bind(call['log']), stat(__file__), stat(NOTE)]
        need(stat(FAILED_CALL) in failed['calls'], 'R1 failure receipt does not bind this actual compile call')
        capture = stat(old.CAP / 'source.json')
        need(capture in failed['consumed'], 'Prepared r1 capture is not sealed by the failure receipt')
        source = read(capture['path'])
        archive = bind(source['archive'])
        cu, wall = bind(source['private_gpu_source']), bind(source['private_wall_include'])
        need(source['intervention'] == 'terminal_rejection_printf_only'
             and source['exact_inverse_original_bytes'] and not source['CXX_locals_added']
             and not source['primary_snapshot_added'] and not source['public_interfaces_changed']
             and not source['physical_arithmetic_changed']
             and set(source['modified_members']) == {'src/source/JSphGpu_ker.cu', 'src/source/JSphGpu_mdbc_ker.cuh'}
             and all(q in failed['consumed'] for q in [archive, cu, wall, *source['source_files']]),
             'Adopt only the sealed r1 inverse-proved printf source and complete frozen closure')
        baseline = read(old.BASE)
        need(baseline['passed'] and baseline['configuration'] == 'Release' and baseline['consumed_stats_unchanged']
             and source['baseline_source_capture'] == baseline['source_capture']
             and source['baseline_source_archive'] == baseline['source_archive'],
             'Prepared r1 source and schema2 baseline differ')
        intdir = Path(baseline['intermediate'])
        tlog = intdir / 'DualSPHysics.tlog/link.command.1.tlog'
        need(stat(tlog) in failed['consumed'], 'Original link command must remain sealed')
        lines = tlog.read_text(encoding='utf-16').splitlines()
        need(sum(q.startswith('^') for q in lines) == 1, 'One original link block required')
        link_args = old.windows_args(' '.join(q for q in lines if q and not q.startswith('^')))
        objects = [Path(q).resolve() for q in link_args if q.lower().endswith('.obj')]
        replacements = [q for q in objects if q.name.lower() == 'jsphgpu_ker.cu.obj']
        need(len(objects) == len(set(objects)) == 113 and len(replacements) == 1
             and sum(q.name.lower() == 'main.obj' for q in objects) == 1
             and all(q.parent == intdir.resolve() and stat(q) in failed['consumed'] for q in objects),
             'Exactly the same 113 original schema2 objects, including main, are required')
        retained = [q for q in objects if q != replacements[0]]
        compile_args = list(call['arguments'])
        need(compile_args.count('-ccbin') == compile_args.count('-o') == compile_args.count('--keep-dir') == 1
             and compile_args[-1] == cu['path']
             and '-I' + str(Path(cu['path']).parent) in compile_args
             and sum('/Fdphysical.pdb' in q for q in compile_args) == 1
             and not any('C08_STAGE_TRACE' in q or 'C08_CAUSAL_TRACE' in q for q in compile_args),
             'Sealed r1 source/include/host-PDB compiler argv required')
        ccbin = Path(compile_args[compile_args.index('-ccbin') + 1])
        need(ccbin.name.lower() == 'x64' and ccbin.parent.name.lower() == 'hostx86'
             and '/14.36.32532/' in ccbin.as_posix(), 'Preserve original HostX86/x64 MSVC directory')
        obj = OUT / 'JSphGpu_ker.cu.obj'
        compile_args[compile_args.index('-o') + 1] = str(obj)
        compile_args[compile_args.index('--keep-dir') + 1] = str(OUT)
        outputs = {'/out:': PROGRAM, '/pdb:': OUT / 'DualSPHysics5.2_GEO_win64.pdb',
                   '/implib:': OUT / 'DualSPHysics5.2_GEO_win64.lib',
                   '/ltcgout:': OUT / 'DualSPHysics5.2_GEO_win64.iobj'}
        linked, seen = [], set()
        for argument in link_args:
            if argument.lower().endswith('.obj') and Path(argument).resolve() == replacements[0]:
                argument = str(obj)
            for prefix, target in outputs.items():
                if argument.lower().startswith(prefix):
                    argument = prefix + str(target)
                    seen.add(prefix)
                    break
            linked.append(argument)
        linked_objects = [Path(q).resolve() for q in linked if q.lower().endswith('.obj')]
        need(seen == set(outputs) and len(linked_objects) == 113
             and set(linked_objects) == set(retained) | {obj.resolve()},
             'Link must replace only one CUDA object and redirect four output paths')
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode == 0, 'Original MSVC environment setup failed')
        env = {key.upper(): value for key, value in os.environ.items()}
        env.update(q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('='))
        env = {key.upper(): value for key, value in env.items()}
        need(env['VCTOOLSVERSION'] == '14.36.32532', 'Original MSVC version required')
        for key in ('CL', '_CL_', 'NVCC_PREPEND_FLAGS', 'NVCC_APPEND_FLAGS'):
            env.pop(key, None)
        env['PATH'] = str(ccbin) + os.pathsep + env.get('PATH', '')
        actual_cl = shutil.which('cl.exe', path=env['PATH'])
        need(actual_cl is not None and Path(actual_cl).samefile(ccbin / 'cl.exe'),
             'Owned compiler PATH must select exactly -ccbin/cl.exe')
        link = ccbin / 'link.exe'
        before += [stat(actual_cl), stat(call['program']), stat(link)]
        runtime_leaves = ('DsphConfig.xml', 'ChronoEngine.dll', 'dsphchrono.dll', 'vcomp140.dll',
                          'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll')
        runtime = [bind(next(q['destination'] for q in baseline['runtime']
                             if Path(q['destination']['path']).name == leaf)) for leaf in runtime_leaves]
        need(all(q in failed['consumed'] for q in runtime), 'Adopt exactly the same frozen schema2 runtime')
        need(all(stat(q['path']) == q for q in before), 'Sealed r1/baseline input changed before compilation')
        OUT.mkdir()
        calls = [invoke(TAG + '.compile', [call['program'], *compile_args], OUT, env)]
        calls.append(invoke(TAG + '.link', [str(link), *linked], S / 'VS', env))
        copied = []
        for entry in runtime:
            destination = OUT / Path(entry['path']).name
            need(not destination.exists(), 'Existing private runtime destination protected')
            shutil.copy2(entry['path'], destination)
            copied_entry = stat(destination)
            need((copied_entry['bytes'], copied_entry['mtime_ns']) == (entry['bytes'], entry['mtime_ns'])
                 and Path(entry['path']).read_bytes() == destination.read_bytes(), 'Frozen runtime copy differs')
            copied.append(copied_entry)
        need(all(stat(q['path']) == q for q in before), 'Sealed r1/baseline input changed')
        save(check, dict(stage=TAG + '.build', passed=True, configuration='Release', program=stat(PROGRAM),
             actual_typed_exit_code=0, actual_Win32_exit=0, intervention='terminal_rejection_printf_only',
             source_capture=capture, source_archive=archive, private_gpu_source=cu, private_wall_include=wall,
             baseline_source_build=stat(old.BASE), baseline_source_capture=baseline['source_capture'],
             baseline_source_archive=baseline['source_archive'], adopted_prepared_r1_source=True,
             adopted_failed_build=stat(FAILED), adopted_failed_compile=stat(FAILED_CALL),
             compiler_PATH_prepended=str(ccbin), host_compiler=stat(actual_cl), PATH_cl_matches_ccbin=True,
             physical_compile_cwd=str(OUT), host_pdb='physical.pdb',
             original_physical_object=stat(replacements[0]), replacement_physical_object=stat(obj),
             retained_project_objects=[stat(q) for q in retained], physical_objects_recompiled=1,
             retained_physical_objects=112, actual_link_objects=113, compile_invocations=1, link_invocations=1,
             exact_inverse_original_bytes=True, CXX_locals_added=False, primary_snapshot_added=False,
             terminal_rejection_printf_only=True, trace_macros_enabled=False, public_interfaces_changed=False,
             production_source_changed=False, physical_arithmetic_changed=False, runtime=copied, calls=calls,
             consumed=before, consumed_stats_unchanged=True, full_project_builds=0, solver_invocations=0,
             helper_program_invocations=0, smoke_invocations=0, native_decodes=0, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        calls = [stat(L / (TAG + q)) for q in ('.compile.call.json', '.link.call.json')
                 if (L / (TAG + q)).is_file()]
        if not check.exists():
            save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=calls,
                 consumed=before, full_project_builds=0, solver_invocations=0, helper_program_invocations=0,
                 smoke_invocations=0, native_decodes=0, physical_acceptance=False, SHA_scans=0))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    arguments = parser.parse_args()
    need(arguments.execution_authorized, 'Author-only until root full-read and later explicit r2 build authorization')
    build()
