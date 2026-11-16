"""Prepare the private P1 beta0 two-TU CPU overlay; never build or run a program."""
from __future__ import annotations
import argparse
import difflib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_cpu_r1"
AUTHOR = T / "support"
BUILD = T / "logs/upl_spr_av_ReleaseCPU_r1.build.json"
BASE_XML = T / "configs/upl_bigstep_2tv_CPU1_r1.xml"
OUT = T / "outputs/upl_tpi_cpu_r1_source"
RECEIPT = T / "logs/upl_tpi_cpu_r1.prepare.json"


def stat(path):
    p = Path(path).resolve()
    s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def same(entry):
    actual = stat(entry["path"])
    if actual != {k: entry[k] for k in ("path", "bytes", "mtime_ns")}:
        raise RuntimeError("Root-frozen stat changed: " + entry["path"])
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    parser.add_argument("--admission", type=Path, required=True,
                        help="Independently reviewed root prepare admission; no solver admission implied")
    args = parser.parse_args()
    if not args.execution_authorized:
        raise SystemExit("Explicit root prepare admission required; no output created")
    if OUT.exists() or RECEIPT.exists():
        raise RuntimeError("Prepare output or receipt exists; preserve it, never overwrite")
    admission_entry = stat(args.admission)
    admission = json.loads(args.admission.read_text(encoding="utf-8-sig"))
    if not (admission.get("stage") == "upl_tpi_cpu_r1.prepare_admission" and
            admission.get("passed") is True and admission.get("prepare_only") is True):
        raise RuntimeError("Reviewed root prepare-only admission required")
    frozen = {str(Path(e["path"]).resolve()): e for e in admission["inputs"]}

    def admitted(path):
        p = str(Path(path).resolve())
        if p not in frozen:
            raise RuntimeError("Consumed input absent from root admission: " + p)
        return same(frozen[p])

    build_entry = admitted(BUILD)
    base_xml_entry = admitted(BASE_XML)
    author_entries = [admitted(AUTHOR / (TAG + suffix))
                      for suffix in (".h", "_prepare.py")]
    author_entries.append(admitted(T / "notes/upl_tpi_cpu_r1_design.md"))
    build = json.loads(BUILD.read_text(encoding="utf-8-sig"))
    if not (build.get("passed") is True and build.get("configuration") == "ReleaseCPU" and
            build.get("object_count") == 86 and build.get("non_main_object_count") == 85 and
            build.get("exact_object_basename_closure") is True):
        raise RuntimeError("Exact completed C02 full-A CPU Release source/object recipe required")
    base_program = admitted(build["program"]["path"])
    # The final A flat source snapshot, not current public source or C08 schema2.
    entries = build["source_snapshot"]
    if len(entries) != 265:
        raise RuntimeError("Expected final-A 265-file source/header snapshot")
    originals_bytes = {}
    base_source_entries = []
    for entry in entries:
        old = entry["snapshot"]
        current = admitted(old["path"])
        p = Path(current["path"])
        if current["bytes"] != old["bytes"] or p.name in originals_bytes:
            raise RuntimeError("Baseline snapshot size/name closure changed")
        originals_bytes[p.name] = p.read_bytes()
        base_source_entries.append(dict(original_receipt=old, snapshot=current))
    originals = {name: originals_bytes[name].decode("utf-8-sig").replace("\r\n", "\n")
                 for name in ("JSphCpu.cpp", "JSphCpuSingle.cpp")}
    changed = dict(originals)
    proof = []

    def replace(file, name, before, after, method=None):
        source = changed[file]
        if method is None:
            count = source.count(before)
            if count != 1:
                raise RuntimeError(name + " count=" + str(count) + ", expected 1")
            source = source.replace(before, after, 1)
        else:
            if source.count(method) != 1:
                raise RuntimeError(name + " unique method absent")
            begin = source.index(method)
            end = source.find("\n//==============================================================================", begin + len(method))
            if end < 0:
                end = len(source)
            body = source[begin:end]
            count = body.count(before)
            if count != 1:
                raise RuntimeError(name + " scoped count=" + str(count) + ", expected 1")
            source = source[:begin] + body.replace(before, after, 1) + source[end:]
        changed[file] = source
        proof.append(dict(file=file, anchor=name, count=count, method_scope=method,
                          before=before, after=after))

    dt_values = [n.attrib["value"] for n in ET.parse(BASE_XML).getroot().iter("parameter")
                 if n.attrib.get("key") == "DtFixed"]
    if len(dt_values) != 1:
        raise RuntimeError("Unique actual full-A fixed dt absent")
    dt = float(dt_values[0])
    if dt != 6.250143051147461e-6:
        raise RuntimeError("Full-A fixed dt changed")
    # Decimal round-trip literal is valid in the original MSVC C++14 mode.
    dt_cpp = format(dt, ".17g")
    replace("JSphCpu.cpp", "private_header", '#include <climits>\n',
            '#include "upl_tpi_cpu_r1.h"\n\n#include <climits>\n')
    replace("JSphCpu.cpp", "single_state_definition", 'using namespace std;\n',
            'using namespace std;\nnamespace upl_tpi_cpu_r1 { State state; }\n')
    replace("JSphCpuSingle.cpp", "private_header", '#include "JSphCpuSingle.h"\n',
            '#include "JSphCpuSingle.h"\n#include "JDsFixedDt.h"\n#include "upl_tpi_cpu_r1.h"\n')
    qualification = r'''
  if(upl_tpi_cpu_r1::Enabled()){
    upl_tpi_cpu_r1::Need(Simulate2D && TStep==STEP_Symplectic && OmpThreads>=1
      && CaseNp==1040 && CaseNfixed==40 && CaseNfluid==1000 && CaseNpb==40
      && !CaseNmoving && !CaseNfloat && !NpDynamic && !InOut && !Shifting && !Damping && !RelaxZones && !UseDEM && !Symmetry
      && !PartBegin && PartBeginDir.empty() && TimeStep==0. && Nstep==0 && TimeMax>0. && TimeMax<=.15
      && (!GaugeSystem || GaugeSystem->GetCount()==0),"P1 requires the fresh bounded C02 native set, no restart or dynamic topology");
    upl_tpi_cpu_r1::Need(FixedDt && FixedDt->GetFixedValue()==BASE_DT && SymplecticDtPre==BASE_DT,
      "P1 retains the actual complete finite-Kw baseline fixed dt");
    upl_tpi_cpu_r1::Need(HydroMech && HydroMechDynamicSeepage && PorosityObserver && PorosityFeedback && DynamicPorePressure
      && DynamicPoreWall && !DynamicPoreConductivity && !PoreShepardRegularization
      && SoilCte.Porosity==.3f && SoilCte.PoreWaterBulkModulus==2e8 && SoilCte.HydraulicConductivity==.0001f
      && SoilCte.PoreWaterRho==1000. && SoilCte.ModulusE==2e6f && SoilCte.PRvs==.3f && !StrainSoftening,
      "P1 retains the original constant-k elastic full-A dynamic-column material");
    upl_tpi_cpu_r1::Need(TBoundary==BC_MDBC && SlipMode==SLIP_FreeSlip && !NoPenetration
      && PeriX && !PeriY && !PeriZ && TKernel==KERNEL_Wendland && Dp==.01 && KernelH==float(.018)
      && HourglassCpu && SoilHourglassXi==.1 && SoilBoundaryDerivativeSPR && SoilStressRateGradCorr
      && !ArtificialStress && TVisco==VISCO_Artificial && Visco==.1f && ViscoBoundFactor==1.f && !ViscoTime
      && SoilDamping && SoilDampingCoef==.04f && TDensity==DDT_None && !DDTArray
      && Gravity.x==0. && Gravity.y==0. && Gravity.z==0.,
      "P1 retains full-A HG.1/SPR1/AV.1/eta.04, kernel, FreeSlip and x-periodicity");
    upl_tpi_cpu_r1::Need(HydroMechInitMode==HMINIT_None && HydroMechTopLoadMode==HMLOAD_TopKernelBand
      && HydroMechTopLoadQ0==10000.f && HydroMechTopLoadRampTime==.0100002288818359375
      && HydroMechDrainage && HydroMechDrainageFixedGrid && HydroMechDrainageStartTime==.0100002288818359375,
      "P1 retains original ramp, normalized band load and fixed-grid drainage event");
    upl_tpi_cpu_r1::Init(this,DirOut,Np,Idpc,Codec,PorePressc,PorePress0c,PoroJc,Kplasticc,TimeStep,Nstep,SymplecticDtPre);
    Log->Print("UplTpiCpuR1: private M0 beta0; B alpha.5 or C alpha0; true ID-owned cold history; endpoint extension, not literal LF/second-order/full-implicit/restart acceptance.");
  }
'''.replace("BASE_DT", dt_cpp)
    replace("JSphCpuSingle.cpp", "bounded_fresh_column_qualification", '  InitRunCpu();\n  RunGaugeSystem(TimeStep,true);',
            '  InitRunCpu();\n' + qualification + '  RunGaugeSystem(TimeStep,true);')
    pre = r'''
  if(upl_tpi_cpu_r1::Enabled()){
    const bool drain=IsHydroMechDrainageActive();
    const auto sourceDrained=[&](unsigned p){return drain && IsHydroMechDrainedParticle(p,PosPrec,Codec,FSTypec);};
    upl_tpi_cpu_r1::Begin(this,Np,Idpc,Codec,PorePressPrec,PoroJc,TimeStep,Nstep,dt,sourceDrained);
    for(unsigned p=0;p<Np;p++){
      if(p<Npb || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
      else PorePressc[p]=(drain && IsHydroMechDrainedParticle(p,PosPrec,Codec,FSTypec)? 0.f: upl_tpi_cpu_r1::Half(Idpc[p]));
      if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p]))upl_tpi_cpu_r1::HalfActual(Idpc[p],PorePressc[p]);
    }
    return; // B/C replace only pressure integration; original solid/J predictors follow.
  }
'''
    replace("JSphCpu.cpp", "history_mechanical_half", '  const double dt05=dt*.5;\n',
            pre + '  const double dt05=dt*.5;\n', 'void JSphCpu::ComputeSymplecticPrePorePressure(double dt){')
    corr = r'''
  if(upl_tpi_cpu_r1::Enabled()){
    upl_tpi_cpu_r1::Need(dt==upl_tpi_cpu_r1::state.dt,"P1 corrector fixed dt changed");
    upl_tpi_cpu_r1::Corr(this,Np,Idpc,Codec,PorePressc,PoroJc,PoroThetac);
    const bool drain=IsHydroMechDrainageActive();
    for(unsigned p=0;p<Np;p++){
      if(p<Npb || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
      else PorePressc[p]=(drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec)? 0.f: upl_tpi_cpu_r1::Guess(Idpc[p]));
    }
    return; // Not a history rotation or a second solid/material/J update.
  }
'''
    replace("JSphCpu.cpp", "history_endpoint_guess", '  const bool drainfs=(DynamicPorePressure && IsHydroMechDrainageActive());\n',
            corr + '  const bool drainfs=(DynamicPorePressure && IsHydroMechDrainageActive());\n',
            'void JSphCpu::ComputeSymplecticCorrPorePressure(double dt){')
    replace("JSphCpu.cpp", "capture_original_single_J_corrector", '  ComputeSymplecticCorrPorePressure(dt);\n  ComputeSymplecticCorrPorosity(dt);',
            '  ComputeSymplecticCorrPorePressure(dt);\n  ComputeSymplecticCorrPorosity(dt);\n'
            '  if(upl_tpi_cpu_r1::Enabled())upl_tpi_cpu_r1::CaptureJ(this,Np,Idpc,Codec,PoroJc);')
    rate_method = 'void JSphCpu::ComputeDynamicPorePressureRateCpu(){'
    replace("JSphCpu.cpp", "endpoint_row_context", '  DynamicConductivitySpeedMax=0.;',
            '  const bool tpiEndpoint=(upl_tpi_cpu_r1::Enabled() && upl_tpi_cpu_r1::state.endpoint);\n'
            '  if(tpiEndpoint)upl_tpi_cpu_r1::Need(upl_tpi_cpu_r1::state.owner==this,"P1 endpoint owner changed");\n'
            '  DynamicConductivitySpeedMax=0.;', rate_method)
    replace("JSphCpu.cpp", "true_drained_row_priority", '      PorePressRatec[p1]=0; //-Dirichlet p is constrained; theta and J still evolve normally.',
            '      if(tpiEndpoint)upl_tpi_cpu_r1::Row(Idpc[p1],true,0.,0.,PoroThetac[p1],PorePressc[p1]);\n'
            '      PorePressRatec[p1]=0; //-Dirichlet p is constrained; theta and J still evolve normally.', rate_method)
    replace("JSphCpu.cpp", "double_diagonal_sum", '    double lp=0,da=0;',
            '    double lp=0,da=0;\n    double tpiSumWeights=0.;', rate_method)
    replace("JSphCpu.cpp", "same_original_pair_weight", '          lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);',
            '          if(tpiEndpoint)tpiSumWeights+=w;\n          lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);', rate_method)
    replace("JSphCpu.cpp", "double_row_before_existing_float_rate", '    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;',
            '    if(tpiEndpoint)upl_tpi_cpu_r1::Row(Idpc[p1],false,-khyd*tpiSumWeights,-gamma*PoroThetac[p1]+khyd*lap,PoroThetac[p1],PorePressc[p1]);\n'
            '    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;', rate_method)
    # Keep both real HG force/update transitions unchanged. A third original
    # CorrectorForce would violate its phase machine, so read committed Q/Mref
    # through public const accessors and use the frozen AddHistory arithmetic.
    replace("JSphCpuSingle.cpp", "readonly_HG_endpoint_force", '  if(HourglassCpu){\n    if(interstep==INTERSTEP_SymPredictor)',
            '  if(HourglassCpu && upl_tpi_cpu_r1::Enabled() && upl_tpi_cpu_r1::state.endpoint){\n'
            '    upl_tpi_cpu_r1::AddReadonlyHG(HourglassCpu,Np,Npb,Idpc,Codec,Acec,PoroJc,MassFluid,RhopZero,SoilCte.PoreWaterRho);\n'
            '  }\n  else if(HourglassCpu){\n    if(interstep==INTERSTEP_SymPredictor)',
            'void JSphCpuSingle::Interaction_Forces(TpInterStep interstep){')
    endpoint = r'''
    if(upl_tpi_cpu_r1::Enabled()){
      upl_tpi_cpu_r1::Endpoint(this,Np,Idpc,Codec,Posc,Velrhopc,Sigmac,Kplasticc,PorePress0c,PorePressc,PoroJc,TimeStep,Nstep,stepdt);
      upl_tpi_cpu_r1::CaptureHG(HourglassCpu);
      bool forceScratch=false;
      try{
        forceScratch=true;
        Interaction_Forces(INTERSTEP_SymCorrector); // Extra endpoint evaluation; no solid/J/material update.
        const double endpointdt=DtVariable(false); // Existing necessary limits retained for this same-dt P1 prototype.
        upl_tpi_cpu_r1::Need(endpointdt==stepdt,"P1 endpoint fixed dt changed");
        upl_tpi_cpu_r1::CheckHG(HourglassCpu);
        upl_tpi_cpu_r1::PrepareFinal(this,Np,Idpc,Codec,Posc,Velrhopc,Sigmac,Kplasticc,PorePress0c,PorePressc,PoroJc);
        PosInteraction_Forces();forceScratch=false;
        upl_tpi_cpu_r1::WriteFinal(Np,Npb,Idpc,Codec,PorePressc);
        upl_tpi_cpu_r1::state.endpoint=false;upl_tpi_cpu_r1::state.temporary=false;
        ApplyPorePressureBoundaries(); // Original actual-clock FS/drainage/periodic policy.
        const bool drain=IsHydroMechDrainageActive();
        for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p]))
          upl_tpi_cpu_r1::SetCommitDrained(Idpc[p],drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec));
        upl_tpi_cpu_r1::Commit(this,Np,Idpc,Codec,PorePressc,PorePress0c,PoroJc);
      }
      catch(...){
        upl_tpi_cpu_r1::state.endpoint=false;upl_tpi_cpu_r1::state.temporary=false;
        if(forceScratch)PosInteraction_Forces();
        throw; // No history rotation or new native SaveData on a rejected endpoint.
      }
    }
'''
    replace("JSphCpuSingle.cpp", "endpoint_after_actual_geometry_before_clock", '    else RunCellDivide(true);\n    TimeStep+=stepdt;',
            '    else RunCellDivide(true);\n' + endpoint + '    TimeStep+=stepdt;')
    replace("JSphCpuSingle.cpp", "sidecar_after_genuine_native_save", '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);',
            '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);\n'
            '  if(upl_tpi_cpu_r1::Enabled())upl_tpi_cpu_r1::Saved(this,Part,TimeStep,Nstep,Np,Idpc,Codec,PorePressc,PoroJc);')
    replace("JSphCpuSingle.cpp", "finish_pressure_lifecycle", '  FinishRun(partoutstop);',
            '  if(upl_tpi_cpu_r1::Enabled())upl_tpi_cpu_r1::Finish(this,Nstep,TimeStep);\n  FinishRun(partoutstop);')

    # All reads/checks precede any writes. No compilation/program/solver occurs.
    if any(changed[n] == originals[n] for n in originals):
        raise RuntimeError("Both private TUs must have an explicit minimal overlay")
    for entry in frozen.values():
        same(entry)
    same(admission_entry)
    OUT.mkdir()
    generated = []
    changed_sources = []
    for name, data in originals_bytes.items():
        target = OUT / name
        body = changed[name].encode("utf-8") if name in changed else data
        with target.open("xb") as f:
            f.write(body)
        record = stat(target)
        generated.append(record)
        if name in changed:
            changed_sources.append(record)
    private_header = OUT / (TAG + ".h")
    with private_header.open("xb") as f:
        f.write((AUTHOR / private_header.name).read_bytes())
    header_entry = stat(private_header)
    generated.append(header_entry)
    difference = dict(stage=TAG + ".source_diff", passed=True, replacements=proof,
        unified_diff="\n".join("".join(difflib.unified_diff(
            originals[n].splitlines(keepends=True), changed[n].splitlines(keepends=True),
            fromfile="final_A/" + n, tofile="private_P1/" + n)) for n in originals),
        line_ending_normalization_in_changed_two_TUs=True,
        unchanged_other_263_source_files_copied_bytewise=True, public_source_changed=False,
        class_or_header_ABI_changed=False, original_two_HG_force_update_transitions_unchanged=True,
        readonly_HG_endpoint_uses_existing_const_Q_over_Mref_accessor=True,
        additional_endpoint_cannot_advance_solid_J_kappa_P0=True, beta_implemented=False,
        public_XML_changed=False, physical_acceptance=False)
    diff_path = OUT / "source_diff.json"
    with diff_path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(difference, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for entry in frozen.values():
        same(entry)
    same(admission_entry)
    receipt = dict(stage=TAG + ".prepare", passed=True, source_root=str(OUT),
        root_admission=admission_entry, base_build=build_entry, base_program=base_program,
        base_xml=base_xml_entry, base_source_entries=base_source_entries, author_files=author_entries,
        files=generated, changed_sources=changed_sources, private_header=header_entry,
        source_diff=stat(diff_path), replacements=len(proof), fixed_dt_from_full_A=dt,
        object_recipe=dict(total_A=86, changed_two_TUs=2, retained_ReleaseCPU_objects=84,
                           DebugCPU_requires_full_frozen_A_recompile=True),
        objects_unmodified=True, consumed_stats_unchanged=True, builder_invocations=0,
        program_invocations=0, solver_invocations=0, native_invocations=0, SHA_scans=0,
        public_source_changed=False, class_or_header_ABI_changed=False, physical_acceptance=False)
    with RECEIPT.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(str(RECEIPT))


if __name__ == "__main__":
    main()
