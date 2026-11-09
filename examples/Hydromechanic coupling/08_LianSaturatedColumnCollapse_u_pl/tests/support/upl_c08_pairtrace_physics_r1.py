"""Scientific extraction of passed pairtrace telemetry; no solver, decoder or physical acceptance."""
import argparse,csv,json
from pathlib import Path
import upl_c08_causal_physics_r1 as old
import upl_c08_pairtrace_trace_review_r1 as schema
np,plt=old.np,old.plt
need,read,stat,bind=schema.need,schema.e.read,schema.stat,schema.bind
T,L=schema.T,schema.L;TAG='upl_c08_pairtrace_physics_r1';JOB='upl_c08_pairtrace_window_GPU_r1';IDS=schema.IDS
CHECK=L/(TAG+'.check.json');NEAR=L/'upl_c08_pair_mechanism_r1.check.json'
FILES={k:T/'figures'/(TAG+'_'+k+s) for k,s in (('steps','.csv'),('cumulative','.csv'),('history','.png'),('material','.png'))}


def location(r):
    return {k:r[k] for k in ('native_id','nstep','step_start_s','tau_s','pre_FSType','cor_FSType','pond_FSType','pre_material_status_name','cor_material_status_name')}


def observe(summary,r):
    s=summary[str(r['native_id'])];loc=location(r)
    for key in ('p_n_Pa','p_half_Pa','p_full_raw_Pa','p_pond_Pa','Jnew','cor_Ireturned_Pa','cor_kappa_candidate'):
        for kind in ('min','max'):
            name=key+'_'+kind
            if name not in s or (r[key]<s[name]['value'] if kind=='min' else r[key]>s[name]['value']):s[name]=dict(value=r[key],**loc)
        if key.startswith('p_') and r[key]<0:s.setdefault('first_sampled_negative_'+key,dict(value=r[key],**loc))
    for prefix in ('pre','cor'):
        if r[prefix+'_material_status']==4:s.setdefault(prefix+'_first_sampled_TensionRepair',dict(Ireturned_Pa=r[prefix+'_Ireturned_Pa'],kappa_candidate=r[prefix+'_kappa_candidate'],**loc))
    if r['cor_material_status']!=1:s.setdefault('cor_first_sampled_nonelastic',loc.copy())
    if r['cor_Ireturned_Pa']>0:s.setdefault('cor_first_sampled_positive_I',dict(value=r['cor_Ireturned_Pa'],kappa_candidate=r['cor_kappa_candidate'],**loc))
    if r['cor_material_status']==4:
        s['sampled_cor_cap_rows']=s.get('sampled_cor_cap_rows',0)+1
        for key in ('cor_Ireturned_Pa','cor_kappa_candidate'):
            for kind in ('min','max'):
                name='cap_'+key+'_'+kind
                if name not in s or (r[key]<s[name] if kind=='min' else r[key]>s[name]):s[name]=r[key]


def stream(path,anchor):
    pending={i:[] for i in IDS};rows=[];summary={str(i):{} for i in IDS};current=None;raw_rows=0;writer=None
    with path.open(encoding='utf-8-sig',newline='') as source,FILES['steps'].open('x',encoding='utf-8',newline='') as output:
        reader=csv.DictReader(source);need(reader.fieldnames==schema.HEADER,'Passed97-column header required')
        def emit():
            nonlocal writer
            for identity in IDS:
                events=pending[identity];r=old.wide(events,anchor);cor=next(q for q in events if int(q['event'])==1 and int(q['interstep'])==3);pond=[q for q in events if int(q['event'])==3 and int(q['interstep'])==3][-1]
                r.update(cor_hydraulic_lap_Pa_s=1e9/float(cor['n'])*float(cor['ki'])/9806.65*float(cor['lap']),pond_FSType=int(pond['FSType']))
                if writer is None:writer=csv.DictWriter(output,fieldnames=list(r));writer.writeheader()
                writer.writerow(r);rows.append(r);observe(summary,r)
        for q in reader:
            step,identity=int(q['nstep']),int(q['native_id']);need(identity in IDS,'Actual observer ID differs')
            if current is not None and step!=current:emit();pending={i:[] for i in IDS}
            current=step;pending[identity].append(q);raw_rows+=1
        need(current is not None,'Empty sealed trace');emit()
    return rows,summary,raw_rows


