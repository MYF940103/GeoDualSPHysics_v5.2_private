"""Three-material-ID stage-trace comparison: epsilon .2, exponent 2.55 versus 3."""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import upl_c08_as05_trace_compare_r1 as old

T=old.T;TAG='upl_c08_asn3_trace_compare_r1';PREFIX=T/'figures'/TAG
BASE=old.JOBS[0];NEW='upl_c08_asn3_window_GPU_r1'
NEW_CHECK=T/'logs/upl_c08_stage_trace_asn3_window_r1.check.json'
BASE_ANALYSIS=T/'figures/upl_c08_as05_trace_compare_r1.check.json'
need,stat,bind=old.need,old.stat,old.bind

def xml_physics(run,exponent):
    root=ET.parse(bind(run['input_xml'])['path']).getroot();pars={x.get('key'):x for x in root.findall('execution/parameters/parameter')}
    need(float(pars['ArtificialStress'].get('value'))==1 and np.float32(pars['ArtificialStressCoef'].get('value'))==np.float32(.2) and np.float32(pars['ArtificialStressExp'].get('value'))==np.float32(exponent),'Actual XML must independently establish AS .2 and its stated exponent')
    # Only the controlled exponent is normalized in this in-memory comparison.
    pars['ArtificialStressExp'].set('value','2.55')
    return tuple(old.physics(root.find('execution/'+name)) for name in ('special','parameters'))

