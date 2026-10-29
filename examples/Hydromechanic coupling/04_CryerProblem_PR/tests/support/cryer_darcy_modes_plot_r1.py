"""Plot the completed fixed-radius scalar Darcy mode screen; no solver or CSV."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cryer_start_r1 import TESTS, bound

source = TESTS/'logs/cryer_darcy_modes_r1.check.json'
output = TESTS/'figures/cryer_darcy_modes_r1.png'
assert not output.exists(), 'Preserve retained figure'
before = bound(source)
record = json.loads(source.read_text(encoding='utf-8-sig'))
assert record['analysis_checks_passed'] and record['before_after_hashes_verified']
assert record['integrated_steps'] == 0 and not record['physical_acceptance']
assert record['geometry']['actual_boundary_radius_m'] == .05
plt.rcParams.update({'font.family': 'Arial', 'font.size': 10, 'axes.grid': True, 'grid.alpha': .2})
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
for name, label, color in [('receiver_C', 'Receiver C', '#1f77b4'), ('symmetric_C', 'Symmetric C', '#d95f02')]:
    rows = sorted((r for r in record['projection_rows'] if r['operator'] == name), key=lambda r: r['mode'])
    assert [r['mode'] for r in rows] == [1, 2, 3]
    x = [r['mode'] for r in rows]
    for ax, field in zip(axes, ['projected_over_exact', 'exact_pairing_relative_rhs_error']):
        y = [100*r[field] for r in rows]
        ax.plot(x, y, 'o-', color=color, label=label, lw=1.5)
        for mode, value in zip(x, y):
            ax.annotate(f'{value:.2f}', (mode, value), xytext=(0, 7), textcoords='offset points', ha='center', fontsize=9)
        ax.set_xticks([1, 2, 3]); ax.set_xlabel('Radial Dirichlet mode n')
axes[0].axhline(100, color='.4', ls=':', label='Exact scalar decay')
axes[0].set_ylim(80, 105); axes[0].set_ylabel('Projected decay / exact scalar decay (%)')
axes[1].set_ylim(0, 72); axes[1].set_ylabel('Exact scalar RHS relative error (%)')
axes[0].legend(fontsize=9)
fig.suptitle('Cryer geometry: frozen scalar Darcy mode projections', fontsize=13)
fig.text(.5, .02, 'Actual R=0.05 m; Dirichlet neighbours retained. Not coupled Cryer eigenvalues or dynamic peak acceptance.', ha='center', fontsize=9)
fig.tight_layout(rect=(0, .07, 1, .94))
assert bound(source) == before
fig.savefig(output, dpi=180); plt.close(fig)
print(json.dumps(dict(source=before, figure=bound(output))))
