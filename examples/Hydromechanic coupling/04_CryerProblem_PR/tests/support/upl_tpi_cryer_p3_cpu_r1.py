"""Prepare and exercise Cryer's private CPU P3 implementation using the VS CPU solution."""
import csv
import difflib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import upl_tpi_cryer_cpu_build_r1 as build_tools

TEST = Path(__file__).resolve().parents[1]
OUT = TEST / "outputs"
LOG = TEST / "logs"
C02 = TEST.parents[1] / "02_TerzaghiConsolidation_q0_PR/tests/outputs/upl_tpi_p3_full_CPU_r1_source"
OLD = OUT / "upl_tpi_cryer_cpu_overlay_r1_source"
SRC = OUT / "upl_tpi_cryer_p3_cpu_r1_source"
OLD_BUILD = "upl_tpi_cryer_cpu_DebugCPU_r1"
BUILD = "upl_tpi_cryer_p3_cpu_DebugCPU_r1"
B64 = "upl_tpi_cryer_p3_cpu_B64_r1"
SEED = OUT / "cryer_p3_local_seed_r1"
INPUT_NAME = "upl_cryer_freebody_short_r1"
DT = 2.0**-19


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Expected a unique source anchor: " + old[:100])
    return text.replace(old, new)


def section(text, start, end):
    begin = text.index(start)
    return text[begin:text.index(end, begin + len(start))]


def source_text(path):
    return path.read_text(encoding="utf-8-sig")


def archive_patch():
    # A compact patch can recover all four final implementation files directly
    # from the prior three-dimensional CPU source, independently of the C02 tree.
    patch = TEST/"support/upl_tpi_cryer_p3_cpu_r1.patch"
    if patch.exists():
        raise FileExistsError(str(patch))
    names = ("JSphCpu.cpp", "JSphCpuSingle.cpp", "upl_tpi_cpu_r1.h", "upl_tpi_m0_dt_r2.h")
    with tempfile.TemporaryDirectory() as scratch, patch.open("x", encoding="utf-8",newline="\n") as output:
        root=Path(scratch)
        changes=[]
        for name in names:
            original=OLD/"source"/name
            base=source_text(original) if original.exists() else ""
            if original.exists():
                (root/name).write_text(base,encoding="utf-8",newline="\n")
            final=source_text(SRC/"source"/name)
            diff=difflib.unified_diff(base.splitlines(keepends=True),final.splitlines(keepends=True),
                fromfile=("a/"+name if original.exists() else "/dev/null"),tofile="b/"+name)
            changes.extend(diff)
        output.writelines(changes);output.flush()
        args=["git","apply","--whitespace=nowarn",str(patch)]
        subprocess.run(args,cwd=root,check=True)
        for name in names:
            if source_text(root/name)!=source_text(SRC/"source"/name):
                raise ValueError("Private source patch did not reproduce "+name)
    build_tools.write_new(LOG/"upl_tpi_cryer_p3_cpu_r1.source_patch.json",dict(passed=True,base=str(OLD/"source"),
        archive=str(patch),verified_files=list(names),comparison="UTF-8 source including all lines, normalized LF/BOM"))


def native_pressure_frames(folder):
    """Per-frame full material-ID pressure and J for a one-pass native comparison."""
    import numpy as np
    import pandas as pd
    source=Path(folder)/"UplTpiP3CpuR1.csv"
    cols=["part","pressure_round","native_id","completed_step","actual_after_BC_float_Pa","Jfull"]
    table=pd.read_csv(source,usecols=cols,float_precision="round_trip")
    ids=np.arange(8,37181)
    frames=[]
    for part,iteration,step in ((0,0,0),(1,3,64)):
        group=table[(table.part==part)&(table.pressure_round==iteration)].sort_values("native_id")
        if not (np.array_equal(group.native_id.to_numpy(),ids) and (group.completed_step==step).all()):
            raise ValueError("Final CPU storage material IDs/step differ")
        frames.append((ids,group.actual_after_BC_float_Pa.to_numpy(dtype=np.float32),group.Jfull.to_numpy(dtype=np.float64)))
    return frames


