"""Author-controlled source-boundary guard/device-fixture patch to GPU P1 r1.

Copy its 269 frozen prepared files, change only the private .cuh, and write
a new receipt. No build, help, solver, device fixture, native or Git runs.
"""
from __future__ import annotations
import argparse
import difflib
import json
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_gpu_r2"
BASE = T / "logs/upl_tpi_gpu_r1.prepare.json"
OUT = T / "outputs" / (TAG + "_source")
NOTE = T / "notes" / (TAG + ".md")
RECEIPT = T / "logs" / (TAG + ".prepare.json")
CHANGED = "upl_tpi_gpu_r1.cuh"


def stat(path):
    p = Path(path).resolve();s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def need(value, message):
    if not value:raise RuntimeError(message)


def same(entry):
    result = stat(entry["path"])
    need(result == {k: entry[k] for k in ("path", "bytes", "mtime_ns")},
         "Root-frozen stat changed: " + entry["path"])
    return result


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


PREDICATE = '''
// Used by the real source stage AND the independently uploaded device fixtures.
// A newly opened owner may have any finite oldFinal, but its actual pn must be
// positive zero. An unconstrained owner must retain every oldFinal float bit.
__device__ static bool SourceStateValid(float pn,float oldFinal,bool drained){
  return isfinite(pn)&&isfinite(oldFinal)&&(drained?Same(pn,0.f):Same(pn,oldFinal));
}
'''

