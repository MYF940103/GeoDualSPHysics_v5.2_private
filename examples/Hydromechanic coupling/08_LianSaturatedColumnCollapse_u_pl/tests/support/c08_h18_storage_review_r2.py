"""Offline one-pass storage-sidecar review; no reader, solver, build, hash or plot invocation."""
import argparse,csv,json,math,struct,sys,xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_compare_r2 as core

T,L=core.T,core.T/'logs'
np,need,read,stat,bind=core.np,core.need,core.read,core.stat,core.bind
TAG='c08_h18_storage_review_r2';NOTE=T/'notes'/(TAG+'.md')
BASE=2000000;IDS=5000;KW=1e9
PROFILES={'debug2':(2,2000002,'Debug'),'short3':(3,2004001,'Release'),'window':(91,2180000,'Release')}
HEADER=('native_id,inits,rhs_h,updates,cap_calls,cap_changes,release_cap_calls,release_cap_changes,errors,last_completed_step,actual_saved_time_s,initial_S,last_S,sum_dt_s,weighted_pressure_delta,compression,Darcy_remainder_including_rate_quantization,source_split_roundoff,pressure_commit_roundoff,weight_change,cap_change,sum_abs_increments,local_budget_sum,rate_quantization_bound_only,endpoint_residual,endpoint_arithmetic_budget').split(',')
INTS=HEADER[:10]
TERMS=['compression','Darcy_remainder_including_rate_quantization','source_split_roundoff','pressure_commit_roundoff','weight_change','cap_change']
CLOCK_HEADER='part,file,time_s,tau_from_actual_release_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,native_IDs,phase'.split(',')
SOURCE_CLOCK_HEADER='part,file,time_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,native_IDs,phase,completed_step_divisible_Shepard40'.split(',')

def bits(x):return struct.pack('<d',float(x))
def gamma(n):
    t=float(n)*sys.float_info.epsilon*.5;need(0<=t<1,'Invalid preregistered arithmetic count');return t/(1-t)
def same(a,b):return Path(a).resolve()==Path(b).resolve()
def entry(q,*keys):
    found=[q[k] for k in keys if k in q];need(found and all(x==found[0] for x in found),'One unambiguous entry required: '+str(keys));return bind(found[0])
def owned(q):
    need(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0,'Original actual call did not complete normally')
    need(not q.get('ownership_failure') and not q.get('ownership_errors'),'Original actual call ownership failed')
    for key in ('actual_solver_Win32_exit','actual_target_Win32_exit'):
        if key in q and q[key] is not None:need(q[key]==0,'Actual target exit differs')
def table(path):
    with Path(path).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def typed(root,nodes,count,consumed):
    """Reuse the existing typed22 schema, dtype recipe and read22 primitive, without analyze_case."""
    root=Path(root);layout=table(root/'typed22_layout.csv');need(len(layout)==22,'All22 exported arrays required');fields=[('time','<f8')]
    for row,(name,kind,width) in zip(layout,core.SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,core.TYPES[kind].itemsize*width),'Original typed22 layout differs')
        fields.append((name,core.TYPES[kind],(nodes,width)))
    dtype=np.dtype(fields,align=False);raw=root/'typed22.bin'
    with raw.open('rb') as f:need(struct.unpack('<III',f.read(12))==(nodes,22,count),'Genuine original typed22 header differs')
    need(raw.stat().st_size==12+count*dtype.itemsize and dtype.itemsize==8+nodes*212,'Actual typed22 extent differs')
    clocks=table(root/'clocks.csv');expected_clock=SOURCE_CLOCK_HEADER if nodes==7060 else CLOCK_HEADER
    need(len(clocks)==count and list(clocks[0])==expected_clock,'Original source/receiver signed-clock layout/count differs')
    expected=np.arange(7060,dtype=np.uint32) if nodes==7060 else np.r_[np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)]
    consumed.extend(stat(root/q) for q in ('typed22.bin','typed22_layout.csv','clocks.csv'))
    return dict(root=root,count=count,nodes=nodes,frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(count,)),clocks=clocks,expected=expected,dtype=dtype)

