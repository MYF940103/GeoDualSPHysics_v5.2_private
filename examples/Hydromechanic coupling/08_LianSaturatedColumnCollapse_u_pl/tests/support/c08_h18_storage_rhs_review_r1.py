"""Offline figures of three completed-state CPU RHS probes, never advance a state."""
import argparse, csv, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_storage_rhs_review_r1'
SRC = T / 'outputs/c08_h18_storage_rhs_r2'
TERMS = ['compression', 'LP', 'Taylor_pressure', 'Da', 'FS_Ace_Lx', 'chain_pressure', 'chain_Ace']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized', action='store_true')
    assert p.parse_args().execution_authorized
    check = T / 'logs' / (TAG + '.check.json')
    outputs = [T / 'figures' / (TAG + s) for s in ('_terms.png', '_fields.png', '_summary.csv')]
    assert not check.exists() and not any(q.exists() for q in outputs), 'Existing review protected'
    sources = [Path(__file__), SRC/'completion.json', SRC/'summary.csv', SRC/'soil_rhs.csv', SRC/'terms.csv',
               T/'logs/c08_h18_storage_rhs_r2.check.json']
    before = [dict(path=str(q), bytes=q.stat().st_size, mtime_ns=q.stat().st_mtime_ns) for q in sources]
    completed = json.loads(sources[1].read_text())
    assert completed['passed'] and completed['physical_steps'] == 0 and completed['actual_force_calls'] == 3
    assert json.loads(sources[-1].read_text())['passed']
    summary = list(csv.DictReader(sources[2].open()))
    soil = np.genfromtxt(sources[3], delimiter=',', names=True, dtype=None, encoding='utf-8')
    terms = list(csv.DictReader(sources[4].open()))
    assert len(summary) == 27 and len(soil) == 15000 and len(terms) == 45000
    reduced, records = [], []
    fig, axes = plt.subplots(1, 3, figsize=(17, 5), constrained_layout=True)
    for axis, part in zip(axes, (30, 60, 90)):
        rows = [q for q in summary if int(q['part']) == part and q['receiver_group'] == 'all']
        assert len(rows) == 3 and {q['donor_group'] for q in rows} == {'all', 'fluid_donors', 'fixed_donors'}
        full = next(q for q in rows if q['donor_group'] == 'all')
        state = soil[soil['part'] == part]
        assert len(state) == 5000 and len(np.unique(state['native_id'])) == 5000
        assert np.array_equal(np.sort(state['native_id']), np.arange(2060, 7060))
        weight = float(full['sum_weight'])
        comp = float(full['compression_Q_m2_s']) / weight / 1000
        hydro = sum(float(full[q+'_Q_m2_s']) for q in TERMS[1:]) / weight / 1000
        actual = float(full['actual_Q_all_only_m2_s']) / weight / 1000
        reduced.append(dict(part=part, tau_s=float(full['tau_s']), storage_weight=weight,
                            weighted_actual_rate_kPa_s=actual, weighted_compression_rate_kPa_s=comp,
                            weighted_hydraulic_rate_kPa_s=hydro,
                            conditional_storage_derivative_m2_s=float(full['conditional_storage_derivative_all_only_m2_s']),
                            saved_FS_changes=int(full['saved_FS_changes'])))
        for j, row in enumerate(rows):
            vals = [float(row[q+'_Q_m2_s']) / weight / 1000 for q in TERMS]
            axis.bar(np.arange(7)+(j-1)*.25, vals, width=.25, label=row['donor_group'])
        axis.axhline(0, color='black', lw=.7)
        axis.set_xticks(np.arange(7), TERMS, rotation=65, ha='right')
        axis.set_title(f"tau={float(full['tau_s']):.6f} s; net {actual:.2f} kPa/s")
        axis.set_ylabel('Storage-weighted signed rate contribution [kPa/s]')
        axis.grid(axis='y', alpha=.2)
        state_terms = [q for q in terms if int(q['part']) == part and q['donor_group'] == 'all']
        by_id = {int(q['native_id']): q for q in state_terms}
        assert len(by_id) == 5000
        c = np.array([float(by_id[int(i)]['compression_Pa_s']) for i in state['native_id']]) / 1000
        h = np.array([sum(float(by_id[int(i)][q+'_Pa_s']) for q in TERMS[1:]) for i in state['native_id']]) / 1000
        records.append((state, c, h))
    axes[0].legend(fontsize=8)
    fig.suptitle('Fresh CPU corrector-mode evaluations on saved GPU states; no physical advance\n'
                 'Donor partitions are additive bookkeeping; storage proxy is not water mass')
    fig.savefig(outputs[0], dpi=180); plt.close(fig)
    fig, axes = plt.subplots(3, 4, figsize=(18, 11), constrained_layout=True)
    names = ['Absolute pore pressure [kPa]', 'Compression rate [kPa/s]', 'Hydraulic rate [kPa/s]', 'Actual rate [kPa/s]']
    arrays = [[r[0]['p_Pa']/1000, r[1], r[2], r[0]['actual_rate_Pa_s']/1000] for r in records]
    for j, name in enumerate(names):
        extreme = max(np.max(np.abs(a[j])) for a in arrays)
        norm = SymLogNorm(linthresh=max(extreme/1000, .001), vmin=-extreme, vmax=extreme)
        for i, (state, _, _) in enumerate(records):
            ax = axes[i, j]
            sc = ax.scatter(state['x_m'], state['z_m'], c=arrays[i][j], s=3, cmap='coolwarm', norm=norm)
            ax.set_aspect('equal'); ax.set_xlabel('x [m]'); ax.set_ylabel('z [m]')
            ax.set_title(f"tau={float(state['tau_s'][0]):.6f} s; {name}", fontsize=9)
        fig.colorbar(sc, ax=axes[:, j], shrink=.65, label=name)
    fig.suptitle('All 5000 material particles; shared symmetric-log scales retain every extreme\n'
                 'Fresh CPU RHS is not a replay of the omitted GPU force substages')
    fig.savefig(outputs[1], dpi=180); plt.close(fig)
    with outputs[2].open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(reduced[0])); w.writeheader(); w.writerows(reduced)
    for q in before:
        s = Path(q['path']).stat(); assert (s.st_size,s.st_mtime_ns)==(q['bytes'],q['mtime_ns'])
    def stat(q): return dict(path=str(q), bytes=q.stat().st_size, mtime_ns=q.stat().st_mtime_ns)
    check.write_text(json.dumps(dict(stage=TAG, analysis_complete=True, consumed=before,
        consumed_stats_unchanged=True, outputs=[stat(q) for q in outputs], reduced=reduced,
        physical_acceptance=False, physical_steps=0, native_decodes=0, SHA_scans=0),indent=2)+'\n')


if __name__ == '__main__': main()
