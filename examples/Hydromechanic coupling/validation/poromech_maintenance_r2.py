"""Exact cross-case ILK/pyc deletion and transparent NTFS VTK compression only."""
from __future__ import annotations
import argparse,ctypes,csv,json,os,re,shutil,subprocess,sys,time
from ctypes import wintypes as w
from pathlib import Path
sys.dont_write_bytecode=True
V=Path(__file__).resolve().parent;H=V.parent;R=H.parent.parent
TAG="poromech_maintenance_r2";NOTE=V/(TAG+".md");PLAN=V/(TAG+".plan.json");JOURNAL=V/(TAG+".apply.journal.jsonl");CHECK=V/(TAG+".apply.check.json")
C2=H/"02_TerzaghiConsolidation_q0_PR/tests";C4=H/"04_CryerProblem_PR/tests";C8=H/"08_LianSaturatedColumnCollapse_u_pl/tests"
START=C2/"logs/upl_tpi_p3_B10us_full2tv_GPU_r1.start.json"
BUILDS=[C2/"logs"/("upl_tpi_p3_full_"+c+"_r1.build.json")for c in("DebugCPU","ReleaseCPU","Debug","Release")]
ILKS=[
 ("upl_gravity_wall_gpu_Debug_r1","upl_gravity_wall_gpu_Debug_r1_helper","upl_gravity_wall_gpu_r1",46016808),
 ("upl_gpu_wall_wall_actual_Debug_r2","upl_gpu_wall_wall_actual_Debug_r2","upl_gpu_wall_actual_r1",46011448),
 ("upl_gpu_perm_component_Debug_r1","upl_gpu_perm_component_Debug_r1","upl_gpu_perm_component_r1",45854672),
 ("upl_gpu_wall_component_Debug_r1","upl_gpu_wall_component_Debug_r1","upl_gpu_wall_component_r1",45772224),
 ("upl_gpu_darcy_component_Debug_r3","upl_gpu_darcy_component_Debug_r3","upl_gpu_darcy_component_r3",45675752),
 ("upl_gpu_darcy_component_Debug_r2","upl_gpu_darcy_component_Debug_r2","upl_gpu_darcy_component_r2",45675752),
 ("upl_gpu_gravity_endpoint_Debug_r1","upl_gpu_gravity_endpoint_Debug_r1_helper","upl_gpu_gravity_endpoint_r1",45666016)]
PYCS=["cryer_darcy_closed_r1","cryer_load_pair_r1","cryer_start_r1"]
GROUPS=[*( (C2/"outputs"/n/"particles",401,41500292)for n in("stress_full_r1_float","stress_full_r1_dt1","stress_full_r1_dt05")),
 (C4/"outputs/vtk_reexport_20261008",11,56655042),(C4/"outputs/vtk_reexport_20261008_initial",11,55720088),
 (C8/"outputs/c08_h18_wall_c_retry_full3_GPU_r2/particles",602,430599463),
 (C8/"outputs/c08_h18_hg_psi2p5_full3_r1/particles",602,430599463),
 (C8/"outputs/upl_c08_nopen_public_reg_r1/particles",30,21442695),
 (C8/"outputs/upl_c08_resume_r1_psi0_GPU_short/particles",20,14295130)]
COMPACT=Path(os.environ.get("SystemRoot","C:/Windows"))/"System32/compact.exe"
K=ctypes.WinDLL("kernel32",use_last_error=True)if os.name=="nt"else None
if K:
 K.GetFileAttributesW.argtypes=[w.LPCWSTR];K.GetFileAttributesW.restype=w.DWORD
 K.GetCompressedFileSizeW.argtypes=[w.LPCWSTR,ctypes.POINTER(w.DWORD)];K.GetCompressedFileSizeW.restype=w.DWORD
 K.GetCurrentProcess.restype=w.HANDLE;K.SetPriorityClass.argtypes=[w.HANDLE,w.DWORD];K.SetPriorityClass.restype=w.BOOL
 K.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];K.GetProcessTimes.restype=w.BOOL
 K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
