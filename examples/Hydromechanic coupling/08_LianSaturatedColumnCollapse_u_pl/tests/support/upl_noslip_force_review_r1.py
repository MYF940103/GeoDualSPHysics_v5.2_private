"""Plot closed instantaneous force components; never invoke a physical solver."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
tag = 'upl_noslip_force_review_r1'
png, csv = (T/'figures'/f'{tag}.{ext}' for ext in ('png', 'csv'))
assert not png.exists() and not csv.exists(), 'Review existing results instead of overwriting'
fig, axes = plt.subplots(1, 2, figsize=(10, 3.7), sharey=True)
tables, summaries = [], {}
for ax, kernel in zip(axes, ('Wendland', 'Cubic')):
    folder = T/'outputs'/f'upl_noslip_force_CPU_{kernel}_r2'
    check = json.loads((T/'logs'/f'upl_noslip_force_CPU_{kernel}_r2.check.json').read_text(encoding='utf-8-sig'))
    assert check['passed']
    pos = pd.read_csv(T/'outputs'/f'upl_noslip_CPU_{kernel}_r1/native_ids.csv')
    assert len(pos) == 1024 and pos.native_id.is_unique
    summaries[kernel] = pd.read_csv(folder/'summary.csv').to_dict('records')
    for mode, color, style in [('FS', '#0072B2', '-'), ('NS', '#D55E00', '--'), ('mixed', '#009E73', ':')]:
        data = pd.read_csv(folder/f'{mode}_force.csv')
        assert len(data) == 1024 and set(data.native_id) == set(pos.native_id)
        data = data.merge(pos[['native_id', 'x0']], on='native_id', validate='one_to_one')
        profile = data.groupby('x0', as_index=False).agg(az_mean=('actual_az', 'mean'), az_min=('actual_az', 'min'), az_max=('actual_az', 'max'), count=('native_id', 'size'))
        assert len(profile) == 32 and np.all(profile['count'] == 32)
        profile.insert(0, 'kernel', kernel); profile.insert(1, 'mode', mode); tables.append(profile)
        ax.plot(profile.x0/(1/16), profile.az_mean, style, color=color, lw=1.8, label=mode)
    ax.set(title=kernel, xlabel='Initial x / slab width')
    ax.grid(alpha=.25); ax.legend(title='Wall slip', frameon=False)
axes[0].set_ylabel('Native mean $a_z$ [m/s$^2$]')
fig.suptitle('Instantaneous response to prescribed shear stress $\\tau_{xz}=8$ Pa')
fig.text(.5, .015, 'Zero physical steps; mixed = left NoSlip / right FreeSlip. No transient or collapse acceptance.', ha='center', fontsize=8)
fig.tight_layout(rect=(0, .05, 1, .94)); fig.savefig(png, dpi=180); plt.close(fig)
pd.concat(tables, ignore_index=True).to_csv(csv, index=False, float_format='%.17g')
note = {'stage': tag, 'source_checks_passed': True, 'profile_rows': 192, 'native_receivers_each_condition': 1024,
        'summary': summaries, 'force_units': 'Raw _N headers use the 2D unit-thickness convention; report reactions as N/m.',
        'physical_steps': 0, 'physical_acceptance': False, 'SHA_scans': 0}
(T/'notes'/f'{tag}.json').write_text(json.dumps(note, indent=2)+'\n', encoding='utf-8')
print('REVIEW_COMPLETE', png.name, csv.name)
