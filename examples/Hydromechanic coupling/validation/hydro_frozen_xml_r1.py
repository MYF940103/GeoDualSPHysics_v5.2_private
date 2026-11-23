"""Render a documented root input for use with its specific frozen GeoDualSPHysics release."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
SUITE=HERE.parent
TEMPLATES=HERE/"hydro_frozen_xml_templates_r1.json"
DYNAMIC="HydroMechDynamicSeepage"
MODEL="HydroMechModel"
LOAD=("HydroMechTopLoadMode","HydroMechTopLoadQ0","HydroMechTopLoadRampTime")
DRAIN=("HydroMechDrainage","HydroMechDrainageStartTime","HydroMechDrainageFixedGrid","HydroMechFreeSeepage")
OLD=(DYNAMIC,)+LOAD+DRAIN
MODES=("None","TopVertical","FlexibleConfinement","TopStripVertical","LianFlexibleStrip","TopKernelBand")


def need(ok, msg):
    if not ok:raise ValueError(msg)


def records():
    return json.loads(TEMPLATES.read_text(encoding="utf-8"))


def validate_template(name,raw):
    record=json.loads(TEMPLATES.read_text(encoding="utf-8")).get(name)
    need(record and len(raw)==record["size"] and hashlib.sha256(raw).hexdigest()==record["sha256"],
         "Archive template differs from the registered original: "+name)


def tree(raw):
    return ET.fromstring(raw,parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True,insert_pis=True)))


def emit(root):
    ET.indent(root,space="    ")
    return ET.tostring(root,encoding="utf-8",xml_declaration=True)+b"\n"


def single(parent,name,required=False):
    items=parent.findall(name)
    need(len(items)==1 if required else len(items)<=1, f"Expected {'one' if required else 'at most one'} {name}")
    return items[0] if items else None


def nodes(root):
    execution=single(root,"execution",True)
    special=single(execution,"special",True)
    return special,single(special,"hydromechanics",True)


def scalar(value):
    v=float(value);need(math.isfinite(v) and v>=0,"Nonnegative finite number required: "+value);return v


def flag(value):
    value=value.lower()
    need(value in ("0","1","true","false"),"Unknown boolean: "+value)
    return value in ("1","true")


def loadmode(value):
    m=next((i for i,name in enumerate(MODES) if value in (str(i),) or value.lower()==name.lower()),None)
    need(m is not None,"Unknown externalload mode: "+value)
    return m


def original_model(name,water):
    dynamic=single(water,DYNAMIC)
    enabled=dynamic is not None and flag(dynamic.get("value"))
    if name in ("CaseCryer_TPI_P3_nu030_full_r1_Def.xml","CaseCryer_TPI_P3_nu030_peak_r1_Def.xml"):
        need(enabled,"P3 portable requires its old dynamic branch and three external runtime selectors")
        return 2
    return int(enabled)


def modernize(name,original):
    need(name in records(),"Not one of the 21 retained formal inputs")
    root=tree(original)
    special,water=nodes(root)
    need(single(water,MODEL) is None and single(special,"externalload") is None and single(special,"drainage") is None,"Mixed source XML")
    model=original_model(name,water)
    values={}
    for key in OLD:
        elem=single(water,key)
        if elem is not None:
            values[key]=elem.attrib["value"];water.remove(elem)
    water.insert(1,ET.Element(MODEL,value=str(model)))
    lm=loadmode(values.get(LOAD[0],"0"));q=values.get(LOAD[1],"0");r=values.get(LOAD[2],"0")
    need((not lm and scalar(q)==0 and scalar(r)==0) or (lm and scalar(q)>0),"Original load inconsistent")
    if lm:
        ET.SubElement(special,"externalload",mode=str(lm),q0=q,ramptime=r)
    drained=flag(values.get(DRAIN[0],"1"));free=flag(values.get(DRAIN[3],"0"));fixed=flag(values.get(DRAIN[2],"0"));start=values.get(DRAIN[1],"0")
    need(not (drained and free) and (drained or (not fixed and scalar(start)==0)),"Inconsistent source drainage")
    attrs={"mode":"freeSeepage" if free else "drained" if drained else "off"}
    if drained:
        attrs["start"]=start
        attrs["clock"]="fixedStep" if fixed else "time"
    ET.SubElement(special,"drainage",attrs)
    return emit(root)


def mode_values(special,water):
    for legacy in OLD:need(single(water,legacy) is None,"Legacy key in modern input: "+legacy)
    model=single(water,MODEL)
    if model is not None:
        need(set(model.attrib)<= {"value","comment","units_comment"} and not list(model),"Invalid HydroMechModel")
    value=model.get("value") if model is not None else "0"
    need(value in ("0","1","2"),"HydroMechModel must be 0, 1 or 2")
    load=single(special,"externalload")
    drain=single(special,"drainage")
    a=load.attrib if load is not None else {}
    d=drain.attrib if drain is not None else {}
    need(set(a)<={"mode","q0","ramptime","comment","units_comment"} and (load is None or not list(load)),"Unknown externalload option")
    need(set(d)<={"mode","start","clock","comment","units_comment"} and (drain is None or not list(drain)),"Unknown drainage option")
    m=loadmode(a.get("mode","0"));q=a.get("q0","0");r=a.get("ramptime","0")
    need((m and scalar(q)>0) or (not m and scalar(q)==0 and scalar(r)==0),"Inconsistent externalload")
    scalar(r)
    dm=d.get("mode","drained").lower();clock=d.get("clock","time").lower();start=d.get("start","0")
    need(dm in ("drained","off","freeseepage") and clock in ("time","fixedstep"),"Unknown drainage mode or clock")
    need(dm=="drained" or ("start" not in d and "clock" not in d),"start/clock only permitted with drained boundary")
    scalar(start)
    return int(value),{LOAD[0]:str(m),LOAD[1]:q,LOAD[2]:r,DRAIN[0]:str(int(dm=="drained")),DRAIN[1]:start,
               DRAIN[2]:str(int(clock=="fixedstep")),DRAIN[3]:str(int(dm=="freeseepage"))}


def xml_contents(element):
    """Ignore only lexical XML presentation in the public document, never a field or annotation."""
    text = element.text if element.text and element.text.strip() else None
    tail = element.tail if element.tail and element.tail.strip() else None
    return (element.tag, element.attrib, text, tail, [xml_contents(child) for child in element])


def restore(name,original,modern):
    validate_template(name,original)
    canonical=modernize(name,original)
    if canonical==modern or xml_contents(tree(canonical))==xml_contents(tree(modern)):
        return original
    item=records()[name]
    need(item["case"] not in ("04","08"),"Frozen release: a manifest/seed or a material-and-wall handoff binds this input; publish a separately verified version for edited XML")
    # FreshPR / Lian strip: emit a separately derived variant, using only options verified in that frozen input.
    root=tree(modern);special,water=nodes(root)
    old=tree(original);_,oldwater=nodes(old)
    model,values=mode_values(special,water)
    base_special,base_water=nodes(tree(canonical))
    base_model,base_values=mode_values(base_special,base_water)
    need(model==base_model,"This frozen program has no verified representation for changing HydroMechModel (in particular, never map TPI to dynamic=1)")
    for selector in OLD+(MODEL,"externalload","drainage"):
        expected=(water.find(selector) if selector==MODEL else special.find(selector) if selector in ("externalload","drainage") else None)
        need(all(n is expected for n in root.iter(selector)),"Misplaced or mixed selector: "+selector)
    public_names={n.tag for n in base_water if isinstance(n.tag,str)}
    need({n.tag for n in water if isinstance(n.tag,str)}-{MODEL}==public_names-{MODEL},
            "Frozen hydromechanics material property set changed; verify a new release before adding or removing properties")
    need(all(len(water.findall(key))<=1 for key in public_names),"Duplicate hydraulic property")
    for parent,key,base_parent in ((water,MODEL,base_water),(special,"externalload",base_special),(special,"drainage",base_special)):
        element,template=parent.find(key),base_parent.find(key)
        for attr in ("comment","units_comment"):
            before=None if template is None else template.get(attr)
            after=None if element is None else element.get(attr)
            need(before==after,"Changed merged XML annotation is not representable losslessly by frozen per-field annotations: "+key)
    for parent,key in ((water,MODEL),(special,"externalload"),(special,"drainage")):
        n=single(parent,key)
        if n is not None:parent.remove(n)
    for key in OLD:
        template=single(oldwater,key)
        if template is None:
            if key in values:
                need(scalar(values[key])==scalar(base_values[key]),"Frozen input cannot express edit to "+key+" without new runtime verification")
            continue
        n=copy.deepcopy(template)
        if key in values and scalar(values[key])!=scalar(base_values[key]):
            n.set("value",values[key])
        water.append(n)
    return emit(root)


def write_new(path,raw):
    with path.open("xb") as output:output.write(raw)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action",choices=("modern","restore"))
    ap.add_argument("--template",type=Path,required=True,help="Original frozen *_Def.xml; keep in a versioned archive")
    ap.add_argument("--modern",type=Path,help="Modern user input for restore")
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args();raw=args.template.read_bytes()
    if args.action=="modern":
        validate_template(args.template.name,raw)
        need(args.modern is None,"Unexpected modern input");result=modernize(args.template.name,raw)
    else:
        need(args.modern is not None,"Missing modern input");result=restore(args.template.name,raw,args.modern.read_bytes())
    write_new(args.out,result)