def need(x,msg):
 if not x:raise RuntimeError(msg)
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def write(p,data):
 with Path(p).open("x",encoding="utf8",newline="\n")as f:json.dump(data,f,indent=2,ensure_ascii=False);f.write("\n")
def key(p):return os.path.normcase(str(Path(p).resolve()))
def stat(p):
 p=Path(p).resolve(strict=True);s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def same(e):
 now=stat(e["path"]);need(all(now[k]==e[k]for k in("path","bytes","mtime_ns")),"Frozen stat changed: "+e["path"]);return now
def attrs(p):
 value=int(K.GetFileAttributesW(str(p)));need(value!=0xffffffff,"GetFileAttributesW failed: "+str(p));return value
def safe(p,exists=True):
 p=Path(os.path.abspath(p));need(p.is_relative_to(R),"Mutation escapes the exact workspace: "+str(p))
 for q in(p,*p.parents):
  if q.exists():need(not(attrs(q)&0x400),"Reparse point forbidden: "+str(q))
  if q==R:break
 z=p.resolve(strict=exists);need(z.is_relative_to(R)and z==p,"Resolved target differs/escapes workspace: "+str(p));return z
def record(p):
 p=safe(p);s=stat(p);a=attrs(p);need(not(a&0x10),"Expected a file: "+str(p));hi=w.DWORD();ctypes.set_last_error(0);lo=int(K.GetCompressedFileSizeW(str(p),ctypes.byref(hi)))
 need(lo!=0xffffffff or ctypes.get_last_error()==0,"GetCompressedFileSizeW failed: "+str(p))
 return dict(**s,attributes=a,compressed=bool(a&0x800),reported_allocated_bytes=(int(hi.value)<<32)|lo)
def exact(e):
 z=record(e["path"]);need(z==e,"Planned file metadata/allocation changed: "+e["path"]);return z
def paths(data):
 out=set()
 def visit(x):
  if isinstance(x,dict):
   for v in x.values():visit(v)
  elif isinstance(x,list):
   for v in x:visit(v)
  elif isinstance(x,str):
   m=re.search(r"(?:^|:)([A-Za-z]:[\\/].*)",x.strip('"'))
   if m:out.add(key(m[1].strip('"')))
 visit(data);return out

class Admission:
 def __init__(self,p,phase):
  self.entry,self.data=stat(p),read(p);self.used={}
  need(self.data.get("stage")==TAG+"."+phase+"_admission"and self.data.get("passed")is True and self.data.get("maintenance_only")is True,"One exact root-reviewed maintenance action required")
  self.frozen={key(e["path"]):e for e in self.data["inputs"]};need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
  for p in(Path(__file__),NOTE,COMPACT):self.pin(p)
 def pin(self,p):
  k=key(p);need(k in self.frozen,"Unadmitted maintenance evidence: "+str(p));self.used[k]=same(self.frozen[k]);return self.used[k]
 def finish(self):
  for e in self.used.values():same(e)
  same(self.entry);return list(self.used.values())

def protection(ad):
 se=ad.pin(START);s=read(START);ae=ad.pin(s["root_admission"]["path"]);same(s["root_admission"]);a=read(ae["path"])
 need(s["owner"]["pid"]==51340 and s["target"]["pid"]==35020 and s["target"]["parent"]==51340,"Expected active full ownership differs")
 roots=[se,ae];named=paths(s)|paths(a)
 for p in BUILDS:
  e=ad.pin(p);d=read(p);need(d.get("passed")is True and d.get("stage")=="upl_tpi_p3_full_build_r1","Original actual full build must pass");roots.append(e);named|=paths(d)
 paused=a["allowed_paused_gpu_processes"];need(len(paused)==1 and paused[0]["pid"]==43828 and paused[0]["parent"]==36608,"Original paused C08 target differs")
 owner=a["protected_C08_owner_observation"];need(owner["pid"]==36608,"Original C08 owner differs")
 return roots,named,dict(full_owner=s["owner"],full_solver=s["target"],C08_owner=owner,C08_solver=paused[0])
