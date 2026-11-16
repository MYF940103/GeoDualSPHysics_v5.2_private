"""Prepare one full C04 private XYZ/HG0 GPU source candidate; never build/run.

Only three original C04 GPU TUs get local hooks. No complete C02 TU, old
object, public source/header or existing output is replaced.
"""
from __future__ import annotations
import argparse
import difflib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True

T = Path(__file__).resolve().parents[1]
R = T.parents[3]
TAG = "upl_tpi_cryer_gpu_r2"
OUT = T / "outputs" / (TAG + "_source")
RECEIPT = T / "logs" / (TAG + ".prepare.json")
BASE_PREP = T / "logs/upl_tpi_cryer_cpu_source_r1.prepare.json"
PRIOR_FAILURE = T / "logs/upl_tpi_cryer_gpu_r1.prepare.json"
BASE = T / "outputs/upl_tpi_cryer_cpu_r1_source"
COMMIT = "de2492afb5be33e9077f8e4a96bfe755b0ffc7ed"
CHANGED = ("JSphGpu.cpp", "JSphGpuSingle.cpp", "JSphGpu_ker.cu")
HELPERS = ("upl_tpi_cryer_gpu_r1.h", "upl_tpi_cryer_gpu_r1.cuh")
PROJECTS = ("DualSPHysics5Re.sln", "DualSPHysics5Re.vcxproj")
NS = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}
C02 = T.parent.parent / "02_TerzaghiConsolidation_q0_PR/tests"


def need(ok, text):
    if not ok: raise RuntimeError(text)


def stat(path):
    p = Path(path).resolve(); s = p.stat(); need(p.is_file(), "Not a file: " + str(p))
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def same(e):
    actual = stat(e["path"]); need(actual == {k: e[k] for k in ("path", "bytes", "mtime_ns")}, "Frozen stat changed: " + e["path"])
    return actual


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f: f.write(data)
    need(path.read_bytes() == data, "New private byte-copy differs: " + str(path))


