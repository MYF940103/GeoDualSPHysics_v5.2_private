"""Offline three-state one-step material/volume attribution; no native or solver action."""
import argparse, csv, json, re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap, SymLogNorm

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_late_step_review_r1'
PARTS = (200, 250, 300)
STEPS = (2400001, 2500001, 2600000)
IDS = set(range(2060, 7060))
STAGES = ('restored_n', 'force_n', 'half_before_divide', 'half_after_divide', 'force_h', 'raw_full', 'completed_cap')
TRACE = ('logJ_minus_elastic_trace', 'kinematic_log_quadrature', 'rate_trace_minus_3Ktheta_equivalent',
         'trial_addition_roundoff_equivalent', 'return_trace_equivalent')


def need(ok, message):
    if not ok: raise RuntimeError(message)


def stat(p):
    p = Path(p).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def table(p):
    with Path(p).open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))


def bind(entry, consumed):
    need(stat(entry['path']) == entry, 'Bound input changed: '+entry['path'])
    consumed.append(entry); return Path(entry['path'])


def vector(rows, key): return np.array([float(q[key]) for q in rows], dtype=float)


def statistics(values, name):
    a = np.asarray(values, dtype=float); need(a.size > 0 and np.isfinite(a).all(), 'Finite nonempty statistic required: '+name)
    return {name+'_mean': float(a.mean()), name+'_sum': float(a.sum()), name+'_RMS': float(np.sqrt(np.mean(a*a))),
            name+'_minimum': float(a.min()), name+'_maximum': float(a.max()), name+'_maxabs': float(np.abs(a).max())}


def idmap(rows, name):
    need(len(rows) == 5000 and {int(q['native_id']) for q in rows} == IDS, 'Exact5000-ID coverage differs: '+name)
    result = {int(q['native_id']): q for q in rows}
    need(len(result) == 5000, 'Duplicate original ID: '+name); return result


