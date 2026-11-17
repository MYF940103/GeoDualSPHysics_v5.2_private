"""Freeze one private P3 source from the actual P2 parent; no build or execution."""
from __future__ import annotations
import argparse,difflib,inspect,re
from pathlib import Path
import upl_tpi_p2_r1_prepare as old
T,L=old.T,old.L
TAG="upl_tpi_p3_source_r1";NOTE=T/"notes"/(TAG+".md")
need,stat,read,same,write=old.need,old.stat,old.read,old.same,old.write_json
BASE={"CPU":("upl_tpi_p2_CPU_r1.prepare.json","upl_tpi_p2_DebugCPU_r1.build.json",267),"GPU":("upl_tpi_p2_GPU_r2.prepare.json","upl_tpi_p2_Debug_r1.build.json",270)}

class Admission:
 def __init__(self,p,backend):
  self.entry,self.data=stat(p),read(p);self.used={}
  need(self.data.get("stage")==TAG+".prepare_admission"and self.data.get("passed")is True and self.data.get("prepare_only")is True and self.data.get("backend")==backend,"One source-only root admission required")
  self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};need(len(self.frozen)==len(self.data["inputs"]),"Duplicate input")
 def pin(self,p):
  key=str(Path(p).resolve());need(key in self.frozen,"Unadmitted P3 source: "+key);self.used[key]=same(self.frozen[key]);return self.used[key]
 def finish(self):
  for e in self.used.values():same(e)
  same(self.entry);return list(self.used.values())

def next_block(backend):
 text=old.cpu_block()if backend=="CPU"else old.gpu_block()
 text=old.old.once(text,"round<2","round<3")
 text=old.old.once(text,"::SecondEndpoint(","::NextEndpoint(")
 text=old.old.once(text,"P2 endpoint fixed dt changed","P3 endpoint fixed dt changed")
 if backend=="CPU":
  text=old.old.once(text,"if(round){upl_tpi_cpu_r1::state.endpoint=false;upl_tpi_cpu_r1::state.temporary=false;}","if(round==2){upl_tpi_cpu_r1::state.endpoint=false;upl_tpi_cpu_r1::state.temporary=false;}")
  text=old.old.once(text,"if(!round)upl_tpi_cpu_r1::ValidateFirstEndpoint(","if(round<2)upl_tpi_cpu_r1::ValidateProvisionalEndpoint(")
 else:text=old.old.once(text,"if(!round)upl_tpi_gpu_r1::ValidateFirstEndpoint(","if(round<2)upl_tpi_gpu_r1::ValidateProvisionalEndpoint(")
 return text

def patch(raw,backend):
 newline="\r\n"if b"\r\n"in raw else"\n";text=raw.decode("utf8").replace("\r\n","\n")
 before=old.cpu_block()if backend=="CPU"else old.gpu_block();text=old.old.once(text,before,next_block(backend))
 banner=next(x for x in text.splitlines()if 'Log->Print("UplTpiP2'+backend+'R1:'in x)
 text=old.old.once(text,banner,'    Log->Print("UplTpiP3'+backend+'R1: private three complete endpoint defects, one solid/J/HG/history commit; original source clock; not LF/implicit/second-order/restart/physics acceptance.");')
 return text.replace("\n",newline).encode("utf8")

