"""Prepare a private frozen-column GPU TPI prediction/leading-LP variant only.

Never compile, run help/solver/native, install canonical files, or hash old
objects/BI4. Existing source snapshots and failed results remain untouched.
"""
from __future__ import annotations
import argparse
import difflib
import json
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_gpu_r1"
OUT = T / "outputs" / (TAG + "_source")
RECEIPT = T / "logs" / (TAG + ".prepare.json")
SOURCE = T / "logs/upl_gpu_stabilizers_r1.source.json"
BUILDS = {c: T / "logs" / ("upl_gpu_stabilizers_" + c + "_r1.build.json")
          for c in ("Debug", "Release")}
NOTE = T / "notes" / (TAG + ".md")
AUTHORS = [T / "support" / (TAG + suffix) for suffix in (".h", ".cuh", "_prepare.py")] + [NOTE]


def stat(path):
    p = Path(path).resolve();s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def same(entry):
    actual = stat(entry["path"])
    if actual != {k: entry[k] for k in ("path", "bytes", "mtime_ns")}:
        raise RuntimeError("Root-frozen stat changed: " + entry["path"])
    return actual


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def need(okay, message):
    if not okay:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execution-authorized", action="store_true")
    p.add_argument("--admission", required=True, type=Path)
    a = p.parse_args()
    need(a.execution_authorized, "Independent root prepare-only admission required")
    need(not OUT.exists() and not RECEIPT.exists(), "Existing prepared source/failure is protected")
    admission_entry = stat(a.admission);admission = read(a.admission)
    need(admission.get("stage") == TAG + ".prepare_admission" and admission.get("passed") is True
         and admission.get("prepare_only") is True, "Reviewed exact root preparation required")
    frozen = {str(Path(x["path"]).resolve()): x for x in admission["inputs"]}

    def pin(path):
        key = str(Path(path).resolve())
        need(key in frozen, "Consumed input absent from root admission: " + key)
        return same(frozen[key])

    authors = [pin(q) for q in AUTHORS]
    source_entry = pin(SOURCE);source = read(SOURCE)
    need(source.get("source_count") == 265 and len(source["files"]) == 267,
         "Frozen GPU stabilizers 265-code plus two-doc source closure required")
    base_builds = {};base_programs = {}
    for config, path in BUILDS.items():
        entry = pin(path);j = read(path)
        need(j.get("passed") is True and j.get("configuration") == config and j.get("object_count") == 111,
             "Actual original GPU111-object builds required")
        base_builds[config] = entry;base_programs[config] = pin(j["program"]["path"])
    original = {};entries = []
    for entry in source["files"]:
        archived = entry["archive"];actual = pin(archived["path"]);name = Path(actual["path"]).name
        need(name not in original and actual["bytes"] == archived["bytes"], "Frozen flat GPU source name/size closure changed")
        original[name] = Path(actual["path"]).read_bytes()
        entries.append(dict(original_receipt=archived, pinned_snapshot=actual))
    names = ("JSphGpu.cpp", "JSphGpuSingle.cpp", "JSphGpu_ker.cu", "JSphHourglassGpu.h")
    baseline = {n: original[n].decode("utf-8-sig").replace("\r\n", "\n") for n in names}
    changed = dict(baseline);proof = []

    def replace(file, label, before, after, method=None):
        s = changed[file];begin = 0;end = len(s)
        if method:
            need(s.count(method) == 1, "Unique method missing for " + label)
            begin = s.index(method);end = s.find("\n//==============================================================================", begin + len(method))
            if end < 0:end = len(s)
        body = s[begin:end];count = body.count(before)
        need(count == 1, label + " expected one anchor, observed " + str(count))
        changed[file] = s[:begin] + body.replace(before, after, 1) + s[end:]
        proof.append(dict(file=file, anchor=label, count=count, method_scope=method, before=before, after=after))

    replace("JSphGpu.cpp", "host_implementation", '#include "JSphGpu.h"\n',
            '#include "JSphGpu.h"\n#define UPL_TPI_GPU_R1_IMPLEMENTATION\n#include "upl_tpi_gpu_r1.h"\n#undef UPL_TPI_GPU_R1_IMPLEMENTATION\n')
    replace("JSphGpu.cpp", "owner_free_before_reset", '  DestructorActive=true;\n',
            '  DestructorActive=true;\n  upl_tpi_gpu_r1::FreeOwner(UPL_TPI_GPU_OWNER); // No CUDA cleanup in static destruction.\n',
            'JSphGpu::~JSphGpu(){')
    replace("JSphHourglassGpu.h", "const_bulk_only_no_layout", '  tdouble3 GetRate(unsigned id)const;\n',
            '  tdouble3 GetRate(unsigned id)const;\n'
            '  const double2* GetHistoryDeviceReadonly()const{ return(Historyg); }\n'
            '  const double2* GetRateDeviceReadonly()const{ return(HistoryRateg); }\n')
    replace("JSphGpuSingle.cpp", "host_declarations", '#include "JSphHourglassGpu.h"\n',
            '#include "JSphHourglassGpu.h"\n#include "JDsFixedDt.h"\n#include "upl_tpi_gpu_r1.h"\n')
    qualification = '''
  if(upl_tpi_gpu_r1::Enabled()){
    upl_tpi_gpu_r1::Require(Simulate2D && TStep==STEP_Symplectic && CaseNp==1040 && CaseNfixed==40
      && CaseNfluid==1000 && CaseNpb==40 && !CaseNmoving && !CaseNfloat && !NpDynamic && !InOut
      && !Shifting && !Damping && !RelaxZones && !UseDEM && !Symmetry && !PartBegin && PartBeginDir.empty()
      && TimeStep==0. && Nstep==0 && TimeMax>0. && TimeMax<=.15
      && (!GaugeSystem || GaugeSystem->GetCount()==0),"Private GPU P1 requires fresh bounded C02 owners/topology");
    upl_tpi_gpu_r1::Require(FixedDt && FixedDt->GetFixedValue()==6.2501430511474609e-6
      && SymplecticDtPre==6.2501430511474609e-6 && HydroMech && HydroMechDynamicSeepage
      && PorosityObserver && PorosityFeedback && DynamicPorePressure && DynamicPoreWall
      && !DynamicPoreConductivity && !PoreShepardRegularization && SoilCte.Porosity==.3f
      && SoilCte.PoreWaterBulkModulus==2e8 && SoilCte.HydraulicConductivity==.0001f
      && SoilCte.PoreWaterRho==1000. && SoilCte.ModulusE==2e6f && SoilCte.PRvs==.3f && !StrainSoftening,
      "Private GPU P1 retains frozen constant-k elastic material and original necessary fixed-dt bounds");
    upl_tpi_gpu_r1::Require(TBoundary==BC_MDBC && SlipMode==SLIP_FreeSlip && !NoPenetration && PeriX && !PeriY && !PeriZ
      && TKernel==KERNEL_Wendland && Dp==.01 && KernelH==float(.018) && HourglassGpu && SoilHourglassXi==.1
      && SoilBoundaryDerivativeSPR && SoilStressRateGradCorr && !ArtificialStress && TVisco==VISCO_Artificial
      && Visco==.1f && ViscoBoundFactor==1.f && !ViscoTime && SoilDamping && SoilDampingCoef==.04f
      && TDensity==DDT_None && !DDTArray && Gravity.x==0. && Gravity.y==0. && Gravity.z==0.,
      "Private GPU P1 retains FreeSlip/SPR1/AV.1/HG.1/eta.04 and original kernel/periodic policy");
    upl_tpi_gpu_r1::Require(HydroMechInitMode==HMINIT_None && HydroMechTopLoadMode==HMLOAD_TopKernelBand
      && HydroMechTopLoadQ0==10000.f && HydroMechTopLoadRampTime==.0100002288818359375
      && HydroMechDrainage && HydroMechDrainageFixedGrid && HydroMechDrainageStartTime==.0100002288818359375,
      "Private GPU P1 retains actual source-clock ramp/drainage and normalized load");
    upl_tpi_gpu_r1::Init(UPL_TPI_GPU_OWNER,DirOut,UPL_TPI_GPU_VIEW,TimeStep,Nstep,SymplecticDtPre);
    Log->Print("UplTpiGpuR1: private Symplectic TPI-neighbour prediction/single leading-LP M0 beta0 variant; not paper LF/implicit/second-order/restart acceptance.");
  }
'''
    replace("JSphGpuSingle.cpp", "bounded_init", '  InitRunGpu();\n  RunGaugeSystem(TimeStep,true);',
            '  InitRunGpu();\n' + qualification + '  RunGaugeSystem(TimeStep,true);')
    pre = '''  if(upl_tpi_gpu_r1::Enabled())
    upl_tpi_gpu_r1::Begin(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW,PorePressPreg,PosxyPreg,PorePressg,
      TimeStep,Nstep,dt,IsHydroMechDrainageActive(),unsigned(HydroMechTopLoadMode));
  else if(HydroMech && PorePressg && PorePressPreg && PorePressRateg)
    cusph::UpdatePorePressureSymplectic(Np,Npb,dt05,Codeg,PorePressPreg,PorePressRateg,PorePressg
      ,DynamicPorePressure && IsHydroMechDrainageActive(),HydroMechTopLoadMode,PosxyPreg,FSTypeg);'''
    replace("JSphGpu.cpp", "history_predictor_only", '''  if(HydroMech && PorePressg && PorePressPreg && PorePressRateg)
    cusph::UpdatePorePressureSymplectic(Np,Npb,dt05,Codeg,PorePressPreg,PorePressRateg,PorePressg
      ,DynamicPorePressure && IsHydroMechDrainageActive(),HydroMechTopLoadMode,PosxyPreg,FSTypeg);''', pre)
    replace("JSphGpu.cpp", "actual_half_before_material_J", '  Timersg->TmStart(TMG_SuComputeStep,false);',
            '  if(upl_tpi_gpu_r1::Enabled())upl_tpi_gpu_r1::Corr(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW);\n  Timersg->TmStart(TMG_SuComputeStep,false);',
            'void JSphGpu::ComputeSymplecticCorr(double dt){')
    replace("JSphGpu.cpp", "original_single_J_capture", '  ComputeSymplecticPorosity(true,dt);',
            '  ComputeSymplecticPorosity(true,dt);\n  if(upl_tpi_gpu_r1::Enabled())upl_tpi_gpu_r1::CaptureJ(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW);',
            'void JSphGpu::ComputeSymplecticCorr(double dt){')
    replace("JSphGpu.cpp", "history_endpoint_guess_after_position", '''  if(HydroMech && DynamicPorePressure && PorePressg && PorePressPreg && PorePressRateg)
    cusph::UpdatePorePressureSymplectic(Np,Npb,dt,Codeg,PorePressPreg,PorePressRateg,PorePressg
      ,IsHydroMechDrainageActive(),HydroMechTopLoadMode,Posxyg,FSTypeg);''', '''  if(upl_tpi_gpu_r1::Enabled())
    upl_tpi_gpu_r1::Guess(UPL_TPI_GPU_VIEW,PorePressPreg,IsHydroMechDrainageActive(),unsigned(HydroMechTopLoadMode));
  else if(HydroMech && DynamicPorePressure && PorePressg && PorePressPreg && PorePressRateg)
    cusph::UpdatePorePressureSymplectic(Np,Npb,dt,Codeg,PorePressPreg,PorePressRateg,PorePressg
      ,IsHydroMechDrainageActive(),HydroMechTopLoadMode,Posxyg,FSTypeg);''')
    replace("JSphGpuSingle.cpp", "readonly_existing_HG_injection", '  if(HourglassGpu){\n    if(interstep==INTERSTEP_SymPredictor)',
            '  if(HourglassGpu && upl_tpi_gpu_r1::Enabled() && upl_tpi_gpu_r1::EndpointActive())\n'
            '    upl_tpi_gpu_r1::AddReadonlyHG(UPL_TPI_GPU_VIEW,Aceg,HourglassGpu,MassFluid,RhopZero,SoilCte.PoreWaterRho);\n'
            '  else if(HourglassGpu){\n    if(interstep==INTERSTEP_SymPredictor)',
            'void JSphGpuSingle::Interaction_Forces(TpInterStep interstep){')
    endpoint = '''    if(upl_tpi_gpu_r1::Enabled()){
      bool scratch=false;
      try{
        upl_tpi_gpu_r1::StartEndpoint(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW,TimeStep,Nstep,stepdt,HourglassGpu);
        scratch=true;Interaction_Forces(INTERSTEP_SymCorrector);
        const double endpointdt=DtVariable(false);
        upl_tpi_gpu_r1::Require(endpointdt==stepdt,"Private GPU endpoint fixed dt changed");
        upl_tpi_gpu_r1::PrepareFinal(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW,HourglassGpu);
        PosInteraction_Forces();scratch=false;
        upl_tpi_gpu_r1::WriteFinal(UPL_TPI_GPU_VIEW);
        ApplyPorePressureBoundaries();
        upl_tpi_gpu_r1::Commit(UPL_TPI_GPU_OWNER,UPL_TPI_GPU_VIEW,IsHydroMechDrainageActive(),unsigned(HydroMechTopLoadMode));
      }catch(...){upl_tpi_gpu_r1::AbortEndpoint();if(scratch){try{PosInteraction_Forces();}catch(...){}}throw;}
    }
'''
    replace("JSphGpuSingle.cpp", "endpoint_before_original_clock", '    else RunCellDivide(true);\n    TimeStep+=stepdt;',
            '    else RunCellDivide(true);\n' + endpoint + '    TimeStep+=stepdt;')
    replace("JSphGpuSingle.cpp", "sidecar_after_actual_SaveData", '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);',
            '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);\n'
            '  if(upl_tpi_gpu_r1::Enabled())upl_tpi_gpu_r1::Saved(UPL_TPI_GPU_OWNER,Part,TimeStep,Nstep,UPL_TPI_GPU_VIEW);')
    replace("JSphGpuSingle.cpp", "summary_before_FinishRun", '  FinishRun(partoutstop);',
            '  if(upl_tpi_gpu_r1::Enabled())upl_tpi_gpu_r1::Finish(UPL_TPI_GPU_OWNER,Nstep,TimeStep);\n  FinishRun(partoutstop);')
    replace("JSphGpu_ker.cu", "private_kernel_declarations", '#include "JSphGpu_ker.h"\n',
            '#include "JSphGpu_ker.h"\n#include "upl_tpi_gpu_r1.h"\n')
    replace("JSphGpu_ker.cu", "single_template_spatial_body", '__global__ void KerComputeDynamicPorePressureRate(unsigned np,unsigned npb',
            'template<bool CaptureRows> __global__ void KerComputeDynamicPorePressureRate(unsigned np,unsigned npb')
    method = 'template<bool CaptureRows> __global__ void KerComputeDynamicPorePressureRate(unsigned np,unsigned npb'
    replace("JSphGpu_ker.cu", "true_Dirichlet_row_before_return", '    if(drainfs && KerHydroMechIsDrainedParticle(p1,loadmode,posxy,code,fstype)){rate[p1]=0.f;return;}',
            '    if(drainfs && KerHydroMechIsDrainedParticle(p1,loadmode,posxy,code,fstype)){\n'
            '      if(CaptureRows)::upl_tpi_gpu_r1::CaptureRow(p1,true,0.,0.,theta[p1],porepress[p1]);\n'
            '      rate[p1]=0.f;return;}', method)
    replace("JSphGpu_ker.cu", "same_pair_diagonal_accumulator", '    double lp=0.,da=0.;',
            '    double lp=0.,da=0.;\n    double tpiSumWeights=0.;', method)
    replace("JSphGpu_ker.cu", "same_original_weight", '          lp+=w*dp;lx.x+=d.x*w;lx.y+=d.y*w;lx.z+=d.z*w;',
            '          if(CaptureRows)tpiSumWeights+=w;\n          lp+=w*dp;lx.x+=d.x*w;lx.y+=d.y*w;lx.z+=d.z*w;', method)
    replace("JSphGpu_ker.cu", "double_complete_R_before_legacy_float", '    rate[p1]=float(value); //-One complete overwrite, never add the compression source twice.',
            '    if(CaptureRows)::upl_tpi_gpu_r1::CaptureRow(p1,false,-__dmul_rn(khyd,tpiSumWeights),\n'
            '      __dadd_rn(-__dmul_rn(gamma,theta[p1]),__dmul_rn(khyd,lap)),theta[p1],porepress[p1]);\n'
            '    rate[p1]=float(value); //-Legacy scaled residual diagnostic, not the M0 dp/dt.', method)
    launch = '''    KerComputeDynamicPorePressureRate <<<sgrid,SPHBSIZE>>> (np,npb,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell+dvd.cellfluid,dcell
      ,posxy,posz,code,corrmat,ace,j,theta,porepress,rate,solid0,kw,rhow,khyd,gamma,vol0,invalid,conductivity,ck,maxspeed,wall,dvd.beginendcell,boundmode
      ,fstype,fsnormal,drainfs,closedfs,unsigned(loadmode));'''
    replace("JSphGpu_ker.cu", "same_public_wrapper_false_or_endpoint_true", launch,
            '    if(::upl_tpi_gpu_r1::CaptureEndpointHost()){\n' + launch.replace('KerComputeDynamicPorePressureRate <<<','KerComputeDynamicPorePressureRate<true> <<<') +
            '\n    }else{\n' + launch.replace('KerComputeDynamicPorePressureRate <<<','KerComputeDynamicPorePressureRate<false> <<<') + '\n    }')
    changed["JSphGpu_ker.cu"] += '\n// Private definitions outside the original cusph namespace.\n#include "upl_tpi_gpu_r1.cuh"\n'
    proof.append(dict(file="JSphGpu_ker.cu", anchor="private_definitions_after_original_namespaces", count=1))
    for e in frozen.values():same(e)
    same(admission_entry)
    OUT.mkdir();files=[]
    for name, data in original.items():
        target=OUT/name;body=changed[name].encode("utf-8") if name in changed else data
        with target.open("xb") as f:f.write(body)
        files.append(stat(target))
    for suffix in (".h", ".cuh"):
        target=OUT/(TAG+suffix)
        with target.open("xb") as f:f.write((T/"support"/target.name).read_bytes())
        files.append(stat(target))
    difference=dict(stage=TAG+".source_diff",passed=True,replacements=proof,
        unified_diff="\n".join("".join(difflib.unified_diff(baseline[n].splitlines(keepends=True),changed[n].splitlines(keepends=True),
          fromfile="frozen_gpu/"+n,tofile="private_P1/"+n)) for n in names),
        unchanged_other_263_files_copied_bytewise=True,old_kernel_external_signatures_changed=False,
        class_layout_or_virtual_ABI_changed=False,HG_cpp_recompile_for_complete_class_ODR=True,
        default_A_has_no_history_allocation_or_extra_endpoint=True,default_A_native_bit_proof_claimed=False,
        original_mechanics_J_kappa_update_count_unchanged=True,complete_R_retains_rhow_Da=True,
        static_destructor_has_no_CUDA_cleanup=True,public_source_changed=False,physical_acceptance=False)
    diff=OUT/"source_diff.json"
    with diff.open("x",encoding="utf-8",newline="\n") as f:json.dump(difference,f,ensure_ascii=False,indent=2);f.write("\n")
    for e in frozen.values():same(e)
    same(admission_entry)
    changed_sources=[stat(OUT/n) for n in names[:3]]
    record=dict(stage=TAG+".prepare",passed=True,root_admission=admission_entry,source_root=str(OUT),
        base_build_debug=base_builds["Debug"],base_build_release=base_builds["Release"],base_programs=base_programs,
        base_source_manifest=source_entry,base_source_entries=entries,author_files=authors,files=files,
        changed_sources=changed_sources,changed_headers=[stat(OUT/"JSphHourglassGpu.h")],
        recompile_sources=changed_sources+[stat(OUT/"JSphHourglassGpu.cpp")],source_diff=stat(diff),
        class_layout_or_virtual_ABI_changed=False,old_kernel_external_signatures_changed=False,
        unchanged_107_object_reuse_requires_configuration_matching=True,public_source_changed=False,
        private_scope="fresh constant-k X-periodic elastic C02 Symplectic TPI-neighbour prediction/single leading-LP M0 beta0 variant",
        paper_literal_LF=False,true_implicit_solution=False,second_order_claimed=False,physical_acceptance=False,
        builder_invocations=0,program_invocations=0,solver_invocations=0,native_invocations=0,SHA_scans=0,
        consumed_stats_unchanged=True)
    with RECEIPT.open("x",encoding="utf-8",newline="\n") as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write("\n")
    print(str(RECEIPT))


if __name__ == "__main__":main()
