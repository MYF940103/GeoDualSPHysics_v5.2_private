"""One offline psi2p5 full3 HG review; no new native read, solve or prefix claim."""
import argparse
from datetime import datetime, timezone
import inspect
from pathlib import Path
import re
import c08_h18_wall_c_retry_full3_hg_review_r1 as old

T, L = old.T, old.L
TAG, FULL = 'c08_h18_hg_psi2p5_full3_review_r1', 'c08_h18_hg_psi2p5_full3_r1'
SCRIPT, NOTE = Path(__file__).resolve(), T / 'notes' / (TAG + '.md')
CHECK, AD = L / (TAG + '.check.json'), L / (TAG + '.root_admission.json')
NATIVE_CHECK = L / 'c08_h18_hg_psi2p5_native_r1.check.json'
CSV, EXT, PNG = [T / 'figures' / (TAG + q) for q in ('_phases.csv','_extrema.csv','_history.png')]
need, stat, read, bits = old.need, old.stat, old.read, old.bits


def phase_kernel():
    """Reuse the literal old numerical loop, removing only its unrelated own-prefix IO."""
    raw = inspect.getsource(old.phases)
    before = '''    fp, sp = full / 'C08OptPlasticHGPolicy.json', short / 'C08OptPlasticHGPolicy.json'
    fc, sc = full / 'C08OptPlasticHG.csv', short / 'C08OptPlasticHG.csv'
'''
    after = '''    fp = full / 'C08OptPlasticHGPolicy.json'
    fc = full / 'C08OptPlasticHG.csv'
'''
    old_prefix = '''    need(policy == read(sp) == expected, 'Actual own/full optimized schema2 HG policies differ')
    fraw, sraw = fc.read_bytes().splitlines(keepends=True), sc.read_bytes().splitlines(keepends=True)
    need(len(fraw) == 603 and len(sraw) == 9 and fraw[:9] == sraw,
         'HG header and all own first8 actual60-column rows must match verbatim')
'''
    changes = [(before,after),
        (old_prefix,"    need(policy == expected, 'Actual full optimized schema2 HG policy differs from the original expected policy')\n"),
        ('own_first8_HG_rows_exact=True, policy_equal=True,',
         'own_prefix_compared=False, own_first8_HG_rows_exact=None, policy_equal_expected=True,')]
    changed = raw
    for a,b in changes:
        need(changed.count(a) == 1, 'Unique old phase context anchor differs')
        changed = changed.replace(a,b,1)
    inverse = changed
    for a,b in reversed(changes):
        need(inverse.count(b) == 1, 'Reverse phase context anchor differs')
        inverse = inverse.replace(b,a,1)
    need(inverse == raw, 'Numerical phase loop changed beyond the three declared context edits')
    namespace = dict(old.__dict__)
    exec(compile(changed,str(SCRIPT) + ':original_phase_kernel','exec'),namespace)
    return namespace['phases']


