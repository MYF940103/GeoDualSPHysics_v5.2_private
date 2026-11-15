"""Build only one closed short4 reader entry over the original AS255 native cores."""
import argparse
import difflib
import os
import subprocess
from pathlib import Path
from zipfile import ZipFile
import c08_h18_as255_native_r1_build as old

T, L = old.T, old.L
TAG = 'c08_h18_hg_opt4_native_r1'
SCRIPT = Path(__file__).resolve()
SOURCE = T / 'support' / (TAG + '_entry.cpp')
NOTE = T / 'notes' / (TAG + '.md')
BASE = L / 'c08_h18_as255_native_r1.build.json'
OUT = T / 'outputs' / (TAG + '_build')
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke
REPLACEMENTS = (
    ('source CLI closed',
     ' if(argc==7&&std::wstring(argv[1])==L"--source"){\n  const std::wstring mode=argv[2];H18Need(mode==L"partial"||mode==L"full","Source mode must be partial or full");H18ReadPlan(argv[5],true,H18Event,H18SourceSamples);return h18source::wmain(argc,argv);\n }',
     ' // Only the short4 receiver CLI is exposed; no source/formal/window command.'),
    ('receiver help',
     'Use --source partial|full DATA MATERIAL_CSV PLAN FRESHOUT; or --receiver window|formal GROUP DATA PRE PLAN PROFILE_CSV FRESHOUT',
     'Use --receiver short4 psi0 DATA PRE PLAN PROFILE_CSV FRESHOUT'),
    ('closed short4 extent and group',
     'const bool window=profile=="window";H18Need(window||profile=="formal","Only .90-window or full3 receiver profiles");const unsigned end=window?H18WindowEnd:H18FormalEnd,samples=window?H18WindowSamples:H18FormalSamples;',
     'H18Need(profile=="short4"&&group=="psi0","Only same-dt short4/psi0 is exposed");const unsigned end=2006001u,samples=4u;'),
    ('exact four actual saves and AS03 input',
     'H18ReadPlan(argv[6],false,end,samples);H18ReadReceiverProfile(argv[7],group);',
     'H18ReadPlan(argv[6],false,end,samples);for(unsigned part=0;part<4u;part++)H18Need(H18Rows[part].completed==2000001u+2000u*part,"Only the four actual saves2000001/2002001/2004001/2006001");H18ReadReceiverProfile(argv[7],group);H18Need(H18Bits(H18AS,.3f)&&H18Bits(H18Exp,2.55f),"Only original AS.3/exponent2.55 is admitted");'),
    ('metadata stage only', 'c08_h18_wend_native_r1.metadata', 'c08_h18_hg_opt4_native_r1.metadata'),
)


