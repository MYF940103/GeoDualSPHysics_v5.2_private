"""Read raw public CPU/GPU PARTs at actual clocks, check the high-k column and compare accepted cost."""
import argparse
import csv
import json
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from c02_tpi_cost_r1 import CASE, CV, EVENT, MC, PLAN, PREFIX, TESTS, directory, need, planned_clock, setup_xml
sys.path.insert(0,str(CASE.parent/'04_CryerProblem_PR/tests/support'))
from cryer_live_history_review import CHILD, _Cursor, read_item

SOIL = np.arange(40,1040)
LAMBDA = (np.arange(512)+.5)*np.pi
COEFF = 2*(-1.)**np.arange(512)/LAMBDA
N0 = float(np.float32(.3))
K0 = float(np.float32(PLAN['hydraulic_conductivity_m_s']))
FIELDS = set('Idp Posd Vel Rhop Sigma_kk Sigma_ij Kplastic SigmaState_kk SigmaState_ij FSType FSNormal PoroVolumeRatio PoroPorosity PoroThetaLastStage PosDiv PoroCurrentVolume PoroMixtureDensity PoroHydraulicConductivity PorePress PorePress0 ExcessPorePress HydroMechLoadAce'.split())
DOUBLE_FIELDS = set('Posd SigmaState_kk SigmaState_ij PoroVolumeRatio PoroPorosity PoroThetaLastStage PoroCurrentVolume PoroMixtureDensity PoroHydraulicConductivity'.split())
VEC3 = set('Posd Vel Sigma_kk Sigma_ij SigmaState_kk SigmaState_ij FSNormal HydroMechLoadAce'.split())


def write_report(path,report):
    def native_scalar(value):
        if isinstance(value,np.generic):
            return value.item()
        raise TypeError('Unexpected non-scalar report value: '+type(value).__name__)
    # Serialize and reject any nonfinite/unexpected value before creating the public receipt.
    encoded=json.dumps(report,indent=2,allow_nan=False,default=native_scalar)+'\n'
    with path.open('x',encoding='utf8') as f:
        f.write(encoded)


def theory(t,z,model):
    # Original one-dimensional surface-drained solution at initial material centres.
    capacity=1/(1+.3*MC/2e8) if model==1 else 1.
    weights=COEFF*np.exp(-LAMBDA**2*CV*capacity*(t-EVENT))
    pp=capacity*1e4*(weights@np.cos(LAMBDA[:,None]*z))
    settlement=1e7/MC*(z-capacity*((weights/LAMBDA)@np.sin(LAMBDA[:,None]*z)))
    return pp,settlement


def check_hg(text,n):
    first=re.search(r'forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)',text)
    second=re.search(r'ratecalculations=(\d+) endpoint_rate_reuses=(\d+)',text)
    limits=re.search(r'max\|sum\(M0\*Href\)\|=(\S+) max\|sum\(mi\*deltaAce\)\|=(\S+) max\(dt/tau\)=(\S+) spinbound=(\S+)',text)
    need(first and second and limits,'Missing physical HG summary')
    need(tuple(map(int,first.groups()))==(2*n,n,n,2*n) and tuple(map(int,second.groups()))==(n+1,n-1),'HG phase or reuse count')
    v=list(map(float,limits.groups()))
    need(np.isfinite(v).all() and min(v)>=0 and v[2]<=.2 and v[3]<.01,'HG safety')
    return v


def read_native(path,part,model,factor):
    raw=path.read_bytes()
    need(raw[:58].rstrip(b' ')==b'#FileJBD JPartDataBi4' and raw[58:64]==b'\n\0\0\0\0\0','BI4 identity')
    cursor=_Cursor(raw,64)
    history_expected=model==2 and part>0
    root=read_item(cursor,0,history_expected)
    cursor.finish('complete PART')
    node,=root['children']
    need(root['name']=='JPartDataBi4' and node['name']==path.stem.upper(),'PART identity')
    m=node['values'];types=node['types'];head=root['values']
    need(head['CaseNp']==m['Npok']==1040 and head['CaseNfixed']==40 and head['CaseNfluid']==1000,'Column extent')
    check_model_header(m,types,model,factor)
    history=node['children'][0] if history_expected else None
    if history is not None:
        need(history['name']==CHILD and history['values']['Scheme']=='P3_B_alpha_half_beta_zero' and history['values']['Schema']==1
             and history['values']['RunCode']==head['RunCode'],'Actual pressure iteration scheme and run identity')
    return head,m,node['arrays'],history


