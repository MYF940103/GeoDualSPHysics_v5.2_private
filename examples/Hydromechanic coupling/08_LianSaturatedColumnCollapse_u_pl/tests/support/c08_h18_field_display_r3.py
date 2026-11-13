"""Display every actual snapshot from a sealed full or partial review CSV; no new data."""
import argparse,json,re,textwrap
from pathlib import Path
import c08_h18_compare_r2 as old

np,T,need,path,stat,read,table,bind=old.np,old.T,old.need,old.path,old.stat,old.read,old.table,old.bind
TAG='c08_h18_field_display_r3'
FIELDS=(('p_Pa','p_kPa','Pore pressure p [kPa]',.001),
        ('native_p_minus_fixedP0_Pa','native_p_minus_fixedP0_kPa','Native p - fixed P0 [kPa]\nNot paper-defined excess',.001),
        ('kappa','kappa','Plastic history kappa [-]',1.),('J','J','Volume ratio J [-]',1.))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Root must fully read this display adapter before one unique invocation')
    manifest=read(args.manifest)
    for key in ('tag','review_check','fields_csv','title'):need(key in manifest,'Missing display manifest key: '+key)
    tag=manifest['tag'];need(re.fullmatch(r'[A-Za-z0-9_]+',tag) and isinstance(manifest['title'],str) and manifest['title'].strip(),'Safe fresh tag and explicit title required')
    prefix=T/'figures'/tag;check=T/'logs'/(tag+'.check.json');need(not check.exists() and not list(prefix.parent.glob(tag+'*')),'Existing display or partial artifacts are protected')
    before=[stat(p) for p in (args.manifest,__file__,T/'notes'/(TAG+'.md'),old.__file__,manifest['review_check'],manifest['fields_csv'])];made=[]
    result=dict(stage=TAG,display_complete=False,physical_acceptance=False,winner_selected=False,prior_status_changed=False,new_data_CSVs=0,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0)
    try:
        prior=read(manifest['review_check']);csv_path=path(manifest['fields_csv'])
        need(prior.get('analysis_complete') is True and prior.get('consumed_stats_unchanged') is True,'Require an already completed, stat-sealed prior analysis')
        for entry in prior['consumed']:bind(entry)
        matches=[entry for entry in prior['files'] if path(entry['path'])==csv_path];need(len(matches)==1 and bind(matches[0])==stat(csv_path),'Requested fields CSV must be an unchanged output bound by that prior analysis')
        summaries=prior.get('receiver_summaries',[prior.get('receiver_summary')]);need(summaries and all(s is not None for s in summaries),'Require explicit prior receiver summaries, including their actual partial/full scope')
        scopes={s['tag']:dict(tag=s['tag'],source_partial=s['source_partial'],actual_samples=s['actual_samples'],actual_first_time_s=s['actual_first_time_s'],actual_end_time_s=s['actual_end_time_s'],runtime_observed=s['runtime_observed']) for s in summaries}
        need(len(scopes)==len(summaries),'Prior receiver tags must be unique')
        base_time=float(prior['source_actual_time_s'] if 'source_actual_time_s' in prior else prior['actual_source_time_s'])
        rows=table(csv_path);need(rows,'Sealed field CSV must be nonempty');required={'part','time_s','tau_s','native_id','x_m','z_m',*(field[0] for field in FIELDS)}
        need(required<=set(rows[0]),'Sealed fields CSV is missing original snapshot columns')
        values={key:np.array([float(row[key]) for row in rows]) for key in required}
        need(all(np.isfinite(v).all() for v in values.values()),'Nonfinite sealed field CSV value')
        groups={}
        for index,row in enumerate(rows):
            case=row.get('tag',next(iter(scopes)) if len(scopes)==1 else None);need(case in scopes,'Each CSV snapshot must identify an actual reviewed receiver')
            part=int(row['part']);need(float(row['part'])==part,'Literal integer snapshot part required');groups.setdefault((case,part),[]).append(index)
        ranges={display:(float(values[key].min()*scale),float(values[key].max()*scale)) for key,display,_,scale in FIELDS}
        color_ranges={key:((lo,hi) if lo<hi else (lo-max(abs(lo)*1e-6,1e-9),hi+max(abs(hi)*1e-6,1e-9))) for key,(lo,hi) in ranges.items()}
        xlim=(float(values['x_m'].min()-.04),float(values['x_m'].max()+.04));zlim=(float(values['z_m'].min()-.04),float(values['z_m'].max()+.04));snapshots=[]
        title='\n'.join(textwrap.fill(line,width=86) for line in manifest['title'].strip().splitlines())
        from matplotlib.colors import Normalize,TwoSlopeNorm
        for index,((case,part),indices) in enumerate(sorted(groups.items())):
            at=np.array(indices);ids=values['native_id'][at];times=np.unique(values['time_s'][at]);taus=np.unique(values['tau_s'][at])
            need(len(at)==5000 and np.array_equal(np.sort(ids),np.arange(2060,7060)),'Every actual snapshot must retain all5000 original soil IDs exactly once')
            need(len(times)==len(taus)==1,'Mixed actual saved clocks in one field snapshot');time,tau=float(times[0]),float(taus[0]);scope=scopes[case]
            need(scope['actual_first_time_s']<=time<=scope['actual_end_time_s'] and abs(time-base_time-tau)<=1e-14,'CSV clock lies outside its reviewed actual interval or differs from actual PRE-relative tau')
            fig,axes=old.plt.subplots(2,2,figsize=(12,8.8),layout='constrained')
            fig.suptitle(title+'\n'+case+f' | Part {part}\nActual t={time:.9f} s; tau={tau:.9f} s',fontsize=11)
            for ax,(key,display,label,scale) in zip(axes.flat,FIELDS):
                lo,hi=color_ranges[display];pressure=display.endswith('_kPa');centered=pressure and lo<0<hi
                norm=TwoSlopeNorm(vmin=lo,vcenter=0.,vmax=hi) if centered else Normalize(vmin=lo,vmax=hi,clip=False)
                im=ax.scatter(values['x_m'][at],values['z_m'][at],c=values[key][at]*scale,norm=norm,cmap='coolwarm' if pressure else 'viridis',s=6,edgecolors='none',rasterized=True)
                ax.set(xlim=xlim,ylim=zlim,xlabel='x [m]',ylabel='z [m]',title=label);ax.set_aspect('equal');ax.tick_params(labelsize=9)
                ticks=np.r_[np.linspace(lo,0.,3)[:-1],np.linspace(0.,hi,3)] if centered else np.linspace(lo,hi,5)
                bar=fig.colorbar(im,ax=ax,ticks=ticks,fraction=.046,pad=.025);bar.set_ticks(ticks,labels=[f'{v:.4g}' for v in ticks]);bar.ax.tick_params(labelsize=8)
            dest=Path(str(prefix)+f'_snapshot{index:02d}_part{part:04d}.png');fig.savefig(dest,dpi=180,bbox_inches='tight',pad_inches=.12);old.plt.close(fig);made.append(stat(dest))
            snapshots.append(dict(tag=case,part=part,time_s=time,tau_s=tau,soil_points=5000,prior_source_partial=scope['source_partial'],figure=str(dest)))
        need(all(stat(entry['path'])==entry for entry in before),'Display manifest, helper or sealed input changed while drawing')
        for entry in prior['consumed']:bind(entry)
        result.update(display_complete=True,prior_review_stage=prior['stage'],prior_receiver_scopes=list(scopes.values()),prior_partial_flags={key:prior[key] for key in ('receiver_complete','whole_run_passed','saved_prefix_native_qualified','actual_saved_records') if key in prior},source_CSV=str(csv_path),snapshots=snapshots,snapshot_count=len(snapshots),shared_full_data_ranges=ranges,shared_colorbar_ranges=color_ranges,constant_field_padding_only=[key for key in ranges if ranges[key][0]==ranges[key][1]],pressure_display_units='kPa',CSV_pressure_units='Pa',spatial_limits_m=dict(x=xlim,z=zlim),full_supplied_state_extrema_used=True,zero_centered_pressure_if_crosses_zero=True,no_smoothing_clipping_refitting=True,existing_figures_unchanged=True,consumed_stats_unchanged=True,visual_QA_pending=True)
    except Exception as error:
        result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        result.update(consumed=before,figures=made)
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
