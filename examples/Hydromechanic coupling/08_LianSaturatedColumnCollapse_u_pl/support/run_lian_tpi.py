"""Run or review the three formal C08 TPI GPU releases from their certified preloads."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from run_lian_release import BIN, CASE, GROUPS, validate_solver
from postprocess_lian_release import native, verify_source_material

TESTS = CASE/"tests"
LOGS = TESTS/"logs"
RUNS = TESTS/"outputs"
BUILD = RUNS/"c08_tpi_formal_build_r1"
INPUTS = RUNS/"c08_tpi_formal_inputs_r1"
RUNTIME = CASE/"support/runtime_tpi_r1"
TAG = "c08_tpi_formal_three_r1"
ORDER = ("psi2p5", "psi0", "psim5")
STEPS = {"short":2_000_208, "full":2_600_200}
RT_FILES = ("ChronoEngine.dll", "dsphchrono.dll", "vcomp140.dll", "DsphConfig.xml")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(file):
    return json.loads(file.read_text(encoding="utf-8-sig"))


def now():
    return datetime.now(timezone.utc).isoformat()


def file_id(path):
    info = path.stat()
    return dict(path=str(path), bytes=info.st_size, mtime_ns=info.st_mtime_ns)


def write(path, data):
    with path.open("x", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def result(group):
    return CASE/f"CaseLianCollapse_{group}_TPI_GPU_out"


def short_dir(group):
    return RUNS/f"c08_tpi_formal_{group}_short_r1"


def pre_frame(group):
    return CASE/f"CaseLianCollapse_{group}_pre_GPU_out/data/Part_1000.bi4"


def install():
    build = load(BUILD/"build.json")
    static = load(BUILD/"static_review.json")
    candidate = Path(build["program"])
    require(file_id(candidate)==build["executable"] and static["linked_objects"]==113 and static["unchanged_objects"]==112
            and static["changed_cuda_objects"]==0 and static["symbols_equal"] and static["dependencies_equal"],
            "Private TPI executable and static review do not agree")
    RUNTIME.mkdir()
    exe = RUNTIME/candidate.name
    shutil.copy2(candidate,exe)
    require(hashlib.sha256(exe.read_bytes()).hexdigest()==build["sha256"], "Runtime copy changed")
    for name in RT_FILES:
        shutil.copy2(BUILD/name,RUNTIME/name)
    write(RUNTIME/"manifest.json",dict(program=exe.name, sha256=build["sha256"],
          build=build["executable"], installed_utc=now(), public_solver=False,
          beta=.04, files=[file_id(RUNTIME/name) for name in (exe.name,*RT_FILES)]))
    print(f"Installed {exe}",flush=True)


def runtime():
    location = Path(os.environ.get("C08_TPI_BIN",RUNTIME)).resolve()
    proof = load(location/"manifest.json")
    exe = location/proof["program"]
    # When copied elsewhere, check executable content rather than absolute machine paths.
    if file_id(exe)!=proof["files"][0]:
        require(hashlib.sha256(exe.read_bytes()).hexdigest()==proof["sha256"], "Wrong TPI binary")
    require(proof["beta"]==.04 and not proof["public_solver"] and all((location/name).is_file() for name in RT_FILES),
            "Missing TPI runtime files or wrong policy")
    return exe


def prepare(group):
    source = pre_frame(group)
    directory = source.parents[1]
    provenance = load(directory/"provenance.json")
    require(provenance["state"]=="completed" and provenance["group"]==group and provenance["stage"]=="preload",
            f"Original preload is not complete for {group}")
    validate_solver(directory,"preload")
    metadata, fields = native(source)
    verify_source_material(metadata,group)
    require(metadata["Step"]+1==2_000_000 and metadata["Nout"]==0 and len(fields)==22,
            f"Unexpected release source for {group}")
    stem = f"CaseLianCollapse_{group}_TPI"
    definition = CASE/(stem+"_Def.xml")
    base = CASE/(f"CaseLianCollapse_{group}_Def.xml")
    declared = ET.parse(definition)
    original = ET.parse(base)
    special = declared.find("execution/special")
    time = declared.find('execution/parameters/parameter[@key="TimeMax"]')
    model = special.find("hydromechanics/HydroMechModel")
    require(model.get("value")=="2" and time.get("value")=="13.001" and
            special.find("drainage").get("mode")=="freeSeepage" and
            special.find("gravitypreload").get("statefile")==f"../{directory.name}/data/Part_1000.bi4",
            "Expected TPI, positive-only free seepage, original material source and 3 s release")
    original.find("execution/special/hydromechanics/HydroMechModel").attrib.update(model.attrib)
    original.find('execution/parameters/parameter[@key="TimeMax"]').attrib.update(time.attrib)
    require(ET.tostring(original.getroot())==ET.tostring(declared.getroot()),
            f"Unexpected changes to physical parameters in {definition.name}")
    folder = INPUTS/group
    seed = folder/stem
    receipt = folder/"inputs.json"
    if receipt.is_file():
        frozen = load(receipt)
        require(frozen["source"]==file_id(source) and frozen["definition"]==file_id(definition) and
                all(file_id(Path(item["path"]))==item for item in frozen["files"]),"Retained GenCase inputs differ")
        return seed
    folder.mkdir(parents=True)
    gencase = BIN/"GenCase_win64.exe"
    call("gen", [gencase,definition.with_suffix(""),seed,"-save:all"], folder)
    generated = ET.parse(seed.with_suffix(".xml"))
    execution = generated.find("execution")
    parts=execution.find("particles")
    registry = [(int(x.get("mkbound")),int(x.get("begin")),int(x.get("count"))) for x in parts.findall("fixed")]
    require(registry==[(0,0,255),(1,255,1550),(2,1805,255)] and
            parts.get("np")=="7060" and parts.get("nbf")=="2060" and
            parts.find("fluid").get("begin")=="2060" and parts.find("fluid").get("count")=="5000" and
            float(execution.find("constants/dp").get("value"))==.04,
            f"Generated registry differs for {group}")
    execution.find("special/gravitypreload").set("statefile",str(source))
    generated.write(seed.with_suffix(".xml"),encoding="utf8",xml_declaration=True)
    fields = [seed.with_suffix(".xml"), seed.with_suffix(".bi4"), folder/(stem+"_Normals.nbi4")]
    write(receipt,dict(group=group, source=file_id(source), definition=file_id(definition),
                      files=[file_id(p) for p in fields], registry=registry, beta=.04))
    return seed


def call(stage, argv, directory, env=None):
    start = directory/f"{stage}.start.json"
    end = directory/f"{stage}.call.json"
    args = [str(a) for a in argv]
    owner = dict(argv=args, executable=file_id(Path(args[0])), owner_pid=os.getpid(), start_utc=now())
    require(not start.exists() and not end.exists(), f"Preserve existing stage {start}")
    with (directory/f"{stage}.console.log").open("xb") as f:
        with subprocess.Popen(args,cwd=CASE,env=env,stdout=f,stderr=subprocess.STDOUT) as child:
            owner["child_pid"] = child.pid
            write(start,owner)
            ret = child.wait()
    write(end,dict(owner,returncode=ret,end_utc=now()))
    require(ret==0,f"{stage} exit code {ret} in {directory}; inspect first failure and last sealed PART")
    return ret


def solver(exe, group, seed, window):
    folder = short_dir(group) if window=="short" else result(group)
    folder.mkdir()
    frozen = load(seed.parent/"inputs.json")
    write(folder/"launch_inputs.json",dict(group=group, window=window, input_registry=file_id(seed.parent/"inputs.json"),
          source=frozen["source"], executable=file_id(exe), beta=.04, limit=STEPS[window]))
    args = [exe, "-gpu:0", "-stable", "-mdbc_freeslip:1", seed, folder, "-dirdataout", "data",
            "-svres", f"-nsteps:{STEPS[window]}"]
    call("solver",args,folder,env=dict(os.environ,C08_PRIVATE_BETA="0.04"))
    return folder


def postprocess(group, folder, window):
    sealed = load(folder/"solver.call.json")
    require(sealed["returncode"]==0 and folder.exists(), "Successful solver receipt required")
    args = [sys.executable,"-B","-X","utf8",CASE/"support/postprocess_lian_tpi.py",
            group,folder,"--window",window]
    if window=="full":
        args += ["--short",short_dir(group)]
    # The review tool adopts retained success. It can repair separate derived products offline.
    subprocess.run(args,cwd=CASE,check=True)


def short_passed(group):
    folder = short_dir(group)
    receipt = load(folder/"postprocess_tpi.native.json")
    call_result = load(folder/"solver.call.json")
    require(receipt["passed"] and call_result["returncode"]==0, f"Short window rejected for {group}")


def dispatch(groups, mode):
    if mode=="prepare":
        for group in groups:
            print(prepare(group))
        return []
    exe = runtime() if mode!="post" else None
    errors = []
    prepared = {}
    if mode!="post":
        for group in groups:
            try:
                seed=prepare(group)
                if not short_dir(group).exists():
                    folder=solver(exe,group,seed,"short")
                    postprocess(group,folder,"short")
                short_passed(group)
                prepared[group]=seed
            except Exception as exc:
                errors.append(dict(group=group,stage="short",error=str(exc)))
                print(f"{group} startup rejected: {exc}",file=sys.stderr,flush=True)
    if mode=="short":
        return errors
    for group in groups if mode=="post" else prepared:
        try:
            if mode!="post":
                solver(exe,group,prepared[group],"full")
            postprocess(group,result(group),"full")
        except Exception as exc:
            errors.append(dict(group=group,stage="full" if mode!="post" else "post",error=str(exc)))
            print(f"{group} full stage interrupted: {exc}",file=sys.stderr,flush=True)
    if len(groups)==3 and not errors:
        try:
            subprocess.run([sys.executable,"-B","-X","utf8",CASE/"support/postprocess_lian_tpi.py","all"],
                           cwd=CASE,check=True)
        except subprocess.CalledProcessError as exc:
            errors.append(dict(stage="combined_figures",error=str(exc)))
    return errors


def own(groups, cli, thread):
    require(cli.is_file() and thread and thread==os.environ.get("CODEX_THREAD_ID"),
            "Owned run requires this task's continuation channel")
    prefix=LOGS/TAG
    write(prefix.with_suffix(".owner.json"),dict(groups=groups,owner_pid=os.getpid(),start_utc=now(),thread=thread))
    try:
        errors = dispatch(groups,"run")
    except Exception as exc:
        errors = [dict(stage="runner",error=str(exc))]
    terminal=prefix.with_suffix(".terminal.json")
    completed=[g for g in groups if not any(e.get("group")==g or e["stage"]=="runner" for e in errors)]
    write(terminal,dict(completed=completed,errors=errors,end_utc=now()))
    message=(f"已授权 C08 根目录三组正式 TPI GPU 顺序已终态。请读取 {terminal} 及各组实际 "
             "solver.start/call、postprocess_tpi.native 和 figures/validation_tpi 的原生数据与对照。"
             "完成的求解仅修复派生结果，失败保留首个真实错误和最后原生帧，勿启动重复求解。"
             "此直接通知一次，勿重发或重新布防。")
    write(prefix.with_suffix(".queue_attempt.json"),dict(utc=now(),terminal=str(terminal)))
    try:
        rc=subprocess.run([str(cli),"queue","--thread",thread,"--message",message],
                          cwd=CASE,capture_output=True,timeout=45).returncode
        outcome=dict(returncode=rc)
    except (OSError,subprocess.TimeoutExpired) as exc:
        outcome=dict(delivery="unknown",error=str(exc))
    write(prefix.with_suffix(".queue_result.json"),outcome)
    return int(bool(errors))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group",choices=(*GROUPS,"all"),default="all")
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument("--install",action="store_true")
    modes.add_argument("--prepare-only",action="store_true")
    modes.add_argument("--short-only",action="store_true")
    modes.add_argument("--postprocess-only",action="store_true")
    modes.add_argument("--own",action="store_true")
    parser.add_argument("--cli",type=Path)
    parser.add_argument("--thread")
    args=parser.parse_args()
    which=ORDER if args.group=="all" else (args.group,)
    if args.install:
        install()
    elif args.own:
        if not args.cli:
            parser.error("--own requires --cli and --thread")
        sys.exit(own(which,args.cli,args.thread))
    else:
        mode="prepare" if args.prepare_only else "short" if args.short_only else "post" if args.postprocess_only else "run"
        sys.exit(int(bool(dispatch(which,mode))))
