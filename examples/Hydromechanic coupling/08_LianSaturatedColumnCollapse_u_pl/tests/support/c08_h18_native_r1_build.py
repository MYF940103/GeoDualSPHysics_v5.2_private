"""Author-reviewed shared H1.8 utility build only; six sealed BI4 objects, no solver/decode."""
import argparse,os,subprocess,difflib
from pathlib import Path
from zipfile import ZipFile
import mdbc_partition_components_r3 as e
import upl_c08_bedkeep_native_r1_build as keep
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='c08_h18_native_r1';OUT=T/'outputs'/(TAG+'_build')
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke

def patch(raw,changes):
 out=raw
 for before,after in changes:need(out.count(before)==1,'Closed derivation anchor differs: '+before[:100]);out=out.replace(before,after,1)
 inverse=out
 for before,after in reversed(changes):need(inverse.count(after)==1,'Reverse derivation anchor differs');inverse=inverse.replace(after,before,1)
 need(inverse==raw,'Core changed beyond the declared profile/scope/interface edits');return out

def derive_source(raw):
 absent='  for(const char* key:{"GravityPreloadHandoffSchema","GravityPreloadElasticSource","GravityPreloadHandoffContract","GravityPreloadSourceCohesion","GravityPreloadActualTime","GravityPreloadActualCompletedStep","GravityPreloadStateFile","GravityPreloadKeepBedOverlap","DynamicArtificialStressPolicy","DynamicArtificialStressActive","DynamicNoPenetrationPolicy","DynamicNoPenetrationActive","FreeSeepagePondingPolicy","FreeSeepagePondingActive"})Need(!p->ExistsValue(key),"Short PRE unexpectedly has certification/release/import/AS/NoPen metadata");'
 certificate='''  for(const char* key:{"GravityPreloadActualTime","GravityPreloadActualCompletedStep","GravityPreloadStateFile","GravityPreloadKeepBedOverlap","DynamicArtificialStressPolicy","DynamicArtificialStressActive","DynamicNoPenetrationPolicy","DynamicNoPenetrationActive","FreeSeepagePondingPolicy","FreeSeepagePondingActive"})Need(!p->ExistsValue(key),"Source PRE unexpectedly released/imported or enabled AS/NoPen");
  if(event)Need(p->ExistsValue("GravityPreloadHandoffSchema",DatUint)&&p->GetvUint("GravityPreloadHandoffSchema")==1&&p->ExistsValue("GravityPreloadElasticSource",DatBool)&&p->GetvBool("GravityPreloadElasticSource")&&p->ExistsValue("GravityPreloadHandoffContract",JBinaryDataDef::DatText)&&!p->GetvText("GravityPreloadHandoffContract").empty()&&p->ExistsValue("GravityPreloadSourceCohesion",DatFloat)&&Bits(p->GetvFloat("GravityPreloadSourceCohesion"),5000.f),"Final source certificate/header/cohesion differs");
  else for(const char* key:{"GravityPreloadHandoffSchema","GravityPreloadElasticSource","GravityPreloadHandoffContract","GravityPreloadSourceCohesion"})Need(!p->ExistsValue(key),"Non-event frame unexpectedly certified");'''
 old_cli='using namespace prediag;Need(argc==6&&std::wstring(argv[1])==L"--read","Use --read h15_failed|h12_control DATA MATERIAL_CSV FRESHOUT");const std::string profile=fs::path(argv[2]).string();const bool h15=profile=="h15_failed";Need(h15||profile=="h12_control","Only two explicit PRE diagnostic profiles");const double H=double(float(h15?.06:.048));const fs::path data=argv[3],params=argv[4],out=argv[5];'
 new_cli='using namespace prediag;Need(argc==7&&std::wstring(argv[1])==L"--source","Use --source partial|full DATA MATERIAL_CSV PLAN FRESHOUT");const std::string profile=fs::path(argv[2]).string();const bool full=profile=="full";Need(full||profile=="partial","Explicit source partial/full mode required");const double H=double(.072f);const fs::path data=argv[3],params=argv[4],out=argv[6];'
 changes=[
  ('Soil=5000,Event=4000000','Soil=5000,Event=2000000'),('constexpr double Dt=.0000025','constexpr double Dt=.000005'),
  ('Outside the two fixed actual source-material profiles','Outside the fixed actual H1.8 elastic-source material profile'),
  ('static void Metadata(JPartDataBi4& f){','static void Metadata(JPartDataBi4& f,bool event){'),(absent,certificate),(old_cli,new_cli),
  ('Need(h15?samples==52:(samples>=1&&samples<=53),"Actual partial source frame count differs")','Need(full?samples==H18Rows.size():(samples>=1&&samples<=H18Rows.size()),"Actual source count differs from its original complete plan")'),
  ('Need((!part?step==0&&time==0.:completed>previous)&&completed< Event&&completed<=(h15?204000u:208000u),"Actual initial/noninitial saved Step differs")','Need(part<H18Rows.size()&&step==H18Rows[part].saved&&completed==H18Rows[part].completed&&std::abs(time-H18Rows[part].time)<=1e-14&&completed<=Event,"Actual initial/noninitial Step/time differs from the original complete plan")'),
  ('Metadata(f);','Metadata(f,completed==Event);'),
  ('const bool snapshot=part==0||part==25||part==50||part==51;','const bool snapshot=part==0||part==100||part==500||part+1==samples;'),
  ('Original P0/excess/kappa0/2D/finite physical domain differs");p0Checks++;','Original P0/excess/kappa0/2D/finite physical domain differs");if(full&&part+1==samples)Need(a.rhop[q]>=700.f&&a.rhop[q]<=3000.f,"Final certified PRE density admission differs");p0Checks++;'),
  ('raw.write(reinterpret_cast<const char*>(&time),8);Typed22(raw,a);','if(full&&part+1==samples)Need(band[6].count>0&&band[6].positive==0,"Final certificate must satisfy the existing handoff free-seepage mask/pressure guard");raw.write(reinterpret_cast<const char*>(&time),8);Typed22(raw,a);'),
  ('Need(!h15||previous==204000,"h15 last saved global completed Step differs")','Need(!full||(samples==1001&&previous==Event),"Full source event/count incomplete")'),
  ('upl_c08_hdp15_preload_partial_r3','c08_h18_native_r1.source'),
  (r'\"partial\":true,\"uncertified\":true,\"certified_PRE\":false',r'\"partial\":"<<(full?"false":"true")<<",\"uncertified\":"<<(full?"false":"true")<<",\"certified_PRE\":"<<(full?"true":"false")<<"'),
  (r'\"physical_acceptance\":false,\"native_rewritten\":false',r'\"source_program_and_XML_binding_required\":true,\"certificate_is_native_header_and_arrays_not_equilibrium\":true,\"source_equilibrium_claimed\":false,\"source_plan_not_truncated\":true,\"physical_acceptance\":false,\"native_rewritten\":false')
 ]
 return patch(raw,changes),changes

