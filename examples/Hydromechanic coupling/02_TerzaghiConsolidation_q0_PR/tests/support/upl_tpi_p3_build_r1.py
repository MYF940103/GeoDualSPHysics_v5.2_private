"""One private P3 host-only build; reuse actual passed P2 recipes, never run a program."""
from __future__ import annotations
import argparse,os,shutil,tempfile
from pathlib import Path
import upl_tpi_p2_build_r1 as old
b,g,T,L,S=old.b,old.g,old.T,old.L,old.S
TAG="upl_tpi_p3_build_r1";NOTE=T/"notes"/(TAG+".md")
CONFIG={k:(v[0],v[1],v[4])for k,v in old.CONFIG.items()}

class Admission:
 def __init__(self,path,cfg):
  self.entry,self.data=b.stat(path),b.read(path);self.used={}
  b.need(self.data.get("stage")==TAG+".build_admission"and self.data.get("passed")is True and self.data.get("build_only")is True and self.data.get("configuration")==cfg,"One exact private build admission required")
  self.frozen={g.key(e["path"]):e for e in self.data["inputs"]};b.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate build input")
 def pin(self,p):
  key=g.key(p);b.need(key in self.frozen,"Unadmitted P3 build input: "+str(p));self.used[key]=b.same(self.frozen[key]);return self.used[key]
 def finish(self):
  b.same(self.entry)
  for e in self.used.values():b.same(e)
  return list(self.used.values())