def extrema(steps,job,scopes):
    rows=[]
    for identity in old.trace.IDS:
        own=steps[steps.native_id==identity]
        for scope in scopes:
            d=own if scope=='all_recorded_starts' else own[own.nstep>=old.trace.DENSE] if scope=='dense_all_steps' else own[own.nstep<old.trace.DENSE]
            for channel in old.PRESSURES:
                v=d[channel].to_numpy();i,j=int(np.argmin(v)),int(np.argmax(v))
                rows.append(dict(group=job,epsilon=.2,native_id=identity,scope=scope,channel=channel,samples=len(d),min_Pa=float(v[i]),max_Pa=float(v[j]),recorded_sample_RMS_Pa=float(np.sqrt(np.mean(v*v))),min_nstep=int(d.iloc[i].nstep),max_nstep=int(d.iloc[j].nstep),min_actual_tau_s=float(d.iloc[i].tau_s),max_actual_tau_s=float(d.iloc[j].tau_s)))
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root must review before this one offline analysis')
    need(not list(PREFIX.parent.glob(TAG+'*')),'Fresh output prefix required');dest=Path(str(PREFIX)+'.check.json');files=[];before=[]
    result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0)
    try:
        cached=old.read(BASE_ANALYSIS);need(cached['passed'] and cached['analysis_completed'] and cached['original_cast_and_sequence_checks_reused_not_rerun'],'Passed existing baseline trace analysis required')
        entries={Path(e['path']).name:e for e in cached['files']};tables={}
        for leaf in ('steps','extrema','frequency_windows','growth','RHS_windows'):
            e=bind(entries['upl_c08_as05_trace_compare_r1_'+leaf+'.csv']);d=pd.read_csv(e['path'],float_precision='round_trip');tables[leaf]=d[d.group==BASE].copy();before.append(e)
        rp=T/'logs'/(BASE+'.run.json');r=old.read(rp);re=stat(rp)
        need(re in cached['consumed'] and r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==old.trace.END and r['saved_frames']==66 and r['consumed_stats_unchanged'],'Cached baseline must bind its actual completed run')
        baseline_physics=xml_physics(r,2.55);newrun=old.read(T/'logs'/(NEW+'.run.json'));newphysics=xml_physics(newrun,3)
        need(r['program']==newrun['program'] and r['source_build']==newrun['source_build'] and r['source_pre_file']==newrun['source_pre_file'] and baseline_physics==newphysics,'Same program/PRE and actual XML physics except exponent required')
        # Sole read of the NEW full CSV. This pure helper reuses its already-passed algebra check.
        g=old.load(NEW,.2,NEW_CHECK);a=tables['steps'].sort_values(['nstep','native_id']);b=g['steps'];anchor=float(cached['source_actual_time_s'])
        need(anchor==g['anchor']==float(r['actual_source_time_from_loader']) and len(a)==len(b)==90000,'Same genuine PRE source clock / three material histories required')
        need(np.array_equal(a[['nstep','native_id']],b[['nstep','native_id']]) and old.same64(a.step_start_s,b.step_start_s) and old.same64(a.tau_s,b.tau_s),'Exact actual sampled clocks/steps/IDs required; no interpolation')
        before += [stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(old.__file__),stat(old.trace.__file__),stat(BASE_ANALYSIS),re,r['input_xml']]+g['before']
        ex=pd.concat([tables['extrema'],extrema(a,BASE,('startup_recorded_before_dense',)),extrema(b,NEW,('all_recorded_starts','startup_recorded_before_dense','dense_all_steps'))],ignore_index=True)
        freq=[];growth=[]
        for identity in old.trace.IDS:
            f,w=old.frequencies(b[b.native_id==identity],identity,NEW);freq.extend(f);growth.append(w)
        fw=pd.concat([tables['frequency_windows'],pd.DataFrame(freq)],ignore_index=True)
        for identity in old.trace.IDS:
            x=fw[(fw.group==BASE)&(fw.native_id==identity)];y=fw[(fw.group==NEW)&(fw.native_id==identity)]
            for key in ('requested_start_s','requested_end_s','first_actual_tau_s','last_actual_tau_s','actual_center_tau_s','actual_mean_dt_s'):
                need(old.same64(x[key],y[key]),'Frequency windows must use identical actual clocks: '+key)
            need(np.array_equal(x.samples,y.samples),'Frequency windows sample counts differ')
        outputs=dict(extrema=ex,frequency_windows=fw,growth=pd.concat([tables['growth'],pd.DataFrame(growth)],ignore_index=True),RHS_windows=pd.concat([tables['RHS_windows'],pd.DataFrame(g['RHS_windows'])],ignore_index=True),new_initial_events=g['initial'],new_extra_ponding=g['extras'])
        for leaf,rows in outputs.items():
            p=Path(str(PREFIX)+'_'+leaf+'.csv');old.export(p,rows);files.append(p)
        plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axes=plt.subplots(3,2,figsize=(15,10),layout='constrained')
        for row,identity in enumerate(old.trace.IDS):
            for col,dense in enumerate((False,True)):
                ax=axes[row,col]
                for data,exp,color in ((a,2.55,'C0'),(b,3,'C1')):
                    d=data[data.native_id==identity];d=d[d.nstep>=old.trace.DENSE] if dense else d
                    channels=(('p_full_prepond_Pa','-'),('p_full_postpond_Pa','--'))+((('p_half_Pa',':'),) if dense else ())
                    for name,style in channels:ax.plot(d.tau_s,d[name]/1000,style,color=color,lw=.7,label='n='+str(exp)+' '+name)
                ax.set(title=str(identity)+(' dense every step' if dense else ' actual early40-step/dense sampling'),xlabel='Actual step-start tau [s]',ylabel='Raw total p [kPa]');ax.grid(alpha=.25);ax.legend(fontsize=5)
        fig.suptitle('Three fixed material IDs: epsilon .2, exponent 2.55 vs 3; raw stage data, no re-timing/filter/clipping')
        p=Path(str(PREFIX)+'_pressure.png');fig.savefig(p);plt.close(fig);files.append(p)
        need(all(stat(e['path'])==e for e in before),'Closed input/helper changed during analysis')
        result.update(passed=True,analysis_completed=True,groups=[BASE,NEW],source_actual_time_s=anchor,new_raw_CSV_passes=1,baseline_raw_CSV_passes=0,baseline_derived_steps_cache_used=True,original_algebra_checks_reused_not_rerun=True,three_fixed_native_IDs=list(old.trace.IDS),sampled_steps_per_ID_per_group=30000,dense_steps_per_ID_per_group=24000,new_extra_ponding_rows=len(g['extras']),all_true_extra_events_preserved_in_new_extra_table=True,FFT_field='full pressure before ponding',FFT_method='same actual narrow windows; demean then Hann largest nonzero rFFT bin; no padding',RMS_growth_not_fitted_eigenvalue=True,startup_RMS_is_sample_RMS_not_time_weighted=True,no_cross_parameter_accuracy_gate=True,visual_QA_pending=True)
    except Exception as error:result['first_failure']=str(error)
    result.update(consumed=before,files=[stat(p) for p in files if p.exists()])
    with dest.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],check=str(dest),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
