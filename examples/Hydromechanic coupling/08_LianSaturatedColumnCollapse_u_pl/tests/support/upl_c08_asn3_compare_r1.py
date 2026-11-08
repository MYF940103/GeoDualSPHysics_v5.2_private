"""Exponent3 versus sealed exponent2.55 caches; only n3 payload is streamed in full."""
import argparse,json,struct
from pathlib import Path
import upl_c08_clustering_r1 as cluster
np,c,plt=cluster.np,cluster.c,cluster.plt
TAG='upl_c08_asn3_compare_r1';T=c.T;PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');JOB='upl_c08_asn3_window_GPU_r1'

def n3(control):
    rp=T/'logs'/(JOB+'.run.json');npth=T/'logs'/(JOB+'.native_r1.json');r,n=c.read(rp),c.read(npth)
    c.need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==4264000 and r['saved_frames']==66 and r['consumed_stats_unchanged'] and r['ArtificialStressCoef']==.2 and r['ArtificialStressExp']==3,'Genuine completed n3 solver required')
    c.need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'] and n['decoder_invocations']==1,'Genuine unique n3 native check required');c.bind(n['source_run']);c.need(Path(n['source_run']['path']).samefile(rp),'Native source-run binding differs')
    native=Path(c.bind(n['completion'])['path']).parent;d=c.read(native/'completion.json');m=c.read(c.bind(n['metadata'])['path']);call=c.read(c.bind(n['actual_call'])['path'])
    counts=dict(samples=66,completed_steps=4264000,typed_arrays=22,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=330000,fixed_marker_checks=119130,P0_bits_checks=449130,rho_cache_bits_checks=330000,kappa_nondecreasing_from_PRE_checks=330000,nonempty_signed_intervals=66,plane_gap_checks=660000)
    c.need(d['passed'] and d['stage']=='upl_c08_asn3_window_native_r1' and all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['actual_retired_count']==255,'Original n3 native scope/guards differ')
    c.need(m['passed'] and m['stage']=='upl_c08_asn3_window_native_r1.metadata' and m['samples']==m['keep_policy_headers']==m['AS_active_true_headers']==66 and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==3 and m['AS_policy']=='ReleaseOnly','Typed n3 metadata differs; old2.55 loader is forbidden')
    c.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and Path(call['arguments'][-1]).samefile(native),'Actual n3 native exit/output differs');c.need(r['program']==control['run']['program'] and r['source_pre_file']==control['run']['source_pre_file'] and d['source_actual_time_s']==control['done']['source_actual_time_s'],'Same program and actual PRE/clock required')
    before=[c.stat(rp),c.stat(npth),c.bind(n['actual_call']),c.bind(n['completion']),c.bind(n['metadata'])]+[c.bind(r[k]) for k in ('program','source_build','input_xml','source_pre_file')]
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):
        before.append(c.bind(next(e for e in n['outputs'] if Path(e['path']).samefile(native/leaf))))
    c.need(c.table(native/'typed22_layout.csv')==c.table(control['native']/'typed22_layout.csv') and (native/'typed22.bin').stat().st_size==12+66*control['dtype'].itemsize,'Literal n3 schema/payload extent differs')
    xml=c.ET.parse(r['input_xml']['path']).getroot();params=xml.findall('execution/parameters/parameter');exp=[p for p in params if p.get('key')=='ArtificialStressExp'];coef=[p for p in params if p.get('key')=='ArtificialStressCoef'];c.need(len(exp)==len(coef)==1 and float(exp[0].get('value'))==3 and float(np.float32(coef[0].get('value')))==float(np.float32(.2)),'Actual n3 XML values differ');exp[0].set('value','2.55');c.need(tuple(c.physics(xml.find('execution/'+key)) for key in ('special','parameters'))==control['physics'],'Physics differs beyond the declared exponent/comments')
    clocks=c.table(native/'clocks.csv');history=c.table(native/'history.csv');c.need(len(clocks)==len(history)==66,'Actual n3 histories required');return dict(label='epsilon0p2_exponent3',epsilon=.2,native=native,dtype=control['dtype'],done=d,clocks=clocks,history=history,before=before,run=r)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();c.need(a.execution_authorized,'Root full-read after real run/native terminal required');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial n3 comparison protected')
    compare=c.read(c.CHECK);repair_path=T/'logs/upl_c08_clustering_plot_r2.check.json';repair=c.read(repair_path);pp=T/'logs/upl_c08_stage_trace_window_GPU_r1.prefix_r1.check.json';prefix=c.read(pp)
    c.need(compare['passed'] and compare['clock_and_steps_exact'] and compare['actual_matched_samples']==66 and repair['passed'] and repair['current_source_bindings_revalidated'] and repair['retained_CSV_rows']==2196 and not repair['original_CSV_rewritten'],'Passed cached body/clustering observations required')
    c.need(prefix['passed'] and prefix['actual_common_frames']==66 and prefix['all22_and_actual_time_payload_byte_exact'] and prefix['signed_clock_header_and_rows_byte_exact'] and prefix['layout_byte_exact'] and prefix['consumed_stats_unchanged'] and prefix['old_original_header']==[6805,22,300] and prefix['new_original_header']==[6805,22,66],'Genuine retained r5/window66 prefix required')
    control=c.load(c.SPECS[0]);new=n3(control);body_path=Path(str(c.PREFIX)+'_history.csv');cluster_path=Path(str(cluster.PREFIX)+'_history.csv')
    body=[dict(r,group='epsilon0p2_exponent2p55',AS_exponent=2.55) for r in c.table(body_path) if r['group']=='epsilon0p2'];cohorts=[dict(r,group='epsilon0p2_exponent2p55',AS_exponent=2.55) for r in c.table(cluster_path) if r['group']=='epsilon0p2_full_r5' and int(r['part'])<66]
    c.need(len(body)==66 and len(cohorts)==396,'Exact cached66 body/six-cohort states required');body.sort(key=lambda r:int(r['part']));old_cohorts={(int(r['part']),r['cohort']):r for r in cohorts};names=('all_soil','kappa_ge_0p1f','kappa_lt_0p1f','geometric_interior','FS23_or_within_kernelR','within_kernelR_of_fixed_B');c.need(len(old_cohorts)==396 and all((i,k) in old_cohorts for i in range(66) for k in names),'Cached cohort duplicate/missing rows')
    before=[c.stat(__file__),c.stat(T/'notes'/(TAG+'.md')),c.stat(c.CHECK),c.stat(repair_path),c.stat(pp),c.stat(cluster.__file__),c.bind(next(e for e in compare['consumed'] if Path(e['path']).samefile(c.__file__))),c.bind(next(e for e in compare['files'] if Path(e['path']).samefile(body_path))),c.bind(next(e for e in repair['files'] if Path(e['path']).samefile(cluster_path)))]+[c.bind(e) for e in prefix['consumed']]+control['before']+new['before'];pairs=[];new_snap=None
    with (new['native']/'typed22.bin').open('rb') as f:
        c.need(struct.unpack('<III',f.read(12))==(6805,22,66),'Original n3 header required')
        for part in range(66):
            raw=f.read(new['dtype'].itemsize);c.need(len(raw)==new['dtype'].itemsize,'Short n3 record');state=np.frombuffer(raw,dtype=new['dtype'],count=1)[0];time,tau,step=c.inspect(state,new,part);b=body[part]
            c.need(int(b['part'])==part and float(b['time_s'])==time and float(b['tau_s'])==tau and int(b['completed_step'])==step and int(b['soil_IDs'])==5000,'Cached body must match exact actual clocks/IDs semantics')
            for k in names:
                r=old_cohorts[(part,k)];c.need(float(r['time_s'])==time and float(r['tau_s'])==tau and int(r['completed_step'])==step and 0<=int(r['soil_count'])<=5000,'Cached cohort actual clock/material semantics differ')
            c.need(int(old_cohorts[(part,'all_soil')]['soil_count'])==5000,'Cached statistics must retain all5000 soil IDs');q=c.quantities(state,new,part,tau,step);q['AS_exponent']=3.;body.append(q);m=cluster.measures(state);context=dict(group=new['label'],epsilon=.2,part=part,time_s=time,tau_s=tau,completed_step=step);nr=cluster.summarize(m,context)
            for r in nr:r['AS_exponent']=3.
            cohorts.extend(nr);all_new=next(r for r in nr if r['cohort']=='all_soil');all_old=old_cohorts[(part,'all_soil')];pair=dict(part=part,time_s=time,tau_s=tau,completed_step=step)
            for key in ('p_min_Pa','p_max_Pa','p_RMS_Pa','velocity_RMS_m_s','front_particle_center_x_m','max_kappa'):pair[key+'_n3_minus_n2p55']=float(q[key])-float(b[key])
            for key in ('rNN_over_dp_min','rNN_over_dp_q05','pair_both_in_cohort_lt_0p7dp'):pair[key+'_n3_minus_n2p55']=float(all_new[key])-float(all_old[key])
            pairs.append(pair)
            if part==65:new_snap={k:m[k].copy() for k in ('x','fixed','nn','kappa','surface')}
        c.need(f.read(1)==b'','Extra bytes beyond genuine66 n3 records')
    formal=cluster.formal();before.extend(formal['before']);c.need(any(Path(e['path']).samefile(formal['native']/'typed22.bin') for e in prefix['consumed']),'Retained prefix is not this formal payload')
    with (formal['native']/'typed22.bin').open('rb') as f:
        c.need(struct.unpack('<III',f.read(12))==(6805,22,300),'Original formal300 header must not change');f.seek(12+65*formal['dtype'].itemsize);frame=np.frombuffer(f.read(formal['dtype'].itemsize),dtype=formal['dtype'],count=1)[0];end=c.inspect(frame,formal,65);c.need(end==(pairs[-1]['time_s'],pairs[-1]['tau_s'],pairs[-1]['completed_step']),'Actual common endpoint differs');m=cluster.measures(frame);old_snap={k:m[k].copy() for k in ('x','fixed','nn','kappa','surface')}
    files=[]
    for leaf,rows in (('body',body),('cohorts',cohorts),('differences',pairs)):
        path=Path(str(PREFIX)+'_'+leaf+'.csv');c.write(path,rows);files.append(path)
    plt.rcParams.update({'font.size':8,'figure.dpi':165});fig,axes=plt.subplots(2,3,figsize=(15,9),layout='constrained')
    for label,exponent,color in (('epsilon0p2_exponent2p55',2.55,'C0'),(new['label'],3.,'C1')):
        rr=sorted((r for r in body if r['group']==label),key=lambda r:int(r['part']));cc=sorted((r for r in cohorts if r['group']==label and r['cohort']=='all_soil'),key=lambda r:int(r['part']));t=[float(r['tau_s']) for r in rr];tag='n='+str(exponent);ax=axes.ravel()
        for key,style in (('p_min_Pa','--'),('p_max_Pa',':'),('p_RMS_Pa','-')):ax[0].plot(t,[float(r[key])*.001 for r in rr],style,c=color,label=tag+' '+key.split('_')[1])
        ax[1].plot(t,[float(r['velocity_RMS_m_s']) for r in rr],c=color,label=tag+' RMS');ax[1].plot(t,[float(r['max_speed_m_s']) for r in rr],'--',c=color,label=tag+' max');ax[2].plot(t,[float(r['front_particle_center_x_m']) for r in rr],c=color,label=tag);ax[3].plot(t,[float(r['max_kappa']) for r in rr],c=color,label=tag)
        for key,style in (('pair_both_in_cohort_lt_0p5dp','-'),('pair_both_in_cohort_lt_0p7dp','--')):ax[4].plot(t,[float(r[key]) for r in cc],style,c=color,label=tag+(' r<.5dp' if style=='-' else ' r<.7dp'))
        for key,style in (('rNN_over_dp_min','-'),('rNN_over_dp_q05','--')):ax[5].plot(t,[float(r[key]) for r in cc],style,c=color,label=tag+(' min' if style=='-' else ' q05'))
    axes[0,0].set_yscale('symlog',linthresh=.1)
    for ax,(title,ylabel) in zip(axes.ravel(),(('Saved p, not dense peaks','p [kPa]'),('Soil speed','Speed [m/s]'),('Particle-center front','x [m]'),('Plastic history','max kappa'),('Unique close pairs; descriptive','Pair count'),('Raw nearest-other spacing','rNN / dp'))):ax.set(title=title,xlabel='Actual tau from PRE [s]',ylabel=ylabel,xlim=(pairs[0]['tau_s'],pairs[-1]['tau_s']));ax.grid(alpha=.25);ax.legend(fontsize=6)
    fig.suptitle('Epsilon=.2, prescribed exponent2.55 versus3; fixed5000 soil IDs; parameter response, not physical/theory acceptance');path=Path(str(PREFIX)+'_history.png');fig.savefig(path);plt.close(fig);files.append(path)
    pictures=(old_snap,new_snap);xy=np.concatenate([q['x'] for q in pictures]);limits=(float(xy[:,0].min()-2*cluster.DP),float(xy[:,0].max()+2*cluster.DP),float(xy[:,1].min()-2*cluster.DP),float(xy[:,1].max()+2*cluster.DP));fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True,layout='constrained')
    for row,key in enumerate(('nn','kappa')):
        values=np.concatenate([q[key] for q in pictures]);norm=cluster.Normalize(float(values.min()),float(values.max()),clip=False)
        for col,q in enumerate(pictures):
            ax=axes[row,col];x=q['x'];ax.scatter(q['fixed'][:,0],q['fixed'][:,1],s=3,c='.7',marker='s',linewidths=0)
            for mask,marker in ((~q['surface'],'o'),(q['surface'],'^')):ax.scatter(x[mask,0],x[mask,1],c=q[key][mask],norm=norm,cmap='viridis',s=7,marker=marker,linewidths=0)
            ax.set(xlim=limits[:2],ylim=limits[2:],xlabel='x [m]',ylabel='z [m]',title='n=%g, actual tau=%.12g s'%(2.55 if col==0 else 3.,end[1]));ax.set_aspect('equal',adjustable='box')
        fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=axes[row,:].tolist(),label='rNN/dp' if key=='nn' else 'Kplastic kappa',shrink=.8)
    fig.suptitle('Complete common endpoint: raw soil spacing and kappa; grey fixed markers, triangles FS2/3\nSmall deformation or large NN spacing alone does not establish removal of tensile instability');path=Path(str(PREFIX)+'_endpoint.png');fig.savefig(path);plt.close(fig);files.append(path)
    c.need(all(c.stat(e['path'])==e for e in before),'Sealed cached/native/source input changed');result=dict(stage=TAG,passed=True,analysis_completed=True,actual_common_frames=66,soil_IDs=5000,n3_typed_payload_sequential_passes=1,baseline66_payload_read=False,baseline_formal_endpoint_records_read=1,baseline_body_from_passed_cache=True,baseline_clustering_from_revalidated_retained_CSV=True,original66_300_headers_not_rewritten=True,n3_exponent_metadata_expected=3.,epsilon_float=float(np.float32(.2)),parameter_differences_not_half_or_theory_error=True,no_cross_parameter_5Pa_gate=True,NN_clustering_metrics_not_tensile_causation=True,dense_trace_read=False,saved_extrema_not_dense_peaks=True,small_motion_not_physical_acceptance=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,queue_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,files=[c.stat(p) for p in files])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('ASN3_COMPARISON_READY',CHECK,flush=True)

if __name__=='__main__':main()
