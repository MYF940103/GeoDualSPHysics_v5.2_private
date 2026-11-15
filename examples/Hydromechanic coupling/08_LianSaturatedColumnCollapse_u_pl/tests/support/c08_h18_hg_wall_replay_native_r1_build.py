"""Build only a two-profile observer-replay native utility; never decode or solve."""
import argparse
import difflib
import os
import subprocess
from pathlib import Path
from zipfile import ZipFile
import c08_h18_as255_native_r1_build as old

T,L=old.T,old.L
TAG='c08_h18_hg_wall_replay_native_r1'
SCRIPT=Path(__file__).resolve()
SOURCE,NOTE=T/'support'/(TAG+'.cpp'),T/'notes'/(TAG+'.md')
BASE,OUT=L/'c08_h18_as255_native_r1.build.json',T/'outputs'/(TAG+'_build')
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke
OBSERVED=r'''static unsigned ObservedPartialSamples(const fs::path& runCsv,unsigned expected){
  Need(H18PartialObserver&&H18Rows.size()==100&&H18Rows.back().completed==2196680&&expected==2196001&&H18Rows[98].completed==expected,"Only actual99-of100 observer failure is supported");
  Need(!fs::exists(runCsv),"Failed observer replay must not have a normal-completion Run.csv");
  const fs::path data=runCsv.parent_path()/"data";unsigned count=0;
  for(const auto& p:fs::directory_iterator(data))if(p.is_regular_file()&&p.path().extension()==".bi4"&&p.path().filename().string().rfind("Part_",0)==0)count++;
  Need(count==99,"Actual failed observer saved-file count differs");
  std::ifstream f(runCsv.parent_path()/"Run.out");Need(bool(f),"Actual failed Run.out missing");std::ostringstream text;text<<f.rdbuf();
  Need(text.str().find("GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.")!=std::string::npos&&text.str().find("Finished execution (code=1).")!=std::string::npos&&text.str().find("DynamicPoreWall rejected: stage=1 sorted_slot=690 native_id=894 step_start=10.983389999668779 step=2196678 B=(4.9000000000000004,0,-0.019999999999999962) normal=(0,0,0.0399999991).")!=std::string::npos,"Exact reported observer wall894 failure/exit text differs");
  // Actual owner/Win32 exit and stdout trace are checked separately by root.
  return count;
}'''
PLAN=r'''static std::vector<unsigned> Planned(const fs::path& path,unsigned samples,unsigned expected){
  Need(fs::equivalent(path,H18PlanPath)&&H18Rows.size()==100&&H18Rows.back().completed==2196680&&(H18PartialObserver?(samples==99&&expected==2196001&&H18Rows[98].completed==expected):(samples==100&&expected==2196680)),"Untouched100 replay plan and exact selected scope required");
  std::vector<unsigned> steps;for(unsigned part=0;part<samples;part++)steps.push_back(H18Rows[part].completed);return steps;
}'''


def reversible(raw,changes):
    current=raw
    for label,before,after in changes:
        a,b=before.encode(),after.encode();need(current.count(a)==1,'Unique original anchor: '+label);current=current.replace(a,b,1)
    inverse=current
    for label,before,after in reversed(changes):
        a,b=before.encode(),after.encode();need(inverse.count(b)==1,'Unique inverse anchor: '+label);inverse=inverse.replace(b,a,1)
    need(inverse==raw,'Declared inverse must restore every original byte');return current


