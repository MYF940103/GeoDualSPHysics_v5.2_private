"""One offline full301 review; original gates, real PRE+1, no old-case reanalysis."""
import argparse, json, struct
from pathlib import Path
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize, TwoSlopeNorm
import c08_h18_n255_review_r1 as narrow
import c08_h18_material_map_r1 as material

core, old = narrow.core, narrow.old
np, T, need, stat, read, table, bind = old.np, old.T, old.need, old.stat, old.read, old.table, old.bind
TAG = 'c08_h18_n255_full3_review_r1'
RUN = 'c08_h18_n255_full3_r1'
BUILD = T / 'logs/c08_h18_as255_native_r1.build.json'
NOTE = T / 'notes' / (TAG + '.md')
SNAPSHOTS = [.3, .6, .9, 1.2, 2., 3.]
CONTROL = 'c08_h18_as05_n255_r1'


def receiver(spec, source, source_spec, consumed):
    need(spec['tag'] == RUN and old.f32(spec['actualAS']['coefficient']) == old.f32(.5)
         and old.f32(spec['actualAS']['exponent']) == old.f32(2.55), 'Exact completed full3 AS.5/n2.55 required')
    saved_build, saved_profile = core.BUILD, core.profile_xml
    try:
        core.BUILD, core.profile_xml = BUILD, narrow.profile_xml_n255
        bundle = core.load_receiver(spec, source, source_spec, consumed)
    finally:
        core.BUILD, core.profile_xml = saved_build, saved_profile
    need(bundle['count'] == 301 and bundle['runtime_observed']['passed'], 'Genuine completed formal301 required')
    return bundle


def retained_prefix(bundle, analysis, consumed):
    """Compare bytes once, then retained metrics only; never reconstruct the old91 run."""
    receipt = T / 'logs/c08_h18_n255_review_r1.check.json'
    check = read(receipt)
    need(check['analysis_complete'] and not check['physical_acceptance'], 'Retained descriptive review required')
    consumed.append(stat(receipt))
    root = T / 'outputs' / CONTROL / 'native_r1'
    for leaf in ('completion.json', 'typed22.bin', 'typed22_layout.csv', 'clocks.csv'):
        q = root / leaf
        entry = next(v for v in check['consumed'] if old.path(v['path']) == q.resolve())
        consumed.append(bind(entry))
    done = read(root / 'completion.json')
    need(done['passed'] and done['samples'] == 91 and done['completed_steps'] == 2180000, 'Original completed91 stays91')
    raw, previous = bundle['root'] / 'typed22.bin', root / 'typed22.bin'
    with previous.open('rb') as a, raw.open('rb') as b:
        h_old, h_new = struct.unpack('<III', a.read(12)), struct.unpack('<III', b.read(12))
        need(h_old == (6805, 22, 91) and h_new == (6805, 22, 301), 'Preserve genuine distinct91/301 headers')
        size = 90 * bundle['frames'].dtype.itemsize
        remaining = size
        while remaining:
            width = min(4 * 1024 * 1024, remaining)
            aa, bb = a.read(width), b.read(width)
            need(len(aa) == len(bb) == width and aa == bb, 'First90 actual typed records are not byte-identical')
            remaining -= width
    need((root / 'typed22_layout.csv').read_bytes() == (bundle['root'] / 'typed22_layout.csv').read_bytes(),
         'Literal22 layouts differ')
    prior_clock = table(root / 'clocks.csv')
    need(len(prior_clock) == 91 and prior_clock[:90] == bundle['clocks'][:90], 'First90 signed-clock rows differ')
    need(int(prior_clock[90]['completed_step']) == 2180000
         and int(bundle['clocks'][90]['completed_step']) == 2180001, 'Forced old final must remain unshared')
    csvpath = T / 'figures/c08_h18_n255_review_r1_history.csv'
    entry = next(v for v in check['files'] if old.path(v['path']) == csvpath.resolve())
    consumed.append(bind(entry))
    previous_rows = [q for q in table(csvpath) if q['tag'] == CONTROL]
    need(len(previous_rows) == 91, 'Exactly91 retained n255 history rows required')
    lookup = {(int(q['completed_step']), float(q['time_s'])): q for q in previous_rows}
    keys = ('p_min_Pa', 'p_max_Pa', 'p_RMS_Pa', 'native_p_minus_fixedP0_RMS_Pa',
            'effective_stress_Frobenius_RMS_Pa', 'total_stress_Frobenius_RMS_Pa', 'velocity_RMS_m_s',
            'current_mixture_KE_J_per_m', 'max_kappa', 'min_J', 'max_J', 'min_n', 'max_n',
            'min_rho', 'max_rho', 'min_k_m_s', 'max_k_m_s', 'front_x_m',
            'top_material_settlement_mm', 'bottom_material_settlement_mm', 'NN_min_over_dp',
            'NN_q05_over_dp', 'pairs_r_lt_0p7dp')
    matched = []
    for q in analysis['history']:
        key = (q['completed_step'], q['time_s'])
        if key not in lookup: continue
        before = lookup[key]
        row = dict(part=q['part'], old_part=int(before['part']), completed_step=key[0], time_s=key[1], tau_s=q['tau_s'])
        for name in keys: row[name + '_minus_retained'] = q[name] - float(before[name])
        matched.append(row)
    need(len(matched) == 90 and [q['part'] for q in matched] == list(range(90)), 'Only real common parts0..89 may match')
    return matched, dict(old_header=list(h_old), new_header=list(h_new), compared_records=90,
        compared_typed_record_bytes=size, all22_arrays_and_actual_time_bytes_equal=True,
        literal_layout_bytes_equal=True, first90_signed_clock_rows_equal=True,
        old_forced_final_completed_step=2180000, new_part90_completed_step=2180001,
        old_final_not_compared=True, retained_metric_rows=90, old_native_reanalysis=False,
        old_0p9s_is_not_a_3s_reference=True, SHA_scans=0)


