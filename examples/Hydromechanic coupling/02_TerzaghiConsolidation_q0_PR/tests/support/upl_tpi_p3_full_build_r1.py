"""One private P3 full-scope Single-TU build from an actual passed P3 recipe."""
from __future__ import annotations
import argparse,os,shutil,tempfile
from pathlib import Path
import upl_tpi_p3_build_r1 as prior
import upl_tpi_p3_full_source_r1 as sourceprep

b,g,T,L,S=prior.b,prior.g,prior.T,prior.L,prior.S
old=prior.old
TAG="upl_tpi_p3_full_build_r1";NOTE=T/"notes"/(TAG+".md");CONFIG=prior.CONFIG

class Admission:
 def __init__(self,path,cfg):
  self.entry,self.data=b.stat(path),b.read(path);self.used={}
  b.need(self.data.get("stage")==TAG+".build_admission"and self.data.get("passed")is True and self.data.get("build_only")is True and self.data.get("configuration")==cfg,"One exact one-configuration build admission required")
  self.frozen={g.key(e["path"]):e for e in self.data["inputs"]};b.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted build input")
 def pin(self,path):
  key=g.key(path);b.need(key in self.frozen,"Unadmitted full-scope build input: "+str(path));self.used[key]=b.same(self.frozen[key]);return self.used[key]
 def finish(self):
  b.same(self.entry)
  for e in self.used.values():b.same(e)
  return list(self.used.values())

