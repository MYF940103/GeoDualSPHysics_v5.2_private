"""One explicit pure-offline native comparison; no solver, decoder, build, retries or chaining."""
import csv,json,struct,sys
from pathlib import Path
import numpy as np
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_material_release_native_r1'
SCHEMA=[('Idp','uint32',1),('Posd','float64',3),('Vel','float32',3),('Sigma_kk','float32',3),('Sigma_ij','float32',3),('FSNormal','float32',3),('HydroMechLoadAce','float32',3),('native_Rhop','float32',1),('Kplastic','float32',1),('PorePress','float32',1),('PorePress0','float32',1),('ExcessPorePress','float32',1),('SigmaState_kk','float64',3),('SigmaState_ij','float64',3),('FSType','uint32',1),('PoroVolumeRatio','float64',1),('PoroPorosity','float64',1),('PoroThetaLastStage','float64',1),('PoroCurrentVolume','float64',1),('PoroMixtureDensity','float64',1),('PoroHydraulicConductivity','float64',1),('PosDiv','float32',1)]
TYPES={'uint32':np.dtype('<u4'),'float32':np.dtype('<f4'),'float64':np.dtype('<f8')}
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text())
def table(p):
    with Path(p).open(newline='') as f:return list(csv.DictReader(f))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def write(p,rows):
    with Path(p).open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def fbits(x):return struct.pack('<d',float(x))
def bound(e):
    a=stat(e['path']);need(a==e,'Closed native artifact changed: '+e['path']);return a
def load(mode,backend,old=False):
    tag='upl_preload_handoff_source_'+backend+'_r1' if old else TAG+'_'+mode+'_'+backend
    cp=L/(tag+'_native_r1.check.json' if old else tag+'.native.check.json');r=read(cp);need(r['passed'] and r['original_native_guards_passed'] and r['consumed_stats_unchanged'],'Native receipt not passed: '+str(cp))
    files=[stat(cp),bound(r['native_completion'])]+[bound(e) for e in r['files']];d=read(r['native_completion']['path']);out=Path(r['native_completion']['path']).parent;clocks=table(out/'clocks.csv');layout=table(out/'typed22_layout.csv');need(len(clocks)==d['samples'] and len(layout)==22,'Actual native clock/layout coverage differs')
    for row,(name,kind,nc) in zip(layout,SCHEMA):need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,nc,TYPES[kind].itemsize*nc),'Original22 typed layout changed')
    if mode=='plastic' and not old:paths={0:out/'typed22.bin'}
    else:paths={int(x['phase']):out/x['filename'] for x in table(out/'phases.csv')}
    byphase={};frames={}
    for phase,p in paths.items():
        with p.open('rb') as f:
            n,arrays,count=struct.unpack('<III',f.read(12));need(arrays==22,'Original actual export header differs');v=[]
            for _ in range(count):
                rawtime=f.read(8);need(len(rawtime)==8,'Missing native time');a={}
                for name,kind,nc in SCHEMA:
                    q=np.fromfile(f,dtype=TYPES[kind],count=n*nc);need(q.size==n*nc and np.isfinite(q).all(),'Truncated/nonfinite native payload');a[name]=q.reshape(n,nc) if nc>1 else q
                need(np.array_equal(np.sort(a['Idp']),a['Idp']) and np.unique(a['Idp']).size==n,'Actual native ID order/uniqueness differs');v.append((rawtime,a))
            need(not f.read(1),'Trailing raw typed bytes');byphase[phase]=v
    cursor={p:0 for p in byphase}
    for c in clocks:
        phase=int(c.get('phase',0));i=cursor[phase];cursor[phase]+=1;rawtime,a=byphase[phase][i];need(rawtime==fbits(c['time_s']),'Original typed/CSV actual times differ');step=int(c['completed_step']);need(step not in frames,'Duplicate saved completed step');frames[step]={'clock':c,'arrays':a,'rawtime':rawtime}
    need(sum(len(v) for v in byphase.values())==len(frames)==len(clocks),'Original binary/clock records do not align')
    return dict(tag=tag,frames=frames,done=d,out=out,consumed=files)