def snapshot_rows(bundle, analysis, reference):
    rows, schedule = [], []
    for requested, (part, snap) in zip(SNAPSHOTS, analysis['snapshots'].items()):
        x = old.read22(bundle, part); soil = x['Idp'][:, 0] >= 2060
        schedule.append(dict(requested_tau_s=requested, part=part, time_s=snap['time_s'], tau_s=snap['tau_s'],
            actual_minus_requested_s=snap['tau_s']-requested, completed_step=int(bundle['clocks'][part]['completed_step'])))
        need(abs(snap['tau_s']-requested) <= 5.01e-6, 'Snapshot must be nearest actual save, with original time retained')
        for i, identity in enumerate(x['Idp'][soil, 0]):
            at = 1805 + i; pos = x['Posd'][at]; v = x['Vel'][at]; p = float(x['PorePress'][at, 0])
            sk, si = x['SigmaState_kk'][at], x['SigmaState_ij'][at]
            row = dict(part=part, requested_tau_s=requested, time_s=snap['time_s'], tau_s=snap['tau_s'], native_id=int(identity),
                x_m=float(pos[0]), y_m=float(pos[1]), z_m=float(pos[2]), initial_z_m=float(reference['initial_pos'][identity, 2]),
                dx_from_PRE_m=float(pos[0]-reference['pos'][identity, 0]), dz_from_PRE_m=float(pos[2]-reference['pos'][identity, 2]),
                vx_m_s=float(v[0]), vy_m_s=float(v[1]), vz_m_s=float(v[2]), p_Pa=p,
                fixed_P0_Pa=float(x['PorePress0'][at, 0]), native_p_minus_fixedP0_Pa=float(x['ExcessPorePress'][at, 0]),
                kappa=float(x['Kplastic'][at, 0]), J=float(x['PoroVolumeRatio'][at, 0]), n=float(x['PoroPorosity'][at, 0]),
                rho_kg_m3=float(x['PoroMixtureDensity'][at, 0]), native_Rhop_kg_m3=float(x['native_Rhop'][at, 0]),
                k_m_s=float(x['PoroHydraulicConductivity'][at, 0]), current_volume_native=float(x['PoroCurrentVolume'][at, 0]),
                FS_type=int(x['FSType'][at, 0]))
            for j, name in enumerate(('xx', 'yy', 'zz')):
                row['effective_' + name + '_Pa'] = float(sk[j]); row['total_' + name + '_Pa'] = float(sk[j]-p)
            for j, name in enumerate(('xy', 'xz', 'yz')): row['effective_and_total_' + name + '_Pa'] = float(si[j])
            rows.append(row)
    need(len(schedule) == 6 and len(rows) == 30000, 'Six genuine5000-ID snapshots required')
    return rows, schedule