def cumulative(path,anchor):
    rows=[];prior={i:None for i in IDS};first={}
    with path.open(encoding='utf-8-sig',newline='') as source:
        reader=csv.DictReader(source);need(reader.fieldnames==schema.TOTAL_HEADER,'Passed56-column Totals header required')
        for raw in reader:
            r={k:int(v) if k in schema.TOTAL_INTS else float(v) for k,v in raw.items()};identity=r['native_id'];K=r['actual_bulk_modulus_Pa'];r['tau_last_step_start_s']=r['last_step_start_s']-anchor
            r['trial_trace_compliance']=r['sum_cor_dt_rsigma_trace_Pa']/(3*K);r['return_trace_compliance_shadow']=r['sum_cor_trial_minus_returned_I_Pa']/(3*K);r['endpoint_trace_change_over_3K']=(r['last_returned_I_Pa']-r['initial_I_Pa'])/(3*K)
            r['trace_compliance_closure_residual']=r['endpoint_trace_change_over_3K']-r['trial_trace_compliance']+r['return_trace_compliance_shadow'];r['all_plane_hits']=sum(r['plane_hit_'+s+'_'+d] for s in ('pre','cor') for d in ('x','z'));r['plane_delta_v_norm_m_s']=float(np.linalg.norm([r['sum_delta_v_'+s+str(d)] for s in ('pre','cor') for d in range(3)]))
            if r['status_cor4']>0 and identity not in first:first[identity]=dict(first_positive_count_snapshot_completed_step=r['completed_step'],last_step_start_s=r['last_step_start_s'],count=r['status_cor4'],previous_snapshot_completed_step=prior[identity]['completed_step'] if prior[identity] else 4000000,not_exact_first_event_time=True)
            prior[identity]=r;rows.append(r)
    old.csvwrite(FILES['cumulative'],rows);return rows,first