def derive(raw):
    result = raw
    for label, before, after in REPLACEMENTS:
        a, b = before.encode('utf-8'), after.encode('utf-8')
        need(result.count(a) == 1, 'Unique original entry anchor required: ' + label)
        result = result.replace(a, b, 1)
    inverse = result
    for label, before, after in reversed(REPLACEMENTS):
        a, b = before.encode('utf-8'), after.encode('utf-8')
        need(inverse.count(b) == 1, 'Unique inverse entry anchor required: ' + label)
        inverse = inverse.replace(b, a, 1)
    need(inverse == raw, 'Inverse declared entry edits must restore every original byte')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true'); args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until root reviews/adopts one private utility build')
    check = L / (TAG + '.build.json')
    need(not OUT.exists() and not check.exists() and all(not (L / (TAG + suffix)).exists()
        for suffix in ('.compile.call.json', '.compile.log', '.link.call.json', '.link.log')),
        'Existing complete/partial utility is protected; no retry or overwrite')
    before, calls = [], []
    try:
        b = read(BASE)
        need(b['stage'] == 'c08_h18_as255_native_r1.build' and b['passed'] and b['consumed_stats_unchanged']
             and b['actual_link_objects'] == 7 and not b['JSph_objects_linked']
             and b['declared_Kernel_XML_CSV'] == 2 and b['source_material_CSV_keys'] == 15
             and b['receiver_material_CSV_keys'] == 17 and b['exact_inverse_original_entry_bytes']
             and not b['original_field_and_numerical_guards_changed'] and b['formal_samples'] == 301
             and b['window_samples'] == 91 and b['explicit_AS_exponent'] == 2.55,
             'Passed original full AS255 native reader closure required')
        objects = [bind(q) for q in b['objects']]
        need(len(objects) == 6 and {Path(q['path']).stem for q in objects}
             == {'Functions','JBinaryData','JException','JObject','JPartDataBi4','JPartDataHead'},
             'Exactly six original BI4 utility objects required, no solver objects')
        originals = {Path(q['path']).name: bind(q) for q in b['generated']}
        leaves = {'h18_as255_entry_r1.cpp','h18_headers_r1.h','public22_core_r1.h',
                  'h18_source_core_r1.cpp','h18_receiver_core_r1.cpp','h18_profiles_r1.h'}
        need(len(b['generated']) == len(originals) == 6 and set(originals) == leaves,
             'Actual six-file generated source closure required')
        before = [stat(q) for q in (BASE,SCRIPT,SOURCE,NOTE,Path(old.__file__),Path(old.old.__file__),Path(old.old.e.__file__))]
        before += [bind(b[k]) for k in ('program','source','source_archive','physical_source_archive','source_capture','core_derivation')]
        before += objects + list(originals.values()) + [bind(q) for q in b['calls']]
        need(len(b['calls']) == 2, 'One original compile and one original link receipt required')
        cc, lc = [read(q['path']) for q in b['calls']]
        need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0
                 and q['ownership_failure'] is None and q['child'] for q in (cc,lc)), 'Passed actual original utility calls required')
        need(SOURCE.read_bytes().count(b'#include "h18_hg_opt4_entry_r1.cpp"') == 1,
             'Exactly one private mechanically derived entry include required')
        raw = Path(originals['h18_as255_entry_r1.cpp']['path']).read_bytes(); revised = derive(raw)
        OUT.mkdir(); headers = OUT / 'headers'; headers.mkdir()
        with ZipFile(b['source_archive']['path']) as archive:
            for item in archive.infolist():
                if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
                    dest = headers / Path(item.filename).name
                    need(not dest.exists(), 'Duplicate archived header leaf'); dest.write_bytes(archive.read(item))
        with ZipFile(b['physical_source_archive']['path']) as archive:
            for leaf in ('JPartDataBi4.h','JPartDataHead.h','JBinaryData.h','TypesDef.h'):
                need((headers / leaf).read_bytes() == archive.read('src/source/' + leaf), 'Original utility/physical ABI differs: ' + leaf)
            for leaf in ('JGravityPreloadState.h','FunSoilMaterial.h'):
                (headers / leaf).write_bytes(archive.read('src/source/' + leaf))
        generated = []
        for leaf, original in originals.items():
            payload = revised if leaf == 'h18_as255_entry_r1.cpp' else Path(original['path']).read_bytes()
            dest = OUT / ('h18_hg_opt4_entry_r1.cpp' if leaf == 'h18_as255_entry_r1.cpp' else leaf)
            dest.write_bytes(payload); need(dest.read_bytes() == payload, 'Actual generated private copy differs')
            generated.append(stat(dest))
        diff, proof = OUT/'entry_profile.diff', OUT/'core_derivation.json'
        diff.write_text(''.join(difflib.unified_diff(raw.decode().splitlines(True),revised.decode().splitlines(True),
            fromfile='sealed_AS255/entry',tofile='private_short4/entry')),encoding='utf-8')
        save(proof,dict(stage=TAG+'.derive',baseline_build=stat(BASE),baseline_generated=list(originals.values()),
            replacements=[dict(label=l,before=a,after=z,count=1) for l,a,z in REPLACEMENTS],
            exact_inverse_original_entry_bytes=True,all_other_entry_bytes_unchanged=True,
            source_and_receiver_numeric_cores_byte_identical=True,original_field_and_numerical_guards_changed=False,
            profiles=['short4'],allowed_group='psi0',completed_steps=[2000001,2002001,2004001,2006001],
            samples=4,end=2006001,new_updates=6001,fixed_dt_s=.000005,scalar_plus_equal_dt=True,
            source_CLI_exposed=False,formal_CLI_exposed=False,window_CLI_exposed=False,
            same_dt_prefix_regression_is_half=False,HG_proven_by_reader=False,old_files_changed=False))
        before += generated + [stat(diff),stat(proof)] + [stat(q) for q in headers.iterdir()]
        setup = subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode == 0, 'Original MSVC setup failed')
        env = {k.upper():v for k,v in os.environ.items()}
        env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        need(env['VCTOOLSVERSION'] == '14.36.32532', 'Same original six-object MSVC14.36 required')
        for k in ('CL','_CL_'): env.pop(k,None)
        oldout = Path(b['program']['path']).parent; obj = OUT/'reader.obj'; exe = OUT/'C08H18HgOpt4NativeR1_win64.exe'
        ca = [str(SOURCE) if q == b['source']['path'] else q.replace(str(oldout),str(OUT)) for q in cc['arguments']]
        la = [q.replace(b['program']['path'],str(exe)).replace(str(oldout),str(OUT)) for q in lc['arguments']]
        linked = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        need(all(q in ca for q in ('/std:c++17','/D_HAS_STD_BYTE=0','/fp:precise','/O2','/MT','/GL-'))
             and ca.count(str(SOURCE)) == 1 and '/Fo'+str(obj) in ca and '/I'+str(headers) in ca,
             'Original precise/static utility ABI and one-entry compile recipe required')
        need(len(linked) == len(set(linked)) == 7 and set(linked) == {Path(q['path']).resolve() for q in objects}|{obj.resolve()},
             'Exactly six original BI4 objects plus one private entry; no physical objects')
        tools = [Path(q['program']) for q in (cc,lc)]
        need(all('/14.36.32532/' in q.as_posix() for q in tools), 'Actual original MSVC tools required')
        before += [stat(q) for q in tools]
        need(all(stat(q['path']) == q for q in before), 'Consumed source/object/tool changed before build')
        calls.append(invoke(TAG+'.compile',[cc['program'],*ca],OUT,env))
        calls.append(invoke(TAG+'.link',[lc['program'],*la],OUT,env))
        need(all(stat(q['path']) == q for q in before), 'Consumed source/object/tool changed during build')
        save(check,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(SOURCE),note=stat(NOTE),baseline_build=stat(BASE),
            source_archive=b['source_archive'],physical_source_archive=b['physical_source_archive'],source_capture=b['source_capture'],
            objects=objects,generated=generated,core_derivation=stat(proof),core_diff=stat(diff),calls=calls,
            consumed=before,consumed_stats_unchanged=True,actual_link_objects=7,retained_reader_objects=6,new_entry_objects=1,
            JSph_objects_linked=False,source_and_receiver_numeric_cores_byte_identical=True,original_field_and_numerical_guards_changed=False,
            profiles=['short4'],allowed_group='psi0',completed_steps=[2000001,2002001,2004001,2006001],samples=4,end=2006001,
            new_updates=6001,fixed_dt_s=.000005,source_material_CSV_keys=15,receiver_material_CSV_keys=17,
            typed_arrays=22,active_IDs=6805,declared_Kernel_XML_CSV=2,actual_AS_coefficient=.3,actual_AS_exponent=2.55,
            source_CLI_exposed=False,formal_CLI_exposed=False,window_CLI_exposed=False,HG_proven_by_reader=False,
            runtime_files=[],runtime_recipe='same original /MT and seven-object closure; no added private DLL',
            PE_system_imports_independently_audited=False,same_dt_prefix_regression_is_half=False,
            native_decodes=0,solver_invocations=0,automatic_next_job=False,physical_acceptance=False,SHA_scans=0))
    except Exception as error:
        actual = [stat(L/(TAG+q)) for q in ('.compile.call.json','.link.call.json') if (L/(TAG+q)).is_file()]
        if not check.exists(): save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=actual,consumed=before,
            partial_outputs_preserved=True,native_decodes=0,solver_invocations=0,physical_acceptance=False))
        raise


if __name__ == '__main__': main()
