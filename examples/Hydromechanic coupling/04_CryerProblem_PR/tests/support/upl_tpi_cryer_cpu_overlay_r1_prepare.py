"""Author-only C04 two-TU TPI overlay preparation; no build or program run."""
from __future__ import annotations
import argparse
import difflib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
TAG = 'upl_tpi_cryer_cpu_overlay_r1'
BASE = T / 'outputs/upl_tpi_cryer_cpu_r1_source'
BASE_CHECK = T / 'logs/upl_tpi_cryer_cpu_source_r1.prepare.json'
OUT = T / 'outputs/upl_tpi_cryer_cpu_overlay_r1_source'
RECEIPT = T / 'logs/upl_tpi_cryer_cpu_overlay_r1.prepare.json'
BASE_XML = T / 'configs/upl_cryer_freebody_short_r1_Def.xml'
C02 = T.parent.parent / '02_TerzaghiConsolidation_q0_PR' / 'tests'
HELPER = 'upl_tpi_cpu_r1.h'


def need(test, message):
    if not test:
        raise RuntimeError(message)


def stat(path):
    p = Path(path).resolve()
    s = p.stat()
    need(p.is_file(), 'Not a file: ' + str(p))
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def same(entry):
    actual = stat(entry['path'])
    need(actual == {k: entry[k] for k in ('path', 'bytes', 'mtime_ns')},
         'Root-frozen input stat changed: ' + entry['path'])
    return actual


