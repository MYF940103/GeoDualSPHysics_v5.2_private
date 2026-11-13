"""Build only the separate failed34_as07 reader; never decode or solve."""
import argparse,difflib,os,subprocess
from pathlib import Path
import c08_h18_wend_partial_native_r1_build as r1

prior,e=r1.prior,r1.e
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='c08_h18_wend_partial_native_r2';OUT=T/'outputs'/(TAG+'_build')
BASE=L/'c08_h18_wend_native_r1.build.json';PARTIAL=L/'c08_h18_wend_partial_native_r1.build.json'

OBSERVED=r'''static unsigned ObservedPartialSamples(const fs::path& runCsv,unsigned expected){
  Need(H18Rows.size()==91&&H18Rows.back().completed==2180000&&expected==2066001&&H18Rows[33].completed==expected,"Only the observed34-of91 AS.7 receiver prefix is supported");
  Need(!fs::exists(runCsv),"A normal-completion Run.csv is not part of this failed-source evidence");
  const fs::path data=runCsv.parent_path()/"data";unsigned count=0;
  for(const auto& p:fs::directory_iterator(data))if(p.is_regular_file()&&p.path().extension()==".bi4"&&p.path().filename().string().rfind("Part_",0)==0)count++;
  Need(count==34,"Actual failed AS.7 receiver saved-file count differs");
  std::ifstream f(runCsv.parent_path()/"Run.out");Need(bool(f),"Actual failed Run.out is missing");std::ostringstream text;text<<f.rdbuf();
  Need(text.str().find("GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.")!=std::string::npos&&text.str().find("Finished execution (code=1).")!=std::string::npos&&text.str().find("DynamicPoreWall rejected: stage=0 sorted_slot=439 native_id=803 step_start=10.332704999693412 step=2066541 ")!=std::string::npos,"Actual recorded AS.7 wall803 failure/exit text differs");
  // Reported rejection text is not an independently reconstructed unsaved state or Win32 audit.
  return count;
}'''
PLAN=r'''static std::vector<unsigned> Planned(const fs::path& path,unsigned samples,unsigned expected){
  Need(fs::equivalent(path,H18PlanPath)&&H18Rows.size()==91&&H18Rows.back().completed==2180000&&samples==34&&expected==H18Rows[33].completed&&expected==2066001,"Untouched complete91 plan and explicit34 saved-prefix scope required");
  std::vector<unsigned> steps;for(unsigned part=0;part<samples;part++)steps.push_back(H18Rows[part].completed);return steps;
}'''

def derive_receiver(raw):
    failed90,baseline_changes=r1.derive_receiver(raw)
    changes=[(r1.OBSERVED,OBSERVED),(r1.PLAN,PLAN),
      ('Actual saved-prefix last step/all90 native coverage incomplete','Actual saved-prefix last step/all34 native coverage incomplete'),
      ('c08_h18_wend_partial_native_r1.receiver','c08_h18_wend_partial_native_r2.receiver'),
      (r'\"observed_saved_samples\":90',r'\"observed_saved_samples\":34'),
      (r'\"last_saved_part\":89',r'\"last_saved_part\":33'),
      (r'\"last_saved_completed_step\":2178001',r'\"last_saved_completed_step\":2066001'),
      (r'\"observed_plan_prefix_records\":90',r'\"observed_plan_prefix_records\":34')]
    return prior.patch(failed90,changes),failed90,baseline_changes,changes