def context(ad,cfg,create=True):
 backend,count,exe=CONFIG[cfg];cls="JSphCpu"if backend=="CPU"else"JSphGpu";names=[cls+".cpp",cls+"Single.cpp"]
 helper="upl_tpi_cpu_r1.h"if backend=="CPU"else"upl_tpi_gpu_r1.h"
 pp=L/("upl_tpi_p3_"+backend+"_r1.prepare.json");bp=L/("upl_tpi_p2_"+cfg+"_r1.build.json")
 for p in(Path(__file__),NOTE,Path(old.__file__),old.NOTE,Path(b.__file__),Path(g.__file__),g.VCVARS,pp,bp):ad.pin(p)
 prep,base=b.read(pp),b.read(bp)
 b.need(prep.get("stage")=="upl_tpi_p3_source_r1.prepare"and prep.get("passed")is True and prep["backend"]==backend and prep.get("consumed_stats_unchanged")is True and prep.get("endpoint_defect_rounds")==3 and prep.get("actual_full_forces_per_update")==5,"Actual P3 source preparation required")
 for k in("other_base_files_byte_identical","spatial_operator_sources_byte_identical","CUDA_source_and_cuh_byte_identical","five_phase_original_bound_arithmetic_retained","material_J_HG_update_order_retained","old_source_clock_retained"):b.need(prep.get(k)is True,"P3 source closure failed: "+k)
 b.need(prep.get("public_class_or_virtual_ABI_changed")is False and prep.get("shared_device_structures_or_inline_tokens_changed")is False,"P3 changed shared ABI")
 b.need(base.get("stage")==old.TAG and base.get("passed")is True and base["configuration"]==cfg and base.get("consumed_stats_unchanged")is True,"Genuine passed P2 same-configuration build required")
 source=Path(prep["source_root"]).resolve();b.need(source==(T/"outputs"/("upl_tpi_p3_"+backend+"_r1_source")).resolve(),"Unexpected P3 source root")
 files={Path(e["path"]).name:e for e in prep["files"]}
 b.need(len(files)==len(prep["files"])==(267 if backend=="CPU"else 270) and prep["changed_sources"]==[cls+"Single.cpp"] and prep["recompile_sources"]==names and set(prep["changed_headers"])=={helper,"upl_tpi_m0_dt_r2.h"},"Exact P3 source and two-host dependency inventory differs")
 for e in prep["files"]:ad.pin(e["path"]);b.same(e)
 for key in("base_prepare","base_build","source_diff"):ad.pin(prep[key]["path"]);b.same(prep[key])
 parent=b.read(prep["base_prepare"]["path"])
 b.need(parent.get("passed")is True and parent.get("endpoint_defect_rounds")==2 and parent["backend"]==backend,"Actual P2 parent preparation required")
 originals={}
 for pair in prep["base_source_entries"]:
  a,z=pair["original"],pair["pinned_snapshot"]
  for e in(a,z):ad.pin(e["path"]);b.same(e)
  name=Path(a["path"]).name;b.need(g.key(z["path"])==g.key(source/name),"P3 source capture association differs");originals[name]=a
 b.need(set(originals)==set(files),"Complete P2 source parent closure absent")
 for name in("JSph.h","JSphCpu.h","JSphGpu.h","JSphHourglassGpu.h","JSphGpu_ker.h","upl_tpi_gpu_r1.cuh","JSphGpu_ker.cu",cls+".cpp"):
  if name in originals:b.need((source/name).read_bytes()==Path(originals[name]["path"]).read_bytes(),"Shared or unchanged host source changed: "+name)
 if backend=="GPU":b.need(prep["GPU_original_prefix_bytes_after_removing_host_only_block"]==3850,"Original device-visible prefix proof differs")
 ad.pin(base["program"]["path"]);b.same(base["program"])
 objects={Path(e["path"]).name.lower():e for e in base["objects"]};b.need(len(objects)==len(base["objects"])==count,"P2 actual object closure differs")
 for e in objects.values():ad.pin(e["path"]);b.same(e)
 recipes,evidence,dependencies={},[],[]
 for name in names:
  entry,call=old.genuine(ad,L/("upl_tpi_p2_"+cfg+"_r1."+Path(name).stem+".call.json"));args=call["arguments"]
  src=[x for x in args if Path(x).name.lower()==name.lower()];b.need(len(src)==1 and Path(src[0]).is_file(),"Exact passed P2 CL source argument required")
  ad.pin(src[0]);recipes[name]=list(args);evidence.append(entry);dependencies.append(Path(src[0]).parent.resolve())
 link_entry,link_call=old.genuine(ad,L/("upl_tpi_p2_"+cfg+"_r1.link.call.json"));evidence.append(link_entry)
 linked=[x for x in link_call["arguments"]if x.lower().endswith(".obj")and not x.startswith("/")]
 b.need(len(linked)==len(set(map(g.key,linked)))==count and {g.key(x)for x in linked}=={g.key(e["path"])for e in objects.values()},"Actual P2 ordered link binding differs")
 libraries=[]
 for e in base["actual_library_search"]:
  a=e["first_existing_candidate"];ad.pin(a["path"]);b.same(a)
  libraries.append(dict(entry=a,evidence="passed_P2_actual_link_binding",**{k:e[k]for k in("stat_source_admission","legacy_reference")if k in e}))
 sdk=base["environment"]["CPU_Debug_original_sdk_adaptation"]if cfg=="DebugCPU"else{}
 for e in sdk.get("old_actual_sdk_header_inputs",[]):ad.pin(e["path"]);b.same(e)
 runtime=[e["destination"]for e in base["runtime"]]
 for e in runtime:ad.pin(e["path"]);b.same(e)
 project,solution=(b.PROJECT,b.SOLUTION)if backend=="CPU"else(g.PROJECT,g.SOLUTION)
 for p in(project,solution):ad.pin(p)
 cmd=Path(os.environ.get("COMSPEC","C:/Windows/System32/cmd.exe"));cl=Path(b.read(evidence[0]["path"])["program"]["path"]);link=Path(link_call["program"]["path"])
 for p in(cmd,cl,link):ad.pin(p)
 pdbs=sorted({Path(e["path"]).parent/"vc143.pdb"for e in objects.values()if(Path(e["path"]).parent/"vc143.pdb").is_file()})
 for p in pdbs:ad.pin(p)
 tag="upl_tpi_p3_"+cfg+"_r1";root=T/"outputs"/tag;intdir=Path(tempfile.gettempdir())/TAG/cfg/"int"
 b.need(not any(x.isspace()for x in str(intdir))and not root.exists()and not intdir.exists(),"Fresh isolated P3 outputs/IntDir required")
 if create:ad.finish();root.mkdir();(root/"out").mkdir();intdir.mkdir(parents=True)
 return dict(tag=tag,backend=backend,configuration=cfg,count=count,exe=exe,root=root,out=root/"out",intdir=intdir,source_root=source,pressure_header=helper,prepared=ad.pin(pp),base_build=ad.pin(bp),source_files=list(files.values()),old_objects=objects,cl_args=recipes,link_args=link_call["arguments"],libraries=libraries,runtime_sources=runtime,tools=dict(cmd=b.stat(cmd),cl=b.stat(cl),link=b.stat(link)),sdk=sdk,original_recipe_evidence=evidence,prior_source_roots={Path(e["path"]).parent.resolve()for e in originals.values()}|set(dependencies),exact_CPU_tlog_source_tail_repairs=[],authoritative_project=ad.pin(project),authoritative_solution=ad.pin(solution),old_compiler_pdbs=[ad.pin(p)for p in pdbs],ReleaseCPU_adopts_P1_not_prior_M0=False)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--configuration",choices=tuple(CONFIG),required=True);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args();b.need(a.execution_authorized,"Root full-read build-only authorization required")
 path=L/("upl_tpi_p3_"+a.configuration+"_r1.build.json");b.need(not path.exists(),"Existing P3 receipt protected");ad=ctx=None;calls=[]
 result=dict(stage=TAG,passed=False,configuration=a.configuration,compile_invocations=0,link_invocations=0,new_CUDA_compile_invocations=0,solver_invocations=0,program_help_invocations=0,native_invocations=0,VTK_invocations=0,SHA_scans=0,physical_acceptance=False,following_action_launched=False,public_source_changed=False,canonical_programs_changed=False)
 try:
  ad=Admission(a.admission,a.configuration);ctx=context(ad,a.configuration)
  result.update(root_admission=ad.entry,backend=ctx["backend"],prepared=ctx["prepared"],source_prepare=ctx["prepared"],base_build=ctx["base_build"],source_files=ctx["source_files"],original_recipe_evidence=ctx["original_recipe_evidence"],authoritative_project=ctx["authoritative_project"],authoritative_solution=ctx["authoritative_solution"],old_compiler_pdbs=ctx["old_compiler_pdbs"],private_no_space_IntDir=str(ctx["intdir"]),private_output_root=str(ctx["root"]),inherited_SDK_and_libraries_from_actual_P2=True)
  env,result["environment"],result["actual_library_search"]=old.environment(ad,ctx,calls)
  changed,deps=old.compile_hosts(ad,ctx,env,calls);program,objects,retained=old.link_hosts(ad,ctx,changed,env,calls);runtime=[]
  for e in ctx["runtime_sources"]:
   z=ctx["out"]/Path(e["path"]).name;b.need(not z.exists(),"Runtime destination protected");shutil.copy2(e["path"],z);runtime.append(dict(source=e,destination=b.stat(z)))
  result.update(passed=True,program=program,objects=objects,retained_objects=retained,object_count=len(objects),replacement_object_count=2,retained_effective_object_count=len(retained),compiler_dependencies=deps,runtime=runtime,new_program_identity_stat_only=True,class_layout_and_kernel_external_ABI_unchanged=True,adopted_CUDA_objects_unchanged=ctx["backend"]=="GPU")
 except Exception as exc:result["failure"]=str(exc);raise
 finally:
  result["calls"]=calls;actual=[b.read(e["path"])for e in calls]
  result["compile_invocations"]=sum(Path(x["program"]["path"]).name.lower()=="cl.exe"and isinstance(x.get("child"),dict)for x in actual);result["link_invocations"]=sum(Path(x["program"]["path"]).name.lower()=="link.exe"and isinstance(x.get("child"),dict)for x in actual)
  if ad is not None:
   try:result["consumed"]=ad.finish();result["consumed_stats_unchanged"]=True
   except Exception as exc:result.update(passed=False,consumed_stats_unchanged=False,final_stat_failure=str(exc))
  if ctx is not None:result["outputs"]=[b.stat(p)for q in(ctx["root"],ctx["intdir"])for p in q.rglob("*")if p.is_file()]
  b.write_new(path,result)
if __name__=="__main__":main()
