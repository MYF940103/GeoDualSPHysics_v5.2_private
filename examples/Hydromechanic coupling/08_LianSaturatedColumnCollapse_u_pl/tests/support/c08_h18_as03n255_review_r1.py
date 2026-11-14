"""Offline AS0.5/0.3 n2.55 comparison; two real reader builds, unchanged native gates."""
import argparse, json
from pathlib import Path
from matplotlib.colors import Normalize, TwoSlopeNorm
import c08_h18_wend_receiver_review_r1 as core

old, plastic = core.old, core.plastic
T, need, path, stat = core.T, core.need, core.path, core.stat
TAG = 'c08_h18_as03n255_review_r1'
NOTE = T/'notes'/(TAG+'.md')
CONTROL, CANDIDATE = 'c08_h18_as05_n255_r1', 'c08_h18_as03_n255_r1'
READERS = {CONTROL: T/'logs/c08_h18_n255_native_r1.build.json',
           CANDIDATE: T/'logs/c08_h18_as255_native_r1.build.json'}
CALLS = {CONTROL: T/'logs/c08_h18_n255_native_run_r1.call.json',
         CANDIDATE: T/'logs/c08_h18_as03_n255_native_r1.call.json'}
COEFFICIENTS = {CONTROL: .5, CANDIDATE: .3}
SNAPSHOTS = [.18, .3, .6, .9]
ORIGINAL_LOAD = core.load_receiver
LOADED_CLOCKS = {}


def profile_xml(spec, xml, source_csv):
    need(spec['tag'] in COEFFICIENTS, 'Only the two declared AS n2.55 cases are supported')
    rows = core.table(spec['material_csv']); p = {q['key']:q['value'] for q in rows}
    keys = plastic.MATERIAL_KEYS|{'Kernel','ArtificialStressCoef','ArtificialStressExp'}
    need(len(rows) == len(p) == 17 and set(p) == keys and p['group'] == 'psi0'
         and p['fresh_trigger_active'] == '0', 'Actual exact17-key psi0/Wendland profile required')
    soil = xml.find('execution/special/soils')
    pairs = [(q.get('key'),q.get('value')) for q in xml.findall('execution/parameters/parameter')]
    pars = dict(pairs); need(soil is not None and len(pars) == len(pairs), 'Actual unique material/parameter XML required')
    for key in keys-{'group','fresh_trigger_active'}:
        node = soil.find(key)
        value = pars[key] if key in ('Kernel','DPCtes','ArtificialStressCoef','ArtificialStressExp') else (node.get('value') if node is not None else '1.65' if key == 'SoilTriggerFos' else None)
        need(value is not None and old.f32(p[key]) == old.f32(value), 'Actual CSV/XML material mismatch: '+key)
    original = {q['key']:q['value'] for q in core.table(source_csv)}
    for key in plastic.MATERIAL_KEYS|{'Kernel'}:
        need(p[key] == original[key] if key in ('group','fresh_trigger_active') else old.f32(p[key]) == old.f32(original[key]), 'Receiver/source material mismatch: '+key)
    a = spec['actualAS']; expected = COEFFICIENTS[spec['tag']]
    need(old.f32(p['Kernel']) == old.f32(2) and old.f32(a['coefficient']) == old.f32(expected)
         and old.f32(a['exponent']) == old.f32(2.55)
         and old.f32(p['ArtificialStressCoef']) == old.f32(expected)
         and old.f32(p['ArtificialStressExp']) == old.f32(2.55), 'Exact tag-specific AS values required')
    return pars


def load_receiver(spec, src, source_spec, consumed):
    tag = spec['tag']; need(tag in READERS, 'No relabelled or additional case is admitted')
    need(path(spec['native_build']) == READERS[tag].resolve() and path(spec['native_call']) == CALLS[tag].resolve(), 'Each case must use its own actual reader build/call')
    saved_build, saved_profile = core.BUILD, core.profile_xml
    try:
        core.BUILD, core.profile_xml = READERS[tag], profile_xml
        bundle = ORIGINAL_LOAD(spec, src, source_spec, consumed)
    finally:
        core.BUILD, core.profile_xml = saved_build, saved_profile
    consumed.append(stat(READERS[tag]))
    need(bundle['count'] == 91 and bundle['runtime_observed']['passed'], 'Both actual complete91 windows are required; no partial relabelling')
    clocks = [(int(q['completed_step']),float(q['time_s'])) for q in bundle['clocks']]
    need(len(clocks) == 91 and tag not in LOADED_CLOCKS, 'One independent load per case required')
    LOADED_CLOCKS[tag] = clocks
    if len(LOADED_CLOCKS) == 2:
        need(LOADED_CLOCKS[CONTROL] == LOADED_CLOCKS[CANDIDATE], 'All91 genuine actual steps/times must match without interpolation')
    return bundle


