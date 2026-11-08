"""Compare existing causal native90/root-r6 full300 prefixes; never decode or rewrite native data."""
import argparse,csv,io,json,math,os,struct
from pathlib import Path
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];C=T.parent;TAG='upl_c08_causal_prefix90_r1';OLD='upl_c08_causal_window_GPU_r1'
FULL=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r6_GPU_out';N=6805;COMMON=90

def native_context(before):
    op=T/'logs'/(OLD+'.native_r1.json');o=e.read(op);e.need(o['passed'] and o['original_native_guards_passed'] and o['consumed_stats_unchanged'],'Passed retained90 native required');old=Path(e.bind(o['completion'])['path']).parent;e.need(old.samefile(T/'outputs'/OLD/'native'),'Actual causal90 native path differs');br=e.read(e.bind(o['source_run'])['path']);e.need(br['passed'] and br['actual_exit']==br['actual_Win32_exit']==0 and br['actual_steps']==4360000 and br['saved_frames']==90 and br['consumed_stats_unchanged'],'Actual normal retained90 run required')
    fp=T/'logs/upl_c08_formal_psi0_r6_r1.run.json';fr=e.read(fp);pp=FULL/'postprocess_r6.json';post=e.read(pp);nc=Path(e.bind(post['native_call'])['path']);call=e.read(nc)
    e.need(fr['passed'] and fr['actual_exit']==fr['actual_Win32_exit']==0 and fr['solver_completed'] and fr['postprocess_completed'] and fr['consumed_stats_unchanged'] and fr['actual_steps']==5200000 and fr['saved_frames']==300 and post['passed'] and post['native_completed'] and post['global_steps']==5200000 and post['saved_frames']==300 and call['passed'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0,'Actual normal root300 run/native post required')
    new=Path(e.bind(post['native_completion'])['path']).parent;files={Path(q['path']).name:q for q in o['outputs']};newfiles={Path(q['path']).name:q for q in call['outputs']};before.extend((e.stat(op),e.stat(fp),e.stat(pp),e.stat(nc),o['source_run']))
    for folder,entries,count,completion in ((old,files,90,o['completion']),(new,newfiles,300,post['native_completion'])):
        d=e.read(e.bind(completion)['path']);e.need(d['passed'] and d['samples']==count and d['completed_steps']==4000000+4000*count and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==N and d['soil_IDs']==5000 and d['actual_fixed_IDs']==1805,'Original native coverage differs')
        for name in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv','plane_gaps.csv','completion.json','bedkeep_metadata.json'):e.need(Path(e.bind(entries[name])['path']).samefile(folder/name),'Unbound native export');before.append(entries[name])
    od,nd=e.read(old/'completion.json'),e.read(new/'completion.json');e.need(od['source_actual_time_s']==nd['source_actual_time_s']==br['actual_source_time_from_loader']==fr['actual_source_time_from_loader'] and br['source_pre_file']==fr['source_pre_file'],'Same actual source PRE/clock required')
    provenance=[]
    for label,r in (('causal_window90',br),('formal300',fr)):
        build_entry=e.bind(r['source_build']);b=e.read(build_entry['path']);e.need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Referenced own program build must be sealed');refs={k:e.bind(b[k]) for k in ('source_capture','source_archive')};program=e.bind(r['program']);before.extend((build_entry,program,*refs.values()));provenance.append(dict(context=label,actual_program=program,source_build=build_entry,**refs))
    return old,new,od,nd,provenance

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();e.need(a.execution_authorized,'Root full-read before one offline prefix comparison');check=T/'logs'/(TAG+'.check.json');table=T/'figures'/(TAG+'_fields.csv');e.need(not check.exists() and not table.exists(),'Fresh derived check/table required');start=T/'logs'/(TAG+'.start.json');e.need(not start.exists(),'Existing/active single-attempt review protected');e.save(start,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=e.psutil.Process(os.getpid()).create_time(),review_only=True));before=[e.stat(__file__),e.stat(T/'notes'/(TAG+'.md')),e.stat(start)];rows=[];result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,queue_invocations=0,SHA_scans=0,raw_native_rewritten=False)
    try:
        old,new,od,nd,provenance=native_context(before);layout=(old/'typed22_layout.csv').read_bytes();layout_equal=layout==(new/'typed22_layout.csv').read_bytes();e.need(layout_equal,'Actual typed layouts differ; no schema adaptation allowed');schema=list(csv.DictReader(io.StringIO(layout.decode('utf-8-sig'))));e.need(len(schema)==22 and len({q['array'] for q in schema})==22,'Exactly22 actual typed arrays required')
        spans=[('actual_time_f64',0,8)];offset=8;types={'uint32':4,'float32':4,'float64':8}
        for q in schema:
            size=int(q['bytes_per_particle']);e.need(types[q['type']]*int(q['components'])==size,'Actual typed field width differs');spans.append((q['array'],offset,offset+N*size));offset+=N*size
        e.need(offset==8+N*212,'Original212-byte particle schema required');rows=[dict(field=name,records_compared=0,records_byte_equal=0,first_different_part=None,first_different_field_byte=None) for name,_,_ in spans];times=[]
        with (old/'typed22.bin').open('rb') as f,(new/'typed22.bin').open('rb') as g:
            ho,hf=struct.unpack('<III',f.read(12)),struct.unpack('<III',g.read(12));e.need(ho==(N,22,90) and hf==(N,22,300),'Original unequal90/300 headers required, never rewrite');e.need((old/'typed22.bin').stat().st_size==12+90*offset and (new/'typed22.bin').stat().st_size==12+300*offset,'Actual complete payload sizes differ')
            for part in range(COMMON):
                x,y=f.read(offset),g.read(offset);e.need(len(x)==len(y)==offset,'Truncated genuine common record');times.append((struct.unpack('<d',x[:8])[0],struct.unpack('<d',y[:8])[0]))
                for row,(_,lo,hi) in zip(rows,spans):
                    left,right=x[lo:hi],y[lo:hi];equal=left==right;row['records_compared']+=1;row['records_byte_equal']+=int(equal)
                    if not equal and row['first_different_part'] is None:row.update(first_different_part=part,first_different_field_byte=next(i for i,(u,v) in enumerate(zip(left,right)) if u!=v))
            e.need(f.read(1)==b'','Retained90 has extra payload bytes')
        texts={}
        for name in ('clocks.csv','history.csv','plane_gaps.csv'):
            left=(old/name).read_bytes().splitlines(keepends=True);right=(new/name).read_bytes().splitlines(keepends=True);e.need(len(left)==91 and len(right)==301,'Original text record counts differ: '+name);texts[name]=dict(original_short_rows=90,original_full_rows=300,header_byte_equal=left[0]==right[0],header_and_common90_rows_byte_equal=left==right[:91],first_different_line=next((i for i,(u,v) in enumerate(zip(left,right[:91])) if u!=v),None))
        for folder,count,column in ((old,90,0),(new,300,1)):
            with (folder/'clocks.csv').open(encoding='utf-8-sig',newline='') as f:clocks=list(csv.DictReader(f))
            e.need(len(clocks)==count,'Actual clock row count differs')
            for part,q in enumerate(clocks):
                error=float(q['signed_dterror_s']);e.need(int(q['part'])==part and int(q['completed_step'])==4000000+4000*(part+1) and int(q['saved_step'])==4000000+4000*(part+1)-1 and float(q['dt_s'])==.0000025 and q['dterror_interval_empty']=='0' and q['native_IDs']=='6805' and q['phase']=='1' and math.isfinite(error) and error<=1e-14,'Actual cadence/Step/dt/signed nonempty interval differs')
                if part<90:e.need(math.isfinite(times[part][column]) and float(q['time_s'])==times[part][column],'Actual binary/text clock differs')
        binary_equal=all(row['records_byte_equal']==90 for row in rows);result.update(actual_common_saved_frames=90,short_original_header=list(ho),full_original_header=list(hf),headers_rewritten=False,all22_and_actual_time_payload_byte_exact=binary_equal,typed_layout_byte_exact=layout_equal,text_exports=texts,signed_clock_header_and_common_rows_byte_exact=texts['clocks.csv']['header_and_common90_rows_byte_equal'],signed_clock_exclusions=[],same_saved_cadence_steps=4000,source_actual_time_s=od['source_actual_time_s'],program_source_contexts=provenance,same_program_is_not_a_gate=True,actual_binary_export_count=1,source_program_identity_is_descriptive_only=True)
        e.need(all(e.stat(q['path'])==q for q in before),'Consumed existing exports/source references changed');e.need(binary_equal and all(v['header_and_common90_rows_byte_equal'] for v in texts.values()),'Actual field/time/text prefix differs; preserve first differences without relaxing any gate');result.update(passed=True,actual_native_export_prefix_byte_exact=True,consumed_stats_unchanged=True,individual_full_native_guards_reused_not_rerun=True)
    except Exception as error:result['first_failure']=str(error)
    if rows:
        with table.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result.update(consumed=before,files=[e.stat(table)] if table.exists() else []);e.save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