def save_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(data)
    need(path.read_bytes() == data, 'New copy byte verification failed: ' + str(path))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--execution-authorized', action='store_true')
    ap.add_argument('--admission', type=Path, required=True)
    args = ap.parse_args()
    need(args.execution_authorized, 'Explicit root source-preparation authorization required')
    need(not OUT.exists() and not RECEIPT.exists(), 'Existing new tag must be preserved, never overwritten or retried')
    admission_entry = stat(args.admission)
    admission = json.loads(args.admission.read_text(encoding='utf-8-sig'))
    need(admission.get('stage') == TAG + '.prepare_admission' and admission.get('passed') is True
         and admission.get('prepare_only') is True, 'Independent root prepare-only admission required')
    frozen = {str(Path(e['path']).resolve()): e for e in admission['inputs']}
    need(len(frozen) == len(admission['inputs']), 'Duplicate root input binding')
    consumed = {}

    def read(path):
        path = Path(path).resolve()
        key = str(path)
        need(key in frozen, 'Consumed input absent from root admission: ' + key)
        entry = same(frozen[key])
        data = path.read_bytes()
        need(len(data) == entry['bytes'] and same(entry) == entry, 'Input changed while reading: ' + key)
        consumed[key] = entry
        return data

    receipt = dict(stage=TAG + '.prepare', passed=False, root_admission=admission_entry,
                   builder_invocations=0, program_invocations=0, solver_invocations=0,
                   native_invocations=0, SHA_scans=0, public_source_changed=False,
                   class_or_header_ABI_changed=False, physical_acceptance=False)
    try:
        read(Path(__file__))
        read(T / 'notes/upl_tpi_cryer_cpu_overlay_r1.md')
        old_check = json.loads(read(BASE_CHECK).decode('utf-8-sig'))
        base_manifest_bytes = read(BASE / 'source_diff.json')
        manifest = json.loads(base_manifest_bytes.decode('utf-8-sig'))
        need(old_check['passed'] and old_check['source_count'] == 265 and old_check['source_inputs_unchanged'],
             'New full C04 reconstruction has not passed')
        need(manifest['passed'] and manifest['source_count'] == 265
             and manifest['two_TU_TPI_hooks_applied'] is False
             and manifest['historical_full_source_capture_claimed'] is False
             and manifest['recovered_candidate_requires_new_full_86_object_compile'] is True,
             'Expected unhooked reconstructed C04 source, not old object-source identity')
        source_rows = manifest['source_origins']
        need(len(source_rows) == 265 and len({x['name'] for x in source_rows}) == 265,
             'Full C04 source membership differs')
        expected_source = {x['name'] for x in source_rows} | {HELPER}
        need({x.name for x in (BASE / 'source').iterdir()} == expected_source,
             'Unregistered file or missing source in frozen C04 source directory')
        files = {}
        for row in source_rows:
            data = read(BASE / 'source' / row['name'])
            need(len(data) == row['bytes'], 'Frozen source recorded length changed')
            files['source/' + row['name']] = data
        helper = read(BASE / 'source' / HELPER)
        need(helper == read(C02 / 'outputs/upl_tpi_cpu_r1_source' / HELPER)
             == read(C02 / 'support' / HELPER), 'Generic tested CPU helper changed; no private edit permitted')
        files['source/' + HELPER] = helper
        for name in ('DualSPHysics5ReCpu_vs2022.sln', 'DualSPHysics5ReCpu.vcxproj'):
            files['VS/' + name] = read(BASE / 'VS' / name)
        for name in ('_FmtXML_ElastoplasticSoil.xml', 'historical_C04_README.md'):
            files['docs/' + name] = read(BASE / 'docs' / name)
        files['base_source_diff.json'] = base_manifest_bytes
        # Existing C02 author is provenance/reference only; never import or execute it.
        read(C02 / 'support/upl_tpi_cpu_r1_prepare.py')
        xml = ET.fromstring(read(BASE_XML))
        def value(tag, key=None):
            a = [x.attrib['value'] for x in xml.iter(tag) if key is None or x.attrib.get('key') == key]
            need(len(a) == 1, 'Original bounded XML value not unique: ' + (key or tag))
            return float(a[0])
        need(value('parameter', 'DtFixed') == 2.**-20 and value('parameter', 'DtIni') == 2.**-20
             and value('parameter', 'Kernel') == 2 and value('parameter', 'SoilHourglassXi') == 0
             and value('parameter', 'SoilBoundaryDerivativeSPR') == 0 and value('parameter', 'Visco') == .1
             and value('parameter', 'SoilDampingCoef') == .00004
             and value('HydraulicConductivity') == .00001 and value('PoreWaterBulkModulus') == 2e8
             and value('HydroMechTopLoadRampTime') == 2.**-8 and value('HydroMechDrainageStartTime') == 2.**-7,
             'Retained short Cryer input physics changed')
        originals = {n: files['source/' + n].decode('utf-8-sig').replace('\r\n', '\n')
                     for n in ('JSphCpu.cpp', 'JSphCpuSingle.cpp')}
        changed, proof = dict(originals), []

        def replace(file, name, before, after, method=None):
            source = changed[file]
            if method is None:
                count = source.count(before)
                need(count == 1, name + ' unique anchor count=' + str(count))
                source = source.replace(before, after, 1)
            else:
                need(source.count(method) == 1, name + ' unique method absent')
                begin = source.index(method)
                end = source.find('\n//==============================================================================', begin + len(method))
                if end < 0:
                    end = len(source)
                body = source[begin:end]
                count = body.count(before)
                need(count == 1, name + ' scoped anchor count=' + str(count))
                source = source[:begin] + body.replace(before, after, 1) + source[end:]
            changed[file] = source
            proof.append(dict(file=file, anchor=name, count=count, method_scope=method,
                              before=before, after=after))

        replace('JSphCpu.cpp', 'private_header', '#include <climits>\n',
                '#include "upl_tpi_cpu_r1.h"\n\n#include <climits>\n')
        replace('JSphCpu.cpp', 'single_state_definition', 'using namespace std;\n',
                'using namespace std;\nnamespace upl_tpi_cpu_r1 { State state; }\n')
        replace('JSphCpuSingle.cpp', 'private_header', '#include "JSphCpuSingle.h"\n',
                '#include "JSphCpuSingle.h"\n#include "JDsFixedDt.h"\n#include "upl_tpi_cpu_r1.h"\n')
        qualification = r'''
  if(upl_tpi_cpu_r1::Enabled()){
    upl_tpi_cpu_r1::Need(!Simulate2D && TStep==STEP_Symplectic && OmpThreads>=1
      && CaseNp==37181 && CaseNfixed==8 && CaseNfluid==37173 && CaseNpb==8 && Np==37181 && Npb==8
      && !CaseNmoving && !CaseNfloat && !NpDynamic && !InOut && !Shifting && !Damping && !RelaxZones && !UseDEM && !Symmetry
      && !PartBegin && PartBeginDir.empty() && TimeStep==0. && Nstep==0 && TimeMax>0.
      && NstepsBreak>0 && NstepsBreak<=128 && (!GaugeSystem || GaugeSystem->GetCount()==0),
      "P3 requires the complete fresh XYZ Cryer native set with an explicit at-most-128-update cap");
    upl_tpi_cpu_r1::Need(FixedDt && FixedDt->GetFixedValue()==0.00000095367431640625
      && SymplecticDtPre==0.00000095367431640625,
      "P3 retains the actual finite-Kw Cryer 2^-20 fixed step");
    upl_tpi_cpu_r1::Need(HydroMech && HydroMechDynamicSeepage && PorosityObserver && PorosityFeedback && DynamicPorePressure
      && DynamicPoreFreeBody && !DynamicPoreWall && !DynamicPoreConductivity
      && HydroMechConductivityModel==0 && HydroMechConductivityCk==0 && !PoreShepardRegularization
      && PoreCompressionGradCorr && PoreCompressionSourceMode==0
      && SoilCte.Porosity==.3f && SoilCte.PoreWaterBulkModulus==2e8f && SoilCte.HydraulicConductivity==.00001f
      && SoilCte.PoreWaterRho==1000.f && RhopZero==2100.f && SoilCte.ModulusE==2e6f && SoilCte.PRvs==.3f
      && SoilCte.coh==1e9f && !StrainSoftening,
      "P3 retains the constant-k, J-feedback, corrected-divergence elastic Cryer material");
    upl_tpi_cpu_r1::Need(TBoundary==BC_DBC && !NoPenetration && !PeriActive
      && TKernel==KERNEL_Wendland && Dp==.0025 && KernelH==float(.0045)
      && !HourglassCpu && SoilHourglassXi==0 && !SoilBoundaryDerivativeSPR && SoilStressRateGradCorr
      && !ArtificialStress && TVisco==VISCO_Artificial && Visco==.1f && ViscoBoundFactor==1.f && !ViscoTime
      && SoilDamping && SoilDampingCoef==.00004f && TDensity==DDT_None && !DDTArray
      && Gravity.x==0. && Gravity.y==0. && Gravity.z==0.,
      "P3 retains inactive remote DBC, Wendland H1.8, raw AV.1/eta4e-5 and HG0/SPR0/AS0");
    upl_tpi_cpu_r1::Need(HydroMechInitMode==HMINIT_None && HydroMechTopLoadMode==HMLOAD_FlexibleConfinement
      && HydroMechTopLoadQ0==10000.f && HydroMechTopLoadRampTime==.00390625
      && HydroMechDrainage && HydroMechDrainageFixedGrid && HydroMechDrainageStartTime==.0078125
      && !PoreDarcySymmetricCorr && !PoreMdbcInterpolationMode,
      "P3 preserves raw confinement, original source-clock ramp/hold/drain and the original free-body guards");
    upl_tpi_cpu_r1::Init(this,DirOut,Np,Idpc,Codec,PorePressc,PorePress0c,PoroJc,Kplasticc,TimeStep,Nstep,SymplecticDtPre);
    Log->Print("UplTpiCryerCpuOverlayR1: XYZ HG0 short qualification only; B alpha.5/C alpha0, beta0 single endpoint defect correction, not literal LF/full implicit/physical acceptance.");
  }
'''
        replace('JSphCpuSingle.cpp', 'fresh_bounded_XYZ_freebody_qualification',
                '  InitRunCpu();\n  RunGaugeSystem(TimeStep,true);',
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
    return; // Only pressure prediction changes; the original XYZ solid/J predictor follows once.
  }