def check_model_header(m,types,model,factor):
    need(m['HydroMechDynamicSeepage']==1 and m['DynamicSeepageSchema']==1 and m['HydroMechConductivityModel']==0,'Dynamic constant-k branch')
    # The compatible explicit finite-Kw format predates the optional TPI model tag.
    need(m.get('HydroMechModel',1)==model,'Model tag')
    need(('HydroMechTpiR' in types)==(model==2 and factor!=1.),'Native hydraulic multiplier presence')
    if 'HydroMechTpiR' in types:
        need(types['HydroMechTpiR']==12 and m['HydroMechTpiR']==factor,'Native double hydraulic multiplier')


def one(lane,backend,frame_sink=None,last_part=None):
    cfg=PLAN['lanes'][lane]
    model=cfg['model'];dt=cfg['dt_s']
    out=directory(lane,backend)
    res=out/'result'
    start=json.loads((out/'start.json').read_text())
    ex=json.loads((out/'exit.json').read_text())
    plan=planned_clock(lane)
    if last_part is not None:
        need(0<last_part<len(plan),'Review cap must be an original planned save')
        plan=plan[:last_part+1]
    args=[ex['program']]+(['-gpu'] if backend=='gpu' else ['-cpu','-ompthreads:1'])
    seed=out/'seed'/PLAN['seed_name']
    args+=['-stable','-mdbc_freeslip',str(seed),str(res),'-dirdataout','data','-svres','-nsteps:'+str(plan[-1][0])]
    need(ex['lane']==lane and ex['backend']==backend and ex['argv']==args and ex['exit']==0 and ex['program_unchanged']
         and ex['host'] and all(ex[k]==v for k,v in start.items()),'Actual solver exit, program or run identity')
    root,_,_=setup_xml(lane)
    need(seed.with_suffix('.xml').read_bytes()==ET.tostring(root.getroot(),encoding='utf-8',xml_declaration=True),'Bound launched XML')
    with (res/'Run.csv').open(encoding='utf-8-sig',errors='replace',newline='') as f:
        rr,=csv.DictReader(f,delimiter=';')
    text=(res/'Run.out').read_text(encoding='utf8',errors='replace')
    driver=re.search(r'^\s*CUDA Driver Version / Runtime Version:\s*([^\r\n]+)',text,re.M) if backend=='gpu' else None
    need(backend!='gpu' or driver,'Missing CUDA driver/runtime identity')
    need(int(rr['Steps'])==plan[-1][0] and int(rr['PartsOut'])==0 and 'Finished execution (code=0)' in text,'Run summary')
    modes=re.findall(r'^\s*HydroMechModel=(\d+)\s*\(',text,re.M)
    vals=re.findall(r'^\s*HydroMechTpiR=(\S+)\s*$',text,re.M)
    need(modes and all(int(v)==model for v in modes),'Actual hydromechanical model')
    need((bool(vals)==(model==2)) and all(float(v)==cfg.get('R',1.) for v in vals),'Actual public TPI hydraulic multiplier')
    hg=check_hg(text,plan[-1][0])
    paths=sorted((res/'data').glob('Part_*.bi4'))
    need(len(paths)==len(plan)==int(rr['PartFiles']),'Native output schedule')
    rows=[];max_layer=max_gap=0.
    ids=np.arange(1040)
    for part,(file,(step,t,target)) in enumerate(zip(paths,plan)):
        head,m,a,hist=read_native(file,part,model,cfg.get('R',1.))
        need(set(a)==FIELDS and m['Step']==max(0,step-1) and m['TimeStep']==t and m['Cpart']==part and m['Nout']==0,'Original native fields, IDs or clock')
        ix=np.argsort(a['Idp']);need(np.array_equal(a['Idp'][ix],ids),'Original column material IDs')
        for field,values in a.items():
            kind='uint32' if field in ('Idp','FSType') else ('float64' if field in DOUBLE_FIELDS else 'float32')
            shape=(1040,3) if field in VEC3 else (1040,)
            need(values.dtype.name==kind and values.shape==shape,'Native type or length '+field)
        a={k:v[ix] for k,v in a.items()}
        need(all(np.isfinite(v).all() for v in a.values()),'Finite native record')
        if part:
            need(m['dtmin']==m['dtmax']==m['SymplecticDtPre']==dt and -sys.float_info.max<m['dterror']<=1e-14,'Signed timestep')
            if model==2:
                h=hist['values'];need(h['Valid'] and h['CompletedUpdates']==step and h['SavedTime']==t and h['Dt']==dt and h['PreviousTime']+dt==t and np.array_equal(hist['arrays']['Idp'],SOIL),'TPI history')
            else:
                need(hist is None,'Explicit model acquired a TPI history')
        else:
            need(m['dterror']==m['dtmin']==m['dtmax']==0 and m['SymplecticDtPre']==dt,'Initial interval and requested dt')
        x=a['Posd']
        if part==0:
            x0=x.copy()
            xyz=x0[40:]
            layers=np.rint(xyz[:,2]/.01-.5).astype(int)
            need(np.all(np.bincount(layers,minlength=100)==10),'100 original material layers')
            zs=np.bincount(layers,xyz[:,2])/10
        need(np.array_equal(x[:40],x0[:40]) and not np.any(a['Vel'][:40]) and not np.any(x[40:,1]) and min(x[40:,2])>0,'Fixed markers, planar geometry or bottom crossing')
        need(not np.any(a['Kplastic']) and not np.any(a['PorePress0']) and np.array_equal(a['PorePress'],a['ExcessPorePress']) and max(a['FSType'])<=4,'Elastic, pore reference or free surface')
        need(np.all((a['Rhop']>=700)&(a['Rhop']<=3000)) and np.all(a['Rhop'][:40]==2100) and not np.any(a['PoroThetaLastStage'][:40]),'Density or fixed markers')
        for block in ('kk','ij'):
            need(np.array_equal(a['SigmaState_'+block].astype(np.float32),a['Sigma_'+block]),'Double stress writeback')
        j=a['PoroVolumeRatio'][40:];n=a['PoroPorosity'][40:];v=a['PoroCurrentVolume'][40:];rho=a['PoroMixtureDensity'][40:]
        need(np.all(a['PoroVolumeRatio']>1-N0) and np.all((n>0)&(n<1)) and np.all(np.abs((1-n)*j-(1-N0))<=5e-13),'Single J porosity')
        for key,ref in [('PoroPorosity',1-(1-N0)/j),('PoroCurrentVolume',head['MassFluid']/2100*j),('PoroMixtureDensity',1000+1100/j),('PoroHydraulicConductivity',K0)]:
            need(not np.any(a[key][:40]) and np.allclose(a[key][40:],ref,rtol=5e-13,atol=0),'Soil ledger '+key)
        # Restored pressure and current-state hydraulic bound remain independent of the skeleton CFL.
        hyd=head['H']**2*np.min(n)*9806.65/(2e8*K0)*cfg.get('R',1.)
        need(dt<=hyd+1e-14,'Hydraulic step at saved state')
        mask=np.isin(a['FSType'][40:],(2,3));p=a['PorePress'][40:]
        need(np.array_equal(mask,layers==99),'Ten actual drained-receiver identities')
        event_step=round(EVENT/dt)
        if step==event_step:
            need(np.max(np.abs(p[mask]))>0,'Drained early at event')
            preopen=p.copy()
        if step>event_step:
            need(np.all(p[mask]==0),'Post-open pressure')
            if model==2 and step==event_step+1:
                prev=hist['arrays']['PorePressPrev']
                need(np.all(prev[mask]==0) and np.array_equal(prev[~mask],preopen[~mask]),'First post-open pressure history')
            force=np.sum((rho*v)[:,None]*a['HydroMechLoadAce'][40:],axis=0)
            need(np.max(np.abs(force-[0,0,-1000]))<=.001,'Post-ramp resultant')
        pp=np.bincount(layers,p)/10
        s=np.bincount(layers,1000*(x0[40:,2]-x[40:,2]))/10
        zz=np.bincount(layers,a['SigmaState_kk'][40:,2]-p)/10
        error=abs(zz+10000).max();gap=abs(zz[-1]-zz[-2])
        if t>=.1:
            max_layer=max(max_layer,error);max_gap=max(max_gap,gap)
        row=dict(part=part,completed=step,t_s=t,target_time_s=target,actual_Tv=CV*(t-EVENT),pressure_RMS_Pa=None,top_error_mm=None,bottom_error_mm=None,
                 load_stress_layer_error_Pa=float(error),topgap_Pa=float(gap),signed_dterror_s=m['dterror'],saved_hydraulic_bound_s=float(hyd))
        if part>=3:
            pref,sref=theory(t,zs,model)
            row.update(pressure_RMS_Pa=float(np.sqrt(np.mean((pp-pref)**2))),top_error_mm=float(s[-1]-sref[-1]),bottom_error_mm=float(s[0]-sref[0]))
        rows.append(row)
        if frame_sink is not None:
            frame_sink(part,m,a,hist)
    sizes=sum(p.stat().st_size for p in (res/'data').iterdir() if p.is_file())
    need(all(np.isfinite(q) and q>0 for q in (ex['wall_seconds'],float(rr['TSimul']),float(rr['TTotal']))),'Reported complete run timing')
    return dict(lane=lane,model=model,backend=backend,host=ex['host'],hardware=rr['Hardware'],cuda_driver_runtime=driver.group(1).strip() if driver else None,
                program_identity={key:ex[key] for key in ('program','size','mtime_ns')},steps=plan[-1][0],wall_s=ex['wall_seconds'],loop_s=float(rr['TSimul']),
                total_s=float(rr['TTotal']),io_bytes=sizes,save_timer_s=None if not rr.get('SU-SavePart') else float(rr['SU-SavePart']),
                hg_limits=hg,early_100Pa_stress_pass=(bool(max_layer<=100 and max_gap<=100) if plan[-1][1]>=.1 else None),
                post01_max_layer_Pa=(float(max_layer) if plan[-1][1]>=.1 else None),
                post01_max_topgap_Pa=(float(max_gap) if plan[-1][1]>=.1 else None),rows=rows)


