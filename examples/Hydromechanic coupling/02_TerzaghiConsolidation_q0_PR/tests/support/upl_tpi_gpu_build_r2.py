"""Isolated GPU r2 build: Debug adopts three r1 hosts; Release compiles four.

Reuse reviewed r1 tool/recipe helpers without altering their functions or
globals. No help, solver, fixture, native read, VTK or next action is run.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import shutil
import tempfile
import upl_tpi_gpu_build_r1 as old

T, L, S = old.T, old.L, old.S
TAG = "upl_tpi_gpu_build_r2"
PREP = L / "upl_tpi_gpu_r2.prepare.json"
BASE_PREP = L / "upl_tpi_gpu_r1.prepare.json"
DEBUG_R1 = L / "upl_tpi_gpu_Debug_r1.build.json"
NOTE = T / "notes/upl_tpi_gpu_build_r2.md"
HOSTS = {"JSphGpu.obj", "JSphGpuSingle.obj", "JSphHourglassGpu.obj"}


class Admission:
    def __init__(self, b, configuration, path):
        self.b=b;self.entry=b.stat(path);self.data=b.read(path)
        b.need(self.data.get("stage")==TAG+".build_admission" and self.data.get("configuration")==configuration
               and self.data.get("passed") is True and self.data.get("build_only") is True,
               "Independent exact-configuration r2 build-only admission required")
        self.frozen={old.key(x["path"]):x for x in self.data["inputs"]};self.consumed={}

    def pin(self, path):
        k=old.key(path);self.b.need(k in self.frozen,"Input absent from root r2 admission: "+str(path))
        self.consumed[k]=self.b.same(self.frozen[k]);return self.consumed[k]

    def finish(self):
        self.b.same(self.entry)
        for x in self.consumed.values():self.b.same(x)
        return list(self.consumed.values())


def context(b, ad, configuration):
    tag="upl_tpi_gpu_"+configuration+"_r2";root=T/"outputs"/tag
    intdir=Path(tempfile.gettempdir())/"upl_tpi_gpu_build_r2"/configuration/"int"
    record=L/(tag+".build.json")
    b.need(not root.exists() and not intdir.exists() and not record.exists(),"Existing r2 build/failure is protected")
    b.need(not re.search(r"\s",str(intdir)),"New CUDA IntDir must have no whitespace")
    for p in (Path(__file__),NOTE,Path(old.__file__),old.COMMON,old.PROJECT,old.SOLUTION,old.VCVARS):ad.pin(p)
    prepared_entry=ad.pin(PREP);base_prepare_entry=ad.pin(BASE_PREP)
    prepared,base_prepare=b.read(PREP),b.read(BASE_PREP)
    b.need(prepared.get("passed") is True and prepared.get("stage")=="upl_tpi_gpu_r2.prepare"
           and prepared.get("host_h_API_and_other_268_files_byte_identical") is True
           and prepared.get("class_layout_or_virtual_ABI_changed") is False
           and prepared.get("old_kernel_external_signatures_changed") is False
           and old.key(prepared["base_prepare"]["path"])==old.key(BASE_PREP),"Exact source-only r2 ancestry required")
    b.need(base_prepare.get("passed") is True and len(base_prepare["files"])==len(prepared["files"])==269,
           "Complete r1/r2 source closures required")
    source=Path(prepared["source_root"]).resolve()
    b.need(source==(T/"outputs/upl_tpi_gpu_r2_source").resolve(),"Unexpected r2 private source root")
    newfiles={Path(e["path"]).name:ad.pin(e["path"]) for e in prepared["files"]}
    oldfiles={Path(e["path"]).name:ad.pin(e["path"]) for e in base_prepare["files"]}
    b.need(len(newfiles)==269 and set(newfiles)==set(oldfiles)
           and {Path(e["path"]).name for e in prepared["changed_headers"]}=={"upl_tpi_gpu_r1.cuh"}
           and not prepared["changed_sources"]
           and {Path(e["path"]).name for e in prepared["recompile_sources"]}=={"JSphGpu_ker.cu"},"Only the private .cuh delta is admitted")
    # Necessary ODR/adoption proof once, no old SHA sweep.
    for name,entry in newfiles.items():
        b.need(Path(entry["path"]).parent==source,"r2 source tree must remain flat")
        if name!="upl_tpi_gpu_r1.cuh":
            b.need(Path(entry["path"]).read_bytes()==Path(oldfiles[name]["path"]).read_bytes(),
                   "Unapproved r2 host/header/source change: "+name)
    ad.pin(prepared["source_diff"]["path"]);ad.pin(base_prepare["source_diff"]["path"])
    source_manifest=ad.pin(base_prepare["base_source_manifest"]["path"])
    base_entry=ad.pin(base_prepare["base_build_debug" if configuration=="Debug" else "base_build_release"]["path"])
    base=b.read(base_entry["path"])
    b.need(base.get("passed") is True and base.get("configuration")==configuration and base.get("object_count")==111,
           "Matching original frozen GPU111 build required")
    old_program=ad.pin(base["program"]["path"])
    old_int=Path("C:/Users/syosh/AppData/Local/Temp/upl_gpu_stabilizers_r1")/configuration/"int"
    paths=sorted(old_int.glob("*.obj"));b.need(len(paths)==111,"Original 111-object set is incomplete")
    objects={p.name.lower():ad.pin(p) for p in paths};b.need(len(objects)==111,"Duplicate old object basenames")
    expected={Path(e["path"]).name.lower() for e in base["objects"]} if configuration=="Debug" else {x.lower() for x in base["object_names"]}
    b.need(set(objects)==expected,"Original recorded object closure differs")
    old_pdb=ad.pin(old_int/"vc143.pdb");logs=old_int/"DualSPHysics.tlog"
    cllog,linklog,readlog=[ad.pin(logs/n) for n in ("CL.command.1.tlog","link.command.1.tlog","link.read.1.tlog")]
    original_call=ad.pin(L/("upl_gpu_stabilizers_"+configuration+"_r1.call.json"));call=b.read(original_call["path"])
    b.need(call.get("exit_code")==0,"Original actual GPU MSBuild failure cannot be adopted")
    original_log=ad.pin(call["log"]["path"])
    link_args=b.windows_argv(" ".join(x for x in old.tlog_text(linklog["path"]).splitlines() if x and not x.startswith("^")))
    linked=[Path(x) for x in link_args if x.lower().endswith(".obj")]
    b.need(len(linked)==111 and {x.name.lower() for x in linked}==set(objects),"Actual original linker ordering/closure differs")
    libraries=[ad.pin(p) for p in old.library_paths(b,old.tlog_text(readlog["path"]))]
    cl_text=old.tlog_text(cllog["path"])
    cl_args={n:old.cl_recipe(b,cl_text,n) for n in sorted(old.RECOMPILE) if n.endswith(".cpp")}
    nvcc_args=old.nvcc_recipe(b,original_log["path"])
    tools=dict(cl=ad.pin(old.TOOLS/"cl.exe"),link=ad.pin(old.TOOLS/"link.exe"),nvcc=ad.pin(nvcc_args[0]),
               cmd=ad.pin(os.environ.get("COMSPEC","C:/Windows/System32/cmd.exe")))
    runtime=[ad.pin(x["path"]) for x in base["runtime"]]
    if configuration=="Debug":
        omp=Path("D:/Program Files/VS2022/VC/Redist/MSVC/14.36.32532/debug_nonredist/x64/Microsoft.VC143.DebugOpenMP/vcomp140d.dll")
        if not any(Path(x["path"]).name.lower()==omp.name.lower() for x in runtime):runtime.append(ad.pin(omp))
    adopted={};adopted_build=None;adopted_pdb=None
    if configuration=="Debug":
        adopted_build=ad.pin(DEBUG_R1);prior=b.read(DEBUG_R1)
        b.need(prior.get("passed") is True and prior.get("configuration")=="Debug" and prior.get("object_count")==111
               and prior.get("compile_invocations")==4 and prior.get("link_invocations")==1
               and old.key(prior["prepared"]["path"])==old.key(BASE_PREP),"Successful exact original r1 Debug build required for host adoption")
        ad.pin(prior["program"]["path"])
        for x in prior["objects"]:
            if Path(x["path"]).name in HOSTS:adopted[Path(x["path"]).name.lower()]=ad.pin(x["path"])
        b.need(set(adopted)=={x.lower() for x in HOSTS},"Exactly three original r1 new host objects must be adopted")
        adopted_pdb=ad.pin(Path(prior["private_no_space_IntDir"])/"vc143.pdb")
        for entry in prior["calls"]:ad.pin(entry["path"])
    project=old.project_closure(b,set(objects))
    ad.finish();root.mkdir();intdir.mkdir(parents=True);out=root/"out";out.mkdir()
    return dict(tag=tag,root=root,intdir=intdir,out=out,record=record,configuration=configuration,
        source_root=source,prepared=prepared_entry,base_prepare=base_prepare_entry,source_files=list(newfiles.values()),
        base_source_manifest=source_manifest,base_build=base_entry,old_program=old_program,old_objects=objects,
        old_compiler_pdb=old_pdb,original_CL_tlog=cllog,original_link_tlog=linklog,original_link_read_tlog=readlog,
        original_MSBuild_call=original_call,original_MSBuild_log=original_log,cl_args=cl_args,nvcc_args=nvcc_args,
        link_args=link_args,libraries=libraries,runtime_sources=runtime,tools=tools,current_project_closure=project,
        adopted_hosts=adopted,adopted_Debug_build=adopted_build,adopted_compiler_pdb=adopted_pdb)


def compile_cuda_only(b, ad, ctx, env, calls):
    """Explicit one-CUDA invocation; no modification of the r1 compile helper."""
    args=list(ctx["nvcc_args"]);program,args=args[0],args[1:]
    b.need(old.key(program)==old.key(ctx["tools"]["nvcc"]["path"]),"Original CUDA compiler changed")
    b.need(sum(Path(x).name=="JSphGpu_ker.cu" for x in args)==1 and args.count("-o")==args.count("--keep-dir")==1,
           "Original CUDA source/output closure differs")
    obj=ctx["intdir"]/"JSphGpu_ker.cu.obj";args[args.index("-o")+1]=str(obj)
    args[args.index("--keep-dir")+1]=ctx["intdir"].as_posix()+"/"
    args=[str(ctx["source_root"]/"JSphGpu_ker.cu") if Path(x).name=="JSphGpu_ker.cu" else x for x in args]
    count=0
    for i,arg in enumerate(args):
        args[i],n=re.subn(r"(?i)/Fd[^ ]+","/Fd"+(ctx["intdir"]/"vc143.pdb").as_posix(),arg);count+=n
    b.need(count==1,"Original CUDA compiler PDB rewrite must occur once")
    ad.finish();old.invoke(b,ctx["tag"]+".JSphGpu_ker",[program,*args],S/"VS",env,calls)
    b.need(obj.is_file(),"Actual new r2 CUDA object missing")
    return {obj.name.lower():b.stat(obj)}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--configuration",choices=("Debug","Release"),required=True)
    p.add_argument("--execution-authorized",action="store_true");p.add_argument("--admission",required=True,type=Path)
    a=p.parse_args()
    if not a.execution_authorized:p.error("Independent root one-configuration GPU build admission required")
    b=old.common_module();ad=None;ctx=None;calls=[]
    result=dict(stage=TAG,passed=False,configuration=a.configuration,compile_invocations=0,link_invocations=0,
        program_help_invocations=0,solver_invocations=0,native_invocations=0,VTK_invocations=0,
        physical_acceptance=False,following_action_launched=False,old_source_object_or_BI4_SHA_scans=0,
        public_source_changed=False,canonical_programs_changed=False,device_fixture_executed=False)
    try:
        ad=Admission(b,a.configuration,a.admission);ctx=context(b,ad,a.configuration)
        result.update(root_admission=ad.entry,prepared=ctx["prepared"],source_prepare=ctx["prepared"],base_prepare=ctx["base_prepare"],
            base_build=ctx["base_build"],base_source_manifest=ctx["base_source_manifest"],source_files=ctx["source_files"],
            authoritative_solution=ad.pin(old.SOLUTION),authoritative_project=ad.pin(old.PROJECT),
            current_project_closure=ctx["current_project_closure"],private_no_space_IntDir=str(ctx["intdir"]),
            private_output_root=str(ctx["root"]),original_MSBuild_call=ctx["original_MSBuild_call"],
            original_MSBuild_log=ctx["original_MSBuild_log"],original_CL_tlog=ctx["original_CL_tlog"],
            original_link_tlog=ctx["original_link_tlog"],original_link_read_tlog=ctx["original_link_read_tlog"],
            old_compiler_pdb=ctx["old_compiler_pdb"],original_objects=list(ctx["old_objects"].values()),
            adopted_Debug_build=ctx["adopted_Debug_build"],adopted_compiler_pdb=ctx["adopted_compiler_pdb"],
            adopted_host_objects=list(ctx["adopted_hosts"].values()),class_layout_and_kernel_external_ABI_unchanged=True)
        env,record=old.environment(b,ctx,calls);result["environment"]=record
        result["actual_library_search"]=old.validate_library_search(b,ctx,env)
        if a.configuration=="Debug":
            objects=dict(ctx["adopted_hosts"]);objects.update(compile_cuda_only(b,ad,ctx,env,calls))
        else:objects=old.compile_sources(b,ad,ctx,env,calls)
        b.need(set(objects)=={old.object_name(x).lower() for x in old.RECOMPILE},"Exact four replacement/adopted object map required")
        program,all_objects,retained=old.link(b,ad,ctx,env,objects,calls)
        result.update(program=program,objects=all_objects,retained_objects=retained,object_count=111,
            replacement_object_count=4,new_object_count=1 if a.configuration=="Debug" else 4,
            adopted_host_object_count=len(ctx["adopted_hosts"]),retained_original_object_count=107,
            retained_effective_object_count=110 if a.configuration=="Debug" else 107,new_program_identity_SHA256_count=1)
        runtime=[]
        for entry in ctx["runtime_sources"]:
            dest=ctx["out"]/Path(entry["path"]).name;b.need(not dest.exists(),"Existing runtime copy destination protected")
            shutil.copy2(entry["path"],dest);runtime.append(dict(source=entry,destination=b.stat(dest)))
        result["runtime"]=runtime;result["passed"]=True
    except Exception as exc:result["failure"]=str(exc)
    finally:
        result["calls"]=calls
        actual=[b.read(x["path"]) for x in calls];children=[x for x in actual if isinstance(x.get("child"),dict)]
        result["compile_invocations"]=sum(Path(x["program"]["path"]).name.lower() in ("cl.exe","nvcc.exe") for x in children)
        result["link_invocations"]=sum(Path(x["program"]["path"]).name.lower()=="link.exe" for x in children)
        if ad is not None:
            try:result["consumed"]=ad.finish();result["consumed_stats_unchanged"]=True
            except Exception as exc:result["passed"]=False;result["consumed_stats_unchanged"]=False;result["failure"]=result.get("failure","")+"; "+str(exc)
        if ctx is not None:
            result["outputs"]=[b.stat(p) for d in (ctx["root"],ctx["intdir"]) for p in sorted(d.rglob("*")) if p.is_file()]
            result["ended_utc"]=b.now();b.write_new(ctx["record"],result)
        print(result["passed"],result.get("failure",""))
    return 0 if result["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