def context(ad,cfg,create=True):
 backend,count,exe=CONFIG[cfg];cls="JSphCpu"if backend=="CPU"else"JSphGpu";name=cls+"Single.cpp";helper="upl_tpi_cpu_r1.h"if backend=="CPU"else"upl_tpi_gpu_r1.h"
 pp=L/("upl_tpi_p3_full_"+backend+"_r1.prepare.json");bp=L/("upl_tpi_p3_"+cfg+"_r1.build.json")
 for p in(Path(__file__),NOTE,Path(prior.__file__),prior.NOTE,Path(sourceprep.__file__),sourceprep.NOTE,Path(old.__file__),old.NOTE,Path(b.__file__),Path(g.__file__),g.VCVARS,pp,bp):ad.pin(p)
 prep,base=b.read(pp),b.read(bp)
 b.need(prep.get("stage")==sourceprep.TAG+".prepare"and prep.get("passed")is True and prep.get("backend")==backend and prep.get("consumed_stats_unchanged")is True,"Actual full-scope source preparation required")
 for key in("other_base_files_byte_identical","CUDA_source_and_cuh_byte_identical","all_headers_and_helpers_byte_identical","original_short_M0_TimeMax_le_2_expression_retained","non_M0_time_arm_retained","only_M0_qualification_time_domain_extended"):b.need(prep.get(key)is True,"Full-scope proof absent: "+key)
 b.need(prep.get("numerical_formula_changed")is False and prep.get("public_class_or_virtual_ABI_changed")is False and prep.get("shared_device_structures_or_inline_tokens_changed")is False,"Full-scope candidate changed equations or shared ABI")
 b.need(base.get("stage")==prior.TAG and base.get("passed")is True and base.get("configuration")==cfg and base.get("consumed_stats_unchanged")is True,"Actual passed same-configuration P3 build required")
 b.need(ad.pin(bp)in prep["base_builds"] and base["source_prepare"]==prep["base_prepare"],"P3 build/source ancestry differs")
 if cfg!="DebugCPU":
  gate=ad.pin(L/"upl_tpi_p3_full_DebugCPU_r1.build.json");gd=b.read(gate["path"])
  b.need(gd.get("stage")==TAG and gd.get("passed")is True and gd.get("configuration")=="DebugCPU"and gd.get("replacement_object_count")==1,"The independently completed CPU Debug full-scope build is required first")
 source=Path(prep["source_root"]).resolve();b.need(source==(T/"outputs"/("upl_tpi_p3_full_"+backend+"_r1_source")).resolve(),"Unexpected full-scope source root")
 files={Path(e["path"]).name:e for e in prep["files"]}
 b.need(len(files)==len(prep["files"])==(267 if backend=="CPU"else 270)and prep["changed_sources"]==prep["recompile_sources"]==[name]and prep["changed_headers"]==[],"Exact Single-only source inventory required")
 for e in prep["files"]:ad.pin(e["path"]);b.same(e)
 for e in[prep["base_prepare"],prep["source_diff"],*prep["base_builds"]]:ad.pin(e["path"]);b.same(e)
 original={}
 for pair in prep["base_source_entries"]:
  a,z=pair["original"],pair["pinned_snapshot"]
  for e in(a,z):ad.pin(e["path"]);b.same(e)
  n=Path(a["path"]).name;b.need(n not in original and g.key(z["path"])==g.key(source/n),"Source capture association differs");original[n]=a
 b.need(set(original)==set(files),"Complete original source closure absent")
 for n,e in original.items():
  expected=sourceprep.patch(Path(e["path"]).read_bytes(),backend)if n==name else Path(e["path"]).read_bytes()
  b.need((source/n).read_bytes()==expected,"Unreviewed source/helper difference: "+n)
 ad.pin(base["program"]["path"]);b.same(base["program"])
 objects={Path(e["path"]).name.lower():e for e in base["objects"]};b.need(len(objects)==len(base["objects"])==count,"Actual P3 object closure differs")
 for e in objects.values():ad.pin(e["path"]);b.same(e)
 ce,call=old.genuine(ad,L/("upl_tpi_p3_"+cfg+"_r1."+Path(name).stem+".call.json"));args=call["arguments"]
 src=[x for x in args if Path(x).name.lower()==name.lower()];b.need(len(src)==1 and g.key(src[0])==g.key(original[name]["path"]),"Original passed Single CL source differs")
 le,linkcall=old.genuine(ad,L/("upl_tpi_p3_"+cfg+"_r1.link.call.json"))
 linked=[x for x in linkcall["arguments"]if x.lower().endswith(".obj")and not x.startswith("/")]
 b.need(len(linked)==len(set(map(g.key,linked)))==count and {g.key(x)for x in linked}=={g.key(e["path"])for e in objects.values()},"Actual ordered P3 link closure differs")
 for e in base["compiler_dependencies"]:ad.pin(e["path"]);b.same(e)
 libraries=[]
 for e in base["actual_library_search"]:
  a=e["first_existing_candidate"];ad.pin(a["path"]);b.same(a);libraries.append(dict(entry=a,evidence="passed_P3_actual_link_binding",**{k:e[k]for k in("stat_source_admission","legacy_reference")if k in e}))
 sdk=base["environment"]["CPU_Debug_original_sdk_adaptation"]if cfg=="DebugCPU"else{}
 for e in sdk.get("old_actual_sdk_header_inputs",[]):ad.pin(e["path"]);b.same(e)
 runtime=[e["destination"]for e in base["runtime"]]
 for e in runtime:ad.pin(e["path"]);b.same(e)
 project,solution=(b.PROJECT,b.SOLUTION)if backend=="CPU"else(g.PROJECT,g.SOLUTION)
 for p in(project,solution):ad.pin(p)
 cmd=Path(os.environ.get("COMSPEC","C:/Windows/System32/cmd.exe"));cl=Path(call["program"]["path"]);link=Path(linkcall["program"]["path"])
 for p in(cmd,cl,link):ad.pin(p)
 pdbs=sorted({Path(e["path"]).parent/"vc143.pdb"for e in objects.values()if(Path(e["path"]).parent/"vc143.pdb").is_file()})
 for p in pdbs:ad.pin(p)
 tag="upl_tpi_p3_full_"+cfg+"_r1";root=T/"outputs"/tag;intdir=Path(tempfile.gettempdir())/TAG/cfg/"int"
 b.need(not any(x.isspace()for x in str(intdir))and not root.exists()and not intdir.exists(),"New isolated output and no-space IntDir required")
 if create:ad.finish();root.mkdir();(root/"out").mkdir();intdir.mkdir(parents=True)
 return dict(tag=tag,backend=backend,configuration=cfg,count=count,exe=exe,single=name,root=root,out=root/"out",intdir=intdir,source_root=source,pressure_header=helper,prepared=ad.pin(pp),base_build=ad.pin(bp),source_files=list(files.values()),old_objects=objects,cl_args={name:list(args)},link_args=linkcall["arguments"],libraries=libraries,runtime_sources=runtime,tools=dict(cmd=b.stat(cmd),cl=b.stat(cl),link=b.stat(link)),sdk=sdk,original_recipe_evidence=[ce,le],prior_source_roots={Path(e["path"]).parent.resolve()for e in original.values()},authoritative_project=ad.pin(project),authoritative_solution=ad.pin(solution),old_compiler_pdbs=[ad.pin(p)for p in pdbs])

def compile_single(ad,ctx,env,calls):
 name=ctx["single"];obj=ctx["intdir"]/(Path(name).stem+".obj");dep=ctx["intdir"]/(name+".sourceDependencies.json");args=[];counts=dict(source=0,fo=0,fd=0);skip=False
 for arg in ctx["cl_args"][name]:
  if skip:skip=False;continue
  low=arg.lower()
  if low=="/sourcedependencies":skip=True
  elif Path(arg).name.lower()==name.lower():args.append(str(ctx["source_root"]/name));counts["source"]+=1
  elif low.startswith("/fo"):args.append("/Fo"+str(obj));counts["fo"]+=1
  elif low.startswith("/fd"):args.append("/Fd"+str(ctx["intdir"]/"vc143.pdb"));counts["fd"]+=1
  elif low.startswith("/i")and not low.startswith("/incremental")and(Path(arg[2:])/name).is_file():continue
  else:args.append(arg)
 release=ctx["configuration"]in("ReleaseCPU","Release")
 b.need(all(x==1 for x in counts.values())and "/fp:precise"in args and "/openmp"in args and("/MT"if release else"/MTd")in args and("/O2"if release else"/Od")in args,"Original source/numerical/CRT/optimization recipe differs")
 args=["/I"+str(ctx["source_root"]),*args,"/sourceDependencies",str(dep)]
 ad.finish();g.invoke(b,ctx["tag"]+"."+Path(name).stem,[ctx["tools"]["cl"]["path"],*args],S/"VS",env,calls)
 b.need(obj.is_file()and dep.is_file(),"New Single object/dependency record missing")
 data=b.read(dep)["Data"];includes=[Path(x).resolve()for x in data["Includes"]]
 b.need(g.key(data["Source"])==g.key(ctx["source_root"]/name)and all(ctx["source_root"]/n in includes for n in(ctx["pressure_header"],"JSph.h","upl_tpi_m0_dt_r2.h"))and all(not p.is_relative_to((S/"source").resolve())for p in includes)and not any(p.is_relative_to(q)for p in includes for q in ctx["prior_source_roots"]),"Single used live/prior headers or omitted actual P3 helpers")
 return {obj.name.lower():b.stat(obj)},[b.stat(dep)]