def bind_native_pressure():
    # Independently index the BI4 headers, mapping the file read-only. Touch
    # only Idp, PorePress and PoroVolumeRatio particle payloads; the 22-field
    # native safety/CPU-GPU audit is already preserved separately.
    import mmap
    import numpy as np
    sys.path.insert(0,str(TEST.parents[1]/"02_TerzaghiConsolidation_q0_PR/tests/support"))
    from upl_tpi_partial_bi4_r1 import _Cursor, _item
    folder=OUT/B64
    results=[]
    def compare(mapped,part,ids,p,j):
        if mapped[:9]!=b"#FileJBD " or mapped[9:58].rstrip(b" ")!=b"JPartDataBi4":
            raise ValueError("Unexpected BI4 binary type")
        cursor=_Cursor(mapped,64)
        root,_,_,children=_item(cursor,0)
        cursor.finish("file")
        node,arr,types,_=children[0]
        if node["values"]["Cpart"]!=part or node["values"]["TimeStep"]!=(64*DT if part else 0.):
            raise ValueError("Native header differs from actual pressure rows")
        if (types["Idp"]["type_id"],types["PorePress"]["type_id"],types["PoroVolumeRatio"]["type_id"])!=(8,11,12):
            raise ValueError("Native material-ID/pressure/J types differ")
        order=np.argsort(arr["Idp"])
        if not np.array_equal(arr["Idp"][order],np.arange(37181)):
            raise ValueError("Native material set differs")
        actual_p=arr["PorePress"][order[ids]]
        actual_j=arr["PoroVolumeRatio"][order[ids]]
        if not np.array_equal(actual_p.view(np.uint32),p.view(np.uint32)) or not np.array_equal(actual_j.view(np.uint64),j.view(np.uint64)):
            raise ValueError("CPU final-round actual saved pressure/J differ")
        return dict(part=part,actual_time_s=float(node["values"]["TimeStep"]),soil_ids=len(ids),pressure_mismatches=0,J_mismatches=0)
    for part,(ids,p,j) in enumerate(native_pressure_frames(folder)):
        with (folder/"data"/("Part_%04d.bi4"%part)).open("rb") as f:
            with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
                results.append(compare(mm,part,ids,p,j))
    build_tools.write_new(LOG/(B64+".native_pressure_binding.json"),dict(passed=True,particle_payloads_read=["Idp","PorePress","PoroVolumeRatio"],
        arrays_rewritten=0,independent_full_native_safety_separate=True,frames=results))


