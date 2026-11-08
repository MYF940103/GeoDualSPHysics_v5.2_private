"""Finish only the failed clustering plot; retain the original exit1 and complete CSV."""
import argparse,json,struct
from pathlib import Path
import upl_c08_clustering_r1 as old

c,T,plt,np=old.c,old.T,old.plt,old.np
TAG='upl_c08_clustering_plot_r2';CHECK=T/'logs'/(TAG+'.check.json');FAILURE=T/'logs/upl_c08_clustering_r1.failure.json';CSV=Path(str(old.PREFIX)+'_history.csv');PNG=Path(str(old.PREFIX)+'_neighbors.png')
COHORTS=('all_soil','kappa_ge_0p1f','kappa_lt_0p1f','geometric_interior','FS23_or_within_kernelR','within_kernelR_of_fixed_B')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();c.need(a.execution_authorized,'Root full-read before one derived plot repair');c.need(not CHECK.exists() and not PNG.exists() and CSV.is_file(),'Fresh plot/r2 receipt and retained CSV required')
    failure=c.read(FAILURE);c.need(failure['execution_tool_exit_code']==1 and failure['exception_type']=='KeyError' and failure['exception_key']=='tau' and failure['traceback_source_line']==87 and not failure['original_Win32_handle_exit_captured'] and not failure['original_final_stat_verification_executed'] and not failure['old_success_receipt_invented'],'Actual original failed observation must remain explicit')
    c.need(c.bind(failure['source_stat_at_failure_audit'])==c.stat(old.__file__) and c.bind(failure['retained_history_csv'])==c.stat(CSV),'Original failed script/complete CSV identity changed')
    comparison=c.read(c.CHECK);c.need(comparison['passed'] and comparison['clock_and_steps_exact'] and comparison['actual_matched_samples']==66,'Sealed epsilon comparison required');first=old.formal();second=c.load(c.SPECS[1]);second.update(frames=66,plot_parts=(65,));groups=(first,second);by_label={g['label']:g for g in groups}
    pp=T/'logs/upl_c08_stage_trace_window_GPU_r1.prefix_r1.check.json';prefix=c.read(pp);c.need(prefix['passed'] and prefix['actual_common_frames']==66 and prefix['all22_and_actual_time_payload_byte_exact'] and prefix['signed_clock_header_and_rows_byte_exact'] and prefix['layout_byte_exact'] and prefix['consumed_stats_unchanged'] and prefix['new_original_header']==[6805,22,66] and prefix['old_original_header']==[6805,22,300] and not prefix['headers_rewritten'],'Original66/300 prefix proof differs')
    c.need(any(Path(e['path']).samefile(first['native']/'typed22.bin') for e in prefix['consumed']) and first['run']['source_pre_file']==second['run']['source_pre_file'] and first['done']['source_actual_time_s']==second['done']['source_actual_time_s'],'Prefix/formal source or shared PRE/clock differs')
    before=[c.stat(__file__),c.stat(T/'notes'/(TAG+'.md')),c.stat(FAILURE),c.bind(failure['source_stat_at_failure_audit']),c.bind(failure['retained_history_csv']),c.stat(pp),c.stat(c.CHECK),c.bind(next(e for e in comparison['consumed'] if Path(e['path']).samefile(c.__file__)))]+[c.bind(e) for e in prefix['consumed']]+first['before']+second['before']
    rows=c.table(CSV);c.need(len(rows)==2196,'Retained CSV must have366 times six cohorts');indexed={}
    for row in rows:
        label=row['group'];c.need(label in by_label and row['cohort'] in COHORTS,'Unknown retained CSV group/cohort');g=by_label[label];part=int(row['part']);c.need(0<=part<g['frames'],'CSV part outside genuine group extent');clock=g['clocks'][part];time=float(clock['time_s']);step=int(clock['completed_step']);key=(label,part,row['cohort'])
        c.need(key not in indexed and float(row['epsilon'])==g['epsilon'] and float(row['time_s'])==time and float(row['tau_s'])==time-g['done']['source_actual_time_s'] and int(row['completed_step'])==step==4000000+4000*(part+1) and 0<=int(row['soil_count'])<=5000,'Retained CSV duplicate/material-count/actual clock/Step differs')
        for k,v in row.items():
            if k not in ('group','cohort') and v!='':c.need(np.isfinite(float(v)),'Nonfinite retained derived CSV '+k)
        indexed[key]=row
    for g in groups:
        for part in range(g['frames']):
            c.need(all((g['label'],part,k) in indexed for k in COHORTS),'Missing actual CSV cohort');c.need(int(indexed[(g['label'],part,'all_soil')]['soil_count'])==5000 and sum(int(indexed[(g['label'],part,k)]['soil_count']) for k in ('kappa_ge_0p1f','kappa_lt_0p1f'))==5000,'Original5000-material cohort cardinalities differ')
    pictures=[];verified_cells=0
    for g in groups:
        with (g['native']/'typed22.bin').open('rb') as f:
            c.need(struct.unpack('<III',f.read(12))==(6805,22,g['frames']),'Original full/window header extent changed')
            for part in g['plot_parts']:
                f.seek(12+part*g['dtype'].itemsize);raw=f.read(g['dtype'].itemsize);c.need(len(raw)==g['dtype'].itemsize,'Short selected native record');frame=np.frombuffer(raw,dtype=g['dtype'],count=1)[0];time,tau,step=c.inspect(frame,g,part);q=old.measures(frame);context=dict(group=g['label'],epsilon=g['epsilon'],part=part,time_s=time,tau_s=tau,completed_step=step)
                for calculated in old.summarize(q,context):
                    retained=indexed[(g['label'],part,calculated['cohort'])];c.need(set(retained)==set(calculated),'Original summary columns differ')
                    for k,v in calculated.items():
                        same=retained[k]=='' if v is None else retained[k]==v if isinstance(v,str) else float(retained[k])==float(v);c.need(same,'Selected raw-state CSV replay differs: '+str((g['label'],part,k)));verified_cells+=1
                pictures.append(dict(**context,**{k:q[k].copy() for k in ('x','fixed','nn','pairs','kappa','surface','bulk','degree')}))
    c.need(len(pictures)==5,'Only the original five plot records may be read')
    # Mechanical copy of r1 plotting; the sole label fix is q['tau_s'].
    plt.rcParams.update({'font.size':8,'figure.dpi':170});fig,axes=plt.subplots(2,3,figsize=(17,10),sharex=True,sharey=True,layout='constrained');nn=np.concatenate([q['nn'] for q in pictures]);xy=np.concatenate([q['x'] for q in pictures]);norm=old.Normalize(float(nn.min()),float(nn.max()),clip=False);limits=(float(xy[:,0].min()-2*old.DP),float(xy[:,0].max()+2*old.DP),float(xy[:,1].min()-2*old.DP),float(xy[:,1].max()+2*old.DP))
    for ax,q in zip(axes.ravel(),pictures):
        x=q['x'];fixed=q['fixed'];surface=q['surface'];high=q['kappa']>=old.KAPPA;interior_sparse=q['bulk']&(q['degree']<4);ax.scatter(fixed[:,0],fixed[:,1],s=3,c='.7',marker='s',linewidths=0,zorder=0)
        if len(q['pairs']):ax.add_collection(old.LineCollection(x[q['pairs']],colors='red',linewidths=.55,alpha=.65,zorder=2))
        for mask,marker in ((~surface,'o'),(surface,'^')):ax.scatter(x[mask,0],x[mask,1],c=q['nn'][mask],norm=norm,cmap='viridis',s=7,marker=marker,linewidths=0,zorder=1)
        ax.scatter(x[high,0],x[high,1],s=10,facecolors='none',edgecolors='.2',linewidths=.2,zorder=3);ax.scatter(x[interior_sparse,0],x[interior_sparse,1],s=22,marker='x',c='black',linewidths=.7,zorder=4);ax.set(xlim=limits[:2],ylim=limits[2:],xlabel='x [m]',ylabel='z [m]',title='epsilon=%g, actual tau=%.12g s'%(q['epsilon'],q['tau_s']));ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.15)
    axes.ravel()[-1].axis('off');handles=[old.Line2D([],[],marker='^',ls='',c='.3',label='Native soil FS2/3'),old.Line2D([],[],marker='s',ls='',c='.7',label='Retained fixed markers'),old.Line2D([],[],c='red',label='Unique soil pairs r<.7dp'),old.Line2D([],[],marker='o',ls='',mfc='none',mec='.2',label='Current kappa>=.1f'),old.Line2D([],[],marker='x',ls='',c='black',label='Interior soil degree<4 within1.5dp')];axes.ravel()[-1].legend(handles=handles,loc='upper left',fontsize=8);fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=axes.ravel()[:5].tolist(),label='Raw nearest-other distance / dp; complete five-state range',shrink=.7)
    fig.suptitle('Fixed5000 material IDs, full-domain ROI; raw neighbor geometry, no smoothing or cause claim\nCompression/shear/FS effects remain confounders; sparse proxy is not an identified internal crack');fig.savefig(PNG);plt.close(fig);c.need(all(c.stat(e['path'])==e for e in before),'Original CSV/script or sealed source/helper changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,plot_completed=True,original_tool_session=failure['execution_tool_session_id'],original_tool_exit_code=1,original_Win32_exit_not_invented=True,original_started_time_unknown=True,original_r1_script_unchanged=True,original_r1_success_receipt_not_created=True,original_final_stat_verification_was_not_executed=True,current_source_bindings_revalidated=True,retained_CSV_rows=2196,retained_actual_times=366,retained_cohorts_per_time=6,retained_all_soil_count_per_time=5000,CSV_has_no_per_ID_cohort_list=True,all_frame_ID_evidence_from_original_native_receipts=True,selected_records_reread=5,selected_records_all6805_ID_and22finite_checks=True,selected_replayed_cohort_rows=30,selected_CSV_cells_exact=verified_cells,remaining361_geometry_states_not_recomputed=True,original_CSV_rewritten=False,original_failed_script_rewritten=False,duplicate_epsilon0p2_window_payload_read=False,plot_math_and_style_unchanged=True,label_fix='tau -> tau_s',selected_plot_states=[{k:q[k] for k in ('group','part','time_s','tau_s')} for q in pictures],plot_common_window_xz_m=list(limits),physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,files=[c.stat(CSV),c.stat(PNG)])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('C08_CLUSTERING_PLOT_FINISHED',CHECK,flush=True)

if __name__=='__main__':main()
