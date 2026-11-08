"""One streamed scientific extraction of already checked causal telemetry; no physical acceptance."""
import argparse,csv,json,os,struct
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import upl_c08_causal_trace_review_r1 as schema

T,L=schema.T,schema.L;F=T/'figures';TAG='upl_c08_causal_physics_r1';JOB='upl_c08_causal_window_GPU_r1';IDS=schema.IDS
Q=L/(JOB+'.trace_review_r1.json');N=L/(JOB+'.native_r1.json');CHECK=L/(TAG+'.check.json')
FILES={k:F/(TAG+'_'+k+s) for k,s in (('stages','.csv'),('totals','.csv'),('native','.csv'),('history','.png'),('dense','.png'))}
need,read,stat,bind=schema.need,schema.e.read,schema.stat,schema.bind
STATUS=('Invalid','Elastic','Smooth','Apex','TensionRepair','NoAdmissibleFlow','NonConverged','UnresolvedPath')
TERMS=('compression','LP','defect','divAce','chain');DENSE=((.79,.81),(.83,.85))
PLOT=('tau_s','p_half_Pa','p_full_raw_Pa','p_pond_Pa',*[f'cor_{q}_Pa_s' for q in TERMS],'cor_RHS_logged_Pa_s','Jnew','pre_trace_drop_over_3K','cor_trace_drop_over_3K','pre_plane_hit_x','pre_plane_hit_z','cor_plane_hit_x','cor_plane_hit_z','pre_material_status','cor_material_status','nstep','cor_Ireturned_Pa')

def number(row,key):return float(row[key])
def csvwrite(path,rows):
    with path.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def rhs(row,prefix):
    factor=1e9/number(row,'n');kg=number(row,'ki')/(1000.*9.80665)
    defect=1000.*sum(number(row,'finishedAce'+str(c))*number(row,'Lx'+str(c)) for c in range(3)) if number(row,'raw_FS_branch') else -sum(number(row,'GpCorr'+str(c))*number(row,'Lx'+str(c)) for c in range(3))
    terms=(-factor*number(row,'theta'),factor*kg*number(row,'LP'),factor*kg*defect,factor*kg*1000.*number(row,'divAce'),factor*number(row,'chain')/(1000.*9.80665))
    result={prefix+'_'+key+'_Pa_s':value for key,value in zip(TERMS,terms)}
    result.update({prefix+'_RHS_logged_Pa_s':number(row,'value_double'),prefix+'_rate_stored_Pa_s':number(row,'rate_after_Pa_s'),prefix+'_theta_s_inv':number(row,'theta'),prefix+'_FSType':int(row['FSType']),prefix+'_raw_FS_branch':int(float(row['raw_FS_branch'])),prefix+'_x_m':number(row,'pos0'),prefix+'_z_m':number(row,'pos2'),prefix+'_J_force':number(row,'J')})
    return result