def prepare_source():
    SRC.mkdir()
    shutil.copytree(OLD / "source", SRC / "source")
    shutil.copytree(OLD / "VS", SRC / "VS")
    local = SRC / "source"
    # Leave the full Cryer XYZ residual, diagonal and original no-HG force path intact.
    for name in ("JSphCpu.cpp", "JSphCpuSingle.cpp"):
        text = source_text(OLD / "source" / name)
        p3 = source_text(C02 / name)
        include = '#include "upl_tpi_cpu_r1.h"'
        text = once(text, include, include + '\n#include "upl_tpi_m0_dt_r2.h"')
        if name == "JSphCpu.cpp":
            start, end = "double JSphCpu::DtVariable(bool final){", "//-Additional local necessary scale"
            text = once(text, section(text, start, end), section(p3, start, end))
            start, end = "  double dt=CFLnumber*min(dt1,dt2);", "  if(DynamicPorePressure){"
            text = once(text, section(text, start, end), section(p3, start, end))
        else:
            start, end = "    upl_tpi_cpu_r1::Need(FixedDt", "    upl_tpi_cpu_r1::Need(HydroMech"
            text = once(text, section(text, start, end),
                '    upl_tpi_cpu_r1::Need(FixedDt && upl_tpi_m0_dt_r2::Enabled(true)\n'
                '      && upl_tpi_m0_dt_r2::AllowedDt(FixedDt->GetFixedValue(),HydroMechDrainageStartTime)\n'
                '      && SymplecticDtPre==FixedDt->GetFixedValue(), "Cryer P3 requires the admitted M0 step");\n')
            start, end = '    Log->Print("UplTpiCryerCpuOverlayR1:', '  }\n  RunGaugeSystem(TimeStep,true);'
            text = once(text, section(text, start, end),
                '    upl_tpi_m0_dt_r2::Init(static_cast<JSphCpu*>(this),DirOut,"CPU",std::getenv("UPL_TPI_CPU_R1"),TimeStep,Nstep,SymplecticDtPre,HydroMechDrainageStartTime);\n'
                '    Log->Print("Cryer P3: three full XYZ pressure defects per solid step, five M0 Eq40/Rh1 checks.");\n')
            start, end = "    if(upl_tpi_cpu_r1::Enabled()){\n", "    TimeStep+=stepdt;"
            original_rounds = section(text, start, end)
            rounds = section(p3, start, end)
            rounds = once(rounds, "      bool forceScratch=false;",
                '      upl_tpi_cpu_r1::Need(!HourglassCpu && SoilHourglassXi==0, "Cryer P3 requires HG0");\n      bool forceScratch=false;')
            text = once(text, original_rounds, rounds)
            for function in ("Saved", "Finish"):
                line = next(s for s in p3.splitlines() if "upl_tpi_m0_dt_r2::" + function + "(" in s)
                old_hook = next(s for s in text.splitlines() if "upl_tpi_cpu_r1::" + function + "(" in s)
                text = once(text, old_hook, old_hook + "\n" + line)
        (local / name).write_text(text, encoding="utf-8")
    shutil.copy2(C02 / "upl_tpi_cpu_r1.h", local / "upl_tpi_cpu_r1.h")
    time_policy = source_text(C02 / "upl_tpi_m0_dt_r2.h")
    time_policy = once(time_policy, "event==.0100002288818359375&&Bits(dt,event/1000.)", "event==.0078125&&Bits(dt,event/4096.)")
    (local / "upl_tpi_m0_dt_r2.h").write_text(time_policy, encoding="utf-8")
    # Verify the common CPU/GPU seed distributed by the root.
    original_seed = OUT / (INPUT_NAME + "_seed")
    if (original_seed / (INPUT_NAME + ".bi4")).read_bytes() != (SEED / (INPUT_NAME + ".bi4")).read_bytes():
        raise ValueError("Common CPU/GPU particle data differ")
    xml = (original_seed / (INPUT_NAME + ".xml")).read_bytes()
    for parameter in ("DtIni", "DtFixed"):
        old = ('key="%s" value="0.00000095367431640625"' % parameter).encode("ascii")
        new = ('key="%s" value="0.0000019073486328125"' % parameter).encode("ascii")
        if xml.count(old) != 1:
            raise ValueError("Missing original seed step parameter: " + parameter)
        xml = xml.replace(old, new)
    if xml != (SEED / (INPUT_NAME + ".xml")).read_bytes():
        raise ValueError("Common CPU/GPU input has additional changes")