RUNCSV=r'''static unsigned RunSamples(const fs::path& path,unsigned expected){
  std::ifstream f(path);std::string h,d,extra;Need(bool(std::getline(f,h))&&bool(std::getline(f,d))&&!std::getline(f,extra),"Closed completed two-line Run.csv required");const char sep=h.find(';')==std::string::npos?',':';';const auto keys=Split(h,sep);auto values=Split(d,sep);const auto ci=std::find(keys.begin(),keys.end(),"Configuration");Need(ci!=keys.end(),"Run.csv Configuration missing");const unsigned at=unsigned(ci-keys.begin());
  if(values.size()==keys.size()+1){Need(sep==';'&&at+1<values.size(),"Only one embedded AS separator is recognized");values[at]+=';'+values[at+1];values.erase(values.begin()+at+1);}Need(values.size()==keys.size(),"Run.csv width differs");const std::string marker="AS_Bui2008(";const auto start=values[at].find(marker),split=values[at].find(';',start),close=values[at].find(')',split);Need(start!=std::string::npos&&values[at].find(marker,start+1)==std::string::npos&&split!=std::string::npos&&close!=std::string::npos,"Actual AS Configuration token missing");Need(H18Bits(float(H18Double(values[at].substr(start+marker.size(),split-start-marker.size()))),H18AS)&&H18Bits(float(H18Double(values[at].substr(split+1,close-split-1))),H18Exp),"Actual AS Run.csv coefficient/exponent differs");
  std::map<std::string,std::string> r;for(unsigned q=0;q<keys.size();q++)Need(r.emplace(keys[q],values[q]).second,"Duplicate Run.csv key");
  Need(std::stoul(r.at("Steps"))==expected&&r.at("Np")=="7060"&&r.at("Nbound")=="2060"&&r.at("Nfixed")=="2060"&&r.at("PartsOut")=="0"&&r.at("PartsOutRhop")=="0"&&r.at("PartsOutVel")=="0","Actual global steps/original registry/no-exclusion summary differs");const auto n=std::stoul(r.at("PartFiles"));Need(n>0&&n<=expected-EventStep,"Invalid actual PartFiles count");return unsigned(n);
}'''
PLAN=r'''static std::vector<unsigned> Planned(const fs::path& path,unsigned samples,unsigned expected){
  Need(fs::equivalent(path,H18PlanPath)&&H18Rows.size()==samples&&H18Rows.back().completed==expected,"Original supplied complete plan identity differs");std::vector<unsigned> steps;for(const auto& q:H18Rows)steps.push_back(q.completed);return steps;
}'''

