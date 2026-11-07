"""Build the small AS metadata adapter around the unchanged bounded native core; no solver/decode."""
import os,subprocess,sys,difflib
from pathlib import Path
from zipfile import ZipFile
import mdbc_partition_components_r3 as old
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_as_plane_native_r2';OUT=T/'outputs'/(TAG+'_build')
need,read,stat,bind,save,invoke=old.need,old.read,old.stat,old.bind,old.save,old.invoke

def derive_core(raw):
 old='const auto keys=Split(h,sep),values=Split(d,sep);Need(keys.size()==values.size(),"Run.csv width differs");'
 new='const auto keys=Split(h,sep);auto values=Split(d,sep);\n  if(values.size()!=keys.size()){\n    Need(sep==\';\'&&values.size()==keys.size()+1,"Only one recognized AS Configuration separator can be repaired");\n    const auto at=std::find(keys.begin(),keys.end(),"Configuration");Need(at!=keys.end()&&std::count(keys.begin(),keys.end(),"Configuration")==1,"Unique Configuration header required for recognized separator repair");\n    const std::size_t c=std::size_t(at-keys.begin()),right=keys.size()-c-1,after=values.size()-right;\n    Need(right>=2&&keys[c+1]=="Nbound"&&keys[c+2]=="Nfixed"&&after==c+2,"Configuration span/right numeric header anchor differs");\n    const std::string left="AS_Bui2008(0.2",rightpart="2.55)";\n    Need(values[c].size()>=left.size()&&values[c].compare(values[c].size()-left.size(),left.size(),left)==0&&values[c+1].rfind(rightpart,0)==0,"Unrecognized embedded Run.csv separator; raw file is not changed");\n    const std::string joined=values[c]+";"+values[c+1],marker="AS_Bui2008(0.2;2.55)";const auto p=joined.find(marker);\n    Need(p!=std::string::npos&&joined.find(marker,p+marker.size())==std::string::npos,"Exactly one known AS_Bui2008 coefficient fragment required");\n    values[c]=joined;values.erase(values.begin()+c+1);\n  }\n  Need(keys.size()==values.size(),"Run.csv width differs");'
 need(raw.count(old)==1,'Frozen RunSamples parser anchor differs; do not broaden repair');return raw.replace(old,new,1)

def main():
 need(sys.argv[1:]==['--execution-authorized'],'One root-reviewed Release reader build required');check=L/(TAG+'.build.json');need(not OUT.exists() and not check.exists(),'Existing/partial reader build protected');consumed=[];calls=[]
 try:
  bp=L/'mdbc_partition_ReleaseCPU_r1.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==87,'Passed current ReleaseCPU87 project closure required')
  objects=[e for e in b['project_objects'] if Path(e['path']).stem in ('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')];need(len(objects)==6,'Exactly six Release BI4 utility objects required')
  capture=read(bind(b['source_capture'])['path']);archive=Path(bind(capture['archive'])['path']);source=T/'support'/(TAG+'.cpp');note=T/'notes'/(TAG+'.md');consumed=[stat(__file__),stat(old.__file__),stat(source),stat(T/'support/upl_c08_plane_native_r1.cpp'),stat(note),stat(bp),bind(b['source_capture']),stat(archive),*[bind(e) for e in objects]]
  OUT.mkdir();core=T/'support/upl_c08_plane_native_r1.cpp';original=core.read_text(encoding='utf8');generated=OUT/'as_plane_core_r2.cpp';generated.write_text(derive_core(original),encoding='utf8',newline='\n');diff=OUT/'as_plane_core_r2.diff';diff.write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),generated.read_text(encoding='utf8').splitlines(keepends=True),fromfile='support/upl_c08_plane_native_r1.cpp',tofile='generated/as_plane_core_r2.cpp',n=3)),encoding='utf8');derivation=OUT/'core_derivation.json';save(derivation,dict(baseline_core=stat(core),generated_core=stat(generated),diff=stat(diff),only_RunSamples_parser_changed=True,recognized_fragment='AS_Bui2008(0.2;2.55)',numeric_column_guards_changed=False,raw_CSV_changed=False));consumed += [stat(generated),stat(diff),stat(derivation)];headers=OUT/'headers';headers.mkdir()
  with ZipFile(archive) as z:
   for item in z.infolist():
    if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
     target=headers/Path(item.filename).name;need(not target.exists(),'Duplicate archived header leaf');target.write_bytes(z.read(item))
  setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW);need(setup.returncode==0,'MSVC setup failed');env=dict(os.environ);env.update(s.split('=',1) for s in setup.stdout.decode('mbcs').splitlines() if '=' in s and not s.startswith('='));need(env['VCTOOLSVERSION']=='14.36.32532','Matching MSVC14.36 required')
  cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=OUT/'reader.obj';exe=OUT/'C08NativeASPlane_win64.exe'
  ca=[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/O2','/MT','/GL-','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(OUT),'/I'+str(headers),'/Fo'+str(obj),str(source)]
  la=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/INCREMENTAL:NO','/OPT:REF','/OPT:NOICF','/OUT:'+str(exe),str(obj),*[e['path'] for e in objects]]
  calls.append(invoke(TAG+'.compile',ca,OUT,env));calls.append(invoke(TAG+'.link',la,OUT,env));need(all(stat(e['path'])==e for e in consumed),'Consumed reader source/object changed')
  save(check,dict(stage=TAG+'.build',passed=True,configuration='ReleaseCPU utility closure; O2 MT fp:precise GL-',program=stat(exe),source=stat(source),generated_core=stat(generated),core_diff=stat(diff),core_derivation=stat(derivation),source_build=stat(bp),source_capture=b['source_capture'],source_archive=stat(archive),objects=objects,calls=calls,consumed=consumed,consumed_stats_unchanged=True,actual_link_objects=7,JSph_objects_linked=False,Debug_objects_or_CRT_used=False,solver_builds=0,solver_invocations=0,native_decodes=0,SHA_scans=0));print('RELEASE_READER_BUILD_PASSED',exe,flush=True)
 except Exception as e:
  if not check.exists():save(check,dict(stage=TAG+'.build',passed=False,first_failure=str(e),calls=calls,consumed=consumed,SHA_scans=0))
  raise
if __name__=='__main__':main()
