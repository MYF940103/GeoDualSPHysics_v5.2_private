"""Build only the failed33 AS0.7/n2.55 saved-prefix reader from sealed N5 partial sources."""
import argparse, difflib, os, subprocess
from pathlib import Path
import c08_h18_n5_partial_native_r1_build as old
import c08_h18_wend_native_r1_build as full

T = Path(__file__).resolve().parents[1]
L = T / 'logs'
TAG = 'c08_h18_a07_n255_partial_native_r1'
OUT = T / 'outputs' / (TAG + '_build')
BASE = L / 'c08_h18_n5_partial_native_r1.build.json'
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke


def derive(entry, receiver):
    predicate = '(H18Bits(H18AS,.3f)||H18Bits(H18AS,.5f)||H18Bits(H18AS,.7f))&&(H18Bits(H18Exp,3.825f)||H18Bits(H18Exp,3.f)||H18Bits(H18Exp,5.f))'
    narrow = '(H18Bits(H18AS,.7f)&&H18Bits(H18Exp,2.55f))'
    old_cli = next(q for q in entry.splitlines() if q.startswith(' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver"'))
    new_cli = old_cli.replace('failed47_as05_n5', 'failed33_as07_n255').replace('H18Bits(H18AS,.5f)&&H18Bits(H18Exp,5.f)', 'H18Bits(H18AS,.7f)&&H18Bits(H18Exp,2.55f)')
    new_cli = new_cli.replace('samples=47,end=H18Rows[46].completed', 'samples=33,end=H18Rows[32].completed').replace('end==2092001', 'end==2064001').replace('AS.5/n5', 'AS.7/n2.55')
    begin = receiver.index('static unsigned ObservedPartialSamples(')
    observed_old = receiver[begin:receiver.index('static unsigned Number(', begin)].rstrip()
    observed = observed_old.replace('expected==2092001&&H18Rows[46]', 'expected==2064001&&H18Rows[32]').replace('observed47-of91 AS.5/n5', 'observed33-of91 AS.7/n2.55').replace('count==47', 'count==33')
    observed = observed.replace('stage=0 sorted_slot=451 native_id=818 step_start=10.461069999688553 step=2092214 ', 'stage=0 sorted_slot=443 native_id=808 step_start=10.32957999969353 step=2065916 ').replace('AS.5/n5', 'AS.7/n2.55').replace('wall818', 'wall808')
    begin = receiver.index('static std::vector<unsigned> Planned(')
    plan_old = receiver[begin:receiver.index('int wmain(', begin)].rstrip()
    plan = plan_old.replace('samples==47', 'samples==33').replace('H18Rows[46]', 'H18Rows[32]').replace('expected==2092001', 'expected==2064001').replace('explicit47 saved-prefix', 'explicit33 saved-prefix')
    entry_changes = [
        (predicate, narrow),
        ('#include "h18_n5_receiver_core_r1.cpp"', '#include "h18_a07_n255_receiver_core_r1.cpp"'),
        (old_cli, new_cli),
        ('// No source/full/formal interface in the failed47_as05_n5 adapter.', '// No source/full/formal interface in the failed33_as07_n255 adapter.'),
        ('c08_h18_n5_partial_native_r1.metadata', TAG + '.metadata'),
        (r'\"whole_run_native_passed\":false', r'\"whole_run_passed\":false,\"whole_run_native_passed\":false')]
    receiver_changes = [
        (observed_old, observed), (plan_old, plan),
        ('Actual saved-prefix last step/all47 native coverage incomplete', 'Actual saved-prefix last step/all33 native coverage incomplete'),
        ('c08_h18_n5_partial_native_r1.receiver', TAG + '.receiver'),
        (r'\"observed_saved_samples\":47', r'\"observed_saved_samples\":33'),
        (r'\"last_saved_part\":46', r'\"last_saved_part\":32'),
        (r'\"last_saved_completed_step\":2092001', r'\"last_saved_completed_step\":2064001'),
        (r'\"observed_plan_prefix_records\":47', r'\"observed_plan_prefix_records\":33'),
        (r'\"whole_run_native_passed\":false', r'\"whole_run_passed\":false,\"whole_run_native_passed\":false')]
    need(all(q in new_cli for q in ('failed33_as07_n255', 'H18Bits(H18AS,.7f)&&H18Bits(H18Exp,2.55f)', 'samples=33,end=H18Rows[32].completed', 'end==2064001'))
         and 'count==33' in observed and 'native_id=808 step_start=10.32957999969353 step=2065916 ' in observed
         and 'samples==33' in plan and 'expected==2064001' in plan, 'Exact33/AS0.7/n2.55 saved-prefix/fault derivation missing')
    new_entry, new_receiver = full.patch(entry, entry_changes), full.patch(receiver, receiver_changes)
    first, last = '  for(unsigned part=0;part<samples;part++){', '  Need(previous==expected'
    need(receiver.count(first) == new_receiver.count(first) == 1 and receiver.count(last) == new_receiver.count(last) == 1, 'One original field-validation loop required')
    loop = receiver[receiver.index(first):receiver.index(last)]
    need(new_receiver[new_receiver.index(first):new_receiver.index(last)].encode('utf-8') == loop.encode('utf-8'), 'Every original field-validation loop byte must remain identical')
    return new_entry, new_receiver, entry_changes, receiver_changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until root full-read and one explicit utility build')
    check = L / (TAG + '.build.json')
    need(not OUT.exists() and not check.exists() and all(not (L / (TAG + q)).exists()
         for q in ('.compile.call.json', '.compile.log', '.link.call.json', '.link.log')), 'Existing partial utility protected')
    before, calls = [], []
    try:
        baseline = read(BASE)
        need(baseline['passed'] and baseline['consumed_stats_unchanged']
             and baseline['explicit_profile'] == 'failed47_as05_n5' and baseline['observed_prefix_records'] == 47
             and baseline['original_plan_records'] == 91 and baseline['receiver_material_CSV_keys'] == 17
             and baseline['declared_Kernel_XML_CSV'] == 2 and baseline['actual_link_objects'] == 7
             and not baseline['JSph_objects_linked'], 'Passed sealed failed47 utility required only as derivation baseline')
        objects = [bind(q) for q in baseline['objects']]
        need(len(objects) == 6 and {Path(q['path']).stem for q in objects}
             == {'JPartDataBi4', 'JPartDataHead', 'JBinaryData', 'JObject', 'JException', 'Functions'},
             'Exactly the same six sealed BI4 utility objects required')
        generated = {Path(q['path']).name: bind(q) for q in baseline['generated']}
        leaves = ('h18_n5_partial_entry_r1.cpp', 'h18_n5_receiver_core_r1.cpp', 'h18_headers_r1.h', 'h18_profiles_r1.h')
        need(all(q in generated for q in leaves), 'Sealed generated entry/core/header closure absent')
        source, note = T / 'support' / (TAG + '.cpp'), T / 'notes' / (TAG + '.md')
        before = [bind(q) for q in baseline['consumed']]
        before += [stat(q) for q in (BASE, Path(__file__), Path(old.__file__), Path(full.__file__), source, note)]
        before += [bind(baseline[q]) for q in ('program', 'source', 'note', 'core_derivation')]
        compile_call, link_call = [read(bind(q)['path']) for q in baseline['calls']]
        before += [bind(q) for q in baseline['calls']] + list(generated.values())
        need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0 and q['ownership_failure'] is None
                 and q['child'] for q in (compile_call, link_call)), 'Passed same utility compiler/link recipe required')
        raw_entry = Path(generated[leaves[0]]['path']).read_bytes().decode('utf-8')
        raw_receiver = Path(generated[leaves[1]]['path']).read_bytes().decode('utf-8')
        entry, receiver, ec, rc = derive(raw_entry, raw_receiver)
        OUT.mkdir()
        new_files = {OUT / 'h18_a07_n255_partial_entry_r1.cpp': entry, OUT / 'h18_a07_n255_receiver_core_r1.cpp': receiver,
                     OUT / leaves[2]: Path(generated[leaves[2]]['path']).read_bytes().decode('utf-8'),
                     OUT / leaves[3]: Path(generated[leaves[3]]['path']).read_bytes().decode('utf-8')}
        for path, text in new_files.items():
            path.write_bytes(text.encode('utf-8'))
        diffs = []
        for label, original, current in (('entry', raw_entry, entry), ('receiver', raw_receiver, receiver)):
            path = OUT / (label + '_core.diff')
            path.write_text(''.join(difflib.unified_diff(original.splitlines(True), current.splitlines(True),
                            fromfile='sealed_failed47/' + label, tofile='failed33_as07_n255/' + label)), encoding='utf-8')
            diffs.append(stat(path))
        proof = OUT / 'core_derivation.json'
        save(proof, dict(stage=TAG + '.derive', baseline_build=stat(BASE), baseline_generated=list(generated.values()),
             entry_declared_replacements=ec, receiver_declared_replacements=rc, reverse_declared_replacements_exact=True,
             original_field_and_numerical_guards_changed=False, original_field_validation_loop_bytes_identical=True, whole_run_passed=False, original_plan_records=91, observed_prefix_records=33,
             last_saved_part=32, last_saved_completed_step=2064001, last_saved_zero_based_step=2064000, original_target_completed_step=2180000,
             AS_coefficient=.7, AS_exponent=2.55, actual_terminal_solver_step_proven=False,
             unsaved_state_reconstructed=False, old_files_changed=False))
        before += [stat(q) for q in new_files] + diffs + [stat(proof)]
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode == 0, 'Same utility MSVC setup failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        for key in ('CL', '_CL_'): env.pop(key, None)
        need(env['VCTOOLSVERSION'] == '14.36.32532', 'Same utility MSVC14.36 required')
        oldout = Path(baseline['program']['path']).parent
        exe = OUT / 'C08H18A07N255PartialNativeR1_win64.exe'
        ca = [str(source) if q == baseline['source']['path'] else q.replace(str(oldout), str(OUT))
              for q in compile_call['arguments']]
        la = [q.replace(baseline['program']['path'], str(exe)).replace(str(oldout), str(OUT))
              for q in link_call['arguments']]
        need(sum(q.lower().endswith('.obj') for q in la) == 7 and set(Path(q).resolve() for q in la
             if q.lower().endswith('.obj')) == {Path(q['path']).resolve() for q in objects} | {(OUT / 'reader.obj').resolve()},
             'Link only one new entry plus six utility objects; no JSph')
        need(all(stat(q['path']) == q for q in before), 'Sealed utility/source input changed')
        calls.append(invoke(TAG + '.compile', [compile_call['program'], *ca], OUT, env))
        calls.append(invoke(TAG + '.link', [link_call['program'], *la], OUT, env))
        need(all(stat(q['path']) == q for q in before), 'Sealed utility/source input changed during build')
        save(check, dict(stage=TAG + '.build', passed=True, program=stat(exe), source=stat(source), note=stat(note),
             baseline_build=stat(BASE), original_full_build=baseline['original_full_build'], objects=objects,
             actual_link_objects=7, JSph_objects_linked=False, generated=[stat(q) for q in new_files],
             core_derivation=stat(proof), core_diffs=diffs, calls=calls, consumed=before, consumed_stats_unchanged=True,
             forensic_receiver_only=True, explicit_profile='failed33_as07_n255', declared_Kernel_XML_CSV=2,
             receiver_material_CSV_keys=17, AS_coefficient=.7, AS_exponent=2.55, observed_prefix_records=33,
             original_plan_records=91, last_saved_completed_step=2064001, last_saved_zero_based_step=2064000, original_target_completed_step=2180000,
             original_field_and_numerical_guards_changed=False, original_field_validation_loop_bytes_identical=True, whole_run_passed=False, decoder_invocations=0, solver_invocations=0, SHA_scans=0))
    except Exception as error:
        actual_calls = [stat(L / (TAG + q)) for q in ('.compile.call.json', '.link.call.json') if (L / (TAG + q)).is_file()]
        if not check.exists():
            save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=actual_calls,
                 consumed=before, decoder_invocations=0, solver_invocations=0, SHA_scans=0))
        raise


if __name__ == '__main__':
    main()
