"""Build only a separate failed90 Wendland receiver reader, never decode or solve."""
import argparse,difflib,os,subprocess
from pathlib import Path
import c08_h18_wend_native_r1_build as prior

e=prior.e
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='c08_h18_wend_partial_native_r1';OUT=T/'outputs'/(TAG+'_build');BASE=L/'c08_h18_wend_native_r1.build.json'
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke


OBSERVED=r'''static unsigned ObservedPartialSamples(const fs::path& runCsv,unsigned expected){
  Need(H18Rows.size()==91&&H18Rows.back().completed==2180000&&expected==2178001&&H18Rows[89].completed==expected,"Only the observed90-of91 receiver prefix is supported");
  Need(!fs::exists(runCsv),"A normal-completion Run.csv is not part of this failed-source evidence");
  const fs::path data=runCsv.parent_path()/"data";unsigned count=0;
  for(const auto& p:fs::directory_iterator(data))if(p.is_regular_file()&&p.path().extension()==".bi4"&&p.path().filename().string().rfind("Part_",0)==0)count++;
  Need(count==90,"Actual failed receiver saved-file count differs");
  std::ifstream f(runCsv.parent_path()/"Run.out");Need(bool(f),"Actual failed Run.out is missing");std::ostringstream text;text<<f.rdbuf();
  Need(text.str().find("GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.")!=std::string::npos&&text.str().find("Finished execution (code=1).")!=std::string::npos,"Actual recorded dynamic-wall failure/exit text differs");
  // A log is not independent proof of Win32 status; caller still binds real owner/call/run receipts.
  return count;
}'''

PLAN=r'''static std::vector<unsigned> Planned(const fs::path& path,unsigned samples,unsigned expected){
  Need(fs::equivalent(path,H18PlanPath)&&H18Rows.size()==91&&H18Rows.back().completed==2180000&&samples==90&&expected==H18Rows[89].completed&&expected==2178001,"Untouched complete91 plan and explicit90 saved-prefix scope required");
  std::vector<unsigned> steps;for(unsigned part=0;part<samples;part++)steps.push_back(H18Rows[part].completed);return steps;
}'''


def derive_receiver(raw):
    first=raw.index('static unsigned RunSamples(');last=raw.index('static unsigned Number(',first);old_run=raw[first:last].rstrip()
    first=raw.index('static std::vector<unsigned> Planned(');last=raw.index('int wmain(',first);old_plan=raw[first:last].rstrip()
    changes=[
      (old_run,OBSERVED),(old_plan,PLAN),
      ('Need(RunSamples(data.parent_path()/"Run.csv",expected)==samples,"Normal Run.csv end/count differs from the explicit owner plan");','Need(ObservedPartialSamples(data.parent_path()/"Run.csv",expected)==samples,"Actual failed saved-prefix file count differs");'),
      ('Actual final global step/full native coverage incomplete','Actual saved-prefix last step/all90 native coverage incomplete'),
      (r'\"stage\":\"c08_h18_wend_native_r1.receiver\",\"passed\":true',r'\"stage\":\"c08_h18_wend_partial_native_r1.receiver\",\"passed\":false,\"diagnostic_complete\":true,\"saved_prefix_native_passed\":true,\"profile\":\"window_partial\",\"partial\":true,\"whole_run_native_passed\":false,\"full_run_completed\":false,\"source_PRE_is_complete\":true,\"certified_receiver\":false,\"original_target_completed_step\":2180000,\"original_target_samples\":91,\"observed_saved_samples\":90,\"last_saved_part\":89,\"last_saved_completed_step\":2178001,\"actual_terminal_solver_step_proven\":false,\"unsaved_state_reconstructed\":false,\"original_plan_records\":91,\"observed_plan_prefix_records\":90,\"plan_modified\":false,\"new_updates_is_last_saved_scope\":true'),
      (r'\"completed_runtime_Run_csv_checked\":true',r'\"completed_runtime_Run_csv_checked\":false,\"actual_failed_Runout_text_checked\":true,\"actual_owner_Win32_failure_binding_required\":true')]
    return prior.patch(raw,changes),changes


