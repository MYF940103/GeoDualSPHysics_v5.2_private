"""Render readable full3 panels from the already reviewed CSVs; no native read."""
import argparse, csv, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_n255_full3_panels_r1'
OLD = 'c08_h18_n255_full3_review_r1'


def stat(p):
    p = Path(p).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def need(ok, message):
    if not ok: raise RuntimeError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args(); need(args.execution_authorized, 'Reviewed render-only admission required')
    check = T/'logs'/(TAG+'.check.json'); prefix = T/'figures'/TAG
    need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')), 'Retained plots/partials protected')
    receipt = T/'logs'/(OLD+'.check.json'); r = json.loads(receipt.read_text(encoding='utf-8'))
    need(r['analysis_complete'] and r['actual_samples'] == 301 and not r['physical_acceptance'], 'Completed descriptive301 review required')
    consumed = [stat(receipt), stat(__file__), stat(T/'notes'/(TAG+'.md'))]
    tables = {}
    for key in ('snapshots', 'history'):
        p = T/'figures'/(OLD+'_'+key+'.csv')
        expected = next(q for q in r['files'] if Path(q['path']).resolve() == p.resolve())
        need(stat(p) == expected, 'Reviewed CSV changed: '+key)
        consumed.append(expected)
        with p.open(newline='', encoding='utf-8') as f: tables[key] = list(csv.DictReader(f))
    files = []
    result = dict(stage=TAG, render_complete=False, physical_acceptance=False, consumed=consumed)
    try:
        snaps, history = tables['snapshots'], tables['history']
        need(len(snaps) == 30000 and len(history) == 301, 'Original six5000-ID snapshots/all301 histories required')
        parts = sorted(set(int(q['part']) for q in snaps)); need(parts == [30, 60, 90, 120, 200, 300], 'Snapshot selection changed')
        data = {part: [q for q in snaps if int(q['part']) == part] for part in parts}
        need(all(len(v) == 5000 and len(set(q['native_id'] for q in v)) == 5000 for v in data.values()), 'Material IDs incomplete')
        columns = [('p_Pa', 'Pressure [kPa]', .001), ('native_p_minus_fixedP0_Pa', 'Native p-P0 [kPa]', .001),
                   ('kappa', 'Plastic history kappa', 1.), ('J', 'Volume ratio J', 1.)]
        norms = {}
        for key, _, scale in columns:
            values = np.array([float(q[key])*scale for q in snaps]); lo, hi = values.min(), values.max()
            norms[key] = TwoSlopeNorm(vmin=lo, vcenter=0., vmax=hi) if key in ('p_Pa', 'native_p_minus_fixedP0_Pa') and lo < 0 < hi else Normalize(lo, hi)
        xmax = max(float(q['x_m']) for q in snaps)
        for label, selected in [('early', parts[:3]), ('late', parts[3:])]:
            fig, axes = plt.subplots(4, 3, figsize=(16, 11), layout='constrained')
            for row, (key, title, scale) in enumerate(columns):
                for col, part in enumerate(selected):
                    values = data[part]; ax = axes[row, col]
                    pc = ax.scatter([float(q['x_m']) for q in values], [float(q['z_m']) for q in values],
                                    c=[float(q[key])*scale for q in values], s=5, linewidths=0,
                                    cmap='coolwarm' if row < 2 else 'viridis', norm=norms[key])
                    ax.set(xlim=(-.04, xmax+.04), ylim=(-.04, 2.04), xlabel='x [m]', ylabel='z [m]')
                    ax.set_aspect('equal'); ax.set_title(f"tau={float(values[0]['tau_s']):.6f} s; Part{part}", fontsize=10)
                fig.colorbar(pc, ax=list(axes[row]), label=title, shrink=.85)
            fig.suptitle('C08 psi=0; h/dp=1.8; AS0.5/n2.55\nActual saved particle centers; shared full color ranges; p-P0 is not paper plastic excess', fontsize=12)
            p = Path(str(prefix)+'_'+label+'_fields.png'); fig.savefig(p, dpi=160, bbox_inches='tight'); plt.close(fig); files.append(p)
        fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout='constrained')
        charts = [('Pressure [kPa]', [('p_mean_Pa', 'mean'), ('p_min_Pa', 'minimum'), ('p_max_Pa', 'maximum')], .001),
                  ('Stress Frobenius RMS [kPa]', [('effective_stress_Frobenius_RMS_Pa', 'effective'), ('total_stress_Frobenius_RMS_Pa', 'total')], .001),
                  ('Speed [m/s]', [('velocity_RMS_m_s', 'RMS'), ('max_speed_m_s', 'maximum')], 1.),
                  ('Fixed-material settlement from PRE [mm]', [('top_material_settlement_mm', 'initial top layer'), ('bottom_material_settlement_mm', 'initial bottom layer')], 1.),
                  ('Front advance from PRE [m]', [('runout_from_PRE_front_m', 'front advance')], 1.),
                  ('Soil particles with p<0', [('negative_p_soil', 'negative pressure count')], 1.)]
        tau = [float(q['tau_s']) for q in history]
        for ax, (title, metrics, scale) in zip(axes.flat, charts):
            for key, name in metrics: ax.plot(tau, [float(q[key])*scale for q in history], label=name)
            ax.set(title=title, xlabel='Actual time since PRE [s]'); ax.grid(alpha=.25); ax.legend(fontsize=8)
        fig.suptitle('C08 psi=0 full3 diagnostic: all301 actual saves; physical accuracy remains unresolved', fontsize=12)
        p = Path(str(prefix)+'_history.png'); fig.savefig(p, dpi=160, bbox_inches='tight'); plt.close(fig); files.append(p)
        need(all(stat(q['path']) == q for q in consumed), 'Consumed CSV/script changed during rendering')
        result.update(render_complete=True, files=[stat(p) for p in files], source_analysis_complete=True,
                      old_figures_unchanged=True, native_reads=0, solver_invocations=0, SHA_scans=0, visual_QA_pending=True)
    except Exception as error:
        result.update(first_failure=str(error), partials_preserved=True); raise
    finally:
        with check.open('x', encoding='utf-8') as f: json.dump(result, f, indent=2); f.write('\n')


if __name__ == '__main__': main()
