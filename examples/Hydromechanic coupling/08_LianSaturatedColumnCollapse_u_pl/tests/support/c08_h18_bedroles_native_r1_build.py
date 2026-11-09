"""Build only the explicit bed-role split H1.8 shared native adapter; old tools unchanged."""
import argparse,os,subprocess,difflib
from pathlib import Path
from zipfile import ZipFile
import c08_h18_native_r1_build as base
e,keep=base.e,base.keep
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='c08_h18_bedroles_native_r1';OUT=T/'outputs'/(TAG+'_build')
need,read,stat,bind,save,invoke=e.need,e.read,e.stat,e.bind,e.save,e.invoke
patch=base.patch

def derive_source(raw):
 previous,original=base.derive_source(raw)
 changes=[('p->GetvUint("GravityPreloadTargetIdBegin")==1800','p->GetvUint("GravityPreloadTargetIdBegin")==1805'),('p->GetvUint("GravityPreloadTargetIdCount")==260','p->GetvUint("GravityPreloadTargetIdCount")==255'),
  ('c08_h18_native_r1.source','c08_h18_bedroles_native_r1.source'),
  (r'\"native_IDs\":7060',r'\"geometry_profile\":\"bedroles\",\"release_target_ID_begin\":1805,\"release_target_ID_count\":255,\"keep_bed_overlap\":false,\"native_IDs\":7060')]
 return patch(previous,changes),original+changes

def derive_receiver(raw):
 previous,original=base.derive_receiver(raw)
 kept='static constexpr unsigned KeptBed[]={1800,1852,1904,1956,2008};\nstatic bool Kept(unsigned id){return std::binary_search(KeptBed,KeptBed+5,id);}\nstatic bool Retired(unsigned id){return id>=RetireBegin&&id<RetireBegin+RetireCount&&!Kept(id);}'
 geometry='  for(unsigned id:KeptBed){Need(id>=RetireBegin&&id<RetireBegin+RetireCount&&id<Fixed,"Kept ID must belong to the original certified right-wall target");const auto x=certified.Pos[certified.ById[id]];Need(std::abs(x.z+.5*Dp)<=1e-6*Dp&&std::abs(x.z+.5*double(float(Dp)))<=1e-6*Dp,"Kept source position is not the original half-dp shallow bed row on plane zero");}'
 changes=[('RetireBegin=1800,RetireCount=260','RetireBegin=1805,RetireCount=255'),(kept,'static bool Retired(unsigned id){return id>=RetireBegin&&id<RetireBegin+RetireCount;}'),
  (geometry,'  Need(RetireBegin==1805&&RetireCount==255&&Active==6805&&Fixed==2060,"Explicit contiguous bed-role split profile differs"); // All retained fixed positions are checked below against source by ID.'),
  ('c08_h18_native_r1.receiver','c08_h18_bedroles_native_r1.receiver'),
  (r'\"release_target_ID_begin\":1800,\"release_target_ID_count\":260,\"actual_retired_count\":255,\"actual_retired_IDs_contiguous\":false,\"kept_bed_IDs\":[1800,1852,1904,1956,2008],\"kept_bed_count\":5,\"actual_fixed_IDs\":1805,\"kept_bed_source_geometry_checks\":5,\"GravityPreloadReleasePolicy\":\"KeepBedOverlap\"',r'\"geometry_profile\":\"bedroles\",\"release_target_ID_begin\":1805,\"release_target_ID_count\":255,\"actual_retired_count\":255,\"actual_retired_IDs_contiguous\":true,\"retained_fixed_ID_begin\":0,\"retained_fixed_ID_count\":1805,\"actual_fixed_IDs\":1805,\"keep_bed_overlap\":false')]
 return patch(previous,changes),original+changes