def derive_entry(raw):
    failed90,baseline_changes=r1.derive_entry(raw)
    old_cli=next(line for line in failed90.splitlines() if line.startswith(' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver"'))
    new_cli=''' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver","Use --receiver failed34_as07 psi0 DATA PRE COMPLETE91PLAN PROFILE17_CSV FRESHOUT");const std::string profile=std::filesystem::path(argv[2]).string(),group=std::filesystem::path(argv[3]).string();H18Need(profile=="failed34_as07"&&group=="psi0","Only the actual failed AS.7 psi0 saved prefix is supported");H18ReadPlan(argv[6],false,H18WindowEnd,H18WindowSamples);H18ReadReceiverProfile(argv[7],group);H18Need(H18Rows.size()==91&&H18Rows.back().completed==2180000&&H18Bits(H18AS,.7f)&&H18Bits(H18Exp,3.825f),"Original91 plan/AS.7/n3.825 scope differs");const unsigned samples=34,end=H18Rows[33].completed;H18Need(end==2066001,"Actual last saved-prefix step differs");const std::filesystem::path data=argv[4],out=argv[8];H18Need(std::filesystem::is_directory(data)&&!std::filesystem::exists(out),"Missing DATA or protected output");'''
    changes=[(old_cli,new_cli),
      ('// No source/full/formal interface in the failed90 adapter.','// No source/full/formal interface in the failed34_as07 adapter.'),
      ('c08_h18_wend_partial_native_r1.metadata','c08_h18_wend_partial_native_r2.metadata')]
    return prior.patch(failed90,changes),failed90,baseline_changes,changes

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Root must fully read these files before one explicit utility build')
    check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing complete or partial forensic build is protected');before=[];calls=[]
    try:
        baseline,partial=read(BASE),read(PARTIAL)
        need(baseline['passed'] and baseline['consumed_stats_unchanged'] and baseline['declared_Kernel_XML_CSV']==2 and baseline['receiver_material_CSV_keys']==17 and baseline['actual_link_objects']==7 and not baseline['JSph_objects_linked'],'Passed original full Wendland utility required')
        need(partial['passed'] and partial['consumed_stats_unchanged'] and partial['baseline_build']==stat(BASE) and partial['observed_prefix_records']==90 and partial['actual_link_objects']==7 and not partial['JSph_objects_linked'],'Passed unchanged failed90 derivation witness required')
        objects=[bind(entry) for entry in baseline['objects']];need(objects==partial['objects'] and len(objects)==6 and {Path(v['path']).stem for v in objects}=={'JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions'},'Exactly the same six original BI4 utility objects required')
        originals={Path(v['path']).name:bind(v) for v in baseline['generated']};witness={Path(v['path']).name:bind(v) for v in partial['generated']}
        leaves=('h18_wend_entry_r1.cpp','h18_headers_r1.h','h18_receiver_core_r1.cpp','h18_profiles_r1.h');need(all(v in originals for v in leaves),'Original passed generated closure differs')
        need(all(v in witness for v in ('h18_wend_partial_entry_r1.cpp','h18_receiver_core_r1.cpp')),'Failed90 generated witness differs')
        source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');headers=Path(bind(baseline['program'])['path']).parent/'headers'
        before=[stat(v) for v in (Path(__file__),Path(r1.__file__),Path(prior.__file__),Path(e.__file__),BASE,PARTIAL,source,note)]+[originals[v] for v in leaves]+list(witness.values())+objects
        before += [bind(baseline[v]) for v in ('program','source','core_derivation','source_archive','physical_source_archive')]+[bind(partial[v]) for v in ('program','source','note','core_derivation')]
        before += [stat(headers/v) for v in ('JGravityPreloadState.h','FunSoilMaterial.h','JPartDataBi4.h','JPartDataHead.h','JBinaryData.h','TypesDef.h')]
        raw_entry=Path(originals['h18_wend_entry_r1.cpp']['path']).read_text(encoding='utf-8');raw_receiver=Path(originals['h18_receiver_core_r1.cpp']['path']).read_text(encoding='utf-8')
        entry,entry90,ec0,ec=derive_entry(raw_entry);receiver,receiver90,rc0,rc=derive_receiver(raw_receiver)
        need(entry90==Path(witness['h18_wend_partial_entry_r1.cpp']['path']).read_text(encoding='utf-8') and receiver90==Path(witness['h18_receiver_core_r1.cpp']['path']).read_text(encoding='utf-8'),'Replayed full-to-failed90 derivation is not exactly the sealed original artifact')
        OUT.mkdir();generated={OUT/'h18_wend_partial_entry_r2.cpp':entry,OUT/'h18_receiver_core_r1.cpp':receiver,OUT/'h18_headers_r1.h':Path(originals['h18_headers_r1.h']['path']).read_text(encoding='utf-8'),OUT/'h18_profiles_r1.h':Path(originals['h18_profiles_r1.h']['path']).read_text(encoding='utf-8')}
        for dest,text in generated.items():dest.write_text(text,encoding='utf-8',newline='\n')
        diffs=[]
        for label,old,new in [('entry',entry90,entry),('receiver',receiver90,receiver)]:
            dest=OUT/(label+'_core.diff');dest.write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='sealed_failed90/'+label,tofile='failed34_as07/'+label,n=4)),encoding='utf-8');diffs.append(stat(dest))
        proof=OUT/'core_derivation.json';save(proof,dict(stage=TAG+'.derive',baseline_build=stat(BASE),failed90_build=stat(PARTIAL),baseline_generated=[originals[v] for v in leaves],failed90_witness=list(witness.values()),replayed_failed90_matches_sealed_generated_exact=True,full_to_failed90_entry_replacements=ec0,full_to_failed90_receiver_replacements=rc0,failed90_to_failed34_entry_replacements=ec,failed90_to_failed34_receiver_replacements=rc,reverse_declared_replacements_exact_at_both_levels=True,original_field_and_numerical_guards_changed=False,original_plan_retained_in_memory_and_on_disk=True,original_plan_records=91,observed_prefix_records=34,last_saved_part=33,last_saved_completed_step=2066001,original_target_completed_step=2180000,actual_terminal_solver_step_proven=False,unsaved_state_reconstructed=False,whole_run_native_passed=False,full_run_completed=False,source_PRE_array_reads_per_future_decode=1,old_files_changed=False))
        before += [stat(v) for v in generated]+diffs+[stat(proof)]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed')
        env=dict(os.environ);env.update(line.split('=',1) for line in setup.stdout.decode('mbcs').splitlines() if '=' in line and not line.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching utility MSVC14.36 required')
        cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08H18WendPartialNativeR2_win64.exe'
        compile_args=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)]
        link_args=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[v['path'] for v in objects]]
        calls.append(invoke(TAG+'.compile',compile_args,OUT,env));calls.append(invoke(TAG+'.link',link_args,OUT,env));need(all(stat(v['path'])==v for v in before),'Frozen baseline/witness/source/objects changed during build')
        save(check,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(source),note=stat(note),baseline_build=stat(BASE),failed90_build=stat(PARTIAL),objects=objects,actual_link_objects=7,JSph_objects_linked=False,generated=[stat(v) for v in generated],core_derivation=stat(proof),core_diffs=diffs,calls=calls,consumed=before,consumed_stats_unchanged=True,forensic_receiver_only=True,explicit_profile='failed34_as07',declared_Kernel_XML_CSV=2,receiver_material_CSV_keys=17,AS_coefficient=.7,AS_exponent=3.825,observed_prefix_records=34,original_plan_records=91,last_saved_completed_step=2066001,original_target_completed_step=2180000,original_field_and_numerical_guards_changed=False,decoder_invocations=0,solver_invocations=0,SHA_scans=0))
    except Exception as error:
        if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,SHA_scans=0))
        raise

if __name__=='__main__':main()
