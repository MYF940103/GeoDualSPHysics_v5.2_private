"""Build only the exact failed99 HG saved-prefix utility; never decode or solve."""
import argparse
import difflib
import os
import subprocess
from pathlib import Path
from zipfile import ZipFile
import c08_h18_as255_native_r1_build as old

T, L = old.T, old.L
TAG = 'c08_h18_hg_failed99_native_r1'
SCRIPT = Path(__file__).resolve()
SOURCE, NOTE = T/'support'/(TAG+'.cpp'), T/'notes'/(TAG+'.md')
BASE, OUT = L/'c08_h18_as255_native_r1.build.json', T/'outputs'/(TAG+'_build')
need, read, stat, bind, save, invoke = old.need, old.read, old.stat, old.bind, old.save, old.invoke
OBSERVED = r'''static unsigned ObservedPartialSamples(const fs::path& runCsv,unsigned expected){
  Need(H18Rows.size()==301&&H18Rows.back().completed==2600000&&expected==2196001&&H18Rows[98].completed==expected,"Only actual99-of301 HG saved prefix is supported");
  Need(!fs::exists(runCsv),"The failed HG run has no normal-completion Run.csv");
  const fs::path data=runCsv.parent_path()/"data";unsigned count=0;
  for(const auto& p:fs::directory_iterator(data))if(p.is_regular_file()&&p.path().extension()==".bi4"&&p.path().filename().string().rfind("Part_",0)==0)count++;
  Need(count==99,"Actual failed HG saved-file count differs");
  std::ifstream f(runCsv.parent_path()/"Run.out");Need(bool(f),"Actual failed Run.out missing");std::ostringstream text;text<<f.rdbuf();
  Need(text.str().find("GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.")!=std::string::npos&&text.str().find("Finished execution (code=1).")!=std::string::npos&&text.str().find("DynamicPoreWall rejected: stage=1 sorted_slot=690 native_id=894 step_start=10.983389999668779 step=2196678 B=(4.9000000000000004,0,-0.019999999999999962) normal=(0,0,0.0399999991).")!=std::string::npos,"Exact reported HG wall894 failure/exit text differs");
  // Reported rejection is not an unsaved native state or independent Win32 audit.
  return count;
}'''
PLAN = r'''static std::vector<unsigned> Planned(const fs::path& path,unsigned samples,unsigned expected){
  Need(fs::equivalent(path,H18PlanPath)&&H18Rows.size()==301&&H18Rows.back().completed==2600000&&samples==99&&expected==H18Rows[98].completed&&expected==2196001,"Untouched complete301 plan and exact99 saved prefix required");
  std::vector<unsigned> steps;for(unsigned part=0;part<samples;part++)steps.push_back(H18Rows[part].completed);return steps;
}'''


def reversible(raw, changes):
    current = raw
    for label, before, after in changes:
        a, b = before.encode(), after.encode(); need(current.count(a)==1, 'Unique original anchor: '+label)
        current = current.replace(a,b,1)
    inverse = current
    for label, before, after in reversed(changes):
        a, b = before.encode(), after.encode(); need(inverse.count(b)==1, 'Unique inverse anchor: '+label)
        inverse = inverse.replace(b,a,1)
    need(inverse==raw, 'Declared inverse must restore all original bytes')
    return current