def context(take):
    runpath = L / (FULL + '.run.json')
    ad = read(take(AD))
    need(ad['authorized'] and ad['offline_only'] and ad['root_thread_id'] == old.THREAD
         and ad['execution_script'] == stat(SCRIPT) and ad['note'] == stat(NOTE)
         and ad['run'] == stat(runpath) and ad['native_check'] == stat(NATIVE_CHECK),
         'Exact separate root offline review admission required')
    run, native = read(take(runpath)), read(take(NATIVE_CHECK))
    need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged']
         and run['solver_identity_matches'] and run['ownership_failure'] is None
         and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit'] == run['actual_tool_Win32_exit'] == 0
         and run['actual_steps'] == 2600000 and run['saved_frames'] == 301 and run['new_updates'] == 600000
         and run['group'] == 'psi2p5' and run['HG_history_cold_zero'] and run['DynamicNoPenetrationReactionClosed'] is False,
         'Actual same-material psi2p5 full301/coldHG run required')
    actual = read(take(run['actual_call'])); old.owned(actual)
    need([actual['program'],*actual['arguments']] == run['argv']
         and actual['child'] == run['solver_identity'] and actual['child']['exe'] == run['program']['path'],
         'Original owned child identity/argv/program differ')
    start = read(take(L / (FULL + '.start.json')))
    prepare = read(take(run['preparation']))
    need(prepare['passed'] and prepare['prepared_only'] and prepare['group'] == 'psi2p5'
         and prepare['consumed_stats_unchanged'] and start['owner'] == run['owner']
         and start['argv'] == run['argv'] and start['preparation'] == run['preparation'],
         'Original start/preparation/owner binding differs')
    for key in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','planned_steps'):
        take(run[key])
        need(prepare[key] == run[key] and start[key] == run[key], 'Original preparation/start binding differs: ' + key)
    take(run['root_admission'])
    for key in ('source_run','source_native','source_native_check','source_material_profile',
                'source_physical_review','source_root_review','material_probe'):
        take(run[key]); need(prepare[key] == run[key], 'Same-material source/probe binding differs: ' + key)
    source_cert, source_check = read(run['source_native']['path']), read(run['source_native_check']['path'])
    need(source_check['passed'] and source_check['reader_invocations'] == 1 and source_check['consumed_stats_unchanged']
         and source_cert['passed'] and source_cert['group'] == 'psi2p5' and source_cert['certified_PRE']
         and source_cert['samples'] == 1001 and source_cert['expected_handoff_schema'] == 2
         and source_cert['same_material_plastic_PRE'] and not source_cert['source_equilibrium_claimed'],
         'Qualified original psi2p5 PRE certificate required; not an equilibrium assertion')
    build = read(run['source_build']['path'])
    need(build['passed'] and build['consumed_stats_unchanged'] and build['material_guard_only']
         and build['actual_link_objects'] == 114 and build['retained_objects_count'] == 113
         and not build['material_law_or_HG_Node_source_changed'] and build['C_quality_CUDA_object_retained']
         and build['host_capture_object_retained'] and build['program'] == run['program'],
         'Actual three-group host-only build with retained HG/C-quality kernels required')
    opt = read(take(build['optimized_build']))
    cuda = Path(take(opt['private_sources']['CUDA']))
    text = cuda.read_text(encoding='utf-8-sig')
    headers = re.findall(r'h<<"(phase,completed_step,[^"]+)"',text)
    need(len(headers) == 1 and all(q in text for q in ('o.ledger=(newE-oldE+nodeWork+loss+deadE).v',
         'o.adjoint_defect=(nodeWork-rowWork).v','std::swap(p.memory.e,p.graph.next_e)')), 'Retained HG arithmetic/lifecycle source anchors differ')
    header = headers[0].removesuffix(r'\n').split(','); need(len(header) == 60, 'Original HG60 schema required')
    need(native['passed'] and native['original_safety_passed'] and native['reader_invocations'] == 1
         and native['consumed_stats_unchanged'] and native['run'] == stat(runpath)
         and native['source_run'] == run['source_run'], 'One successful unique psi2p5 full301 native read required')
    old.owned(read(take(native['actual_call'])))
    for entry in native['outputs']: take(entry)
    need(len(native['outputs']) == 7, 'Original native seven-file export seal required')
    nd = read(take(native['native_completion'])); take(native['metadata'])
    need(nd['passed'] and nd['samples'] == 301 and nd['completed_steps'] == 2600000
         and nd['actual_native_IDs_per_frame'] == 6805 and nd['soil_IDs'] == 5000 and nd['actual_fixed_IDs'] == 1805
         and nd['typed_arrays'] == 22 and not nd['native_rewritten'] and nd['nonempty_signed_intervals'] == 301
         and nd['max_scalar_clock_error_s'] <= 1e-14 and nd['max_signed_dterror_s'] <= 1e-14,
         'Original full native extent/identity/signed/clock guards differ')
    full = Path(run['output']); need(full == T / 'outputs' / FULL, 'Actual full output path differs')
    _, plan = old.table(take(run['planned_steps']))
    _, clocks = old.table(take(full / 'native_r1/clocks.csv'))
    need(len(plan) == len(clocks) == 301, 'Original full301 actual plan/clock coverage required')
    wanted = {int(q['completed_step']) for q in plan}; scalar, steps = float(run['actual_source_time_s']), {}
    for step in range(2000001,2600001):
        previous = scalar; scalar += .000005
        if step in wanted: steps[step] = (previous,scalar)
    need(bits(scalar) == bits(run['planned_actual_end_s']), 'Original scalar +=dt endpoint differs')
    for part,(p,c) in enumerate(zip(plan,clocks)):
        step = int(p['completed_step']); expected = 2000001 + part*2000 if part < 300 else 2600000
        need(int(p['part']) == int(c['part']) == part and step == int(c['completed_step']) == expected
             and int(p['saved_step']) == int(c['saved_step']) == step-1
             and bits(p['time_s']) == bits(c['time_s']) == bits(steps[step][1])
             and bits(p['dt_s']) == bits(c['dt_s']) == bits(.000005)
             and c['dterror_interval_empty'] == '0' and float(c['signed_dterror_s']) <= 1e-14
             and int(c['native_IDs']) == 6805, 'Original full301 actual clock/signed row differs')
    return run,full,header,plan,steps


