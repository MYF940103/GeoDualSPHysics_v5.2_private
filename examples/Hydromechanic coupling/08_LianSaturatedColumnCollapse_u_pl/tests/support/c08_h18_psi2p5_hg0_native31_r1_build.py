"""Build only a closed31-frame psi2p5 HG0 reader over the unchanged AS255 cores."""
import argparse
import difflib
import os
import subprocess
from pathlib import Path
from zipfile import ZipFile
import c08_h18_as255_native_r1_build as old

T, L = old.T, old.L
TAG = 'c08_h18_psi2p5_hg0_native31_r1'
SCRIPT = Path(__file__).resolve()
SOURCE, NOTE = T / 'support' / (TAG + '.cpp'), T / 'notes' / (TAG + '.md')
BASE, OUT = L / 'c08_h18_as255_native_r1.build.json', T / 'outputs' / (TAG + '_build')
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke
REPLACEMENTS = (
    ('close source CLI',
     ' if(argc==7&&std::wstring(argv[1])==L"--source"){\n  const std::wstring mode=argv[2];H18Need(mode==L"partial"||mode==L"full","Source mode must be partial or full");H18ReadPlan(argv[5],true,H18Event,H18SourceSamples);return h18source::wmain(argc,argv);\n }',
     ' // Only the window31/psi2p5 receiver CLI is exposed; no source/formal/window91 command.'),
    ('closed CLI help',
     'Use --source partial|full DATA MATERIAL_CSV PLAN FRESHOUT; or --receiver window|formal GROUP DATA PRE PLAN PROFILE_CSV FRESHOUT',
     'Use --receiver window31 psi2p5 DATA PRE PLAN PROFILE_CSV FRESHOUT'),
    ('exact extent and group',
     'const bool window=profile=="window";H18Need(window||profile=="formal","Only .90-window or full3 receiver profiles");const unsigned end=window?H18WindowEnd:H18FormalEnd,samples=window?H18WindowSamples:H18FormalSamples;',
     'H18Need(profile=="window31"&&group=="psi2p5","Only window31/psi2p5 is exposed");const unsigned end=2060000u,samples=31u;'),
    ('exact actual saves and AS03',
     'H18ReadPlan(argv[6],false,end,samples);H18ReadReceiverProfile(argv[7],group);',
     'H18ReadPlan(argv[6],false,end,samples);for(unsigned part=0;part<31u;part++)H18Need(H18Rows[part].completed==(part<30u?2000001u+2000u*part:2060000u),"Only actual first-post31 saves with forced final2060000 are admitted");H18ReadReceiverProfile(argv[7],group);H18Need(H18Bits(H18AS,.3f)&&H18Bits(H18Exp,2.55f),"Only AS.3/exponent2.55 is admitted");'),
    ('actual HG sidecars absent',
     'for(unsigned part=0;part<samples;part++){\n  headerPart=part;',
     'H18Need(!std::filesystem::exists(data.parent_path()/"C08OptPlasticHG.csv")&&!std::filesystem::exists(data.parent_path()/"C08OptPlasticHGPolicy.json"),"HG0 output must not contain private optimized HG sidecars");\n for(unsigned part=0;part<samples;part++){\n  headerPart=part;'),
    ('metadata stage only','c08_h18_wend_native_r1.metadata','c08_h18_psi2p5_hg0_native31_r1.metadata'),
    ('explicit missing-sidecar scope',
     r'\"metadata_header_scans\":',
     r'\"HG_expected\":false,\"HG_sidecars_absent\":true,\"HG_kernel_correctness_claimed\":false,\"metadata_header_scans\":'),
)


