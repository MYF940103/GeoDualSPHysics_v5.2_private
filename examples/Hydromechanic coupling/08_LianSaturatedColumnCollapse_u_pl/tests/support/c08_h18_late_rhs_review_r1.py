"""Offline late three-state original CPU RHS review; no physical/native action."""
import argparse, csv, json, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_late_rhs_review_r1'
SRC = T/'outputs/c08_h18_late_rhs_r1'
PARTS, STEPS = (200, 250, 300), (2400001, 2500001, 2600000)
TERMS = ['compression', 'LP', 'Taylor_pressure', 'Da', 'FS_Ace_Lx', 'chain_pressure', 'chain_Ace']


def need(ok, message):
    if not ok: raise RuntimeError(message)


def stat(p):
    p = Path(p).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def table(p):
    with Path(p).open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))


def write(p, rows):
    need(rows, 'Nonempty derived CSV required')
    with p.open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def bound(entry, consumed):
    need(stat(entry['path']) == entry, 'Consumed bound input changed: '+entry['path'])
    consumed.append(entry); return Path(entry['path'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args(); need(args.execution_authorized, 'Author-only until root full-read and component review')
    check = T/'logs'/(TAG+'.check.json'); prefix = T/'figures'/TAG
    need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')), 'Existing complete/partial review protected')
    component_path = T/'logs/c08_h18_late_rhs_r1.check.json'
    build_path = T/'logs/c08_h18_late_rhs_r1.build.json'
    review_path = T/'logs/c08_h18_n255_full3_review_r1.check.json'
    paths = [Path(__file__), T/'notes'/(TAG+'.md'), T/'support/c08_h18_storage_rhs_review_r1.py',
             component_path, build_path, review_path]
    consumed = [stat(p) for p in paths]; component, build, review = map(read, (component_path, build_path, review_path))
    need(component['passed'] and component['consumed_stats_unchanged'] and component['component_invocations'] == 1
         and component['physical_steps'] == 0 and not component['physical_acceptance'], 'One passed zero-step component required')
    need(build['passed'] and build['consumed_stats_unchanged'] and build['original_Single_no_hook']
         and build['physical_objects_compiled'] == 0, 'Original numerical body/build closure required')
    need(review['analysis_complete'] and review['consumed_stats_unchanged'] and review['actual_samples'] == 301
         and not review['physical_acceptance'], 'Completed descriptive301 review required')
    actual = read(bound(component['actual_call'], consumed))
    need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None,
         'Actual component owned exit failed')
    bound(component['build'], consumed); completed = read(bound(component['completion'], consumed))
    need(completed['passed'] and completed['source_parts'] == list(PARTS) and completed['source_samples'] == 301
         and completed['physical_steps'] == completed['material_return_calls'] == completed['filter_calls'] == 0
         and completed['actual_force_calls'] == completed['actual_Darcy_calls'] == 3
         and completed['soil_rows'] == completed['literal_final_float_bits_matched'] == 15000
         and completed['term_rows'] == 45000 and completed['wall_rows'] == 5415
         and completed['summary_rows'] == 27 and completed['all5000_primary_bits_unchanged_per_call'],
         'Original late three-state coverage/identity differs')
    sourcefiles = {}
    for leaf in ('summary.csv', 'soil_rhs.csv', 'terms.csv', 'walls.csv'):
        p = SRC/leaf
        entry = next(q for q in component['consumed'] if Path(q['path']).resolve() == p.resolve())
        sourcefiles[leaf] = bound(entry, consumed)
    history_path = T/'figures/c08_h18_n255_full3_review_r1_history.csv'
    bound(next(q for q in review['files'] if Path(q['path']).resolve() == history_path.resolve()), consumed)
    xml = bound(build['input_xml'], consumed)
    kw = float(ET.parse(xml).getroot().find('execution/special/hydromechanics/PoreWaterBulkModulus').get('value'))
    need(np.isfinite(kw) and kw > 0, 'Actual finite positive Kw required')
    result = dict(stage=TAG, analysis_complete=False, physical_acceptance=False, consumed=consumed)
    outputs = []
    try:
        summary, terms = table(sourcefiles['summary.csv']), table(sourcefiles['terms.csv'])
        soil = np.genfromtxt(sourcefiles['soil_rhs.csv'], delimiter=',', names=True, dtype=None, encoding='utf-8')
        history = table(history_path)
        need(len(summary) == 27 and len(soil) == 15000 and len(terms) == 45000 and len(history) == 301,
             'Full late diagnostic/original301 history required')
        reduced, cohorts, per_id, theta, records = [], [], [], [], []
        fig, axes = plt.subplots(1, 3, figsize=(17, 5), layout='constrained')
        for axis, part, step in zip(axes, PARTS, STEPS):
            rows = [q for q in summary if int(q['part']) == part and q['receiver_group'] == 'all']
            need(len(rows) == 3 and {q['donor_group'] for q in rows} == {'all', 'fluid_donors', 'fixed_donors'}, 'Three donor partitions required')
            full = next(q for q in rows if q['donor_group'] == 'all')
            state = soil[soil['part'] == part]
            need(len(state) == 5000 and np.array_equal(np.sort(state['native_id']), np.arange(2060, 7060))
                 and np.all(state['completed_step'] == step), 'Exact original5000 IDs/actual completed step required')
            hrow = history[part]
            need(int(hrow['part']) == part and int(hrow['completed_step']) == step and float(hrow['time_s']) == float(full['time_s'])
                 and np.all(state['time_s'] == float(full['time_s'])), 'Actual matched native/component clock required')
            weight = float(full['sum_weight']); need(weight > 0, 'Positive global storage weight required')
            comp = float(full['compression_Q_m2_s'])/weight/1000
            hydro = sum(float(full[q+'_Q_m2_s']) for q in TERMS[1:])/weight/1000
            actual_rate = float(full['actual_Q_all_only_m2_s'])/weight/1000
            reduced.append(dict(part=part, time_s=float(full['time_s']), tau_s=float(full['tau_s']), completed_step=step,
                native_mean_pressure_kPa=float(hrow['p_mean_Pa'])/1000, storage_weight=weight,
                weighted_actual_rate_kPa_s=actual_rate, weighted_compression_rate_kPa_s=comp,
                weighted_hydraulic_rate_kPa_s=hydro,
                coefficient_change_equivalent_kPa_s=float(full['coefficient_Q_all_only_m2_s'])/weight/1000,
                conditional_storage_derivative_m2_s=float(full['conditional_storage_derivative_all_only_m2_s']),
                saved_FS_changes=int(full['saved_FS_changes'])))
            for row in [q for q in summary if int(q['part']) == part]:
                out = dict(part=part, tau_s=float(row['tau_s']), donor_group=row['donor_group'], receiver_group=row['receiver_group'],
                           receivers=int(row['receivers']), global_storage_weight=weight)
                out.update({key+'_global_weighted_kPa_s': float(row[key+'_Q_m2_s'])/weight/1000 for key in TERMS})
                out['expanded_global_weighted_kPa_s'] = float(row['expanded_Q_m2_s'])/weight/1000
                cohorts.append(out)
            for j, row in enumerate(rows):
                axis.bar(np.arange(7)+(j-1)*.25, [float(row[q+'_Q_m2_s'])/weight/1000 for q in TERMS], width=.25, label=row['donor_group'])
            axis.axhline(0, color='black', lw=.7); axis.set_xticks(np.arange(7), TERMS, rotation=65, ha='right')
            axis.set(title=f"tau={float(full['tau_s']):.6f}s; net {actual_rate:.2f} kPa/s", ylabel='Storage-weighted signed rate [kPa/s]')
            axis.grid(axis='y', alpha=.2)
            state_terms = [q for q in terms if int(q['part']) == part and q['donor_group'] == 'all']
            by_id = {int(q['native_id']): q for q in state_terms}; need(len(by_id) == 5000, 'All5000 original term IDs required')
            c = np.array([float(by_id[int(i)]['compression_Pa_s']) for i in state['native_id']])/1000
            hydraulic = np.array([sum(float(by_id[int(i)][q+'_Pa_s']) for q in TERMS[1:]) for i in state['native_id']])/1000
            saved_c = -kw/state['n']*state['saved_theta_s_1']/1000
            theta.append(dict(part=part, tau_s=float(full['tau_s']),
                fresh_theta_RMS_s_1=float(np.sqrt(np.mean(state['fresh_theta_s_1']**2))),
                saved_theta_RMS_s_1=float(np.sqrt(np.mean(state['saved_theta_s_1']**2))),
                fresh_minus_saved_theta_RMS_s_1=float(np.sqrt(np.mean((state['fresh_theta_s_1']-state['saved_theta_s_1'])**2))),
                saved_theta_compression_global_weighted_kPa_s=float(np.sum(state['storage_weight']*saved_c)/weight),
                fresh_theta_compression_global_weighted_kPa_s=comp,
                fresh_actual_rate_RMS_kPa_s=float(np.sqrt(np.mean((state['actual_rate_Pa_s']/1000)**2)))))
            for q, cv, hv, sv in zip(state, c, hydraulic, saved_c):
                per_id.append(dict(part=part, time_s=float(q['time_s']), tau_s=float(q['tau_s']), completed_step=step, native_id=int(q['native_id']),
                    p_Pa=float(q['p_Pa']), J=float(q['J']), n=float(q['n']), V_m2=float(q['V_m2']),
                    saved_theta_s_1=float(q['saved_theta_s_1']), fresh_theta_s_1=float(q['fresh_theta_s_1']),
                    saved_theta_compression_Pa_s=sv*1000, fresh_compression_Pa_s=cv*1000,
                    fresh_hydraulic_Pa_s=hv*1000, fresh_actual_rate_Pa_s=float(q['actual_rate_Pa_s']),
                    coefficient_Q_m2_s=float(q['coefficient_Q_m2_s'])))
            records.append((state, c, hydraulic))
        axes[0].legend(fontsize=8)
        fig.suptitle('Original CPU RHS on three saved late GPU states: no physical advance\nDonor partitions are additive; conditional storage is not water mass')
        p = Path(str(prefix)+'_terms.png'); fig.savefig(p, dpi=180, bbox_inches='tight'); plt.close(fig); outputs.append(p)
        fig, axes = plt.subplots(3, 4, figsize=(18, 11), layout='constrained')
        names = ['Pressure [kPa]', 'Compression [kPa/s]', 'Hydraulic [kPa/s]', 'Actual rate [kPa/s]']
        arrays = [[s['p_Pa']/1000, c, h, s['actual_rate_Pa_s']/1000] for s, c, h in records]
        for j, name in enumerate(names):
            extreme = max(np.max(np.abs(a[j])) for a in arrays)
            norm = SymLogNorm(linthresh=max(extreme/1000, .001), vmin=-extreme, vmax=extreme)
            for i, (state, _, _) in enumerate(records):
                ax = axes[i, j]; pc = ax.scatter(state['x_m'], state['z_m'], c=arrays[i][j], s=3, cmap='coolwarm', norm=norm)
                ax.set_aspect('equal'); ax.set(xlabel='x [m]', ylabel='z [m]', title=f"tau={float(state['tau_s'][0]):.6f}s; {name}")
            fig.colorbar(pc, ax=axes[:, j], shrink=.65, label=name)
        fig.suptitle('All5000 IDs, shared symmetric-log scales retain every extreme\nFresh CPU fields are not omitted GPU-substage replays')
        p = Path(str(prefix)+'_fields.png'); fig.savefig(p, dpi=180, bbox_inches='tight'); plt.close(fig); outputs.append(p)
        secants = []
        for left, right in zip(PARTS[:-1], PARTS[1:]):
            a, b = history[left], history[right]; width = float(b['time_s'])-float(a['time_s'])
            secants.append(dict(start_part=left, end_part=right, actual_start_tau_s=float(a['tau_s']), actual_end_tau_s=float(b['tau_s']),
                actual_duration_s=width, mean_pressure_endpoint_secant_kPa_s=(float(b['p_mean_Pa'])-float(a['p_mean_Pa']))/width/1000,
                ordinary_mean_not_storage_weighted_rate=True, secant_not_instantaneous_rate=True))
        for key, rows in [('summary', reduced), ('cohorts', cohorts), ('theta', theta), ('per_ID', per_id), ('mean_secants', secants)]:
            p = Path(str(prefix)+'_'+key+'.csv'); write(p, rows); outputs.append(p)
        need(all(stat(q['path']) == q for q in consumed), 'Consumed evidence changed during review')
        result.update(analysis_complete=True, reduced=reduced, theta=theta, mean_pressure_secants=secants,
                      consumed_stats_unchanged=True, outputs=[stat(q) for q in outputs], physical_steps=0,
                      native_decodes=0, solver_invocations=0, SHA_scans=0, visual_QA_pending=True,
                      storage_proxy_is_not_water_mass=True, late_instantaneous_driver_not_integrated_error_proof=True)
    except Exception as error:
        result.update(first_failure=str(error), partial_outputs_preserved=True); raise
    finally:
        with check.open('x', encoding='utf-8') as f: json.dump(result, f, indent=2, allow_nan=False); f.write('\n')


if __name__ == '__main__': main()
