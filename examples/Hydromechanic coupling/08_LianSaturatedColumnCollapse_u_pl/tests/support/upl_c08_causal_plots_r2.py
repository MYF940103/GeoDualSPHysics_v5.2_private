"""Plot-only repair from sealed scientific CSVs; no raw telemetry, typed data or model recomputation."""
import argparse,csv,json
from pathlib import Path
import upl_c08_causal_physics_r1 as old

np,plt=old.np,old.plt;T,L,F=old.T,old.L,old.F;IDS,TERMS,DENSE,PLOT=old.IDS,old.TERMS,old.DENSE,old.PLOT
need,read,stat,bind=old.need,old.read,old.stat,old.bind;TAG='upl_c08_causal_plots_r2'
OUT={k:F/(TAG+'_'+k+'.png') for k in ('history','dense')};CHECK=L/(TAG+'.check.json')

def main():
    need(not any(p.exists() for p in (*OUT.values(),CHECK)),'Existing complete/partial r2 plots protected')
    q=read(old.CHECK);need(q['passed'] and q['analysis_completed'] and q['consumed_stats_unchanged'],'Sealed scientific extraction required')
    inputs=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(old.__file__),old.CHECK)]
    for key in ('stages','totals','native'):inputs.append(bind(next(e for e in q['outputs'] if Path(e['path']).resolve()==old.FILES[key].resolve())))
    data={i:[] for i in IDS}
    with old.FILES['stages'].open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):data[int(r['native_id'])].append(tuple(float(r[k]) for k in PLOT))
    data={i:np.asarray(v,dtype=np.float64) for i,v in data.items()};index={k:j for j,k in enumerate(PLOT)}
    def table(path):
        with path.open(encoding='utf-8-sig',newline='') as f:return [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
    totals,native=table(old.FILES['totals']),table(old.FILES['native']);dense={};values=[]
    for identity in IDS:
        for column,(low,high) in enumerate(DENSE):
            a=data[identity];b=a[(a[:,index['tau_s']]>=low)&(a[:,index['tau_s']]<high)];need(len(b)>0,'Missing actual dense-window samples');dense[identity,column]=b
            values.append(b[:,[index['pre_trace_drop_over_3K'],index['cor_trace_drop_over_3K']]].reshape(-1))
    values=np.concatenate(values);need(np.isfinite(values).all(),'Nonfinite sealed trace-drop values');low,high=float(values.min()),float(values.max());span=high-low
    margin=.05*(span if span else max(abs(low),np.finfo(float).eps));limits=(low-margin,high+margin)
    fig,axes=plt.subplots(3,4,figsize=(19,10),constrained_layout=True)
    for row,identity in enumerate(IDS):
        a=data[identity];x=a[:,index['tau_s']];n=[r for r in native if r['native_id']==identity];ax=axes[row,0]
        for key,label in (('p_half_Pa','half'),('p_full_raw_Pa','full before ponding'),('p_pond_Pa','after ponding')):ax.plot(x,a[:,index[key]]/1000.,label=label,lw=.8)
        ax.plot([r['tau_s'] for r in n],[r['p_Pa']/1000. for r in n],'.',ms=2,color='k',label='native saved');ax.set(ylabel='ID'+str(identity)+' pressure [kPa]');ax=axes[row,1]
        for key in TERMS:ax.plot(x,a[:,index['cor_'+key+'_Pa_s']]/1000.,label=key,lw=.7)
        ax.plot(x,a[:,index['cor_RHS_logged_Pa_s']]/1000.,color='k',label='actual total RHS',lw=1.,zorder=5);ax.set_yscale('symlog',linthresh=1.);ax.set(ylabel='Cor RHS [kPa/s]')
        ax=axes[row,2];ax.plot(x,a[:,index['Jnew']]-1.,label='stage Jnew-1',color='C2',lw=.8);ax.plot([r['tau_s'] for r in n],[r['J']-1. for r in n],'.',color='k',ms=2,label='native J-1');ax.set(ylabel='Jnew-1');twin=ax.twinx()
        twin.plot(x,a[:,index['cor_Ireturned_Pa']]/1000.,color='C3',label='Cor returned Ieff',lw=.8);twin.plot([r['tau_s'] for r in n],[r['Ieff_Pa']/1000. for r in n],'.',color='C4',ms=2,label='native Ieff');twin.set_ylabel('Effective stress trace [kPa]');twin.legend(fontsize=6,loc='lower right')
        ax=axes[row,3];r=[v for v in totals if v['native_id']==identity];tx=[v['tau_step_start_s'] for v in r]
        for key,label in (('sum_cor_dt_theta','sum dt theta'),('sum_cor_log_Jnew_over_Jbase','sum log Jnew/Jbase'),('sum_cor_dt_rsigma_trace_Pa_over_3K','sum dt trace(rate)/(3K)'),('sum_cor_trial_minus_returned_I_Pa_over_3K','sum return trace drop/(3K)')):ax.plot(tx,[v[key] for v in r],label=label,lw=1.1)
        ax.set(ylabel='Full-step cumulative [dimensionless]',title='Direct plane hits:'+str(int(r[-1]['all_plane_hits'])))
        for ax in axes[row]:
            for lo,hi in DENSE:ax.axvspan(lo,hi,color='0.85',alpha=.5)
            ax.grid(alpha=.25);ax.set_xlabel('Recorded tau [s]');ax.legend(fontsize=6)
    fig.suptitle('Three-ID observations: sampled RHS and full-step Totals; not causal proof');fig.savefig(OUT['history'],dpi=170);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(14,10),constrained_layout=True)
    for row,identity in enumerate(IDS):
        for column in range(2):
            b=dense[identity,column];x=b[:,index['tau_s']];ax=axes[row,column]
            for key,label,color in (('p_half_Pa','half','0.55'),('p_full_raw_Pa','full raw','C0'),('p_pond_Pa','ponded','C2')):ax.plot(x,b[:,index[key]]/1000.,color=color,label=label,lw=.8)
            twin=ax.twinx()
            for key,label,style in (('pre_trace_drop_over_3K','Pre return drop/(3K)',':'),('cor_trace_drop_over_3K','Cor return drop/(3K)','--')):twin.plot(x,b[:,index[key]],style,label=label,lw=.7,alpha=.8)
            twin.set_ylim(*limits);twin.set_ylabel('Return trace-drop strain; one common scale');hit=np.any(b[:,[index[p+'_plane_hit_'+c] for p in ('pre','cor') for c in ('x','z')]]>0,axis=1)
            if np.any(hit):ax.plot(x[hit],b[hit,index['p_full_raw_Pa']]/1000.,'kx',label='sampled plane hit',ms=3)
            ax.set(title='ID'+str(identity)+'; sampled plane-hit rows='+str(int(hit.sum())),xlabel='Actual step-start tau [s]',ylabel='Pressure [kPa]');ax.grid(alpha=.25);h,l=ax.get_legend_handles_labels();h2,l2=twin.get_legend_handles_labels();ax.legend(h+h2,l+l2,fontsize=6,loc='best');ax.ticklabel_format(axis='x',style='plain',useOffset=False)
    fig.suptitle('Dense windows: all actual trace-drop points, common scale; no filtering or clipping');fig.savefig(OUT['dense'],dpi=170);plt.close(fig)
    need(all(stat(e['path'])==e for e in inputs),'Sealed derived CSV/source changed during rendering')
    result=dict(stage=TAG,passed=True,plot_only=True,physical_acceptance=False,source_physics=stat(old.CHECK),consumed=inputs,outputs=[stat(p) for p in OUT.values()],consumed_stats_unchanged=True,dense_actual_return_drop_min=low,dense_actual_return_drop_max=high,dense_margin=margin,dense_common_right_limits=list(limits),dense_return_drop_points=len(values),identical_right_limits_all_six_panels=True,constant_range_fallback=(span==0),data_filtered=False,data_clipped=False,data_changed_to_zero=False,CSVs_copied=False,raw_telemetry_passes=0,typed_data_passes=0,mathematics_recomputed=False,solver_invocations=0,decoder_invocations=0,checker_invocations=0,SHA_scans=0)
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(passed=True,check=str(CHECK),common_return_drop_limits=limits)),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one plot-only invocation');main()