def derive(raw):
    changed = raw
    for label,before,after in REPLACEMENTS:
        a,b = before.encode('utf-8'),after.encode('utf-8')
        need(changed.count(a) == 1,'Unique original entry anchor differs: '+label)
        changed = changed.replace(a,b,1)
    inverse = changed
    for label,before,after in reversed(REPLACEMENTS):
        a,b = before.encode('utf-8'),after.encode('utf-8')
        need(inverse.count(b) == 1,'Unique reverse entry anchor differs: '+label)
        inverse = inverse.replace(b,a,1)
    need(inverse == raw,'Declared count/profile/sidecar edits did not restore every original entry byte')
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized',action='store_true')
    need(parser.parse_args().execution_authorized,'Author-only until root full read and separate utility-build authorization')
    check = L / (TAG + '.build.json'); intdir = Path(os.environ['TEMP']) / TAG
    need(not OUT.exists() and not intdir.exists() and ' ' not in str(intdir) and not check.exists()
         and all(not (L/(TAG+s)).exists() for s in ('.compile.call.json','.compile.log','.link.call.json','.link.log')),
         'Existing complete/partial utility is protected; no retry or overwrite')
    before, calls, setup_result = [], [], None
    try:
        b = read(BASE)
        need(b['passed'] and b['consumed_stats_unchanged'] and b['actual_link_objects'] == 7
             and not b['JSph_objects_linked'] and b['declared_Kernel_XML_CSV'] == 2
             and b['source_material_CSV_keys'] == 15 and b['receiver_material_CSV_keys'] == 17
             and b['exact_inverse_original_entry_bytes'] and not b['original_field_and_numerical_guards_changed']
             and b['formal_samples'] == 301 and b['window_samples'] == 91 and b['explicit_AS_exponent'] == 2.55,
             'Passed original AS255 seven-object native closure required')
        objects = [bind(q) for q in b['objects']]
        need(len(objects) == 6 and {Path(q['path']).stem for q in objects}
             == {'Functions','JBinaryData','JException','JObject','JPartDataBi4','JPartDataHead'},'Exactly six original BI4 utility objects required')
        originals = {Path(q['path']).name:bind(q) for q in b['generated']}
        need(len(originals) == len(b['generated']) == 6 and set(originals)
             == {'h18_as255_entry_r1.cpp','h18_headers_r1.h','public22_core_r1.h','h18_source_core_r1.cpp','h18_receiver_core_r1.cpp','h18_profiles_r1.h'},
             'Original six-file source/header closure required')
        before = [stat(q) for q in (BASE,SCRIPT,SOURCE,NOTE,Path(old.__file__),Path(old.old.__file__),Path(old.old.e.__file__))]
        before += [bind(b[k]) for k in ('program','source','source_archive','physical_source_archive','source_capture','core_derivation')]
        before += objects + list(originals.values()) + [bind(q) for q in b['calls']]
        need(len(b['calls']) == 2,'Original one-CL/one-link receipts required')
        cc,lc = [read(q['path']) for q in b['calls']]
        need(all(q['actual_Popen_wait_exit'] == q['actual_Win32_exit'] == 0 and q['ownership_failure'] is None and q['child'] for q in (cc,lc)),
             'Original actual utility owned exits required')
        need(SOURCE.read_bytes().count(b'#include "h18_psi2p5_hg0_native31_entry_r1.cpp"') == 1,'Exactly one private derived-entry include required')
        raw = Path(originals['h18_as255_entry_r1.cpp']['path']).read_bytes(); revised = derive(raw)
        OUT.mkdir(); intdir.mkdir(); headers = OUT/'headers'; headers.mkdir()
        with ZipFile(b['source_archive']['path']) as archive:
            for item in archive.infolist():
                if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
                    dest = headers/Path(item.filename).name; need(not dest.exists(),'Duplicate archived header leaf'); dest.write_bytes(archive.read(item))
        with ZipFile(b['physical_source_archive']['path']) as archive:
            for leaf in ('JPartDataBi4.h','JPartDataHead.h','JBinaryData.h','TypesDef.h'):
                need((headers/leaf).read_bytes() == archive.read('src/source/'+leaf),'Original utility/physical ABI differs: '+leaf)
            for leaf in ('JGravityPreloadState.h','FunSoilMaterial.h'): (headers/leaf).write_bytes(archive.read('src/source/'+leaf))
        generated = []
        for leaf,entry in originals.items():
            payload = revised if leaf == 'h18_as255_entry_r1.cpp' else Path(entry['path']).read_bytes()
            dest = OUT/('h18_psi2p5_hg0_native31_entry_r1.cpp' if leaf == 'h18_as255_entry_r1.cpp' else leaf)
            dest.write_bytes(payload); need(dest.read_bytes() == payload,'Private source/header copy differs'); generated.append(stat(dest))
        diff, proof = OUT/'entry_profile.diff',OUT/'core_derivation.json'
        diff.write_text(''.join(difflib.unified_diff(raw.decode().splitlines(True),revised.decode().splitlines(True),
            fromfile='sealed_AS255/entry',tofile='private_window31_psi2p5_HG0/entry')),encoding='utf-8')
        save(proof,dict(stage=TAG+'.derive',baseline_build=stat(BASE),baseline_generated=list(originals.values()),
            replacements=[dict(label=l,before=a,after=z,count=1) for l,a,z in REPLACEMENTS],exact_inverse_original_entry_bytes=True,
            source_and_receiver_numeric_cores_byte_identical=True,original_field_and_numerical_guards_changed=False,
            profiles=['window31'],allowed_group='psi2p5',samples=31,end=2060000,new_updates=60000,fixed_dt_s=.000005,
            first30_completed_steps=[2000001+2000*i for i in range(30)],forced_final_completed_step=2060000,
            scalar_plus_equal_dt=True,HG_expected=False,HG_sidecars_absence_checked=True,HG602_gate_added=False,
            solver_internal_wall_threshold_not_claimed_native_checked=True,old_files_changed=False))
        before += generated + [stat(diff),stat(proof)] + [stat(q) for q in headers.iterdir()]
        envcmd = intdir/'env.cmd'
        envcmd.write_bytes(('@echo off\r\ncall "D:\\Program Files\\VS2022\\VC\\Auxiliary\\Build\\vcvarsall.bat" x64 -vcvars_ver=14.36 >nul\r\n'
                            'if errorlevel 1 exit /b %errorlevel%\r\nset\r\n').encode('ascii'))
        setup_argv = [str(Path(os.environ['SystemRoot'])/'System32/cmd.exe'),'/d','/c',str(envcmd)]
        setup = subprocess.run(setup_argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        setup_result = dict(argv=setup_argv,environment_cmd=stat(envcmd),actual_Popen_wait_exit=setup.returncode,
                            stderr=setup.stderr.decode('mbcs',errors='replace'),stdout_environment_not_written=True)
        need(setup.returncode == 0,'Original MSVC environment setup failed')
        env = {k.upper():v for k,v in os.environ.items()}
        env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        need(env['VCTOOLSVERSION'] == '14.36.32532','Original six-object MSVC14.36 required')
        for key in ('CL','_CL_'):env.pop(key,None)
        oldout = Path(b['program']['path']).parent; obj = OUT/'reader.obj'; exe = OUT/'C08H18Psi2p5Hg0Native31R1_win64.exe'
        ca = [str(SOURCE) if q == b['source']['path'] else q.replace(str(oldout),str(OUT)) for q in cc['arguments']]
        la = [q.replace(b['program']['path'],str(exe)).replace(str(oldout),str(OUT)) for q in lc['arguments']]
        linked = [Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        need(all(q in ca for q in ('/std:c++17','/D_HAS_STD_BYTE=0','/fp:precise','/O2','/MT','/GL-'))
             and ca.count(str(SOURCE)) == 1 and '/Fo'+str(obj) in ca and '/I'+str(headers) in ca,'Original precise/static one-TU utility ABI required')
        need(len(linked) == len(set(linked)) == 7 and set(linked) == {Path(q['path']).resolve() for q in objects}|{obj.resolve()},
             'Only six original BI4 objects plus one new entry may link')
        tools = [Path(q['program']) for q in (cc,lc)]
        need(all('/14.36.32532/' in q.as_posix() for q in tools),'Original actual MSVC tools required')
        before += [stat(q) for q in tools] + [stat(envcmd)]
        need(all(stat(q['path']) == q for q in before),'Bound source/object changed before build')
        for phase,tool,args in (('compile',cc['program'],ca),('link',lc['program'],la)):
            calls.append(invoke(TAG+'.'+phase,[tool,*args],OUT,env)); actual = read(calls[-1]['path'])
            need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None,
                 'Actual owned utility CL/link exit failed')
        need(all(stat(q['path']) == q for q in before),'Bound source/object changed during build')
        save(check,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(SOURCE),note=stat(NOTE),baseline_build=stat(BASE),
            source_archive=b['source_archive'],physical_source_archive=b['physical_source_archive'],source_capture=b['source_capture'],
            objects=objects,generated=generated,core_derivation=stat(proof),core_diff=stat(diff),calls=calls,environment_setup=setup_result,
            consumed=before,consumed_stats_unchanged=True,actual_link_objects=7,retained_reader_objects=6,new_entry_objects=1,
            JSph_objects_linked=False,CUDA_objects_linked=False,source_and_receiver_numeric_cores_byte_identical=True,
            original_field_and_numerical_guards_changed=False,profiles=['window31'],allowed_group='psi2p5',samples=31,end=2060000,
            new_updates=60000,fixed_dt_s=.000005,receiver_material_CSV_keys=17,typed_arrays=22,active_IDs=6805,
            declared_Kernel_XML_CSV=2,actual_AS_coefficient=.3,actual_AS_exponent=2.55,HG_expected=False,
            HG_sidecars_absence_checked=True,HG_kernel_correctness_claimed=False,HG602_gate_added=False,
            source_CLI_exposed=False,formal_CLI_exposed=False,window91_CLI_exposed=False,runtime_files=[],
            same_static_MT_utility_ABI=True,solver_internal_wall_threshold_not_claimed_native_checked=True,
            physical_dependencies_written=False,native_decodes=0,solver_invocations=0,help_invocations=0,
            automatic_next_job=False,physical_acceptance=False,SHA_scans=0))
    except Exception as error:
        actual = [stat(L/(TAG+s)) for s in ('.compile.call.json','.link.call.json') if (L/(TAG+s)).is_file()]
        if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=actual,consumed=before,
            environment_setup=setup_result,partial_outputs_preserved=True,automatic_retry=False,native_decodes=0,
            solver_invocations=0,physical_acceptance=False,SHA_scans=0))
        raise


if __name__ == '__main__':
    main()
