"""Strict same-configuration offline comparison, all native typed fields plus signed clocks; no decoder/solver."""
import csv,json,struct,sys
from pathlib import Path
import numpy as np
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='mdbc_admission_r2'
SCHEMA=[('Idp','uint32',1),('Posd','float64',3),('Vel','float32',3),('Sigma_kk','float32',3),('Sigma_ij','float32',3),('FSNormal','float32',3),('HydroMechLoadAce','float32',3),('native_Rhop','float32',1),('Kplastic','float32',1),('PorePress','float32',1),('PorePress0','float32',1),('ExcessPorePress','float32',1),('SigmaState_kk','float64',3),('SigmaState_ij','float64',3),('FSType','uint32',1),('PoroVolumeRatio','float64',1),('PoroPorosity','float64',1),('PoroThetaLastStage','float64',1),('PoroCurrentVolume','float64',1),('PoroMixtureDensity','float64',1),('PoroHydraulicConductivity','float64',1),('PosDiv','float32',1)]
TYPES={'uint32':np.dtype('<u4'),'float32':np.dtype('<f4'),'float64':np.dtype('<f8')}
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def table(p):
    with Path(p).open(encoding='utf-8-sig',newline='')as f:return list(csv.DictReader(f))
def clockbits(r,n):return struct.pack('<dIIddII',float(r['time_s']),int(r['completed_step']),int(r['saved_step']),float(r['dt_s']),float(r['signed_dterror_s']),int(r['dterror_interval_empty']),n)
def main(profile,backend):
    need(profile in('source','periodic','cryer_static','cryer_dynamic')and backend in('CPU','GPU'),'Declared offline pair required');tag=TAG+'_'+profile+'_'+backend;cp=L/(tag+'.check.json');fp=T/'figures'/(tag+'_fields.csv');need(not cp.exists()and not fp.exists(),'Existing review protected');consumed={};result=dict(stage=tag,passed=False,physical_acceptance=False,solver_or_reader_invoked=False,SHA_scans=0)
    def bound(e):
        a=stat(e['path']);need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Consumed binding changed: '+e['path']);consumed[a['path']]=a;return a
    def loadnew(variant):
        q=L/(tag+'_'+variant+'.native.check.json');d=read(q);bound(stat(q));need(d['passed']and d['actual_exit']==d['actual_Win32_exit']==0 and d['original_native_guards_passed']and d['consumed_stats_unchanged'],'Selected native control not passed')
        for e in d['files']:bound(e)
        run=read(d['source_run']['path']);bound(d['source_run']);need(run['passed']and run['consumed_stats_unchanged'],'Actual solver owner did not pass');bound(run['program']);bound(run['source_build']);bound(run['config'])
        out=Path(d['native_completion']['path']).parent;raw=(out/'typed.bin').read_bytes();clocks=table(out/'clocks.csv');frames=[{}for _ in clocks]
        for r in table(out/'layout.csv'):
            part=int(r['part']);n=int(r['count']);offset=int(r['offset']);size=int(r['bytes']);name=r['array'];need(name not in frames[part]and offset+size<=len(raw),'Invalid typed export layout');frames[part][name]=raw[offset:offset+size]
        return frames,clocks,run,d
    rows=[]
    try:
        new,clocks,nrun,nd=loadnew('new');nschema=SCHEMA[:15]if profile=='cryer_static'else SCHEMA
        if profile in('source','periodic'):
            plan=read(T/'notes/mdbc_admission_r1.json');oldtag=plan[profile+'_control'][backend];q=L/(oldtag+'.native.check.json');d=read(q);bound(stat(q));need(d['passed']and d['original_native_guards_passed']and d['consumed_stats_unchanged'],'Retained baseline original native gate did not pass')
            for e in d['files']:bound(e)
            run=read(d['source_run']['path']);bound(d['source_run']);bound(run['program']);bound(run['source_build']);out=Path(d['native_completion']['path']).parent;oldclocks=table(out/'clocks.csv');old=[{}for _ in oldclocks]
            phases=table(out/'phases.csv')if profile=='source'else[dict(phase='0',filename='typed22.bin',actual_native_IDs='1024',actual_saved_frames='5')]
            for phase in phases:
                raw=(out/phase['filename']).read_bytes();n,fields,frames=struct.unpack_from('<III',raw);need(n==int(phase['actual_native_IDs'])and fields==22 and frames==int(phase['actual_saved_frames']),'Retained native raw header differs');offset=12
                indices=[i for i,r in enumerate(oldclocks)if int(r.get('phase','0'))==int(phase['phase'])];need(len(indices)==frames,'Retained phase-clock count differs')
                for i in indices:
                    need(raw[offset:offset+8]==struct.pack('<d',float(oldclocks[i]['time_s'])),'Retained actual raw time differs');offset+=8
                    for name,dtype,comp in SCHEMA:
                        size=n*TYPES[dtype].itemsize*comp;old[i][name]=raw[offset:offset+size];offset+=size
                    oldclocks[i]['native_IDs']=str(n)
                need(offset==len(raw),'Retained native typed payload has extra/missing bytes')
            oldrun=run
        else:old,oldclocks,oldrun,od=loadnew('old')
        need(nrun['configuration']==oldrun.get('configuration', 'Release'if backend=='GPU'and profile=='source'else'DebugCPU'if backend=='CPU'else'Debug'),'Compiler configuration differs; no strict cross-configuration claim')
        need(len(new)==len(old)==len(clocks)==len(oldclocks),'Actual pair sample counts differ');allbits=True;allclock=True;maxP=0.;maxU=0.;allIDs=True
        for part,(a,b,ca,cb)in enumerate(zip(new,old,clocks,oldclocks)):
            n=int(ca['native_IDs']);need(set(a)==set(b)=={s[0]for s in nschema},'Actual typed array membership differs');sameclock=clockbits(ca,n)==clockbits(cb,int(cb['native_IDs']));allclock=allclock and sameclock
            ids=np.frombuffer(a['Idp'],dtype='<u4');need(len(ids)==n and len(b['Idp'])==4*n,'Actual paired ID lengths differ');allIDs=allIDs and a['Idp']==b['Idp']
            for name,dtype,comp in nschema:
                aa=np.frombuffer(a[name],dtype=TYPES[dtype]).reshape(n,comp);bb=np.frombuffer(b[name],dtype=TYPES[dtype]).reshape(n,comp);bits=a[name]==b[name];allbits=allbits and bits;changes=np.any(aa.view(np.uint8).reshape(n,-1)!=bb.view(np.uint8).reshape(n,-1),axis=1);diff=np.abs(aa.astype(np.float64)-bb.astype(np.float64));mx=float(np.max(diff));rows.append(dict(part=part,time_s=ca['time_s'],array=name,native_IDs=n,bit_equal=bits,changed_IDs=int(np.count_nonzero(changes)),first_changed_ID=int(ids[np.flatnonzero(changes)[0]])if np.any(changes)else'',max_abs_numeric_difference=mx,clock_bits_equal=sameclock))
            soil=ids>=(2060 if profile=='source'else 0 if profile=='periodic'else 8);p=(np.frombuffer(a['PorePress'],dtype='<f4').astype(np.float64)-np.frombuffer(b['PorePress'],dtype='<f4').astype(np.float64))[soil];maxP=max(maxP,float(np.sqrt(np.mean(p*p))));u=(np.frombuffer(a['Posd'],dtype='<f8').reshape(n,3)-np.frombuffer(b['Posd'],dtype='<f8').reshape(n,3))[soil];maxU=max(maxU,float(np.max(np.abs(u))*1000.))
        with fp.open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        result.update(passed=bool(allbits and allclock and allIDs),all_native_typed_fields_bit_equal=bool(allbits),all_actual_clocks_and_signed_intervals_bit_equal=bool(allclock),all_native_IDs_equal=bool(allIDs),samples=len(new),arrays_per_sample=len(nschema),array_pair_checks=len(rows),max_pressure_RMS_Pa=maxP,max_XYZ_position_difference_mm=maxU,original_5Pa_005mm_budget_satisfied=maxP<=5 and maxU<=.005,strict_bit_gate_not_replaced_by_numerical_budget=True,fields_CSV=stat(fp),old_program=oldrun['program'],new_program=nrun['program'],new_native_completion=nd['native_completion'],implementation_continuity=bool(allbits and allclock and allIDs),full_cycle_or_half_step_or_theory_acceptance=False)
        if not result['passed']:result['first_failure']='Strict same-configuration native typed or signed-clock equality failed; all differences retained'
    except Exception as e:result['first_failure']=str(e)
    result['consumed_stats_unchanged']=bool(consumed)and all(stat(e['path'])==e for e in consumed.values());result['passed']=bool(result['passed']and result['consumed_stats_unchanged']);result['consumed']=list(consumed.values())
    with cp.open('x',encoding='utf-8')as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(check=str(cp),passed=result['passed'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed']else 1
if __name__=='__main__':
    need(len(sys.argv)==4 and sys.argv[3]=='--execution-authorized','Use PROFILE CPU|GPU --execution-authorized; pure offline only');raise SystemExit(main(*sys.argv[1:3]))
