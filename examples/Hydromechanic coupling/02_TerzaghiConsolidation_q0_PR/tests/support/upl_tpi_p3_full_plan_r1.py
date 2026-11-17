"""Prepare one fresh P3 full diagnostic input/actual clock only; launch no program."""
from __future__ import annotations
import argparse,csv,json,shutil,struct,sys,xml.etree.ElementTree as ET
from pathlib import Path
sys.dont_write_bytecode=True
import upl_tpi_cpu_run_r1 as c
T,L=c.T,c.L;TAG="upl_tpi_p3_full_plan_r1";SCRIPT=Path(__file__).resolve();NOTE=T/"notes"/(TAG+".md")
BASE_RUN=L/"upl_tpi_m0_dt_B10us_window2s_GPU_r1.run.json"
TIMEOUT_SOURCE=T/"outputs/upl_tpi_p3_GPU_r1_source/JDsOutputTime.cpp"
CONFIG=T/"configs/upl_tpi_p3_full_r1.xml";SEED=T/"outputs/upl_tpi_p3_full_r1_seed";PREFIX=SEED/"upl_bigstep_2tv_CPU1_r1"
PLAN=L/(TAG+".clock.csv");CHECK=L/(TAG+".prepare.json")
CAP=72.88428690075874;DT=1.0000228881835938e-5;STEPS=7288262;FRAMES=1653;END=72.88428815806371;EVENT=.0100002288818359375
HEADER=["part","completed_steps","saved_step","time_s","dt_s","post_open_by_completed_step","target_time_s","forced_final"]
SEGMENTS=[(0.,2.**-13),(.009765625,2.**-19),(.01025390625,2.**-13),(.0250244140625,2.**-9),(2.0000457763671875,.18218571428571428)]
def bits(v):return struct.pack("<d",float(v))
class Admission:
 def __init__(self,path):
  self.entry,self.data=c.stat(path),c.read(path);self.used={}
  c.need(self.data.get("stage")==TAG+".prepare_admission"and self.data.get("passed")is True and self.data.get("prepare_only")is True,"One root-reviewed input/clock-only admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};c.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
  for p in(SCRIPT,NOTE,Path(c.__file__),c.NOTE,BASE_RUN,TIMEOUT_SOURCE):self.pin(p)
 def pin(self,path):
  key=str(Path(path).resolve());c.need(key in self.frozen,"Unadmitted input: "+key);self.used[key]=c.same(self.frozen[key]);return self.used[key]
 def finish(self):
  for e in self.used.values():c.same(e)
  c.same(self.entry);return list(self.used.values())
def next_time(t,segments):
 # Literal arithmetic/branch order of frozen JDsOutputTime::GetNextTime (157-185).
 base=0
 while base+1<len(segments)and t>=segments[base+1][0]:base+=1
 anchor,interval=segments[base];following=segments[base+1][0]if base+1<len(segments)else sys.float_info.max
 if t<anchor:return anchor
 count=int((t-anchor)/interval);target=anchor+interval*count
 while target<=t:target=anchor+interval*count;count+=1
 return min(target,following)
def actual_plan(segments):
 time=0.;target=next_time(0.,segments);rows=[dict(zip(HEADER,(0,0,0,0.,DT,0,0.,0)))];before=0.
 for completed in range(1,STEPS+1):
  before=time;time+=DT;ordinary=time>=target;stop=time>=CAP or completed==STEPS
  if ordinary or stop:
   rows.append(dict(zip(HEADER,(len(rows),completed,completed-1,time,DT,int(completed>1000),target,int(stop and not ordinary)))))
   target=next_time(time,segments)
  if stop:break
 c.need(completed==STEPS and len(rows)==FRAMES and bits(time)==bits(END)and before<CAP<=time and rows[-1]["forced_final"]==1,"Exact full scalar cap/first-crossing/count differs")
 c.need(sum(r["post_open_by_completed_step"]for r in rows)==1549 and rows[103]["completed_steps"]==1000 and rows[104]["completed_steps"]==1001,"True preopen/postopen coverage differs")
 c.need(rows[1262]["completed_steps"]==200000 and bits(rows[1262]["time_s"])==bits(2.0000457763714676)and rows[1262]["forced_final"]==0,"Original timeout-boundary crossing differs")
 return rows

def compare_old_plan(ad,entry,rows):
 ad.pin(entry["path"]);c.same(entry)
 with Path(entry["path"]).open(encoding="utf-8-sig",newline="")as f:
  reader=csv.DictReader(f);old=list(reader);c.need(reader.fieldnames==HEADER and len(old)==1263,"Exact retained eight-column window plan required")
 def equal(a,b):
  return all(int(a[k])==int(b[k])for k in(HEADER[0],HEADER[1],HEADER[2],HEADER[5],HEADER[7]))and all(bits(a[k])==bits(b[k])for k in(HEADER[3],HEADER[4],HEADER[6]))
 shared=[i for i,(a,b)in enumerate(zip(old,rows))if equal(a,b)]
 c.need(shared==list(range(1262))and int(old[-1]["completed_steps"])==199996 and bits(old[-1]["time_s"])==bits(2.00000577545594)and int(old[-1]["forced_final"])==1 and not equal(old[-1],rows[1262]),"Real shared plan prefix or old forced-final distinction differs")
 return dict(source_plan=entry,actual_clock_step_all8_field_shared_records=1262,first_shared_index=0,last_shared_index=1261,old_forced_final_not_shared=True,old_final=dict(old[-1]),new_part1262=rows[1262],native_byte_proof_performed=False,headers_or_old_rows_rewritten=False)

def prepare(ad,result):
 c.need(not any(p.exists()for p in(CONFIG,SEED,PLAN)),"Existing/partial input/clock outputs protected")
 run=c.read(BASE_RUN);c.need(run.get("stage")=="upl_tpi_m0_dt_run_r2.run"and run.get("passed")is True and(run["configuration"],run["scheme"],run["mode"])==("Release","B","window2s"),"Exact retained genuine B10us window input source required")
 c.need(run["clock"]["completed_updates"]==199996 and run["clock"]["native_frames"]==1263 and bits(run["clock"]["actual_fixed_dt_s"])==bits(DT)and run["PART_restart"]is False,"Retained source profile differs")
 expected=T/"outputs/upl_tpi_m0_dt_B10us_window2s_GPU_r1_seed/upl_bigstep_2tv_CPU1_r1"
 source=run["seed"];c.need(len(source)==3 and [Path(e["path"]).resolve()for e in source]==[Path(str(expected)+x).resolve()for x in(".xml",".bi4","_Normals.nbi4")],"Exact original generated seed tuple required")
 for e in source:ad.pin(e["path"]);c.same(e)
 original=Path(source[0]["path"]).read_bytes();old=b'<parameter key="TimeMax" value="2.0"';new=b'<parameter key="TimeMax" value="72.88428690075874"'
 c.need(original.count(old)==1,"Unique original TimeMax=2.0 byte token required");changed=original.replace(old,new,1)
 c.need(changed.replace(new,old,1)==original and changed.count(new)==1,"XML changed beyond the sole TimeMax token")
 root=ET.fromstring(changed);params={x.get("key"):x.get("value")for x in root.iter("parameter")};timeouts=root.findall(".//timeout")
 c.need(len(timeouts)==1 and timeouts[0].get("active")=="true","One original active timeout policy required")
 segments=[(float(x.get("time")),float(x.get("timeout")))for x in timeouts[0].findall("tout")]
 c.need(segments==SEGMENTS and bits(float(params["DtFixed"]))==bits(DT)==bits(float(params["DtIni"]))and bits(float(params["TimeMax"]))==bits(CAP)and float(params["TimeOut"])==.18218571428571428,"Original dt/output policy or exact full cap differs")
 c.need(bits(float(next(root.iter("HydroMechDrainageStartTime")).get("value")))==bits(EVENT)and bits(float(next(root.iter("HydroMechTopLoadRampTime")).get("value")))==bits(EVENT)and bits(DT)==bits(EVENT/1000.),"Original ramp/drain/fixed grid differs")
 rows=actual_plan(segments);shared=compare_old_plan(ad,run["plan"],rows)
 counters=dict(completed_updates=STEPS,endpoint_calls_and_writes=3*STEPS,provisional_validations_and_transitions=2*STEPS,core_field_bit_checks=21000*STEPS,HG_readonly_snapshot_checks=6000*STEPS,physical_HG_force_and_rate_calls=2*STEPS,five_force_phase_total=5*STEPS,pressure_saved_records_per_round=1000*FRAMES,pressure_saved_records_all3_rounds=3000*FRAMES)
 c.need(STEPS-1<2**32 and max(counters.values())<2**53 and max(counters.values())<2**64,"Original Step/64-bit counters are insufficient")
 ad.finish();SEED.mkdir() # Exclusive new directory, never a delete/reuse path.
 for path,data in[(CONFIG,changed),(Path(str(PREFIX)+".xml"),changed)]:
  with path.open("xb")as f:f.write(data)
 for e,suffix in zip(source[1:],(".bi4","_Normals.nbi4")):
  destination=Path(str(PREFIX)+suffix)
  with Path(e["path"]).open("rb")as src,destination.open("xb")as dst:shutil.copyfileobj(src,dst)
  c.need(destination.read_bytes()==Path(e["path"]).read_bytes(),"Copied small generated seed bytes differ")
 with PLAN.open("x",encoding="utf-8",newline="")as f:
  writer=csv.DictWriter(f,fieldnames=HEADER);writer.writeheader();writer.writerows(rows)
 c.need(CONFIG.read_bytes()==changed==Path(str(PREFIX)+".xml").read_bytes(),"Written input XML differs from sole-token patch")
 cv=(1e-4*(2e6*(1.-.3)/((1.+.3)*(1.-2.*.3))))/(1000.*9.81)
 result.update(passed=True,source_window_run=c.stat(BASE_RUN),source_seed=source,original_output_time_implementation=ad.pin(TIMEOUT_SOURCE),config=c.stat(CONFIG),input_prefix=str(PREFIX),seed=[c.stat(Path(str(PREFIX)+x))for x in(".xml",".bi4","_Normals.nbi4")],plan=c.stat(PLAN),clock=dict(method="binary64 scalar +=dt; original output-target operation order",actual_fixed_dt_s=DT,actual_scalar_end_s=END,completed_updates=STEPS,native_frames=FRAMES,runtime_TimeMax_s=CAP,nsteps_upper_cap=STEPS,event_completed_step=1000,event_step_is_preopen=True,first_post_open_completed_step=1001,event_part=103,first_post_part=104,post_open_frames=1549,expected_true_drained_receivers=15490,n_times_dt_clock_used=False,actual_native_review_pending=True),shared_window_plan=shared,timeout_segments=segments,XML_only_TimeMax_value_changed=True,XML_comments_and_all_other_bytes_retained=True,small_generated_binary_seed_bytes_equal=True,expected_64bit_lifecycles=counters,reference=dict(legacy_Cv_M0_m2_s=cv,unfitted_2Tv_target_s=EVENT+2./cv,actual_end_legacy_Tv=(END-EVENT)*cv,finite_Kw_A_has_own_reference=True,reference_not_exact_ramp_band_inertial_currentJ_solution=True),source_full_completed=False,solver_qualifier_still_requires_separate_review=True,consumed=ad.finish(),consumed_stats_unchanged=True)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args()
 c.need(a.execution_authorized,"Root-reviewed input-only execution flag required");c.need(not CHECK.exists(),"Existing preparation receipt/failure protected");ad=Admission(a.admission)
 result=dict(stage=TAG+".prepare",passed=False,root_admission=ad.entry,prepare_only=True,solver_invocations=0,GenCase_invocations=0,program_invocations=0,build_invocations=0,native_invocations=0,VTK_invocations=0,Git_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_follow_up=False)
 try:prepare(ad,result)
 except Exception as exc:result.update(first_error=str(exc),partials_preserved=True,consumed=list(ad.used.values()))
 c.write_new(CHECK,result);print(json.dumps(dict(passed=result["passed"],receipt=str(CHECK),first_error=result.get("first_error")),ensure_ascii=False));return 0 if result["passed"]else 1
if __name__=="__main__":raise SystemExit(main())
