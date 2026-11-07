"""Offline four-run shared-PRE continuity review. No solver, reader, hash scan or retry."""
import csv,json,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];L=T/'logs';P=T/'figures/upl_preload_handoff_review_r1';CHECK=L/'upl_preload_handoff_review_r1.check.json'

def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def table(p):
    with Path(p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write(p,rows):
    with Path(p).open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def frob(v):return np.sqrt(np.sum(v[:,:3]**2,axis=1)+2*np.sum(v[:,3:]**2,axis=1))
def bits(v):return np.ascontiguousarray(v).tobytes()
CLOCK_INTS=('completed_step','saved_step','dterror_interval_empty','phase','actual_native_IDs')
CLOCK_FLOATS=('time_s','dt_s','signed_dterror_s')
def clockbytes(c):
    # Part/file/local counters are genuine renumbered output identity, not integration state.
    return struct.pack('<5Q3d',*(int(c[k]) for k in CLOCK_INTS),*(float(c[k]) for k in CLOCK_FLOATS))

def load(mode,backend):
    old=mode=='old';tag=('upl_ck2_release_short_'+backend+'_r1' if old else 'upl_preload_handoff_'+mode+'_'+backend+'_r1')
    d=T/'outputs'/(tag+'_native_r1');check=L/(tag+'_native_r1.check.json');receipt=read(check);runpath=L/(tag+'.run.json');run=read(runpath)
    need(receipt['passed'] and receipt['original_native_guards_passed'] and receipt['consumed_stats_unchanged'] and run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0,'Closed owned run/native safety required: '+tag)
    for e in [receipt['native_completion'],*receipt['files']]:need(stat(e['path'])==e,'Closed native output changed: '+e['path'])
    done=read(d/'completion.json');need(done['HydroMechConductivityModel']==1 and done['HydroMechConductivityCk']==2 and done['completed_steps']==800 and done['typed_arrays']==22,'Wrong native Ck2/completion profile')
    if not old:
        need(receipt['qualified_elastic_PRE_verified'] and done['qualified_PRE_read_by_current_helper'] and done['source_PRE_completed_step']==380 and done['receiver_part0_is_not_t0']==(mode=='receive'),'Genuine qualified source PRE/receiver identity missing')
        need(run['new_updates_from_completed_counters']==(420 if mode=='receive' else 800),'Actual global/new update count differs')
        need(stat(receipt['certified_pre_file']['path'])==receipt['certified_pre_file'],'Certified PRE changed')
    if backend=='GPU':need(run['memcheck_zero_errors_and_leaks'],'Actual GPU memcheck did not pass')
    layout=table(d/'typed22_layout.csv');need(len(layout)==22 and sum(int(r['bytes_per_particle']) for r in layout)==212 and len({r['array'] for r in layout})==22,'Original22 layout differs')
    dtype={'uint32':'<u4','float32':'<f4','float64':'<f8'};clocks=table(d/'clocks.csv');need(len(clocks)==done['samples'],'Incomplete actual clock history')
    original=table(d/'native_ids.csv');need(len(original)==7060 and all(int(r['id'])==i for i,r in enumerate(original)),'Original native reference IDs differ')
    x0=np.array([[float(r[k]) for k in ('x0','y0','z0')] for r in original]);data={};counts=done['phase_saved_frames'];blobs={}
    for phase,count in enumerate(counts):
        if not count:continue
        blob=(d/('phase%d_typed22.bin'%phase)).read_bytes();blobs[phase]=blob;n=7060 if phase==0 else 6800;size=8+n*212
        need(struct.unpack('<III',blob[:12])==(n,22,count) and len(blob)==12+count*size,'Actual phase header/count/size differs');records=[]
        for local in range(count):
            off=12+local*size;time=struct.unpack_from('<d',blob,off)[0];off+=8;arrays={}
            for r in layout:
                nc=int(r['components']);dt=np.dtype(dtype[r['type']]);v=np.frombuffer(blob,dt,count=n*nc,offset=off);off+=n*nc*dt.itemsize
                need(np.isfinite(v).all(),'Nonfinite original typed array');arrays[r['array']]=v.reshape(n,nc) if nc>1 else v
            wanted=np.arange(7060) if phase==0 else np.r_[np.arange(1800),np.arange(2060,7060)]
            need(np.array_equal(arrays['Idp'],wanted),'Actual original ID membership/order differs');records.append((time,arrays))
        data[phase]=records
    frames=[];previous=0;scalar=0.;used=[0,0]
    for part,c in enumerate(clocks):
        phase=int(c['phase']);local=int(c['phase_local_index']);need(local==used[phase] and int(c['part'])==part,'Actual phase/part ordering differs');used[phase]+=1;time,a=data[phase][local];completed=int(c['completed_step'])
        for _ in range(previous,completed):scalar+=2.5e-6
        previous=completed;need(abs(time-scalar)<=1e-14 and time==float(c['time_s']),'Actual scalar+=dt clock differs')
        if part or mode=='receive':need(int(c['dterror_interval_empty'])==0 and float(c['signed_dterror_s'])<=1e-14,'Original signed interval failed/empty')
        if mode=='receive':need(phase==1 and completed>380,'Receiver emitted an artificial PRE/t0 state')
        ids=a['Idp'];soil=ids>=2060;soilids=ids[soil];need(np.array_equal(soilids,np.arange(2060,7060)),'Missing5000 original soil material IDs')
        j=a['PoroVolumeRatio'][soil];n=a['PoroPorosity'][soil];k=a['PoroHydraulicConductivity'][soil];pn=float(np.float32(.35));k0=float(np.float32(.0002));reference=k0*np.exp((j-1)/((1-pn)*2))
        need(np.all(np.abs(k-reference)<=5e-13*np.abs(reference)),'Independent same-J conductivity law mismatch')
        uall=(a['Posd']-x0[ids])*1000;u=uall[soil];p=a['PorePress'][soil].astype(float);total=np.c_[a['SigmaState_kk'][soil]-p[:,None],a['SigmaState_ij'][soil]];z=x0[soilids,2];h=float(np.float32(.048));top=z>=z.max()-2*h;bottom=z<=z.min()+2*h
        row=dict(mode=mode,backend=backend,part=part,completed_step=completed,saved_step=int(c['saved_step']),actual_time_s=time,phase=phase,native_IDs=len(ids),soil_IDs=5000,p_mean_Pa=float(p.mean()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),p_min_Pa=float(p.min()),p_max_Pa=float(p.max()),top_material_settlement_mm=float(-u[top,2].mean()),bottom_material_settlement_mm=float(-u[bottom,2].mean()),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(total)**2))),J_min=float(j.min()),J_max=float(j.max()),n_min=float(n.min()),n_max=float(n.max()),k_min_m_s=float(k.min()),k_max_m_s=float(k.max()),kappa_max=float(a['Kplastic'][soil].max()),FS23_soil=int(np.isin(a['FSType'][soil],(2,3)).sum()),signed_dterror_s=float(c['signed_dterror_s']),signed_interval_empty=int(c['dterror_interval_empty']))
        frames.append(dict(row=row,clock=c,a=a,p=p,uall=uall,u=u,total=total,j=j,n=n,k=k))
    need(used==counts and previous==800 and abs(frames[-1]['row']['actual_time_s']-.002)<=2.5e-6+1e-14,'Incomplete frame coverage/end')
    return dict(tag=tag,frames=frames,layout=layout,blobs=blobs,receipt=receipt,check=stat(check),run=run,runcheck=stat(runpath),directory=d,done=done)

