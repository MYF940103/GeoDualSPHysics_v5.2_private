"""Plot two original dense-time slices from passed derived steps only; no trace/native reread."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
T=Path(__file__).resolve().parents[1];TAG='upl_c08_stage_trace_zoom_r1'
SOURCE_CHECK=T/'figures/upl_c08_stage_trace_terms_r2_window.check.json'
STEPS=T/'figures/upl_c08_stage_trace_terms_r2_window_steps.csv'
IDS=(5809,4956,4959);INTERVALS=((.6200,.6205),(.6403,.6407))
TERMS=('compression','LP','interior_defect','FS_Ace_L','divAce','k_chain')

def need(ok,message):
    if not ok:raise RuntimeError(message)

def stat(path):
    p=Path(path).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one offline zoom')
    prefix=T/'figures'/TAG;check=Path(str(prefix)+'.check.json');need(not list(prefix.parent.glob(prefix.name+'*')),'Existing complete/partial zoom outputs preserved')
    before=[stat(p) for p in (SOURCE_CHECK,STEPS,Path(__file__),T/'notes'/(TAG+'.md'),T/'notes/upl_c08_stage_trace_window_science_r1.md')]
    source=json.loads(SOURCE_CHECK.read_text(encoding='utf-8'));need(source['passed'] and source['analysis_completed'] and source['profile']=='window' and source['all_original_events_retained'] and source['stage_time_axis_is_actual_context_step_start_not_shifted_half_time'],'Passed original window terms check required')
    need(next(e for e in source['files'] if Path(e['path']).resolve()==STEPS.resolve())==before[1],'Closed derived steps binding differs')
    files=[];result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,terms_invocations=0,raw_trace_or_native_read=False,FFT_computed=False,interpolation=False,time_shift=False,filtering=False,consumed=before)
    try:
        data=pd.read_csv(STEPS,float_precision='round_trip');selected=[];observations=[]
        for lo,hi in INTERVALS:
            frame=data[(data.tau_s>=lo)&(data.tau_s<=hi)&data.native_id.isin(IDS)].copy();reference=None
            for identity in IDS:
                rows=frame[frame.native_id==identity];need(len(rows)>=2,'Nonempty genuine dense samples required for every ID/interval')
                steps=rows.nstep.to_numpy();times=rows.tau_s.to_numpy();need(np.all(np.diff(steps)==1) and np.all(np.diff(times)>0),'Selected actual dense steps/clocks are not increasing consecutively')
                context=rows[['nstep','step_start_s','tau_s']].to_numpy();need(reference is None or np.array_equal(reference,context),'Three IDs do not share the original actual step clocks');reference=context
                dt=np.diff(times);observations.append(dict(native_id=identity,requested_tau_interval_s=[lo,hi],samples=len(rows),first_nstep=int(steps[0]),last_nstep=int(steps[-1]),first_actual_tau_s=float(times[0]),last_actual_tau_s=float(times[-1]),nominal_solver_dt_s=2.5e-6,actual_step_start_dt_min_s=float(dt.min()),actual_step_start_dt_max_s=float(dt.max()),actual_step_start_dt_mean_s=float(dt.mean())))
            frame.insert(0,'zoom_interval_s',format(lo,'.4f')+'..'+format(hi,'.4f'));selected.append(frame)
        export=pd.concat(selected,ignore_index=True);path=Path(str(prefix)+'_selected.csv');export.to_csv(path,index=False,mode='x',float_format='%.17g');files.append(path)
        plt.rcParams.update({'font.size':9,'figure.dpi':170})
        for channel in ('pressure','corrector_rhs'):
            fig,axes=plt.subplots(3,2,figsize=(15,10),layout='constrained',squeeze=False)
            for col,((lo,hi),frame) in enumerate(zip(INTERVALS,selected)):
                for row,identity in enumerate(IDS):
                    part=frame[frame.native_id==identity];x=part.tau_s.to_numpy();ax=axes[row,col]
                    if channel=='pressure':
                        for name,label,style in (('p_n_Pa','old p_n','-'),('p_half_Pa','predictor half','--'),('p_full_prepond_Pa','full before ponding',':'),('p_full_postpond_Pa','full after ponding','-.')):
                            y=part[name].to_numpy()/1000.;need(np.all(np.isfinite(y)),'Nonfinite selected pressure');ax.plot(x,y,style,lw=.9,marker='.',ms=2,label=label)
                        ax.set_ylabel('Raw total pressure [kPa]')
                    else:
                        for term in TERMS:
                            y=part['corrector_'+term+'_Pa_s'].to_numpy();need(np.all(np.isfinite(y)),'Nonfinite selected RHS');ax.plot(x,y,lw=.8,marker='.',ms=2,label=term)
                        y=part.corrector_value_double_Pa_s.to_numpy();need(np.all(np.isfinite(y)),'Nonfinite selected recorded RHS');ax.plot(x,y,'k--',lw=1,marker='.',ms=2,label='recorded value_double');ax.set_ylabel('Corrector RHS [Pa/s]')
                    ax.set_title(str(identity)+'; original tau '+format(lo,'.4f')+'..'+format(hi,'.4f')+' s');ax.set_xlabel('Actual context step-start tau [s]');ax.xaxis.set_major_formatter(FormatStrFormatter('%.6f'));ax.grid(alpha=.25);ax.legend(fontsize=6)
            fig.suptitle('Original samples, linear axes, no clipping/filtering/phase re-timing; lines only connect recorded points')
            path=Path(str(prefix)+'_'+channel+'.png');fig.savefig(path);plt.close(fig);files.append(path)
        need(all(stat(e['path'])==e for e in before),'Frozen derived inputs or author files changed')
        result.update(passed=True,analysis_completed=True,selected_rows=len(export),interval_observations=observations,actual_tau_retained=True,all_plotted_extrema_retained=True,stage_phases_share_recorded_context_clock=True,visual_QA_pending=True)
    except Exception as error:result['first_failure']=str(error)
    result['files']=[stat(p) for p in files if p.exists()]
    with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