def build():
    old, fresh = OUT / OLD_BUILD, OUT / BUILD
    fresh.mkdir()
    (fresh / "out").mkdir()
    shutil.copytree(old / "lib", fresh / "lib")
    intdir = Path(os.environ["LOCALAPPDATA"]) / "Temp" / BUILD / "int"
    intdir.mkdir(parents=True)
    target = fresh / "private_debug.targets"
    target.write_text(source_text(old / target.name).replace(OLD_BUILD, BUILD), encoding="utf-8")
    cmdfile = fresh / "load_environment.cmd"
    shutil.copy2(old / cmdfile.name, cmdfile)
    _, raw = build_tools.invoke(BUILD + ".environment", [os.environ["COMSPEC"], "/d", "/s", "/c", cmdfile.name], fresh, os.environ.copy(), True)
    env = {k.upper():v for k,v in os.environ.items()}
    env.update((k.upper(),v) for k,v in
        (line.split("=",1) for line in raw.decode("mbcs").splitlines() if "=" in line and not line.startswith("=")))
    for key in ("CL", "_CL_", "LINK", "_LINK_"):
        env.pop(key, None)
    old_call = build_tools.read(LOG / (OLD_BUILD + ".msbuild.call.json"))
    args = [str(build_tools.MSBUILD)] + [x.replace(str(OLD), str(SRC)).replace(OLD_BUILD, BUILD) for x in old_call["arguments"]]
    call, _ = build_tools.invoke(BUILD + ".msbuild", args, SRC / "VS", env)
    objects = list(intdir.glob("*.obj"))
    if len(objects) != 86:
        raise RuntimeError(f"Expected 86 new CPU objects; found {len(objects)}")
    for tu in ("JSphCpu", "JSphCpuSingle"):
        data = build_tools.read(intdir / (tu + ".dependencies.json"))["Data"]
        if Path(data["Source"]).resolve() != (SRC / "source" / (tu + ".cpp")).resolve():
            raise ValueError("Wrong TU in build: " + tu)
        for header in ("upl_tpi_cpu_r1.h", "upl_tpi_m0_dt_r2.h"):
            if (SRC / "source" / header).resolve() not in {Path(s).resolve() for s in data["Includes"]}:
                raise ValueError("Missing actual private time integration include: " + header)
    review = build_tools.read(LOG / (OLD_BUILD + ".build_review_r2.json"))
    for runtime in review["runtime"]:
        src = Path(runtime["destination"]["path"])
        shutil.copy2(src, fresh / "out" / src.name)
    program = fresh / "out/DualSPHysics5.2CPU_win64_debug.exe"
    build_tools.write_new(LOG / (BUILD + ".build.json"), dict(passed=True, call=call,
        program=build_tools.stat(program), source_root=str(SRC), object_count=len(objects), isolated=True))


def qualify_hg0():
    # C02 checks two HG history/rate values per ID per round. Cryer has no HG
    # object. Preserve the original C02 header and the first private link.
    local = SRC / "source"
    header = local / "upl_tpi_cpu_r1.h"
    text = source_text(header)
    for term in ("2ull*s.soilCount*(3*s.commits+round)", "6ull*s.soilCount*(s.commits+1)", "6ull*s.soilCount*s.commits"):
        text = once(text, "s.hgSnapshotChecks==" + term, "s.hgSnapshotChecks==0")
    old, fresh = OUT / BUILD, OUT / (BUILD + "_hg0")
    fresh.mkdir()
    (fresh / "out").mkdir()
    shutil.copy2(header, fresh / "before_hg0_specialization.h")
    header.write_text(text, encoding="utf-8")
    intdir = Path(os.environ["LOCALAPPDATA"]) / "Temp" / BUILD / "int"
    targets = source_text(old / "private_debug.targets")
    targets = targets.replace(str(old / "out"),str(fresh / "out")).replace(str(old / "evaluated_compile_sources.txt"),str(fresh / "evaluated_compile_sources.txt"))
    (fresh / "private_debug.targets").write_text(targets,encoding="utf-8")
    shutil.copy2(old / "load_environment.cmd", fresh / "load_environment.cmd")
    tag = BUILD + "_hg0"
    _,raw = build_tools.invoke(tag + ".environment", [os.environ["COMSPEC"],"/d","/s","/c","load_environment.cmd"], fresh, os.environ.copy(), True)
    env = {k.upper():v for k,v in os.environ.items()}
    env.update((k.upper(),v) for k,v in (r.split("=",1) for r in raw.decode("mbcs").splitlines() if "=" in r and not r.startswith("=")))
    for key in ("CL", "_CL_", "LINK", "_LINK_"):
        env.pop(key,None)
    args = build_tools.read(LOG / (BUILD + ".msbuild.call.json"))["arguments"]
    args = [arg.replace(str(old / "out"),str(fresh / "out")).replace(str(old / "private_debug.targets"),str(fresh / "private_debug.targets")).replace(str(LOG / (BUILD + ".binlog")),str(LOG / (tag + ".binlog"))) for arg in args]
    call,_ = build_tools.invoke(tag + ".msbuild", [str(build_tools.MSBUILD), *args], SRC / "VS", env)
    if not all((intdir / name).stat().st_mtime_ns>=header.stat().st_mtime_ns for name in ("JSphCpu.obj","JSphCpuSingle.obj")):
        raise RuntimeError("Corrected header was not rebuilt in both CPU translation units")
    for name in ("DsphConfig.xml","ChronoEngine.dll","dsphchrono.dll","vcomp140.dll","vcomp140d.dll"):
        shutil.copy2(old / "out" / name, fresh / "out" / name)
    program = fresh / "out/DualSPHysics5.2CPU_win64_debug.exe"
    build_tools.write_new(LOG / (tag + ".build.json"),dict(passed=True,call=call,program=build_tools.stat(program),header=build_tools.stat(header),required_HG_snapshot_checks=0))


