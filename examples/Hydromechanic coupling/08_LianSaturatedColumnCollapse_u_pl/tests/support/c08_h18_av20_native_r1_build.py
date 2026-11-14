"""Build only the two closed AV.2 native profiles; never decode or run a solver."""
import argparse
import difflib
import os
import subprocess
from pathlib import Path
from zipfile import ZipFile
import c08_h18_as255_native_r1_build as old

T, L = old.T, old.L
TAG = 'c08_h18_av20_native_r1'
OUT = T/'outputs'/(TAG+'_build')
BASE = L/'c08_h18_as255_native_r1.build.json'
SOURCE = T/'support'/(TAG+'.cpp')
NOTE = T/'notes'/(TAG+'.md')
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke

SOURCE_CLI = r''' if(argc==7&&std::wstring(argv[1])==L"--source"){
  const std::wstring mode=argv[2];H18Need(mode==L"partial"||mode==L"full","Source mode must be partial or full");H18ReadPlan(argv[5],true,H18Event,H18SourceSamples);return h18source::wmain(argc,argv);
 }
'''
OLD_PROFILE = r'''const bool window=profile=="window";H18Need(window||profile=="formal","Only .90-window or full3 receiver profiles");const unsigned end=window?H18WindowEnd:H18FormalEnd,samples=window?H18WindowSamples:H18FormalSamples;'''
NEW_PROFILE = r'''const bool smoke=profile=="smoke";H18Need(smoke||profile=="window","Only CPU2-frame smoke or GPU91-frame window profiles");H18Need(group=="psi0","Only original psi0 AV.2 diagnostic material is admitted");const unsigned end=smoke?2000400u:H18WindowEnd,samples=smoke?2u:H18WindowSamples;'''
OLD_READ_PLAN = r'''H18ReadPlan(argv[6],false,end,samples);'''
NEW_READ_PLAN = r'''H18ReadPlan(argv[6],false,end,samples);H18Need(H18Rows.front().completed==2000001u,"The first receiver save must be actual PRE+one update");if(smoke){H18Need(H18Rows.size()==2&&H18Rows[1].completed==2000400u,"Only completed2000001/2000400 CPU smoke saves");}else for(unsigned part=0;part<samples;part++)H18Need(H18Rows[part].completed==(part==90?2180000u:2000001u+2000u*part),"Only original91-frame GPU .90s completed-step plan");'''
OLD_MATERIAL = r'''H18ReadReceiverProfile(argv[7],group);'''
NEW_MATERIAL = r'''H18ReadReceiverProfile(argv[7],group);H18Need(H18Bits(H18AS,.3f)&&H18Bits(H18Exp,2.55f),"Only original AS.3/exponent2.55 with release AV.2 is admitted");'''
OLD_POLICY = r'''  for(const char* key:{"FreeSeepagePondingPolicy","FreeSeepagePondingActive","DynamicArtificialViscosityPolicy","DynamicArtificialViscosityOverrideActive","DynamicArtificialViscosityCoef"})H18Need(!p->ExistsValue(key),"CompletedOnly/original AV profile must not contain private policy metadata");'''
NEW_POLICY = r'''  for(const char* key:{"FreeSeepagePondingPolicy","FreeSeepagePondingActive"})H18Need(!p->ExistsValue(key),"CompletedOnly requires both experimental ponding-policy keys absent");
  H18Need(p->ExistsValue("DynamicArtificialViscosityPolicy",JBinaryDataDef::DatText)&&p->GetvText("DynamicArtificialViscosityPolicy")=="ReleaseOnly"&&p->ExistsValue("DynamicArtificialViscosityOverrideActive",JBinaryDataDef::DatBool)&&p->GetvBool("DynamicArtificialViscosityOverrideActive")&&p->ExistsValue("DynamicArtificialViscosityCoef",JBinaryDataDef::DatFloat)&&H18Bits(p->GetvFloat("DynamicArtificialViscosityCoef"),.2f),"Typed actual release-only AV override/float.2 differs");'''