def processes(ad,expected):
 import psutil
 ad.pin(psutil.__file__);out={}
 for role,e in expected.items():
  p=psutil.Process(e["pid"]);z=dict(pid=p.pid,created=p.create_time(),exe=p.exe(),argv=p.cmdline(),parent=p.ppid(),status=p.status())
  need(z["created"]==e["created"]and all(z[k]==e[k]for k in("exe","argv","parent")if k in e),"Protected process ownership changed: "+role)
  need(z["status"]==psutil.STATUS_STOPPED if role.startswith("C08")else z["status"]not in(psutil.STATUS_STOPPED,psutil.STATUS_DEAD,psutil.STATUS_ZOMBIE),"Protected process status differs: "+role);out[role]=z
 return out
def file_list(directory):
 directory=safe(directory);need(attrs(directory)&0x10,"Expected exact VTK directory")
 return sorted((safe(p)for p in directory.glob("*.vtk")),key=lambda p:p.name.lower())

def plan(ad):
 need(not PLAN.exists(),"Existing plan/failure protected");result=dict(stage=TAG+".plan",passed=False,root_admission=ad.entry,SHA_scans=0,mutations=0)
 try:
  roots,named,expected=protection(ad);observed=processes(ad,expected);deletes=[];retained=[];evidence=[]
  for tag,directory,stem,size in ILKS:
   folder=C2/"outputs"/directory;p=safe(folder/(stem+".ilk"));he=ad.pin(C2/"logs"/(tag+".helper.json"));le=ad.pin(C2/"logs"/(tag+"_link.call.json"));h,l=read(he["path"]),read(le["path"])
   need(str(h.get("status","")).endswith("linked_not_run")and l.get("exit_code")==0 and l.get("owned_call_exited")is True,"Old helper/link lacks its genuine completed link evidence")
   need(key(p)not in(named|paths(h)|paths(l)),"ILK is named by protected/helper evidence: "+str(p));r=record(p);need(r["bytes"]==size,"Exact old ILK size differs");deletes.append(dict(kind="old_link_incremental",file=r))
   keep=[folder/(stem+".exe"),folder/"helper.obj",folder/"compile.pdb",folder/"link.pdb"]
   need(key(h["program"]["path"])==key(keep[0])and key(h["helper_object"]["path"])==key(keep[1]),"Original retained EXE/helper.obj binding differs")
   for q in keep:
    e=ad.pin(q);safe(q);retained.append(e)
   need(stat(keep[0])["bytes"]==h["program"]["bytes"]and stat(keep[1])["bytes"]==h["helper_object"]["bytes"],"Original retained artifact byte size differs")
   evidence.extend((he,le))
  for name in PYCS:
   source=C4/"support"/(name+".py");ad.pin(source);safe(source);deletes.append(dict(kind="rebuildable_CPython311_cache",file=record(C4/"support/__pycache__"/(name+".cpython-311.pyc")),source=stat(source)))
  groups=[]
  for directory,count,size in GROUPS:
   files=[record(p)for p in file_list(directory)];need(len(files)==count and sum(e["bytes"]for e in files)==size,"Exact closed VTK group changed: "+str(directory));groups.append(dict(directory=str(directory.resolve()),count=count,logical_bytes=size,files=files))
  result.update(passed=True,protection_roots=roots,protected_named_path_count=len(named),protected_processes=observed,C08_owner_original_fields_available=list(expected["C08_owner"]),helper_evidence=evidence,retained_artifacts=retained,deletions=deletes,compression_groups=groups,delete_count=10,VTK_count=2479,NTFS_API="GetCompressedFileSizeW",volume_free_bytes_descriptive=shutil.disk_usage(R).free,all_raw_and_program_objects_protected=True,full_file_hash_or_bit_proof=False,consumed=ad.finish(),consumed_stats_unchanged=True)
 except Exception as exc:result.update(first_error=str(exc),partials_preserved=True)
 write(PLAN,result);print(PLAN);return 0 if result["passed"]else 1