def derive_entry(raw):
    first=raw.index(' if(argc==7&&std::wstring(argv[1])==L"--source"){');last=raw.index(' H18Need(argc==9',first);source_cli=raw[first:last]
    old_cli=next(line for line in raw.splitlines() if line.startswith(' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver"'))
    new_cli=''' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver","Use --receiver failed90 psi0 DATA PRE COMPLETE91PLAN PROFILE17_CSV FRESHOUT");const std::string profile=std::filesystem::path(argv[2]).string(),group=std::filesystem::path(argv[3]).string();H18Need(profile=="failed90"&&group=="psi0","Only the actual failed AS.3 psi0 saved prefix is supported");H18ReadPlan(argv[6],false,H18WindowEnd,H18WindowSamples);H18ReadReceiverProfile(argv[7],group);H18Need(H18Rows.size()==91&&H18Rows.back().completed==2180000&&H18Bits(H18AS,.3f)&&H18Bits(H18Exp,3.825f),"Original91 plan/AS.3/n3.825 scope differs");const unsigned samples=90,end=H18Rows[89].completed;H18Need(end==2178001,"Actual last saved-prefix step differs");const std::filesystem::path data=argv[4],out=argv[8];H18Need(std::filesystem::is_directory(data)&&!std::filesystem::exists(out),"Missing DATA or protected output");'''
    source_namespace='namespace h18source{\n#include "h18_source_core_r1.cpp"\n}\n'
    changes=[
      (source_namespace,'// Source trajectory decoder is deliberately unavailable in this failed-receiver adapter.\n'),
      (source_cli,' // No source/full/formal interface in the failed90 adapter.\n'),(old_cli,new_cli),
      (r'\"stage\":\"c08_h18_wend_native_r1.metadata\",\"passed\":true',r'\"stage\":\"c08_h18_wend_partial_native_r1.metadata\",\"passed\":false,\"saved_metadata_passed\":true,\"partial\":true,\"whole_run_native_passed\":false,\"full_run_completed\":false,\"original_target_samples\":91,\"original_target_completed_step\":2180000,\"actual_terminal_solver_step_proven\":false,\"unsaved_state_reconstructed\":false'),
      ('<<profile<<','<<"window_partial"<<')]
    return prior.patch(raw,changes),changes


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');a=parser.parse_args();need(a.execution_authorized,'Root must completely read before one explicit utility build')
    check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing/partial forensic build protected');calls=[];before=[]
    try:
        baseline=read(BASE);need(baseline['passed'] and baseline['consumed_stats_unchanged'] and baseline['declared_Kernel_XML_CSV']==2 and baseline['source_material_CSV_keys']==15 and baseline['receiver_material_CSV_keys']==17 and baseline['actual_link_objects']==7 and not baseline['JSph_objects_linked'],'Passed explicit Wendland utility baseline required')
        program=Path(bind(baseline['program'])['path']);oldout=program.parent;headers=oldout/'headers';objects=[bind(q) for q in baseline['objects']];need(len(objects)==6 and {Path(q['path']).stem for q in objects}=={'JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions'},'Exactly six sealed BI4 utility objects required')
        originals={Path(q['path']).name:bind(q) for q in baseline['generated']};leaves=('h18_wend_entry_r1.cpp','h18_headers_r1.h','h18_receiver_core_r1.cpp','h18_profiles_r1.h');need(all(k in originals for k in leaves),'Original passed generated core closure differs')
        source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');before=[stat(q) for q in (Path(__file__),Path(prior.__file__),Path(e.__file__),BASE,source,note)]+[originals[k] for k in leaves]+objects+[bind(baseline[k]) for k in ('program','source','core_derivation','source_archive','physical_source_archive')]
        before += [stat(headers/q) for q in ('JGravityPreloadState.h','FunSoilMaterial.h','JPartDataBi4.h','JPartDataHead.h','JBinaryData.h','TypesDef.h')]
        entry,ec=derive_entry(Path(originals['h18_wend_entry_r1.cpp']['path']).read_text(encoding='utf-8'));receiver,rc=derive_receiver(Path(originals['h18_receiver_core_r1.cpp']['path']).read_text(encoding='utf-8'))
        OUT.mkdir();generated={OUT/'h18_wend_partial_entry_r1.cpp':entry,OUT/'h18_receiver_core_r1.cpp':receiver,OUT/'h18_headers_r1.h':Path(originals['h18_headers_r1.h']['path']).read_text(encoding='utf-8'),OUT/'h18_profiles_r1.h':Path(originals['h18_profiles_r1.h']['path']).read_text(encoding='utf-8')}
        for dest,text in generated.items():dest.write_text(text,encoding='utf-8',newline='\n')
        diffs=[]
        for label,leaf,new in [('entry','h18_wend_entry_r1.cpp',entry),('receiver','h18_receiver_core_r1.cpp',receiver)]:
            dest=OUT/(label+'_core.diff');old=Path(originals[leaf]['path']).read_text(encoding='utf-8');dest.write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='passed_wendland/'+label,tofile='failed90/'+label,n=4)),encoding='utf-8');diffs.append(stat(dest))
        proof=OUT/'core_derivation.json';save(proof,dict(stage=TAG+'.derive',baseline=stat(BASE),baseline_generated=[originals[k] for k in leaves],generated=[stat(q) for q in generated],entry_declared_replacements=ec,receiver_declared_replacements=rc,reverse_declared_replacements_exact=True,original_field_and_numerical_guards_changed=False,original_plan_retained_in_memory_and_on_disk=True,original_plan_records=91,observed_prefix_records=90,last_saved_completed_step=2178001,original_target_completed_step=2180000,whole_run_native_passed=False,full_run_completed=False,source_PRE_array_reads=1,old_files_changed=False));before += [stat(q) for q in generated]+diffs+[stat(proof)]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching utility MSVC14.36 required')
        cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08H18WendPartialNative_win64.exe';ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)];la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[q['path'] for q in objects]]
        calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(q['path'])==q for q in before),'Frozen baseline/source/object changed during build')
        save(check,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(source),note=stat(note),baseline_build=stat(BASE),objects=objects,actual_link_objects=7,JSph_objects_linked=False,generated=[stat(q) for q in generated],core_derivation=stat(proof),core_diffs=diffs,calls=calls,consumed=before,consumed_stats_unchanged=True,forensic_receiver_only=True,declared_Kernel_XML_CSV=2,receiver_material_CSV_keys=17,observed_prefix_records=90,original_plan_records=91,original_field_and_numerical_guards_changed=False,decoder_invocations=0,solver_invocations=0,SHA_scans=0))
    except Exception as error:
        if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,SHA_scans=0))
        raise


if __name__=='__main__':main()
