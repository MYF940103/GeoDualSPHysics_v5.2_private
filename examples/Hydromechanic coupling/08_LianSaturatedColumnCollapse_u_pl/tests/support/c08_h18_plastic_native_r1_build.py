"""Build only the separate H1.8 same-material plastic PRE/receiver inspector."""
import argparse,os,subprocess,difflib
from pathlib import Path
from zipfile import ZipFile
import c08_h18_bedroles_native_r1_build as base

e,keep=base.e,base.keep
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='c08_h18_plastic_native_r1';OUT=T/'outputs'/(TAG+'_build')
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke
patch=base.patch

def derive_source(raw):
 previous,original=base.derive_source(raw)
 changes=[
  ('const std::set<std::string> keys={"DPCtes",','const std::set<std::string> keys={"group","ModulusE","PRvs","DPCtes",'),
  ('degrees=v("phi");fos=v("SoilTriggerFos");','degrees=v("phi");fos=v("SoilTriggerFos");H18Group=p.at("group");Need(H18Group=="psi0"||H18Group=="psi2p5"||H18Group=="psim5","Closed source material group required");H18TargetCoh=H18Group=="psim5"?7500.f:5000.f;H18Decay=H18Group=="psi0"?0.f:.2f;H18E=v("ModulusE");H18Nu=v("PRvs");Need(H18E==20e6f&&H18Nu==.33f,"Actual source E/nu differs from the closed scope");'),
  ('fsoil::Material m={0.f,0.f,float(TORAD*degrees),','fsoil::Material m={H18E/(3.f*(1.f-2.f*H18Nu)),H18E/(2.f*(1.f+H18Nu)),float(TORAD*degrees),'),
  ('m.coh_p==5000.f&&m.coh_r==1000.f&&m.n_c==5.f&&m.psi0==0.f&&m.sf==0.f','m.coh_p==H18TargetCoh&&m.coh_r==1000.f&&m.n_c==5.f&&m.psi0==float(TORAD*(H18Group=="psi0"?0.f:(H18Group=="psi2p5"?2.5f:-5.f)))&&m.sf==H18Decay'),
  ('Outside the fixed actual H1.8 elastic-source material profile','Outside the fixed actual H1.8 same-material plastic source group'),
  ('Bits(p->GetvFloat("DilationDecay"),0.f),"Actual source material law2/sf0 differs"','Bits(p->GetvFloat("DilationDecay"),H18Decay),"Actual source material law2/group sf differs"'),
  ('p->GetvUint("GravityPreloadHandoffSchema")==1','p->GetvUint("GravityPreloadHandoffSchema")==2'),
  ('&&p->GetvBool("GravityPreloadElasticSource")&&p->ExistsValue("GravityPreloadHandoffContract"','&&!p->GetvBool("GravityPreloadElasticSource")&&p->ExistsValue("GravityPreloadHandoffContract"'),
  ('&&!p->GetvText("GravityPreloadHandoffContract").empty()','&&p->GetvText("GravityPreloadHandoffContract").rfind("gravity-preload-2 ",0)==0'),
  ('Bits(p->GetvFloat("GravityPreloadSourceCohesion"),5000.f)','Bits(p->GetvFloat("GravityPreloadSourceCohesion"),H18TargetCoh)'),
  ('std::vector<float> p0(Total);','std::vector<float> p0(Total),previousK(Total,0.f);'),
  ('a.plastic[q]==0.f&&Norm2(a.load[q])==0','a.plastic[q]>=0.f&&a.plastic[q]>=previousK[id]&&Norm2(a.load[q])==0'),
  ('p0Checks++;','p0Checks++;previousK[id]=a.plastic[q];if(!part)Need(a.plastic[q]==0.f,"Initial source kappa must be zero");'),
  ('a.j[q]>1-Por&&a.theta[q]==0','a.j[q]>1-Por&&a.plastic[q]==0.f&&a.theta[q]==0'),
  ('const double yield=inv.q+dp.DP_phi*inv.I-dp.DP_kc;','const auto currentDP=fsoil::UpdateDPvars(material,double(a.plastic[q]),fit);const double yield=inv.q+currentDP.DP_phi*inv.I-currentDP.DP_kc;'),
  ('Original P0/excess/kappa0/2D/finite physical domain differs','Original P0/excess/nonnegative monotone kappa/2D/finite physical domain differs'),
  ('c08_h18_bedroles_native_r1.source','c08_h18_plastic_native_r1.source'),
  (r'\"geometry_profile\":\"bedroles\"',r'\"group\":\""<<H18Group<<"\",\"ModulusE_float_reference\":"<<double(H18E)<<",\"PRvs_float_reference\":"<<double(H18Nu)<<",\"expected_handoff_schema\":2,\"source_material_CSV_keys\":14,\"source_group_XML_binding_required\":true,\"source_group_certificate_checked\":"<<(full?"true":"false")<<",\"same_material_plastic_PRE\":true,\"source_yield_uses_actual_kappa\":true,\"DP_coefficients_are_initial_kappa0_reference_only\":true,\"full_material_contract_independently_reconstructed\":false,\"geometry_profile\":\"bedroles\"'),
  (r'\"kappa_zero_checks\":"<<p0Checks',r'\"kappa_nondecreasing_checks\":"<<ledger<<",\"fixed_kappa_zero_checks\":"<<fixedChecks<<",\"initial_kappa_zero_checks\":"<<Total')]
 return patch(previous,changes),original+changes

