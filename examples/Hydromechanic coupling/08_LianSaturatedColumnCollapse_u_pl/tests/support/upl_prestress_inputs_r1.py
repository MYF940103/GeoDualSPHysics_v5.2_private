"""Prepare fresh decimal-time static-head / damped gravity inputs; no program starts."""
import json,re,shutil,xml.etree.ElementTree as ET
from pathlib import Path
T=Path(__file__).resolve().parents[1]
BASE='CaseLianSaturatedColumnCollapse_preload_r1'
def change(text,key,value,comment,parameter=False):
    pattern=(r'(<parameter\s+key="'+re.escape(key)+r'"\s+value=")[^"]*("\s+comment=")[^"]*' if parameter else r'(<'+re.escape(key)+r'\s+value=")[^"]*("\s+comment=")[^"]*')
    text,count=re.subn(pattern,lambda m:m.group(1)+value+m.group(2)+comment,text)
    assert count==1,(key,count)
    return text
items=(('check','0.001','0.0001',400),('gravity','5.0','0.01',2000000))
outputs=[]
for stage,end,cadence,steps in items:
    name='CaseLianSaturatedColumnCollapse_prestress_'+stage+'_r1'
    seed=T/'outputs'/('upl_prestress_'+stage+'_r1_seed')
    assert not seed.exists();seed.mkdir()
    for suffix in ('_Def.xml','.xml'):
        src=T/'configs'/(BASE+suffix);dst=T/'configs'/(name+suffix)
        assert not dst.exists();text=src.read_text(encoding='utf-8')
        for key,val,comment,par in (
            ('PoreShepardRegularization','1','Optional excess-pressure Shepard during gravity preload',False),
            ('HydroMechInitMode','ConstantZ','Initialize hydrostatic pressure only; effective stress starts at zero',False),
            ('SoilDamping','1','Bui-Fukagawa damping during actual gravity preload',True),
            ('DtIni','0.0000025','Decimal initial step below the original coupled limits',True),
            ('DtFixed','0.0000025','Fixed 2.5 microsecond step; unchanged necessary stability checks',True),
            ('TimeMax',end,'Gravity preload '+end+' seconds; CLI step cap '+str(steps),True),
            ('TimeOut',cadence,'Decimal physical output interval; actual native times retained',True)):
            text=change(text,key,val,comment,par)
        anchor=re.search(r'^([ \t]*)<HydroMechInitMode[^\n]*\n',text,re.M);assert anchor
        at=anchor.end();indent=anchor.group(1)
        text=text[:at]+indent+'<HydroMechInitZ value="2.0" comment="Physical fully saturated soil-top water table" units_comment="m" />\n'+indent+'<PoreShepardInterval value="40" comment="Preload excess-pressure filtering every 40 completed steps" />\n'+text[at:]
        anchor=re.search(r'^([ \t]*)<parameter key="SoilDamping"[^\n]*\n',text,re.M);assert anchor
        text=text[:anchor.end()]+anchor.group(1)+'<parameter key="SoilDampingCoef" value="0.02" comment="Existing prestress damping strength" />\n'+text[anchor.end():]
        ET.fromstring(text)
        with dst.open('x',encoding='utf-8',newline='') as f:f.write(text)
        outputs.append(str(dst))
        if suffix=='.xml':shutil.copy2(dst,seed/(name+'.xml'))
    old=T/'outputs/upl_material_preload_r1_seed'/BASE
    for suffix in ('.bi4','_Normals.nbi4'):shutil.copy2(str(old)+suffix,seed/(name+suffix))
    outputs.append(str(seed))
p=T/'notes/upl_prestress_inputs_r1.json';assert not p.exists()
with p.open('x',encoding='utf-8') as f:
    json.dump(dict(stage='upl_prestress_inputs_r1',prepared_only=True,geometry_unchanged=True,
        controls=dict(HydroMechInitMode='ConstantZ',HydroMechInitZ=2,SoilDamping=1,SoilDampingCoef=.02,PoreShepardRegularization=1,PoreShepardInterval=40),
        effective_stress_initialized=False,dt_s=.0000025,check=dict(end_s=.001,steps=400,TimeOut_s=.0001),
        extended=dict(end_s=5.,steps=2000000,TimeOut_s=.01),
        new_geostatic_mode=False,solver_started=False,GenCase_invocations=0,SHA_scans=0,outputs=outputs),f,indent=2);f.write('\n')
print(json.dumps(dict(prepared=True,short_steps=400,preload_steps=2000000,solver_started=False)))
