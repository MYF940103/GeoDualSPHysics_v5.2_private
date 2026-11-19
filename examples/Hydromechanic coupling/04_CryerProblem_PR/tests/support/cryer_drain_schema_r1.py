"""Verify the structured drainage XML on the private, three-round Cryer CPU/GPU solvers."""
import argparse
import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import cryer_model_strict_r1 as old
from cryer_row_gpu_r1 import call, load, need, save
from cryer_xml_prepare_r1 import edit, replace

KEYS = ("HydroMechDrainage", "HydroMechDrainageStartTime", "HydroMechDrainageFixedGrid")


def tag(backend):
    return "cryer_drain_schema_" + backend + "_r1"


def private_source(backend):
    return old.OUT / (tag(backend) + "_source")


def prepare(backend):
    previous = old.source_root(backend)
    result = private_source(backend)
    unit = Path("source") if backend == "cpu" else Path()
    public = (old.PUBLIC/"JSph.cpp").read_text(encoding="latin1")
    read = old.block(public, "void JSph::ReadDrainage(", "\n//====")
    # The old private solver has no atmospheric free-seepage operator or storage field.
    read = replace(read, '  HydroMechFreeSeepage=(mode=="freeseepage");',
                   '  if(mode=="freeseepage")Run_Exceptioon("Private Cryer does not implement freeSeepage.");')
    allowlist = "  if(hydroNode)sxml->CheckElementNames(hydroEle,true,"
    strength = "  //-Soil strength parameters."
    def cpp(text):
        text = replace(text, "void JSph::ReadExternalLoad(",read + "\nvoid JSph::ReadExternalLoad(")
        text = replace(text, old.block(text,allowlist,strength), old.block(public,allowlist,strength))
        entry = '  ReadExternalLoad(sxml,solidEle->Parent()->ToElement());'
        return replace(text, old.block(text, '  HydroMechDrainage=sxml->ReadElementBool(',entry),
                       '  ReadDrainage(sxml,solidEle->Parent()->ToElement());\n')
    signature = '  void ReadExternalLoad('
    header = lambda s: replace(s, signature, '  void ReadDrainage(const JXml *xml,const TiXmlElement *special);\n' + signature)
    for filename, change in (("JSph.cpp",cpp),("JSph.h",header)):
        change((previous/unit/filename).read_text(encoding="latin1"))
    shutil.copytree(previous,result)
    edit(result/unit/"JSph.cpp",cpp)
    edit(result/unit/"JSph.h",header)


def seed(backend, profile, output, *, new=True, event=False, reject=False):
    reference = old.OUT / (old.tag(backend) + "_" + profile)
    original = reference.with_name(reference.name + "_seed")/old.SEED_NAME
    prefix = output.with_name(output.name + "_seed")/old.SEED_NAME
    prefix.parent.mkdir()
    tree = ET.parse(original.with_suffix(".xml"))
    special = tree.find("execution/special")
    hydro = special.find("hydromechanics")
    enabled,start,clock = [hydro.find(k) for k in KEYS]
    need((enabled.get("value"),clock.get("value"))==("1","1"),"Expected drained fixedStep reference")
    if event:
        dt = 2.**-20
        start.set("value", str(2*dt))
        special.find("externalload").set("ramptime", str(dt))
        tree.find("execution/parameters/parameter[@key='TimeOut']").set("value",str(dt))
    if new:
        for child in (enabled,start,clock):
            hydro.remove(child)
        attrs = {"mode":"drained","start":start.get("value"),"clock":"fixedStep"}
        ET.SubElement(special,"drainage", {"mode":"freeSeepage"} if reject else attrs)
    tree.write(prefix.with_suffix(".xml"), encoding="utf-8", xml_declaration=True)
    shutil.copyfile(original.with_suffix(".bi4"),prefix.with_suffix(".bi4"))
    return prefix,reference



def event_run(backend, *, new, reject=False):
    """Run a fresh four-update explicit u-pl receiver using a real old or new executable."""
    label = tag(backend) + ("_freeSeepage" if reject else "_event_new" if new else "_event_old")
    output = old.OUT/label
    receipt = old.LOG/(label + ".call.json")
    need(not output.exists() and not receipt.exists(), "Fresh event output required")
    prefix,_ = seed(backend, "model1", output, new=new, event=True, reject=reject)
    build = (tag(backend) if new else old.tag(backend)) + ("_DebugCPU" if backend=="cpu" else "_Release")
    binding = load(old.LOG/(build+".build.json"))
    exe = Path(binding["program"]["path"])
    need(binding["passed"] and exe.stat().st_size == binding["program"]["bytes"], "Private executable binding")
    args = [str(exe),"-"+backend]
    if backend=="cpu":
        args.append("-ompthreads:8")
    args += ["-stable",str(prefix),str(output),"-dirdataout","data","-svres","-nsteps:4"]
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith("UPL_TPI")}
    log = old.LOG/(label+".console.log")
    result = call(args,exe.parent,env,log)
    save(receipt,result)
    need(result["popen_exit"]==result["win32_exit"]==(1 if reject else 0), "Unexpected exit: "+str(log))
    if reject:
        need("Private Cryer does not implement freeSeepage." in log.read_text(errors="replace")
             and not list((output/"data").glob("Part_*.bi4")), "Expected unsupported private freeSeepage rejection")


def review_event(backend):
    import struct
    from cryer_p3_verify_r1 import physical, snapshot
    roots = [old.OUT/(tag(backend)+"_event_"+k)/"data" for k in ("old","new")]
    dt = 2.**-20
    steps = list(range(5))
    expected_files = ["Part_%04d.bi4"%step for step in steps]
    for root in roots:
        need(sorted(p.name for p in root.glob("Part_*.bi4")) == expected_files, "Four actual updates and five native saves")
    history = []
    for step,leaf in zip(steps,expected_files):
        (old_state,old_error),(actual,error) = [snapshot(root/leaf,step,step,dt) for root in roots]
        if step==0:
            initial = actual["Posd"]
        need(struct.pack("<d",old_error)==struct.pack("<d",error), "Signed dt error changed")
        for name in actual:
            need(old_state[name].tobytes()==actual[name].tobytes(), "Event native difference: "+name)
        sample = physical(actual,initial,step>2)
        history.append(dict(step=step,time_s=dt*step,surface_count=sample["surface_count"],
                            active_drained=sample["active_drain_count"],surface_max_abs_p_Pa=sample["surface_p_absmax_Pa"]))
    need(history[2]["surface_max_abs_p_Pa"]>0, "Event sample must exercise nonzero pre-open surface pressure")
    save(old.LOG/(tag(backend)+"_event.check.json"),
         dict(passed=True,model=1,dt_s=dt,start_s=2*dt,exact_arrays=22,ids_per_frame=37181,history=history))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend",choices=("cpu","gpu"))
    parser.add_argument("action",choices=("prepare","build","suite","event-old","event-new","event-review","reject"))
    opts = parser.parse_args()
    if opts.action == "prepare":
        prepare(opts.backend)
    elif opts.action == "build":
        old.build(opts.backend, tag(opts.backend), private_source(opts.backend))
    elif opts.action.startswith("event-") or opts.action=="reject":
        if opts.action=="event-review":
            review_event(opts.backend)
        else:
            event_run(opts.backend, new=opts.action!="event-old", reject=opts.action=="reject")
    else:
        for profile in old.VALID:
            old.run(opts.backend, profile, build_name=tag(opts.backend), prepare_seed=seed)