def compare(a,b,exact,label):
    shared=sorted(set(a['frames'])&set(b['frames']));need(shared,'No actual common saved steps');rows=[];fields=[];fail=[]
    need(set(b['frames'])<=set(a['frames']) if exact else set(a['frames'])==set(b['frames']),'Actual comparison frame coverage differs')
    for step in shared:
        x,y=a['frames'][step],b['frames'][step];ca,cb=x['clock'],y['clock'];fa,fb=x['arrays'],y['arrays'];need(np.array_equal(fa['Idp'],fb['Idp']),'Native material IDs differ at actual common step')
        checks=['time_s','dt_s','signed_dterror_s'];clockexact=all(fbits(ca[k])==fbits(cb[k]) for k in checks) and all(int(ca[k])==int(cb[k]) for k in ['completed_step','saved_step','dterror_interval_empty'])
        need(fbits(ca['time_s'])==fbits(cb['time_s']),'Only exact actual saved times are paired; no interpolation')
        if exact and not clockexact:fail.append(label+':signedclock:'+str(step))
        fieldexact=True
        for name,kind,nc in SCHEMA:
            bit=fa[name].tobytes()==fb[name].tobytes();delta=fb[name].astype(float)-fa[name].astype(float);maximum=float(np.abs(delta).max());fieldexact &=bit
            fields.append(dict(comparison=label,completed_step=step,time_s=float(ca['time_s']),array=name,type=kind,components=nc,bit_equal=bit,max_abs_native_difference=maximum))
        ids=fa['Idp'];soil=ids>=2060 if mode_scope(label)=='source' else np.ones(ids.size,dtype=bool)
        dp=fb['PorePress'].astype(float)[soil]-fa['PorePress'].astype(float)[soil];du=fb['Posd'].astype(float)[soil]-fa['Posd'].astype(float)[soil]
        if mode_scope(label)=='plastic':du[:,[0,2]]-=1.28*np.round(du[:,[0,2]]/1.28)
        pRMS=float(np.sqrt(np.mean(dp*dp)));umax=float(1000*np.linalg.norm(du,axis=1).max());sigmaa=np.column_stack((fa['SigmaState_kk']-fa['PorePress'][:,None],fa['SigmaState_ij']))[soil];sigmab=np.column_stack((fb['SigmaState_kk']-fb['PorePress'][:,None],fb['SigmaState_ij']))[soil];ds=sigmab-sigmaa
        sigmaRMS=float(np.sqrt(np.mean(np.sum(ds[:,:3]**2,axis=1)+2*np.sum(ds[:,3:]**2,axis=1))))
        if exact and not fieldexact:fail.append(label+':typed22:'+str(step))
        if not exact and (pRMS>5 or umax>.005):fail.append(label+':backend_budget:'+str(step))
        rows.append(dict(comparison=label,completed_step=step,time_s=float(ca['time_s']),left_part=int(ca['part']),right_part=int(cb['part']),native_IDs=ids.size,typed22_bit_equal=fieldexact,signed_clock_exact=clockexact,pressure_RMS_difference_Pa=pRMS,material_XYZ_max_difference_mm=umax,total_stress_Frobenius_RMS_difference_Pa=sigmaRMS))
    return rows,fields,fail
def mode_scope(label):return 'plastic' if label=='cross_plastic' else 'source'
def main():
    need(len(sys.argv)==3,'Use baseline|alias|receive_old|receive_new CPU|GPU, or cross source|plastic')
    action,arg=sys.argv[1:];need((action in ('baseline','alias','receive_old','receive_new') and arg in ('CPU','GPU')) or (action=='cross' and arg in ('source','plastic')),'Bounded comparison required');label=action+'_'+arg;prefix=TAG+'_'+label;CHECK=L/(prefix+'.review.json');CSV=T/'figures'/(prefix+'_pairs.csv');FIELDS=T/'figures'/(prefix+'_fields.csv');need(not any(p.exists() for p in [CHECK,CSV,FIELDS]),'Existing/partial offline review protected')
    if action=='baseline':a,b=load('source',arg,True),load('source',arg)
    elif action=='alias':a,b=load('source',arg),load('alias0',arg)
    elif action.startswith('receive'):a,b=load('source',arg),load(action,arg)
    else:a,b=load(arg,'CPU'),load(arg,'GPU')
    rows,fields,fail=compare(a,b,action!='cross',label);byteclock=None
    if action in ('baseline','alias'):
        byteclock=(a['out']/'clocks.csv').read_bytes()==(b['out']/'clocks.csv').read_bytes()
        if not byteclock:fail.append(label+':entire_actual_clock_CSV_bytes')
    expected=11 if action.startswith('receive') else 5 if action=='cross' and arg=='plastic' else 22;need(len(rows)==expected,'Actual declared common-state count differs')
    write(CSV,rows);write(FIELDS,fields);consumed=a['consumed']+b['consumed'];need(all(stat(e['path'])==e for e in consumed),'Closed native evidence changed during offline review')
    result=dict(stage=prefix+'.review',passed=not fail,comparison=label,actual_matched_states=len(rows),typed_arrays=22,max_pressure_RMS_difference_Pa=max(x['pressure_RMS_difference_Pa'] for x in rows),max_material_XYZ_difference_mm=max(x['material_XYZ_max_difference_mm'] for x in rows),all_typed22_bits_equal=all(x['typed22_bit_equal'] for x in rows),all_actual_signed_clock_fields_exact=all(x['signed_clock_exact'] for x in rows),entire_actual_clock_CSV_bytes_equal=byteclock,exact_same_backend_gate=action!='cross',cross_backend_5Pa_005mm_gate=action=='cross',matched_receiver_is_advanced_state_not_independent_import_snapshot=action.startswith('receive'),failures=fail,consumed=consumed,outputs=[stat(CSV),stat(FIELDS)],solver_decoder_build_Git_SHA_actions=0,physical_acceptance=False)
    save(CHECK,result);print(json.dumps(result),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
