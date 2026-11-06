"""Prepare narrow release tests and a pure10s preload; never run a program."""
import json,re,shutil,xml.etree.ElementTree as ET
from pathlib import Path
T=Path(__file__).resolve().parents[1]
BASE='CaseLianSaturatedColumnCollapse_prestress_check_r1'
SOURCE=T/'outputs/upl_prestress_check_r1_seed'/BASE
def change(text,key,value,comment):
    pattern=r'(<parameter\s+key="'+re.escape(key)+r'"\s+value=")[^"]*("\s+comment=")[^"]*'
    text,n=re.subn(pattern,lambda m:m.group(1)+value+m.group(2)+comment,text)
    assert n==1,(key,n)
    return text
items=[('on','CaseLianSaturatedColumnCollapse_releasecheck_r1','0.002','0.0001','0.00095',800),
       ('smoke','CaseLianSaturatedColumnCollapse_releasesmoke_r1','0.0001','0.00005','0.00005',40),
       ('preload10','CaseLianSaturatedColumnCollapse_prestress10_r1','10.0','0.01',None,4000000)]
outputs=[]
for tag,name,end,cadence,event,steps in items:
    seed=T/'outputs'/('upl_gravity_release_'+tag+'_r1_seed')
    assert not seed.exists();seed.mkdir()
    for suffix in ('_Def.xml','.xml'):
        src=T/'configs'/(BASE+suffix);dst=T/'configs'/(name+suffix)
        assert not dst.exists();text=src.read_text(encoding='utf-8')
        text=change(text,'TimeMax',end,'Physical seconds; fresh diagnostic step cap '+str(steps))
        text=change(text,'TimeOut',cadence,'Decimal physical output interval; retain actual saved times')
        if event is not None:
            text=change(text,'PartsOutMax','0','No fluid loss allowed; planned fixed-wall retirement is accounted separately')
            anchor=re.search(r'^([ \t]*)</hydromechanics>[^\n]*\n',text,re.M);assert anchor
            at=anchor.end();text=text[:at]+anchor.group(1)+'<gravitypreload time="'+event+'" release_mkbound="2" comment="Preload-only damping and Shepard; retire right wall before next predictor" />\n'+text[at:]
        root=ET.fromstring(text)
        assert len(root.findall('.//gravitypreload'))==int(event is not None)
        assert root.find('.//SoilDampingCoef') is None # existing parameter is unchanged
        with dst.open('x',encoding='utf-8',newline='') as f:f.write(text)
        if suffix=='.xml':shutil.copy2(dst,seed/(name+'.xml'))
        outputs.append(str(dst))
    for suffix in ('.bi4','_Normals.nbi4'):shutil.copy2(str(SOURCE)+suffix,seed/(name+suffix))
    outputs.append(str(seed))
p=T/'notes/upl_gravity_release_inputs_r1.json'
with p.open('x',encoding='utf-8') as f:
    json.dump(dict(stage='upl_gravity_release_inputs_r1',prepared_only=True,
        dt_s=.0000025,geometry_unchanged=True,GenCase_invocations=0,
        OFF='Reuse existing prestress_check seed,400 updates,end.001,out.0001; no event',
        ON=dict(steps=800,end_s=.002,output_s=.0001,event_s=.00095,fluid_loss_allowed=0),
        smoke=dict(steps=40,end_s=.0001,output_s=.00005,event_s=.00005),
        preload10=dict(steps=4000000,end_s=10,output_s=.01,event_absent=True,
            damping=.02,Shepard_interval=40,solver_started=False,equilibrium_accepted=False),
        direct_effective_stress_assignment=False,unsupported_restart=False,
        solver_invocations=0,SHA_scans=0,outputs=outputs),f,indent=2);f.write('\n')
print(json.dumps(dict(prepared=True,physical_solver_started=False,preload10_steps=4000000)))
