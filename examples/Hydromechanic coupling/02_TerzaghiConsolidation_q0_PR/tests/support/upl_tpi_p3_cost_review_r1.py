"""One offline, read-only SQLite performance review; never repair the failed probe label."""
from __future__ import annotations
import argparse,csv,json,re,sqlite3
from contextlib import closing
from pathlib import Path

T=Path(__file__).resolve().parents[1];L=T/"logs";TAG="upl_tpi_p3_cost_review_r1"
JOB="upl_tpi_p3_cost_probe_GPU_r1";NOTE=T/"notes"/(TAG+".md");OUT=T/"outputs"/TAG
CHECK=L/(TAG+".check.json");REPORT=T/"outputs"/(JOB+"_nsys")
DB=REPORT/"trace.sqlite";REP=REPORT/"trace.nsys-rep";GPID=282010706771968;PID=31932
FIXTURE="UplTpiGpuSourceRoleFixtureR2: source_cases=8 owner_role_cases=8 device_cases_checked=16 device_kernel_completed=true private_error_bits=0"
FLAGS=["profile","--trace=cuda","--sample=none","--cpuctxsw=none","--system-wide=false","--kill=false","--wait=all","--stop-on-exit=true","--force-overwrite=false","--stats=true","--show-output=true"]
PTX=L/"upl_tpi_gpu_Release_r3.raw_write_ptx_r1.binding.json";COMPILE=L/"upl_tpi_gpu_Release_r3.JSphGpu_ker.call.json"
NAME="CASE WHEN substr(s.value,-6,2)='_v' THEN substr(s.value,1,length(s.value)-6) ELSE s.value END"
SQL={
 "api":f"SELECT {NAME} name,count(*) calls,sum(r.end-r.start) total_ns,min(r.end-r.start) min_ns,max(r.end-r.start) max_ns FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId WHERE (r.globalTid&0xFFFFFFFFFF000000)=:g GROUP BY 1 ORDER BY total_ns DESC",
 "kernels":"SELECT s.value name,count(*) instances,sum(k.end-k.start) total_ns,min(k.end-k.start) min_ns,max(k.end-k.start) max_ns FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON s.id=k.shortName WHERE k.globalPid=:g GROUP BY 1 ORDER BY total_ns DESC",
 "memcpy":"SELECT e.label operation,m.copyKind copy_kind,m.bytes bytes_each,count(*) events,sum(m.bytes) total_bytes,sum(m.end-m.start) gpu_total_ns FROM CUPTI_ACTIVITY_KIND_MEMCPY m JOIN ENUM_CUDA_MEMCPY_OPER e ON e.id=m.copyKind WHERE m.globalPid=:g GROUP BY 1,2,3 ORDER BY gpu_total_ns DESC",
 "memset":"SELECT bytes bytes_each,count(*) events,sum(bytes) total_bytes,sum(end-start) gpu_total_ns FROM CUPTI_ACTIVITY_KIND_MEMSET WHERE globalPid=:g GROUP BY 1 ORDER BY gpu_total_ns DESC",
 "correlated_memcpy":f"""WITH per_api AS (
 SELECT r.rowid api_row,{NAME} api_name,e.label operation,m.copyKind copy_kind,m.bytes bytes_each,
 max(r.end-r.start) api_ns,count(*) gpu_events,sum(m.end-m.start) gpu_ns
 FROM CUPTI_ACTIVITY_KIND_MEMCPY m JOIN CUPTI_ACTIVITY_KIND_RUNTIME r
 ON m.correlationId=r.correlationId AND m.globalPid=(r.globalTid&0xFFFFFFFFFF000000)
 JOIN StringIds s ON s.id=r.nameId JOIN ENUM_CUDA_MEMCPY_OPER e ON e.id=m.copyKind
 WHERE m.globalPid=:g GROUP BY 1,2,3,4,5)
 SELECT api_name,operation,copy_kind,bytes_each,count(*) unique_api_calls,sum(gpu_events) gpu_events,
 sum(api_ns) associated_api_ns,sum(gpu_ns) gpu_total_ns FROM per_api GROUP BY 1,2,3,4 ORDER BY associated_api_ns DESC"""}
