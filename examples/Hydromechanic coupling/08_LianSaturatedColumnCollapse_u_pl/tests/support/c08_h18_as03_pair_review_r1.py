"""Selected saved-material pair diagnosis only; no decoder, force or solver."""
import argparse
import csv
import json
import math
import struct
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_as03_pair_review_r1'
REVIEW = T/'logs/c08_h18_as03n255_full3_review_r1.check.json'
CANDIDATE = T/'outputs/c08_h18_as03n255_full3_r1/native_r1'
SOURCE = T/'outputs/c08_h18_wend_psi0_pre_r2/native_r1'
PAIRS = ((6767, 6865), (4953, 4954))
FOCUS = (7010, 7011, 7012, 6230, 6231)  # Original five full3 tracks, unchanged.
IDS = tuple(sorted(set(FOCUS).union(*map(set, PAIRS))))
DP = .04
SCHEMA = (
    ('Idp', 'uint32', 1), ('Posd', 'float64', 3), ('Vel', 'float32', 3),
    ('Sigma_kk', 'float32', 3), ('Sigma_ij', 'float32', 3), ('FSNormal', 'float32', 3),
    ('HydroMechLoadAce', 'float32', 3), ('native_Rhop', 'float32', 1),
    ('Kplastic', 'float32', 1), ('PorePress', 'float32', 1), ('PorePress0', 'float32', 1),
    ('ExcessPorePress', 'float32', 1), ('SigmaState_kk', 'float64', 3), ('SigmaState_ij', 'float64', 3),
    ('FSType', 'uint32', 1), ('PoroVolumeRatio', 'float64', 1), ('PoroPorosity', 'float64', 1),
    ('PoroThetaLastStage', 'float64', 1), ('PoroCurrentVolume', 'float64', 1),
    ('PoroMixtureDensity', 'float64', 1), ('PoroHydraulicConductivity', 'float64', 1), ('PosDiv', 'float32', 1),
)
PAIR_KEYS = ('pair', 'partner_ID', 'pair_distance_m', 'pair_distance_over_dp',
             'pair_direction_x', 'pair_direction_y', 'pair_direction_z',
             'pair_closing_m_s', 'pair_direction_defined', 'effective_pair_normal_Pa',
             'total_pair_normal_Pa', 'partner_total_pair_normal_Pa', 'pair_mean_total_normal_Pa')


def need(value, message):
    if not bool(value):
        raise RuntimeError(message)


