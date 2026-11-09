"""Prepare one H1.8 PRE and scalar-clock output plans; never start a program."""
import csv,json,xml.etree.ElementTree as ET
from pathlib import Path
T=Path(__file__).resolve().parents[1];C=T.parent
TAG='c08_h18_pre_r1';DT=.000005;EVENT=2000000;INTERVAL=.01

def next_output(t):
    nt=int(t/INTERVAL);value=INTERVAL*nt
    while value<=t:
        nt+=1;value=INTERVAL*nt
    return value

def save_plan(name,rows):
    p=T/'configs'/name
    with p.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return p

def main():
    config=T/'configs'/(TAG+'_Def.xml');bat=T/'configs'/('x'+TAG+'_win64_GPU.bat');profiles=T/'configs/c08_h18_profiles_r1.json'
    if any(p.exists() for p in (config,bat,profiles)):raise RuntimeError('Prepared files already exist; do not overwrite')
    template=C/'CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml';text=template.read_text(encoding='utf-8')
    replacements=[('<hdp value="1.2"','<hdp value="1.8"'),('key="SoilDampingCoef" value="0.02"','key="SoilDampingCoef" value="0.03"'),('key="DtIni" value="0.0000025"','key="DtIni" value="0.000005"'),('key="DtFixed" value="0.0000025"','key="DtFixed" value="0.000005"'),('key="TimeMax" value="13.0"','key="TimeMax" value="10.0"'),('10 s actual gravity preload plus 3 s after release; no PART restart','10 s fresh gravity preload; stop at certified PRE before release'),('Fixed 2.5 microsecond step','Fixed 5 microsecond step'),('r3 server validation candidate: unified DP v2 and bounded shared-PRE handoff checked; actual 10 s elasticity and full collapse remain unaccepted.','Fresh H1.8/Cubic strict-elastic PRE; damping coefficient0.03 retains the old coefficient/H rate; no collapse in this run.')]
    for old,new in replacements:
        if text.count(old)!=1:raise RuntimeError('Template anchor changed: '+old)
        text=text.replace(old,new,1)
    text=text.replace('Lian 2023 Section 3.1: h/dp for the cubic spline kernel','Requested h/dp sensitivity; source and receiver kernel/H must match').replace('Existing prestress damping strength','Coefficient/H preserves the prior preload damping rate').replace('Experimental dynamic u-pl; bounded compatibility checked, full13s physical review pending','Dynamic u-pl with current-J conductivity; source eligibility and equilibrium require review')
    root=ET.fromstring(text);p={q.get('key'):q.get('value') for q in root.findall('execution/parameters/parameter')}
    assert p['TimeMax']=='10.0' and p['DtFixed']=='0.000005' and p['SoilDampingCoef']=='0.03' and p.get('ArtificialStress','0')==p.get('NoPenetration','0')=='0'
    assert root.find('execution/special/gravitypreload').get('elastic_source')=='true'
    with config.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    with bat.open('x',encoding='ascii',newline='') as f:f.write('@echo off\r\nsetlocal\r\ncd /d "%~dp0..\\.."\r\nset "c08python=D:\\anaconda3\\python.exe"\r\nif not exist "%c08python%" set "c08python=python"\r\n"%c08python%" -X utf8 -B "tests\\support\\c08_h18_pre_r1.py" --execution-authorized --notify\r\nif errorlevel 1 goto fail\r\necho Fresh PRE finished. Native and equilibrium review still required.\r\npause\r\nexit /b 0\r\n:fail\r\necho Preserve outputs. Do not overwrite or restart this run.\r\npause\r\nexit /b 1\r\n')
    rows=[dict(part=0,completed_step=0,saved_step=0,time_s=0.,dt_s=DT)];scalar=0.;nxt=next_output(scalar)
    for completed in range(1,EVENT+1):
        scalar+=DT
        if scalar>=nxt or scalar>=10. or completed==EVENT:
            rows.append(dict(part=len(rows),completed_step=completed,saved_step=completed-1,time_s=scalar,dt_s=DT));nxt=next_output(scalar)
    assert len(rows)==1001 and rows[-1]['completed_step']==EVENT
    preplan=save_plan('c08_h18_pre_r1.steps.csv',rows);receiver=[]
    for duration,end in ((.9,2180000),(3.,2600000)):
        clock=scalar;nxt=next_output(clock);rr=[]
        for completed in range(EVENT+1,end+1):
            clock+=DT
            if clock>=nxt or clock>=10.+duration or completed==end:
                rr.append(dict(part=len(rr),completed_step=completed,saved_step=completed-1,time_s=clock,dt_s=DT));nxt=next_output(clock)
        path=save_plan('c08_h18_release_'+('w09' if duration==.9 else 'full3')+'_r1.steps.csv',rr)
        receiver.append(dict(duration_s=duration,end_completed_step=end,samples=len(rr),plan=str(path),first_actual_time_s=rr[0]['time_s'],actual_end_s=rr[-1]['time_s']))
    data=dict(schema=1,source_job=TAG,kernel='Cubic',kernel_id=1,hdp=1.8,Dp=.04,H_nominal_m=.072,fixed_dt_s=DT,preload_time_s=10.,preload_completed_step=EVENT,preload_samples=len(rows),preload_plan=str(preplan),preload_actual_end_s=scalar,preload_damping_coefficient=.03,release_damping=False,release_Shepard=False,residual_viscosity=False,AS_coefficients_first=[.3,.5,.7],AS_exponent_first=3.825,AS_exponents_followup=[3.,5.],maximum_followup_combinations=2,receiver=receiver,groups=[dict(name='psi0',dilation_deg=0.,cohesion_Pa=5000.,decay=0.),dict(name='psi2p5',dilation_deg=2.5,cohesion_Pa=5000.,decay=.2),dict(name='psim5',dilation_deg=-5.,cohesion_Pa=7500.,decay=.2)],selection_requires_physical_review=True,source_guards_unchanged=True,new_half_runs_planned=False,formal_inputs_written=False)
    with profiles.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2);f.write('\n')
    print(json.dumps(data,indent=2))

if __name__=='__main__':main()