def run():
    output = OUT / B64
    output.mkdir()
    program = OUT / (BUILD + "_hg0") / "out/DualSPHysics5.2CPU_win64_debug.exe"
    env = {k:v for k,v in os.environ.items() if not k.startswith("UPL_TPI")}
    env.update(UPL_TPI_CPU_R1="B", UPL_TPI_P3_ROWS_R1="3", UPL_TPI_M0_DT_R1="EQ40_RH1")
    argv = [str(program), "-cpu", "-ompthreads:8", "-stable", str(SEED / INPUT_NAME),
        str(output), "-dirdataout", "data", "-svres", "-nsteps:64"]
    call, _ = build_tools.invoke(B64, argv, output, env)
    with (output / "Run.csv").open(encoding="utf-8-sig") as file:
        row, = csv.DictReader(file, delimiter=";")
    summary = build_tools.read(output / "UplTpiP3CpuR1.summary.json")
    m0 = build_tools.read(output / "UplTpiP3DtR1.summary.json")
    ok = int(row["Steps"])==64 and int(row["PartFiles"])==2 and int(row["PartsOut"])==0
    ok = ok and int(row["Np"])==37181 and int(row["Nfixed"])==8 and summary["completed"]
    ok = ok and summary["commits"]==64 and summary["first_validations"]==64 and summary["second_validations"]==64
    ok = ok and summary["endpoint_calls"]==summary["endpoint_writes"]==192 and summary["actual_end"]==64*DT
    ok = ok and summary["core_field_bit_checks"]==7*37173*192 and summary["HG_readonly_snapshot_checks"]==0
    with (output / "UplTpiP3DtR1.csv").open(encoding="utf-8-sig") as file:
        saved = list(csv.DictReader(file))
    ok = ok and len(saved)==2 and all(int(saved[-1]["total_" + phase])==64 for phase in ("pre","cor","endpoint1","endpoint2","endpoint3"))
    ok = ok and float(saved[-1]["max_dt_minus_bound_s"])<=0
    build_tools.write_new(LOG / (B64 + ".run.json"), dict(passed=ok, call=call, program=build_tools.stat(program),
        seed=str(SEED), output=str(output), dt=DT, actual_end=summary["actual_end"],commits=summary["commits"],
        core_field_bit_checks=summary["core_field_bit_checks"], last_dt_row=saved[-1], m0_summary=m0, native_review_pending=True))
    if not ok:
        raise RuntimeError("CPU runtime/pressure or method-bound counters differ; inspect preserved tables")


