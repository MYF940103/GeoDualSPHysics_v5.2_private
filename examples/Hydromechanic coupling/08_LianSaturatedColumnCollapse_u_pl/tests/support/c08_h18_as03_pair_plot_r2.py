"""Repair only the local trajectory view from the completed pair CSV; no native reanalysis."""
from pathlib import Path
import csv,json,datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1]
TAG='c08_h18_as03_pair_plot_r2'
PAIRS=((6767,6865),(4953,4954))
def stat(p):
 s=p.stat();return dict(path=str(p.resolve()),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def main():
    src=T/'figures/c08_h18_as03_pair_review_r1_history.csv'
    summary=T/'figures/c08_h18_as03_pair_review_r1_summary.json'
    checked=json.loads(summary.read_text(encoding='utf-8'));assert checked['analysis_complete']
    assert stat(src)==next(q for q in checked['outputs'] if Path(q['path']).resolve()==src.resolve())
    plot_path=T/'figures'/(TAG+'.png');check=T/'logs'/(TAG+'.check.json')
    assert not plot_path.exists() and not check.exists()
    with src.open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
    fields=('tau_s','pair_distance_over_dp','pair_closing_m_s','p_Pa','total_pair_normal_Pa','kappa','J','x_m','z_m')
    for row in rows:
        row['native_id']=int(row['native_id'])
        for key in fields:row[key]=float(row[key]) if row[key] else None
    per_id={identity:[q for q in rows if q['phase']=='collapse' and q['native_id']==identity] for pair in PAIRS for identity in pair}
    assert all(len(q)==301 for q in per_id.values())
    references={'source_PRE':{identity:{'row':next(q for q in rows if q['phase']=='source_PRE' and q['native_id']==identity)} for identity in per_id}}
    fig, axes = plt.subplots(5, 2, figsize=(15, 20), layout='constrained')
    colors = ('#2467ac', '#b94724')
    for col, (a, b) in enumerate(PAIRS):
        aa, bb = per_id[a], per_id[b]; tau = [q['tau_s'] for q in aa]
        pre_a, pre_b = references['source_PRE'][a]['row'], references['source_PRE'][b]['row']
        axes[0, col].plot(tau, [q['pair_distance_over_dp'] for q in aa], color='#333333', lw=1.7)
        axes[0, col].scatter([0], [pre_a['pair_distance_over_dp']], marker='s', color='black', s=22, label='Actual PRE reference')
        axes[0, col].axhline(.7, color='#b94724', ls=':', lw=1, label='Descriptive r/dp = 0.7')
        axes[0, col].set(title=f'Fixed material pair {a}/{b}', ylabel='Saved pair distance / dp'); axes[0, col].legend(fontsize=8)
        axes[1, col].plot(tau, [q['pair_closing_m_s'] for q in aa], color='#333333', lw=1.2)
        axes[1, col].axhline(0, color='black', lw=.6); axes[1, col].set(ylabel='Closing speed [m/s]\npositive = approach')
        for rows, pre_row, color, identity in ((aa, pre_a, colors[0], a), (bb, pre_b, colors[1], b)):
            axes[2, col].plot(tau, [q['p_Pa']/1000 for q in rows], color=color, label=f'{identity} p')
            axes[2, col].plot(tau, [q['total_pair_normal_Pa']/1000 if q['total_pair_normal_Pa'] is not None else np.nan for q in rows],
                              color=color, ls='--', label=f'{identity} total sigma along pair')
            axes[3, col].plot(tau, [q['kappa'] for q in rows], color=color, label=f'{identity} kappa')
            axes[4, col].plot([q['x_m'] for q in rows], [q['z_m'] for q in rows], color=color, label=str(identity))
            axes[4, col].scatter([pre_row['x_m']], [pre_row['z_m']], color=color, marker='s', s=25)
            axes[4, col].scatter([rows[-1]['x_m']], [rows[-1]['z_m']], color=color, marker='x', s=35)
        axes[2, col].set(ylabel='Pressure / pair stress [kPa]\nstress tension positive'); axes[2, col].legend(fontsize=8)
        axes[3, col].set(ylabel='Plastic history kappa')
        twin = axes[3, col].twinx()
        for rows, color, identity in ((aa, colors[0], a), (bb, colors[1], b)):
            twin.plot(tau, [q['J'] for q in rows], color=color, ls='--', lw=1.1, label=f'{identity} J')
        twin.set_ylabel('J, dashed'); lines, labels = axes[3, col].get_legend_handles_labels(); rlines, rlabels = twin.get_legend_handles_labels()
        axes[3, col].legend(lines+rlines, labels+rlabels, fontsize=8, ncol=2)
        for row in range(4):
            axes[row, col].set_xlabel('Actual saved time since PRE [s]'); axes[row, col].grid(alpha=.2)
        if col == 0:
            axes[4, col].axhline(0, color='black', ls=':', lw=.8, label='Bed wall plane z=0')
        else:
            axes[4, col].text(.02, .02, 'Bed plane z=0 lies outside this local view', transform=axes[4, col].transAxes, fontsize=8)
            axes[4, col].set_xlim(min(q['x_m'] for q in aa+bb)-.02, max(q['x_m'] for q in aa+bb)+.02)
            axes[4, col].set_ylim(min(q['z_m'] for q in aa+bb)-.02, max(q['z_m'] for q in aa+bb)+.02)
        axes[4, col].set(xlabel='x [m]', ylabel='z above bed plane [m]', title='All saved XZ positions; square=PRE, cross=last')
        axes[4, col].set_aspect('equal'); axes[4, col].legend(fontsize=8); axes[4, col].grid(alpha=.2)
    fig.suptitle('AS0.3 / n2.55: two fixed-material pairs, original 301 saved states\nSaved pressure/stress/closing correlations cannot establish substage causation; no physical acceptance', fontsize=13)
    fig.savefig(plot_path, dpi=180, bbox_inches='tight'); plt.close(fig)
    with check.open('x',encoding='utf-8') as f:json.dump(dict(stage=TAG,passed=True,derived_plot_only=True,physical_acceptance=False,input_CSV=stat(src),original_summary=stat(summary),script=stat(Path(__file__)),output=stat(plot_path),original_PNG_preserved=True,change='Local high-wall pair view does not autoscale to remote bed z=0; all curves/values unchanged',decoder_invocations=0,solver_invocations=0,SHA_scans=0,visual_QA_pending=True),f,indent=2)
if __name__=='__main__':main()
