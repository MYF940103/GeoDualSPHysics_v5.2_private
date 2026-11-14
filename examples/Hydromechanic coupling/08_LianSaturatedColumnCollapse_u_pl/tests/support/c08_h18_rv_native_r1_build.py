"""Build closed H1.8 RV-body native profiles only; never run a solver or decode."""
import argparse
import difflib
import os
import subprocess
from pathlib import Path
from zipfile import ZipFile
import c08_h18_storage_native_r1_build as old

T, L = old.T, old.L
TAG = 'c08_h18_rv_native_r1'
OUT = T/'outputs'/(TAG+'_build')
BASE = L/'c08_h18_storage_native_r1.build.json'
SOURCE = T/'support'/(TAG+'.cpp')
NOTE = T/'notes'/(TAG+'.md')
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke

OLD_PROFILE = r'''const bool debug2=profile=="debug2",short3=profile=="short3",window=profile=="window";H18Need(debug2||short3||window,"Only Debug2, Release-short3 or window91 receiver profiles");H18Need(group=="psi0","Only original psi0 storage observer material is admitted");const unsigned end=debug2?2000002u:(short3?2004001u:H18WindowEnd),samples=debug2?2u:(short3?3u:H18WindowSamples);'''
NEW_PROFILE = r'''const bool off1=profile=="off1",debug2=profile=="debug2",window=profile=="window";H18Need(off1||debug2||window,"Only OFF-one-frame, Debug-two-update or window91 receiver profiles");H18Need(group=="psi0","Only original psi0 RV-body material is admitted");const unsigned end=off1?2000001u:(debug2?2000002u:H18WindowEnd),samples=off1?1u:(debug2?2u:H18WindowSamples);'''
OLD_PLAN = r'''H18ReadPlan(argv[6],false,end,samples);H18Need(H18Rows.front().completed==2000001u,"The first receiver save must be actual PRE+one update");if(debug2){H18Need(H18Rows.size()==2&&H18Rows[1].completed==2000002u,"Only two true Debug updates2000001/2000002");}else if(short3){for(unsigned part=0;part<samples;part++)H18Need(H18Rows[part].completed==2000001u+2000u*part,"Only original first3 Release saved steps2000001/2002001/2004001");}else for(unsigned part=0;part<samples;part++)H18Need(H18Rows[part].completed==(part==90?2180000u:2000001u+2000u*part),"Only original91-frame GPU .90s completed-step plan");'''
NEW_PLAN = r'''H18ReadPlan(argv[6],false,end,samples);H18Need(H18Rows.front().completed==2000001u,"The first receiver save must be actual PRE+one update");if(off1){H18Need(H18Rows.size()==1&&H18Rows[0].completed==2000001u,"Only one true OFF update2000001");}else if(debug2){H18Need(H18Rows.size()==2&&H18Rows[1].completed==2000002u,"Only two true Debug updates2000001/2000002");}else for(unsigned part=0;part<samples;part++)H18Need(H18Rows[part].completed==(part==90?2180000u:2000001u+2000u*part),"Only original91-frame GPU .90s completed-step plan");'''
REPLACEMENTS = (
    ('closed source comment', ' // Source decoding is not exposed by the three-profile storage utility.\n',
     ' // Source decoding is not exposed by this closed RV-body utility.\n'),
    ('closed receiver help', 'Use --receiver debug2|short3|window psi0 DATA PRE PLAN PROFILE_CSV FRESHOUT',
     'Use --receiver off1|debug2|window psi0 DATA PRE PLAN PROFILE_CSV FRESHOUT'),
    ('three closed profiles', OLD_PROFILE, NEW_PROFILE),
    ('actual off1/debug2/window saved steps', OLD_PLAN, NEW_PLAN),
    ('metadata stage', 'c08_h18_storage_native_r1.metadata', TAG+'.metadata'),
    ('RV not proven by arrays', r'\"observer_pressure_budget_proven_by_reader\":false',
     r'\"residual_viscosity_proven_by_reader\":false,\"RV_program_owner_sidecar_review_required\":true'),
)