def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def table(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until root separately reviews/admit this offline script')
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    prefix = T/'figures'/TAG
    history_path, plot_path, summary_path = (Path(str(prefix)+suffix) for suffix in ('_history.csv', '_pairs.png', '_summary.json'))
    need(not any(p.exists() for p in (history_path, plot_path, summary_path)), 'Existing complete/partial selected-pair review protected')
    consumed = [stat(Path(__file__)), stat(T/'notes'/(TAG+'.md')), stat(REVIEW)]
    review = read(REVIEW)
    need(review['stage'] == 'c08_h18_as03n255_full3_review_r1' and review['analysis_complete']
         and review['consumed_stats_unchanged'] and review['actual_samples'] == 301
         and not review['physical_acceptance'] and review['candidate_shear_mapping'] == 'SigmaState_ij=(xy,yz,xz)',
         'Completed AS03 full301 saved-state review is required')
    # Bind only files actually consumed here, once. Do not rescan transitive programs, PRE BI4 or controls.
    bindings = {}
    for entry in review['consumed']:
        path = Path(entry['path']).resolve()
        if path in bindings:
            need(bindings[path] == entry, 'Conflicting retained stat binding: '+str(path))
        bindings[path] = entry

    def bound(path):
        path = Path(path).resolve()
        need(path in bindings and stat(path) == bindings[path], 'Selected native input stat changed: '+str(path))
        consumed.append(bindings[path]); return path

    run = read(bound(T/'logs/c08_h18_as03n255_full3_r1.run.json'))
    native = read(bound(T/'logs/c08_h18_as03n255_full3_native_r1.check.json'))
    need(run['passed'] and run['solver_completed'] and run['actual_exit'] == run['actual_Win32_exit'] == 0
         and run['actual_steps'] == 2600000 and run['saved_frames'] == 301,
         'Already reviewed full301 run receipt differs')
    need(native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations'] == 1
         and native['native_completion'] == bindings[(CANDIDATE/'completion.json').resolve()],
         'Already reviewed unique native receipt differs')
    bundles = []
    maps = []
    result = dict(stage=TAG, analysis_complete=False, physical_acceptance=False, consumed=consumed,
                  selected_pairs=[list(q) for q in PAIRS], original_five_track_IDs=list(FOCUS),
                  selected_IDs=list(IDS), solver_invocations=0, force_invocations=0, decoder_invocations=0,
                  VTK_invocations=0, SHA_scans=0, existing_review_stat_bindings_checked_once=True,
                  all_native_or_control_reanalysis=False, saved_states_cannot_prove_substage_causation=True)
    try:
        for root, nodes, count, source in ((SOURCE, 7060, 1001, True), (CANDIDATE, 6805, 301, False)):
            paths = {name: bound(root/name) for name in ('completion.json', 'typed22_layout.csv', 'clocks.csv', 'typed22.bin')}
            done = read(paths['completion.json'])
            need(done['passed'] and done['samples'] == count and done['typed_arrays'] == 22
                 and done['typed_bytes_per_particle'] == 212, 'Original native extent/completion differs')
            if source:
                need(done['certified_PRE'] and not done['partial'] and done['completed_steps'] == 2000000
                     and done['native_IDs'] == nodes, 'Original completed same-material Wendland PRE reference required')
            else:
                need(done['completed_steps'] == 2600000 and done['new_updates'] == 600000
                     and done['actual_native_IDs_per_frame'] == nodes
                     and done['receiver_part0_is_real_post_not_t0_or_PRE']
                     and not done['reaction_J_Darcy_closed'], 'Original AS03 receiver scope differs')
            layout = table(paths['typed22_layout.csv'])
            fields = [('time', '<f8')]
            types = {'uint32': np.dtype('<u4'), 'float32': np.dtype('<f4'), 'float64': np.dtype('<f8')}
            need(len(layout) == 22, 'Exact original22 schema required')
            for row, (name, kind, width) in zip(layout, SCHEMA):
                need((row['array'], row['type'], int(row['components']), int(row['bytes_per_particle']))
                     == (name, kind, width, types[kind].itemsize*width), 'Original typed22 layout differs')
                fields.append((name, types[kind], (nodes, width)))
            dtype = np.dtype(fields, align=False)
            with paths['typed22.bin'].open('rb') as f:
                need(struct.unpack('<III', f.read(12)) == (nodes, 22, count), 'Native header is not the original full record')
            need(bindings[paths['typed22.bin']]['bytes'] == 12+count*dtype.itemsize, 'Original typed payload extent differs')
            clocks = table(paths['clocks.csv'])
            need(len(clocks) == count, 'Actual saved-clock coverage differs')
            frames = np.memmap(paths['typed22.bin'], dtype=dtype, offset=12, mode='r', shape=(count,))
            maps.append(frames)
            bundles.append(dict(root=root, done=done, nodes=nodes, clocks=clocks, frames=frames, source=source))
        pre, collapse = bundles
        release_time = float(pre['done']['actual_end_s'])
        need(release_time == float(collapse['done']['source_actual_time_s']), 'Actual PRE/release reference differs')
        references = {}
        records = []
        pair_for = {a: (a, b) for pair in PAIRS for a, b in (pair, pair[::-1])}

        def snapshot(bundle, part, phase):
            frame, clock = bundle['frames'][part], bundle['clocks'][part]
            need(int(clock['part']) == part and float(frame['time']) == float(clock['time_s'])
                 and float(clock['dt_s']) == .000005 and float(clock['signed_dterror_s']) <= 1e-14,
                 'Original actual clock/dt/signed diagnostic differs')
            indices = np.array(IDS, dtype=np.int64)-(0 if bundle['source'] else 255)
            need(np.array_equal(frame['Idp'][indices, 0], np.array(IDS, dtype=np.uint32)), 'Selected material ID mapping differs')
            states = {}
            for identity, at in zip(IDS, indices):
                pos = np.array(frame['Posd'][at], dtype=float)
                vel = np.array(frame['Vel'][at], dtype=float)
                sk = np.array(frame['SigmaState_kk'][at], dtype=float)
                si = np.array(frame['SigmaState_ij'][at], dtype=float)
                p, p0 = float(frame['PorePress'][at, 0]), float(frame['PorePress0'][at, 0])
                effective = np.array(((sk[0], si[0], si[2]), (si[0], sk[1], si[1]), (si[2], si[1], sk[2])))
                total = effective-p*np.eye(3)
                effective_principal, total_principal = np.linalg.eigvalsh(effective), np.linalg.eigvalsh(total)
                row = dict(phase=phase, part=part, time_s=float(frame['time']), tau_s=float(frame['time'])-release_time,
                    completed_step=int(clock['completed_step']), saved_step=int(clock['saved_step']),
                    dt_s=float(clock['dt_s']), signed_dterror_s=float(clock['signed_dterror_s']),
                    dterror_interval_empty=int(clock['dterror_interval_empty']), native_id=identity,
                    original_track_ID=identity in FOCUS, x_m=float(pos[0]), y_m=float(pos[1]), z_m=float(pos[2]),
                    height_above_bed_plane_m=float(pos[2]), vx_m_s=float(vel[0]), vy_m_s=float(vel[1]), vz_m_s=float(vel[2]),
                    speed_m_s=float(np.linalg.norm(vel)), p_Pa=p, fixed_P0_Pa=p0,
                    native_p_minus_fixedP0_Pa=float(frame['ExcessPorePress'][at, 0]),
                    kappa=float(frame['Kplastic'][at, 0]), J=float(frame['PoroVolumeRatio'][at, 0]),
                    n=float(frame['PoroPorosity'][at, 0]), k_m_s=float(frame['PoroHydraulicConductivity'][at, 0]),
                    rho_kg_m3=float(frame['PoroMixtureDensity'][at, 0]), native_Rhop_kg_m3=float(frame['native_Rhop'][at, 0]),
                    FS_type=int(frame['FSType'][at, 0]))
                for name, value in zip(('xx', 'yy', 'zz'), sk):
                    row['effective_'+name+'_Pa'] = float(value)
                    row['total_'+name+'_Pa'] = float(value-p)
                for name, value in zip(('xy', 'yz', 'xz'), si):
                    row['effective_and_total_'+name+'_Pa'] = float(value)
                for name, values in (('effective', effective_principal), ('total', total_principal)):
                    for label, value in zip(('min', 'middle', 'max'), values):
                        row[name+'_principal_'+label+'_Pa'] = float(value)
                need(all(math.isfinite(v) for v in row.values() if isinstance(v, (int, float))), 'Nonfinite selected saved field')
                row.update({key: None for key in PAIR_KEYS})
                states[identity] = dict(row=row, pos=pos, vel=vel, effective=effective, total=total)
            for identity in IDS:
                item = states[identity]; row = item['row']
                if identity in pair_for:
                    a, b = pair_for[identity]; partner = states[b]
                    delta = partner['pos']-item['pos']; distance = float(np.linalg.norm(delta))
                    row.update(pair='_'.join(map(str, sorted((a, b)))), partner_ID=b, pair_distance_m=distance,
                               pair_distance_over_dp=distance/DP, pair_direction_defined=distance > 0)
                    if distance > 0:
                        direction = delta/distance
                        effective_normal = float(direction@item['effective']@direction)
                        total_normal = float(direction@item['total']@direction)
                        other_normal = float(direction@partner['total']@direction)
                        row.update(pair_direction_x=float(direction[0]), pair_direction_y=float(direction[1]), pair_direction_z=float(direction[2]),
                            pair_closing_m_s=-float((partner['vel']-item['vel'])@direction),
                            effective_pair_normal_Pa=effective_normal, total_pair_normal_Pa=total_normal,
                            partner_total_pair_normal_Pa=other_normal, pair_mean_total_normal_Pa=.5*(total_normal+other_normal))
                records.append(row)
            return states

        references['source_initial'] = snapshot(pre, 0, 'source_initial')
        references['source_PRE'] = snapshot(pre, 1000, 'source_PRE')
        for part in range(301):
            snapshot(collapse, part, 'collapse')
        need(len(records) == 303*len(IDS), 'Only two source references plus301 selected receiver samples required')
        collapse_rows = [q for q in records if q['phase'] == 'collapse']
        per_id = {identity: [q for q in collapse_rows if q['native_id'] == identity] for identity in IDS}
        for identity, rows in per_id.items():
            need(len(rows) == 301 and [q['part'] for q in rows] == list(range(301)), 'Selected material sample coverage differs')
            need(all(q['fixed_P0_Pa'] == references['source_PRE'][identity]['row']['fixed_P0_Pa'] for q in rows),
                 'Selected immutable P0 inheritance differs')
        need(per_id[IDS[0]][0]['completed_step'] == 2000001 and per_id[IDS[0]][-1]['completed_step'] == 2600000,
             'Do not relabel first post-update or final saved state')

        def longest_close(rows):
            runs, start = [], None
            for index, row in enumerate(rows+[None]):
                close = row is not None and row['pair_distance_over_dp'] < .7
                if close and start is None: start = index
                if not close and start is not None:
                    a, b = rows[start], rows[index-1]
                    runs.append(dict(saved_samples=index-start, start_part=a['part'], end_part=b['part'],
                        start_tau_s=a['tau_s'], end_tau_s=b['tau_s'], observed_saved_span_s=b['time_s']-a['time_s']))
                    start = None
            return max(runs, key=lambda q: q['saved_samples']) if runs else None

        pairs = []
        for a, b in PAIRS:
            rows = per_id[a]; worst = min(rows, key=lambda q: q['pair_distance_over_dp'])
            event = {key: worst[key] for key in ('part', 'time_s', 'tau_s', 'completed_step', 'pair_distance_over_dp', 'pair_closing_m_s')}
            first_close = []
            for threshold in (.7, .5):
                first = next((q for q in rows if q['pair_distance_over_dp'] < threshold), None)
                if first is not None:
                    other = per_id[b][first['part']]
                    first_close.append(dict(descriptive_threshold_over_dp=threshold, part=first['part'],
                        tau_s=first['tau_s'], completed_step=first['completed_step'], pair_distance_over_dp=first['pair_distance_over_dp'],
                        total_principal_max_a_Pa=first['total_principal_max_Pa'], total_principal_max_b_Pa=other['total_principal_max_Pa'],
                        total_pair_normal_a_Pa=first['total_pair_normal_Pa'], total_pair_normal_b_Pa=other['total_pair_normal_Pa']))
            pairs.append(dict(IDs=[a, b], source_initial_distance_over_dp=references['source_initial'][a]['row']['pair_distance_over_dp'],
                actual_PRE_distance_over_dp=references['source_PRE'][a]['row']['pair_distance_over_dp'],
                first_post_distance_over_dp=rows[0]['pair_distance_over_dp'], last_distance_over_dp=rows[-1]['pair_distance_over_dp'],
                closest_saved_event=event, first_saved_close_events=first_close,
                selected_pair_saved_samples_below_0p7dp=sum(q['pair_distance_over_dp'] < .7 for q in rows),
                longest_observed_saved_run_below_0p7dp=longest_close(rows),
                zero_distance_saved_samples=sum(not q['pair_direction_defined'] for q in rows),
                not_a_scan_of_all_nearest_neighbors_or_pair_edges=True))
        tracks = []
        for identity in FOCUS:
            rows = per_id[identity]
            tracks.append(dict(native_id=identity, p_min_Pa=min(q['p_Pa'] for q in rows), p_max_Pa=max(q['p_Pa'] for q in rows),
                total_principal_max_peak_Pa=max(q['total_principal_max_Pa'] for q in rows),
                total_principal_min_floor_Pa=min(q['total_principal_min_Pa'] for q in rows),
                kappa_final=rows[-1]['kappa'], J_min=min(q['J'] for q in rows), J_max=max(q['J'] for q in rows),
                min_height_above_bed_plane_m=min(q['height_above_bed_plane_m'] for q in rows),
                saved_FS_switches=sum(a['FS_type'] != b['FS_type'] for a, b in zip(rows[:-1], rows[1:]))))
        with history_path.open('x', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)

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
            axes[4, col].axhline(0, color='black', ls=':', lw=.8, label='Bed wall plane z=0')
            axes[4, col].set(xlabel='x [m]', ylabel='z above bed plane [m]', title='All saved XZ positions; square=PRE, cross=last')
            axes[4, col].set_aspect('equal'); axes[4, col].legend(fontsize=8); axes[4, col].grid(alpha=.2)
        fig.suptitle('AS0.3 / n2.55: two fixed-material pairs, original 301 saved states\nSaved pressure/stress/closing correlations cannot establish substage causation; no physical acceptance', fontsize=13)
        fig.savefig(plot_path, dpi=180, bbox_inches='tight'); plt.close(fig)
        result.update(analysis_complete=True, receiver_saved_frames=301, source_reference_frames=[0, 1000],
            selected_receiver_particle_records=301*len(IDS), source_selected_reference_records=2*len(IDS),
            history_rows=len(records), actual_release_time_s=release_time,
            first_receiver_time_s=per_id[IDS[0]][0]['time_s'], actual_end_s=per_id[IDS[0]][-1]['time_s'],
            first_receiver_is_PRE_plus_one_update=True, source_reference_is_not_an_initial_receiver_save=True,
            principal_values_order='ascending; min most compressive, max most tensile',
            tensor_shear_mapping='SigmaState_ij = xy,yz,xz', total_stress_definition='sigma_total = sigma_effective - p I',
            pair_normal_projection='e.T @ sigma @ e at each endpoint; e is instantaneous saved pair direction',
            pair_closing_definition='-dot(v_partner-v_self, e); positive means approach',
            bed_height_definition='particle-center z minus actual fixed plane z=0, not center minus dp/2',
            native_p_minus_P0_is_not_paper_plastic_excess=True, reaction_J_Darcy_closed=False,
            no_pressure_or_stress_smoothing_or_clipping=True, selected_pairs=pairs, original_tracks=tracks,
            input_stat_checks_pre_read_only=True, no_claim_of_fresh_full22_safety_scan=True,
            visual_QA_pending=True, outputs=[stat(history_path), stat(plot_path)])
    except Exception as error:
        result.update(first_failure=str(error), partial_outputs_preserved=True)
        raise
    finally:
        for frames in maps:
            frames._mmap.close()
        with summary_path.open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2, allow_nan=False); f.write('\n')


if __name__ == '__main__':
    main()