def late_states(bundle, analysis, reference):
    rows, states = [], []
    history = analysis['history']; last = old.read22(bundle, 300); top = reference['initial_pos'][2060:, 2]
    top, bottom = top == top.max(), top == top.min()
    keys = ('p_mean_Pa', 'p_min_Pa', 'p_max_Pa', 'p_RMS_Pa', 'native_p_minus_fixedP0_RMS_Pa',
            'effective_stress_Frobenius_RMS_Pa', 'total_stress_Frobenius_RMS_Pa', 'velocity_RMS_m_s',
            'max_speed_m_s', 'current_mixture_KE_J_per_m', 'max_kappa', 'min_J', 'max_J', 'min_n', 'max_n',
            'min_rho', 'max_rho', 'min_k_m_s', 'max_k_m_s', 'runout_from_PRE_front_m',
            'top_material_settlement_mm', 'bottom_material_settlement_mm', 'NN_q05_over_dp', 'pairs_r_lt_0p7dp')
    for duration in (1., .5):
        at = next(i for i, q in enumerate(history) if q['time_s'] >= history[-1]['time_s']-duration)
        tail = history[at:]; first = old.read22(bundle, at); width = tail[-1]['time_s']-tail[0]['time_s']
        common = dict(requested_duration_s=duration, actual_start_s=tail[0]['time_s'], actual_end_s=tail[-1]['time_s'],
            actual_start_tau_s=tail[0]['tau_s'], actual_end_tau_s=tail[-1]['tau_s'], actual_duration_s=width,
            start_part=at, end_part=300, samples=len(tail))
        for key in keys:
            values = [q[key] for q in tail]
            rows.append(dict(**common, metric=key, first=values[0], last=values[-1], delta=values[-1]-values[0],
                minimum=min(values), maximum=max(values), endpoint_secant_per_s=(values[-1]-values[0])/width))
        du = last['Posd'][1805:]-first['Posd'][1805:]
        state = dict(**common, same_ID_movement_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du*du, axis=1)))),
            same_ID_movement_max_mm=float(1000*np.linalg.norm(du, axis=1).max()),
            top_material_settlement_change_mm=float(-1000*du[top, 2].mean()),
            bottom_material_settlement_change_mm=float(-1000*du[bottom, 2].mean()))
        dp = last['PorePress'][1805:, 0].astype(float)-first['PorePress'][1805:, 0].astype(float)
        sk = last['SigmaState_kk'][1805:]-first['SigmaState_kk'][1805:]
        si = last['SigmaState_ij'][1805:]-first['SigmaState_ij'][1805:]
        total = sk-dp[:, None]; dv = last['Vel'][1805:].astype(float)-first['Vel'][1805:].astype(float)
        state['effective_stress_same_ID_Frob_RMS_change_Pa'] = float(np.sqrt(np.mean(np.sum(sk*sk, axis=1)+2*np.sum(si*si, axis=1))))
        state['total_stress_same_ID_Frob_RMS_change_Pa'] = float(np.sqrt(np.mean(np.sum(total*total, axis=1)+2*np.sum(si*si, axis=1))))
        state['velocity_vector_same_ID_RMS_change_m_s'] = float(np.sqrt(np.mean(np.sum(dv*dv, axis=1))))
        for field, name in (('PorePress', 'p_Pa'), ('Kplastic', 'kappa'), ('PoroVolumeRatio', 'J'),
                            ('PoroPorosity', 'n'), ('PoroMixtureDensity', 'rho_kg_m3'), ('PoroHydraulicConductivity', 'k_m_s')):
            delta = last[field][1805:, 0].astype(float)-first[field][1805:, 0].astype(float)
            state[name+'_same_ID_change_RMS'] = float(np.sqrt(np.mean(delta*delta)))
            state[name+'_same_ID_change_maxabs'] = float(np.abs(delta).max())
        states.append(state)
    return rows, states


