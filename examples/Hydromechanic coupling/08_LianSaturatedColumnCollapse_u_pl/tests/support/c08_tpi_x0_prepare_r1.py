"""AUTHOR-FROZEN private CPU X0 overlay generator; prepare only, never build/run."""
from __future__ import annotations
import argparse
import difflib
import json
from pathlib import Path
import zipfile

T = Path(__file__).resolve().parents[1]
TAG = "c08_tpi_x0_r1"
OUT = T / "outputs" / (TAG + "_build")
BUILD = T / "logs/c08_preload_schema2_ReleaseCPU_r1.build.json"
HEADER = T / "support/c08_tpi_x0_r1.h"
NOTE = T / "notes/c08_tpi_x0_r1.md"

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
    record = T / "logs/c08_tpi_x0_r1.prepare.json"
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
            '#include "c08_tpi_x0_r1.h"\n\n#include <climits>\n')
    replace("JSphCpu.cpp", "single_extern_definition", 'using namespace std;\n',
            'using namespace std;\nnamespace c08x0 { State state; }\n')
    replace("JSphCpuSingle.cpp", "private_header", '#include "JSphCpuSingle.h"\n',
            '#include "JSphCpuSingle.h"\n#include "JDsFixedDt.h"\n#include "c08_tpi_x0_r1.h"\n')

    qualification = r'''
  if(c08x0::Requested()){
    c08x0::Need(Simulate2D && TStep==STEP_Symplectic && OmpThreads==1
      && CaseNp==1040 && CaseNfixed==40 && CaseNfluid==1000 && CaseNpb==40
      && !CaseNmoving && !CaseNfloat && !NpDynamic && !InOut && !Shifting && !Damping && !RelaxZones && !UseDEM && !Symmetry
      && (!GaugeSystem || GaugeSystem->GetCount()==0),"X0 only admits fresh CPU1 1040-ID no-gauge column");
    c08x0::Need(!PartBegin && PartBeginDir.empty() && !GravityPreload && !IsGravityPreloadHandoff()
      && TimeStep==0. && Nstep==0 && TimeMax==.15 && FixedDt && FixedDt->GetFixedValue()==c08x0::Dt
      && SymplecticDtPre==c08x0::Dt,"X0 fresh 5us/.15s clock contract rejected");
    c08x0::Need(HydroMech && HydroMechDynamicSeepage && PorosityObserver && PorosityFeedback && DynamicPorePressure
      && DynamicPoreWall && !DynamicPoreConductivity && !DynamicPoreFreeBody && !HydroMechNoWall
      && HydroMechInitMode==HMINIT_None && SoilCte.Porosity==.3f && SoilCte.PoreWaterBulkModulus==2e8
      && SoilCte.HydraulicConductivity==.0001f && SoilCte.PoreWaterRho==1000.
      && SoilCte.ModulusE==2e6f && SoilCte.PRvs==.3f && DPCtes==DP_PS,"X0 constant-k dynamic column contract rejected");
    c08x0::Need(TBoundary==BC_MDBC && SlipMode==SLIP_FreeSlip && !MdbcSlipModeByMk && !NoPenetration
      && PeriX && !PeriY && !PeriZ && PeriActive==1 && std::fabs(std::fabs(PeriXinc.x)-.1)<=64.*DBL_EPSILON*.1
      && PeriXinc.y==0. && PeriXinc.z==0. && TKernel==KERNEL_Wendland && Dp==.01
      && KernelH==float(.018) && RhopZero==2100.f,"X0 wall/kernel/geometry/periodic contract rejected");
    c08x0::Need(!HourglassCpu && SoilHourglassXi==0. && !PoreShepardRegularization && !ArtificialStress && !StrainSoftening
      && SoilBoundaryDerivativeSPR && SoilStressRateGradCorr && SoilDamping && SoilDampingCoef==.04f
      && TVisco==VISCO_Artificial && Visco==.1f && ViscoBoundFactor==1.f && !ViscoTime && TDensity==DDT_None && !DDTArray
      && Gravity.x==0. && Gravity.y==0. && Gravity.z==0.,"X0 only admits HG0/ShepardOFF/elastic SPR1/AV.1/G1/eta.04");
    c08x0::Need(HydroMechTopLoadMode==HMLOAD_TopKernelBand && HydroMechTopLoadQ0==10000.
      && HydroMechTopLoadRampTime==.01 && HydroMechDrainage && HydroMechDrainageFixedGrid
      && HydroMechDrainageStartTime==.01 && !HydroMechFreeSeepage,"X0 original decimal load/drain contract rejected");
    c08x0::Init(this,DirOut,Np,Idpc,Codec,PorePressc,PorePress0c,PoroJc,Kplasticc);
    Log->Print("C02TpiX0: private CPU1 beta0 alpha0.5 cold history; endpoint geometry/original source clock n; no paper-LF/implicit claim.");
  }
'''
    replace("JSphCpuSingle.cpp", "fresh_qualification_after_initialization", '  InitRunCpu();\n  RunGravityPreloadHandoffCpu();',
            '  InitRunCpu();\n' + qualification + '  RunGravityPreloadHandoffCpu();')

    pre = r'''
  if(c08x0::Requested()){
    c08x0::Begin(this,Np,Idpc,Codec,PorePressPrec,PoroJc,TimeStep,Nstep,dt);
    const bool drain=IsHydroMechDrainageActive();
    for(unsigned p=0;p<Np;p++){
      if(p<Npb || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
      else PorePressc[p]=(drain && IsHydroMechDrainedParticle(p,PosPrec,Codec,FSTypec)? 0.f: c08x0::Half(Idpc[p]));
      if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p]))c08x0::HalfActual(Idpc[p],PorePressc[p]);
    }
    return; // No finite-Kw predictor pressure update on X0.
  }
'''
    replace("JSphCpu.cpp", "history_half_instead_of_finite_Kw_predictor",
            '  const double dt05=dt*.5;\n', pre + '  const double dt05=dt*.5;\n',
            'void JSphCpu::ComputeSymplecticPrePorePressure(double dt){')
    corr = r'''
  if(c08x0::Requested()){
    c08x0::Need(dt==c08x0::state.dt,"X0 corrector dt changed");
    c08x0::Corr(this,Np,Idpc,Codec,PorePressc,PoroJc,PoroThetac);
    const bool drain=IsHydroMechDrainageActive();
    for(unsigned p=0;p<Np;p++){
      if(p<Npb || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
      else PorePressc[p]=(drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec)? 0.f: c08x0::Guess(Idpc[p]));
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
            '  if(c08x0::Requested())c08x0::CaptureJ(this,Np,Idpc,Codec,PoroJc);')
    for name in ("Pre", "Corr"):
        replace("JSphCpu.cpp", "X0_requires_actual_elastic_return_" + name,
                '  const bool requireelastic=RequireElasticGravityPreload();',
                '  const bool requireelastic=(RequireElasticGravityPreload() || c08x0::Requested());',
                'void JSphCpu::ComputeSymplectic' + name + '(double dt){')
    # Only this completed positive-FS cap is suppressed for the temporary guess.
    # ApplyFreeSurfacePorePressure (true drained0 + periodic copying) is untouched.
    replace("JSphCpu.cpp", "temporary_guess_skips_only_completed_positive_FS_cap",
            '  if(HydroMechFreeSeepage && !PorePressPrec){',
            '  if(HydroMechFreeSeepage && !PorePressPrec && !(c08x0::Requested() && c08x0::state.temporary)){',
            'void JSphCpu::ApplyPorePressureBoundaries(){')

    rate_method = 'template<TpKernel tker> void JSphCpu::ComputeDynamicPorePressureRateCpuT(){'
    replace("JSphCpu.cpp", "endpoint_row_context", '  DynamicConductivitySpeedMax=0.;',
            '  const bool x0endpoint=(c08x0::Requested() && c08x0::state.endpoint);\n'
            '  if(x0endpoint)c08x0::Need(c08x0::state.owner==this && !DynamicPoreConductivity,"X0 endpoint owner/constant-k changed");\n'
            '  DynamicConductivitySpeedMax=0.;', rate_method)
    replace("JSphCpu.cpp", "drained_row_priority", '      PorePressRatec[p1]=0; //-Dirichlet p is constrained; theta and J still evolve normally.',
            '      if(x0endpoint)c08x0::Row(Idpc[p1],true,0.,0.,PoroThetac[p1],PorePressc[p1]);\n'
            '      PorePressRatec[p1]=0; //-Dirichlet p is constrained; theta and J still evolve normally.', rate_method)
    replace("JSphCpu.cpp", "endpoint_diagonal_accumulator", '    double lp=0,da=0;',
            '    double lp=0,da=0;\n    double x0sumw=0.;', rate_method)
    replace("JSphCpu.cpp", "original_weight_sum_only_endpoint",
            '          lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);',
            '          if(x0endpoint)x0sumw+=w;\n          lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);', rate_method)
    replace("JSphCpu.cpp", "actual_double_unscaled_row_before_original_float_rate_store",
            '    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;',
            '    if(x0endpoint)c08x0::Row(Idpc[p1],false,-khyd*x0sumw,-gamma*PoroThetac[p1]+khyd*lap,PoroThetac[p1],PorePressc[p1]);\n'
            '    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;', rate_method)

    endpoint = r'''
    if(c08x0::Requested()){
      c08x0::Endpoint(this,Np,Idpc,Codec,PorePressc,PoroJc,TimeStep,Nstep,stepdt);
      bool forceScratch=false;
      try{
        forceScratch=true;
        Interaction_Forces(INTERSTEP_SymCorrector); // Third genuine force; no solid/material/J update.
        const double endpointdt=DtVariable(false); // Original necessary force/wave/pore limits, no final dt-stat commit.
        c08x0::Need(endpointdt==stepdt,"X0 endpoint fixed dt changed");
        c08x0::PrepareFinal(this,Np,Idpc,Codec,PoroJc);
        PosInteraction_Forces();forceScratch=false;
        c08x0::WriteFinal(Np,Npb,Idpc,Codec,PorePressc);
        c08x0::state.endpoint=false;c08x0::state.temporary=false;
        ApplyPorePressureBoundaries(); // Original final drainage/FS/positive-cap and periodic copying.
        const bool drain=IsHydroMechDrainageActive();
        for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p]))
          c08x0::state.commitDrained[Idpc[p]]=unsigned(drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec));
        c08x0::Commit(this,Np,Idpc,Codec,PorePressc,PoroJc); // Full history rotates exactly once after all checks.
      }
      catch(...){
        c08x0::state.endpoint=false;c08x0::state.temporary=false;
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
            '  if(c08x0::Requested())c08x0::Saved(this,Part,TimeStep,Nstep,Np,Idpc,Codec,PorePressc,PoroJc);')
    replace("JSphCpuSingle.cpp", "finish_implementation_counters",
            '  FinishRun(partoutstop);',
            '  if(c08x0::Requested())c08x0::Finish(this,Nstep,TimeStep);\n  FinishRun(partoutstop);')

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
            "default_OFF_no_private_allocations": True,
            "endpoint_original_source_clock": True, "physical_acceptance": False}
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