def target_rows(a,b,indices):
    results=[]
    for index in indices:
        x,y=a['rows'][index],b['rows'][index]
        results.append(dict(target_Tv=(index-2)*PLAN['save_delta_Tv'],time_difference_s=y['t_s']-x['t_s'],
                            pressure_ok=y['pressure_RMS_Pa']<=x['pressure_RMS_Pa']+10,
                            top_ok=abs(y['top_error_mm'])<=abs(x['top_error_mm'])+.001*1e7/MC,
                            bottom_ok=abs(x['bottom_error_mm'])<=.005 and abs(y['bottom_error_mm'])<=min(.005,abs(x['bottom_error_mm'])+.002)))
    return results


def target_budgets(a,b):
    # The two predeclared targets included in the full cost window are .005 and .05.
    results=target_rows(a,b,(3,12))
    passed=a['early_100Pa_stress_pass'] and b['early_100Pa_stress_pass'] and all(v['pressure_ok'] and v['top_ok'] and v['bottom_ok'] for v in results)
    return dict(reference=a['lane'],candidate=b['lane'],passed=passed,targets=results)


def compare(reference,candidate,anchor):
    a,b=reference,candidate
    need(a['model']==anchor['model']==1 and anchor['lane']=='kw25' and a['lane']!=b['lane'],'Distinct candidate and explicit reference with kw25 anchor')
    need(all(a[k]==b[k]==anchor[k] for k in ('backend','host','hardware','cuda_driver_runtime','program_identity')),'Require same host, backend, device, driver and program')
    direct=target_budgets(a,b)
    candidate_anchor=direct if a['lane']=='kw25' else target_budgets(anchor,b)
    ref_anchor=None if a['lane']=='kw25' else target_budgets(anchor,a)
    passed=direct['passed'] and candidate_anchor['passed'] and (ref_anchor is None or ref_anchor['passed'])
    return dict(explicit_reference=a['lane'],candidate=b['lane'],predeclared_target_noninferiority_pass=passed,
                actual_scope='Tv=.005 and .05, with model-specific analytical pressure and settlement and saved stress guards',
                relative_to_reference=direct,reference_against_kw25=ref_anchor,candidate_against_kw25=candidate_anchor,
                observed_loop_ratio_ref_over_candidate=a['loop_s']/b['loop_s'],observed_wall_ratio_ref_over_candidate=a['wall_s']/b['wall_s'])


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('backend',choices=['cpu','gpu']);ap.add_argument('lane',choices=PLAN['lanes'])
    ap.add_argument('--reference',choices=['kw25','kw40'])
    args=ap.parse_args()
    report=one(args.lane,args.backend)
    if args.reference:
        reference=one(args.reference,args.backend)
        anchor=reference if args.reference=='kw25' else one('kw25',args.backend)
        report['comparison']=compare(reference,report,anchor)
    dest=TESTS/'logs'/(PREFIX+'_'+args.lane+'_'+args.backend+('_vs_'+args.reference if args.reference else '')+'.json')
    write_report(dest,report)