def wide(events,anchor):
    core={};leading=[];trailing=[];begun=False
    for r in events:
        key=(int(r['event']),int(r['interstep']))
        if key[0]==3:(trailing if begun else leading).append(r)
        else:need(key not in core,'Duplicate already-checked core event');core[key]=r;begun=True
    pr,pu,mp,pp,cr,mc,pc,cu=(core[k] for k in ((1,2),(2,2),(4,2),(5,2),(1,3),(4,3),(5,3),(2,3)))
    step=int(pr['nstep']);time=number(pr,'step_start_s');need(trailing,'Checked completed ponding event missing')
    pond=lambda rows:json.dumps([[int(r['FSType']),number(r,'p_before_Pa'),number(r,'p_after_Pa'),int(float(r['ponding_changed']))] for r in rows],separators=(',',':'))
    result=dict(native_id=int(pr['native_id']),nstep=step,step_start_s=time,tau_s=time-anchor,sampling='dense_079_081' if 4316000<=step<4324000 else 'dense_083_085' if 4332000<=step<4340000 else 'every40',p_n_Pa=number(pu,'p_before_Pa'),p_half_Pa=number(pu,'p_after_Pa'),p_full_raw_Pa=number(cu,'p_after_Pa'),p_pond_Pa=number(trailing[-1],'p_after_Pa'),leading_ponding=pond(leading),trailing_ponding=pond(trailing),Jnew=number(pc,'Jnew'))
    for prefix,r,m,p in (('pre',pr,mp,pp),('cor',cr,mc,pc)):
        result.update(rhs(r,prefix));K=number(m,'actual_bulk_modulus_Pa');status=int(m['material_status'])
        result.update({prefix+'_material_status':status,prefix+'_material_status_name':STATUS[status],prefix+'_K_Pa':K,prefix+'_Ibase_Pa':number(m,'base_I_Pa'),prefix+'_Itrial_Pa':number(m,'trial_I_Pa'),prefix+'_Ireturned_Pa':number(m,'returned_I_Pa'),prefix+'_trace_drop_over_3K':(number(m,'trial_I_Pa')-number(m,'returned_I_Pa'))/(3.*K),prefix+'_kappa_old':number(m,'kappa_old'),prefix+'_kappa_candidate':number(m,'kappa_candidate'),prefix+'_kappa_saved':number(m,'kappa_saved'),prefix+'_Jbase':number(m,'Jbase'),prefix+'_Jhalf':number(m,'Jhalf'),prefix+'_sigma_rate_trace_Pa_s':number(m,'sigma_rate_trace')})
        for axis,c in (('x',0),('z',2)):
            result[prefix+'_plane_hit_'+axis]=int(p['plane_hit_'+axis]);result[prefix+'_plane_velocity_clamp_'+axis]=int(p['plane_velocity_clamp_'+axis])
            for kind in ('before','after'):result[prefix+'_v'+axis+'_'+kind+'_m_s']=number(p,'velocity_'+kind+str(c))
            result[prefix+'_delta_v'+axis+'_m_s']=number(p,'velocity_after'+str(c))-number(p,'velocity_before'+str(c));result[prefix+'_delta_move_'+axis+'_m']=number(p,'move_after'+str(c))-number(p,'move_before'+str(c))
    return result

def stream_stages(path,anchor):
    plots={i:[] for i in IDS};summary={str(i):{} for i in IDS};pending={i:[] for i in IDS};previous={i:None for i in IDS};current=None;raw_rows=sample_rows=0;writer=None
    def emit(handle):
        nonlocal writer,sample_rows
        for identity in IDS:
            r=wide(pending[identity],anchor);prior=previous[identity];r['previous_sampled_nstep']=prior['nstep'] if prior else '';contiguous=prior is not None and prior['nstep']+1==r['nstep']
            for prefix in ('pre','cor'):r[prefix+'_TensionRepair_onset_in_contiguous_samples']=int(contiguous and prior[prefix+'_material_status']!=4 and r[prefix+'_material_status']==4)
            if writer is None:writer=csv.DictWriter(handle,fieldnames=list(r));writer.writeheader()
            writer.writerow(r);plots[identity].append(tuple(r[k] for k in PLOT));sample_rows+=1;s=summary[str(identity)]
            location={k:r[k] for k in ('nstep','step_start_s','tau_s','pre_FSType','cor_FSType','pre_material_status_name','cor_material_status_name')}
            for key in ('p_half_Pa','p_full_raw_Pa','p_pond_Pa','Jnew','pre_trace_drop_over_3K','cor_trace_drop_over_3K'):
                for kind,op in (('min',lambda a,b:a<b),('max',lambda a,b:a>b)):
                    name=key+'_'+kind
                    if name not in s or op(r[key],s[name]['value']):s[name]=dict(value=r[key],**location)
            for prefix in ('pre','cor'):
                for name,condition in (('first_sampled_nonelastic',r[prefix+'_material_status']!=1),('first_sampled_TensionRepair',r[prefix+'_material_status']==4),('first_sampled_plane_hit',bool(r[prefix+'_plane_hit_x'] or r[prefix+'_plane_hit_z']))):
                    if condition:s.setdefault(prefix+'_'+name,location.copy())
                if r[prefix+'_TensionRepair_onset_in_contiguous_samples']:s.setdefault(prefix+'_first_contiguous_TensionRepair_onset_'+r['sampling'],location.copy())
            previous[identity]=r
    with path.open(encoding='utf-8-sig',newline='') as source,FILES['stages'].open('x',encoding='utf-8',newline='') as output:
        reader=csv.DictReader(source);need(reader.fieldnames==schema.HEADER,'Bound checked97-column header differs')
        for row in reader:
            step=int(row['nstep']);identity=int(row['native_id'])
            if current is not None and step!=current:emit(output);pending={i:[] for i in IDS}
            current=step;pending[identity].append(row);raw_rows+=1
        need(current is not None,'Empty sealed trace');emit(output)
    return {i:np.asarray(rows,dtype=np.float64) for i,rows in plots.items()},summary,raw_rows,sample_rows