OLD_BACKEND = r'''std::vector<std::wstring> args={argv[0],L"--read",argv[3],L"GPU",argv[4]'''
NEW_BACKEND = r'''std::vector<std::wstring> args={argv[0],L"--read",argv[3],(smoke?L"CPU":L"GPU"),argv[4]'''
OLD_META = r'''\"backend_proven_by_reader\":false,\"physical_acceptance\":false}'''
NEW_META = r'''\"AV_policy\":\"ReleaseOnly\",\"AV_override_active_expected\":true,\"AV_coefficient_float_reference\":"<<double(.2f)<<",\"AV_override_headers\":"<<samples<<",\"source_PRE_AV_metadata_required\":false,\"backend_argument\":\""<<(smoke?"CPU":"GPU")<<"\",\"backend_proven_by_reader\":false,\"physical_acceptance\":false}'''
REPLACEMENTS = (
    ('close source CLI', SOURCE_CLI, ' // Source decoding is not exposed by the two-profile AV20 utility.\n'),
    ('receiver help', 'Use --source partial|full DATA MATERIAL_CSV PLAN FRESHOUT; or --receiver window|formal GROUP DATA PRE PLAN PROFILE_CSV FRESHOUT',
     'Use --receiver smoke|window psi0 DATA PRE PLAN PROFILE_CSV FRESHOUT'),
    ('two closed profiles', OLD_PROFILE, NEW_PROFILE),
    ('exact smoke/window planned completed steps', OLD_READ_PLAN, NEW_READ_PLAN),
    ('closed AS03 psi0', OLD_MATERIAL, NEW_MATERIAL),
    ('replace explicit AV rejection with typed .2 requirement', OLD_POLICY, NEW_POLICY),
    ('preserve actual CPU/GPU argument labels', OLD_BACKEND, NEW_BACKEND),
    ('metadata stage', 'c08_h18_wend_native_r1.metadata', TAG+'.metadata'),
    ('AV typed-header annotation', OLD_META, NEW_META),
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
    need(inverse == raw, 'Declared entry transformations must recover every original byte')
    return revised


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until separate root utility-build admission')
    check = L/(TAG+'.build.json')
    need(not OUT.exists() and not check.exists() and all(not (L/(TAG+q)).exists() for q in
         ('.compile.call.json', '.compile.log', '.link.call.json', '.link.log')), 'Existing complete/partial utility build protected')
    before, calls = [], []
    try:
        baseline = read(BASE)
        need(baseline['stage'] == 'c08_h18_as255_native_r1.build' and baseline['passed']
             and baseline['consumed_stats_unchanged'] and baseline['actual_link_objects'] == 7
             and not baseline['JSph_objects_linked'] and baseline['declared_Kernel_XML_CSV'] == 2
             and baseline['source_material_CSV_keys'] == 15 and baseline['receiver_material_CSV_keys'] == 17,
             'Passed original full AS255 Wendland/schema2 utility required')
        objects = [bind(q) for q in baseline['objects']]
        need(len(objects) == 6 and {Path(q['path']).stem for q in objects}
             == {'JPartDataBi4', 'JPartDataHead', 'JBinaryData', 'JObject', 'JException', 'Functions'},
             'Only the six original BI4 utility objects may be reused')
        originals = {Path(q['path']).name: bind(q) for q in baseline['generated']}
        leaves = {'h18_as255_entry_r1.cpp', 'h18_headers_r1.h', 'public22_core_r1.h',
                  'h18_source_core_r1.cpp', 'h18_receiver_core_r1.cpp', 'h18_profiles_r1.h'}
        need(len(baseline['generated']) == len(originals) == 6 and set(originals) == leaves,
             'Exact original full generated typed22 closure required')
        before = [stat(q) for q in (BASE, Path(__file__), Path(old.__file__), SOURCE, NOTE)]
        before += [bind(baseline[q]) for q in ('program', 'source', 'source_archive', 'physical_source_archive', 'source_capture', 'core_derivation')]
        before += objects+list(originals.values())+[bind(q) for q in baseline['calls']]
        need(len(baseline['calls']) == 2, 'Original CL and LINK calls required')
        compile_call, link_call = [read(q['path']) for q in baseline['calls']]
        need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0
                 and q['ownership_failure'] is None and q['child'] for q in (compile_call, link_call)),
             'Original utility actual owned tool exits failed')
        raw = Path(originals['h18_as255_entry_r1.cpp']['path']).read_bytes()
        entry = derive_entry(raw)
        need(SOURCE.read_bytes().count(b'#include "h18_av20_entry_r1.cpp"') == 1,
             'One private derived entry must be the new utility implementation')
        OUT.mkdir(); headers = OUT/'headers'; headers.mkdir()
        with ZipFile(baseline['source_archive']['path']) as archive:
            for item in archive.infolist():
                if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h', '.hpp', '.inl', '.cuh'):
                    dest = headers/Path(item.filename).name
                    need(not dest.exists(), 'Duplicate archived header leaf')
                    dest.write_bytes(archive.read(item))
        with ZipFile(baseline['physical_source_archive']['path']) as archive:
            for leaf in ('JPartDataBi4.h', 'JPartDataHead.h', 'JBinaryData.h', 'TypesDef.h'):
                need((headers/leaf).read_bytes() == archive.read('src/source/'+leaf), 'Original utility/physical header differs: '+leaf)
            for leaf in ('JGravityPreloadState.h', 'FunSoilMaterial.h'):
                (headers/leaf).write_bytes(archive.read('src/source/'+leaf))
        generated = []
        for name, original in originals.items():
            dest = OUT/('h18_av20_entry_r1.cpp' if name == 'h18_as255_entry_r1.cpp' else name)
            payload = entry if name == 'h18_as255_entry_r1.cpp' else Path(original['path']).read_bytes()
            dest.write_bytes(payload)
            need(dest.read_bytes() == payload, 'Private generated source copy differs')
            generated.append(stat(dest))
        diff = OUT/'entry_profile.diff'
        diff.write_text(''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True), entry.decode('utf-8').splitlines(True),
                                                  fromfile='sealed_AS255/entry', tofile='AV20/entry')), encoding='utf-8')
        proof = OUT/'core_derivation.json'
        save(proof, dict(stage=TAG+'.derive', baseline_build=stat(BASE), baseline_generated=list(originals.values()),
            replacements=[dict(label=label, before=a, after=b, count=1) for label, a, b in REPLACEMENTS],
            exact_inverse_original_entry_bytes=True, all_other_entry_bytes_unchanged=True,
            source_and_receiver_numeric_cores_byte_identical=True, original_numeric_guards_changed=False,
            source_CLI_exposed=False, formal_CLI_exposed=False, allowed_group='psi0',
            AS_coefficient=.3, AS_exponent=2.55, AV_policy='ReleaseOnly', AV_override_active=True,
            AV_coefficient_float_literal='.2f', source_PRE_AV_metadata_required=False,
            cpu_profile=dict(name='smoke', backend_argument='CPU', samples=2, completed_steps=[2000001, 2000400], end=2000400),
            gpu_profile=dict(name='window', backend_argument='GPU', samples=91, end=2180000,
                             first_completed_step=2000001, original_w09_plan_required=True),
            receiver_material_CSV_keys=17, typed_arrays=22, active_IDs=6805,
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
        obj, exe = OUT/'reader.obj', OUT/'C08H18Av20NativeR1_win64.exe'
        ca = [str(SOURCE) if q == baseline['source']['path'] else q.replace(str(oldout), str(OUT)) for q in compile_call['arguments']]
        la = [q.replace(baseline['program']['path'], str(exe)).replace(str(oldout), str(OUT)) for q in link_call['arguments']]
        linked = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        need(all(q in ca for q in ('/std:c++17', '/D_HAS_STD_BYTE=0', '/fp:precise', '/O2', '/MT', '/GL-'))
             and ca.count(str(SOURCE)) == 1 and '/Fo'+str(obj) in ca and '/I'+str(headers) in ca,
             'Original utility ABI/FP recipe with one new entry required')
        need(len(linked) == len(set(linked)) == 7
             and set(linked) == {Path(q['path']).resolve() for q in objects}|{obj.resolve()},
             'One new entry plus six original utility objects only, no JSph')
        tools = [Path(q['program']) for q in (compile_call, link_call)]
        need(all('/14.36.32532/' in q.as_posix() for q in tools), 'Actual original MSVC tools required')
        before += [stat(q) for q in tools]
        need(all(stat(q['path']) == q for q in before), 'Consumed utility/source input changed before build')
        calls.append(invoke(TAG+'.compile', [compile_call['program'], *ca], OUT, env))
        calls.append(invoke(TAG+'.link', [link_call['program'], *la], OUT, env))
        need(all(stat(q['path']) == q for q in before), 'Consumed utility/source input changed during build')
        save(check, dict(stage=TAG+'.build', passed=True, program=stat(exe), source=stat(SOURCE), note=stat(NOTE),
            baseline_build=stat(BASE), source_archive=baseline['source_archive'],
            physical_source_archive=baseline['physical_source_archive'], source_capture=baseline['source_capture'],
            objects=objects, generated=generated, core_derivation=stat(proof), core_diff=stat(diff), calls=calls,
            consumed=before, consumed_stats_unchanged=True, actual_link_objects=7, JSph_objects_linked=False,
            source_and_receiver_numeric_cores_byte_identical=True, original_numeric_guards_changed=False,
            profiles=['smoke', 'window'], smoke_backend_argument='CPU', window_backend_argument='GPU',
            smoke_samples=2, smoke_end=2000400, window_samples=91, window_end=2180000,
            allowed_group='psi0', actual_AS_coefficient=.3, actual_AS_exponent=2.55,
            actual_AV_policy='ReleaseOnly', actual_AV_override_active=True, actual_AV_float_reference='.2f',
            source_PRE_AV_metadata_required=False, declared_Kernel_XML_CSV=2,
            source_material_CSV_keys=15, receiver_material_CSV_keys=17,
            actual_typed_exit_code=0, actual_Win32_exit=0, native_decodes=0, solver_invocations=0,
            physical_acceptance=False, SHA_scans=0))
    except Exception as error:
        actual_calls = [stat(L/(TAG+q)) for q in ('.compile.call.json', '.link.call.json') if (L/(TAG+q)).is_file()]
        if not check.exists():
            save(check, dict(stage=TAG+'.build', passed=False, first_failure=str(error), calls=actual_calls,
                             consumed=before, native_decodes=0, solver_invocations=0, physical_acceptance=False))
        raise


if __name__ == '__main__':
    main()