FIXTURE = '''
// These fixtures have their own allocations/error packet, no View, DeviceState,
// history/force pointer, physical counter or material array. Uploaded data keeps
// the predicate inputs as real device memory values, not folded literal tests.
struct SourceFixtureInputR2 {float pn,oldFinal;unsigned drained,expected;};
struct RoleFixtureInputR2 {unsigned id,fixed,total,normal,periodic,isfixed,isfluid,expected;};
struct SourceRoleFixtureResultR2 {unsigned bits,firstId,checked;};
__global__ void SourceRoleFixtureKernelR2(const SourceFixtureInputR2* source,
  const RoleFixtureInputR2* roles,SourceRoleFixtureResultR2* error){
  const unsigned i=blockIdx.x*blockDim.x+threadIdx.x;bool actual=false,wanted=false;
  if(i<8){const auto x=source[i];actual=SourceStateValid(x.pn,x.oldFinal,x.drained!=0);wanted=x.expected!=0;}
  else if(i<16){const auto x=roles[i-8];actual=OwnerRole(x.id,x.fixed,x.total,x.normal!=0,x.periodic!=0,x.isfixed!=0,x.isfluid!=0);wanted=x.expected!=0;}
  else return;
  atomicAdd(&error->checked,1u);
  if(actual!=wanted){atomicOr(&error->bits,1u);atomicMin(&error->firstId,i);}
}
static void SourceRoleDeviceFixturesR2(){
  float negativeZero;const unsigned negativeZeroBits=0x80000000u;
  std::memcpy(&negativeZero,&negativeZeroBits,sizeof(negativeZero));
  const SourceFixtureInputR2 source[8]={
    {10.f,10.f,1,0}, // Actual regression: drained/nonzero==oldFinal must reject.
    {negativeZero,negativeZero,1,0}, // A drained negative zero must reject.
    {0.f,10.f,1,1}, {0.f,0.f,1,1},
    {10.f,10.f,0,1}, {11.f,10.f,0,0},
    {negativeZero,0.f,0,0}, {negativeZero,negativeZero,0,1}
  };
  const RoleFixtureInputR2 roles[8]={
    {0,1,2,1,0,1,0,1}, {1,1,2,1,0,0,1,1},
    {0,1,2,0,1,1,0,1}, {1,1,2,0,1,0,1,1},
    {0,1,2,0,1,0,1,0}, {1,1,2,0,1,1,0,0},
    {0,1,2,0,0,1,0,0}, {1,1,2,0,0,0,1,0}
  };
  SourceFixtureInputR2* sg=nullptr;RoleFixtureInputR2* rg=nullptr;SourceRoleFixtureResultR2* eg=nullptr;
  try{
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&sg),sizeof(source)));
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&rg),sizeof(roles)));
    CheckCuda(cudaMalloc(reinterpret_cast<void**>(&eg),sizeof(SourceRoleFixtureResultR2)));
    const SourceRoleFixtureResultR2 initial={0,UINT_MAX,0};
    CheckCuda(cudaMemcpy(sg,source,sizeof(source),cudaMemcpyHostToDevice));
    CheckCuda(cudaMemcpy(rg,roles,sizeof(roles),cudaMemcpyHostToDevice));
    CheckCuda(cudaMemcpy(eg,&initial,sizeof(initial),cudaMemcpyHostToDevice));
    SourceRoleFixtureKernelR2<<<1,32>>>(sg,rg,eg);CheckCuda(cudaGetLastError());
    SourceRoleFixtureResultR2 actual;CheckCuda(cudaMemcpy(&actual,eg,sizeof(actual),cudaMemcpyDeviceToHost));
    if(actual.bits||actual.firstId!=UINT_MAX||actual.checked!=16)throw std::runtime_error(
      "GPU source/owner-role device fixture rejected case="+std::to_string(actual.firstId));
    {auto p=sg;sg=nullptr;CheckCuda(cudaFree(p));}
    {auto p=rg;rg=nullptr;CheckCuda(cudaFree(p));}
    {auto p=eg;eg=nullptr;CheckCuda(cudaFree(p));}
    std::fprintf(stdout,"UplTpiGpuSourceRoleFixtureR2: source_cases=8 owner_role_cases=8 device_cases_checked=%u device_kernel_completed=true private_error_bits=0\\n",actual.checked);
    std::fflush(stdout);
  }catch(...){if(sg)cudaFree(sg);if(rg)cudaFree(rg);if(eg)cudaFree(eg);throw;}
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execution-authorized", action="store_true")
    p.add_argument("--admission", required=True, type=Path)
    a = p.parse_args()
    need(a.execution_authorized, "Independent root prepare-only admission required")
    need(not OUT.exists() and not RECEIPT.exists(), "Existing source/failure outputs are protected")
    admission_entry = stat(a.admission);admission = read(a.admission)
    need(admission.get("stage") == TAG + ".prepare_admission" and admission.get("passed") is True
         and admission.get("prepare_only") is True, "Reviewed root r2 prepare-only admission required")
    frozen = {str(Path(x["path"]).resolve()): x for x in admission["inputs"]}

    def pin(path):
        key = str(Path(path).resolve())
        need(key in frozen, "Consumed input absent from root admission: " + key)
        return same(frozen[key])

    authors = [pin(Path(__file__)),pin(NOTE)];base_entry=pin(BASE);base=read(BASE)
    need(base.get("passed") is True and base.get("stage") == "upl_tpi_gpu_r1.prepare"
         and len(base["files"]) == 269 and base.get("class_layout_or_virtual_ABI_changed") is False
         and base.get("old_kernel_external_signatures_changed") is False,
         "Complete unchanged-ABI frozen r1 prepared source required")
    pin(base["source_diff"]["path"])
    contents={};before=[]
    for entry in base["files"]:
        actual=pin(entry["path"]);name=Path(actual["path"]).name
        need(name not in contents,"Duplicate prepared flat source name")
        contents[name]=Path(actual["path"]).read_bytes();before.append(actual)
    need(CHANGED in contents and "upl_tpi_gpu_r1.h" in contents,"Original private helper closure missing")
    old=contents[CHANGED].decode("utf-8");new=old;proof=[]

    def replace(label, lhs, rhs):
        nonlocal new
        count=new.count(lhs);need(count==1,label+" expected one anchor, found "+str(count))
        new=new.replace(lhs,rhs,1);proof.append(dict(anchor=label,count=count,before=lhs,after=rhs))

    replace("fixture_host_headers", '#include <stdexcept>\n',
            '#include <stdexcept>\n#include <cstring>\n#include <cstdio>\n')
    replace("real_shared_source_predicate", '__device__ static bool Same(float x,float y){return __float_as_uint(x)==__float_as_uint(y);}\n',
            '__device__ static bool Same(float x,float y){return __float_as_uint(x)==__float_as_uint(y);}\n'+PREDICATE)
    replace("original_source_stage_uses_same_predicate",
            '  if(!isfinite(pn[p])||!isfinite(v.J[p])||v.J[p]<=0.||(!Same(pn[p],o.finalP)&&!(drained&&pn[p]==0.f))){Bad(d,256,id);return;}',
            '  if(!SourceStateValid(pn[p],o.finalP,drained)||!isfinite(v.J[p])||v.J[p]<=0.){Bad(d,256,id);return;}')
    initialize='void Initialize(View v,DeviceState d){InitializeKernel<<<(d.total+127)/128,128>>>(v,d);CheckCuda(cudaGetLastError());}'
    replace("real_initialize_runs_independent_device_fixture", initialize,
            FIXTURE+'\nvoid Initialize(View v,DeviceState d){SourceRoleDeviceFixturesR2();InitializeKernel<<<(d.total+127)/128,128>>>(v,d);CheckCuda(cudaGetLastError());}')
    need(new!=old and new.count('SourceStateValid(pn[p],o.finalP,drained)')==1,
         "Real source-stage predicate was not patched exactly once")
    for entry in frozen.values():same(entry)
    same(admission_entry)
    OUT.mkdir();files=[]
    for name,data in contents.items():
        body=new.encode("utf-8") if name==CHANGED else data;target=OUT/name
        with target.open("xb") as f:f.write(body)
        files.append(stat(target))
    diff=OUT/"source_diff.json"
    difference=dict(stage=TAG+".source_diff",passed=True,base_prepare=base_entry,
        base_source_diff=pin(base["source_diff"]["path"]),changed_file=CHANGED,replacements=proof,
        unified_diff="".join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),
          fromfile="frozen_r1/"+CHANGED,tofile="private_r2/"+CHANGED)),
        remaining_268_files_copied_bytewise=True,host_h_API_changed=False,
        class_layout_or_virtual_ABI_changed=False,old_kernel_external_signatures_changed=False,
        pressure_update_or_spatial_equations_changed=False,source_boundary_guard_strengthened=True,
        device_fixture_source_authored=True,device_fixture_executed=False,
        physical_or_history_buffers_passed_to_fixture=False,physical_acceptance=False)
    with diff.open("x",encoding="utf-8",newline="\n") as f:json.dump(difference,f,ensure_ascii=False,indent=2);f.write("\n")
    for entry in frozen.values():same(entry)
    same(admission_entry)
    record=dict(stage=TAG+".prepare",passed=True,root_admission=admission_entry,author_files=authors,
        base_prepare=base_entry,base_source_diff=pin(base["source_diff"]["path"]),base_source_entries=before,
        source_root=str(OUT),files=files,source_diff=stat(diff),changed_sources=[],
        changed_headers=[stat(OUT/CHANGED)],recompile_sources=[stat(OUT/"JSphGpu_ker.cu")],
        only_one_CUDA_TU_requires_recompilation=True,host_h_API_and_other_268_files_byte_identical=True,
        class_layout_or_virtual_ABI_changed=False,old_kernel_external_signatures_changed=False,
        source_boundary_guard_strengthened=True,physical_operator_equations_changed=False,
        independent_device_fixture_cases=dict(source_state=8,owner_role=8),device_fixture_executed=False,
        solver_invocations=0,program_or_help_invocations=0,native_invocations=0,builder_invocations=0,
        SHA_scans=0,consumed_stats_unchanged=True,physical_acceptance=False)
    with RECEIPT.open("x",encoding="utf-8",newline="\n") as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write("\n")
    print(str(RECEIPT))


if __name__ == "__main__":main()