def totals(path,anchor):
    rows=[];previous={i:{} for i in IDS}
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);need(reader.fieldnames==schema.TOTAL_HEADER,'Bound checked56-column header differs')
        for raw in reader:
            r={k:int(v) if k in schema.TOTAL_INTS else float(v) for k,v in raw.items()};identity=r['native_id'];K=r['actual_bulk_modulus_Pa'];r['tau_step_start_s']=r['last_step_start_s']-anchor
            for key in ('sum_cor_dt_rsigma_trace_Pa','sum_cor_trial_minus_returned_I_Pa'):
                r[key+'_over_3K']=r[key]/(3.*K);r['interval_'+key+'_over_3K']=(r[key]-previous[identity].get(key,0.))/(3.*K)
            for key in ('sum_cor_log_Jnew_over_Jbase','sum_cor_dt_theta'):r['interval_'+key]=r[key]-previous[identity].get(key,0.)
            r['all_plane_hits']=sum(r['plane_hit_'+stage+'_'+axis] for stage in ('pre','cor') for axis in ('x','z'));previous[identity]=r.copy();rows.append(r)
    csvwrite(FILES['totals'],rows);return rows

def native(folder,anchor):
    layout=list(csv.DictReader((folder/'typed22_layout.csv').open(encoding='utf-8-sig')));fields=[('time','<f8')]
    for field in layout:fields.append((field['array'],{'uint32':'<u4','float32':'<f4','float64':'<f8'}[field['type']],(6805,int(field['components']))))
    dtype=np.dtype(fields);need(len(layout)==22 and dtype.itemsize==8+6805*212,'Fixed6805/22 typed view differs')
    with (folder/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(6805,22,90),'Real90-frame header differs; never rewrite')
    data=np.memmap(folder/'typed22.bin',dtype=dtype,offset=12,mode='r',shape=(90,));clocks=list(csv.DictReader((folder/'clocks.csv').open(encoding='utf-8-sig')));rows=[]
    for part,frame in enumerate(data):
        ids=frame['Idp'][:,0]
        for identity in IDS:
            j=int(np.searchsorted(ids,identity));need(ids[j]==identity,'Tracked native ID absent');v=frame['Vel'][j];s=frame['SigmaState_kk'][j]
            rows.append(dict(native_id=identity,part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-anchor,completed_step=int(clocks[part]['completed_step']),p_Pa=float(frame['PorePress'][j,0]),J=float(frame['PoroVolumeRatio'][j,0]),kappa=float(frame['Kplastic'][j,0]),Ieff_Pa=float(s.sum()),x_m=float(frame['Posd'][j,0]),z_m=float(frame['Posd'][j,2]),vx_m_s=float(v[0]),vz_m_s=float(v[2]),FSType=int(frame['FSType'][j,0])))
    csvwrite(FILES['native'],rows);return rows

