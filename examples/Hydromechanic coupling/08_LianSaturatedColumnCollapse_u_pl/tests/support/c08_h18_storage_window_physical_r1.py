"""Scientific CSV-only interpretation after the passed window R2 review; never run physical tools."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_storage_window_physical_r1'
GATE = T/'logs/c08_h18_storage_window_review_r2.check.json'
OLD_REVIEW = T/'logs/c08_h18_as03n255_review_r1.check.json'
OLD_HISTORY = T/'figures/c08_h18_as03n255_review_r1_history.csv'
CONTROL = 'c08_h18_as03_n255_r1'
FOCUS = (4953, 4954, 6767, 6865)
TERMS = ('compression', 'Darcy_remainder_including_rate_quantization',
         'source_split_roundoff', 'pressure_commit_roundoff', 'weight_change', 'cap_change')
LABELS = ('Compression', 'Darcy remainder', 'Source split roundoff',
          'Pressure commit roundoff', 'Weight change', 'Positive-FS cap')
COLORS = ('#0072B2', '#D55E00', '#CC79A7', '#009E73', '#E69F00', '#6A51A3')
SCALE = 1e6
consumed = []
first_scientific_bindings = []


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def stat(path):
    p = Path(path).resolve()
    s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def consume(path, expected=None, first=False):
    q = stat(path)
    if expected:
        need(Path(expected['path']).resolve() == Path(q['path']) and
             (expected['bytes'], expected['mtime_ns']) == (q['bytes'], q['mtime_ns']),
             'Bound scientific input changed: '+str(path))
    consumed.append(q)
    if first:
        first_scientific_bindings.append(q)
    return Path(q['path'])


def table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    need(rows, 'Empty scientific table')
    with path.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def number_rows(rows):
    return [{k: (v if k in ('storage_proxy_not_fluid_mass', 'rate_quantization_is_bound_only') else float(v))
             for k, v in q.items()} for q in rows]


def load():
    consume(Path(__file__))
    consume(T/'notes'/(TAG+'.md'))
    consume(GATE)
    gate = read(GATE)
    proof = gate['no_feedback_byteproof']
    need(gate['stage'] == 'c08_h18_storage_review_r2' and gate['profile'] == 'window' and
         gate['passed'] and gate['consumed_stats_unchanged'] and
         gate['observations']['actual_rows'] == 455000 and
         gate['observations']['actual_saved_states'] == 91 and
         proof['compared_records'] == 91 and proof['all22_and_actual_time_bytes_equal'] and
         proof['literal_layout_bytes_equal'] and proof['all_signed_clock_row_bytes_equal'],
         'Complete passed R2 window/91-record original-physics byte proof required')
    summary_path = consume(gate['summary']['path'], gate['summary'])
    sidecar = consume(gate['observer_sidecar']['path'], gate['observer_sidecar'])
    consume(gate['source_run']['path'], gate['source_run'])
    run = read(gate['source_run']['path'])
    source_time = float(run['actual_source_time_s'])
    nrpath = consume(gate['native_receipt']['path'], gate['native_receipt'])
    nr = read(nrpath)
    need(nr['passed'], 'Actual new native receipt failed')
    done_entry = nr.get('native_completion', nr.get('completion'))
    need(done_entry is not None, 'Native completion binding missing')
    done_path = consume(done_entry['path'], done_entry)
    done = read(done_path)
    need(done['passed'] and done['samples'] == 91 and done['completed_steps'] == 2180000,
         'Actual new native91 endpoint differs')
    nroot = done_path.parent
    clocks_path = nroot/'clocks.csv'
    history_path = nroot/'history.csv'
    known = [q for q in gate['consumed'] if Path(q['path']).resolve() == clocks_path.resolve()]
    need(len(known) == 1, 'R2 signed-clock binding missing')
    consume(clocks_path, known[0])
    # R2 checked all typed arrays. History is a small genuine reader-derived CSV;
    # seal it now if the native receipt did not already record its stat.
    history_entries = [q for q in nr.get('files', nr.get('outputs', []))
                       if Path(q['path']).resolve() == history_path.resolve()]
    consume(history_path, history_entries[0] if history_entries else None,
            first=not history_entries)
    clocks = table(clocks_path)
    native = table(history_path)
    global_rows = number_rows(table(summary_path))
    consume(OLD_REVIEW)
    old_review = read(OLD_REVIEW)
    need(old_review['analysis_complete'] and old_review['consumed_stats_unchanged'],
         'Retained AS03 physical CSV review missing')
    old_entry = [q for q in old_review['files'] if Path(q['path']).resolve() == OLD_HISTORY.resolve()]
    need(len(old_entry) == 1, 'Original physical-history binding missing')
    consume(OLD_HISTORY, old_entry[0])
    old = [q for q in table(OLD_HISTORY) if q['tag'] == CONTROL]
    need(len(clocks) == len(native) == len(global_rows) == len(old) == 91,
         'All91 genuine scientific histories required')
    physical = []
    for i, (s, c, n, o) in enumerate(zip(global_rows, clocks, native, old)):
        time = float(c['time_s'])
        step = int(c['completed_step'])
        need(int(s['part']) == int(c['part']) == int(n['part']) == int(o['part']) == i and
             int(s['completed_step']) == int(o['completed_step']) == step and
             float(s['actual_time_s']) == float(n['time_s']) == float(o['time_s']) == time,
             'Actual scientific time/step join differs; no interpolation permitted')
        s['tau_s'] = time-source_time
        s['delta_S_from_PRE'] = s['last_S']-s['initial_S']
        p = dict(part=i, completed_step=step, actual_time_s=time, tau_s=time-source_time)
        for key in ('p_mean_Pa', 'p_RMS_Pa', 'p_min_Pa', 'p_max_Pa', 'velocity_RMS_m_s',
                    'total_stress_Frobenius_RMS_Pa', 'max_kappa', 'min_J', 'max_J'):
            p[key] = float(n[key])
        p['mean_settlement_from_PRE_mm'] = -1000*float(n['mean_dz_from_PRE_m'])
        for key in ('top_material_settlement_mm', 'bottom_material_settlement_mm',
                    'NN_min_over_dp', 'NN_q05_over_dp', 'pairs_r_lt_0p7dp',
                    'runout_from_PRE_front_m'):
            p[key] = float(o[key])
        physical.append(p)
    return gate, global_rows, physical, sidecar, source_time


def scientific_stream(sidecar, global_rows):
    """One extra scientific stream: sum only unsigned bound/abs columns and retain four IDs."""
    focus = []
    qvalues, avalues = [], []
    rows = 0
    with sidecar.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        needed = {'native_id', 'actual_saved_time_s', 'last_completed_step', 'initial_S', 'last_S',
                  'rate_quantization_bound_only', 'sum_abs_increments', *TERMS}
        need(needed <= set(reader.fieldnames or ()), 'Actual scientific sidecar columns missing')
        for r in reader:
            part = rows//5000
            need(part < 91, 'Extra scientific sidecar batch')
            qvalues.append(float(r['rate_quantization_bound_only']))
            avalues.append(float(r['sum_abs_increments']))
            native_id = int(r['native_id'])
            if native_id in FOCUS:
                s = global_rows[part]
                need(float(r['actual_saved_time_s']) == s['actual_time_s'] and
                     int(r['last_completed_step']) == int(s['completed_step']),
                     'Fixed-ID actual scientific clock differs')
                q = dict(part=part, native_id=native_id, completed_step=int(s['completed_step']),
                         actual_time_s=s['actual_time_s'], tau_s=s['tau_s'])
                for key in ('initial_S', 'last_S', *TERMS, 'rate_quantization_bound_only',
                            'endpoint_residual', 'endpoint_arithmetic_budget'):
                    q[key] = float(r[key])
                q['delta_S_from_PRE'] = q['last_S']-q['initial_S']
                focus.append(q)
            rows += 1
            if rows % 5000 == 0:
                global_rows[part]['rate_quantization_bound_only'] = math.fsum(qvalues)
                global_rows[part]['sum_abs_increments_scientific'] = math.fsum(avalues)
                qvalues, avalues = [], []
    need(rows == 455000 and len(focus) == 364 and not qvalues,
         'All91 scientific batches/four fixed IDs required')
    need(all([q['native_id'] for q in focus if q['part'] == i] == list(FOCUS)
             for i in range(91)), 'Fixed IDs/order missing from scientific extraction')
    return focus


def intervals(global_rows, focus, source_time):
    groups = [('global5000', global_rows)]
    groups += [(str(native_id), [q for q in focus if q['native_id'] == native_id])
               for native_id in FOCUS]
    marks = [-1, 0, 10, 30, 38, 60, 76, 90]
    rows = []
    for label, series in groups:
        for a, b in zip(marks, marks[1:]):
            old = series[a] if a >= 0 else None
            new = series[b]
            q = dict(cohort=label, start_part=a, end_part=b,
                     actual_start_s=source_time if old is None else old['actual_time_s'],
                     actual_end_s=new['actual_time_s'],
                     tau_start_s=0. if old is None else old['tau_s'], tau_end_s=new['tau_s'],
                     start_completed_step=2000000 if old is None else int(old['completed_step']),
                     end_completed_step=int(new['completed_step']))
            q['delta_S'] = new['last_S']-(new['initial_S'] if old is None else old['last_S'])
            for key in (*TERMS, 'rate_quantization_bound_only'):
                q[key] = new[key]-(0. if old is None else old[key])
            q['sum_abs_signed_partition_changes'] = math.fsum(abs(q[k]) for k in TERMS)
            q['ledger_minus_delta_S'] = math.fsum(q[k] for k in TERMS)-q['delta_S']
            rows.append(q)
    return rows


def decorate(ax, onset, xlabel=True):
    for x in onset:
        ax.axvline(x, color='0.55', lw=.8, ls=':')
    ax.grid(alpha=.25)
    if xlabel:
        ax.set_xlabel('Actual time since PRE release [s]')
    if ax.get_yscale() == 'linear':
        ax.ticklabel_format(axis='y', style='sci', scilimits=(-3, 4), useMathText=True)


def line(ax, rows, key, label, color, scale=1., **kwargs):
    ax.plot([q['tau_s'] for q in rows], [scale*q[key] for q in rows],
            label=label, color=color, **kwargs)


def savefig(fig, path):
    fig.savefig(path, dpi=190, bbox_inches='tight')
    plt.close(fig)


def plots(global_rows, physical, focus, interval_rows, paths):
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'legend.fontsize': 8})
    onset = [global_rows[i]['tau_s'] for i in (38, 76)]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    a = axes[0, 0]
    line(a, global_rows, 'last_S', 'S = sum(n V p / Kw)', 'black', SCALE, lw=1.9)
    a.axhline(SCALE*global_rows[0]['initial_S'], color='0.5', ls='--', label='PRE S')
    a.set_title('Conditional pressure-storage proxy, not water mass')
    a.set_ylabel('S [10^-6 m2 per unit depth]')
    a.legend()
    a = axes[0, 1]
    for k, label, color in zip((TERMS[0], TERMS[1], TERMS[5]),
                               (LABELS[0], LABELS[1], LABELS[5]),
                               (COLORS[0], COLORS[1], COLORS[5])):
        line(a, global_rows, k, label, color, SCALE)
    line(a, global_rows, 'delta_S_from_PRE', 'Net delta S', 'black', SCALE, lw=1.8)
    a.set_title('Signed cumulative contributions; cancellation retained')
    a.set_ylabel('Cumulative term [10^-6 m2]')
    a.legend()
    a = axes[1, 0]
    line(a, global_rows, 'weight_change', 'p_raw * delta w', COLORS[4], SCALE)
    a.set_title('Capacity/weight change, separate from pressure write')
    a.set_ylabel('Cumulative term [10^-6 m2]')
    a.legend()
    a = axes[1, 1]
    for key, label, color in ((TERMS[3], LABELS[3], COLORS[3]),
                              (TERMS[2], LABELS[2], COLORS[2]),
                              ('rate_quantization_bound_only', 'Rate quantization bound ONLY', '0.35')):
        line(a, global_rows, key, label, color, SCALE)
    a.set_yscale('symlog', linthresh=1e-8)
    a.set_title('Write/split terms and unsigned bound (not a source)')
    a.set_ylabel('Cumulative term / bound [10^-6 m2]')
    a.legend()
    for a in axes.flat:
        decorate(a, onset)
    fig.suptitle('C08 AS.3/n2.55, AV.1: output-only cumulative observation')
    savefig(fig, paths['storage'])

    g = [q for q in interval_rows if q['cohort'] == 'global5000']
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), constrained_layout=True)
    x = np.arange(len(g))
    for j, k in enumerate((TERMS[0], TERMS[1], TERMS[5], TERMS[4])):
        ix = TERMS.index(k)
        axes[0].bar(x+(j-1.5)*.18, [SCALE*q[k] for q in g], width=.18,
                    label=LABELS[ix], color=COLORS[ix])
    axes[0].plot(x, [SCALE*q['delta_S'] for q in g], 'ko', label='Observed delta S')
    axes[0].set_ylabel('Interval signed term [10^-6 m2]')
    axes[0].set_title('True saved endpoint differences; no fitted or interpolated boundary')
    axes[0].legend(ncol=3)
    for k, label, color in ((TERMS[3], LABELS[3], COLORS[3]),
                            (TERMS[2], LABELS[2], COLORS[2]),
                            ('rate_quantization_bound_only', 'Unsigned rate bound', '0.35')):
        axes[1].plot(x, [SCALE*q[k] for q in g], 'o-', label=label, color=color, ms=3)
    axes[1].set_yscale('symlog', linthresh=1e-8)
    axes[1].set_ylabel('Small interval term / bound [10^-6 m2]')
    axes[1].legend()
    labels = [f"P{q['start_part']} -> P{q['end_part']}\n{q['tau_start_s']:.6f}-{q['tau_end_s']:.6f}s"
              if q['start_part'] >= 0 else 'PRE -> P0\nrelease + first update' for q in g]
    for a in axes:
        a.axhline(0, color='0.5', lw=.7)
        a.set_xticks(x, labels, fontsize=8)
        a.grid(axis='y', alpha=.25)
    fig.suptitle('Intervals bracket saved pair onsets P38 and P76; correlation is not causation')
    savefig(fig, paths['intervals'])

    fig, axes = plt.subplots(3, 2, figsize=(13, 11), constrained_layout=True)
    a = axes[0, 0]
    for key, label, color in (('p_mean_Pa', 'Mean', 'black'), ('p_RMS_Pa', 'RMS', '#0072B2'),
                              ('p_min_Pa', 'Minimum', '#D55E00'), ('p_max_Pa', 'Maximum', '#009E73')):
        line(a, physical, key, label, color, .001)
    a.set_title('Actual native gauge pore pressure')
    a.set_ylabel('Pressure [kPa]')
    a.legend(ncol=2)
    a = axes[0, 1]
    for key, label, color in (('top_material_settlement_mm', 'Fixed PRE top material', '#0072B2'),
                              ('mean_settlement_from_PRE_mm', 'All-soil mean', 'black'),
                              ('bottom_material_settlement_mm', 'Fixed PRE bottom material', '#D55E00')):
        line(a, physical, key, label, color)
    a.set_title('Material settlement from the same PRE')
    a.set_ylabel('Downward settlement [mm]')
    a.legend()
    a = axes[1, 0]
    line(a, physical, 'total_stress_Frobenius_RMS_Pa', 'Total stress Frobenius RMS', '#0072B2', .001)
    a.set_title('Stress and motion remain genuine retained physics')
    a.set_ylabel('Total stress [kPa]')
    a.legend()
    a = axes[1, 1]
    line(a, physical, 'NN_min_over_dp', 'Minimum NN / dp', '#D55E00')
    line(a, physical, 'NN_q05_over_dp', '5% NN / dp', '#0072B2')
    a.axhline(.7, color='0.5', ls='--', label='.7 observation level')
    a.set_title('Closeness tail; .7 is descriptive')
    a.set_ylabel('Nonself soil distance / dp')
    a.legend()
    a = axes[2, 0]
    line(a, physical, 'pairs_r_lt_0p7dp', 'Pairs r < .7 dp', '#6A51A3')
    a.set_title('All-soil close-pair count')
    a.set_ylabel('Unique pairs')
    a.legend()
    a = axes[2, 1]
    line(a, physical, 'velocity_RMS_m_s', 'Velocity RMS', '#009E73')
    a.set_title('Flow has not been declared accepted or repaired')
    a.set_ylabel('Speed [m/s]')
    a.legend()
    for a in axes.flat:
        decorate(a, onset)
    fig.suptitle('91 native states equal retained AS03 physics: no new reference solve')
    savefig(fig, paths['physical'])

    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for a, native_id in zip(axes.flat, FOCUS):
        rows = [q for q in focus if q['native_id'] == native_id]
        for ix in (0, 1, 5):
            line(a, rows, TERMS[ix], LABELS[ix], COLORS[ix], SCALE)
        line(a, rows, 'delta_S_from_PRE', 'Net delta S', 'black', SCALE, lw=1.8)
        a.set_title(f'Fixed native material ID {native_id}')
        a.set_ylabel('Cumulative contribution [10^-6 m2]')
        decorate(a, onset)
        a.legend(ncol=2)
    fig.suptitle('Two reviewed close pairs: saved S attribution, not substage causality')
    savefig(fig, paths['focus'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Root full review and one offline scientific-analysis admission required')
    prefix = T/'figures'/TAG
    paths = {k: Path(str(prefix)+'_'+k+'.png') for k in ('storage', 'intervals', 'physical', 'focus')}
    csvpaths = {k: Path(str(prefix)+'_'+k+'.csv') for k in ('global', 'physical', 'focus', 'intervals')}
    check = T/'logs'/(TAG+'.check.json')
    need(not any(p.exists() for p in [*paths.values(), *csvpaths.values(), check]),
         'Existing complete/partial scientific outputs protected')
    result = dict(stage=TAG, analysis_complete=False, physical_acceptance=False,
                  causal_claim=False, solver_invocations=0, reader_invocations=0, VTK_invocations=0,
                  build_invocations=0, SHA_scans=0)
    try:
        gate, global_rows, physical, sidecar, source_time = load()
        focus = scientific_stream(sidecar, global_rows)
        interval_rows = intervals(global_rows, focus, source_time)
        need(all(stat(q['path']) == q for q in consumed), 'A sealed scientific input changed')
        for key, rows in (('global', global_rows), ('physical', physical),
                          ('focus', focus), ('intervals', interval_rows)):
            write_csv(csvpaths[key], rows)
        plots(global_rows, physical, focus, interval_rows, paths)
        need(all(stat(q['path']) == q for q in consumed), 'A scientific input changed during plotting')
        final = global_rows[-1]
        result.update(analysis_complete=True, R2_gate=stat(GATE), native_states=91, soil_IDs=5000,
            extra_scientific_sidecar_passes=1, sidecar_rows=455000, focus_IDs=list(FOCUS),
            focus_rows=364, interval_rows=len(interval_rows),
            fixed_original_control=CONTROL, old_physics_reused_only_after_all91_byteproof=True,
            source_actual_time_s=source_time, actual_tau_end_s=final['tau_s'],
            final_global={k: final[k] for k in ('initial_S', 'last_S', 'delta_S_from_PRE',
                         *TERMS, 'rate_quantization_bound_only', 'global_endpoint_residual',
                         'global_arithmetic_budget')},
            global_intervals=[q for q in interval_rows if q['cohort'] == 'global5000'],
            saved_pair_onset_markers={str(i): global_rows[i]['tau_s'] for i in (38, 76)},
            storage_proxy_not_water_mass=True, P0_fixed_not_paper_plastic_excess=True,
            signed_rate_quantization_measured=False, release_cap_amount_separately_measured=False,
            no_interpolation_filter_clipping_or_state_relabel=True,
            first_scientific_bindings=first_scientific_bindings, consumed=consumed,
            outputs=[stat(p) for p in [*csvpaths.values(), *paths.values()]], visual_QA_pending=True)
    except Exception as error:
        result.update(first_failure=str(error), consumed=consumed, partial_outputs_preserved=True)
        raise
    finally:
        with check.open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