def save(path, obj):
    write(path, (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execution-authorized", action="store_true"); p.add_argument("--admission", type=Path, required=True)
    a = p.parse_args(); need(a.execution_authorized, "Independent root prepare-only authorization required")
    need(not OUT.exists() and not RECEIPT.exists(), "Existing source/receipt/failure is protected; never retry or overwrite")
    adentry = stat(a.admission); ad = read(a.admission)
    need(ad.get("stage") == TAG + ".prepare_admission" and ad.get("passed") is True and ad.get("prepare_only") is True,
         "Reviewed exact root source-only admission required")
    frozen = {str(Path(e["path"]).resolve()): e for e in ad["inputs"]}; consumed = {}
    need(len(frozen) == len(ad["inputs"]), "Duplicate frozen root input")
    def observed(path):
        k = str(Path(path).resolve()); need(k in frozen, "Consumed input absent from root admission: " + k)
        e = same(frozen[k]); raw = Path(k).read_bytes(); same(e); consumed[k] = e
        return raw
    def finish():
        for e in consumed.values(): same(e)
        same(adentry)
    result = dict(stage=TAG + ".prepare", passed=False, root_admission=adentry,
                  build_invocations=0, help_invocations=0, solver_invocations=0, native_invocations=0,
                  VTK_invocations=0, SHA_scans=0, public_source_changed=False, physical_acceptance=False,
                  historical_full_source_capture_claimed=False, old_objects_reused=False)
    try:
        authors = [Path(__file__), T / "notes/upl_tpi_cryer_gpu_r2.md", *[T / "support" / x for x in HELPERS]]
        for path in authors: observed(path)
        prior = json.loads(observed(PRIOR_FAILURE).decode("utf-8-sig"))
        need(prior.get("stage") == "upl_tpi_cryer_gpu_r1.prepare" and prior.get("passed") is False
             and prior.get("first_error") == "Old GPU local dependency path is absent from complete C04 source"
             and prior.get("partial_output_preserved") is False
             and not (T / "outputs/upl_tpi_cryer_gpu_r1_source").exists(),
             "Preserved r1 source/project-classification preflight failure required; no prior source output may be overwritten")
        prepared = json.loads(observed(BASE_PREP).decode("utf-8-sig"))
        manifest_raw = observed(BASE / "source_diff.json"); manifest = json.loads(manifest_raw.decode("utf-8-sig"))
        need(prepared.get("passed") is True and prepared.get("source_count") == 265 and
             manifest.get("passed") is True and manifest.get("base_commit") == COMMIT and
             manifest.get("historical_full_source_capture_claimed") is False,
             "Complete reconstructed C04 source, not a retroactive old object/source identity, required")
        origins = manifest["source_origins"]; need(len(origins) == 265 and len({x["name"] for x in origins}) == 265, "C04 base source membership differs")
        files, source_entries = {}, []
        for row in origins:
            path = BASE / "source" / row["name"]; raw = observed(path)
            need(len(raw) == row["bytes"], "C04 baseline source length changed")
            files["source/" + row["name"]] = raw; source_entries.append(consumed[str(path.resolve())])
        # The CPU-private helper in the reconstruction tree is deliberately not copied.
        for name in ("_FmtXML_ElastoplasticSoil.xml", "historical_C04_README.md"):
            files["docs/" + name] = observed(BASE / "docs" / name)
        files["base_source_diff.json"] = manifest_raw
        for name in PROJECTS:
            call = subprocess.run(["git", "show", COMMIT + ":src/VS/" + name], cwd=R,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            need(call.returncode == 0 and call.stdout, "Read-only recorded Git project restore failed: " + name)
            files["VS/" + name] = call.stdout
        project = ET.fromstring(files["VS/DualSPHysics5Re.vcxproj"])
        closure = {}
        for config in ("Debug", "Release"):
            kinds = {}
            for kind in ("ClCompile", "CudaCompile"):
                members = []
                for item in project.findall(".//m:" + kind + "[@Include]", NS):
                    excluded = any(config + "|x64" in n.get("Condition", "") and n.text == "true" for n in item.findall("m:ExcludedFromBuild", NS))
                    if not excluded: members.append(Path(item.get("Include").replace("\\", "/")).name)
                kinds[kind] = members
            need(len(kinds["ClCompile"]) == 97 and len(kinds["CudaCompile"]) == 14, "Restored GPU97CL/14CUDA project closure differs")
            buildpath = T / "logs" / ("upl_cryer_freebody_r1_" + config + ".build.json")
            callpath = T / "logs" / ("upl_cryer_freebody_r1_" + config + ".call.json")
            oldbuild = json.loads(observed(buildpath).decode("utf-8-sig")); oldcall = json.loads(observed(callpath).decode("utf-8-sig"))
            need(oldbuild.get("passed") is True and oldbuild.get("objects") == 111 and oldcall.get("direct_exit") is True and oldcall.get("exit_code") == 0,
                 "Genuine original GPU111 build/call metadata required")
            intargs = [x for x in oldcall["arguments"] if x.startswith("/p:IntDir=")]; need(len(intargs) == 1, "Original private IntDir ambiguous")
            root = Path(intargs[0].split("=", 1)[1]) / "DualSPHysics.tlog"
            logs = {name: observed(root / name).decode("utf-16") for name in ("CL.read.1.tlog", "CudaCompile.read.1u.tlog", "link.command.1.tlog")}
            source_names = lambda text: [Path(x).name for line in text.splitlines() if line.startswith("^") for x in line[1:].split("|")]
            oldcl, oldcu = source_names(logs["CL.read.1.tlog"]), source_names(logs["CudaCompile.read.1u.tlog"])
            need(len(oldcl) == len(set(x.casefold() for x in oldcl)) == 97 and
                 {x.casefold() for x in oldcl} == {x.casefold() for x in kinds["ClCompile"]} and
                 len(oldcu) == len(set(x.casefold() for x in oldcu)) == 14 and
                 {x.casefold() for x in oldcu} == {x.casefold() for x in kinds["CudaCompile"]}, "Actual old GPU TU paths differ from recorded authoritative project")
            objects = source_names(logs["link.command.1.tlog"])
            wanted = {Path(x).stem.casefold() + ".obj" for x in kinds["ClCompile"]} | {x.casefold() + ".obj" for x in kinds["CudaCompile"]}
            need(len(objects) == 111 and len(set(x.casefold() for x in objects)) == 111 and {x.casefold() for x in objects} == wanted
                 and {"functionsgeo3d_iker.h.obj", "functionsmath_iker.h.obj"} <= wanted, "Actual GPU111 object names or two h.obj entries differ")
            local_source_paths, local_project_paths = set(), set()
            for name in ("CL.read.1.tlog", "CudaCompile.read.1u.tlog"):
                for line in logs[name].splitlines():
                    if not line or "|" in line:
                        continue
                    path = Path(line.lstrip("^")).resolve()
                    if not path.is_relative_to(R):
                        continue
                    if path.is_relative_to(R / "src/source"):
                        local_source_paths.add(path)
                    elif path == R / "src/VS/DualSPHysics5Re.vcxproj":
                        local_project_paths.add(path)
                    else:
                        raise RuntimeError("Unknown historical repository dependency path: " + str(path))
            local = {p.name.casefold() for p in local_source_paths}
            need(len(local_source_paths) == len(local) == 257 and
                 local <= {x["name"].casefold() for x in origins},
                 "Original257 source/header dependency paths are not covered by complete C04 source")
            need(local_project_paths == {R / "src/VS/DualSPHysics5Re.vcxproj"},
                 "Exactly the recorded authoritative GPU project metadata dependency is required")
            closure[config] = dict(project_CL_sources=kinds["ClCompile"], project_CUDA_sources=kinds["CudaCompile"],
                expected_object_basenames=objects, object_count=111, old_local_dependency_path_count=len(local_source_paths)+len(local_project_paths),
                old_local_source_header_dependency_count=len(local_source_paths),
                old_local_project_metadata_dependency_count=len(local_project_paths),
                old_local_project_metadata_dependency_paths=[str(p) for p in sorted(local_project_paths)],
                project_metadata_is_not_a_source_header=True, historical_project_bytes_proven_by_tlog=False,
                historical_dependency_contents_proven=False, old_objects_reused=False,
                original_build=consumed[str(buildpath.resolve())], original_call=consumed[str(callpath.resolve())])
        # Bound provenance of the tested pressure-time mathematics/device guards only.
        for name in ("upl_tpi_gpu_r1.h", "upl_tpi_gpu_r1.cuh"):
            observed(C02 / "outputs/upl_tpi_gpu_r2_source" / name)
        original = {n: files["source/" + n].decode("utf-8-sig").replace("\r\n", "\n") for n in CHANGED}
        changed, proof = dict(original), []
        def replace(file, label, before, after, method=None):
            text = changed[file]; start, end = 0, len(text)
            if method:
                need(text.count(method) == 1, "Unique method absent: " + label)
                start = text.index(method); end = text.find("\n//==============================================================================", start + len(method))
                if end < 0: end = len(text)
            body = text[start:end]; need(body.count(before) == 1, "Nonunique original C04 splice: " + label)
            changed[file] = text[:start] + body.replace(before, after, 1) + text[end:]
            proof.append(dict(file=file, anchor=label, method=method, before=before, after=after))
        replace("JSphGpu.cpp", "private_host_implementation", '#include "JSphGpu.h"\n',
                '#include "JSphGpu.h"\n#define UPL_TPI_CRYER_GPU_R1_IMPLEMENTATION\n#include "upl_tpi_cryer_gpu_r1.h"\n#undef UPL_TPI_CRYER_GPU_R1_IMPLEMENTATION\n')
        replace("JSphGpu.cpp", "private_cuda_cleanup_before_original_reset", '  DestructorActive=true;\n',
                '  DestructorActive=true;\n  upl_tpi_cryer_gpu_r1::FreeOwner(UPL_TPI_CRYER_GPU_OWNER);\n', 'JSphGpu::~JSphGpu(){')
        replace("JSphGpuSingle.cpp", "private_host_declarations", '#include "JSphHourglassGpu.h"\n',
                '#include "JSphHourglassGpu.h"\n#include "JDsFixedDt.h"\n#include "upl_tpi_cryer_gpu_r1.h"\n')
        qualification = r'''
  if(upl_tpi_cryer_gpu_r1::Enabled()){
    upl_tpi_cryer_gpu_r1::Require(!Simulate2D && TStep==STEP_Symplectic && CaseNp==37181 && CaseNfixed==8
      && CaseNfluid==37173 && CaseNpb==8 && Np==37181 && Npb==8 && !CaseNmoving && !CaseNfloat && !NpDynamic
      && !InOut && !Shifting && !Damping && !RelaxZones && !UseDEM && !Symmetry && !PartBegin && PartBeginDir.empty()
      && TimeStep==0. && Nstep==0 && TimeMax>0. && NstepsBreak>0 && NstepsBreak<=128
      && (!GaugeSystem || GaugeSystem->GetCount()==0),"Private C04 GPU P3 requires complete fresh XYZ startup128 owners");
    upl_tpi_cryer_gpu_r1::Require(FixedDt && FixedDt->GetFixedValue()==0.00000095367431640625
      && SymplecticDtPre==0.00000095367431640625 && HydroMech && HydroMechDynamicSeepage
      && PorosityObserver && PorosityFeedback && DynamicPorePressure && DynamicPoreFreeBody && !DynamicPoreWall
      && !DynamicPoreConductivity && HydroMechConductivityModel==0 && HydroMechConductivityCk==0
      && !PoreShepardRegularization && PoreCompressionGradCorr && PoreCompressionSourceMode==0
      && SoilCte.Porosity==.3f && SoilCte.PoreWaterBulkModulus==2e8f && SoilCte.HydraulicConductivity==.00001f
      && SoilCte.PoreWaterRho==1000.f && RhopZero==2100.f && SoilCte.ModulusE==2e6f && SoilCte.PRvs==.3f
      && SoilCte.coh==1e9f && !StrainSoftening,"Private C04 GPU P3 retains original constant-k elastic freebody material/dt");
    upl_tpi_cryer_gpu_r1::Require(TBoundary==BC_DBC && !NoPenetration && !PeriActive && TKernel==KERNEL_Wendland
      && Dp==.0025 && KernelH==float(.0045) && !HourglassGpu && SoilHourglassXi==0 && !SoilBoundaryDerivativeSPR
      && SoilStressRateGradCorr && !ArtificialStress && TVisco==VISCO_Artificial && Visco==.1f && ViscoBoundFactor==1.f
      && !ViscoTime && SoilDamping && SoilDampingCoef==.00004f && TDensity==DDT_None && !DDTArray
      && Gravity.x==0. && Gravity.y==0. && Gravity.z==0.,"Private C04 GPU P3 retains remote DBC/HG0/SPR0/AS0/AV.1/eta4e-5");
    upl_tpi_cryer_gpu_r1::Require(HydroMechInitMode==HMINIT_None && HydroMechTopLoadMode==HMLOAD_FlexibleConfinement
      && HydroMechTopLoadQ0==10000.f && HydroMechTopLoadRampTime==.00390625 && HydroMechDrainage
      && HydroMechDrainageFixedGrid && HydroMechDrainageStartTime==.0078125
      && !PoreDarcySymmetricCorr && !PoreMdbcInterpolationMode,"Private C04 GPU P3 retains raw source-clock ramp/hold/drain");
    upl_tpi_cryer_gpu_r1::Init(UPL_TPI_CRYER_GPU_OWNER,DirOut,UPL_TPI_CRYER_GPU_VIEW,TimeStep,Nstep,SymplecticDtPre);
    Log->Print("UplTpiCryerGpuR1: XYZ HG0 startup128 only; alpha.5/0 beta0 single defect correction, not literal LF/implicit/second-order/physical acceptance.");
  }
'''
        replace("JSphGpuSingle.cpp", "fresh_XYZ_HG0_qualification", '  InitRunGpu();\n  RunGaugeSystem(TimeStep,true);',
                '  InitRunGpu();\n' + qualification + '  RunGaugeSystem(TimeStep,true);')
        replace("JSphGpu.cpp", "history_mechanical_half", '  if(HydroMech && PorePressg && PorePressPreg && PorePressRateg)\n',
                '  if(upl_tpi_cryer_gpu_r1::Enabled())\n    upl_tpi_cryer_gpu_r1::Begin(UPL_TPI_CRYER_GPU_OWNER,UPL_TPI_CRYER_GPU_VIEW,PorePressPreg,PosxyPreg,PorePressg,\n      TimeStep,Nstep,dt,IsHydroMechDrainageActive(),unsigned(HydroMechTopLoadMode));\n  else if(HydroMech && PorePressg && PorePressPreg && PorePressRateg)\n', 'void JSphGpu::ComputeSymplecticPre(double dt){')
        replace("JSphGpu.cpp", "capture_actual_half_before_original_material_and_J", '  Timersg->TmStart(TMG_SuComputeStep,false);',
                '  if(upl_tpi_cryer_gpu_r1::Enabled())upl_tpi_cryer_gpu_r1::Corr(UPL_TPI_CRYER_GPU_OWNER,UPL_TPI_CRYER_GPU_VIEW);\n  Timersg->TmStart(TMG_SuComputeStep,false);', 'void JSphGpu::ComputeSymplecticCorr(double dt){')
        replace("JSphGpu.cpp", "capture_unique_original_full_J", '  ComputeSymplecticPorosity(true,dt);',
                '  ComputeSymplecticPorosity(true,dt);\n  if(upl_tpi_cryer_gpu_r1::Enabled())upl_tpi_cryer_gpu_r1::CaptureJ(UPL_TPI_CRYER_GPU_OWNER,UPL_TPI_CRYER_GPU_VIEW);')
        replace("JSphGpu.cpp", "history_endpoint_guess_after_full_positions", '  if(HydroMech && DynamicPorePressure && PorePressg && PorePressPreg && PorePressRateg)\n',
                '  if(upl_tpi_cryer_gpu_r1::Enabled())\n    upl_tpi_cryer_gpu_r1::Guess(UPL_TPI_CRYER_GPU_VIEW,PorePressPreg,IsHydroMechDrainageActive(),unsigned(HydroMechTopLoadMode));\n  else if(HydroMech && DynamicPorePressure && PorePressg && PorePressPreg && PorePressRateg)\n', 'void JSphGpu::ComputeSymplecticCorr(double dt){')
        endpoint = r'''    if(upl_tpi_cryer_gpu_r1::Enabled()){
      bool scratch=false;
      try{
        upl_tpi_cryer_gpu_r1::Require(!HourglassGpu && SoilHourglassXi==0,"C04 P3 endpoint requires HG0");
        upl_tpi_cryer_gpu_r1::StartEndpoint(UPL_TPI_CRYER_GPU_OWNER,UPL_TPI_CRYER_GPU_VIEW,TimeStep,Nstep,stepdt,HourglassGpu);
        scratch=true;Interaction_Forces(INTERSTEP_SymCorrector);
        const double endpointdt=DtVariable(false);
        upl_tpi_cryer_gpu_r1::Require(endpointdt==stepdt,"Private C04 GPU endpoint fixed dt changed");
        upl_tpi_cryer_gpu_r1::PrepareFinal(UPL_TPI_CRYER_GPU_OWNER,UPL_TPI_CRYER_GPU_VIEW,HourglassGpu);
        PosInteraction_Forces();scratch=false;
        upl_tpi_cryer_gpu_r1::WriteFinal(UPL_TPI_CRYER_GPU_VIEW);
        ApplyPorePressureBoundaries();
        upl_tpi_cryer_gpu_r1::Commit(UPL_TPI_CRYER_GPU_OWNER,UPL_TPI_CRYER_GPU_VIEW,IsHydroMechDrainageActive(),unsigned(HydroMechTopLoadMode));
      }catch(...){upl_tpi_cryer_gpu_r1::AbortEndpoint();if(scratch){try{PosInteraction_Forces();}catch(...){}}throw;}
    }
'''
        replace("JSphGpuSingle.cpp", "endpoint_after_cell_divide_before_original_scalar_clock", '    else RunCellDivide(true);\n    TimeStep+=stepdt;',
                '    else RunCellDivide(true);\n' + endpoint + '    TimeStep+=stepdt;')
        replace("JSphGpuSingle.cpp", "sidecar_only_after_genuine_native_save", '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);',
                '  JSph::SaveData(npsave,arrays,1,vdom,&infoplus);\n  if(upl_tpi_cryer_gpu_r1::Enabled())upl_tpi_cryer_gpu_r1::Saved(UPL_TPI_CRYER_GPU_OWNER,Part,TimeStep,Nstep,UPL_TPI_CRYER_GPU_VIEW);')
        replace("JSphGpuSingle.cpp", "final_pressure_lifecycle", '  FinishRun(partoutstop);',
                '  if(upl_tpi_cryer_gpu_r1::Enabled())upl_tpi_cryer_gpu_r1::Finish(UPL_TPI_CRYER_GPU_OWNER,Nstep,TimeStep);\n  FinishRun(partoutstop);')
        replace("JSphGpu_ker.cu", "private_device_declarations", '#include "JSphGpu_ker.h"\n',
                '#include "JSphGpu_ker.h"\n#include "upl_tpi_cryer_gpu_r1.h"\n')
        replace("JSphGpu_ker.cu", "one_original_XYZ_spatial_body", '__global__ void KerComputeDynamicPorePressureRate(unsigned np,unsigned npb',
                'template<bool CaptureRows> __global__ void KerComputeDynamicPorePressureRate(unsigned np,unsigned npb')
        method = 'template<bool CaptureRows> __global__ void KerComputeDynamicPorePressureRate(unsigned np,unsigned npb'
        replace("JSphGpu_ker.cu", "true_Dirichlet_priority", '    if(drainfs && KerHydroMechIsDrainedParticle(p1,loadmode,posxy,code,fstype)){rate[p1]=0.f;return;}',
                '    if(drainfs && KerHydroMechIsDrainedParticle(p1,loadmode,posxy,code,fstype)){\n      if(CaptureRows)::upl_tpi_cryer_gpu_r1::CaptureRow(p1,true,0.,0.,theta[p1],porepress[p1]);\n      rate[p1]=0.f;return;}', method)
        replace("JSphGpu_ker.cu", "leading_LP_weight_sum", '    double lp=0.,da=0.;', '    double lp=0.,da=0.;\n    double tpiSumWeights=0.;', method)
        replace("JSphGpu_ker.cu", "same_original_XYZ_pair_weight", '          lp+=w*dp;lx.x+=d.x*w;lx.y+=d.y*w;lx.z+=d.z*w;',
                '          if(CaptureRows)tpiSumWeights+=w;\n          lp+=w*dp;lx.x+=d.x*w;lx.y+=d.y*w;lx.z+=d.z*w;', method)
        replace("JSphGpu_ker.cu", "complete_double_R_before_legacy_float_rate", '    rate[p1]=float(value); //-One complete overwrite, never add the compression source twice.',
                '    if(CaptureRows)::upl_tpi_cryer_gpu_r1::CaptureRow(p1,false,-__dmul_rn(khyd,tpiSumWeights),\n      __dadd_rn(-__dmul_rn(gamma,theta[p1]),__dmul_rn(khyd,lap)),theta[p1],porepress[p1]);\n    rate[p1]=float(value); //-Original legacy scaled residual, not the M0 dp/dt.', method)
        launch = '''    KerComputeDynamicPorePressureRate <<<sgrid,SPHBSIZE>>> (np,npb,dvd.scelldiv,dvd.nc,dvd.cellzero,dvd.beginendcell+dvd.cellfluid,dcell
      ,posxy,posz,code,corrmat,ace,j,theta,porepress,rate,solid0,kw,rhow,khyd,gamma,vol0,invalid,conductivity,ck,maxspeed,wall,dvd.beginendcell,boundmode
      ,fstype,fsnormal,drainfs,closedfs,unsigned(loadmode),make_double3(bodycentre.x,bodycentre.y,bodycentre.z),bodyradius2);'''
        replace("JSphGpu_ker.cu", "same_external_freebody_signature_and_original_launch_arguments", launch,
                '    if(::upl_tpi_cryer_gpu_r1::CaptureEndpointHost()){\n' + launch.replace('KerComputeDynamicPorePressureRate <<<', 'KerComputeDynamicPorePressureRate<true> <<<') +
                '\n    }else{\n' + launch.replace('KerComputeDynamicPorePressureRate <<<', 'KerComputeDynamicPorePressureRate<false> <<<') + '\n    }')
        changed["JSphGpu_ker.cu"] += '\n// Private definitions outside the original cusph namespace.\n#include "upl_tpi_cryer_gpu_r1.cuh"\n'
        need(len(proof) == 18 and all(changed[n] != original[n] for n in CHANGED), "Exactly18 local C04 GPU splice anchors required")
        finish(); OUT.mkdir(); generated = []
        for relative, raw in files.items():
            name = Path(relative).name
            if relative.startswith("source/") and name in changed: raw = changed[name].encode("utf-8")
            target = OUT / relative; write(target, raw); generated.append(stat(target))
        for name in HELPERS:
            target = OUT / "source" / name; write(target, observed(T / "support" / name)); generated.append(stat(target))
        difference = dict(stage=TAG + ".source_diff", passed=True, replacements=proof,
            unified_diff="\n".join("".join(difflib.unified_diff(original[n].splitlines(keepends=True), changed[n].splitlines(keepends=True), fromfile="C04_base/"+n, tofile="C04_private_GPU/"+n)) for n in CHANGED),
            only_changed_TUs=list(CHANGED), unchanged_baseline_source_header_count=262, new_private_helpers=list(HELPERS),
            original_headers_changed=False, class_or_header_ABI_changed=False, old_kernel_external_signatures_changed=False,
            freebody_centre_radius_signature_and_separation_guards_preserved=True, full_XYZ_Rgamma_and_S_preserved=True,
            original_force_AV_grad_material_sourceclock_retained=True, one_original_J_and_material_update=True,
            HG_adapters_called=False, HG_header_getters_added=False, HG_snapshot_checks_expected=0,
            default_A_has_no_history_allocation_sidecar_or_extra_endpoint=True, default_A_raw22_bit_proof_claimed=False,
            beta=0, single_defect_not_converged_implicit=True, paper_literal_LF=False, second_order_claimed=False,
            original_fast_math_FTZ_policy_preserved=True, requires_full_new_111_object_compile=True,
            old_objects_reused=False, historical_full_source_capture_claimed=False, physical_acceptance=False)
        save(OUT / "source_diff.json", difference); finish()
        result.update(passed=True, source_root=str(OUT), source_count=265, private_helper_count=2,
            files=generated, prior_failed_prepare=consumed[str(PRIOR_FAILURE.resolve())],
            helpers_unchanged_from_r1_authors=True, physical_hooks_unchanged_from_r1=True,
            base_prepare=consumed[str(BASE_PREP.resolve())], base_source_manifest=consumed[str((BASE / "source_diff.json").resolve())],
            base_source_entries=source_entries, source_diff=stat(OUT / "source_diff.json"), author_files=[consumed[str(x.resolve())] for x in authors],
            changed_sources=[stat(OUT / "source" / n) for n in CHANGED], changed_headers=[],
            new_private_helpers=list(HELPERS), old_GPU_closure=closure,
            class_or_header_ABI_changed=False, old_kernel_external_signatures_changed=False, HG_adapters_called=False,
            requires_full_new_111_object_compile=True, consumed_inputs=list(consumed.values()), consumed_stats_unchanged=True)
    except Exception as exc:
        result.update(passed=False, first_error=str(exc), partial_output_preserved=OUT.exists())
    save(RECEIPT, result)
    print(json.dumps(dict(passed=result["passed"], receipt=str(RECEIPT), first_error=result.get("first_error")), ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__": raise SystemExit(main())
