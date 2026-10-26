"""Independent saved-native 15-s review; no solver, interpolation or old edits."""
from concurrent.futures import ThreadPoolExecutor
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lian_release_r1 import TESTS, READER, bound, native, write_json, utc
from lian_drained_review_r1 import verify
from lian_mirror_review_r1 import sample

TAG = 'lian_mirror15_review_r1'


def main():
    receipt = TESTS/'logs'/(TAG+'.check.json')
    assert not receipt.exists()
    status = TESTS/'logs/lian_mirror15_r1.status.json'
    state = json.loads(status.read_text())
    assert state['status'] == 'pair_passed_pending_late_physical_review'
    assert state['half']['passed'] and state['half']['sample_pairs'] == 301
    verify(state)
    short_path = TESTS/'logs/lian_mirror_review_r1.check.json'
    short = json.loads(short_path.read_text())
    assert short['passed'] and short['visual_review_passed']
    verify(short)
    strict_path = TESTS/'logs/lian_late15_r1.run.json'
    strict = json.loads(strict_path.read_text())
    assert strict['solver_exit_code'] == 0 and strict['owned_exited']
    # Strict historical source paths now contain the candidate; preserve their
    # historical hashes, but independently verify the retained raw output bytes.
    verify({k: strict[k] for k in ('outputs', 'artifacts')})
    assert bound(strict['log']['path'])['sha256'] == strict['log']['sha256']
    sources = [bound(p) for p in [__file__, status, short_path, strict_path, READER,
        TESTS/'scripts/lian_release_r1.py', TESTS/'scripts/lian_mirror_review_r1.py']]
    folders = {'mirror_c': TESTS/'outputs/lian_mirror15_r1_c',
               'mirror_h': TESTS/'outputs/lian_mirror15_r1_h',
               'strict_c': TESTS/'outputs/lian_late15_r1'}
    for run, item in zip(['mirror_c', 'mirror_h'], state['runs']):
        assert item['name'] == folders[run].name
        assert item['exit_code'] == 0 and item['owned_exited']
        assert item['saved_frames'] == 301 and item['all_saved_native_checks_passed']
        assert abs(item['actual_final_time_s']-15) < 2e-5
        verify(item)
        assert bound(item['log']['path'])['sha256'] == item['log']['sha256']
    for folder in folders.values():
        text = (folder/'Run.out').read_text(errors='replace')
        assert 'Finished execution (code=0)' in text and 'NVIDIA GeForce RTX 3050' in text
        sources.append(bound(folder/'Run.out'))
    origins = {k: native(p, 0) for k, p in folders.items()}
    origin = origins['mirror_c']
    assert len(origin) == 20301
    for other in origins.values():
        assert np.array_equal(origin.id, other.id)
        assert np.array_equal(origin[['x','y','z']], other[['x','y','z']])
    top = origin.z.gt(9.99).to_numpy()
    rows, pairs, prefixes = [], [], []
    final = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for i in range(301):
            data = dict(zip(folders, pool.map(lambda p: native(p, i), folders.values())))
            for run, a in data.items():
                dt = 5e-6 if run == 'mirror_h' else 1e-5
                row = sample(a, origins[run], dt, run.startswith('mirror'))
                w = a.loc[a.id.eq(1744)].iloc[0]
                row.update(run=run, part=i, step=int(a.saved_step.iloc[0]),
                    pressure_max_pa=float(a.pressure.max()),
                    pressure_rms_pa=float(np.sqrt(np.mean(a.pressure**2))),
                    sigma_xx_rms_pa=float(np.sqrt(np.mean(a.sigma_xx**2))),
                    id1744_contact=bool(abs(w.x) <= 1.25 if run.startswith('mirror') else 0 <= w.x <= 1.25),
                    id1744_drained=bool(row['drainage_active'] and w.fstype in [2,3] and
                        not (abs(w.x) <= 1.25 if run.startswith('mirror') else 0 <= w.x <= 1.25)),
                    id1744_fstype=int(w.fstype), id1744_vx_m_s=float(w.vx), id1744_vz_m_s=float(w.vz))
                for point in ['A','B']:
                    k = int(np.flatnonzero(origin.id.eq(row[point+'_id']))[0])
                    row[point+'_ux_mm'] = 1000*float(a.x.iloc[k]-origin.x.iloc[k])
                rows.append(row)
                if i <= 60 and run.startswith('mirror'):
                    ref_folder = TESTS/'outputs'/('lian_mirror_short_r2_drained_'+run[-1])
                    ref = native(ref_folder, i)
                    shared = (float(a.time_s.iloc[0]) == float(ref.time_s.iloc[0]) and
                              int(a.saved_step.iloc[0]) == int(ref.saved_step.iloc[0]))
                    if shared:
                        assert list(a.columns) == list(ref.columns)
                        assert np.array_equal(a.to_numpy(), ref.to_numpy()), (run, i)
                    else:
                        assert i == 60, (run, i, 'Nonfinal prefix mismatch')
                    prefixes.append(dict(run=run, part=i, time_s=float(a.time_s.iloc[0]),
                        reference_time_s=float(ref.time_s.iloc[0]), all_native_fields_0ulp=shared))
            c, h, old = data['mirror_c'], data['mirror_h'], data['strict_c']
            assert float(c.time_s.iloc[0]) == float(old.time_s.iloc[0])
            assert int(c.saved_step.iloc[0]) == int(old.saved_step.iloc[0])
            assert abs(float(c.time_s.iloc[0]-h.time_s.iloc[0])) <= 1.01e-5
            p = float(np.sqrt(np.mean((c.pressure-h.pressure)**2)))
            u = float(1000*np.max(abs(c.z.to_numpy()[top]-h.z.to_numpy()[top])))
            assert p <= 5 and u <= .005, (i, p, u)
            pairs.append(dict(part=i, coarse_time_s=float(c.time_s.iloc[0]),
                half_time_s=float(h.time_s.iloc[0]), strict_time_s=float(old.time_s.iloc[0]),
                half_pressure_rms_pa=p, half_top_material_mm=u,
                strict_pressure_rms_difference_pa=float(np.sqrt(np.mean((c.pressure-old.pressure)**2))),
                strict_sigma_zz_rms_difference_pa=float(np.sqrt(np.mean((c.sigma_zz-old.sigma_zz)**2))),
                strict_top_material_max_difference_mm=float(1000*np.max(abs(c.z.to_numpy()[top]-old.z.to_numpy()[top])))))
            if i == 300:
                final = data
            if i % 30 == 0:
                print('Independent native review through part', i, flush=True)
    history, paired, prefix = pd.DataFrame(rows), pd.DataFrame(pairs), pd.DataFrame(prefixes)
    assert prefix.groupby('run').all_native_fields_0ulp.sum().eq(61).all()
    assert abs(paired.half_pressure_rms_pa.max()-state['half']['pressure_rms_max_pa']) < 1e-12
    assert abs(paired.half_top_material_mm.max()-state['half']['top_material_max_mm']) < 1e-12
    artifacts = []

    def csv(name, frame):
        p = TESTS/'figures'/(TAG+'_'+name+'.csv')
        assert not p.exists()
        frame.to_csv(p, index=False, float_format='%.17g')
        artifacts.append(bound(p))

    def png(name, figure):
        p = TESTS/'figures'/(TAG+'_'+name+'.png')
        assert not p.exists()
        figure.savefig(p, dpi=160)
        plt.close(figure)
        artifacts.append(bound(p))

    csv('history', history)
    csv('pairs', paired)
    csv('prefix', prefix)
    styles = [('strict_c','#555555',':'), ('mirror_c','#215a8a','-'), ('mirror_h','#b56b28','--')]
    for figure_name, columns, labels, scales, layout in [
        ('history', ['A_pressure_pa','B_pressure_pa','A_settlement_mm','B_settlement_mm','pressure_mean_pa','sigma_zz_rms_pa'],
         ['A pressure (kPa)','B pressure (kPa)','A material settlement (mm)','B material settlement (mm)','Soil mean pressure (kPa)','Vertical stress RMS (kPa)'], [.001,.001,1,1,.001,.001], (2,3)),
        ('contact', ['id1744_x_m','id1744_pressure_pa','force_N_m','vmax_m_s','pressure_min_pa','loaded_count'],
         ['Native1744 x (micrometres)','Native1744 pressure (kPa)','Actual applied force (kN/m)','Maximum soil speed (m/s)','Minimum soil pressure (kPa)','Loaded native-node count'], [1e6,.001,.001,1,.001,1], (3,2))]:
        fig, axes = plt.subplots(*layout, figsize=(14,8.5), layout='constrained')
        for run, color, line in styles:
            d = history[history.run.eq(run)]
            for ax, col, label, scale in zip(axes.flat, columns, labels, scales):
                ax.plot(d.time_s, d[col]*scale, line, color=color, label=run)
                ax.set(xlabel='Actual saved time (s)', ylabel=label, xlim=(0,15), xticks=[0,3,6,9,12,15])
                ax.grid(alpha=.2)
        axes.flat[0].legend()
        fig.suptitle('Lian 15-s mirrored-contact review: same-dt strict control and independent half step\nOriginal 13-node load quadrature retained (+4% width); NOT 100-s/FEM acceptance')
        png(figure_name, fig)
    c, old = final['mirror_c'], final['strict_c']
    fields = pd.DataFrame(dict(id=origin.id, x0_m=origin.x, z0_m=origin.z,
        mirror_pressure_pa=c.pressure, strict_pressure_pa=old.pressure,
        pressure_difference_pa=c.pressure-old.pressure,
        mirror_sigma_zz_pa=c.sigma_zz, strict_sigma_zz_pa=old.sigma_zz,
        mirror_settlement_mm=1000*(origin.z-c.z), strict_settlement_mm=1000*(origin.z-old.z)))
    csv('fields', fields)
    fig, axes = plt.subplots(1,3, figsize=(14,4.8), layout='constrained')
    common = max(abs(fields[['strict_pressure_pa','mirror_pressure_pa']].to_numpy()).max(), 1.)/1000
    for ax, col, title in zip(axes, ['strict_pressure_pa','mirror_pressure_pa','pressure_difference_pa'],
                            ['Strict control pressure (kPa)','Mirrored pressure (kPa)','Mirror minus strict (kPa)']):
        limit = max(abs(fields[col]).max()/1000, 1e-9) if col == 'pressure_difference_pa' else common
        artist = ax.tricontourf(origin.x, origin.z, fields[col]/1000,
            levels=np.linspace(-limit,limit,31), cmap='RdBu_r', extend='both')
        ax.set(title=title, xlabel='Initial material x (m)', ylabel='Initial material z (m)', aspect='equal')
        fig.colorbar(artist, ax=ax, shrink=.75)
    fig.suptitle('Native-ID pressure at actual 15.00001 s; common pressure scale, separate difference scale')
    png('fields', fig)
    summaries = {}
    for run in folders:
        d = history[history.run.eq(run)]
        after = d[d.source_prior_time_s.ge(1)]
        changes = d.id1744_contact.astype(int).diff().fillna(0).ne(0)
        summaries[run] = dict(actual_final_time_s=float(d.time_s.iloc[-1]),
            minimum_pressure_pa=float(d.pressure_min_pa.min()), maximum_speed_m_s=float(d.vmax_m_s.max()),
            postramp_force_min_N_m=float(after.force_N_m.min()), postramp_force_max_N_m=float(after.force_N_m.max()),
            postramp_loaded_counts=sorted(after.loaded_count.unique().astype(int).tolist()),
            id1744_contact_transitions=int(changes.sum()),
            id1744_drained_samples=int(d.id1744_drained.sum()), final=d.iloc[-1].to_dict())
    active = history[history.run.str.startswith('mirror') & history.drainage_active]
    assert len(active) and active.drained_abs_max_pa.eq(0).all()
    assert all(summaries[k]['id1744_contact_transitions'] == 0 and
               summaries[k]['postramp_loaded_counts'] == [13] and
               summaries[k]['minimum_pressure_pa'] >= 0 for k in ['mirror_c','mirror_h'])
    result = dict(passed=True, visual_review_passed=False, late_contact_repair_accepted=False,
        physical_full_cycle_accepted=False, utc=utc(), summary=summaries,
        half=dict(samples=len(paired), pressure_rms_max_pa=float(paired.half_pressure_rms_pa.max()),
                  top_material_max_mm=float(paired.half_top_material_mm.max())),
        prefix0ulp_frames_per_run=61, same_dt_strict_matching_frames=301,
        active_drained_node_samples=int(active.potential_drained_count.sum()),
        active_drained_abs_pressure_max_pa=float(active.drained_abs_max_pa.max()),
        sources=sources, artifacts=artifacts, limits=[
            'Saved .05-s samples do not resolve every integration step; the earlier dense startup and independent short tests remain separate evidence.',
            'Only the mode4 symmetry-edge footprint changed. The original 13-node/1.3-m quadrature remains +4% versus ideal 1.25 m.',
            'Strict comparison is same-dt/current double stress, not a legacy float precision-only comparison.',
            'A/B are retained nearest material IDs; paper-location mapping must be checked before formal reference comparisons.',
            '15-s/half agreement and contact repair do not establish 100-s/FEM, general-contact or mixed-slip SPR acceptance.'])
    write_json(receipt, result)
    print(json.dumps(dict(half=result['half'], summaries={k:{n:v for n,v in s.items() if n != 'final'}
        for k,s in summaries.items()}), indent=2), flush=True)


if __name__ == '__main__':
    main()