def device_prefix(header,label):
 split=b"#ifdef UPL_TPI_GPU_R1_IMPLEMENTATION";need(header.count(split)==1,"Unique GPU implementation marker required");prefix=header.split(split,1)[0]
 a=list(re.finditer(rb"// "+label.encode()+rb"_HOST_API_R1_BEGIN\r?\n",prefix));z=list(re.finditer(rb"// "+label.encode()+rb"_HOST_API_R1_END\r?\n",prefix))
 need(len(a)==len(z)==1 and a[0].end()<z[0].start(),"Unique host-only API block required")
 block=prefix[a[0].start():z[0].end()].replace(b"\r\n",b"\n")
 need(block.count(b"#ifndef __CUDACC__\n")==1 and block.count(b"#endif\n")==1 and block.count(b"#if")==1,"All new API declarations must be excluded from CUDA")
 return prefix[:a[0].start()]+prefix[z[0].end():]

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--backend",choices=BASE,required=True);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args()
 need(a.execution_authorized,"Root full-read source-only authorization required");backend=a.backend;ad=Admission(a.admission,backend)
 label="upl_tpi_p3_"+backend+"_r1";out=T/"outputs"/(label+"_source");receipt=L/(label+".prepare.json");diff=L/(label+".source.diff")
 need(not out.exists()and not receipt.exists()and not diff.exists(),"Existing source/failure/partial protected")
 result=dict(stage=TAG+".prepare",backend=backend,passed=False,root_admission=ad.entry,build_invocations=0,solver_invocations=0,reader_invocations=0,SHA_scans=0,physical_acceptance=False)
 try:
  helper="upl_tpi_cpu_r1.h"if backend=="CPU"else"upl_tpi_gpu_r1.h";cls="JSphCpu"if backend=="CPU"else"JSphGpu"
  author_paths=[Path(__file__),NOTE,Path(old.__file__),Path(old.old.__file__)]
  author_paths.extend(Path(inspect.getmodule(f).__file__)for f in(need,stat,read,same,write,old.old.once))
  authors=[ad.pin(p)for p in dict.fromkeys(author_paths)]
  replacements={helper:T/"support"/("upl_tpi_p3_"+backend.lower()+"_r1.h"),"upl_tpi_m0_dt_r2.h":T/"support"/"upl_tpi_p3_dt_r1.h"}
  for p in replacements.values():authors.append(ad.pin(p))
  notes=["upl_tpi_p3_"+backend.lower()+"_r1.md","upl_tpi_p3_dt_r1.md","upl_tpi_p3_reuse_contract_r1.md","upl_tpi_p3_time_options_r1.md"]
  if backend=="GPU":notes.append("upl_tpi_p3_host_reuse_contract_r1.md")
  for name in notes:authors.append(ad.pin(T/"notes"/name))
  for name in("upl_tpi_p3_time_options_r1.check.json","upl_tpi_p2_error_sources_r1.check.json","upl_tpi_p2_window_root_r1.review.json"):
   e=ad.pin(L/name);d=read(e["path"])
   if name.startswith("upl_tpi_p3_time"):need(d.get("passed")is True and d.get("algebra_complete")is True,"Reviewed P3 algebra required")
   elif name.startswith("upl_tpi_p2_error"):need(d.get("passed")is True and d.get("original_budget_results_unchanged")is True,"Reviewed offline error split required")
   else:need(d.get("analysis_and_root_visual_review_complete")is True and d.get("physical_or_full_cycle_acceptance")is False,"Preserved P2 outcome required")
  pp,bp,count=BASE[backend];pe,be=ad.pin(L/pp),ad.pin(L/bp);base,built=read(pe["path"]),read(be["path"])
  expected="upl_tpi_p2_r1.prepare"if backend=="CPU"else"upl_tpi_p2_gpu_prepare_r2.prepare"
  need(base.get("stage")==expected and base.get("passed")is True and base["backend"]==backend and base.get("endpoint_defect_rounds")==2 and built.get("passed")is True and built.get("stage")=="upl_tpi_p2_build_r1"and built["source_prepare"]==pe,"Actual P2 source/build binding required")
  root=Path(base["source_root"]).resolve();need(len(base["files"])==count,"Original source inventory differs");raw={};originals=[]
  for e in base["files"]:
   q=ad.pin(e["path"]);same(e);p=Path(q["path"]);need(p.parent==root and p.name not in raw,"Flat P2 source identity differs");raw[p.name]=p.read_bytes();originals.append(q)
  new=dict(raw);changed=[cls+"Single.cpp"];new[changed[0]]=patch(raw[changed[0]],backend)
  for name,p in replacements.items():need(name in raw,"Missing original helper");new[name]=p.read_bytes()
  prefix=None
  if backend=="GPU":
   before=device_prefix(raw[helper],"P2");after=device_prefix(new[helper],"P3");need(before==after and len(after)==3850,"Original device-visible prefix changed");prefix=len(after)
  modified=set(changed)|set(replacements);need(all(new[n]==v for n,v in raw.items()if n not in modified),"Unrelated source changed")
  need(new[cls+".cpp"]==raw[cls+".cpp"],"Original endpoint phase selection host must remain exact")
  ad.finish();out.mkdir();files=[];pairs=[];lines=[]
  for name,data in new.items():
   p=out/name
   with p.open("xb")as f:f.write(data)
   e=stat(p);files.append(e);pairs.append(dict(original=next(x for x in originals if Path(x["path"]).name==name),pinned_snapshot=e))
   if name in modified:lines.extend(difflib.unified_diff(raw[name].decode("utf8").splitlines(True),data.decode("utf8").splitlines(True),fromfile="frozen_P2/"+name,tofile="private_P3/"+name))
  with diff.open("x",encoding="utf8",newline="\n")as f:f.writelines(lines)
  result.update(passed=True,source_root=str(out.resolve()),base_prepare=pe,base_build=be,base_source_entries=pairs,files=files,source_diff=stat(diff),changed_sources=changed,recompile_sources=[cls+".cpp",cls+"Single.cpp"],changed_headers=list(replacements),other_base_files_byte_identical=True,spatial_operator_sources_byte_identical=True,CUDA_source_and_cuh_byte_identical=True,five_phase_original_bound_arithmetic_retained=True,material_J_HG_update_order_retained=True,old_source_clock_retained=True,public_class_or_virtual_ABI_changed=False,shared_device_structures_or_inline_tokens_changed=False,GPU_original_prefix_bytes_after_removing_host_only_block=prefix,endpoint_defect_rounds=3,actual_full_forces_per_update=5,public_source_changed=False,default_A_native_regression_pending=True,author_files=authors,consumed=ad.finish(),consumed_stats_unchanged=True)
 except Exception as exc:result.update(first_failure=str(exc),partials_preserved=True);raise
 finally:write(receipt,result)
 print(receipt)
if __name__=="__main__":main()