def derive_entry(raw):
 line=next(q for q in raw.splitlines() if 'H18Need(p->ExistsValue("GravityPreloadKeepBedOverlap"' in q)
 changes=[('// Shared H=.072f / 5us C08 native inspector. No solver or physical update is linked.','// Shared H=.072f / 5us C08 bed-role split inspector: no KeepBedOverlap and no physical update.'),
  (line,'  for(const char* key:{"GravityPreloadKeepBedOverlap","GravityPreloadReleasePolicy","GravityPreloadKeptBedIds","GravityPreloadKeptBedCount","GravityPreloadActualRetiredCount"})H18Need(!p->ExistsValue(key),"Bed-role split must not carry old KeepBedOverlap metadata");'),
  ('c08_h18_native_r1.metadata','c08_h18_bedroles_native_r1.metadata'),
  (r'\"keep_bed_overlap\":true,\"original_target_count\":260,\"actual_retired_count\":255,\"kept_bed_IDs\":[1800,1852,1904,1956,2008]',r'\"geometry_profile\":\"bedroles\",\"keep_bed_overlap\":false,\"original_target_begin\":1805,\"original_target_count\":255,\"actual_retired_count\":255,\"retained_fixed_ID_begin\":0,\"retained_fixed_ID_count\":1805')]
 return patch(raw,changes),changes

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profiles',type=Path,required=True);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized,'Root full-read before one utility build');check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing/partial utility build protected');before=[];calls=[]
 try:
  profiles=read(args.profiles);need(profiles['kernel']=='Cubic' and profiles['hdp']==1.8 and profiles['Dp']==.04 and profiles['fixed_dt_s']==.000005 and profiles['preload_completed_step']==2000000 and profiles['preload_samples']==1001 and profiles['preload_damping_coefficient']==.03,'Prepared H1.8 source profile differs');recv=profiles['receiver'];need(len(recv)==2 and [q['end_completed_step'] for q in recv]==[2180000,2600000] and [q['samples'] for q in recv]==[91,301],'Use the actual replayed 91/301 plans including first-post5us')
  bp=L/'mdbc_partition_ReleaseCPU_r1.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'],'Passed closed utility build required');objects=[q for q in b['project_objects'] if Path(q['path']).stem in ('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')];need(len(objects)==6,'Exactly six sealed BI4 utility objects');capture=read(bind(b['source_capture'])['path']);archive=Path(bind(capture['archive'])['path']);physical_build=L/'upl_c08_bedkeep_Release_r1.build.json';pb=read(physical_build);need(pb['passed'],'Original runtime_r6 source build required');physical_archive=Path(bind(pb['source_archive'])['path'])
  source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');source_base=T/'support/upl_c08_hdp15_preload_partial_r3.cpp';receiver_base=T/'support/upl_c08_plane_native_r1.cpp';neutral=T.parent.parent/'02_TerzaghiConsolidation_q0_PR/tests/support/upl_cpu_public_native_r1.cpp';entry_base=T/'support/c08_h18_native_r1.cpp';before=[stat(q) for q in (Path(__file__),Path(base.__file__),entry_base,Path(e.__file__),Path(keep.__file__),Path(keep.csvfix.__file__),source,note,source_base,receiver_base,neutral,args.profiles,bp,physical_build)]+[bind(b['source_capture']),stat(archive),stat(physical_archive),*[bind(q) for q in objects]]+[stat(Path(q)) for q in [profiles['preload_plan']]+[x['plan'] for x in recv]]
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
  generated={OUT/'h18_bedroles_entry_r1.cpp':entry_core,OUT/'h18_headers_r1.h':'\n'.join(includes)+'\n',OUT/'public22_core_r1.h':lift(pure),OUT/'h18_source_core_r1.cpp':lift(source_core,True),OUT/'h18_receiver_core_r1.cpp':lift(receiver_core),OUT/'h18_profiles_r1.h':'static constexpr unsigned H18Event=2000000,H18SourceSamples=1001,H18WindowEnd=2180000,H18WindowSamples=91,H18FormalEnd=2600000,H18FormalSamples=301;\nstatic constexpr double H18Dt=.000005;\n'}
  for path,text in generated.items():path.write_text(text,encoding='utf-8',newline='\n')
  diffs=[]
  for name,old,new in [('source',source_raw,source_core),('receiver',keep.derive_core(receiver_raw),receiver_core),('entry',entry_raw,entry_core)]:
   path=OUT/(name+'_core.diff');path.write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='sealed/'+name,tofile='generated/'+name,n=3)),encoding='utf-8');diffs.append(stat(path))
  derivation=OUT/'core_derivation.json';save(derivation,dict(source_baseline=stat(source_base),receiver_baseline=stat(receiver_base),generated=[stat(q) for q in generated],diffs=diffs,source_declared_replacements=source_changes,receiver_declared_replacements=receiver_changes,entry_declared_replacements=entry_changes,geometry_profile='bedroles',release_target_ID_begin=1805,release_target_ID_count=255,retained_fixed_ID_begin=0,retained_fixed_ID_count=1805,KeepBedOverlap_metadata_required_absent=True,profile_source_job_used_as_runtime_identity=False,reverse_declared_replacements_exact=True,headers_lifted_before_separate_namespaces=True,pure22_loader_body_unchanged=True,original_numerical_tolerances_changed=False,source_event=2000000,source_count=1001,receiver_counts=[91,301],actual_five_column_plans=True,first_post_saved_step=2000000,first_post_completed_step=2000001,old_files_changed=False));before += [stat(q) for q in generated]+diffs+[stat(derivation),stat(headers/'FunSoilMaterial.h'),stat(headers/'JGravityPreloadState.h')]
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required');cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08H18BedrolesNative_win64.exe';ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)];la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[q['path'] for q in objects]];calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(q['path'])==q for q in before),'Closed source/object/profile changed')
  save(check,dict(stage=TAG+'.build',passed=True,geometry_profile='bedroles',profile_source_job_used_as_runtime_identity=False,program=stat(exe),source=stat(source),profiles=stat(args.profiles),source_build=stat(bp),source_capture=b['source_capture'],source_archive=stat(archive),physical_source_build=stat(physical_build),physical_source_archive=stat(physical_archive),generated=[stat(q) for q in generated],core_derivation=stat(derivation),objects=objects,actual_link_objects=7,JSph_objects_linked=False,calls=calls,consumed=before,consumed_stats_unchanged=True,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0))
 except Exception as error:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(error),calls=calls,consumed=before,SHA_scans=0))
  raise
if __name__=='__main__':main()
