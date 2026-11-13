"""Build only a narrow failed47_as05_n5 reader from sealed failed35 sources; never decode or solve."""
import argparse, difflib, os, subprocess
from pathlib import Path
import c08_h18_centroid_partial_native_r1_build as old

T = Path(__file__).resolve().parents[1]
L = T / 'logs'
TAG = 'c08_h18_n5_partial_native_r1'
OUT = T / 'outputs' / (TAG + '_build')
BASE = L / 'c08_h18_centroid_partial_native_r1.build.json'
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke


def derive(entry, receiver):
    old_cli = next(q for q in entry.splitlines() if q.startswith(' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver"'))
    new_cli = old_cli.replace('failed35_centroid_as07', 'failed47_as05_n5')
    new_cli = new_cli.replace('H18Bits(H18AS,.7f)&&H18Bits(H18Exp,3.825f)', 'H18Bits(H18AS,.5f)&&H18Bits(H18Exp,5.f)')
    new_cli = new_cli.replace('samples=35,end=H18Rows[34].completed', 'samples=47,end=H18Rows[46].completed')
    new_cli = new_cli.replace('end==2068001', 'end==2092001').replace('AS.7/n3.825', 'AS.5/n5').replace('failed AS.7', 'failed AS.5/n5')
    begin = receiver.index('static unsigned ObservedPartialSamples(')
    observed_old = receiver[begin:receiver.index('static unsigned Number(', begin)].rstrip()
    observed = observed_old.replace('expected==2068001&&H18Rows[34]', 'expected==2092001&&H18Rows[46]')
    observed = observed.replace('observed35-of91 centroid AS.7', 'observed47-of91 AS.5/n5').replace('count==35', 'count==47')
    observed = observed.replace(
        'stage=0 sorted_slot=443 native_id=808 step_start=10.347964999692834 step=2069593 ',
        'stage=0 sorted_slot=451 native_id=818 step_start=10.461069999688553 step=2092214 ')
    observed = observed.replace('failed AS.7 receiver', 'failed AS.5/n5 receiver').replace('AS.7 wall803', 'AS.5/n5 wall818')
    begin = receiver.index('static std::vector<unsigned> Planned(')
    plan_old = receiver[begin:receiver.index('int wmain(', begin)].rstrip()
    plan = plan_old.replace('samples==35', 'samples==47').replace('H18Rows[34]', 'H18Rows[46]')
    plan = plan.replace('expected==2068001', 'expected==2092001').replace('explicit35 saved-prefix', 'explicit47 saved-prefix')
    entry_changes = [
        ('#include "h18_centroid_receiver_core_r1.cpp"', '#include "h18_n5_receiver_core_r1.cpp"'),
        (old_cli, new_cli),
        ('// No source/full/formal interface in the failed35_centroid_as07 adapter.',
         '// No source/full/formal interface in the failed47_as05_n5 adapter.'),
        ('c08_h18_centroid_partial_native_r1.metadata', TAG + '.metadata')]
    receiver_changes = [
        (observed_old, observed), (plan_old, plan),
        ('Actual saved-prefix last step/all35 native coverage incomplete', 'Actual saved-prefix last step/all47 native coverage incomplete'),
        ('c08_h18_centroid_partial_native_r1.receiver', TAG + '.receiver'),
        (r'\"observed_saved_samples\":35', r'\"observed_saved_samples\":47'),
        (r'\"last_saved_part\":34', r'\"last_saved_part\":46'),
        (r'\"last_saved_completed_step\":2068001', r'\"last_saved_completed_step\":2092001'),
        (r'\"observed_plan_prefix_records\":35', r'\"observed_plan_prefix_records\":47')]
    need(all(q in new_cli for q in ('failed47_as05_n5', 'H18Bits(H18AS,.5f)&&H18Bits(H18Exp,5.f)',
                                   'samples=47,end=H18Rows[46].completed', 'end==2092001'))
         and 'count==47' in observed and 'native_id=818 step_start=10.461069999688553 step=2092214 ' in observed
         and 'samples==47' in plan and 'expected==2092001' in plan, 'Explicit N5 prefix/AS/fault derivation missing')
    patch = old.old.prior.patch
    return patch(entry, entry_changes), patch(receiver, receiver_changes), entry_changes, receiver_changes


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
             and baseline['explicit_profile'] == 'failed35_centroid_as07' and baseline['observed_prefix_records'] == 35
             and baseline['original_plan_records'] == 91 and baseline['receiver_material_CSV_keys'] == 17
             and baseline['declared_Kernel_XML_CSV'] == 2 and baseline['actual_link_objects'] == 7
             and not baseline['JSph_objects_linked'], 'Passed sealed failed35 utility required only as derivation baseline')
        objects = [bind(q) for q in baseline['objects']]
        need(len(objects) == 6 and {Path(q['path']).stem for q in objects}
             == {'JPartDataBi4', 'JPartDataHead', 'JBinaryData', 'JObject', 'JException', 'Functions'},
             'Exactly the same six sealed BI4 utility objects required')
        generated = {Path(q['path']).name: bind(q) for q in baseline['generated']}
        leaves = ('h18_centroid_partial_entry_r1.cpp', 'h18_centroid_receiver_core_r1.cpp', 'h18_headers_r1.h', 'h18_profiles_r1.h')
        need(all(q in generated for q in leaves), 'Sealed generated entry/core/header closure absent')
        source, note = T / 'support' / (TAG + '.cpp'), T / 'notes' / (TAG + '.md')
        before = [bind(q) for q in baseline['consumed']]
        before += [stat(q) for q in (BASE, Path(__file__), Path(old.__file__), source, note)]
        before += [bind(baseline[q]) for q in ('program', 'source', 'note', 'core_derivation')]
        compile_call, link_call = [read(bind(q)['path']) for q in baseline['calls']]
        before += [bind(q) for q in baseline['calls']] + list(generated.values())
        need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0 and q['ownership_failure'] is None
                 and q['child'] for q in (compile_call, link_call)), 'Passed same utility compiler/link recipe required')
        raw_entry = Path(generated[leaves[0]]['path']).read_text(encoding='utf-8')
        raw_receiver = Path(generated[leaves[1]]['path']).read_text(encoding='utf-8')
        entry, receiver, ec, rc = derive(raw_entry, raw_receiver)
        OUT.mkdir()
        new_files = {OUT / 'h18_n5_partial_entry_r1.cpp': entry, OUT / 'h18_n5_receiver_core_r1.cpp': receiver,
                     OUT / leaves[2]: Path(generated[leaves[2]]['path']).read_text(encoding='utf-8'),
                     OUT / leaves[3]: Path(generated[leaves[3]]['path']).read_text(encoding='utf-8')}
        for path, text in new_files.items():
            path.write_text(text, encoding='utf-8', newline='\n')
        diffs = []
        for label, original, current in (('entry', raw_entry, entry), ('receiver', raw_receiver, receiver)):
            path = OUT / (label + '_core.diff')
            path.write_text(''.join(difflib.unified_diff(original.splitlines(True), current.splitlines(True),
                            fromfile='sealed_failed35/' + label, tofile='failed47_as05_n5/' + label)), encoding='utf-8')
            diffs.append(stat(path))
        proof = OUT / 'core_derivation.json'
        save(proof, dict(stage=TAG + '.derive', baseline_build=stat(BASE), baseline_generated=list(generated.values()),
             entry_declared_replacements=ec, receiver_declared_replacements=rc, reverse_declared_replacements_exact=True,
             original_field_and_numerical_guards_changed=False, original_plan_records=91, observed_prefix_records=47,
             last_saved_part=46, last_saved_completed_step=2092001, original_target_completed_step=2180000,
             AS_coefficient=.5, AS_exponent=5., actual_terminal_solver_step_proven=False,
             unsaved_state_reconstructed=False, old_files_changed=False))
        before += [stat(q) for q in new_files] + diffs + [stat(proof)]
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode == 0, 'Same utility MSVC setup failed')
        env = dict(os.environ)
        env.update(q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('='))
        need(env['VCTOOLSVERSION'] == '14.36.32532', 'Same utility MSVC14.36 required')
        oldout = Path(baseline['program']['path']).parent
        exe = OUT / 'C08H18N5PartialNativeR1_win64.exe'
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
             forensic_receiver_only=True, explicit_profile='failed47_as05_n5', declared_Kernel_XML_CSV=2,
             receiver_material_CSV_keys=17, AS_coefficient=.5, AS_exponent=5., observed_prefix_records=47,
             original_plan_records=91, last_saved_completed_step=2092001, original_target_completed_step=2180000,
             original_field_and_numerical_guards_changed=False, decoder_invocations=0, solver_invocations=0, SHA_scans=0))
    except Exception as error:
        if not check.exists():
            save(check, dict(stage=TAG + '.build', passed=False, first_failure=str(error), calls=calls,
                 consumed=before, decoder_invocations=0, solver_invocations=0, SHA_scans=0))
        raise


if __name__ == '__main__':
    main()