def label(analysis):
    return 'AS='+format(COEFFICIENTS[analysis['summary']['tag']], '.1f')


def plot_results(analyses, prefix):
    """Only replace inherited display, keeping the original analyses and CSV definitions."""
    plt = old.plt; files = []
    charts = [('Pressure mean / RMS [kPa]', [('p_mean_Pa','mean'),('p_RMS_Pa','RMS')], .001),
              ('Pressure extrema [kPa]', [('p_min_Pa','minimum'),('p_max_Pa','maximum')], .001),
              ('Stress RMS [kPa]', [('effective_stress_Frobenius_RMS_Pa','effective'),('total_stress_Frobenius_RMS_Pa','total')], .001),
              ('Material settlement from PRE [mm]', [('top_material_settlement_mm','top'),('bottom_material_settlement_mm','bottom')], 1.),
              ('Front advance from PRE [m]', [('runout_from_PRE_front_m','')], 1.),
              ('Velocity RMS [m/s]', [('velocity_RMS_m_s','')], 1.),
              ('Maximum plastic history', [('max_kappa','')], 1.),
              ('5% nearest distance / dp', [('NN_q05_over_dp','')], 1.),
              ('Pairs at r < 0.7dp', [('pairs_r_lt_0p7dp','')], 1.)]
    fig, axes = plt.subplots(3,3,figsize=(15,10),layout='constrained')
    for ax, (title, columns, scale) in zip(axes.flat, charts):
        for i, analysis in enumerate(analyses):
            h = analysis['history']
            for j, (key, name) in enumerate(columns):
                ax.plot([q['tau_s'] for q in h], [q[key]*scale for q in h], color='C'+str(i), linestyle=('-','--')[j], label=(label(analysis)+' '+name).strip())
        ax.set(title=title,xlabel='Actual time since PRE [s]'); ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle('C08 psi=0 | Wendland H/dp=1.8 | AS exponent=2.55\nAS0.5 versus AS0.3; same 5 us step, all91 actual saves',fontsize=12)
    dest = Path(str(prefix)+'_history.png'); fig.savefig(dest,dpi=170,bbox_inches='tight'); plt.close(fig); files.append(dest)
    selected = [a['snapshots'] for a in analyses]
    need(len(analyses) == 2 and all(len(q) == 4 for q in selected) and list(selected[0]) == list(selected[1]), 'Same four actual snapshot parts required')
    keys = [('p','Pressure [kPa]',.001),('excess','Native p-P0 [kPa]',.001),('kappa','Plastic history',1.),('J','Volume ratio J',1.)]
    norms = {}
    for key, _, scale in keys:
        values = old.np.concatenate([s[key]*scale for snaps in selected for s in snaps.values()])
        lo, hi = float(values.min()), float(values.max())
        norms[key] = TwoSlopeNorm(vmin=lo,vcenter=0.,vmax=hi) if key in ('p','excess') and lo < 0 < hi else Normalize(vmin=lo,vmax=hi)
    xmin = min(float(s['pos'][:,0].min()) for snaps in selected for s in snaps.values())
    xmax = max(float(s['pos'][:,0].max()) for snaps in selected for s in snaps.values())
    zmin = min(float(s['pos'][:,2].min()) for snaps in selected for s in snaps.values())
    zmax = max(float(s['pos'][:,2].max()) for snaps in selected for s in snaps.values())
    for index, part in enumerate(selected[0]):
        fig, axes = plt.subplots(4,2,figsize=(12,11),layout='constrained')
        for row, (key, title, scale) in enumerate(keys):
            for col, analysis in enumerate(analyses):
                s = analysis['snapshots'][part]; ax = axes[row,col]
                pc = ax.scatter(s['pos'][:,0],s['pos'][:,2],c=s[key]*scale,s=4,linewidths=0,cmap='coolwarm' if row < 2 else 'viridis',norm=norms[key])
                ax.set(xlim=(min(-.04,xmin-.04),xmax+.04),ylim=(min(-.04,zmin-.04),max(2.04,zmax+.04)),xlabel='x [m]',ylabel='z [m]',title=label(analysis)+f" | actual tau={s['tau_s']:.6f}s")
                ax.set_aspect('equal')
            fig.colorbar(pc,ax=list(axes[row]),shrink=.85,label=title)
        fig.suptitle(f'Actual saved fields near requested tau={SNAPSHOTS[index]:g}s\nShared full ranges across both cases/all times; native p-P0 is not paper plastic excess',fontsize=11)
        dest = Path(str(prefix)+f'_fields_{index:02d}.png'); fig.savefig(dest,dpi=170,bbox_inches='tight'); plt.close(fig); files.append(dest)
    return files