'''
        replace('JSphCpu.cpp', 'history_mechanical_half', '  const double dt05=dt*.5;\n',
                pre + '  const double dt05=dt*.5;\n', 'void JSphCpu::ComputeSymplecticPrePorePressure(double dt){')
        corr = r'''
  if(upl_tpi_cpu_r1::Enabled()){
    upl_tpi_cpu_r1::Need(dt==upl_tpi_cpu_r1::state.dt,"P3 corrector fixed dt changed");
    upl_tpi_cpu_r1::Corr(this,Np,Idpc,Codec,PorePressc,PoroJc,PoroThetac);
    const bool drain=IsHydroMechDrainageActive();
    for(unsigned p=0;p<Np;p++){
      if(p<Npb || !CODE_IsFluid(Codec[p]))PorePressc[p]=PorePressPrec[p];
      else PorePressc[p]=(drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec)? 0.f: upl_tpi_cpu_r1::Guess(Idpc[p]));
    }
    return; // No history rotation or repeated solid/material/J update.
  }
'''
        replace('JSphCpu.cpp', 'history_endpoint_guess',
                '  const bool drainfs=(DynamicPorePressure && IsHydroMechDrainageActive());\n',
                corr + '  const bool drainfs=(DynamicPorePressure && IsHydroMechDrainageActive());\n',
                'void JSphCpu::ComputeSymplecticCorrPorePressure(double dt){')
        replace('JSphCpu.cpp', 'capture_original_single_J_corrector',
                '  ComputeSymplecticCorrPorePressure(dt);\n  ComputeSymplecticCorrPorosity(dt);',
                '  ComputeSymplecticCorrPorePressure(dt);\n  ComputeSymplecticCorrPorosity(dt);\n'
                '  if(upl_tpi_cpu_r1::Enabled())upl_tpi_cpu_r1::CaptureJ(this,Np,Idpc,Codec,PoroJc);')
        rate_method = 'void JSphCpu::ComputeDynamicPorePressureRateCpu(){'
        replace('JSphCpu.cpp', 'endpoint_row_context', '  DynamicConductivitySpeedMax=0.;',
                '  const bool tpiEndpoint=(upl_tpi_cpu_r1::Enabled() && upl_tpi_cpu_r1::state.endpoint);\n'
                '  if(tpiEndpoint)upl_tpi_cpu_r1::Need(upl_tpi_cpu_r1::state.owner==this,"P3 endpoint owner changed");\n'
                '  DynamicConductivitySpeedMax=0.;', rate_method)
        replace('JSphCpu.cpp', 'true_drained_row_priority',
                '      PorePressRatec[p1]=0; //-Dirichlet p is constrained; theta and J still evolve normally.',
                '      if(tpiEndpoint)upl_tpi_cpu_r1::Row(Idpc[p1],true,0.,0.,PoroThetac[p1],PorePressc[p1]);\n'
                '      PorePressRatec[p1]=0; //-Dirichlet p is constrained; theta and J still evolve normally.', rate_method)
        replace('JSphCpu.cpp', 'double_diagonal_sum', '    double lp=0,da=0;',
                '    double lp=0,da=0;\n    double tpiSumWeights=0.;', rate_method)
        replace('JSphCpu.cpp', 'same_original_XYZ_pair_weight',
                '          lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);',
                '          if(tpiEndpoint)tpiSumWeights+=w;\n          lp+=w*dp;lx=lx+d*w;gp=gp-gi*(vol2*dp);', rate_method)
        replace('JSphCpu.cpp', 'full_double_R_before_legacy_float_rate',
                '    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;',
                '    if(tpiEndpoint)upl_tpi_cpu_r1::Row(Idpc[p1],false,-khyd*tpiSumWeights,-gamma*PoroThetac[p1]+khyd*lap,PoroThetac[p1],PorePressc[p1]);\n'
                '    if(!std::isfinite(rate) || fabs(rate)>FLT_MAX)invalid++;', rate_method)
        endpoint = r'''
    if(upl_tpi_cpu_r1::Enabled()){
      upl_tpi_cpu_r1::Need(!HourglassCpu && SoilHourglassXi==0,"P3 endpoint must remain HG0; no HG adapter is called");
      upl_tpi_cpu_r1::Endpoint(this,Np,Idpc,Codec,Posc,Velrhopc,Sigmac,Kplasticc,PorePress0c,PorePressc,PoroJc,TimeStep,Nstep,stepdt);
      bool forceScratch=false;
      try{
        forceScratch=true;
        Interaction_Forces(INTERSTEP_SymCorrector); // Endpoint forces/rate only; no XYZ solid/material/J update.
        const double endpointdt=DtVariable(false);
        upl_tpi_cpu_r1::Need(endpointdt==stepdt,"P3 endpoint fixed dt changed");
        upl_tpi_cpu_r1::PrepareFinal(this,Np,Idpc,Codec,Posc,Velrhopc,Sigmac,Kplasticc,PorePress0c,PorePressc,PoroJc);
        PosInteraction_Forces();forceScratch=false;
        upl_tpi_cpu_r1::WriteFinal(Np,Npb,Idpc,Codec,PorePressc);
        upl_tpi_cpu_r1::state.endpoint=false;upl_tpi_cpu_r1::state.temporary=false;
        ApplyPorePressureBoundaries(); // Original actual-clock FS/drainage policy, unchanged.
        const bool drain=IsHydroMechDrainageActive();
        for(unsigned p=Npb;p<Np;p++)if(CODE_IsNormal(Codec[p]) && CODE_IsFluid(Codec[p]))
          upl_tpi_cpu_r1::SetCommitDrained(Idpc[p],drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec));
        upl_tpi_cpu_r1::Commit(this,Np,Idpc,Codec,PorePressc,PorePress0c,PoroJc);
      }
      catch(...){
        upl_tpi_cpu_r1::state.endpoint=false;upl_tpi_cpu_r1::state.temporary=false;
        if(forceScratch)PosInteraction_Forces();
        throw; // Never rotate history or save a rejected endpoint.
      }
    }
