"""Review the sealed eight-update CPU component; never advances or decodes a state."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_plastic_hg_stage_review_r1'
SOURCE = 'c08_h18_plastic_hg_stage_r1'
OUT = T/'outputs'/SOURCE
CHECK = T/'logs'/(TAG+'.check.json')
CSV = T/'figures'/(TAG+'.csv')
PNG = T/'figures'/(TAG+'.png')

def stat(p):
    p = Path(p).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)

def table(p):
    with p.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized', action='store_true')
    assert p.parse_args().execution_authorized
    assert not any(q.exists() for q in (CHECK, CSV, PNG)), 'Preserve derived outputs'
    gatepath = T/'logs'/(SOURCE+'.check.json')
    gate = json.loads(gatepath.read_text(encoding='utf-8'))
    assert gate['passed'] and gate['consumed_stats_unchanged']
    assert gate['actual_updates'] == 8 and not gate['physical_acceptance']
    consumed = [stat(Path(__file__)), stat(gatepath)]
    for q in (gate['actual_call'], gate['completion']):
        assert stat(q['path']) == q
        consumed.append(q)
    call = json.loads(Path(gate['actual_call']['path']).read_text())
    assert call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
    assert call['ownership_failure'] is None
    for name in ('stage_nodes.csv', 'on_completed_soil.csv', 'manual_off.csv',
                 'hg_stages.csv', 'actual_work.csv'):
        q = next(q for q in gate['files'] if Path(q['path']).name == name)
        assert stat(q['path']) == q
        consumed.append(q)
    groups = defaultdict(list)
    for q in table(OUT/'stage_nodes.csv'):
        groups[(int(q['source_part']), q['mode'], int(q['update']), q['force_stage'])].append(q)
    assert len(groups) == 12 and sum(map(len, groups.values())) == 60000
    rows = []
    for (part, mode, update, stage), group in groups.items():
        assert len(group) == 5000
        assert {int(q['native_id']) for q in group} == set(range(2060, 7060))
        a = lambda k: np.array([float(q[k]) for q in group])
        da = np.column_stack((a('Ace1x')-a('Ace0x'), a('Ace1z')-a('Ace0z')))
        dr = a('new_full_rate')-a('discarded_original_rate')
        gamma = a('gamma'); counts = Counter(int(q['same_input_shadow_status']) for q in group)
        assert np.isfinite(da).all() and np.isfinite(dr).all()
        assert (gamma >= 0).all() and (gamma <= 1).all()
        assert all(q['actual_sigma_kappa_match'] == '1' for q in group)
        if mode == 'OFF':
            assert not da.any() and not dr.any()
        rows.append(dict(source_part=part, mode=mode, update=update, force_stage=stage,
            nodes=5000, elastic=counts[1], smooth=counts[2], apex=counts[3],
            tension_repair=counts[4], gamma_min=float(gamma.min()),
            gamma_mean=float(gamma.mean()), gamma_max=float(gamma.max()),
            delta_Ace_vector_RMS_m_s2=float(np.sqrt(np.mean(np.sum(da*da, axis=1)))),
            delta_Ace_vector_max_m_s2=float(np.linalg.norm(da, axis=1).max()),
            delta_rate_RMS_Pa_s=float(np.sqrt(np.mean(dr*dr))),
            delta_rate_maxabs_Pa_s=float(np.abs(dr).max())))
    body = table(OUT/'on_completed_soil.csv')
    assert len(body) == 20000
    for part in (38, 76):
        for update in (0, 1):
            g = [q for q in body if int(q['source_part']) == part and int(q['update']) == update]
            assert len(g) == 5000 and {int(q['native_id']) for q in g} == set(range(2060, 7060))
    hg = table(OUT/'hg_stages.csv'); work = table(OUT/'actual_work.csv'); off = table(OUT/'manual_off.csv')
    assert (len(hg), len(work), len(off)) == (8, 4, 2)
    assert all(q['all_match'] == '1' and int(q['field_bit_checks']) == 110000 for q in off)
    assert all(float(q['signed_dterror_s']) <= 1e-14 for q in off)
    assert all(abs(float(q['ledger'])) <= float(q['ledger_bound']) for q in hg)
    with CSV.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    fig, ax = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    labels = ('n0', 'h0', 'n1', 'h1')
    for part, color in ((38, 'tab:blue'), (76, 'tab:orange')):
        r = [q for q in rows if q['source_part'] == part and q['mode'] == 'ON']
        r.sort(key=lambda q: (q['update'], q['force_stage'] == 'h'))
        for panel, key in ((ax[0,0], 'delta_Ace_vector_RMS_m_s2'), (ax[0,1], 'delta_rate_RMS_Pa_s')):
            panel.plot(range(4), [q[key] for q in r], 'o-', color=color, label=f'P{part}, fresh HG')
        g = [q for q in hg if int(q['source_part']) == part]
        for key, style in (('ledger', 'o-'), ('ledger_bound', '--')):
            ax[1,0].plot(range(4), [abs(float(q[key])) for q in g], style, color=color,
                         label=f'P{part} '+('absolute residual' if key == 'ledger' else 'arithmetic bound'))
        w = [q for q in work if int(q['source_part']) == part]
        ax[1,1].plot(range(2), [float(q['observed_full_discrete_defect_not_gate']) for q in w], 'o-',
                     color=color, label=f'P{part}')
    ax[0,0].set_ylabel('Added HG acceleration RMS [m/s2]')
    ax[0,1].set_ylabel('Conditional Darcy rate change RMS [Pa/s]')
    ax[1,0].set_ylabel('Fixed-stage HG ledger [J/m]'); ax[1,0].set_yscale('log')
    ax[1,1].set_ylabel('Actual full-step HG work defect [J/m]')
    ax[1,1].set_xticks((0,1), ('full0','full1')); ax[1,1].axhline(0, color='k', lw=.6)
    for a in (ax[0,0], ax[0,1], ax[1,0]): a.set_xticks(range(4), labels)
    for a in ax.flat: a.grid(alpha=.25); a.legend(fontsize=8)
    fig.suptitle('Two cold-HG actual CPU steps at each retained state, dt=5 us\nImplementation feasibility; no clump-repair or coupled-energy acceptance')
    fig.savefig(PNG, dpi=160); plt.close(fig)
    assert all(stat(q['path']) == q for q in consumed)
    result = dict(stage=TAG, passed=True, analysis_complete=True, stage_node_rows=60000,
        completed_soil_rows=20000, groups=rows, consumed=consumed,
        consumed_stats_unchanged=True, files=[stat(CSV), stat(PNG)],
        visual_QA_pending=True, physical_acceptance=False, solver_invocations=0,
        native_invocations=0, build_invocations=0, SHA_scans=0)
    with CHECK.open('x', encoding='utf-8') as f: json.dump(result, f, indent=2, allow_nan=False)

if __name__ == '__main__': main()