def metrics_plot(analyses, prefix):
    fig, axes = old.plt.subplots(2,3,figsize=(13,8),layout='constrained')
    charts = [('runout_from_PRE_front_m','Front advance [m]',1.),('NN_q05_over_dp','5% nearest distance / dp',1.),('pairs_r_lt_0p7dp','Pairs at r < 0.7dp',1.),('current_mixture_KE_J_per_m','Current mixture KE [J/m]',1.),('p_min_Pa','Minimum pressure [kPa]',.001),('p_RMS_Pa','Pressure RMS [kPa]',.001)]
    for ax, (key,title,scale) in zip(axes.flat,charts):
        for a in analyses: ax.plot([q['tau_s'] for q in a['history']],[q[key]*scale for q in a['history']],label=label(a))
        ax.set(title=title,xlabel='Actual time since PRE [s]'); ax.grid(alpha=.2); ax.legend(fontsize=8)
    fig.suptitle('AS0.5 / AS0.3, fixed exponent2.55\nIdentical material, PRE, kernel and timestep',fontsize=12)
    dest = Path(str(prefix)+'_selection.png'); fig.savefig(dest,dpi=170,bbox_inches='tight'); old.plt.close(fig); return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--execution-authorized',action='store_true'); args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until both complete native91 receipts and root full-read')
    manifest = core.read(args.manifest)
    need(manifest['tag'] == TAG and manifest['reference_tag'] == CONTROL and manifest['snapshots_tau_s'] == SNAPSHOTS
         and [q['tag'] for q in manifest['cases']] == [CONTROL,CANDIDATE], 'Exact AS05/AS03 n2.55 manifest required')
    for spec in manifest['cases']:
        tag = spec['tag']
        need(path(spec['run']) == T/'logs'/(tag+'.run.json') and old.f32(spec['actualAS']['coefficient']) == old.f32(COEFFICIENTS[tag])
             and old.f32(spec['actualAS']['exponent']) == old.f32(2.55), 'Actual run/tag-specific AS values required')
    receipt = T/'logs'/(TAG+'.adapter.json'); need(not receipt.exists(), 'Existing adapter result/partial protected')
    before = [stat(q) for q in (Path(__file__),NOTE,Path(core.__file__),args.manifest,*READERS.values())]
    saved = core.TAG,core.load_receiver,core.metrics_plot,old.plot_results
    result = dict(stage=TAG+'.adapter',adapter_complete=False,physical_acceptance=False,before=before)
    try:
        need(not LOADED_CLOCKS, 'No repeated analysis in the same interpreter')
        core.TAG,core.load_receiver,core.metrics_plot,old.plot_results = TAG,load_receiver,metrics_plot,plot_results
        core.main()
        check = T/'logs'/(TAG+'.check.json'); final = core.read(check)
        need(final['analysis_complete'] and final['exact_matching_option_rows'] == 91 and final['consumed_stats_unchanged']
             and not final['physical_acceptance'] and not final['winner_selected'], 'All91 descriptive pairs required; no automatic acceptance')
        need(all(stat(q['path']) == q for q in before), 'Adapter/core/native builds changed during analysis')
        result.update(adapter_complete=True,analysis_check=stat(check),stats_unchanged=True,actual_common_step_time_rows=91,
                      case_native_builds={k:stat(v) for k,v in READERS.items()},no_native_or_solver_invocations=True,SHA_scans=0)
    except Exception as error:
        result.update(first_failure=str(error),partials_preserved=True); raise
    finally:
        core.TAG,core.load_receiver,core.metrics_plot,old.plot_results = saved
        with receipt.open('x',encoding='utf-8') as f: json.dump(result,f,indent=2,allow_nan=False); f.write('\n')


if __name__ == '__main__': main()
