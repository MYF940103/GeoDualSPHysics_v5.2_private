"""Two explicit offline AS/fixed-plane implementation reviews; no solver/native calls or next stage."""
import argparse,csv,json,struct
from pathlib import Path
import numpy as np
import mdbc_partition_components_r3 as e
import upl_c08_plane_window_review_r1 as loader
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_as_short_review_r1'

def closed(stem,expectAS,n,end):
    tag='upl_c08_asplane_'+stem+'_r1';folder=T/'outputs'/tag/'native';rp=L/(tag+'.native.json');r=e.read(rp)
    e.need(r['passed'] and r['original_native_guards_passed'] and r['consumed_stats_unchanged'] and r['expected_AS']==expectAS,'Closed new native wrapper required: '+stem);m=e.read(folder/'AS_metadata.json')
    e.need(m['passed'] and m['stage']=='upl_c08_as_plane_native_r2' and m['expected_AS']==expectAS and m['samples']==n and m['completed_steps']==end and m['AS_active_true_headers']==(n if expectAS else 0) and m['core_array_decode_passes']==1,'AS header adapter scope differs')
    paths=[e.stat(rp)]
    for key in ('actual_call','source_run','original_run','completion','AS_metadata'):paths.append(e.bind(r[key]))
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):
        entry=next(x for x in r['outputs'] if Path(x['path']).samefile(folder/leaf));paths.append(e.bind(entry))
    data=loader.load(folder,n,end);return folder,data,paths

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('phase',choices=('smoke','off'));ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();e.need(a.execution_authorized,'Root full-read and explicit offline phase required');tag=TAG+'_'+a.phase;check=L/(tag+'.check.json');csvpath=T/'figures'/(tag+'_pairs.csv');e.need(not check.exists() and not csvpath.exists(),'Existing/partial review protected');before=[e.stat(Path(__file__)),e.stat(Path(loader.__file__)),e.stat(T/'notes'/(TAG+'.md'))];result=dict(stage=tag,passed=False,phase=a.phase,solver_invocations=0,reader_invocations=0,physical_acceptance=False,SHA_scans=0);rows=[]
    try:
        if a.phase=='smoke':
            _,cpu,cpaths=closed('smoke_CPU',True,1,4000040);_,gpu,gpaths=closed('smoke_GPU',True,1,4000040);before += cpaths+gpaths;ca,ga=cpu[0][0],gpu[0][0]
            e.need(np.array_equal(ca['Idp'],ga['Idp']) and int(cpu[2][0]['completed_step'])==int(gpu[2][0]['completed_step'])==4000040 and abs(float(ca['time'])-float(ga['time']))<=1e-14,'Actual one-frame native clock/global step/6800 IDs differ')
            soil=ca['Idp'][:,0]>=2060;e.need(int(soil.sum())==5000,'All5000 actual soil material IDs required');dp=ca['PorePress'][soil,0].astype('float64')-ga['PorePress'][soil,0].astype('float64');du=(ca['Posd'][soil]-ga['Posd'][soil])*1000.;pRMS=float(np.sqrt(np.mean(dp*dp)));uMax=float(np.max(np.abs(du)))
            for idp,pc,pg,delta,xyz in zip(ca['Idp'][soil,0],ca['PorePress'][soil,0],ga['PorePress'][soil,0],dp,du):rows.append(dict(native_ID=int(idp),CPU_actual_time_s=float(ca['time']),GPU_actual_time_s=float(ga['time']),CPU_pressure_Pa=float(pc),GPU_pressure_Pa=float(pg),CPU_minus_GPU_Pa=float(delta),dx_CPU_minus_GPU_mm=float(xyz[0]),dy_CPU_minus_GPU_mm=float(xyz[1]),dz_CPU_minus_GPU_mm=float(xyz[2])))
            result.update(pressure_RMS_difference_Pa=pRMS,material_XYZmax_difference_mm=uMax,actual_clock_difference_s=abs(float(ca['time'])-float(ga['time'])),actual_frame_pairs=1,all5000_material_IDs=True)
            numerical=pRMS<=5. and uMax<=.005
        else:
            folder,new,npaths=closed('off_GPU',False,2,4008000);before += npaths;old=T/'outputs/upl_c08_plane_partial_r1';oc=L/'upl_c08_plane_partial_r1.check.json';o=e.read(oc);e.need(o['passed'] and o['original_saved_native_guards_passed'] and o['consumed_stats_unchanged'] and not o['runtime_success_claimed'],'Old54 partial review not passed')
            original=L/'upl_c08_plane_on_GPU_r1.run.json';oldrun=e.read(original);e.need(not oldrun['passed'] and oldrun['actual_exit']==oldrun['actual_Win32_exit']==1,'Old original solver must remain failed1');olddata=loader.load(old,54,4216000);before += [e.stat(oc),e.stat(original),e.bind(o['native_completion'])]
            for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):
                entry=next(x for x in o['files'] if Path(x['path']).samefile(old/leaf));before.append(e.bind(entry))
            stride=8+6800*212;records=[]
            with (folder/'typed22.bin').open('rb') as aa,(old/'typed22.bin').open('rb') as bb:
                nh=struct.unpack('<III',aa.read(12));oh=struct.unpack('<III',bb.read(12));e.need(nh==(6800,22,2) and oh==(6800,22,54),'Real2/54 headers differ; never rewrite')
                for i in range(2):
                    x,y=aa.read(stride),bb.read(stride);e.need(len(x)==len(y)==stride,'Incomplete actual prefix record');records.append(x==y);rows.append(dict(part=i,new_actual_time_s=float(new[0][i]['time']),old_actual_time_s=float(olddata[0][i]['time']),new_completed_step=int(new[2][i]['completed_step']),old_completed_step=int(olddata[2][i]['completed_step']),all22_and_time_record_bytes_equal=x==y))
                e.need(aa.read(1)==b'','Extra new OFF native record')
            nc=(folder/'clocks.csv').read_bytes().splitlines(keepends=True);oldc=(old/'clocks.csv').read_bytes().splitlines(keepends=True);e.need(len(nc)==3 and len(oldc)==55,'Actual2/54 signed clock counts differ');clock=[nc[i]==oldc[i] for i in range(3)];layout=(folder/'typed22_layout.csv').read_bytes()==(old/'typed22_layout.csv').read_bytes();numerical=all(records) and all(clock) and layout
            result.update(actual_original_headers=[list(nh),list(oh)],actual_common_records=2,typed_arrays_per_record=22,record_bytes=stride,time_and_all22_record_bytes_equal=records,header_and_two_complete_signed_clock_rows_equal=clock,layout_byte_equal=layout,header_count_or_records_rewritten=False,old_runtime_exit=1,old_runtime_success_claimed=False,prefix_saved_state_equality_not_runtime_success=True)
        with csvpath.open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        e.need(all(e.stat(x['path'])==x for x in before),'Closed source/native products changed');result.update(passed=bool(numerical),consumed_stats_unchanged=True,pair_CSV=e.stat(csvpath))
        if not numerical:result['first_failure']='Declared original implementation comparison failed; preserve numeric metrics/bytes and CSV, no repeated decoder or solver.'
    except Exception as error:result.update(first_failure=str(error))
    result['consumed']=before;e.save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