def figures(data,total,native_rows):
    index={k:j for j,k in enumerate(PLOT)};fig,axes=plt.subplots(3,4,figsize=(19,10),constrained_layout=True)
    for row,identity in enumerate(IDS):
        a=data[identity];x=a[:,index['tau_s']];ax=axes[row,0]
        for key,label in (('p_half_Pa','half'),('p_full_raw_Pa','full before ponding'),('p_pond_Pa','after ponding')):ax.plot(x,a[:,index[key]]/1000.,label=label,lw=.8)
        n=[r for r in native_rows if r['native_id']==identity];ax.plot([r['tau_s'] for r in n],[r['p_Pa']/1000. for r in n],'.',ms=2,color='k',label='native saved');ax.set(ylabel='ID'+str(identity)+' pressure [kPa]')
        ax=axes[row,1]
        for key in TERMS:ax.plot(x,a[:,index['cor_'+key+'_Pa_s']]/1000.,label=key,lw=.7)
        ax.plot(x,a[:,index['cor_RHS_logged_Pa_s']]/1000.,color='k',label='actual total RHS',lw=1.,zorder=5)
        ax.set_yscale('symlog',linthresh=1.);ax.set(ylabel='Cor RHS [kPa/s]')
        ax=axes[row,2];ax.plot(x,a[:,index['Jnew']]-1.,label='stage Jnew-1',color='C2',lw=.8);ax.plot([r['tau_s'] for r in n],[r['J']-1. for r in n],'.',color='k',ms=2,label='native J-1');ax.set(ylabel='Jnew-1');twin=ax.twinx();twin.plot(x,a[:,index['cor_Ireturned_Pa']]/1000.,color='C3',label='Cor returned Ieff',lw=.8);twin.plot([r['tau_s'] for r in n],[r['Ieff_Pa']/1000. for r in n],'.',color='C4',ms=2,label='native Ieff');twin.set_ylabel('Effective stress trace [kPa]');twin.legend(fontsize=6,loc='lower right')
        ax=axes[row,3];r=[v for v in total if v['native_id']==identity];tx=[v['tau_step_start_s'] for v in r]
        for key,label in (('sum_cor_dt_theta','sum dt theta'),('sum_cor_log_Jnew_over_Jbase','sum log Jnew/Jbase'),('sum_cor_dt_rsigma_trace_Pa_over_3K','sum dt trace(rate)/(3K)'),('sum_cor_trial_minus_returned_I_Pa_over_3K','sum return trace drop/(3K)')):ax.plot(tx,[v[key] for v in r],label=label,lw=1.1)
        ax.set(ylabel='Full-step cumulative [dimensionless]',title='Actual plane hits='+str(r[-1]['all_plane_hits'])+'; delta-v is retained in CSV')
        for ax in axes[row]:
            for low,high in DENSE:ax.axvspan(low,high,color='0.85',alpha=.5)
            ax.grid(alpha=.25);ax.set_xlabel('Recorded tau [s]');ax.legend(fontsize=6)
    fig.suptitle('Output-only three-ID observations: sampled RHS versus genuine full-step Totals; not a causal proof');fig.savefig(FILES['history'],dpi=170);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(14,10),constrained_layout=True)
    for row,identity in enumerate(IDS):
        a=data[identity]
        for column,(low,high) in enumerate(DENSE):
            b=a[(a[:,index['tau_s']]>=low)&(a[:,index['tau_s']]<high)];need(len(b)>0,'No actual samples in requested dense interval');ax=axes[row,column];x=b[:,index['tau_s']]
            for key,label,color in (('p_half_Pa','half','0.55'),('p_full_raw_Pa','full raw','C0'),('p_pond_Pa','ponded','C2')):ax.plot(x,b[:,index[key]]/1000.,color=color,label=label,lw=.8)
            twin=ax.twinx()
            for key,label,style in (('pre_trace_drop_over_3K','Pre return drop/(3K)',':'),('cor_trace_drop_over_3K','Cor return drop/(3K)','--')):twin.plot(x,b[:,index[key]],style,label=label,lw=.7,alpha=.8)
            hit=np.any(b[:,[index[p+'_plane_hit_'+c] for p in ('pre','cor') for c in ('x','z')]]>0,axis=1)
            if np.any(hit):ax.plot(x[hit],b[hit,index['p_full_raw_Pa']]/1000.,'kx',label='sampled plane hit',ms=3)
            ax.set(title='ID'+str(identity)+'; sampled plane-hit rows='+str(int(hit.sum())),xlabel='Actual step-start tau [s]',ylabel='Pressure [kPa]');twin.set_ylabel('Return trace-drop strain (J is in history panel)');ax.grid(alpha=.25)
            h,l=ax.get_legend_handles_labels();h2,l2=twin.get_legend_handles_labels();ax.legend(h+h2,l+l2,fontsize=6,loc='best');ax.ticklabel_format(axis='x',style='plain',useOffset=False)
    fig.suptitle('Dense windows without regridding: Cor RHS precedes Cor return and plane; plane does not rewrite that RHS');fig.savefig(FILES['dense'],dpi=170);plt.close(fig)