def derive(entry, receiver):
    e, r = entry.decode(), receiver.decode()
    source_cli = e[e.index(' if(argc==7&&std::wstring(argv[1])==L"--source"){'):e.index(' H18Need(argc==9')]
    old_cli = next(q for q in e.splitlines() if q.startswith(' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver"'))
    new_cli = ' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver","Use --receiver failed99_hg psi0 DATA PRE COMPLETE301PLAN PROFILE17_CSV FRESHOUT");const std::string profile=std::filesystem::path(argv[2]).string(),group=std::filesystem::path(argv[3]).string();H18Need(profile=="failed99_hg"&&group=="psi0","Only actual HG failed99 psi0 is exposed");H18ReadPlan(argv[6],false,H18FormalEnd,H18FormalSamples);H18ReadReceiverProfile(argv[7],group);H18Need(H18Rows.size()==301&&H18Rows.back().completed==2600000&&H18Bits(H18AS,.3f)&&H18Bits(H18Exp,2.55f),"Exact original full301 AS.3/n2.55 required");const unsigned samples=99u,end=H18Rows[98].completed;H18Need(end==2196001,"Actual last saved step differs");const std::filesystem::path data=argv[4],out=argv[8];H18Need(std::filesystem::is_directory(data)&&!std::filesystem::exists(out),"Missing DATA or protected output");'
    partial = r'\"partial\":true,\"whole_run_passed\":false,\"whole_run_native_passed\":false,\"full_run_completed\":false,\"saved_prefix_native_passed\":true,\"original_target_completed_step\":2600000,\"original_target_samples\":301,\"observed_saved_samples\":99,\"last_saved_part\":98,\"last_saved_completed_step\":2196001,\"original_plan_records\":301,\"observed_plan_prefix_records\":99,\"plan_modified\":false,\"unsaved_state_reconstructed\":false,'
    ec = [('close source CLI',source_cli,' // No source/full/formal/window CLI in this failed99 adapter.\n'),
          ('closed exact receiver CLI',old_cli,new_cli),
          ('partial metadata',r'\"stage\":\"c08_h18_wend_native_r1.metadata\",\"passed\":true,',r'\"stage\":\"c08_h18_hg_failed99_native_r1.metadata\",\"passed\":true,'+partial)]
    a = r.index('static unsigned RunSamples('); old_run = r[a:r.index('static unsigned Number(',a)].rstrip()
    a = r.index('static std::vector<unsigned> Planned('); old_plan = r[a:r.index('int wmain(',a)].rstrip()
    rc = [('failed observation',old_run,OBSERVED),('full301 plan with99 reads',old_plan,PLAN),
          ('call failed observation','Need(RunSamples(data.parent_path()/"Run.csv",expected)==samples,"Normal Run.csv end/count differs from the explicit owner plan");','Need(ObservedPartialSamples(data.parent_path()/"Run.csv",expected)==samples,"Actual failed99 saved-file count differs");'),
          ('saved-scope message','Actual final global step/full native coverage incomplete','Actual failed99 last saved step/native coverage incomplete'),
          ('partial completion',r'\"stage\":\"c08_h18_wend_native_r1.receiver\",\"passed\":true,',r'\"stage\":\"c08_h18_hg_failed99_native_r1.receiver\",\"passed\":false,\"diagnostic_complete\":true,\"certified_receiver\":false,\"source_PRE_is_complete\":true,\"actual_terminal_solver_step_proven\":false,\"new_updates_is_last_saved_scope\":true,'+partial),
          ('failed-runtime distinction',r'\"completed_runtime_Run_csv_checked\":true',r'\"completed_runtime_Run_csv_checked\":false,\"actual_failed_Runout_text_checked\":true,\"actual_owner_Win32_failure_binding_required\":true')]
    ne, nr = reversible(entry,ec), reversible(receiver,rc)
    begin, end = '  for(unsigned part=0;part<samples;part++){', '  Need(previous==expected'
    need(r.count(begin)==nr.decode().count(begin)==1, 'One original22 validation loop required')
    loop = r[r.index(begin):r.index(end)].encode(); text = nr.decode()
    need(text[text.index(begin):text.index(end)].encode()==loop, 'Original22 field validation loop changed')
    return ne,nr,ec,rc


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized',action='store_true'); args=parser.parse_args()
    need(args.execution_authorized,'Author-only until root reviews and independently authorizes one build')
    check=L/(TAG+'.build.json'); need(not OUT.exists() and not check.exists() and all(not (L/(TAG+s)).exists() for s in ('.compile.call.json','.compile.log','.link.call.json','.link.log')),'Existing complete/partial utility protected')
    before,calls=[],[]
    try:
        b=read(BASE)
        need(b['passed'] and b['consumed_stats_unchanged'] and b['actual_link_objects']==7 and not b['JSph_objects_linked'] and b['explicit_AS_exponent']==2.55 and b['formal_samples']==301 and b['declared_Kernel_XML_CSV']==2,'Passed originalAS255 closure required')
        objects=[bind(q) for q in b['objects']]
        need(len(objects)==6 and {Path(q['path']).stem for q in objects}=={'Functions','JBinaryData','JException','JObject','JPartDataBi4','JPartDataHead'},'Same six BI4 utility objects required')
        originals={Path(q['path']).name:bind(q) for q in b['generated']}
        need(set(originals)=={'h18_as255_entry_r1.cpp','h18_headers_r1.h','public22_core_r1.h','h18_source_core_r1.cpp','h18_receiver_core_r1.cpp','h18_profiles_r1.h'},'Actual six-file AS255 source closure required')
        before=[stat(q) for q in (BASE,SCRIPT,SOURCE,NOTE,Path(old.__file__),Path(old.old.__file__),Path(old.old.e.__file__))]
        before += [bind(b[k]) for k in ('program','source','source_archive','physical_source_archive','source_capture','core_derivation')]+objects+list(originals.values())+[bind(q) for q in b['calls']]
        need(len(b['calls'])==2,'Original compile/link pair required'); cc,lc=[read(q['path']) for q in b['calls']]
        need(all(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q['ownership_failure'] is None for q in (cc,lc)),'Original utility calls must pass')
        need(SOURCE.read_bytes().count(b'#include "h18_hg_failed99_entry_r1.cpp"')==1,'One private entry include required')
        raw=Path(originals['h18_as255_entry_r1.cpp']['path']).read_bytes(); rr=Path(originals['h18_receiver_core_r1.cpp']['path']).read_bytes()
        revised,revised_receiver,ec,rc=derive(raw,rr)
        OUT.mkdir(); headers=OUT/'headers'; headers.mkdir()
        with ZipFile(b['source_archive']['path']) as archive:
            for item in archive.infolist():
                if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
                    dest=headers/Path(item.filename).name; need(not dest.exists(),'Duplicate archived header leaf'); dest.write_bytes(archive.read(item))
        with ZipFile(b['physical_source_archive']['path']) as archive:
            for leaf in ('JPartDataBi4.h','JPartDataHead.h','JBinaryData.h','TypesDef.h'):
                need((headers/leaf).read_bytes()==archive.read('src/source/'+leaf),'Original utility/physical ABI differs: '+leaf)
            for leaf in ('JGravityPreloadState.h','FunSoilMaterial.h'):(headers/leaf).write_bytes(archive.read('src/source/'+leaf))
        generated=[]
        for leaf,q in originals.items():
            payload=revised if leaf=='h18_as255_entry_r1.cpp' else revised_receiver if leaf=='h18_receiver_core_r1.cpp' else Path(q['path']).read_bytes()
            dest=OUT/('h18_hg_failed99_entry_r1.cpp' if leaf=='h18_as255_entry_r1.cpp' else leaf); dest.write_bytes(payload); need(dest.read_bytes()==payload,'Actual derived source copy differs'); generated.append(stat(dest))
        diffs=[]
        for label,a,z in (('entry',raw,revised),('receiver',rr,revised_receiver)):
            dest=OUT/(label+'_core.diff'); dest.write_text(''.join(difflib.unified_diff(a.decode().splitlines(True),z.decode().splitlines(True),fromfile='sealed_AS255/'+label,tofile='failed99_hg/'+label)),encoding='utf-8'); diffs.append(stat(dest))
        proof=OUT/'core_derivation.json'
        save(proof,dict(stage=TAG+'.derive',baseline_build=stat(BASE),baseline_generated=list(originals.values()),entry_declared_replacements=ec,receiver_declared_replacements=rc,exact_inverse_original_entry_bytes=True,exact_inverse_original_receiver_bytes=True,source_numeric_core_byte_identical=True,original_field_validation_loop_bytes_identical=True,original_field_and_numerical_guards_changed=False,explicit_profile='failed99_hg',allowed_group='psi0',original_plan_records=301,observed_prefix_records=99,last_saved_part=98,last_saved_completed_step=2196001,original_target_completed_step=2600000,whole_run_native_passed=False,full_run_completed=False,unsaved_state_reconstructed=False,actual_terminal_solver_step_proven=False,old_files_changed=False))
        before += generated+diffs+[stat(proof)]+[stat(q) for q in headers.iterdir()]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode==0,'Original MSVC setup failed'); env={k.upper():v for k,v in os.environ.items()}; env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        need(env['VCTOOLSVERSION']=='14.36.32532','Same MSVC14.36 required')
        for k in ('CL','_CL_'):env.pop(k,None)
        oldout=Path(b['program']['path']).parent; obj=OUT/'reader.obj'; exe=OUT/'C08H18HgFailed99NativeR1_win64.exe'
        ca=[str(SOURCE) if q==b['source']['path'] else q.replace(str(oldout),str(OUT)) for q in cc['arguments']]
        la=[q.replace(b['program']['path'],str(exe)).replace(str(oldout),str(OUT)) for q in lc['arguments']]
        linked=[Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        need(all(q in ca for q in ('/std:c++17','/D_HAS_STD_BYTE=0','/fp:precise','/O2','/MT','/GL-')) and ca.count(str(SOURCE))==1 and '/Fo'+str(obj) in ca and '/I'+str(headers) in ca,'Original utility precise/static ABI recipe required')
        need(len(linked)==len(set(linked))==7 and set(linked)=={Path(q['path']).resolve() for q in objects}|{obj.resolve()},'Link only six original utility objects and one new entry')
        tools=[Path(q['program']) for q in (cc,lc)]; need(all('/14.36.32532/' in q.as_posix() for q in tools),'Original MSVC tool paths required'); before += [stat(q) for q in tools]
        need(all(stat(q['path'])==q for q in before),'A consumed input changed before build')
        calls.append(invoke(TAG+'.compile',[cc['program'],*ca],OUT,env)); calls.append(invoke(TAG+'.link',[lc['program'],*la],OUT,env))
        need(all(stat(q['path'])==q for q in before),'A consumed input changed during build')
        save(check,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(SOURCE),note=stat(NOTE),baseline_build=stat(BASE),objects=objects,generated=generated,core_derivation=stat(proof),core_diffs=diffs,calls=calls,consumed=before,consumed_stats_unchanged=True,actual_link_objects=7,retained_reader_objects=6,new_entry_objects=1,JSph_objects_linked=False,source_numeric_core_byte_identical=True,original_field_validation_loop_bytes_identical=True,original_field_and_numerical_guards_changed=False,forensic_receiver_only=True,explicit_profile='failed99_hg',allowed_group='psi0',original_plan_records=301,observed_prefix_records=99,last_saved_part=98,last_saved_completed_step=2196001,last_saved_zero_based_step=2196000,original_target_completed_step=2600000,fixed_dt_s=.000005,source_material_CSV_keys=15,receiver_material_CSV_keys=17,typed_arrays=22,active_IDs=6805,declared_Kernel_XML_CSV=2,AS_coefficient=.3,AS_exponent=2.55,source_CLI_exposed=False,formal_CLI_exposed=False,whole_run_passed=False,whole_run_native_passed=False,full_run_completed=False,HG_proven_by_reader=False,unsaved_state_reconstructed=False,actual_terminal_solver_step_proven=False,runtime_files=[],runtime_recipe='same original /MT and seven-object closure; no added private DLL',native_decodes=0,solver_invocations=0,automatic_next_job=False,physical_acceptance=False,SHA_scans=0))
    except Exception as error:
        actual=[stat(L/(TAG+s)) for s in ('.compile.call.json','.link.call.json') if (L/(TAG+s)).is_file()]
        if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=actual,consumed=before,partial_outputs_preserved=True,native_decodes=0,solver_invocations=0,physical_acceptance=False))
        raise


if __name__=='__main__':main()