def compact(ad,tag,cwd,pattern):
 safe(cwd);callpath=V/(TAG+"_"+tag+".call.json");log=V/(TAG+"_"+tag+".log");need(not callpath.exists()and not log.exists(),"Existing compact call protected")
 argv=[str(COMPACT),"/C","/I","/Q",pattern];p=None;result=dict(stage=TAG+".compact",program=ad.pin(COMPACT),arguments=argv[1:],cwd=str(cwd),shell=False,low_priority=True,actual_Popen_wait_exit=None,actual_Win32_exit=None,passed=False,argv_is_CreateProcess_request_not_separate_readback=True)
 try:
  ad.finish()
  with log.open("xb")as f:
   p=subprocess.Popen(argv,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,shell=False,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   handle=w.HANDLE(int(p._handle));created,ended,kernel,user=(w.FILETIME()for _ in range(4));need(K.GetProcessTimes(handle,*[ctypes.byref(x)for x in(created,ended,kernel,user)]),"Original compact handle creation unavailable")
   result.update(pid=p.pid,original_Win32_creation_FILETIME_ticks=(created.dwHighDateTime<<32)|created.dwLowDateTime,native_handle_observed_before_wait=True)
   result["actual_Popen_wait_exit"]=p.wait();code=w.DWORD();need(K.GetExitCodeProcess(handle,ctypes.byref(code)),"Compact native exit unavailable");result["actual_Win32_exit"]=int(code.value)
  result["passed"]=result["actual_Popen_wait_exit"]==result["actual_Win32_exit"]==0
 except Exception as exc:
  result["first_error"]=str(exc)
  if p is not None:result["actual_Popen_wait_exit"]=p.wait()
 finally:
  if log.exists():result["log"]=stat(log)
  write(callpath,result)
 return stat(callpath),result

def apply(ad):
 need(not CHECK.exists()and not JOURNAL.exists(),"Existing apply/failure/journal protected; never restart");pe=ad.pin(PLAN);p=read(PLAN);need(p.get("stage")==TAG+".plan"and p.get("passed")is True,"One genuine successful frozen plan required")
 expected={key(C2/"outputs"/directory/(stem+".ilk"))for _,directory,stem,_ in ILKS}|{key(C4/"support/__pycache__"/(n+".cpython-311.pyc"))for n in PYCS}
 need(len(p["deletions"])==10 and {key(x["file"]["path"])for x in p["deletions"]}==expected,"Plan is not the exact seven-ILK/three-pyc whitelist")
 need([(key(x["directory"]),x["count"],x["logical_bytes"])for x in p["compression_groups"]]==[(key(d),n,z)for d,n,z in GROUPS],"Plan is not the exact nine closed VTK groups")
 need(K.SetPriorityClass(K.GetCurrentProcess(),0x4000),"Unable to lower only cleanup owner priority")
 result=dict(stage=TAG+".apply",passed=False,root_admission=ad.entry,plan=pe,SHA_scans=0,solver_invocations=0,reader_invocations=0,watcher_invocations=0,full_file_hash_or_bit_proof=False,automatic_retry=False,low_priority_owner=True);deleted=[];compressed=[];calls=[]
 with JOURNAL.open("x",encoding="utf8",newline="\n")as journal:
  def event(data):journal.write(json.dumps(data,ensure_ascii=False)+"\n");journal.flush()
  try:
   roots,named,_=protection(ad);need(roots==p["protection_roots"],"Original protection roots changed");before=processes(ad,p["protected_processes"])
   for e in p["consumed"]:ad.pin(e["path"]);same(e)
   for e in p["retained_artifacts"]:same(e)
   result["processes_before"]=before;result["volume_free_bytes_before_descriptive"]=shutil.disk_usage(R).free
   fixture=safe(V/(TAG+"_fixture"),False);need(not fixture.exists(),"Fixture/failure protected");fixture.mkdir();fp=fixture/"transparent.bin";payload=bytes(range(256))*512
   with fp.open("xb")as f:f.write(payload)
   fbefore=record(fp);ce,call=compact(ad,"fixture",fixture,fp.name);calls.append(ce);fafter=record(fp)
   ok=call["passed"]and fp.read_bytes()==payload and(fbefore["bytes"],fbefore["mtime_ns"])==(fafter["bytes"],fafter["mtime_ns"])and fafter["compressed"]and fafter["reported_allocated_bytes"]<=fbefore["reported_allocated_bytes"]
   event(dict(action="fixture",passed=ok,before=fbefore,after=fafter,byte_equal_checked=True,call=ce));need(ok,"Unique128KiB NTFS transparency/stat fixture failed; no real mutation admitted")
   for item in p["deletions"]:
    processes(ad,p["protected_processes"]);e=item["file"];safe(e["path"]);exact(e);need(key(e["path"])not in named,"Deletion became a protected input")
    if "source"in item:same(item["source"])
    event(dict(action="delete_begin",kind=item["kind"],file=e));Path(e["path"]).unlink();need(not Path(e["path"]).exists(),"Whitelisted file remains after unlink");deleted.append(e);event(dict(action="delete_done",kind=item["kind"],file=e));processes(ad,p["protected_processes"])
   for index,group in enumerate(p["compression_groups"]):
    processes(ad,p["protected_processes"]);directory=safe(group["directory"]);need([key(x)for x in file_list(directory)]==[key(e["path"])for e in group["files"]],"Closed VTK inventory changed")
    for e in group["files"]:exact(e)
    event(dict(action="compact_begin",directory=str(directory),count=group["count"]));ce,call=compact(ad,"vtk%02d"%index,directory,"*.vtk");calls.append(ce);out=[];valid=True
    for e in group["files"]:
     z=record(e["path"]);ok=(e["bytes"],e["mtime_ns"])==(z["bytes"],z["mtime_ns"])and z["compressed"];valid=valid and ok;row=dict(action="compact_file",passed=ok,before=e,after=z);event(row);out.append(z)
    compressed.extend(zip(group["files"],out));event(dict(action="compact_done",directory=str(directory),passed=bool(call["passed"]and valid),call=ce));processes(ad,p["protected_processes"]);need(call["passed"]and valid,"Compact batch failed/partial; preserve journal and never retry automatically")
   for e in p["retained_artifacts"]:same(e)
   result.update(passed=True,processes_after=processes(ad,p["protected_processes"]),deleted_count=len(deleted),deleted_logical_bytes=sum(e["bytes"]for e in deleted),deleted_reported_allocated_bytes=sum(e["reported_allocated_bytes"]for e in deleted),compressed_file_count=len(compressed),VTK_reported_allocated_bytes_before=sum(a["reported_allocated_bytes"]for a,z in compressed),VTK_reported_allocated_bytes_after=sum(z["reported_allocated_bytes"]for a,z in compressed),VTK_reported_allocated_reduction_bytes=sum(a["reported_allocated_bytes"]-z["reported_allocated_bytes"]for a,z in compressed),VTK_logical_size_and_mtime_preserved=True,VTK_full_byte_proof_performed=False,fixture=stat(fp),retained_artifact_stats_unchanged=True,consumed=ad.finish(),consumed_stats_unchanged=True)
  except Exception as exc:result.update(first_error=str(exc),partials_preserved=True);event(dict(action="failed",first_error=str(exc)))
  finally:result.update(compact_calls=calls,actual_deleted_records=deleted,observed_compressed_records=len(compressed),volume_free_bytes_after_descriptive=shutil.disk_usage(R).free)
 result["journal"]=stat(JOURNAL);write(CHECK,result)
 print(CHECK);return 0 if result["passed"]else 1

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("phase",choices=("plan","apply"));ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args();need(os.name=="nt"and a.execution_authorized,"Windows and root full-read action authorization required")
 ad=Admission(a.admission,a.phase);return plan(ad)if a.phase=="plan"else apply(ad)
if __name__=="__main__":raise SystemExit(main())