def derive(entry,receiver):
    e,r=entry.decode(),receiver.decode()
    source_cli=e[e.index(' if(argc==7&&std::wstring(argv[1])==L"--source"){'):e.index(' H18Need(argc==9')]
    old_cli=next(q for q in e.splitlines() if q.startswith(' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver"'))
    new_cli=' H18Need(argc==9&&std::wstring(argv[1])==L"--receiver","Use --receiver failed99_obs|cap100 psi0 DATA PRE COMPLETE100PLAN PROFILE17_CSV FRESHOUT");const std::string profile=std::filesystem::path(argv[2]).string(),group=std::filesystem::path(argv[3]).string();H18Need((profile=="failed99_obs"||profile=="cap100")&&group=="psi0","Only the two explicit psi0 observer scopes are exposed");H18PartialObserver=profile=="failed99_obs";H18ReadPlan(argv[6],false,2196680u,100u);H18ReadReceiverProfile(argv[7],group);H18Need(H18Bits(H18AS,.3f)&&H18Bits(H18Exp,2.55f),"Exact AS.3/n2.55 profile required");for(unsigned part=0;part<99u;part++)H18Need(H18Rows[part].completed==2000001u+2000u*part,"Actual first99 observer saves differ");const unsigned samples=H18PartialObserver?99u:100u,end=H18Rows[samples-1u].completed;H18Need(end==(H18PartialObserver?2196001u:2196680u),"Actual last selected saved step differs");const std::filesystem::path data=argv[4],out=argv[8];H18Need(std::filesystem::is_directory(data)&&!std::filesystem::exists(out),"Missing DATA or protected output");'
    scope=r'\"diagnostic_complete\":true,\"partial\":"<<(H18PartialObserver?"true":"false")<<",\"saved_prefix_native_passed\":"<<(H18PartialObserver?"true":"false")<<",\"replay_cap_native_passed\":"<<(H18PartialObserver?"false":"true")<<",\"full_run_completed\":false,\"base_case_full3_completed\":false,\"whole_run_passed\":false,\"whole_run_native_passed\":false,\"original_target_completed_step\":2196680,\"original_target_samples\":100,\"base_case_target_completed_step\":2600000,\"base_case_target_samples\":301,\"observed_saved_samples\":"<<(H18PartialObserver?99:100)<<",\"last_saved_part\":"<<(H18PartialObserver?98:99)<<",\"last_saved_completed_step\":"<<H18Rows[H18PartialObserver?98:99].completed<<",\"original_plan_records\":100,\"observed_plan_prefix_records\":"<<(H18PartialObserver?99:100)<<",\"plan_modified\":false,\"unsaved_state_reconstructed\":false,'
    ec=[('one closed partial flag','static std::string H18Group;','static std::string H18Group;\nstatic bool H18PartialObserver=false;'),
        ('close source CLI',source_cli,' // No source/formal/window CLI in this capped observer adapter.\n'),
        ('two closed receiver scopes',old_cli,new_cli),
        ('scoped metadata',r'\"stage\":\"c08_h18_wend_native_r1.metadata\",\"passed\":true,',r'\"stage\":\"c08_h18_hg_wall_replay_native_r1.metadata\",\"passed\":true,'+scope)]
    a=r.index('static std::vector<unsigned> Planned(');old_plan=r[a:r.index('int wmain(',a)].rstrip()
    rc=[('add separate failed observer', 'static unsigned Number(',OBSERVED+'\nstatic unsigned Number('),
        ('closed100 plan',old_plan,PLAN),
        ('conditional runtime observation','Need(RunSamples(data.parent_path()/"Run.csv",expected)==samples,"Normal Run.csv end/count differs from the explicit owner plan");','Need((H18PartialObserver?ObservedPartialSamples(data.parent_path()/"Run.csv",expected):RunSamples(data.parent_path()/"Run.csv",expected))==samples,"Selected observer runtime end/count differs");'),
        ('saved-scope message','Actual final global step/full native coverage incomplete','Actual selected observer last saved step/native coverage incomplete'),
        ('scoped conditional completion',r'\"stage\":\"c08_h18_wend_native_r1.receiver\",\"passed\":true,',r'\"stage\":\"c08_h18_hg_wall_replay_native_r1.receiver\",\"passed\":"<<(H18PartialObserver?"false":"true")<<",'+scope),
        ('conditional completed-runtime label',r'\"completed_runtime_Run_csv_checked\":true',r'\"completed_runtime_Run_csv_checked\":"<<(H18PartialObserver?"false":"true")<<",\"actual_failed_Runout_text_checked\":"<<(H18PartialObserver?"true":"false")<<",\"actual_owner_Win32_binding_required\":true')]
    ne,nr=reversible(entry,ec),reversible(receiver,rc);text=nr.decode()
    begin,end='  for(unsigned part=0;part<samples;part++){','  Need(previous==expected'
    need(r.count(begin)==text.count(begin)==1,'One original22 loop required')
    need(text[text.index(begin):text.index(end)].encode()==r[r.index(begin):r.index(end)].encode(),'Original22 validation loop changed')
    original_run=r[r.index('static unsigned RunSamples('):r.index('static unsigned Number(')].encode()
    need(text[text.index('static unsigned RunSamples('):text.index('static unsigned ObservedPartialSamples(')].encode()==original_run,'Normal RunSamples bytes changed')
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
        need(SOURCE.read_bytes().count(b'#include "h18_hg_wall_replay_entry_r1.cpp"')==1,'One private entry include required')
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
            dest=OUT/('h18_hg_wall_replay_entry_r1.cpp' if leaf=='h18_as255_entry_r1.cpp' else leaf); dest.write_bytes(payload); need(dest.read_bytes()==payload,'Actual derived source copy differs'); generated.append(stat(dest))
        diffs=[]
        for label,a,z in (('entry',raw,revised),('receiver',rr,revised_receiver)):
            dest=OUT/(label+'_core.diff'); dest.write_text(''.join(difflib.unified_diff(a.decode().splitlines(True),z.decode().splitlines(True),fromfile='sealed_AS255/'+label,tofile='wall_replay/'+label)),encoding='utf-8'); diffs.append(stat(dest))
        proof=OUT/'core_derivation.json'
        save(proof,dict(stage=TAG+'.derive',baseline_build=stat(BASE),baseline_generated=list(originals.values()),entry_declared_replacements=ec,receiver_declared_replacements=rc,exact_inverse_original_entry_bytes=True,exact_inverse_original_receiver_bytes=True,source_numeric_core_byte_identical=True,original_field_validation_loop_bytes_identical=True,original_normal_RunSamples_bytes_identical=True,single_receiver_core=True,original_field_and_numerical_guards_changed=False,profiles=['failed99_obs','cap100'],allowed_group='psi0',original_plan_records=100,failed_saved_prefix_records=99,cap_samples=100,cap_completed_step=2196680,failed_last_saved_part=98,failed_last_saved_completed_step=2196001,original_target_completed_step=2196680,original_target_samples=100,base_case_target_completed_step=2600000,base_case_target_samples=301,whole_run_native_passed=False,full_run_completed=False,unsaved_state_reconstructed=False,actual_terminal_solver_step_proven=False,old_files_changed=False))
        before += generated+diffs+[stat(proof)]+[stat(q) for q in headers.iterdir()]
        setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        need(setup.returncode==0,'Original MSVC setup failed'); env={k.upper():v for k,v in os.environ.items()}; env.update((k.upper(),v) for k,v in (q.split('=',1) for q in setup.stdout.decode('mbcs').splitlines() if '=' in q and not q.startswith('=')))
        need(env['VCTOOLSVERSION']=='14.36.32532','Same MSVC14.36 required')
        for k in ('CL','_CL_'):env.pop(k,None)
        oldout=Path(b['program']['path']).parent; obj=OUT/'reader.obj'; exe=OUT/'C08H18HgWallReplayNativeR1_win64.exe'
        ca=[str(SOURCE) if q==b['source']['path'] else q.replace(str(oldout),str(OUT)) for q in cc['arguments']]
        la=[q.replace(b['program']['path'],str(exe)).replace(str(oldout),str(OUT)) for q in lc['arguments']]
        linked=[Path(q).resolve() for q in la if q.lower().endswith('.obj')]
        need(all(q in ca for q in ('/std:c++17','/D_HAS_STD_BYTE=0','/fp:precise','/O2','/MT','/GL-')) and ca.count(str(SOURCE))==1 and '/Fo'+str(obj) in ca and '/I'+str(headers) in ca,'Original utility precise/static ABI recipe required')
        need(len(linked)==len(set(linked))==7 and set(linked)=={Path(q['path']).resolve() for q in objects}|{obj.resolve()},'Link only six original utility objects and one new entry')
        tools=[Path(q['program']) for q in (cc,lc)]; need(all('/14.36.32532/' in q.as_posix() for q in tools),'Original MSVC tool paths required'); before += [stat(q) for q in tools]
        need(all(stat(q['path'])==q for q in before),'A consumed input changed before build')
        calls.append(invoke(TAG+'.compile',[cc['program'],*ca],OUT,env)); calls.append(invoke(TAG+'.link',[lc['program'],*la],OUT,env))
        need(all(stat(q['path'])==q for q in before),'A consumed input changed during build')
        save(check,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(SOURCE),note=stat(NOTE),baseline_build=stat(BASE),objects=objects,generated=generated,core_derivation=stat(proof),core_diffs=diffs,calls=calls,consumed=before,consumed_stats_unchanged=True,actual_link_objects=7,retained_reader_objects=6,new_entry_objects=1,JSph_objects_linked=False,source_numeric_core_byte_identical=True,original_field_validation_loop_bytes_identical=True,original_normal_RunSamples_bytes_identical=True,single_receiver_core=True,original_field_and_numerical_guards_changed=False,forensic_receiver_only=True,profiles=['failed99_obs','cap100'],allowed_group='psi0',original_plan_records=100,failed_saved_prefix_records=99,cap_samples=100,cap_completed_step=2196680,failed_last_saved_part=98,failed_last_saved_completed_step=2196001,failed_last_saved_zero_based_step=2196000,original_target_completed_step=2196680,original_target_samples=100,base_case_target_completed_step=2600000,base_case_target_samples=301,fixed_dt_s=.000005,source_material_CSV_keys=15,receiver_material_CSV_keys=17,typed_arrays=22,active_IDs=6805,declared_Kernel_XML_CSV=2,AS_coefficient=.3,AS_exponent=2.55,source_CLI_exposed=False,formal_CLI_exposed=False,whole_run_passed=False,whole_run_native_passed=False,full_run_completed=False,HG_proven_by_reader=False,unsaved_state_reconstructed=False,actual_terminal_solver_step_proven=False,runtime_files=[],runtime_recipe='same original /MT and seven-object closure; no added private DLL',native_decodes=0,solver_invocations=0,automatic_next_job=False,physical_acceptance=False,SHA_scans=0))
    except Exception as error:
        actual=[stat(L/(TAG+s)) for s in ('.compile.call.json','.link.call.json') if (L/(TAG+s)).is_file()]
        if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=actual,consumed=before,partial_outputs_preserved=True,native_decodes=0,solver_invocations=0,physical_acceptance=False))
        raise


if __name__=='__main__':main()