def derive_receiver(raw):
 previous,original=base.derive_receiver(raw)
 old='const std::string contract=meta->GetvText("GravityPreloadHandoffContract");JGravityPreloadState certified;'
 new='const std::string contract=meta->GetvText("GravityPreloadHandoffContract");Need(contract.rfind("gravity-preload-2 ",0)==0&&meta->ExistsValue("GravityPreloadHandoffSchema",DatUint)&&meta->GetvUint("GravityPreloadHandoffSchema")==2&&meta->ExistsValue("GravityPreloadElasticSource",DatBool)&&!meta->GetvBool("GravityPreloadElasticSource")&&meta->ExistsValue("GravityPreloadSourceCohesion",DatFloat)&&Bits(meta->GetvFloat("GravityPreloadSourceCohesion"),targetCoh)&&meta->ExistsValue("DilationDecay",DatFloat)&&Bits(meta->GetvFloat("DilationDecay"),sf),"Actual source schema2/cp/sf does not match the declared receiver group");JGravityPreloadState certified;'
 changes=[(old,new),
  ('targetCoh,N0,Rho,Water,Mass,K0,Ck);Need((certified.MaterialLawVersion==2)','targetCoh,N0,Rho,Water,Mass,K0,Ck,contract);Need(certified.Schema==2&&(certified.MaterialLawVersion==2)'),
  ('Only a legacyMR1/unifiedv2 certified elastic 10s PRE/event is admitted','Only the same-material unifiedv2 schema2 full10s PRE/event is admitted'),
  ('c08_h18_bedroles_native_r1.receiver','c08_h18_plastic_native_r1.receiver'),
  (r'\"source_completed_step\":2000000',r'\"source_handoff_schema\":2,\"source_elastic\":false,\"same_material_plastic_PRE\":true,\"source_contract_from_actual_native_header\":true,\"full_material_contract_independently_reconstructed\":false,\"target_full_material_contract_enforced_by_solver\":true,\"source_completed_step\":2000000')]
 return patch(previous,changes),original+changes

