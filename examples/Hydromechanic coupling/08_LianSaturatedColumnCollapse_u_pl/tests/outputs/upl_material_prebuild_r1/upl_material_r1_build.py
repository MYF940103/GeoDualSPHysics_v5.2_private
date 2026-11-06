import datetime,json,os,pathlib,re,subprocess,sys,time,xml.etree.ElementTree as E,zipfile
import psutil
S=pathlib.Path(r'D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b/src')
T=S.parent/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests'
conf=sys.argv[1];assert conf in ('DebugCPU','Debug') and len(sys.argv)==2
gpu=conf=='Debug';tag='upl_material_'+conf+'_r1'
out=T/'outputs'/tag;intdir=pathlib.Path(r'C:/Users/syosh/AppData/Local/Temp/upl_material_r1')/conf/'int'
log=T/'logs'/(tag+'.log');call=T/'logs'/(tag+'.call.json');build=T/'logs'/(tag+'.build.json')
source=T/'logs'/(tag+'.source.json');binlog=T/'logs'/(tag+'.binlog')
def smt(p):
 p=pathlib.Path(p);s=p.stat();return dict(path=str(p.resolve()),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def save(p,d):
 with pathlib.Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
for p in (out,intdir.parent,log,call,build,source,binlog):assert not p.exists(),p
if gpu:
 previous=T/'logs/upl_free_seepage_Debug_r1'
else:
 previous=T/'logs/upl_free_seepage_DebugCPU_r1'
priorcall=read(str(previous)+'.call.json');assert priorcall['exit_code']==0
priorbuild=read(str(previous)+'.build.json');assert priorbuild['passed'] is True
prior_source=read(priorbuild['source'])
apply_record=T/'logs/upl_material_apply_r1.json';ap=read(apply_record)
assert ap['base_head']=='0c29b432b2343351e98afacc474e93440cfde628'
applied=[]
for x in ap['after']:
 p=S.parent/x['path']
 if p.parent!=S/'source':continue  # XML prose is not a compiler input.
 r=smt(p);assert (r['bytes'],r['mtime_ns'])==(x['bytes'],x['mtime_ns']),p
 applied.append(r)
assert {pathlib.Path(x['path']).name for x in applied}=={'DualSphDef.h','FunSoilMaterial.h','JPartsLoad4.cpp','JSph.cpp','JSphCpu.cpp','JSphGpu.cpp','JSphGpu.h','JSphGpuSimple_ker.h','JSphGpuSimple_ker.cu'}
proj=S/'VS'/('DualSPHysics5Re.vcxproj' if gpu else 'DualSPHysics5ReCpu.vcxproj')
sln=S/'VS'/('DualSPHysics5Re.sln' if gpu else 'DualSPHysics5ReCpu_vs2022.sln')
ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'};pr=E.parse(proj).getroot();units=[]
for kind in ('ClCompile','CudaCompile'):
 for x in pr.findall('.//m:'+kind+'[@Include]',ns):
  if not any((z.text or '').lower()=='true' and "'"+conf+"|x64'" in z.attrib.get('Condition','') for z in x.findall('m:ExcludedFromBuild',ns)):
   units.append((proj.parent/x.attrib['Include'].replace('\\','/')).resolve())
expected=111 if gpu else 86
assert len(units)==expected and all(p.is_file() for p in units)
files=sorted(set([pathlib.Path(x['path']) for x in prior_source['files']]+units+[proj,sln,pathlib.Path(__file__).resolve(),apply_record]+[pathlib.Path(x['path']) for x in applied]))
before=[smt(p) for p in files]
canonical=[smt(p) for p in sorted((S.parent/'bin/windows').iterdir()) if p.is_file() and p.suffix.lower() in ('.exe','.pdb','.dll','.xml')]
protected=[]
for q in ('upl_free_seepage_DebugCPU_r1','upl_free_seepage_Debug_r1'):
 d=read(T/'logs'/(q+'.build.json'));records=d.get('project_objects',d.get('object_records'))
 assert records
 protected += [smt(x['path']) for x in records]
 assert protected[-len(records):]==records
 protected.append(smt(d['program']['path']))
runtime=read(T/'logs/upl_c08_global_GPU_r1.build.json')['runtime']
for x in runtime:assert smt(x['path'])==x;protected.append(x)
if gpu:
 d=read(T/'logs/upl_material_DebugCPU_r1.build.json');assert d['passed'] is True
 protected += [smt(x['path']) for x in d['project_objects']]+[smt(d['program']['path'])]
envcall='call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set'
v=subprocess.run(['cmd','/d','/s','/c',envcall],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
for line in v.stdout.decode('mbcs').splitlines():
 if '=' in line and not line.startswith('='):
  k,val=line.split('=',1);os.environ[k]=val
assert os.environ['VCTOOLSVERSION']=='14.36.32532' 
assert not any((p.info['name'] or '').lower().startswith('dualsphysics') for p in psutil.process_iter(['name']))
if gpu:
 assert 'v11.7' in os.environ.get('CUDA_PATH_V11_7','').replace('\\','/')
 assert 'compute_86,sm_86' in proj.read_text(encoding='utf-8')
out.mkdir();intdir.mkdir(parents=True);archive=out/'source.zip'
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.relative_to(S.parent).as_posix())
save(source,dict(stage=tag+'.source',base_head_reported=ap['base_head'],Git_used=False,SHA_scans=0,configuration=conf+'|x64',effective_compile_units=expected,files=before,applied_source=applied,archive=smt(archive),compiler='MSVC14.36.32532',cuda='11.7 sm86' if gpu else None,scope='Current project/source SMT and local archive; docs and historical live-source hashes are not compiler-identity gates.'))
assert [smt(p) for p in files]==before
msbuild=pathlib.Path(priorcall['program'])
args=list(priorcall['arguments']);args[0]=str(sln)
args=[('/p:OutDir='+out.as_posix()+'/' if a.startswith('/p:OutDir=') else '/p:IntDir='+intdir.as_posix()+'/' if a.startswith('/p:IntDir=') else '/bl:'+str(binlog) if a.startswith('/bl:') else a) for a in args]
if not any(a.startswith('/bl:') for a in args):args.append('/bl:'+str(binlog))
if '/nr:false' not in args:args.append('/nr:false')
if '/p:PostBuildEventUseInBuild=false' not in args:args.append('/p:PostBuildEventUseInBuild=false')
owner=psutil.Process();ownerinfo=dict(pid=owner.pid,creation_time=owner.create_time(),exe=owner.exe(),command=owner.cmdline(),cwd=owner.cwd())
started=now();t0=time.monotonic();rc=None;child=None;failure=None
try:
 with log.open('xb') as f:
  p=subprocess.Popen([str(msbuild)]+args,cwd=str(S),env=os.environ.copy(),stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
  q=psutil.Process(p.pid);child=dict(pid=p.pid,creation_time=q.create_time(),ppid=q.ppid(),exe=q.exe(),command=q.cmdline())
  assert child['ppid']==owner.pid
  print(tag+' MSBuild PID '+str(p.pid)+' owner '+str(owner.pid),flush=True)
  rc=p.wait()
except BaseException as e:failure=repr(e)
save(call,dict(stage=tag,owner=ownerinfo,program=str(msbuild),arguments=args,working_directory=str(S),source=str(source),started_utc=started,child=child,exit_code=rc,direct_exit=type(rc) is int,typed_returncode_captured_from_Popen_wait=type(rc) is int,invocation_failure=failure,ended_utc=now(),elapsed_s=time.monotonic()-t0,log=str(log),binlog=str(binlog)))
def changes(records):
 return [x['path'] for x in records if not pathlib.Path(x['path']).is_file() or smt(x['path'])!=x]
changed=changes(before);canonical_changed=changes(canonical);protected_changed=changes(protected)
objects=[smt(p) for p in sorted(intdir.glob('*.obj'))]
exe=out/('DualSPHysics5.2_win64_debug.exe' if gpu else 'DualSPHysics5.2CPU_win64_debug.exe')
text=log.read_bytes().decode('mbcs',errors='replace')
warnings=[x for x in text.splitlines() if re.search(r'\bwarning [A-Z]+\d+',x,re.I)]
errors=[x for x in text.splitlines() if re.search(r'\b(?:fatal )?error [A-Z]+\d+',x,re.I)]
passed=type(rc) is int and rc==0 and failure is None and exe.is_file() and len(objects)==expected and (intdir/'main.obj').is_file() and not changed and not canonical_changed and not protected_changed and not errors
d=dict(stage=tag,passed=passed,program=smt(exe) if exe.is_file() else None,objects=len(objects),objects_directory=str(intdir),project_objects=objects,non_main_objects=sum(pathlib.Path(x['path']).name.lower()!='main.obj' for x in objects),source=str(source),call=str(call),actual_typed_exit_code=rc,source_stats_unchanged=not changed,changed_source=changed,canonical_stats_before=canonical,canonical_stats_unchanged=not canonical_changed,changed_canonical=canonical_changed,protected_prior_program_object_runtime_stats=protected,protected_stats_unchanged=not protected_changed,changed_protected=protected_changed,warning_lines=warnings,error_lines=errors,compiler='MSVC14.36.32532',cuda='11.7 sm86' if gpu else None,base_head_reported=ap['base_head'],compiler_link_exit_scope='The genuine MSBuild wait exit is captured. CL/CUDA/link tasks are owned by MSBuild and recorded in the log/binlog; no separate tool exit codes are invented.',runtime_copied=False,program_or_component_started=False,SHA_scans=0,Git_used=False,material_caller_validation_pending=True,public_mixed_gravity_or_plastic_admission=False,physical_acceptance=False)
save(build,d)
print(json.dumps(dict(stage=tag,passed=passed,exit_code=rc,program=d['program'],objects=len(objects),non_main_objects=d['non_main_objects'],objects_directory=str(intdir),warnings=len(warnings),errors=errors,source_unchanged=not changed,canonical_unchanged=not canonical_changed,protected_unchanged=not protected_changed),indent=2),flush=True)
assert passed,(rc,failure,errors,changed,canonical_changed,protected_changed)