def main():
    need(not any(p.exists() for p in (*FILES.values(),CHECK)),'Existing complete/partial scientific outputs protected')
    q,n=read(Q),read(N);need(q['passed'] and q['action']=='window' and q['CSV_consistency_checked'] and q['consumed_stats_unchanged'] and n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'],'Only sealed passed window checker/native may be consumed')
    need(bind(q['native_receipt'])==stat(N),'Checker must bind this actual native receipt');rp=bind(q['source_run']);run=read(rp['path']);anchor=float(run['actual_source_time_from_loader']);completion=bind(n['completion']);done=read(completion['path'])
    need(done['stage']=='upl_c08_causal_native_r1' and done['samples']==90 and done['completed_steps']==4360000,'Literal causal90 native profile required');folder=Path(completion['path']).parent
    inputs=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(schema.__file__),Q,N)]+[rp,completion,bind(n['metadata']),bind(q['trace']),bind(q['totals'])]
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):inputs.append(bind(next(e for e in n['outputs'] if Path(e['path']).resolve()==(folder/leaf).resolve())))
    data,extrema,raw_rows,sample_rows=stream_stages(Path(q['trace']['path']),anchor);need(raw_rows==q['observations']['rows'],'Actual single-pass row identity differs from sealed checker');total=totals(Path(q['totals']['path']),anchor);points=native(folder,anchor);figures(data,total,points)
    final={str(i):next(r for r in reversed(total) if r['native_id']==i) for i in IDS};need(all(stat(e['path'])==e for e in inputs),'Bound source changed during scientific extraction')
    result=dict(stage=TAG,passed=True,analysis_completed=True,physical_acceptance=False,consumed=inputs,outputs=[stat(p) for p in FILES.values()],consumed_stats_unchanged=True,main_CSV_stream_passes=1,raw_main_rows=raw_rows,sampled_ID_step_rows=sample_rows,native_selected_points=len(points),full_step_totals_rows=len(total),sampled_extrema=extrema,full_step_final_totals=final,actual_source_time_s=anchor,figures_are_scientific_observations_not_physical_acceptance=True,limitations=['All stage x coordinates use their recorded step_start_s; native points use actual saved clocks. No phase time shift/regridding/filtering.','RHS Pre then pressure half update then Pre material/plane, then Cor RHS then Cor material/plane then full pressure update/ponding. Cor return cannot cause its already formed RHS; Pre return may affect Cor force.','Five instantaneous pressure terms preserve the actual FS defect branch. No sparse integration is presented as a full-step pressure budget.','Only Totals contains every actual full Cor/material/plane update. Endpoint differences retain original budgets and base_trace_changes; they are not sums of sampled rows.','Trace drop/(3K) is a constitutive trace-reduction diagnostic, not a complete independently measured plastic-volume history.','Actual plane hits and delta-v, including zeros, are retained. No reaction/work/J closure or contact cause is inferred.','Three tracked IDs and conditional event ordering do not establish a global instability cause.'],solver_invocations=0,decoder_invocations=0,checker_invocations=0,SHA_scans=0)
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(passed=True,check=str(CHECK),main_rows=raw_rows,ID_step_rows=sample_rows)),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one offline scientific extraction');main()