'''
        replace('JSphCpuSingle.cpp', 'endpoint_after_actual_geometry_before_clock',
                '    else RunCellDivide(true);\n    TimeStep+=stepdt;',
                '    else RunCellDivide(true);\n' + endpoint + '    TimeStep+=stepdt;')
        replace('JSphCpuSingle.cpp', 'sidecar_after_genuine_native_save',
                '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);',
                '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);\n'
                '  if(upl_tpi_cpu_r1::Enabled())upl_tpi_cpu_r1::Saved(this,Part,TimeStep,Nstep,Np,Idpc,Codec,PorePressc,PoroJc);')
        replace('JSphCpuSingle.cpp', 'finish_pressure_lifecycle', '  FinishRun(partoutstop);',
                '  if(upl_tpi_cpu_r1::Enabled())upl_tpi_cpu_r1::Finish(this,Nstep,TimeStep);\n  FinishRun(partoutstop);')

        need(all(changed[n] != originals[n] for n in originals), 'Both C04 TUs require explicit changes')
        need(len(proof) == 15, 'Unexpected C04 hook count')
        need(not any(x in changed['JSphCpuSingle.cpp'] for x in ('upl_tpi_cpu_r1::CaptureHG(',
             'upl_tpi_cpu_r1::CheckHG(', 'upl_tpi_cpu_r1::AddReadonlyHG(')), 'No HG adapter/check call is permitted in C04 HG0')
        for entry in consumed.values():
            same(entry)
        same(admission_entry)
        OUT.mkdir()
        generated = []
        for relative, data in files.items():
            name = Path(relative).name
            if relative.startswith('source/') and name in changed:
                data = changed[name].encode('utf-8')
            target = OUT / relative
            save_new(target, data)
            generated.append(stat(target))
        difference = dict(stage=TAG + '.source_diff', passed=True, replacements=proof,
            unified_diff='\n'.join(''.join(difflib.unified_diff(
                originals[n].splitlines(keepends=True), changed[n].splitlines(keepends=True),
                fromfile='C04_full_base/' + n, tofile='C04_private_TPI/' + n)) for n in originals),
            only_changed_TUs=['JSphCpu.cpp', 'JSphCpuSingle.cpp'], unchanged_source_header_count=263,
            unchanged_generic_helper_byte_copy=True, line_ending_normalization_in_changed_two_TUs=True,
            public_source_changed=False, class_or_header_ABI_changed=False,
            actual_Rgamma_includes_XYZ_Taylor_and_acceleration=True, S_is_leading_LP_not_full_Jacobian=True,
            beta=0, new_public_XML_parameter=False, extra_endpoint_advances_solid_J_kappa_P0=False,
            source_clock_load_and_drain_unchanged=True, original_freebody_separation_guard_unchanged=True,
            HG_adapters_called=False, HG_snapshot_checks_expected=0,
            requires_new_full_DebugCPU_86_TU_build=True, old_objects_reused=False, physical_acceptance=False)
        save_new(OUT / 'source_diff.json', (json.dumps(difference, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
        for entry in consumed.values():
            same(entry)
        same(admission_entry)
        receipt.update(passed=True, source_root=str(OUT), base_prepare_check=consumed[str(BASE_CHECK.resolve())],
                       base_manifest=consumed[str((BASE / 'source_diff.json').resolve())], files=generated,
                       source_diff=stat(OUT / 'source_diff.json'), replacements=len(proof),
                       consumed_inputs=list(consumed.values()), consumed_stats_unchanged=True,
                       fresh_BC_max_updates=128, native_count=37181, soil_count=37173, fixed_count=8,
                       fixed_dt=2.**-20, helper_unchanged_byte_copy=True, HG_adapters_called=False,
                       requires_full_DebugCPU_86_TU_compile=True, historical_full_source_capture_claimed=False)
    except Exception as exc:
        receipt.update(passed=False, first_error=str(exc), partial_output_preserved=OUT.exists())
    save_new(RECEIPT, (json.dumps(receipt, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
    print(json.dumps(dict(passed=receipt['passed'], receipt=str(RECEIPT), first_error=receipt.get('first_error')), ensure_ascii=False))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