def inputs(profile,runpath,nativepath,consumed):
    count,end,configuration=PROFILES[profile];run=read(runpath);native=read(nativepath)
    need(run['passed'] and run['solver_completed'] and run['actual_steps']==end and run['saved_frames']==count,'Actual solver/declared bounded profile differs')
    if 'consumed_stats_unchanged' in run:need(run['consumed_stats_unchanged'],'Actual run consumed binding changed')
    need(native['passed'] and native['consumed_stats_unchanged'] and entry(native,'source_run')==stat(runpath),'Unique native receipt must bind this actual new run')
    invocations=[native[k] for k in ('reader_invocations','decoder_invocations') if k in native];need(invocations and all(x==1 for x in invocations),'Exactly one retained native read required')
    actual=entry(run,'actual_call');owned(read(actual['path']));ncall=entry(native,'actual_call');nc=read(ncall['path']);owned(nc)
    doneentry=entry(native,'native_completion','completion');metaentry=entry(native,'metadata');done=read(doneentry['path']);meta=read(metaentry['path']);root=Path(doneentry['path']).parent
    need(done['passed'] and done['stage']=='c08_h18_wend_native_r1.receiver' and done['samples']==count and done['completed_steps']==end and done['typed_arrays']==22 and done['typed_bytes_per_particle']==212,'Actual new receiver native completion differs')
    need(done['actual_native_IDs_per_frame']==6805 and done['actual_fixed_IDs']==1805 and done['soil_IDs']==5000 and done['ledger_checks']==count*5000 and done['P0_bits_checks']==count*6805,'Original full-ID/ledger/P0 coverage differs')
    need(done['max_scalar_clock_error_s']<=1e-14 and done['max_ledger_relative_error']<=5e-13 and done['max_signed_dterror_s']<=1e-14,'Original native numerical budgets differ')
    need(meta['passed'] and meta['stage']=='c08_h18_storage_native_r1.metadata' and meta['samples']==count and meta['backend_argument']=='GPU' and meta['original_AV_private_keys_absent_headers']==count and meta['observer_pressure_budget_proven_by_reader'] is False,'Observer-independent actual metadata required')
    planentry=entry(run,'planned_steps');plan=table(planentry['path']);need(len(plan)==count and list(plan[0])==['part','completed_step','saved_step','time_s','dt_s'],'Bound actual scalar plan differs')
    preentry=entry(run,'source_pre_file');need(same(preentry['path'],T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'),'Original certified PRE required')
    args=nc['arguments'];need(len(args)==8 and args[:3]==['--receiver',profile,'psi0'] and same(args[4],preentry['path']) and same(args[5],planentry['path']) and same(args[-1],root),'Actual reader profile/PRE/plan/output binding differs')
    rb=entry(native,'reader_build');reader=read(rb['path']);need(reader['passed'] and reader['consumed_stats_unchanged'] and same(nc['program'],entry(reader,'program')['path']),'Actual independent reader program differs')
    buildentry=entry(run,'source_build');build=read(buildentry['path']);need(build['passed'] and build['configuration']==configuration and build['consumed_stats_unchanged'] and build['actual_link_objects']==114 and build['original_physical_CUDA_recompiled']==0 and build['macro_enabled_in_host_and_observer_TUs'],'Exact independent observer build required')
    need(entry(build,'program')==entry(run,'program') and entry(build,'source_capture')==entry(run,'source_capture') and entry(build,'source_archive')==entry(run,'source_archive'),'Actual private program/source binding differs')
    sidecar=entry(run,'observer_sidecar');need(Path(sidecar['path']).name=='C08StorageTrace.csv' and Path(sidecar['path']).parent==Path(entry(run,'Run_out')['path']).parent,'Actual sidecar path differs from owned run')
    xmlentry=entry(run,'input_xml');xml=ET.parse(xmlentry['path']).getroot();kw=core.f32(xml.find('execution/special/hydromechanics/PoreWaterBulkModulus').get('value'));need(kw==KW,'Original Kw differs')
    bundle=typed(root,6805,count,consumed)
    for i,(q,p) in enumerate(zip(bundle['clocks'],plan)):
        need(int(q['part'])==int(p['part'])==i and int(q['completed_step'])==int(p['completed_step']) and int(q['saved_step'])==int(p['saved_step']) and float(q['dt_s'])==float(p['dt_s'])==5e-6 and abs(float(q['time_s'])-float(p['time_s']))<=1e-14,'Actual scalar plan/clock differs')
    need(int(plan[-1]['completed_step'])==end,'Actual planned endpoint differs')
    source_done_entry=entry(run,'source_native');source_done=read(source_done_entry['path']);need(source_done['passed'] and source_done['certified_PRE'] and source_done['samples']==1001 and source_done['completed_steps']==BASE,'Original qualified PRE native completion required')
    pre=typed(Path(source_done_entry['path']).parent,7060,1001,consumed);pref=core.read22(pre,1000);need(bits(pref['time'])==bits(source_done['actual_end_s']),'Actual PRE endpoint clock differs')
    initial=np.asarray(pref['PoroPorosity'][2060:,0]*pref['PoroCurrentVolume'][2060:,0]/kw*pref['PorePress'][2060:,0],dtype=np.float64)
    consumed.extend([stat(runpath),stat(nativepath),actual,ncall,doneentry,metaentry,planentry,preentry,rb,buildentry,sidecar,xmlentry,source_done_entry])
    consumed.extend(entry(run,k) for k in ('program','source_capture','source_archive','Run_out'))
    return bundle,initial,sidecar,run,kw

def byteproof(bundle,profile,consumed):
    if profile=='debug2':return dict(required=False,compared_records=0,Debug_is_not_Release_bit_truth=True)
    control=T/'outputs/c08_h18_as03_n255_r1/native_r1';receipt=T/'logs/c08_h18_as03_n255_native_r1.check.json';q=read(receipt)
    need(q['passed'] and q['consumed_stats_unchanged'],'Retained actual AS03 native control required');consumed.append(stat(receipt))
    ref=typed(control,6805,91,consumed);count=bundle['count'];need(count in (3,91),'Only true first3 or complete91 records are admitted')
    need((bundle['root']/'typed22_layout.csv').read_bytes()==(control/'typed22_layout.csv').read_bytes(),'Literal original layout bytes differ')
    with (bundle['root']/'typed22.bin').open('rb') as a,(control/'typed22.bin').open('rb') as b:
        need(struct.unpack('<III',a.read(12))==(6805,22,count) and struct.unpack('<III',b.read(12))==(6805,22,91),'Preserve genuine new/control headers')
        remaining=count*bundle['dtype'].itemsize
        while remaining:
            n=min(remaining,4*1024*1024);x,y=a.read(n),b.read(n);need(len(x)==len(y)==n and x==y,'Actual all22 and time payload bytes differ');remaining-=n
    with (bundle['root']/'clocks.csv').open('rb') as a,(control/'clocks.csv').open('rb') as b:
        need(a.readline()==b.readline(),'Literal original signed-clock header differs')
        for _ in range(count):need(a.readline()==b.readline(),'Literal original signed-clock row differs')
    return dict(required=True,compared_records=count,genuine_new_header_samples=count,genuine_control_header_samples=91,all22_and_actual_time_bytes_equal=True,literal_layout_bytes_equal=True,all_signed_clock_row_bytes_equal=True,interpolation=False,headers_rewritten=False)

def stream(bundle,initial,sidecar):
    rows=0;previous=[None]*IDS;summaries=[];max_endpoint_ratio=max_native_ratio=max_initial_ratio=0.;expected_dt_sum=0.;prior_updates=0
    with Path(sidecar['path']).open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f);need(reader.fieldnames==HEADER,'Exact26-column actual observer sidecar required')
        for part in range(bundle['count']):
            frame=core.read22(bundle,part);clock=bundle['clocks'][part];step=int(clock['completed_step']);updates=step-BASE;time=float(clock['time_s']);need(0<updates<=180000,'Actual bounded update count differs')
            while prior_updates<updates:expected_dt_sum+=5e-6;prior_updates+=1
            finalS=np.asarray(frame['PoroPorosity'][1805:,0]*frame['PoroCurrentVolume'][1805:,0]/KW*frame['PorePress'][1805:,0],dtype=np.float64)
            sums={k:0. for k in ['initial_S','last_S','weighted_pressure_delta',*TERMS]};abs_global=0.;budget_sum=0.;global_residual=0.;caps=changes=release_changes=0;cap_calls_this_state=None
            for s in range(IDS):
                try:q=next(reader)
                except StopIteration:raise RuntimeError('Truncated actual observer sidecar')
                need(list(q)==HEADER and None not in q and all(q[k].isdecimal() for k in INTS),'Actual observer row integer/layout differs');r={k:int(q[k]) if k in INTS else float(q[k]) for k in HEADER};need(all(math.isfinite(v) for v in r.values()),'Nonfinite observer row')
                need(r['native_id']==2060+s and r['inits']==1 and r['errors']==0 and r['rhs_h']==r['updates']==updates and r['last_completed_step']==step and bits(r['actual_saved_time_s'])==bits(time),'Actual5000-ID/time/stage coverage differs')
                need(bits(r['sum_dt_s'])==bits(expected_dt_sum),'Actual sequential dt accumulation differs; no n*dt substitution')
                need(r['release_cap_calls']==1 and 0<=r['release_cap_changes']<=1 and r['cap_calls']>=updates+1 and r['release_cap_changes']<=r['cap_changes']<=r['cap_calls'],'Actual unique release/cap counts differ')
                if cap_calls_this_state is None:cap_calls_this_state=r['cap_calls']
                need(r['cap_calls']==cap_calls_this_state,'A whole-soil cap observation missed an ID')
                need(r['cap_change']<=0 and all(r[k]>=0 for k in ('sum_abs_increments','local_budget_sum','rate_quantization_bound_only','endpoint_arithmetic_budget')),'Cap/absolute/bound sign differs')
                old=previous[s]
                if old is not None:
                    need(bits(r['initial_S'])==bits(old['initial_S']) and r['release_cap_changes']==old['release_cap_changes'] and r['cap_change']<=old['cap_change'] and all(r[k]>=old[k] for k in ('cap_calls','cap_changes','sum_abs_increments','local_budget_sum','rate_quantization_bound_only')),'Actual per-ID cumulative record regressed')
                c,d,split,write,jw,cap=(r[k] for k in TERMS);ledger=((((c+d)+split)+write)+jw)+cap;residual=(r['last_S']-r['initial_S'])-ledger
                budget=r['local_budget_sum']+gamma(16*updates+8*r['cap_calls']+128)*(r['sum_abs_increments']+abs(r['initial_S'])+abs(r['last_S']))
                need(bits(residual)==bits(r['endpoint_residual']) and bits(budget)==bits(r['endpoint_arithmetic_budget']) and abs(residual)<=budget,'Original per-ID endpoint residual/budget differs or failed')
                need(abs(r['weighted_pressure_delta']-(((c+d)+split)+write))<=budget,'Actual pressure-delta subtotal exceeds the same original arithmetic budget')
                eb=gamma(32)*(abs(initial[s])+abs(r['initial_S']))+32*sys.float_info.min;ne=gamma(32)*(abs(finalS[s])+abs(r['last_S']))+32*sys.float_info.min
                need(abs(r['initial_S']-initial[s])<=eb and abs(r['last_S']-finalS[s])<=ne,'Independent PRE/native pressure-capacity endpoint differs')
                max_endpoint_ratio=max(max_endpoint_ratio,abs(residual)/budget if budget else 0);max_native_ratio=max(max_native_ratio,abs(r['last_S']-finalS[s])/ne if ne else 0);max_initial_ratio=max(max_initial_ratio,abs(r['initial_S']-initial[s])/eb if eb else 0)
                for k in sums:sums[k]+=r[k]
                global_residual+=residual;budget_sum+=budget;abs_global+=abs(r['initial_S'])+abs(r['last_S'])+sum(abs(r[k]) for k in TERMS);caps+=r['cap_calls'];changes+=r['cap_changes'];release_changes+=r['release_cap_changes'];previous[s]=r;rows+=1
            gledger=((((sums[TERMS[0]]+sums[TERMS[1]])+sums[TERMS[2]])+sums[TERMS[3]])+sums[TERMS[4]])+sums[TERMS[5]];gres=(sums['last_S']-sums['initial_S'])-gledger;gbudget=budget_sum+gamma(16*IDS+128)*abs_global
            need(abs(gres)<=gbudget and abs(gres-global_residual)<=gamma(16*IDS+128)*abs_global,'Ordered global storage aggregation exceeds local-plus-sum budget')
            summaries.append(dict(part=part,actual_time_s=time,completed_step=step,updates_per_ID=updates,soil_IDs=IDS,cap_calls=caps,cap_changes=changes,release_cap_changes=release_changes,**sums,global_endpoint_residual=gres,sum_local_endpoint_residual=global_residual,global_arithmetic_budget=gbudget,storage_proxy_not_fluid_mass=True,rate_quantization_is_bound_only=True))
        need(next(reader,None) is None,'Unexpected extra observer records')
    need(rows==IDS*bundle['count'],'Complete sidecar count differs')
    return dict(actual_rows=rows,actual_saved_states=bundle['count'],all5000IDs_per_state=True,all26_columns_exact=True,all_per_ID_endpoint_budgets_passed=True,independent_PRE_initial_and_native_final_S_checked=True,max_endpoint_budget_ratio=float(max_endpoint_ratio),max_native_S_arithmetic_ratio=float(max_native_ratio),max_PRE_initial_S_arithmetic_ratio=float(max_initial_ratio)),summaries

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',choices=tuple(PROFILES),required=True);p.add_argument('--run-receipt',type=Path,required=True);p.add_argument('--native-receipt',type=Path,required=True);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Root full read and offline review admission required')
    check=L/('c08_h18_storage_'+a.profile+'_review_r2.check.json');summary=T/'figures'/('c08_h18_storage_'+a.profile+'_review_r2_summary.csv');need(not check.exists() and not summary.exists(),'Existing complete/failed analysis artifacts protected');consumed=[];result=dict(stage=TAG,profile=a.profile,passed=False,solver_invocations=0,reader_invocations=0,build_invocations=0,GPU_actions=0,SHA_scans=0,physical_acceptance=False)
    try:
        consumed=[stat(Path(__file__)),stat(NOTE),stat(Path(core.__file__))];bundle,initial,sidecar,run,kw=inputs(a.profile,a.run_receipt,a.native_receipt,consumed);proof=byteproof(bundle,a.profile,consumed);observations,summaries=stream(bundle,initial,sidecar)
        need(all(stat(q['path'])==q for q in consumed),'A bound source/native/sidecar artifact changed during offline review')
        with summary.open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
        result.update(passed=True,source_run=stat(a.run_receipt),native_receipt=stat(a.native_receipt),observer_sidecar=sidecar,observations=observations,no_feedback_byteproof=proof,summary=stat(summary),consumed=consumed,consumed_stats_unchanged=True,storage_is_conditional_proxy=True,rate_quantization_not_signed_measured_term=True)
    except Exception as error:result.update(first_failure=str(error),consumed=consumed,partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
if __name__=='__main__':main()
