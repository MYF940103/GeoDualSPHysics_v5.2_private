"""AUTHOR-DRAFT private C08 M0/TPI-negative CPU overlay generator; prepare only, never build/run."""
from __future__ import annotations
import argparse
import difflib
import json
from pathlib import Path
import zipfile

T = Path(__file__).resolve().parents[1]
TAG = "c08_tpi_negative_r1"
OUT = T / "outputs" / (TAG + "_build")
BUILD = T / "logs/c08_preload_schema2_ReleaseCPU_r1.build.json"
HEADER = T / "support/c08_tpi_negative_r1.h"
NOTE = T / "notes/c08_tpi_negative_r1.md"

def stat(path):
    p = Path(path).resolve()
    s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)

def same(entry):
    actual = stat(entry["path"])
    if actual["bytes"] != entry["bytes"] or actual["mtime_ns"] != entry["mtime_ns"]:
        raise RuntimeError("Frozen stat changed: " + entry["path"])
    return actual

def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--execution-authorized", action="store_true")
    args = a.parse_args()
    if not args.execution_authorized:
        raise SystemExit("Explicit root prepare admission required; no output created")
    if OUT.exists():
        raise RuntimeError("Private output already exists; preserve it, never overwrite")
    record = T / "logs/c08_tpi_negative_r1.prepare.json"
    if record.exists():
        raise RuntimeError("Prepare receipt exists; never overwrite")
    build_entry = stat(BUILD)
    build = json.loads(BUILD.read_text(encoding="utf-8-sig"))
    if not (build["passed"] and build["configuration"] == "ReleaseCPU" and
            build["consumed_stats_unchanged"] and build["solver_invocations"] == 0):
        raise RuntimeError("Passed frozen schema2 CPU build required")
    archive = same(build["source_archive"])
    capture = same(build["source_capture"])
    program = same(build["program"])
    helper_entry, note_entry = stat(HEADER), stat(NOTE)
    with zipfile.ZipFile(archive["path"]) as z:
        originals = {n: z.read("src/source/" + n).decode("utf-8").replace("\r\n", "\n")
                     for n in ("JSphCpu.cpp", "JSphCpuSingle.cpp")}
    changed = dict(originals)
    proof = []

    def replace(file, name, before, after, method=None):
        source = changed[file]
        if method is None:
            count = source.count(before)
            if count != 1:
                raise RuntimeError(name + " count is " + str(count) + ", expected 1")
            source = source.replace(before, after, 1)
        else:
            start = source.find(method)
            if start < 0 or source.count(method) != 1:
                raise RuntimeError(name + " unique method anchor absent")
            next_method = source.find("\n//==============================================================================", start + len(method))
            if next_method < 0:
                next_method = len(source)
            body = source[start:next_method]
            count = body.count(before)
            if count != 1:
                raise RuntimeError(name + " scoped count is " + str(count) + ", expected 1")
            source = source[:start] + body.replace(before, after, 1) + source[next_method:]
        changed[file] = source
        proof.append(dict(file=file, anchor=name, count=count, method_scope=method,
                          before=before, after=after))

    replace("JSphCpu.cpp", "private_header", '#include <climits>\n',
            '#include "c08_tpi_negative_r1.h"\n\n#include <climits>\n')
    replace("JSphCpu.cpp", "single_extern_definition", 'using namespace std;\n',
            'using namespace std;\nnamespace c08negative { State state; }\n')
    replace("JSphCpuSingle.cpp", "private_header", '#include "JSphCpuSingle.h"\n',
            '#include "JSphCpuSingle.h"\n#include "JDsFixedDt.h"\n#include "c08_tpi_negative_r1.h"\n')

    qualification = r'''
  if(c08negative::Requested()){
    c08negative::RejectHGEnvironment();(void)c08negative::RequestedBeta();
    c08negative::Need(Simulate2D && TStep==STEP_Symplectic && OmpThreads==1
      && CaseNp==7060 && CaseNfixed==2060 && CaseNfluid==5000 && CaseNpb==2060
      && !CaseNmoving && !CaseNfloat && !NpDynamic && !InOut && !Shifting && !Damping && !RelaxZones && !UseDEM && !Symmetry
      && (!GaugeSystem || GaugeSystem->GetCount()==0),"Private C08 TPI requires CPU1 bed-last 7060-ID source geometry and no gauge/dynamic topology");
    c08negative::Need(!PartBegin && PartBeginDir.empty() && GravityPreload && IsGravityPreloadHandoff()
      && !GravityPreloadElasticSource && !GravityPreloadKeepBedOverlap && !GravityPreloadReleased
      && GravityPreloadTime==10. && GravityPreloadStep==c08negative::SourceStep
      && GravityPreloadMkBound==2 && GravityPreloadIdBegin==1805 && GravityPreloadIdCount==255
      && TimeStep==0. && Nstep==0 && TimeMax>10. && TimeMax<=13.
      && FixedDt && FixedDt->GetFixedValue()==c08negative::Dt && SymplecticDtPre==c08negative::Dt,
      "Private C08 TPI requires schema2 same-material 10s/2M PRE and a separately capped target");
    c08negative::Need(HydroMech && HydroMechDynamicSeepage && PorosityObserver && PorosityFeedback && DynamicPorePressure
      && DynamicPoreWall && DynamicPoreConductivity && HydroMechConductivityModel==1 && HydroMechConductivityCk==2.
      && !DynamicPoreFreeBody && !HydroMechNoWall && HydroMechInitMode==HMINIT_ConstantZ
      && SoilCte.Porosity==.35f && SoilCte.PoreWaterBulkModulus==1e9 && SoilCte.HydraulicConductivity==.0002f
      && SoilCte.PoreWaterRho==1000. && SoilCte.ModulusE==2e7f && SoilCte.PRvs==.33f && DPCtes==DP_PS
      && IsDynamicPorePlasticConfig(),"Private C08 TPI original dynamic/variable-k/plastic material contract rejected");
    c08negative::Need(TBoundary==BC_MDBC && SlipMode==SLIP_FreeSlip && MdbcSlipModeByMk && NoPenetration
      && !PeriActive && TKernel==KERNEL_Wendland && Dp==.04 && KernelH==float(.072)
      && !HourglassCpu && SoilHourglassXi==0. && !SoilBoundaryDerivativeSPR && SoilStressRateGradCorr
      && ArtificialStress && ArtificialStressCoef==.3f && ArtificialStressExp==2.55f
      && TVisco==VISCO_Artificial && Visco==.1f && ViscoBoundFactor==1.f && !ViscoTime
      && TDensity==DDT_None && !DDTArray && Gravity.x==0. && Gravity.y==0. && Gravity.z==-9.81f,
      "Private C08 TPI original HG0/AS.3n2.55/AV.1/mixed-slip/plane/kernel configuration rejected");
    c08negative::Need(HydroMechTopLoadMode==HMLOAD_None && !HydroMechDrainage && !HydroMechDrainageFixedGrid
      && HydroMechFreeSeepage,"Private C08 TPI preserves original completed-only free seepage");
    Log->Print("C08TpiNegative: private M0/original-space Symplectic endpoint extension; alpha .5, explicit beta 0 or .04/m; cold history, no literal LF/implicit/physics claim.");
  }
'''
    replace("JSphCpuSingle.cpp", "fresh_qualification_after_initialization", '  InitRunCpu();\n  RunGravityPreloadHandoffCpu();',
            '  InitRunCpu();\n' + qualification + '  RunGravityPreloadHandoffCpu();')

    released_init = r'''
    if(c08negative::Requested() && !c08negative::state.ready){
      c08negative::Need(GravityPreloadReleased && IsGravityPreloadHandoff() && !GravityPreloadKeepBedOverlap
        && Np==6805 && Npb==1805 && !SoilDamping && !PoreShepardRegularization
        && UseDynamicPorePlaneContact() && !HourglassCpu && SoilHourglassXi==0.
        && TimeStep==GravityPreloadActualTime && unsigned(Nstep)==GravityPreloadActualStep,
        "C08 TPI cold history starts only after actual same-material handoff and retire255");
      c08negative::Init(this,DirOut,Np,Npb,Idpc,Codec,PorePressc,PorePress0c,PoroJc,Kplasticc,TimeStep,unsigned(Nstep),SymplecticDtPre);
    }
'''
    replace("JSphCpuSingle.cpp", "cold_history_after_actual_original_release",
            '    if(GravityPreload && !GravityPreloadReleased)RunGravityPreloadRelease();',
            '    if(GravityPreload && !GravityPreloadReleased)RunGravityPreloadRelease();\n'+released_init)

    pre = r'''
  if(c08negative::Requested()){
    c08negative::Begin(this,Np,Idpc,Codec,PorePressPrec,PoroJc,TimeStep,Nstep,dt);
    const bool drain=IsHydroMechDrainageActive();
    for(unsigned p=0;p<Np;p++){
      if(p<Npb || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
      else PorePressc[p]=(drain && IsHydroMechDrainedParticle(p,PosPrec,Codec,FSTypec)? 0.f: c08negative::Half(Idpc[p]));
      if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p]))c08negative::HalfActual(Idpc[p],PorePressc[p]);
    }
    return; // No finite-Kw predictor pressure update on C08 TPI.
  }
'''
    replace("JSphCpu.cpp", "history_half_instead_of_finite_Kw_predictor",
            '  const double dt05=dt*.5;\n', pre + '  const double dt05=dt*.5;\n',
            'void JSphCpu::ComputeSymplecticPrePorePressure(double dt){')
    corr = r'''
  if(c08negative::Requested()){
    c08negative::Need(dt==c08negative::state.dt,"C08 TPI corrector dt changed");
    c08negative::Corr(this,Np,Idpc,Codec,PorePressc,PoroJc,PoroThetac);
    const bool drain=IsHydroMechDrainageActive();
    for(unsigned p=0;p<Np;p++){
      if(p<Npb || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
      else PorePressc[p]=(drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec)? 0.f: c08negative::Guess(Idpc[p]));
    }
    return; // No finite-Kw corrector pressure update or history rotation here.
  }
'''
    replace("JSphCpu.cpp", "history_guess_instead_of_finite_Kw_corrector",
            '  const bool drainfs=(DynamicPorePressure && IsHydroMechDrainageActive());\n',
            corr + '  const bool drainfs=(DynamicPorePressure && IsHydroMechDrainageActive());\n',
            'void JSphCpu::ComputeSymplecticCorrPorePressure(double dt){')
    replace("JSphCpu.cpp", "capture_single_original_J_corrector",
            '  ComputeSymplecticCorrPorePressure(dt);\n  ComputeSymplecticCorrPorosity(dt);',
            '  ComputeSymplecticCorrPorePressure(dt);\n  ComputeSymplecticCorrPorosity(dt);\n'
            '  if(c08negative::Requested())c08negative::CaptureJ(this,Np,Idpc,Codec,PoroJc);')
    # Only this completed positive-FS cap is suppressed for the temporary guess.
    # ApplyFreeSurfacePorePressure (true drained0 + periodic copying) is untouched.
    replace("JSphCpu.cpp", "temporary_guess_skips_only_completed_positive_FS_cap",
            '  if(HydroMechFreeSeepage && !PorePressPrec){',
            '  if(HydroMechFreeSeepage && !PorePressPrec && !(c08negative::Requested() && c08negative::state.temporary)){',
            'void JSphCpu::ApplyPorePressureBoundaries(){')

    rate_method = 'template<TpKernel tker> void JSphCpu::ComputeDynamicPorePressureRateCpuT(){'
    replace("JSphCpu.cpp", "endpoint_row_context", '  DynamicConductivitySpeedMax=0.;',
            '  const bool negativeEndpoint=(c08negative::Requested() && c08negative::state.endpoint);\n'
            '  if(negativeEndpoint)c08negative::Need(c08negative::state.owner==this,"C08 TPI endpoint owner changed");\n'
            '  DynamicConductivitySpeedMax=0.;', rate_method)
    replace("JSphCpu.cpp", "drained_row_priority", '      PorePressRatec[p1]=0; //-Dirichlet p is constrained; theta and J still evolve normally.',
            '      if(negativeEndpoint)c08negative::Row(Idpc[p1],true,0.,0.,PoroThetac[p1],PorePressc[p1]);\n'
            '      PorePressRatec[p1]=0; //-Dirichlet p is constrained; theta and J still evolve normally.', rate_method)
    replace("JSphCpu.cpp", "endpoint_diagonal_accumulator", '    double lp=0,da=0;',
            '    double lp=0,da=0;\n    double tpiSumWeights=0.,tpiChain=0.;', rate_method)
    replace("JSphCpu.cpp", "original_weight_sum_only_endpoint",
            '          lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);',
            '          if(negativeEndpoint)tpiSumWeights+=w;\n          lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);', rate_method)
    replace("JSphCpu.cpp", "actual_double_unscaled_row_before_original_float_rate_store",
            '    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;',
            '    if(negativeEndpoint)c08negative::Row(Idpc[p1],false,-ki*tpiSumWeights,-gamma*PoroThetac[p1]+ki*lap+tpiChain,PoroThetac[p1],PorePressc[p1]);\n'
            '    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;', rate_method)

    replace("JSphCpu.cpp", "capture_actual_variable_k_chain_without_reconstruction",
            '      rate=kw/porosity*(-PoroThetac[p1]+ki/gamma*lap+chain/gamma);',
            '      if(negativeEndpoint)tpiChain=chain;\n      rate=kw/porosity*(-PoroThetac[p1]+ki/gamma*lap+chain/gamma);', rate_method)

    endpoint = r'''
    if(c08negative::Requested()){
      c08negative::Endpoint(this,Np,Idpc,Codec,Posc,Velrhopc,Sigmac,Kplasticc,PorePress0c,PorePressc,PoroJc,TimeStep,Nstep,stepdt);
      bool forceScratch=false;
      try{
        forceScratch=true;
        Interaction_Forces(INTERSTEP_SymCorrector); // Third genuine force; no solid/material/J update.
        const double endpointdt=DtVariable(false); // Original necessary force/wave/pore limits, no final dt-stat commit.
        c08negative::Need(endpointdt==stepdt,"C08 TPI endpoint fixed dt changed");
        c08negative::PrepareFinal(this,Np,Idpc,Codec,Posc,Velrhopc,Sigmac,Kplasticc,PorePress0c,PorePressc,PoroJc);
        PosInteraction_Forces();forceScratch=false;
        c08negative::WriteFinal(Np,Npb,Idpc,Codec,PorePressc);
        c08negative::state.endpoint=false;c08negative::state.temporary=false;
        ApplyPorePressureBoundaries(); // Original final drainage/FS/positive-cap and periodic copying.
        const bool drain=IsHydroMechDrainageActive();
        for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p]))
          c08negative::state.commitDrained[Idpc[p]]=unsigned(drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec));
        c08negative::Commit(this,Np,Idpc,Codec,FSTypec,PorePressc,PorePress0c,PoroJc); // Full history rotates exactly once after all checks.
      }
      catch(...){
        c08negative::state.endpoint=false;c08negative::state.temporary=false;
        if(forceScratch)PosInteraction_Forces();
        throw; // No history commit or new SaveData on failed endpoint.
      }
    }
'''
    replace("JSphCpuSingle.cpp", "third_force_after_original_completed_geometry_before_clock_increment",
            '    else RunCellDivide(true);\n    TimeStep+=stepdt;',
            '    else RunCellDivide(true);\n' + endpoint + '    TimeStep+=stepdt;')
    replace("JSphCpuSingle.cpp", "save_only_sidecar_after_real_native_save",
            '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);',
            '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);\n'
            '  if(c08negative::Requested())c08negative::Saved(this,Part,TimeStep,Nstep,Np,Idpc,Codec,PorePressc,PoroJc);')
    replace("JSphCpuSingle.cpp", "finish_implementation_counters",
            '  FinishRun(partoutstop);',
            '  if(c08negative::Requested())c08negative::Finish(this,Nstep,TimeStep);\n  FinishRun(partoutstop);')

    # No execution of generated source occurs here. All outputs are new and exclusive.
    for n in originals:
        if changed[n] == originals[n]:
            raise RuntimeError("No private changes generated for " + n)
    same(build_entry);same(archive);same(capture);same(program);same(helper_entry);same(note_entry)
    OUT.mkdir()
    generated = []
    for n in originals:
        p = OUT / n
        with p.open("x", encoding="utf-8", newline="\n") as f:
            f.write(changed[n])
        generated.append(stat(p))
    h = OUT / HEADER.name
    with h.open("xb") as f:
        f.write(HEADER.read_bytes())
    generated.append(stat(h))
    diff = {"stage": TAG + ".source_diff", "passed": True,
            "archive": archive, "header": helper_entry, "replacements": proof,
            "normalized_line_endings_only_outside_replacements": True,
            "unified_diff": "\n".join("".join(difflib.unified_diff(
                originals[n].splitlines(keepends=True), changed[n].splitlines(keepends=True),
                fromfile="archive/" + n, tofile="private/" + n)) for n in originals),
            "public_files_changed": False, "class_or_header_ABI_changed": False,
            "default_OFF_no_private_allocations": True, "M0_ON_not_finite_Kw": True,
            "beta_selected_only_later_by_root_env": True, "cold_previous_from_actual_schema2_pn": True,
            "endpoint_original_source_clock": True, "HG_rejected": True, "original_plastic_return_unchanged": True, "no_new_CellDivide_NoPen_Shepard_in_extra_force": True, "physical_acceptance": False}
    p = OUT / "source_diff.json"
    with p.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(diff, f, ensure_ascii=False, indent=2)
        f.write("\n")
    generated.append(stat(p))
    same(build_entry);same(archive);same(capture);same(program);same(helper_entry);same(note_entry)
    receipt = dict(stage=TAG + ".prepare", passed=True, source_build=build_entry,
        source_archive=archive, source_capture=capture, original_program=program,
        author_header=helper_entry, note=note_entry, generated=generated,
        source_diff=stat(p), replacements=len(proof), consumed_stats_unchanged=True,
        builder_invocations=0, program_invocations=0, solver_invocations=0,
        native_invocations=0, public_source_changed=False, physical_acceptance=False, SHA_scans=0)
    with record.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(str(record))

if __name__ == "__main__":
    main()