def write(p, rows):
    need(rows, 'Nonempty derived table required')
    with p.open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args(); need(args.execution_authorized, 'Author-only until root full-file review')
    check = T/'logs'/(TAG+'.check.json'); prefix = T/'figures'/TAG
    need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')), 'Existing complete/partial outputs protected')
    consumed, outputs = [], []
    result = dict(stage=TAG, analysis_complete=False, physical_acceptance=False, consumed=consumed)
    try:
        for p in (Path(__file__), T/'notes'/(TAG+'.md')): consumed.append(stat(p))
        buildpath = T/'logs/c08_h18_late_step_r1.build.json'; consumed.append(stat(buildpath)); build = read(buildpath)
        need(build['passed'] and build['consumed_stats_unchanged'] and build['physical_objects_compiled'] == 0
             and build['actual_step_call_block_byte_equal'] and build['material_shadow_not_feedback'], 'Original one-step build required')
        program = bind(build['program'], consumed)
        header = T/'outputs/c08_h18_late_step_r1_build/headers/src/source/FunSoilMaterial.h'
        bind(next(q for q in build['archived_headers'] if Path(q['path']).resolve() == header.resolve()), consumed)
        text = header.read_text(encoding='utf-8-sig')
        statuses = [q.strip() for q in re.search(r'enum class Status:unsigned\{([^}]+)\};', text).group(1).split(',')]
        reasons = [q.strip() for q in re.search(r'enum class Reason:unsigned\{([^}]+)\};', text).group(1).split(',')]
        need(statuses == ['Invalid','Elastic','Smooth','Apex','TensionRepair','NoAdmissibleFlow','NonConverged','UnresolvedPath'], 'Frozen status enum changed')
        admitted = ('Elastic', 'Smooth', 'Apex', 'TensionRepair')
        summary, cohorts, per_id, plot_data = [], [], [], []
        for part, step in zip(PARTS, STEPS):
            tag = 'c08_h18_late_step_r1_p'+str(part); receipt = T/'logs'/(tag+'.check.json')
            consumed.append(stat(receipt)); c = read(receipt)
            need(c['passed'] and c['consumed_stats_unchanged'] and c['physical_steps'] == 1 and not c['physical_acceptance'], 'Actual passed one-step receipt required')
            need(bind(c['build'], consumed) == buildpath, 'Common actual build required')
            call = read(bind(c['actual_call'], consumed)); done = read(bind(c['completion'], consumed))
            need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and call['ownership_failure'] is None
                 and Path(call['program']).resolve() == program.resolve() and call['arguments'][3:5] == ['--part',str(part)], 'Actual owned part-specific call failed')
            need(done['passed'] and done['source_part'] == part and done['source_completed_step'] == step
                 and done['completed_step'] == step+1 and done['dt_s'] == .000005 and done['physical_steps'] == 1
                 and done['actual_force_calls'] == done['actual_Darcy_calls'] == 2
                 and done['stage_rows'] == 35000 and done['balance_rows'] == 5000 and done['summary_rows'] == 3
                 and done['material_shadow_rows'] == 10000 and done['trace_balance_rows'] == 5000
                 and done['all6_material_sigma_and_policy_kappa_bits_matched'] and done['sorted_predictor_scalar_bases_bit_equal']
                 and done['positive_only_completed_cap_verified'] and done['shadow_status_not_instrumented_original_status']
                 and done['completed_time_s'] == done['source_time_s']+done['dt_s'], 'Original completion/bit/clock coverage differs')
            root = T/'outputs'/tag; raw = {}
            for leaf in ('stages.csv','balance.csv','summary.csv','material_shadow.csv','trace_balance.csv'):
                path = root/leaf
                raw[leaf] = table(bind(next(q for q in c['outputs'] if Path(q['path']).resolve() == path.resolve()), consumed))
            stages, material, trace, balance = raw['stages.csv'], raw['material_shadow.csv'], raw['trace_balance.csv'], raw['balance.csv']
            need(len(stages) == 35000 and len(material) == 10000 and len(trace) == len(balance) == 5000
                 and len(raw['summary.csv']) == 3, 'Actual CSV row coverage differs')
            maps = {name: idmap([q for q in stages if q['stage'] == name], name) for name in STAGES}
            need({q['stage'] for q in stages} == set(STAGES), 'Unexpected stage label')
            for q in stages:
                need(float(q['solver_time_s']) == done['source_time_s'] and int(q['solver_completed_step']) == step, 'Actual source clock changed')
            tm, bm = idmap(trace, 'trace'), idmap(balance, 'balance')
            need(all(float(q['source_time_s']) == done['source_time_s'] and int(q['source_completed_step']) == step
                     and float(q['dt_s']) == done['dt_s'] and abs(float(q['closure'])) <= float(q['closure_budget']) for q in trace), 'Original trace clock/arithmetic gate differs')
            need(all(abs(float(q['closure_error'])) <= float(q['closure_budget']) for q in balance), 'Original pressure/J arithmetic gate differs')
            mm = {name: idmap([q for q in material if q['stage'] == name], 'material '+name) for name in ('half','full')}
            need({q['stage'] for q in material} == {'half','full'}, 'Unexpected material stage')
            base, final = maps['restored_n'], maps['completed_cap']
            row = dict(part=part, actual_source_time_s=done['source_time_s'], actual_tau_s=done['source_tau_s'],
                       source_completed_step=step, actual_next_time_s=done['completed_time_s'], dt_s=done['dt_s'])
            for name in ('half','full'):
                seq = [mm[name][i] for i in sorted(IDS)]
                for q in seq:
                    status, reason = int(q['shadow_status']), int(q['shadow_reason'])
                    need(0 <= status < len(statuses) and statuses[status] in admitted and 0 <= reason < len(reasons), 'Uncommitted material status/reason')
                    need(float(q['source_time_s']) == done['source_time_s'] and int(q['source_completed_step']) == step
                         and float(q['stage_width_s']) == done['dt_s']*(.5 if name == 'half' else 1.), 'Actual material stage clock differs')
                    need(float(q['actual_saved_kappa']) == float(q['kappa_n'] if name == 'half' else q['shadow_kappa']),
                         'Original predictor/corrector saved-kappa policy differs')
                for status in admitted: row[name+'_'+status+'_IDs'] = sum(statuses[int(q['shadow_status'])] == status for q in seq)
                for field, label in [('lambda_shear','lambda_shear'),('lambda_apex','lambda_apex'),('lambda_tension','lambda_tension')]:
                    row.update(statistics(vector(seq, field), name+'_'+label))
                row.update(statistics(-vector(seq,'return_deltaI_Pa'), name+'_trace_reduction_Pa'))
                growth = vector(seq,'actual_saved_kappa')-vector(seq,'kappa_n')
                row.update(statistics(growth, name+'_actual_saved_kappa_growth'))
                row[name+'_actual_kappa_growth_IDs'] = int((growth > 0).sum())
                for status in admitted:
                    for region in ('all','FS23_at_source','interior_at_source'):
                        chosen = [q for q in seq if statuses[int(q['shadow_status'])] == status and
                                  (region == 'all' or ((int(base[int(q['native_id'])]['FS']) in (2,3)) == (region == 'FS23_at_source')))]
                        if not chosen: continue
                        identity = [int(q['native_id']) for q in chosen]
                        out = dict(part=part, actual_tau_s=done['source_tau_s'], stage=name, shadow_status=status,
                                   source_region=region, IDs=len(chosen), source_negative_p_IDs=sum(float(base[i]['p_Pa']) < 0 for i in identity))
                        out.update(statistics([float(base[i]['p_Pa']) for i in identity], 'source_p_Pa'))
                        out.update(statistics(vector(chosen,'kappa_n'), 'source_kappa'))
                        out.update(statistics(-vector(chosen,'return_deltaI_Pa'), 'trace_reduction_Pa'))
                        out.update(statistics(vector(chosen,'lambda_tension'), 'lambda_tension'))
                        out.update(statistics(vector(chosen,'actual_saved_kappa')-vector(chosen,'kappa_n'), 'actual_saved_kappa_growth'))
                        cohorts.append(out)
            for key in TRACE: row.update(statistics(vector(trace,key), key))
            row['mean_actual_delta_p_Pa'] = float(np.mean([float(final[i]['p_Pa'])-float(base[i]['p_Pa']) for i in IDS]))
            row['mean_actual_delta_J'] = float(np.mean([float(final[i]['J'])-float(base[i]['J']) for i in IDS]))
            row['mean_actual_delta_logJ'] = float(np.mean(vector(trace,'delta_logJ')))
            row['mean_actual_delta_effective_trace_Pa'] = float(np.mean([
                sum(float(final[i]['sigma_'+k])-float(base[i]['sigma_'+k]) for k in ('xx','yy','zz')) for i in IDS]))
            row['mean_actual_completed_cap_delta_p_Pa'] = float(np.mean(vector(balance,'delta_cap')))
            row['completed_pressure_cap_IDs'] = int(np.count_nonzero(vector(balance,'delta_cap')))
            contact_keys = ('pre_contact_dx','pre_contact_dz','pre_contact_dvx','pre_contact_dvz','corr_contact_dx','corr_contact_dz','corr_contact_dvx','corr_contact_dvz')
            for key in contact_keys: row[key+'_maxabs'] = float(np.abs(vector(balance,key)).max())
            topz = max(float(q['z']) for q in base.values())
            row['source_current_highest_z_m'] = topz  # Geometry diagnostic only; not an original top-material set.
            summary.append(row)
            for i in sorted(IDS):
                q = dict(part=part, actual_tau_s=done['source_tau_s'], native_id=i, source_x_m=float(base[i]['x']), source_z_m=float(base[i]['z']),
                         source_FS=int(base[i]['FS']), source_p_Pa=float(base[i]['p_Pa']), actual_next_p_Pa=float(final[i]['p_Pa']),
                         source_kappa=float(base[i]['kappa']), actual_next_kappa=float(final[i]['kappa']),
                         shadow_half_status=statuses[int(mm['half'][i]['shadow_status'])], shadow_full_status=statuses[int(mm['full'][i]['shadow_status'])],
                         shadow_half_reason=reasons[int(mm['half'][i]['shadow_reason'])], shadow_full_reason=reasons[int(mm['full'][i]['shadow_reason'])],
                         full_lambda_tension=float(mm['full'][i]['lambda_tension']), full_trace_reduction_Pa=-float(mm['full'][i]['return_deltaI_Pa']))
                q.update({key: float(tm[i][key]) for key in TRACE}); per_id.append(q)
            plot_data.append([q for q in per_id if q['part'] == part])
        for leaf, rows in [('summary',summary),('cohorts',cohorts),('per_ID',per_id)]:
            p = Path(str(prefix)+'_'+leaf+'.csv'); write(p,rows); outputs.append(p)
        fig, axes = plt.subplots(2,2,figsize=(13,8),layout='constrained'); x = np.arange(3); bottom = np.zeros(3)
        colors = dict(Elastic='#7299b8', Smooth='#dfac4a', Apex='#9d72b2', TensionRepair='#bd3942')
        for status in admitted:
            counts = [q['full_'+status+'_IDs'] for q in summary]; axes[0,0].bar(x,counts,bottom=bottom,label=status,color=colors[status]); bottom += counts
        axes[0,0].set(title='Full-stage same-input shadow status',ylabel='IDs'); axes[0,0].legend(fontsize=8)
        for key, label in [(TRACE[0],'measured logJ - elastic trace'),(TRACE[-1],'material return trace')]:
            axes[0,1].plot(x,[q[key+'_mean'] for q in summary],marker='o',label=label)
        axes[0,1].set(title='Mean equivalent volumetric increment',ylabel='Dimensionless'); axes[0,1].legend(fontsize=8)
        for key in TRACE[1:]: axes[1,0].plot(x,[q[key+'_RMS'] for q in summary],marker='o',label=key.replace('_',' '))
        axes[1,0].set_yscale('symlog',linthresh=1e-19); axes[1,0].set(title='Per-ID RMS: return versus arithmetic terms',ylabel='Dimensionless'); axes[1,0].legend(fontsize=7)
        axes[1,1].bar(x,[q['mean_actual_delta_p_Pa'] for q in summary],color='#536e88'); axes[1,1].set(title='Actual mean pressure change in one 5 us step',ylabel='Pressure change [Pa]')
        for ax in axes.flat:
            ax.set_xticks(x,[f"{q['actual_tau_s']:.6f}" for q in summary]); ax.set_xlabel('Actual source tau [s]'); ax.grid(axis='y',alpha=.2)
        fig.suptitle('Three independent original CPU steps from saved GPU states\nShadow labels are inferred from bit-matched material results; no full-history attribution',fontsize=12)
        p = Path(str(prefix)+'_summary.png'); fig.savefig(p,dpi=170,bbox_inches='tight'); plt.close(fig); outputs.append(p)
        fig, axes = plt.subplots(3,2,figsize=(13,9),layout='constrained'); cmap=ListedColormap([colors[q] for q in admitted]); norm=BoundaryNorm(np.arange(-.5,4.5),4)
        largest=max(abs(q['return_trace_equivalent']) for rows in plot_data for q in rows); need(largest>0,'Nonzero observed return required for this diagnostic plot')
        scalar=SymLogNorm(linthresh=largest/1000,vmin=-largest,vmax=largest)
        for row, values in enumerate(plot_data):
            xx=[q['source_x_m'] for q in values]; zz=[q['source_z_m'] for q in values]; time=values[0]['actual_tau_s']
            pc=axes[row,0].scatter(xx,zz,c=[admitted.index(q['shadow_full_status']) for q in values],cmap=cmap,norm=norm,s=4,linewidths=0)
            pr=axes[row,1].scatter(xx,zz,c=[q['return_trace_equivalent'] for q in values],cmap='coolwarm',norm=scalar,s=4,linewidths=0)
            for ax in axes[row]: ax.set(title=f'Actual source tau={time:.6f} s',xlabel='x [m]',ylabel='z [m]'); ax.set_aspect('equal')
        bar=fig.colorbar(pc,ax=list(axes[:,0]),ticks=np.arange(4),shrink=.7);bar.ax.set_yticklabels(admitted);bar.set_label('Full same-input shadow status')
        fig.colorbar(pr,ax=list(axes[:,1]),shrink=.7,label='Return trace equivalent, dimensionless')
        fig.suptitle('Original5000 source positions; no interpolation or moving-material relabeling\nMaterial return can change volume response at psi=0; that alone is not a bug or a repair',fontsize=12)
        p=Path(str(prefix)+'_fields.png');fig.savefig(p,dpi=170,bbox_inches='tight');plt.close(fig);outputs.append(p)
        need(all(stat(q['path'])==q for q in consumed),'Consumed original evidence changed during analysis')
        result.update(analysis_complete=True,parts=list(PARTS),status_names_from_frozen_header=statuses,
                      material_shadow_rows=30000,trace_balance_rows=15000,actual_stage_rows=105000,summary=summary,
                      consumed_stats_unchanged=True,outputs=[stat(q) for q in outputs],visual_QA_pending=True,
                      component_invocations=0,solver_invocations=0,native_decodes=0,SHA_scans=0,
                      shadow_status_is_not_original_call_instrumentation=True,whole_GPU_history_attribution=False,
                      no_automatic_cap_policy_or_other_psi=True)
    except Exception as error:
        result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