def link_single(ad,ctx,changed,env,calls):
 targets={"/out:":ctx["out"]/(ctx["exe"]+".exe"),"/pdb:":ctx["out"]/(ctx["exe"]+".pdb"),"/implib:":ctx["out"]/(ctx["exe"]+".lib"),"/ltcgout:":ctx["intdir"]/(ctx["exe"]+".iobj"),"/ilk:":ctx["intdir"]/(ctx["exe"]+".ilk"),"/pgd:":ctx["intdir"]/(ctx["exe"]+".pgd")}
 counts=dict.fromkeys(targets,0);args=[];objects=[];retained=[]
 for arg in ctx["link_args"]:
  low=arg.lower();option=next((x for x in targets if low.startswith(x)),None)
  if option:args.append(arg[:len(option)]+str(targets[option]));counts[option]+=1
  elif low.endswith(".obj")and not arg.startswith("/"):
   name=Path(arg).name.lower();entry=changed.get(name,ctx["old_objects"][name]);args.append(entry["path"]);objects.append(entry)
   if name not in changed:retained.append(entry)
  else:args.append(arg)
 b.need(len(changed)==1 and all(counts[x]==1 for x in("/out:","/pdb:","/implib:","/ltcgout:","/ilk:"))and counts["/pgd:"]<=1 and len(objects)==ctx["count"]and len(retained)==ctx["count"]-1,"Ordered Single replacement/output redirection differs")
 ad.finish();g.invoke(b,ctx["tag"]+".link",[ctx["tools"]["link"]["path"],*args],S/"VS",env,calls);b.need(targets["/out:"].is_file(),"New linked program missing")
 return b.stat(targets["/out:"]),objects,retained

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--configuration",choices=tuple(CONFIG),required=True);ap.add_argument("--admission",type=Path,required=True);ap.add_argument("--execution-authorized",action="store_true");a=ap.parse_args();b.need(a.execution_authorized,"Root full-read build-only authorization required")
 path=L/("upl_tpi_p3_full_"+a.configuration+"_r1.build.json");b.need(not path.exists(),"Existing build/failure receipt protected");ad=ctx=None;calls=[]
 result=dict(stage=TAG,passed=False,configuration=a.configuration,compile_invocations=0,link_invocations=0,new_CUDA_compile_invocations=0,solver_invocations=0,program_help_invocations=0,native_invocations=0,VTK_invocations=0,SHA_scans=0,physical_acceptance=False,following_action_launched=False,public_source_changed=False,canonical_programs_changed=False)
 try:
  ad=Admission(a.admission,a.configuration);ctx=context(ad,a.configuration)
  result.update(root_admission=ad.entry,backend=ctx["backend"],prepared=ctx["prepared"],source_prepare=ctx["prepared"],base_build=ctx["base_build"],source_files=ctx["source_files"],original_recipe_evidence=ctx["original_recipe_evidence"],authoritative_project=ctx["authoritative_project"],authoritative_solution=ctx["authoritative_solution"],old_compiler_pdbs=ctx["old_compiler_pdbs"],private_no_space_IntDir=str(ctx["intdir"]),private_output_root=str(ctx["root"]),inherited_SDK_and_libraries_from_actual_P3=True)
  env,result["environment"],result["actual_library_search"]=old.environment(ad,ctx,calls)
  changed,deps=compile_single(ad,ctx,env,calls);program,objects,retained=link_single(ad,ctx,changed,env,calls);runtime=[]
  for e in ctx["runtime_sources"]:
   p=ctx["out"]/Path(e["path"]).name;b.need(not p.exists(),"Runtime destination protected");shutil.copy2(e["path"],p);runtime.append(dict(source=e,destination=b.stat(p)))
  result.update(passed=True,program=program,objects=objects,retained_objects=retained,object_count=len(objects),replacement_object_count=1,retained_effective_object_count=len(retained),compiler_dependencies=deps,runtime=runtime,new_program_identity_stat_only=True,class_layout_and_kernel_external_ABI_unchanged=True,all_CUDA_objects_unchanged=ctx["backend"]=="GPU",full_scope_only=True,short_regression_pending=True,full_cycle_acceptance=False)
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
