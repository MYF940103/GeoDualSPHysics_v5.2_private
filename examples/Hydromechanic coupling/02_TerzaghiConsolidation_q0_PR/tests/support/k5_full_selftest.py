"""Offline preparation/guard self-test; never launches a solver."""
import collections
from decimal import Decimal
import itertools
import json
import re
import xml.etree.ElementTree as ET
import k5_full_sequence as flow
from mdbc_gpu_vector_run import bound,read


def signature(e):
    attrs=tuple(sorted((k,v) for k,v in e.attrib.items() if not k.endswith("comment")))
    return e.tag,attrs,(e.text or "").strip(),tuple(signature(c) for c in e)


def main():
    t=flow.TESTS;out=t/"logs/k5_full_selftest_r1.check.json";assert not out.exists()
    old=t/"configs/k5_long5_r1_c_Def.xml";new=t/"configs/k5_full_r1_Def.xml"
    a,b=ET.parse(old).getroot(),ET.parse(new).getroot()
    schedule=b.find("execution/special/timeout")
    assert [(float(x.attrib["time"]),float(x.attrib["timeout"])) for x in schedule]==[(0.,.000999999999),(15.,.1)]
    b.find("execution/special").remove(schedule)
    for key,value in (("TimeMax","728.75286"),("TimeOut","0.1")):
        xpath="execution/parameters/parameter[@key='"+key+"']"
        assert b.find(xpath).attrib["value"]==value
        b.find(xpath).attrib["value"]=a.find(xpath).attrib["value"]
    assert signature(a)==signature(b),"Only duration/output cadence may change"
    assert int(Decimal("728.75286")/Decimal(".000005"))==flow.STEPS
    expected=collections.deque(itertools.accumulate(itertools.repeat(flow.DT,flow.STEPS)),maxlen=1)[0]
    expected15=collections.deque(itertools.accumulate(itertools.repeat(flow.DT,3000000)),maxlen=1)[0]
    state=read(t/"logs/k5_long5_r1.status.json")
    assert expected15==state["runs"][0]["final"]["time_s"]
    assert expected==728.752858518274 and abs(expected-flow.END)<flow.DT
    assert .0027444522857366896*(expected-.01)>=2
    bat=t/"configs/xk5_full_r1_win64_GPU.bat";text=bat.read_text(encoding="utf8")
    assert re.findall(r'-nsteps:(\d+)',text)==[str(flow.STEPS)]
    assert "if exist \"%dirout%\" goto fail" in text and "-force" not in text
    assert "-first:!lastpart! -last:!lastpart!" in text
    folder=t/"outputs/k5_long5_r1_c"
    first=flow.cell.probe.native(folder,0);sample=flow.cell.probe.native(folder,100)
    flow.cell.metrics(sample,first)
    mutations={"stress_guard":lambda b:b.__setitem__("sigma_zz",b.sigma_zz+500),
        "resultant_guard":lambda b:b.__setitem__("load_az",b.load_az*.99),
        "drainage_guard":lambda b:b.__setitem__("drained",0),
        "native_id_guard":lambda b:b.__setitem__("id",b.id+1),
        "density_guard":lambda b:b.__setitem__("rho",-1)}
    rejected=[]
    for label,mutate in mutations.items():
        changed=sample.copy();mutate(changed)
        try:flow.cell.metrics(changed,first)
        except AssertionError:rejected.append(label)
        else:raise AssertionError("Guard mutation was not rejected: "+label)
    result=dict(passed=True,solver_started=False,xml_only_duration_output_changes=True,original_guard_mutations_rejected=rejected,
        expected_binary64_final_time_s=expected,nominal_time_s=flow.END,nominal_drift_s=expected-flow.END,
        fixed_step_count=flow.STEPS,retained_15s_accumulation_exact=True,original_physical_limits_unchanged=True,
        evidence=[bound(p) for p in (__file__,flow.__file__,flow.cell.__file__,old,new,bat,t/"logs/k5_long5_r1.status.json")])
    with out.open("x",encoding="utf8") as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!="evidence"},indent=2))


if __name__=="__main__":main()