def review():
    import numpy as np
    import pandas as pd
    output = OUT / B64
    trace = pd.read_csv(output / "UplTpiP3CpuR1.csv", float_precision="round_trip")
    groups = {}
    soil = np.arange(8, 37181)
    expected = {(0,0),(1,1),(1,2),(1,3)}
    for (part,iteration), rows in trace.groupby(["part","pressure_round"]):
        rows = rows.set_index("native_id").sort_index()
        if not np.array_equal(rows.index, soil) or not np.isfinite(rows.to_numpy()).all():
            raise ValueError("Soil ID ownership or finite pressure-round evidence differs")
        groups[(part,iteration)] = rows
    if set(groups) != expected or len(trace) != len(soil) * 4:
        raise ValueError("Initial or endpoint pressure-round rows incomplete")
    def f32(rows,key):
        return rows[key].to_numpy().astype(np.float32)
    def require_equal(actual, expected, label):
        if not np.array_equal(actual, expected):
            raise ValueError(label)
    init = groups[0,0]
    if (init["actual_save_time_s"]!=0).any() or (init["actual_after_BC_float_Pa"]!=0).any():
        raise ValueError("Initial state differs")
    first = groups[1,1]
    previous = f32(first,"mechanical_half_actual_float_Pa")
    results = []
    for iteration in (1,2,3):
        row = groups[1,iteration]
        if (row["source_step_zero_based"]!=63).any() or (row["completed_step"]!=64).any():
            raise ValueError("Output step differs")
        if (row["actual_save_time_s"]!=64*DT).any() or (row["source_time_s"]!=63*DT).any() or (row["dt_s"]!=DT).any():
            raise ValueError("Output clock differs")
        if row[["source_drained","endpoint_drained","provisional_or_final_commit_drained"]].ne(0).any().any():
            raise ValueError("Unexpected active drainage during ramp")
        q = f32(row,"endpoint_q_actual_float_Pa")
        require_equal(q.view(np.uint32), previous.view(np.uint32), "Round did not consume the actual preceding pressure")
        s,r = row["S_1_per_m_s"].to_numpy(), row["Rgamma_Pa_per_m_s"].to_numpy()
        if not np.all(s>0):
            raise ValueError("Nonpositive endpoint diagonal")
        candidate = (q.astype(np.float64) + r/s).astype(np.float32)
        actual = f32(row,"actual_after_BC_float_Pa")
        require_equal(candidate.view(np.uint32), f32(row,"raw_candidate_float_Pa").view(np.uint32), "Endpoint float pressure update differs")
        require_equal(actual.view(np.uint32), candidate.view(np.uint32), "Unexpected boundary change during ramp")
        for key in ("Jn","Jhalf","Jfull","theta_half_for_J_1_per_s","pn_Pa","previous_Pa"):
            require_equal(row[key].to_numpy(), first[key].to_numpy(), key + " changed between endpoint evaluations")
        step_change = candidate.astype(np.float64)-q
        results.append(dict(round=iteration,pressure_min_Pa=float(actual.min()),pressure_max_Pa=float(actual.max()),
            pressure_RMS_Pa=float(np.sqrt(np.mean(actual.astype(float)**2))),rms_correction_Pa=float(np.sqrt(np.mean(step_change**2))),
            rms_residual=float(np.sqrt(np.mean(r**2))),min_diagonal=float(s.min()),max_diagonal=float(s.max())))
        previous = actual
    predictor = first["pn_Pa"].to_numpy() + 0.5*(first["pn_Pa"].to_numpy()-first["previous_Pa"].to_numpy())
    require_equal(predictor,first["prediction_double_Pa"].to_numpy(),"History-based prediction differs")
    require_equal(predictor.astype(np.float32).view(np.uint32),f32(first,"mechanical_half_actual_float_Pa").view(np.uint32),"Mechanical stage pressure differs")
    build_tools.write_new(LOG / (B64+".pressure_review.json"),dict(passed=True,soil_count=len(soil),total_rows=len(trace),
        actual_time_s=64*DT,ramp_duration_s=2.**-8,drainage_opening_s=2.**-7,Jfull_min=float(first["Jfull"].min()),Jfull_max=float(first["Jfull"].max()),
        endpoint_rounds=results,actual_reference_rows_bound=True,native_cross_review_separate=True,physical_acceptance=False))


if __name__ == "__main__":
    {"prepare": prepare_source, "build": build, "qualify_hg0":qualify_hg0, "run": run, "review":review,
        "archive":archive_patch,"bind_native_pressure":bind_native_pressure}[sys.argv[1]]()