def plot(rows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    charts = [('HG energy','Energy [J/m]',('Eold','Enew')),('HG work','Work [J/m]',('row_work','node_work')),
        ('Loading and rotation','Energy [J/m]',('loading_loss','rotation_change','ledger')),
        ('Directed rows','Count',('rows','accepted_dead')),('HG time-step ratio','dt / limit',('dt_over_0p2_limit',)),
        ('Loading factor','Gamma',('gamma_min','gamma_max')),('Local spin','Half-angle [rad]',('max_half_angle',)),
        ('Force writeback','Force [N/m]',('max_commit_error','commit_budget')),
        ('Diagnostic budget ratios','Absolute value / budget',('ledger_over_recorded_budget','adjoint_over_recorded_budget','torque_over_recorded_budget'))]
    fig,axes = plt.subplots(3,3,figsize=(18,15),layout='constrained')
    for ax,(title,unit,columns) in zip(axes.flat,charts):
        for phase,style in (('Pre','--'),('Cor','-')):
            rr = [r for r in rows if r['phase'] == phase]
            for column in columns: ax.plot([r['tau_s'] for r in rr],[r[column] for r in rr],style,label=phase+' '+column,lw=1)
        ax.set(title=title,xlabel='Actual time after release [s]',ylabel=unit); ax.grid(alpha=.2); ax.legend(fontsize=7)
    axes[1,1].axhline(1,color='black',lw=.6); axes[2,0].axhline(.005,color='black',lw=.6)
    fig.suptitle('C08 psi = +2.5 deg: full3 HG observations\nPre/Cor share committed energy; diagnostic budgets are not a coupled-energy certificate')
    fig.savefig(PNG,dpi=160); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execution-authorized',action='store_true')
    need(parser.parse_args().execution_authorized,'Root full read and independent offline authorization required')
    need(not any(p.exists() for p in (CHECK,CSV,EXT,PNG)),'Existing complete/partial review protected')
    consumed = {}
    def take(value):
        p = Path(value['path'] if isinstance(value,dict) else value).resolve(); q = stat(p)
        need(not isinstance(value,dict) or q == value,'Bound input stat changed: '+str(p))
        need(str(p) not in consumed or consumed[str(p)] == q,'Consumed input changed: '+str(p))
        consumed[str(p)] = q; return p
    result = dict(stage=TAG,passed=False,analysis_complete=False,group='psi2p5',own_prefix_compared=False,
                  no_feedback_proof_claimed=False,physical_acceptance=False,solver_invocations=0,reader_invocations=0,
                  build_invocations=0,VTK_invocations=0,SHA_scans=0,automatic_next_job=False)
    try:
        take(SCRIPT); take(NOTE); take(Path(old.__file__))
        run,full,header,plan,steps = context(take)
        rows,hg = phase_kernel()(run,full,None,header,plan,steps,take)
        extrema = old.extrema(rows)
        need(all(stat(q['path']) == q for q in consumed.values()),'Consumed input changed during offline review')
        old.write(CSV,rows); old.write(EXT,extrema); plot(rows)
        result.update(passed=True,analysis_complete=True,source_run=stat(L/(FULL+'.run.json')),
            source_native_check=stat(NATIVE_CHECK),HG=hg,files=[stat(p) for p in (CSV,EXT,PNG)],
            original_numerical_phase_loop_retained_by_exact_inverse_proof=True,consumed_stats_unchanged=True,
            full_solver_completed=True,full_native_safety_inherited_from_unique_read=True,visual_QA_pending=True,
            cache_scope='Input13/commit7 are one-producer coherence, not an independent material oracle',
            energy_scope='Pre/Cor trials start from the same committed e; never add as consecutive accepted work',
            budget_scope='Original diagnostic estimates and undefined ratios, not outward/coupled passivity certificates',
            NoPen_projection_work_not_captured=True,NoPenReactionClosed=False,source_PRE_HG_OFF_then_cold_release_e0=True,
            exact_HG_PART_restart_claimed=False,no_half_or_cross_material_equivalence_claimed=True,
            all_updates_scope='Completed owner/control-flow plus602 saved observations, not every-stage exports')
    except Exception as error: result['first_failure'] = repr(error)
    result.update(created_utc=datetime.now(timezone.utc).isoformat(),consumed=list(consumed.values()))
    old.save(CHECK,result); need(result['passed'],result.get('first_failure','Offline review failed; preserve outputs'))


if __name__ == '__main__':
    main()