def compare(label,left,right,phase1=False):
    need(left['layout']==right['layout'],'Compared native layouts differ');a=[f for f in left['frames'] if not phase1 or f['row']['phase']==1];b=[f for f in right['frames'] if not phase1 or f['row']['phase']==1]
    need(len(a)==len(b)>0,'Actual common frame coverage differs: '+label);rows=[];fields=[]
    for x,y in zip(a,b):
        xr,yr=x['row'],y['row'];need(xr['completed_step']==yr['completed_step'] and xr['phase']==yr['phase'] and np.array_equal(x['a']['Idp'],y['a']['Idp']),'Actual matched steps/phases/IDs differ: '+label)
        dp=y['p']-x['p'];du=y['uall']-x['uall'];ds=y['total']-x['total'];fieldrows=[]
        for r in left['layout']:
            name=r['array'];v,w=x['a'][name],y['a'][name];need(v.shape==w.shape and v.dtype==w.dtype,'Native field dtype/shape differs');item=v.dtype.itemsize
            vb=np.ascontiguousarray(v).view(np.dtype('<u%d'%item));wb=np.ascontiguousarray(w).view(np.dtype('<u%d'%item));unequal=vb!=wb;maxabs=float(np.abs(w.astype(np.float64)-v.astype(np.float64)).max())
            fieldrows.append(dict(comparison=label,completed_step=xr['completed_step'],actual_time_s=xr['actual_time_s'],phase=xr['phase'],array=name,dtype=str(v.dtype),components=int(r['components']),bit_equal=bool(not unequal.any()),unequal_scalar_values=int(unequal.sum()),scalar_values=int(v.size),max_abs_difference=maxabs))
        fields.extend(fieldrows)
        row=dict(comparison=label,completed_step=xr['completed_step'],actual_time_s=xr['actual_time_s'],phase=xr['phase'],native_IDs=xr['native_IDs'],time_difference_s=abs(xr['actual_time_s']-yr['actual_time_s']),signed_dterror_difference_s=abs(float(x['clock']['signed_dterror_s'])-float(y['clock']['signed_dterror_s'])),signed_clock_record_bit_equal=clockbytes(x['clock'])==clockbytes(y['clock']),pressure_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),material_XYZ_max_mm=float(np.linalg.norm(du,axis=1).max()),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(ds)**2))),J_max_difference=float(np.abs(y['j']-x['j']).max()),n_max_difference=float(np.abs(y['n']-x['n']).max()),k_max_difference_m_s=float(np.abs(y['k']-x['k']).max()),kappa_max_difference=float(np.abs(y['a']['Kplastic'].astype(float)-x['a']['Kplastic'].astype(float)).max()),FSType_unequal_IDs=int(np.count_nonzero(y['a']['FSType']!=x['a']['FSType'])),all22_fields_bit_equal=all(r['bit_equal'] for r in fieldrows),P0_and_ID_bits_equal=all(bits(x['a'][k])==bits(y['a'][k]) for k in ('Idp','PorePress0')))
        rows.append(row)
    return rows,fields