def derive_entry(raw):
 previous,original=base.derive_entry(raw)
 changes=[
  ('static float H18AS=0.f,H18Exp=0.f,H18TargetCoh=5000.f,H18Decay=0.f;','static float H18AS=0.f,H18Exp=0.f,H18TargetCoh=5000.f,H18Decay=0.f,H18E=0.f,H18Nu=0.f;\nstatic std::string H18Group;'),
  ('const std::set<std::string> keys={"group","ArtificialStressCoef"','const std::set<std::string> keys={"group","ModulusE","PRvs","ArtificialStressCoef"'),
  ('H18AS=v("ArtificialStressCoef");','H18Group=group;H18E=v("ModulusE");H18Nu=v("PRvs");H18Need(H18E==20e6f&&H18Nu==.33f,"Actual receiver E/nu differs from the closed scope");H18AS=v("ArtificialStressCoef");'),
  ('c08_h18_bedroles_native_r1.metadata','c08_h18_plastic_native_r1.metadata'),
  (r'\"geometry_profile\":\"bedroles\"',r'\"expected_source_handoff_schema\":2,\"same_material_plastic_PRE\":true,\"expected_source_material_CSV_keys\":14,\"receiver_material_CSV_keys\":16,\"ModulusE_float_reference\":"<<double(H18E)<<",\"PRvs_float_reference\":"<<double(H18Nu)<<",\"full_material_contract_independently_reconstructed\":false,\"target_full_material_contract_enforced_by_solver\":true,\"geometry_profile\":\"bedroles\"')]
 return patch(previous,changes),original+changes

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profiles',type=Path,required=True);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized,'Root full-read before one utility build');check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing/partial utility build protected');before=[];calls=[]
 try:
  profiles=read(args.profiles);need(profiles['kernel']=='Cubic' and profiles['hdp']==1.8 and profiles['Dp']==.04 and profiles['fixed_dt_s']==.000005 and profiles['preload_completed_step']==2000000 and profiles['preload_samples']==1001 and profiles['preload_damping_coefficient']==.03,'Prepared H1.8 source profile differs');recv=profiles['receiver'];need(len(recv)==2 and [q['end_completed_step'] for q in recv]==[2180000,2600000] and [q['samples'] for q in recv]==[91,301],'Use the actual replayed 91/301 plans including first-post5us')
  bp=L/'mdbc_partition_ReleaseCPU_r1.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'],'Passed closed utility build required');objects=[q for q in b['project_objects'] if Path(q['path']).stem in ('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')];need(len(objects)==6,'Exactly six sealed BI4 utility objects');capture=read(bind(b['source_capture'])['path']);archive=Path(bind(capture['archive'])['path']);physical_build=L/'c08_preload_schema2_ReleaseCPU_r1.build.json';pb=read(physical_build);need(pb['passed'] and pb['configuration']=='ReleaseCPU' and pb['consumed_stats_unchanged'],'Passed actual schema2 physical source/header build required');physical_archive=Path(bind(pb['source_archive'])['path'])
  source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');source_base=T/'support/upl_c08_hdp15_preload_partial_r3.cpp';receiver_base=T/'support/upl_c08_plane_native_r1.cpp';neutral=T.parent.parent/'02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp';entry_base=T/'support/c08_h18_native_r1.cpp';before=[stat(q) for q in (Path(__file__),Path(base.__file__),Path(base.base.__file__),entry_base,Path(e.__file__),Path(keep.__file__),Path(keep.csvfix.__file__),source,note,source_base,receiver_base,neutral,args.profiles,bp,physical_build)]+[bind(b['source_capture']),stat(archive),stat(physical_archive),*[bind(q) for q in objects]]+[stat(Path(q)) for q in [profiles['preload_plan']]+[x['plan'] for x in recv]]
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
  source_raw=source_base.read_text(encoding='utf-8');receiver_raw=receiver_base.read_text(encoding='utf-8');source_core,source_changes=derive_source(source_raw);receiver_core,receiver_changes=derive_receiver(receiver_raw);entry_raw=entry_base.read_text(encoding='utf-8');entry_core,entry_changes=derive_entry(entry_raw);includes=[]
  for text in (pure,source_core,receiver_core):
   for line in text.splitlines():
    if line.startswith('#include ') and '"public22_core_r1.h"' not in line and line not in includes:includes.append(line)
  def lift(text,keep_pure=False):return '\n'.join(line for line in text.splitlines() if not line.startswith('#include ') or (keep_pure and '"public22_core_r1.h"' in line))+'\n'
  generated={OUT/'h18_plastic_entry_r1.cpp':entry_core,OUT/'h18_headers_r1.h':'\n'.join(includes)+'\n',OUT/'public22_core_r1.h':lift(pure),OUT/'h18_source_core_r1.cpp':lift(source_core,True),OUT/'h18_receiver_core_r1.cpp':lift(receiver_core),OUT/'h18_profiles_r1.h':'static constexpr unsigned H18Event=2000000,H18SourceSamples=1001,H18WindowEnd=2180000,H18WindowSamples=91,H18FormalEnd=2600000,H18FormalSamples=301;\nstatic constexpr double H18Dt=.000005;\n'}
  for path,text in generated.items():path.write_text(text,encoding='utf-8',newline='\n')
  diffs=[]
  for name,old,new in [('source',source_raw,source_core),('receiver',keep.derive_core(receiver_raw),receiver_core),('entry',entry_raw,entry_core)]:
   path=OUT/(name+'_core.diff');path.write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='sealed/'+name,tofile='generated/'+name,n=3)),encoding='utf-8');diffs.append(stat(path))
  derivation=OUT/'core_derivation.json';save(derivation,dict(source_baseline=stat(source_base),receiver_baseline=stat(receiver_base),generated=[stat(q) for q in generated],diffs=diffs,source_declared_replacements=source_changes,receiver_declared_replacements=receiver_changes,entry_declared_replacements=entry_changes,geometry_profile='bedroles',PRE_schema=2,same_material_plastic_PRE=True,source_material_CSV_keys=14,receiver_material_CSV_keys=16,source_yield_uses_actual_kappa=True,old_elastic_tool_changed=False,release_target_ID_begin=1805,release_target_ID_count=255,retained_fixed_ID_begin=0,retained_fixed_ID_count=1805,KeepBedOverlap_metadata_required_absent=True,profile_source_job_used_as_runtime_identity=False,reverse_declared_replacements_exact=True,headers_lifted_before_separate_namespaces=True,pure22_loader_body_unchanged=True,original_numerical_tolerances_changed=False,source_event=2000000,source_count=1001,receiver_counts=[91,301],actual_five_column_plans=True,first_post_saved_step=2000000,first_post_completed_step=2000001,old_files_changed=False));before += [stat(q) for q in generated]+diffs+[stat(derivation),stat(headers/'FunSoilMaterial.h'),stat(headers/'JGravityPreloadState.h')]
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required');cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08H18PlasticNative_win64.exe';ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)];la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[q['path'] for q in objects]];calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(q['path'])==q for q in before),'Closed source/object/profile changed')
  save(check,dict(stage=TAG+'.build',passed=True,geometry_profile='bedroles',PRE_schema=2,same_material_plastic_PRE=True,full_material_contract_independently_reconstructed=False,profile_source_job_used_as_runtime_identity=False,program=stat(exe),source=stat(source),profiles=stat(args.profiles),source_build=stat(bp),source_capture=b['source_capture'],source_archive=stat(archive),physical_source_build=stat(physical_build),physical_source_archive=stat(physical_archive),generated=[stat(q) for q in generated],core_derivation=stat(derivation),objects=objects,actual_link_objects=7,JSph_objects_linked=False,calls=calls,consumed=before,consumed_stats_unchanged=True,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0))
 except Exception as error:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,SHA_scans=0))
  raise
if __name__=='__main__':main()