REQUIRED={"StringIds":{"id","value"},"CUPTI_ACTIVITY_KIND_RUNTIME":{"start","end","globalTid","correlationId","nameId"},
 "CUPTI_ACTIVITY_KIND_KERNEL":{"start","end","globalPid","shortName","demangledName"},
 "CUPTI_ACTIVITY_KIND_MEMCPY":{"start","end","globalPid","bytes","copyKind","correlationId"},
 "CUPTI_ACTIVITY_KIND_MEMSET":{"start","end","globalPid","bytes"},
 "ENUM_CUDA_MEMCPY_OPER":{"id","name","label"},"ProcessStreams":{"globalPid","filenameId","contentId"}}
INVALID={}
def need(q,m):
 if not q:raise RuntimeError(m)
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def text(v):
 if not isinstance(v,bytes):return v
 try:return v.decode("utf-8")
 except UnicodeDecodeError:
  escaped=v.decode("utf-8","backslashreplace");INVALID[v.hex()]=escaped;return escaped
def write(p,data):
 with Path(p).open("x",encoding="utf-8",newline="\n")as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
class Admission:
 def __init__(self,p):
  self.entry=stat(p);self.data=read(p);self.used={}
  need(self.data.get("stage")==TAG+".review_admission"and self.data.get("passed")is True and self.data.get("offline_only")is True,"One root-read offline-only admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};need(len(self.frozen)==len(self.data["inputs"]),"Duplicate input")
 def pin(self,p):
  expected=p if isinstance(p,dict)else None;path=Path(expected["path"]if expected else p).resolve();entry=stat(path)
  need(str(path)in self.frozen and entry=={k:self.frozen[str(path)][k]for k in entry},"Unadmitted/changed input: "+str(path))
  if expected:need(entry=={k:expected[k]for k in entry},"Historical stat changed: "+str(path))
  self.used[str(path)]=entry;return entry
 def finish(self):
  need(stat(self.entry["path"])==self.entry and all(stat(e["path"])==e for e in self.used.values()),"Offline input changed");return list(self.used.values())
def bindings(ad):
 for p in(Path(__file__),NOTE,T/"support/upl_tpi_p3_cost_probe_r1.py",T/"notes/upl_tpi_p3_cost_probe_r1.md",DB,REP):ad.pin(p)
 rp=L/(JOB+".run.json");ad.pin(rp);r=read(rp);ad.pin(r["call"]);call=read(r["call"]["path"])
 ad.pin(L/(JOB+".start.json"));start=read(L/(JOB+".start.json"));ad.pin(r["root_admission"]);ad.pin(call["log"])
 need(r["stage"]=="upl_tpi_p3_cost_probe_r1.run"and r["passed"]is False and r["failure"]=="Actual GPU mode/hardware/once16 fixture differs","Original failed runtime must stay failed")
 need(r["source_inputs_unchanged"]and r["consumed_stats_unchanged"],"Original frozen provenance failed for another reason")
 need(call["passed"]and all(r[k]==call[k]==0 for k in("actual_Popen_wait_exit","actual_Win32_exit","target_actual_Win32_exit")),"Three genuine exits required")
 need(call["tool_is_solver"]is False and call["tool_handle_acquired_before_wait"]and call["target_handle_acquired_while_live"],"Independent live tool/target handles absent")
 need(r["tool"]==start["tool"]==call["child"]and r["target"]==start["target"]==call["target"]and start["owner"]==call["owner"]and r["target"]["pid"]==PID,"Historical owner/target identity differs")
 need(call["program"]==r["nsys"]and r["tool"]["parent"]==call["owner"]["pid"]and r["tool"]["argv"][1:]==call["arguments"]==[*FLAGS,"--output",r["report_prefix"],r["program"]["path"],*r["arguments"]],"Actual Nsight tool command differs")
 need(start["target_ancestry"]==call["target_ancestry"]==r["target_ancestry"]and start["target_ancestry"][-1]==r["tool"],"Actual ancestry differs")
 for child,parent in zip(start["target_ancestry"],start["target_ancestry"][1:]):need(child["parent"]==parent["pid"]and parent["created"]<=child["created"]+1e-6,"Reused ancestry identity")
 for role in("target","tool"):
  identity=r[role];ticks=call[role+"_creation_FILETIME_ticks"];need(abs((ticks-116444736000000000)/1e7-identity["created"])<=1e-6,"Native creation differs")
 need(r["program"]==start["program"]==call["target_program"]and r["target"]["argv"][1:]==r["arguments"]==start["arguments"]==call["target_arguments"],"Actual program/argv differs")
 need(start["source_run"]==r["source_run"]and start["source_build"]==r["source_build"]and start["plan"]==r["plan"],"Original start/source/plan binding differs")
 need(r["actual_environment"]==start["actual_environment"]==call["actual_environment"]==call["actual_target_environment"]==start["actual_target_environment"],"Actual selector environment differs")
 for e in(r["program"],r["source_build"],r["source_prepare"],r["source_run"],r["source_plan"],r["plan"],r["nsys"],*r["runtime"],*r["seed"]):ad.pin(e)
 need(r["clock"]["completed_updates"]==2000 and r["clock"]["native_frames"]==210 and start["clock"]==r["clock"]and r["arguments"][-1]=="-nsteps:2000","Original probe scope differs")
 out=Path(r["output_directory"]);ad.pin(out/"Run.csv");ad.pin(out/"Run.out")
 with(out/"Run.csv").open(encoding="utf-8-sig",newline="")as f:rows=list(csv.DictReader(f,delimiter=";"))
 need(len(rows)==1 and int(rows[0]["Steps"])==2000 and int(rows[0]["PartFiles"])==210 and int(rows[0]["Np"])==1040 and float(rows[0]["TSimul"])==52.946587,"Actual target loop summary differs")
 need((out/"Run.out").read_text(encoding="utf-8-sig").splitlines().count("Finished execution (code=0).") ==1,"Actual target normal finish absent")
 return r,call,rows[0]
def fixture_provenance(ad,r):
 ad.pin(PTX);p=read(PTX);ad.pin(COMPILE);c=read(COMPILE);build=read(r["source_build"]["path"])
 need(p["passed"]and p["object_and_tool_stat_unchanged"]and c["passed"]and c["actual_Popen_wait_exit"]==c["actual_Win32_exit"]==0,"Actual retained CUDA compile/PTX evidence absent")
 ad.pin(p["input_object"]);ad.pin(p["actual_tool"]);ad.pin(p["call"]);tool=read(p["call"]["path"])
 for e in(c["program"],c["log"],tool["program"],tool["log"]):ad.pin(e)
 objects=[e for e in build["objects"]if Path(e["path"]).resolve()==Path(p["input_object"]["path"]).resolve()]
 need(len(objects)==1 and {k:objects[0][k]for k in("path","bytes","mtime_ns")}=={k:p["input_object"][k]for k in("path","bytes","mtime_ns")},"Unique retained CUDA object stat differs")
 need(tool["passed"]and tool["actual_Popen_wait_exit"]==tool["actual_Win32_exit"]==0 and tool["program"]==p["actual_tool"]and tool["arguments"]==["--dump-ptx",p["input_object"]["path"]]and c["arguments"][c["arguments"].index("-o")+1]==p["input_object"]["path"]and "-use_fast_math"in c["arguments"],"Actual linked CUDA compile/PTX binding differs")
 source=[Path(a)for a in c["arguments"]if Path(a).name=="JSphGpu_ker.cu"];need(len(source)==1,"Exact old NVCC source required");ad.pin(source[0]);old=source[0].with_name("upl_tpi_gpu_r1.cuh")
 current=Path(read(r["source_prepare"]["path"])["source_root"])/"upl_tpi_gpu_r1.cuh"
 ad.pin(old);ad.pin(current);raw=current.read_bytes();need(raw==old.read_bytes(),"Current fixture source differs from retained compile")
 need(all(s in raw for s in(b"SourceRoleFixtureKernelR2<<<1,32>>>",b"cudaMemcpy(&actual,eg,sizeof(actual),cudaMemcpyDeviceToHost)",b"if(actual.bits||actual.firstId!=UINT_MAX||actual.checked!=16)throw",b"SourceRoleDeviceFixturesR2();InitializeKernel")),"Original device fixture/checked16 rejection chain differs")
 return dict(retained_linked_object=p["input_object"],same_fixture_cuh=stat(current),guard_checked16_after_D2H=True,console_evidence_fabricated=False)
def query(db,sql,args=()):
 cur=db.execute(sql,args);columns=[d[0]for d in cur.description];return[{k:text(v)for k,v in zip(columns,row)}for row in cur]
def analyze(db):
 names={text(r[0])for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")};schema={}
 for table,wanted in REQUIRED.items():
  need(table in names,"Missing actual SQLite table: "+table);columns={text(r[1])for r in db.execute('PRAGMA table_info("'+table+'")')};need(wanted<=columns,"Actual SQLite columns differ: "+table);schema[table]=sorted(columns)
 need(((GPID>>24)&0xffffff)==PID,"Declared encoded PID differs")
 products={name:query(db,sql,{"g":GPID})for name,sql in SQL.items()}
 for table,condition in(("CUPTI_ACTIVITY_KIND_RUNTIME","(globalTid&0xFFFFFFFFFF000000)=?"),("CUPTI_ACTIVITY_KIND_KERNEL","globalPid=?"),("CUPTI_ACTIVITY_KIND_MEMCPY","globalPid=?"),("CUPTI_ACTIVITY_KIND_MEMSET","globalPid=?")):
  n,bad=db.execute("SELECT count(*),sum(end<start OR start IS NULL OR end IS NULL) FROM "+table+" WHERE "+condition,(GPID,)).fetchone();need(n>0 and not bad,"Missing/invalid actual target events: "+table)
 api={r["name"]:r for r in products["api"]}
 for name,n,duration in(("cudaMemcpy",456300,33779186856),("cudaLaunchKernel",723944,5072882843)):need(api[name]["calls"]==n and api[name]["total_ns"]==duration,"Previously observed target API aggregate differs: "+name)
 fixture=[r for r in products["kernels"]if r["name"].rsplit("::",1)[-1]=="SourceRoleFixtureKernelR2"];need(len(fixture)==1 and fixture[0]["instances"]==1 and fixture[0]["total_ns"]==1312,"Actual captured fixture kernel differs")
 streams=query(db,"SELECT p.globalPid,p.filenameId,p.contentId,f.value filename,c.value content FROM ProcessStreams p LEFT JOIN StringIds f ON f.id=p.filenameId LEFT JOIN StringIds c ON c.id=p.contentId WHERE p.globalPid=?",(GPID,))
 for row in streams:row.update(content_is_null=row["content"]is None,content_length=None if row["content"]is None else len(row["content"]),console_fixture_markers=None if row["content"]is None else row["content"].count(FIXTURE))
 expected_files={"stdout_0d7f-0e32-4266-cdf8.log","stderr_0d7f-0e32-4266-cdf8.log"}
 need(len(streams)==2 and {Path(r["filename"]).name for r in streams}==expected_files,"Actual target must have exactly its stdout/stderr pair")
 need(all(Path(r["filename"]).parent.name=="streams"and Path(r["filename"]).parent.parent.name=="quadd_session_1029272"and r["contentId"]==13 and r["content"]in(None,"")for r in streams),"Target stream scope/empty-content evidence changed")
 returns=dict(returnValue_available="returnValue"in schema["CUPTI_ACTIVITY_KIND_RUNTIME"],nonzero_return_does_not_always_mean_failure=True)
 if returns["returnValue_available"]:
  products["nonzero_returns"]=query(db,f"SELECT {NAME} name,r.returnValue,count(*) calls FROM CUPTI_ACTIVITY_KIND_RUNTIME r JOIN StringIds s ON s.id=r.nameId WHERE (r.globalTid&0xFFFFFFFFFF000000)=:g AND r.returnValue IS NOT NULL AND r.returnValue<>0 GROUP BY 1,2",{"g":GPID})
  returns["nonzero_calls"]=sum(r["calls"]for r in products["nonzero_returns"])
  status_APIs={"cudaMemcpy","cudaMemcpyAsync","cudaMemset","cudaMemsetAsync","cudaMalloc","cudaFree","cudaLaunchKernel","cudaDeviceSynchronize","cudaStreamSynchronize","cudaEventSynchronize"}
  returns["nonzero_known_cudaError_t_calls"]=sum(r["calls"]for r in products["nonzero_returns"]if r["name"]in status_APIs and isinstance(r["returnValue"],int)and r["returnValue"]!=0)
  returns["known_cudaError_t_API_names"]=sorted(status_APIs)
 else:returns.update(nonzero_calls=None,API_return_failure_count_unavailable=True)
 allowed_metadata=("TARGET_INFO_GPU","TARGET_INFO_SESSION_START_TIME","META_DATA_CAPTURE","META_DATA_EXPORT")
 metadata={n:query(db,'SELECT * FROM "'+n+'" LIMIT 16')for n in allowed_metadata if n in names}
 return products,dict(schema=schema,target_globalPid=GPID,target_PID=PID,fixture_kernel=fixture[0],process_streams=streams,non_target_ProcessStreams_content_read=False,console_observation_available=False,API_returns=returns,GPU_session_metadata_first16=metadata,metadata_whitelist_missing=[n for n in allowed_metadata if n not in names],correlation_api_time_not_additive_across_byte_groups=True)
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args();need(a.execution_authorized,"Root full-read offline authorization required")
 need(not OUT.exists()and not CHECK.exists(),"Existing/partial review protected");ad=None;result=dict(stage=TAG,passed=False,performance_evidence_valid=False,origin_runtime_failed=True,origin_receipt_rewritten=False,fixture_console_observation_available=False,physical_acceptance=False,native_acceptance=False,solver_invocations=0,reader_invocations=0,tool_invocations=0,build_invocations=0,SHA_scans=0,automatic_follow_up=False)
 try:
  ad=Admission(a.admission);result["root_admission"]=ad.entry;r,call,run=bindings(ad);proof=fixture_provenance(ad,r)
  with closing(sqlite3.connect(DB.resolve().as_uri()+"?mode=ro&immutable=1",uri=True))as db:
   db.text_factory=bytes;db.execute("PRAGMA query_only=ON");products,metrics=analyze(db)
  ad.finish();OUT.mkdir()
  for name,rows in products.items():
   if rows:
    with(OUT/(name+".csv")).open("x",encoding="utf-8",newline="")as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  diagnostics=[line for line in text(Path(call["log"]["path"]).read_bytes()).splitlines()if "ERROR"in line or "UTF8"in line or "UTF-8"in line]
  metrics.update(origin_failure=r["failure"],original_run_passed=False,independent_fixture_kernel_code_exit_evidence=proof,target_TSimul_s=float(run["TSimul"]),tool_wall_including_profile_exports_s=call["wall_seconds_including_profile_and_exports"],original_Nsight_diagnostic_lines=diagnostics,invalid_utf8_escaped_with_original_hex=INVALID,API_GPU_duration_sums_must_not_be_added=True,percent_of_application_walltime_claimed=False,probe_save_density_not_full_cycle_representative=True,all22_native_verified=False)
  write(OUT/"metrics.json",metrics);result.update(passed=True,performance_evidence_valid=True,original_full_runtime_postcheck_not_relabelled=True,fixture_observation_is_kernel_code_exit_not_console=True,products=[stat(p)for p in OUT.iterdir()if p.is_file()],consumed=ad.finish(),consumed_stats_unchanged=True)
 except Exception as exc:result.update(first_failure=str(exc),partials_preserved=True);raise
 finally:write(CHECK,result)
 print(str(CHECK))
if __name__=="__main__":main()