def main():
    output=[Path(str(P)+s) for s in ('.png','_history.csv','_pairs.csv','_fields.csv')];need(not any(p.exists() for p in [CHECK,*output]),'Existing review protected; no retry/overwrite')
    groups={(mode,backend):load(mode,backend) for mode in ('old','source','receive') for backend in ('CPU','GPU')};pairs=[];fields=[];comparisons={};default={}
    for backend in ('CPU','GPU'):
        old,source,receive=(groups[(m,backend)] for m in ('old','source','receive'))
        rows,f=compare('source_vs_old_'+backend,old,source);pairs.extend(rows);fields.extend(f)
        fullraw=old['blobs'].keys()==source['blobs'].keys() and all(old['blobs'][phase]==source['blobs'][phase] for phase in old['blobs'])
        exact=fullraw and all(r['all22_fields_bit_equal'] and r['signed_clock_record_bit_equal'] for r in rows)
        default[backend]=dict(actual_matched_samples=len(rows),all_actual_phase_export_bytes_equal=fullraw,all22_fields_and_signed_clock_exact=exact)
        rows,f=compare('source_vs_receive_'+backend,source,receive,phase1=True);pairs.extend(rows);fields.extend(f);comparisons['source_vs_receive_'+backend]=rows
        need(source['receipt']['certified_pre_file']==receive['receipt']['certified_pre_file'],'Receiver adopted a different actual PRE file')
    for mode in ('source','receive'):
        rows,f=compare('CPU_vs_GPU_'+mode,groups[(mode,'CPU')],groups[(mode,'GPU')]);pairs.extend(rows);fields.extend(f);comparisons['CPU_vs_GPU_'+mode]=rows
    summaries={name:dict(actual_matched_pairs=len(rows),pressure_RMS_max_Pa=max(r['pressure_RMS_Pa'] for r in rows),material_XYZ_max_mm=max(r['material_XYZ_max_mm'] for r in rows),time_error_max_s=max(r['time_difference_s'] for r in rows),total_stress_Frobenius_RMS_max_Pa=max(r['total_stress_Frobenius_RMS_Pa'] for r in rows),J_max_difference=max(r['J_max_difference'] for r in rows),n_max_difference=max(r['n_max_difference'] for r in rows),k_max_difference_m_s=max(r['k_max_difference_m_s'] for r in rows),kappa_max_difference=max(r['kappa_max_difference'] for r in rows),FSType_max_unequal_IDs=max(r['FSType_unequal_IDs'] for r in rows),signed_dterror_max_difference_s=max(r['signed_dterror_difference_s'] for r in rows),all_signed_clock_records_bit_equal=all(r['signed_clock_record_bit_equal'] for r in rows),all22_fields_bit_equal=all(r['all22_fields_bit_equal'] for r in rows),P0_and_ID_bits_equal=all(r['P0_and_ID_bits_equal'] for r in rows)) for name,rows in comparisons.items()}
    bounded=all(s['pressure_RMS_max_Pa']<=5 and s['material_XYZ_max_mm']<=.005 and s['time_error_max_s']<=1e-14 and s['P0_and_ID_bits_equal'] for s in summaries.values())
    passed=bounded and all(s['all22_fields_and_signed_clock_exact'] for s in default.values())
    history=[f['row'] for m in ('source','receive') for b in ('CPU','GPU') for f in groups[(m,b)]['frames']]
    write(output[1],history);write(output[2],pairs);write(output[3],fields)
    fig,axes=plt.subplots(2,3,figsize=(13.8,7.6));metrics=[('p_RMS_Pa','Pore pressure RMS (Pa)'),('top_material_settlement_mm','Top material settlement (mm)'),('total_stress_Frobenius_RMS_Pa','Total stress Frobenius RMS (Pa)'),('J_min','Minimum J'),('k_min_m_s','Minimum k (m/s)')]
    styles={('source','CPU'):('#1766a4','-',None),('source','GPU'):('#cb771c','--',None),('receive','CPU'):('#1766a4','none','o'),('receive','GPU'):('#cb771c','none','x')}
    for key,(color,ls,marker) in styles.items():
        rows=[f['row'] for f in groups[key]['frames']];x=[r['actual_time_s']*1000 for r in rows]
        for ax,(field,label) in zip(axes.flat,metrics):ax.plot(x,[r[field] for r in rows],label=key[1]+' '+key[0],color=color,ls=ls,marker=marker,mfc='none',ms=4);ax.set(xlabel='Actual time (ms)',ylabel=label);ax.grid(alpha=.25);ax.axvline(.95,color='gray',ls=':',lw=1)
    for backend,color in (('CPU','#1766a4'),('GPU','#cb771c')):
        rows=comparisons['source_vs_receive_'+backend];axes[1,2].plot([r['actual_time_s']*1000 for r in rows],[r['pressure_RMS_Pa'] for r in rows],color=color,marker='o',ms=3,label=backend+' continuity')
    axes[1,2].set(xlabel='Actual time (ms)',ylabel='Source/receiver pressure RMS difference (Pa)');axes[1,2].grid(alpha=.25);axes[1,2].legend();axes[0,0].legend(fontsize=8)
    fig.suptitle('C08 shared elastic PRE handoff: short implementation continuity, not 10 s equilibrium or full collapse');fig.tight_layout(rect=(0,0,1,.95));fig.savefig(output[0],dpi=160);plt.close(fig)
    result=dict(stage='upl_preload_handoff_review_r1',passed=passed,implementation_continuity=passed,default_math_regression=default,comparison_summaries=summaries,native_checks={m+'_'+b:groups[(m,b)]['check'] for m in ('old','source','receive') for b in ('CPU','GPU')},new_run_checks={m+'_'+b:groups[(m,b)]['runcheck'] for m in ('source','receive') for b in ('CPU','GPU')},actual_coarse_dt_s=2.5e-6,global_completed_steps=800,source_new_updates=800,receiver_new_updates=420,source_event_completed_step=380,material_scope='psi0/cohesion5000; source shared PRE certification only',all22_field_differences_reported=True,all_signed_clock_record_differences_reported=True,all_original_single_run_safety_required=True,original_bounds=dict(pressure_RMS_Pa=5,material_XYZ_max_mm=.005,time_s=1e-14),outputs=[stat(p) for p in output],physical_acceptance=False,preload10s_equilibrium_or_qualification_proven=False,full13s_or_three_group_material_validation=False,exact_general_PART_restart_proven=False,source_cell_raw_order_recoverable_from_ID_sorted_BI4=False,primary_state_exact_import_independently_observed=False,continuity_gate_does_not_hide_all22_bit_differences=True,additional_half_or_reference_runs=0,solver_invocations=0,decoder_invocations=0,SHA_scans=0)
    save(CHECK,result);print(json.dumps(result,indent=2));need(passed,'Implementation review failed; preserve all evidence and diagnose without relaxed gates or rerun')
if __name__=='__main__':main()