def plots(rows,total,near):
    fig,axes=plt.subplots(3,3,figsize=(16,10),layout='constrained')
    for j,identity in enumerate(IDS):
        d=[r for r in rows if r['native_id']==identity];x=[r['tau_s'] for r in d]
        for key,label,style in (('p_n_Pa','p_n',':'),('p_half_Pa','half','--'),('p_full_raw_Pa','full raw','-'),('p_pond_Pa','after ponding','-')):axes[j,0].plot(x,[r[key]/1000 for r in d],style,label=label,lw=.8)
        axes[j,0].axvline(near,color='.5',ls=':',lw=.8,label='7011/12 first saved close');axes[j,0].set(ylabel='ID%d pressure [kPa]'%identity)
        for key,label,color in (('cor_compression_Pa_s','compression','C0'),('cor_hydraulic_lap_Pa_s','k lap / gamma','C1'),('cor_chain_Pa_s','chain / gamma','C2'),('cor_RHS_logged_Pa_s','logged RHS','k')):axes[j,1].plot(x,[r[key]/1000 for r in d],label=label,color=color,lw=.8)
        axes[j,1].set_yscale('symlog',linthresh=1.);axes[j,1].set(ylabel='Cor pressure source [kPa/s]');axes[j,2].plot(x,[r['Jnew']-1 for r in d],label='actual Cor Jnew - 1');axes[j,2].set(ylabel='Kinematic volume change')
    for ax in axes.flat:ax.set_xlabel('Actual step-start tau [s]');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle('Three-ID sampled pressure and volume; Cor RHS is formed before Cor material/plane');
    with FILES['history'].open('xb') as handle:fig.savefig(handle,format='png',dpi=170)
    plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(14,10),layout='constrained')
    for j,identity in enumerate(IDS):
        d=[r for r in rows if r['native_id']==identity];x=[r['tau_s'] for r in d];ax=axes[j,0];ax.plot(x,[r['cor_Ireturned_Pa']/1000 for r in d],label='Cor returned Ieff',color='C0');cap=[r for r in d if r['cor_material_status']==4]
        if cap:ax.scatter([r['tau_s'] for r in cap],[r['cor_Ireturned_Pa']/1000 for r in cap],s=3,color='C3',label='actual status4')
        ax.set(ylabel='ID%d effective trace [kPa]'%identity);ax.axhline(0,color='.5',lw=.5);twin=ax.twinx();twin.plot(x,[r['cor_kappa_candidate'] for r in d],color='C2',label='committed kappa',lw=.8);twin.set_ylabel('kappa');ax.legend(fontsize=7,loc='upper left');twin.legend(fontsize=7,loc='lower right')
        d=[r for r in total if r['native_id']==identity];tx=[r['tau_last_step_start_s'] for r in d];ax=axes[j,1]
        for key,label in (('sum_cor_dt_theta','sum dt theta'),('sum_cor_log_Jnew_over_Jbase','sum log J ratio'),('trial_trace_compliance','trial trace / 3K'),('return_trace_compliance_shadow','return drop / 3K'),('endpoint_trace_change_over_3K','endpoint delta I / 3K')):ax.plot(tx,[r[key] for r in d],label=label,lw=1.)
        final=d[-1];ax.set(ylabel='Full-step cumulative diagnostics');ax.set_title('Direct plane hits:%d; delta-v norm %.3g m/s'%(final['all_plane_hits'],final['plane_delta_v_norm_m_s']),fontsize=9);ax.legend(fontsize=7)
    for ax in axes.flat:ax.set_xlabel('Actual recorded step-start tau [s]');ax.grid(alpha=.2)
    fig.suptitle('Actual return status and nonzero initial stress; return compliance is not added to J');
    with FILES['material'].open('xb') as handle:fig.savefig(handle,format='png',dpi=170)
    plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before formal reproducible extraction');need(not CHECK.exists() and not any(p.exists() for p in FILES.values()),'Existing complete/partial science products protected');inputs=[];result=dict(stage=TAG,passed=False,analysis_completed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,checker_invocations=0,build_invocations=0,SHA_scans=0)
    try:
        rp=L/(JOB+'.run.json');npth=L/(JOB+'.native_r1.json');qp=L/(JOB+'.trace_review_r1.json');r,n,q=read(rp),read(npth),read(qp);prefix=n['retained_causal90_prefix'];need(r['passed'] and r['consumed_stats_unchanged'] and r['solver_completed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==4120000 and r['saved_frames']==30 and n['passed'] and n['consumed_stats_unchanged'] and n['original_native_guards_passed'] and n['source_run']==stat(rp) and prefix['passed'] and prefix['actual_common_saved_frames']==30 and prefix['all22_and_actual_time_payload_byte_exact'] and prefix['typed_layout_byte_exact'] and prefix['clock_and_signed_header_and_first30_rows_byte_exact'],'Normal run/native and exact retained30-prefix must pass');need(q['passed'] and q['consumed_stats_unchanged'] and q['source_run']==stat(rp) and q['native_receipt']==stat(npth) and q['trace']==r['trace_file'] and q['totals']==r['totals_file'] and q['observed_native_IDs']==list(IDS),'Actual passed trace-review bindings required')
        near=read(NEAR);need(near['passed'] and near['first_saved_close_pair_part']==14,'Existing saved-spacing observation required');nearpoint=near['first_saved_close_pair'];anchor=float(r['actual_source_time_from_loader']);inputs=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(old.__file__),Path(schema.__file__),rp,npth,qp,NEAR)]+[bind(r[k]) for k in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','trace_file','totals_file')]+[bind(n[k]) for k in ('completion','metadata')]
        rows,summary,rawrows=stream(Path(r['trace_file']['path']),anchor);total,cap_snapshots=cumulative(Path(r['totals_file']['path']),anchor);need(len(rows)==9000 and len(total)==90 and rawrows==q['observations']['rows'],'Already checked sampled/full-snapshot accounting differs');plots(rows,total,float(nearpoint['tau_s']));need(all(stat(e['path'])==e for e in inputs),'Consumed closed telemetry/helper changed')
        result.update(passed=True,analysis_completed=True,source_run=stat(rp),native_receipt=stat(npth),trace_review=stat(qp),actual_source_time_s=anchor,observed_native_IDs=list(IDS),main_CSV_stream_passes=1,raw_main_rows=rawrows,sampled_ID_step_rows=len(rows),actual_full_step_totals_rows=len(total),sampled_resolution_s=.0001,sampled_onsets_and_extrema=summary,first_positive_all_step_cap_count_snapshots=cap_snapshots,full_step_final_totals={str(i):next(v for v in reversed(total) if v['native_id']==i) for i in IDS},first_saved_close_pair_observation=nearpoint,continuous_close_pair_onset_claimed=False,raw_q_or_lambda_available=False,return_compliance_is_shadow_not_added_J=True,sampled_sums_are_not_full_step_budgets=True,prior_temporary_readonly_query_disclosed=True,visual_QA_pending=True,repair_selected=False)
    except Exception as error:result['first_failure']=str(error)
    result.update(consumed=inputs,consumed_stats_unchanged=bool(inputs) and all(stat(e['path'])==e for e in inputs),outputs=[stat(p) for p in FILES.values() if p.exists()])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(passed=result['passed'],check=str(CHECK),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