def derive_entry(raw):
    revised = raw
    for label, before, after in REPLACEMENTS:
        a, b = before.encode('utf-8'), after.encode('utf-8')
        need(revised.count(a) == 1, 'Unique sealed entry anchor required: '+label)
        revised = revised.replace(a, b, 1)
    inverse = revised
    for label, before, after in reversed(REPLACEMENTS):
        a, b = before.encode('utf-8'), after.encode('utf-8')
        need(inverse.count(b) == 1, 'Unique inverse entry anchor required: '+label)
        inverse = inverse.replace(b, a, 1)
    need(inverse == raw, 'Declared entry changes must recover every original byte')
    return revised


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until separate root full-read/build admission')
    check = L/(TAG+'.build.json')
    need(not OUT.exists() and not check.exists() and all(not (L/(TAG+q)).exists() for q in
         ('.compile.call.json', '.compile.log', '.link.call.json', '.link.log')), 'Existing full/partial utility build protected')
    before, calls = [], []
    try:
        baseline = read(BASE)
        need(baseline['stage'] == 'c08_h18_storage_native_r1.build' and baseline['passed']
             and baseline['consumed_stats_unchanged'] and baseline['actual_link_objects'] == 7
             and not baseline['JSph_objects_linked'] and baseline['declared_Kernel_XML_CSV'] == 2
             and baseline['source_material_CSV_keys'] == 15 and baseline['receiver_material_CSV_keys'] == 17
             and baseline['source_and_receiver_numeric_cores_byte_identical']
             and not baseline['original_numeric_guards_changed']
             and baseline['profiles'] == ['debug2', 'short3', 'window']
             and baseline['allowed_group'] == 'psi0' and baseline['actual_AS_coefficient'] == .3
             and baseline['actual_AS_exponent'] == 2.55,
             'Passed exact original-physics storage typed22 baseline required')
        objects = [bind(q) for q in baseline['objects']]
        need(len(objects) == 6 and {Path(q['path']).stem for q in objects}
             == {'JPartDataBi4', 'JPartDataHead', 'JBinaryData', 'JObject', 'JException', 'Functions'},
             'Exactly six original BI4 utility objects, no physical objects')
        originals = {Path(q['path']).name: bind(q) for q in baseline['generated']}
        leaves = {'h18_storage_entry_r1.cpp', 'h18_headers_r1.h', 'public22_core_r1.h',
                  'h18_source_core_r1.cpp', 'h18_receiver_core_r1.cpp', 'h18_profiles_r1.h'}
        need(len(baseline['generated']) == len(originals) == 6 and set(originals) == leaves,
             'Exact six-file original generated source closure required')
        before = [stat(q) for q in (BASE, Path(__file__), Path(old.__file__), SOURCE, NOTE)]
        before += [bind(baseline[q]) for q in ('program', 'source', 'source_archive', 'physical_source_archive', 'source_capture', 'core_derivation')]
        before += objects+list(originals.values())+[bind(q) for q in baseline['calls']]
        need(len(baseline['calls']) == 2, 'Exactly original CL and LINK calls required')
        compile_call, link_call = [read(q['path']) for q in baseline['calls']]
        need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0
                 and q['ownership_failure'] is None and q['child'] for q in (compile_call, link_call)),
             'Passed actual owned original utility tools required')
        raw = Path(originals['h18_storage_entry_r1.cpp']['path']).read_bytes()
        entry = derive_entry(raw)
        need(SOURCE.read_bytes().count(b'#include "h18_rv_entry_r1.cpp"') == 1,
             'One private derived entry must supply this utility')
        OUT.mkdir(); headers = OUT/'headers'; headers.mkdir()
        with ZipFile(baseline['source_archive']['path']) as archive:
            for item in archive.infolist():
                if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h', '.hpp', '.inl', '.cuh'):
                    dest = headers/Path(item.filename).name
                    need(not dest.exists(), 'Duplicate archived header leaf')
                    dest.write_bytes(archive.read(item))
        with ZipFile(baseline['physical_source_archive']['path']) as archive:
            for leaf in ('JPartDataBi4.h', 'JPartDataHead.h', 'JBinaryData.h', 'TypesDef.h'):
                need((headers/leaf).read_bytes() == archive.read('src/source/'+leaf), 'Original utility/physical ABI differs: '+leaf)
            for leaf in ('JGravityPreloadState.h', 'FunSoilMaterial.h'):
                (headers/leaf).write_bytes(archive.read('src/source/'+leaf))
        generated = []
        for name, original in originals.items():
            dest = OUT/('h18_rv_entry_r1.cpp' if name == 'h18_storage_entry_r1.cpp' else name)
            payload = entry if name == 'h18_storage_entry_r1.cpp' else Path(original['path']).read_bytes()
            dest.write_bytes(payload)
            need(dest.read_bytes() == payload, 'Private generated source copy differs')
            generated.append(stat(dest))
        diff = OUT/'entry_profile.diff'
        diff.write_text(''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True), entry.decode('utf-8').splitlines(True),
                                                  fromfile='sealed_storage/entry', tofile='RV_body/entry')), encoding='utf-8')
        proof = OUT/'core_derivation.json'
        save(proof, dict(stage=TAG+'.derive', baseline_build=stat(BASE), baseline_generated=list(originals.values()),
            replacements=[dict(label=label, before=a, after=b, count=1) for label, a, b in REPLACEMENTS],
            exact_inverse_original_entry_bytes=True, all_other_entry_bytes_unchanged=True,
            source_and_receiver_numeric_cores_byte_identical=True, original_numeric_guards_changed=False,
            source_CLI_exposed=False, formal_CLI_exposed=False, allowed_group='psi0',
            AS_coefficient=.3, AS_exponent=2.55, original_AV_private_keys_rejected=True, backend_argument='GPU',
            profiles=[dict(name='off1', samples=1, completed_steps=[2000001], end=2000001),
                      dict(name='debug2', samples=2, completed_steps=[2000001, 2000002], end=2000002),
                      dict(name='window', samples=91, end=2180000, first_completed_step=2000001, original_w09_plan_required=True)],
            residual_viscosity_proven_by_reader=False, RV_program_owner_sidecar_review_required=True,
            debug_is_Release_bit_truth=False, receiver_material_CSV_keys=17, typed_arrays=22, active_IDs=6805,
            no_native_decode_or_solver_authorized_by_build=True, old_files_changed=False))
        before += generated+[stat(diff), stat(proof)]+[stat(p) for p in headers.iterdir()]
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode == 0, 'Original utility MSVC setup failed')
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (q.split('=', 1) for q in setup.stdout.decode('mbcs').splitlines()
                                            if '=' in q and not q.startswith('=')))
        need(env['VCTOOLSVERSION'] == '14.36.32532', 'Original six-object MSVC14.36 required')
        for key in ('CL', '_CL_'): env.pop(key, None)
        oldout = Path(baseline['program']['path']).parent
        obj, exe = OUT/'reader.obj', OUT/'C08H18RvNativeR1_win64.exe'
        ca = [str(SOURCE) if q == baseline['source']['path'] else q.replace(str(oldout), str(OUT)) for q in compile_call['arguments']]
        la = [q.replace(baseline['program']['path'], str(exe)).replace(str(oldout), str(OUT)) for q in link_call['arguments']]
        linked = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        need(all(q in ca for q in ('/std:c++17', '/D_HAS_STD_BYTE=0', '/fp:precise', '/O2', '/MT', '/GL-'))
             and ca.count(str(SOURCE)) == 1 and '/Fo'+str(obj) in ca and '/I'+str(headers) in ca,
             'Original utility ABI/FP recipe with one new entry required')
        need(len(linked) == len(set(linked)) == 7
             and set(linked) == {Path(q['path']).resolve() for q in objects}|{obj.resolve()},
             'Exactly one new entry plus six original BI4 utility objects, no JSph')
        tools = [Path(q['program']) for q in (compile_call, link_call)]
        need(all('/14.36.32532/' in q.as_posix() for q in tools), 'Actual original MSVC tools required')
        before += [stat(q) for q in tools]
        need(all(stat(q['path']) == q for q in before), 'Consumed original utility/source changed before build')
        calls.append(invoke(TAG+'.compile', [compile_call['program'], *ca], OUT, env))
        calls.append(invoke(TAG+'.link', [link_call['program'], *la], OUT, env))
        need(all(stat(q['path']) == q for q in before), 'Consumed original utility/source changed during build')
        save(check, dict(stage=TAG+'.build', passed=True, program=stat(exe), source=stat(SOURCE), note=stat(NOTE),
            baseline_build=stat(BASE), source_archive=baseline['source_archive'], physical_source_archive=baseline['physical_source_archive'],
            source_capture=baseline['source_capture'], objects=objects, generated=generated, core_derivation=stat(proof), core_diff=stat(diff),
            calls=calls, consumed=before, consumed_stats_unchanged=True, actual_link_objects=7, JSph_objects_linked=False,
            source_and_receiver_numeric_cores_byte_identical=True, original_numeric_guards_changed=False,
            profiles=['off1', 'debug2', 'window'], backend_argument='GPU', off_samples=1, off_end=2000001,
            debug_samples=2, debug_end=2000002, window_samples=91, window_end=2180000,
            allowed_group='psi0', actual_AS_coefficient=.3, actual_AS_exponent=2.55, original_AV_private_keys_rejected=True,
            residual_viscosity_proven_by_reader=False, RV_program_owner_sidecar_review_required=True,
            debug_is_Release_bit_truth=False, declared_Kernel_XML_CSV=2,
            source_material_CSV_keys=15, receiver_material_CSV_keys=17,
            actual_typed_exit_code=0, actual_Win32_exit=0, native_decodes=0, solver_invocations=0, physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        actual_calls = [stat(L/(TAG+q)) for q in ('.compile.call.json', '.link.call.json') if (L/(TAG+q)).is_file()]
        if not check.exists():
            save(check, dict(stage=TAG+'.build', passed=False, first_failure=str(error), calls=actual_calls,
                             consumed=before, native_decodes=0, solver_invocations=0, physical_acceptance=False))
        raise


if __name__ == '__main__':
    main()