def material_geometry(bundle, analysis, reference, prefix):
    initial = reference['initial_pos'][2060:][:, (0, 2)]; xs, zs = np.unique(initial[:, 0]), np.unique(initial[:, 1])
    need(len(xs) == 100 and len(zs) == 50, 'Original100x50 grid required')
    grid = np.full((50, 100), -1, dtype=int)
    for node, (x, z) in enumerate(zip(np.searchsorted(xs, initial[:, 0]), np.searchsorted(zs, initial[:, 1]))):
        need(grid[z, x] == -1, 'Duplicate original material node'); grid[z, x] = node
    need((grid >= 0).all(), 'Missing original material node')
    cells = np.stack((grid[:-1, :-1], grid[:-1, 1:], grid[1:, 1:], grid[1:, :-1]), axis=-1).reshape(-1, 4)
    local = initial[cells]-initial[cells][:, :1]
    area0 = .5*np.sum(material.cross(local, np.roll(local, -1, axis=1)), axis=1)
    need(len(cells) == 4851 and np.allclose(area0, .04**2, rtol=0, atol=1e-15), 'Original4851 positive cells required')
    rows, critical, snaps = [], [], {}
    for part in range(301):
        x = old.read22(bundle, part); j = x['PoroVolumeRatio'][1805:, 0]
        ratio, tri, mixed, bow, poly = material.measures(x['Posd'][1805:][:, (0, 2)], cells, area0)
        meanj = np.mean(j[cells], axis=1); at = int(ratio.argmin()); h = analysis['history'][part]
        rows.append(dict(part=part, time_s=h['time_s'], tau_s=h['tau_s'], min_area_ratio=float(ratio.min()),
            max_area_ratio=float(ratio.max()), nonpositive_area_cells=int((ratio <= 0).sum()),
            chosen_diagonal_triangle_reversal=int(tri.sum()), mixed_turn_cells=int(mixed.sum()), self_cross_cells=int(bow.sum()),
            area_minus_meanJ_RMS=float(np.sqrt(np.mean((ratio-meanj)**2))),
            total_signed_area_ratio=float(np.sum(ratio*area0)/np.sum(area0))))
        critical.append(dict(part=part, time_s=h['time_s'], tau_s=h['tau_s'], cell=at,
            ID_LL=int(cells[at, 0]+2060), ID_LR=int(cells[at, 1]+2060), ID_UR=int(cells[at, 2]+2060),
            ID_UL=int(cells[at, 3]+2060), signed_area_ratio=float(ratio[at]), native_corner_mean_J=float(meanj[at])))
        if part in analysis['snapshots']: snaps[part] = (poly.copy(), ratio.copy())
    lo, hi = min(v[1].min() for v in snaps.values()), max(v[1].max() for v in snaps.values())
    norm = TwoSlopeNorm(vmin=lo, vcenter=1., vmax=hi) if lo < 1 < hi else Normalize(vmin=lo, vmax=hi)
    fig, axes = old.plt.subplots(2, 3, figsize=(16, 9), layout='constrained')
    xmax = max(s['pos'][:, 0].max() for s in analysis['snapshots'].values())
    for ax, (part, (poly, ratio)) in zip(axes.flat, snaps.items()):
        pc = PolyCollection(poly, array=ratio, cmap='coolwarm', norm=norm, edgecolors='.3', linewidth=.1)
        ax.add_collection(pc); ax.set(xlim=(-.04, xmax+.04), ylim=(-.04, 2.04), xlabel='x [m]', ylabel='z [m]',
            title=f"part{part}; actual tau={analysis['history'][part]['tau_s']:.9f}s\nA<=0: {(ratio <= 0).sum()}")
        ax.set_aspect('equal')
    fig.colorbar(pc, ax=list(axes.flat), label='Signed chord area / original area', shrink=.7)
    fig.suptitle('Original material quadrilaterals; raw connectivity, no smoothing\nStraight chord geometry is a resolution diagnostic, not exact material volume or an SPH J gate')
    dest = Path(str(prefix)+'_material_cells.png'); fig.savefig(dest, dpi=170); old.plt.close(fig)
    return rows, critical, dest


