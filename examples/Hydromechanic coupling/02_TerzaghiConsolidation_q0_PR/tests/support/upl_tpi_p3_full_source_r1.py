"""Freeze the single-qualifier private P3 full-scope candidate; never build or run."""
from __future__ import annotations
import argparse,difflib,inspect
from pathlib import Path
import upl_tpi_p3_source_r1 as prior

T,L=prior.T,prior.L
TAG="upl_tpi_p3_full_source_r1";NOTE=T/"notes"/(TAG+".md")
need,stat,read,same,write=prior.need,prior.stat,prior.read,prior.same,prior.write
BASE={"CPU":(267,"JSphCpu",("DebugCPU","ReleaseCPU")),"GPU":(270,"JSphGpu",("Debug","Release"))}
FULL_TIME=72.88428690075874;FULL_CAP=7288262

class Admission:
 def __init__(self,path,backend):
  self.entry,self.data=stat(path),read(path);self.used={}
  need(self.data.get("stage")==TAG+".prepare_admission" and self.data.get("passed")is True and self.data.get("prepare_only")is True and self.data.get("backend")==backend,"One exact source-only root admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
 def pin(self,path):
  key=str(Path(path).resolve());need(key in self.frozen,"Unadmitted full-scope source input: "+key);self.used[key]=same(self.frozen[key]);return self.used[key]
 def finish(self):
  same(self.entry)
  for e in self.used.values():same(e)
  return list(self.used.values())

def patch(raw,backend):
 """Only extend the true M0 arm; retain the <=2 and non-M0 arms verbatim."""
 nl="\r\n"if b"\r\n"in raw else"\n";text=raw.decode("utf8").replace("\r\n","\n")
 ns="upl_tpi_cpu_r1"if backend=="CPU"else"upl_tpi_gpu_r1"
 before="(upl_tpi_m0_dt_r2::Enabled("+ns+"::Enabled())?TimeMax<=2.:"
 after="(upl_tpi_m0_dt_r2::Enabled("+ns+"::Enabled())?(TimeMax<=2. || (TimeMax==72.88428690075874 && NstepsBreak==7288262)):"
 need(text.count(before)==1,"Unique original P3 M0 time qualifier required")
 result=text.replace(before,after,1)
 need(result.replace(after,before,1)==text,"Only one time-domain expression may change")
 if backend=="GPU":
  legacy="(TimeMax<=.15 || (TimeMax==72.88428690075874 && NstepsBreak==11661219))"
  need(text.count(legacy)==result.count(legacy)==1,"Original non-M0 11661219 arm must remain exact")
 return result.replace("\n",nl).encode("utf8")

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--backend",choices=BASE,required=True);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args()
 need(a.execution_authorized,"Root full-read source-only authorization required");backend=a.backend;ad=Admission(a.admission,backend)
 label="upl_tpi_p3_full_"+backend+"_r1";out=T/"outputs"/(label+"_source");receipt=L/(label+".prepare.json");diff=L/(label+".source.diff")
 need(not any(p.exists()for p in(out,receipt,diff)),"Existing source/failure/partial protected")
 result=dict(stage=TAG+".prepare",backend=backend,passed=False,root_admission=ad.entry,build_invocations=0,solver_invocations=0,reader_invocations=0,SHA_scans=0,physical_acceptance=False)
 try:
  count,cls,cfgs=BASE[backend];single=cls+"Single.cpp"
  author_paths=[Path(__file__),NOTE,Path(prior.__file__)]
  author_paths.extend(Path(inspect.getmodule(f).__file__)for f in(need,stat,read,same,write))
  authors=[ad.pin(p)for p in dict.fromkeys(author_paths)]
  pe=ad.pin(L/("upl_tpi_p3_"+backend+"_r1.prepare.json"));base=read(pe["path"])
  need(base.get("stage")=="upl_tpi_p3_source_r1.prepare"and base.get("passed")is True and base["backend"]==backend and base.get("consumed_stats_unchanged")is True and base.get("endpoint_defect_rounds")==3 and base.get("actual_full_forces_per_update")==5,"Actual passed P3 source parent required")
  builds=[]
  for cfg in cfgs:
   e=ad.pin(L/("upl_tpi_p3_"+cfg+"_r1.build.json"));d=read(e["path"])
   need(d.get("stage")=="upl_tpi_p3_build_r1"and d.get("passed")is True and d.get("configuration")==cfg and d.get("source_prepare")==pe and d.get("object_count")== (86 if backend=="CPU"else 111),"Actual same-source P3 configuration build required")
   builds.append(e)
  root=Path(base["source_root"]).resolve();need(root==(T/"outputs"/("upl_tpi_p3_"+backend+"_r1_source")).resolve()and len(base["files"])==count,"Exact original source inventory required")
  raw={};originals={}
  for e in base["files"]:
   q=ad.pin(e["path"]);same(e);p=Path(q["path"]);need(p.parent==root and p.name not in raw,"Flat unique P3 source required");raw[p.name]=p.read_bytes();originals[p.name]=q
  need(single in raw,"Original Single TU missing");new=dict(raw);new[single]=patch(raw[single],backend)
  need(all(new[n]==v for n,v in raw.items()if n!=single),"Any change outside the Single qualifier is forbidden")
  ad.finish();out.mkdir();files=[];pairs=[]
  for name,data in new.items():
   p=out/name
   with p.open("xb")as f:f.write(data)
   e=stat(p);files.append(e);pairs.append(dict(original=originals[name],pinned_snapshot=e))
  with diff.open("x",encoding="utf8",newline="\n")as f:
   f.writelines(difflib.unified_diff(raw[single].decode("utf8").splitlines(True),new[single].decode("utf8").splitlines(True),fromfile="frozen_P3/"+single,tofile="private_P3_full/"+single))
  result.update(passed=True,source_root=str(out.resolve()),base_prepare=pe,base_builds=builds,base_source_entries=pairs,files=files,source_diff=stat(diff),changed_sources=[single],recompile_sources=[single],changed_headers=[],other_base_files_byte_identical=True,CUDA_source_and_cuh_byte_identical=True,all_headers_and_helpers_byte_identical=True,shared_device_structures_or_inline_tokens_changed=False,public_class_or_virtual_ABI_changed=False,numerical_formula_changed=False,original_short_M0_TimeMax_le_2_expression_retained=True,non_M0_time_arm_retained=True,only_M0_qualification_time_domain_extended=True,full_scope=dict(TimeMax=FULL_TIME,NstepsBreak=FULL_CAP,dt_event_divisor=1000,required_scheme="B",required_endpoint_defect_rounds=3,scheme_and_dt_enforced_by_unchanged_P3_helpers=True),short_regression_pending=True,full_cycle_acceptance=False,author_files=authors,consumed=ad.finish(),consumed_stats_unchanged=True)
 except Exception as exc:result.update(first_failure=str(exc),partials_preserved=True);raise
 finally:write(receipt,result)
 print(receipt)
if __name__=="__main__":main()