def derive_receiver(raw):
 base=keep.derive_core(raw);start=base.index('static unsigned RunSamples(');stop=base.index('static unsigned Number(',start);old_run=base[start:stop].rstrip()
 a=base.index('static std::vector<unsigned> Planned(');b=base.index('int wmain(',a);old_plan=base[a:b].rstrip()
 changes=[(old_run,RUNCSV),(old_plan,PLAN),('EventStep=4000000','EventStep=2000000'),('Dt=.0000025','Dt=.000005'),('H=double(float(.048))','H=double(float(.072))'),
  ('Need(group=="psi0","Only the bounded psi0 material is admitted");const float targetCoh=5000.f,sf=0.f;','Need(group=="psi0"||group=="psi2p5"||group=="psim5","Only the three closed C08 groups are admitted");const float targetCoh=H18TargetCoh,sf=H18Decay;'),
  ('const unsigned saved=f.Get_Step(),completed=saved+1,n=f.Get_Npok();const double time=f.Get_TimeStep();','const unsigned saved=f.Get_Step(),completed=saved+1,n=f.Get_Npok();const double time=f.Get_TimeStep();Need(part<H18Rows.size()&&saved==H18Rows[part].saved&&std::abs(time-H18Rows[part].time)<=1e-14,"Actual record differs from complete scalar-time plan");'),
  ('const auto* meta=pf.GetPart();','Need(pf.Get_H()==H&&pf.Get_Dp()==Dp,"Source H/dp must match the H1.8 receiver");const auto* meta=pf.GetPart();'),
  ('(certified.MaterialLawVersion==1||certified.MaterialLawVersion==2)','(certified.MaterialLawVersion==2)'),
  ('upl_c08_bedkeep_native_r1','c08_h18_native_r1.receiver'),(r'\"source_completed_step\":4000000',r'\"source_completed_step\":2000000'),
  (r'\"typed_arrays\":22',r'\"H\":"<<H<<",\"fixed_dt_s\":"<<Dt<<",\"actual_plan_columns\":5,\"first_saved_step_from_actual_plan\":"<<H18Rows.front().saved<<",\"typed_arrays\":22')]
 return patch(base,changes),changes

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profiles',type=Path,required=True);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized,'Root full-read before one utility build');check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing/partial utility build protected');before=[];calls=[]
 try:
  profiles=read(args.profiles);need(profiles['kernel']=='Cubic' and profiles['hdp']==1.8 and profiles['Dp']==.04 and profiles['fixed_dt_s']==.000005 and profiles['preload_completed_step']==2000000 and profiles['preload_samples']==1001 and profiles['preload_damping_coefficient']==.03,'Prepared H1.8 source profile differs');recv=profiles['receiver'];need(len(recv)==2 and [q['end_completed_step'] for q in recv]==[2180000,2600000] and [q['samples'] for q in recv]==[91,301],'Use the actual replayed 91/301 plans including first-post5us')
  bp=L/'mdbc_partition_ReleaseCPU_r1.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'],'Passed closed utility build required');objects=[q for q in b['project_objects'] if Path(q['path']).stem in ('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')];need(len(objects)==6,'Exactly six sealed BI4 utility objects');capture=read(bind(b['source_capture'])['path']);archive=Path(bind(capture['archive'])['path']);physical_build=L/'upl_c08_bedkeep_Release_r1.build.json';pb=read(physical_build);need(pb['passed'],'Original runtime_r6 source build required');physical_archive=Path(bind(pb['source_archive'])['path'])
  source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');source_base=T/'support/upl_c08_hdp15_preload_partial_r3.cpp';receiver_base=T/'support/upl_c08_plane_native_r1.cpp';neutral=T.parent.parent/'02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp';before=[stat(q) for q in (Path(__file__),Path(e.__file__),Path(keep.__file__),Path(keep.csvfix.__file__),source,note,source_base,receiver_base,neutral,args.profiles,bp,physical_build)]+[bind(b['source_capture']),stat(archive),stat(physical_archive),*[bind(q) for q in objects]]+[stat(Path(q)) for q in [profiles['preload_plan']]+[x['plan'] for x in recv]]
  OUT.mkdir();headers=OUT/'headers';headers.mkdir()
  with ZipFile(archive) as z:
   for item in z.infolist():
    if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
     dest=headers/Path(item.filename).name;need(not dest.exists(),'Duplicate archived header leaf');dest.write_bytes(z.read(item))
  with ZipFile(physical_archive) as z:
   for leaf in ('JPartDataBi4.h','JPartDataHead.h','JBinaryData.h','TypesDef.h'):need((headers/leaf).read_bytes()==z.read('src/source/'+leaf),'Physical/utility ABI header differs: '+leaf)
   for leaf in ('JGravityPreloadState.h','FunSoilMaterial.h'):(headers/leaf).write_bytes(z.read('src/source/'+leaf))
  raw=neutral.read_text(encoding='utf-8-sig');pure=raw[:raw.index('static constexpr double A=')]+raw[raw.index('static void Need('):raw.index('using Row=')];unused=['#include "JAppInfo.h"\n','JAppInfo AppInfo("PublicDynamicCpuNative","r1","01-11-2026");\n']
  for value in unused:need(pure.count(value)==1,'Exact unused AppInfo declaration required');pure=pure.replace(value,'',1)
  source_raw=source_base.read_text(encoding='utf-8');receiver_raw=receiver_base.read_text(encoding='utf-8');source_core,source_changes=derive_source(source_raw);receiver_core,receiver_changes=derive_receiver(receiver_raw);includes=[]
  for text in (pure,source_core,receiver_core):
   for line in text.splitlines():
    if line.startswith('#include ') and '"public22_core_r1.h"' not in line and line not in includes:includes.append(line)
  def lift(text,keep_pure=False):return '\n'.join(line for line in text.splitlines() if not line.startswith('#include ') or (keep_pure and '"public22_core_r1.h"' in line))+'\n'
  generated={OUT/'h18_headers_r1.h':'\n'.join(includes)+'\n',OUT/'public22_core_r1.h':lift(pure),OUT/'h18_source_core_r1.cpp':lift(source_core,True),OUT/'h18_receiver_core_r1.cpp':lift(receiver_core),OUT/'h18_profiles_r1.h':'static constexpr unsigned H18Event=2000000,H18SourceSamples=1001,H18WindowEnd=2180000,H18WindowSamples=91,H18FormalEnd=2600000,H18FormalSamples=301;\nstatic constexpr double H18Dt=.000005;\n'}
  for path,text in generated.items():path.write_text(text,encoding='utf-8',newline='\n')
  diffs=[]
  for name,old,new in [('source',source_raw,source_core),('receiver',keep.derive_core(receiver_raw),receiver_core)]:
   path=OUT/(name+'_core.diff');path.write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='sealed/'+name,tofile='generated/'+name,n=3)),encoding='utf-8');diffs.append(stat(path))
  derivation=OUT/'core_derivation.json';save(derivation,dict(source_baseline=stat(source_base),receiver_baseline=stat(receiver_base),generated=[stat(q) for q in generated],diffs=diffs,source_declared_replacements=source_changes,receiver_declared_replacements=receiver_changes,reverse_declared_replacements_exact=True,headers_lifted_before_separate_namespaces=True,pure22_loader_body_unchanged=True,original_numerical_tolerances_changed=False,source_event=2000000,source_count=1001,receiver_counts=[91,301],actual_five_column_plans=True,first_post_saved_step=2000000,first_post_completed_step=2000001,old_files_changed=False));before += [stat(q) for q in generated]+diffs+[stat(derivation),stat(headers/'FunSoilMaterial.h'),stat(headers/'JGravityPreloadState.h')]
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required');cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08H18Native_win64.exe';ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)];la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[q['path'] for q in objects]];calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(q['path'])==q for q in before),'Closed source/object/profile changed')
  save(check,dict(stage=TAG+'.build',passed=True,program=stat(exe),source=stat(source),profiles=stat(args.profiles),source_build=stat(bp),source_capture=b['source_capture'],source_archive=stat(archive),physical_source_build=stat(physical_build),physical_source_archive=stat(physical_archive),generated=[stat(q) for q in generated],core_derivation=stat(derivation),objects=objects,actual_link_objects=7,JSph_objects_linked=False,calls=calls,consumed=before,consumed_stats_unchanged=True,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0))
 except Exception as error:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,SHA_scans=0))
  raise
if __name__=='__main__':main()
