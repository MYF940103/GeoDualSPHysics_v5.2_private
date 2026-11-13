"""Display only the sealed AS.3 CSV as three readable 2x2 particle figures."""
import argparse,csv,json
from pathlib import Path
T=Path(__file__).resolve().parents[1]
CSV=T/'figures/c08_h18_wend_a03_partial_review_r1_fields.csv'
SOURCE=T/'logs/c08_h18_wend_a03_partial_review_r1.check.json'
TAG='c08_h18_wend_a03_display_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')
FIELDS=(('p_Pa','Pore pressure p [kPa]',.001),('native_p_minus_fixedP0_Pa','Native p - fixed P0 [kPa]\nNot paper-defined excess',.001),('kappa','Plastic history kappa [-]',1.),('J','Volume ratio J [-]',1.))
def need(ok,text):
    if not ok:raise RuntimeError(text)
def stat(path):
    p=Path(path);s=p.stat();return dict(path=str(p.resolve()),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    need(a.execution_authorized,'Root full-read and one explicit display action required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing display/partial artifacts protected')
    before=[stat(q) for q in (Path(__file__),T/'notes/c08_h18_field_display_r1.md',SOURCE,CSV)];made=[]
    result=dict(stage='c08_h18_field_display_r1',display_complete=False,physical_acceptance=False,receiver_complete=False,whole_run_passed=False,source_CSV=str(CSV),new_data_CSVs=0,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0)
    try:
        d=json.loads(SOURCE.read_text(encoding='utf-8-sig'))
        need(d['analysis_complete'] and d['saved_prefix_native_qualified'] and d['actual_saved_records']==90 and not d['receiver_complete'] and not d['whole_run_passed'] and d['consumed_stats_unchanged'],'Only the sealed failed90 AS.3 analysis is supported')
        entry=[q for q in d['files'] if Path(q['path']).samefile(CSV)]
        need(len(entry)==1 and stat(CSV)==entry[0],'Original analysis CSV binding changed')
        with CSV.open(encoding='utf-8-sig',newline='') as f:
            r=csv.DictReader(f);rows=list(r);header=r.fieldnames
        need(header==['part','time_s','tau_s','native_id','x_m','z_m','p_Pa','native_p_minus_fixedP0_Pa','kappa','J'] and len(rows)==15000,'Literal plotted CSV shape differs')
        import numpy as np
        import matplotlib;matplotlib.use('Agg')
        from matplotlib import pyplot as plt
        from matplotlib.colors import Normalize,TwoSlopeNorm
        values={k:np.array([float(q[k]) for q in rows]) for k in header}
        need(all(np.isfinite(v).all() for v in values.values()),'Nonfinite existing CSV value')
        parts=sorted({int(q['part']) for q in rows});need(parts==[30,60,89],'Actual three saved snapshots differ')
        limits={key:(float(values[key].min()*scale),float(values[key].max()*scale)) for key,_,scale in FIELDS}
        need(all(lo<hi for lo,hi in limits.values()),'Expected actual nonconstant field ranges differ')
        xlim=(float(values['x_m'].min()-.04),float(values['x_m'].max()+.04));zlim=(float(values['z_m'].min()-.04),float(values['z_m'].max()+.04));snapshots=[]
        for part in parts:
            mask=values['part']==part;rr=[q for q in rows if int(q['part'])==part]
            need(len(rr)==5000 and sorted(int(q['native_id']) for q in rr)==list(range(2060,7060)),'Actual selected soil-ID coverage differs')
            times={float(q['time_s']) for q in rr};taus={float(q['tau_s']) for q in rr}
            need(len(times)==len(taus)==1,'Mixed actual clocks in a selected snapshot')
            time=next(iter(times));tau=next(iter(taus));need(abs(time-d['actual_source_time_s']-tau)<=1e-14,'Actual source-relative CSV clock differs')
            fig,axes=plt.subplots(2,2,figsize=(11.6,7.4),layout='constrained')
            fig.suptitle('C08 psi=0 deg | Wendland h/dp=1.8 | AS=0.3, n=3.825\n'+f'Part {part}: actual t={time:.9f} s, tau={tau:.9f} s',fontsize=12)
            for ax,(key,label,scale) in zip(axes.flat,FIELDS):
                lo,hi=limits[key];centered=key in ('p_Pa','native_p_minus_fixedP0_Pa') and lo<0<hi
                norm=TwoSlopeNorm(vmin=lo,vcenter=0.,vmax=hi) if centered else Normalize(vmin=lo,vmax=hi,clip=False)
                im=ax.scatter(values['x_m'][mask],values['z_m'][mask],c=values[key][mask]*scale,norm=norm,cmap='coolwarm' if key in ('p_Pa','native_p_minus_fixedP0_Pa') else 'viridis',s=6,edgecolors='none',rasterized=True)
                ax.set(xlim=xlim,ylim=zlim,xlabel='x [m]',ylabel='z [m]',title=label);ax.set_aspect('equal');ax.tick_params(labelsize=9)
                ticks=np.unique(np.r_[np.linspace(lo,hi,5),0.]) if centered else np.linspace(lo,hi,5)
                bar=fig.colorbar(im,ax=ax,ticks=ticks,fraction=.046,pad=.025);bar.set_ticks(ticks,labels=[f'{v:.4g}' for v in ticks]);bar.ax.tick_params(labelsize=8)
            dest=Path(str(PREFIX)+f'_part{part:04d}.png');fig.savefig(dest,dpi=180);plt.close(fig);made.append(stat(dest));snapshots.append(dict(part=part,time_s=time,tau_s=tau,soil_points=5000))
        need(all(stat(q['path'])==q for q in before),'Sealed inputs changed while drawing')
        result.update(display_complete=True,all_three_snapshots=snapshots,shared_display_ranges=limits,pressure_display_units='kPa',CSV_pressure_units='Pa',spatial_limits_m=dict(x=xlim,z=zlim),full_selected_state_extrema_used=True,zero_centered_pressure_if_crosses_zero=True,no_smoothing_clipping_refitting=True,existing_figures_unchanged=True,visual_QA_pending=True)
    except Exception as error:
        result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        result.update(consumed=before,figures=made)
        with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
