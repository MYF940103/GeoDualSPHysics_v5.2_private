"""Pure offline branch/post-source strict native comparison. No solver, decoder, new reference or package."""
import csv,json,struct,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from mdbc_admission_review_r2 import T,L,SCHEMA,TYPES,need,read,stat,table,clockbits
TAG='upl_c08_branches_r1'
def main(group):
    need(group in('psi2p5','psim5'),'Only two prepared receiver groups');tag=TAG+'_'+group+'_GPU';cp=L/(tag+'.review.json');fp=T/'figures'/(tag+'_fields.csv');need(not cp.exists()and not fp.exists(),'Existing review protected');consumed={};result=dict(stage=tag,passed=False,solver_or_decoder_invoked=False,physical_acceptance=False,SHA_scans=0)
    def bound(e):
        a=stat(e['path']);need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Consumed stat changed: '+e['path']);consumed[a['path']]=a;return a
    try:
        plan=read(T/'notes/upl_c08_branches_r1.json');src=read(plan['source_native_check']);bound(stat(plan['source_native_check']));need(src['passed']and src['qualified_elastic_PRE_verified']and src['original_native_guards_passed']and src['consumed_stats_unchanged']and src['actual_completion']['source_material_law_version']==2,'Certified Version2 ReleaseGPU source not passed')
        for e in src['files']:bound(e)
        sn=Path(src['native_completion']['path']).parent;sourceclocks=[r for r in table(sn/'clocks.csv')if int(r['phase'])==1];raw=(sn/'phase1_typed22.bin').read_bytes();n,fields,samples=struct.unpack_from('<III',raw);need((n,fields,samples)==(6800,22,11)and len(sourceclocks)==11,'Actual source post-state membership differs');old=[];offset=12
        for r in sourceclocks:
            need(raw[offset:offset+8]==struct.pack('<d',float(r['time_s'])),'Source typed time differs');offset+=8;a={}
            for name,dtype,comp in SCHEMA:
                size=n*TYPES[dtype].itemsize*comp;a[name]=raw[offset:offset+size];offset+=size
            old.append(a);r['native_IDs']=str(n)
        need(offset==len(raw),'Source post payload bytes incomplete')
        npth=L/(tag+'.native.check.json');d=read(npth);bound(stat(npth));need(d['passed']and d['actual_exit']==d['actual_Win32_exit']==0 and d['original_native_guards_passed']and d['consumed_stats_unchanged'],'New receiver native gate did not pass')
        for e in d['files']:bound(e)
        run=read(d['source_run']['path']);bound(d['source_run']);need(run['passed']and run['actual_exit']==run['actual_Win32_exit']==0 and run['configuration']=='Release'and run['new_updates_from_completed_counters']==420,'Actual matching ReleaseGPU receiver not passed');bound(run['program']);bound(run['source_build']);bound(run['config']);bound(run['source_pre_file']);need(Path(run['source_pre_file']['path']).samefile(plan['PRE']),'Receiver imported another actual PRE')
        newdir=Path(d['native_completion']['path']).parent;newraw=(newdir/'typed.bin').read_bytes();clocks=table(newdir/'clocks.csv');new=[{}for _ in clocks]
        for r in table(newdir/'layout.csv'):
            i=int(r['part']);a=int(r['offset']);size=int(r['bytes']);need(int(r['count'])==6800 and a+size<=len(newraw),'Receiver typed layout differs');new[i][r['array']]=newraw[a:a+size]
        need(len(new)==len(old)==len(clocks)==11,'Actual shared post sample count differs');allbits=allclock=allIDs=True;rows=[];maxP=maxU=maxK=0.;nonzero=set()
        for part,(a,b,ca,cb)in enumerate(zip(new,old,clocks,sourceclocks)):
            need(set(a)==set(b)=={s[0]for s in SCHEMA},'Actual22 array membership differs');sameclock=clockbits(ca,6800)==clockbits(cb,6800);allclock=allclock and sameclock;ids=np.frombuffer(a['Idp'],dtype='<u4');need(len(ids)==6800,'Receiver ID length differs');allIDs=allIDs and a['Idp']==b['Idp'];soil=ids>=2060
            for name,dtype,comp in SCHEMA:
                aa=np.frombuffer(a[name],dtype=TYPES[dtype]).reshape(6800,comp);bb=np.frombuffer(b[name],dtype=TYPES[dtype]).reshape(6800,comp);bits=a[name]==b[name];allbits=allbits and bits;changed=np.any(aa.view(np.uint8).reshape(6800,-1)!=bb.view(np.uint8).reshape(6800,-1),axis=1);rows.append(dict(receiver_part=part,source_part=cb['part'],actual_time_s=ca['time_s'],array=name,bit_equal=bits,changed_native_IDs=int(np.count_nonzero(changed)),first_changed_ID=int(ids[np.flatnonzero(changed)[0]])if np.any(changed)else'',max_abs_numeric_difference=float(np.max(np.abs(aa.astype(np.float64)-bb.astype(np.float64)))),signed_clock_bits_equal=sameclock))
            p=(np.frombuffer(a['PorePress'],dtype='<f4').astype(np.float64)-np.frombuffer(b['PorePress'],dtype='<f4').astype(np.float64))[soil];u=(np.frombuffer(a['Posd'],dtype='<f8').reshape(6800,3)-np.frombuffer(b['Posd'],dtype='<f8').reshape(6800,3))[soil];maxP=max(maxP,float(np.sqrt(np.mean(p*p))));maxU=max(maxU,float(np.max(np.abs(u))*1000.));k=np.frombuffer(a['Kplastic'],dtype='<f4');maxK=max(maxK,float(np.max(k[soil])));nonzero.update(int(i)for i in ids[soil&(k>0)])
        with fp.open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        result.update(passed=bool(allbits and allclock and allIDs),samples=11,typed_arrays=22,all22_native_fields_bit_equal=bool(allbits),all_actual_clocks_and_signed_intervals_bit_equal=bool(allclock),native_IDs_equal=bool(allIDs),max_pressure_RMS_difference_Pa=maxP,max_material_XYZ_difference_mm=maxU,original5Pa_005mm_budget_satisfied=maxP<=5 and maxU<=.005,strict_gate_not_replaced_by_budget=True,material_parameters=run['material_parameters'],new_updates=420,global_completed_steps=800,max_saved_kappa=maxK,saved_nonzero_kappa_material_IDs=len(nonzero),nonzero_plastic_psiDecay_verified=False,PRE_import_before_advance_independently_observed=False,matched_states_are_advanced_receiver_states=True,fields_CSV=stat(fp),source_PRE=run['source_pre_file'],source_native_check=stat(plan['source_native_check']),receiver_native_check=stat(npth),scope='New ReleaseGPU Version2 elastic-PRE material-branch implementation continuity only; no10s source/fullcollapse/paper acceptance')
        if not result['passed']:result['first_failure']='Strict22 native fields or signed-clock comparison failed; evidence retained'
    except Exception as e:result['first_failure']=str(e)
    result['consumed_stats_unchanged']=bool(consumed)and all(stat(e['path'])==e for e in consumed.values());result['passed']=bool(result['passed']and result['consumed_stats_unchanged']);result['consumed']=list(consumed.values())
    with cp.open('x',encoding='utf-8')as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(passed=result['passed'],review=str(cp),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed']else 1
if __name__=='__main__':
    need(len(sys.argv)==3 and sys.argv[2]=='--execution-authorized','Use psi2p5|psim5 --execution-authorized; offline only');raise SystemExit(main(sys.argv[1]))