def focus_plot(analysis, prefix):
    charts = [('Pressure RMS [kPa]', ('p_RMS_Pa', 'native_p_minus_fixedP0_RMS_Pa'), .001),
        ('Stress Frobenius RMS [kPa]', ('effective_stress_Frobenius_RMS_Pa', 'total_stress_Frobenius_RMS_Pa'), .001),
        ('Mixture density [kg/m3]', ('min_rho', 'max_rho'), 1.), ('Porosity', ('min_n', 'max_n'), 1.),
        ('Conductivity [m/s]', ('min_k_m_s', 'max_k_m_s'), 1.), ('J', ('min_J', 'max_J'), 1.),
        ('Settlement including preload [mm]', ('top_material_settlement_mm_including_preload', 'bottom_material_settlement_mm_including_preload'), 1.),
        ('Motion [m/s]', ('velocity_RMS_m_s', 'max_speed_m_s'), 1.),
        ('Front advance from PRE [m]', ('runout_from_PRE_front_m',), 1.)]
    fig, axes = old.plt.subplots(3, 3, figsize=(15, 11), layout='constrained'); h = analysis['history']
    for ax, (title, keys, scale) in zip(axes.flat, charts):
        for key in keys: ax.plot([q['tau_s'] for q in h], [q[key]*scale for q in h], label=key)
        ax.set(title=title, xlabel='Actual saved time since PRE [s]'); ax.grid(alpha=.2); ax.legend(fontsize=6)
    fig.suptitle('AS.5/n2.55 psi0 full3 diagnostic; all301 actual saves\nFirst point is PRE+1, with no artificial t=0 or fitted arrest/decay model')
    dest = Path(str(prefix)+'_focus.png'); fig.savefig(dest, dpi=170); old.plt.close(fig); return dest


def paper_plot(analysis, prefix, consumed):
    receipt = T / 'logs/upl_c08_lian14_outline_r1.check.json'; check = read(receipt); consumed.append(stat(receipt))
    need(check['passed'] and check['analysis_completed'] and not check['physical_acceptance']
         and not check['pressure_values_sampled'], 'Retained descriptive outline required')
    destinations = [T / 'figures' / ('upl_c08_lian14_outline_r1_'+q+'.csv') for q in ('outline', 'summary')]
    for p in destinations: consumed.append(bind(next(v for v in check['outputs'] if old.path(v['path']) == p.resolve())))
    outline, summaries = (table(p) for p in destinations); rows = []
    fig, axes = old.plt.subplots(1, 3, figsize=(15, 5), layout='constrained')
    for ax, p in zip(axes, summaries):
        requested = float(p['requested_tau_s']); part, snap = min(analysis['snapshots'].items(), key=lambda q: abs(q[1]['tau_s']-requested))
        need(abs(snap['tau_s']-requested) <= 5.01e-6, 'Paper comparison uses actual nearby save only')
        edge = [q for q in outline if float(q['requested_tau_s']) == requested]
        ax.scatter(snap['pos'][:, 0], snap['pos'][:, 2], s=2, color='C0', label='Native particle centers')
        ax.scatter([float(q['x_m']) for q in edge], [float(q['z_m']) for q in edge], s=3, color='C1', label='Paper visible bulk edge')
        ax.set(xlim=(-.04, 8.04), ylim=(-.04, 2.04), xlabel='x [m]', ylabel='z [m]',
            title=f"Fig14 {requested:g}s; native {snap['tau_s']:.9f}s"); ax.set_aspect('equal'); ax.legend(fontsize=7)
        front = float(snap['pos'][:, 0].max()); paper = float(p['front_colored_extent_m'])
        rows.append(dict(requested_tau_s=requested, native_part=part, native_actual_tau_s=snap['tau_s'],
            native_particle_center_front_m=front, paper_visible_colored_extent_m=paper, center_minus_visible_extent_m=front-paper,
            paper_raster_allowance_m=float(p['front_digitization_allowance_m']), separate_representation_scale_m=.02,
            difference_is_theory_error=False, pressure_values_compared=False))
    fig.suptitle('Lian2023 Fig14 psi0 is a numerical qualitative reference\nRaw native centers and retained raster edge; no geometric shift, fit, pressure-color sampling or parameter tuning')
    dest = Path(str(prefix)+'_paper_shape.png'); fig.savefig(dest, dpi=170); old.plt.close(fig); return rows, dest


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--execution-authorized', action='store_true'); args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until root full-read and one separately completed native301 read')
    manifest = read(args.manifest); need(manifest['tag'] == TAG and manifest['snapshots_tau_s'] == SNAPSHOTS
        and len(manifest['cases']) == 1, 'Exact one-case full3 manifest required')
    prefix = T / 'figures' / TAG; check = T / 'logs' / (TAG+'.check.json')
    need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')), 'Existing complete/partial analysis protected')
    paths = [args.manifest, Path(__file__), NOTE, BUILD, Path(core.__file__), Path(narrow.__file__),
        Path(old.__file__), Path(core.source.__file__), Path(core.plastic.__file__), Path(material.__file__),
        T/'support/c08_h18_centroid_partial_review_r1.py',
        old.C.parents[2]/'src/papers/PDF/Lian 2023 u-pl.pdf', old.C.parents[2]/'src/papers/u-pw/Lian 2023 u-pl.md']
    consumed = [stat(p) for p in paths]
    result = dict(stage=TAG, analysis_complete=False, physical_acceptance=False, consumed=consumed)
    try:
        source = core.source.load(manifest['source'], consumed); reference = old.reference_from(source)
        bundle = receiver(manifest['cases'][0], source, manifest['source'], consumed); bundle['_source'] = source
        analysis = old.analyze_case(bundle, reference, SNAPSHOTS)
        definitions = core.add_total_settlement(analysis, reference); first = core.first_step(bundle, reference)
        matched, proof = retained_prefix(bundle, analysis, consumed)
        fields, schedule = snapshot_rows(bundle, analysis, reference); late, states = late_states(bundle, analysis, reference)
        geometry, critical, cell_png = material_geometry(bundle, analysis, reference, prefix)
        paper, paper_png = paper_plot(analysis, prefix, consumed); files = [cell_png, paper_png]
        for suffix, rows in [(key, analysis[key]) for key in ('history', 'extrema', 'layers', 'tracks')] + [
            ('first_real_step', [first]), ('selection_metrics', [core.selection_summary(analysis)]),
            ('snapshot_schedule', schedule), ('snapshots', fields), ('late_metrics', late), ('late_same_ID_states', states),
            ('material_geometry', geometry), ('material_min_cells', critical), ('retained_common90', matched), ('paper_shape', paper)]:
            dest = Path(str(prefix)+'_'+suffix+'.csv'); old.write_csv(dest, rows); files.append(dest)
        files += old.plot_results([analysis], prefix); files.append(focus_plot(analysis, prefix))
        need(all(stat(q['path']) == q for q in consumed), 'Consumed evidence/helper changed during analysis')
        result.update(analysis_complete=True, actual_samples=301, soil_IDs=5000, actual_native_IDs_per_frame=6805,
            summary=analysis['summary'], first_real_step=first, reference_definitions=definitions, prefix_proof=proof,
            snapshot_schedule=schedule, late_same_ID_states=states, material_quads=4851,
            late_pressure_decay_or_arrest_automatically_accepted=False, physical_acceptance=False,
            native_fixed_P0_excess_is_not_paper_plastic_excess=True, straight_chord_area_is_not_native_J=True,
            full_material_contract_independently_reconstructed=False, reaction_J_Darcy_closed=False,
            no_automatic_winner_or_next_job=True, solver_invocations=0, decoder_invocations=0, VTK_invocations=0,
            SHA_scans=0, old_cases_reanalyzed=0, consumed_stats_unchanged=True, visual_QA_pending=True,
            files=[stat(q) for q in files])
    except Exception as error:
        result.update(first_failure=str(error), partial_outputs_preserved=True); raise
    finally:
        with check.open('x', encoding='utf-8') as handle:
            json.dump(result, handle, indent=2, allow_nan=False); handle.write('\n')


if __name__ == '__main__': main()
