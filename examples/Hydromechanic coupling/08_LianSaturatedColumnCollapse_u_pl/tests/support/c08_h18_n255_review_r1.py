"""Original-AS05 versus exact AS0.5/n2.55 offline adapter; unchanged receiver numerical gates."""
import argparse, json
from pathlib import Path
import c08_h18_wend_receiver_review_r1 as core

old, plastic = core.old, core.plastic
need, table = core.need, core.table
TAG = 'c08_h18_n255_review_r1'; NOTE = core.T / 'notes' / (TAG + '.md')
CONTROL, CANDIDATE = 'c08_h18_wend_psi0_a05_w09_r1', 'c08_h18_as05_n255_r1'
BUILD = core.T / 'logs/c08_h18_n255_native_r1.build.json'
ORIGINAL_LOAD = core.load_receiver


def profile_xml_n255(spec,xml,source_csv):
    rows=table(spec['material_csv']);p={q['key']:q['value'] for q in rows};keys=plastic.MATERIAL_KEYS|{'Kernel','ArtificialStressCoef','ArtificialStressExp'};need(len(rows)==len(p)==17 and set(p)==keys and p['group']=='psi0' and p['fresh_trigger_active']=='0','Actual17-key psi0/Wendland receiver profile required')
    soil=xml.find('execution/special/soils');pairs=[(q.get('key'),q.get('value')) for q in xml.findall('execution/parameters/parameter')];pars=dict(pairs);need(soil is not None and len(pars)==len(pairs),'Actual unique receiver material/parameter XML required')
    for key in keys-{'group','fresh_trigger_active'}:
        node=soil.find(key);value=pars[key] if key in ('Kernel','DPCtes','ArtificialStressCoef','ArtificialStressExp') else (node.get('value') if node is not None else '1.65' if key=='SoilTriggerFos' else None);need(value is not None and old.f32(p[key])==old.f32(value),'Receiver17CSV does not match actual XML: '+key)
    original={q['key']:q['value'] for q in table(source_csv)}
    for key in plastic.MATERIAL_KEYS|{'Kernel'}:need(p[key]==original[key] if key in ('group','fresh_trigger_active') else old.f32(p[key])==old.f32(original[key]),'Receiver differs from its same-material source: '+key)
    a=spec['actualAS'];need(old.f32(p['Kernel'])==2 and old.f32(a['coefficient'])==old.f32(.5) and old.f32(a['exponent'])==old.f32(2.55) and old.f32(p['ArtificialStressCoef'])==old.f32(a['coefficient']) and old.f32(p['ArtificialStressExp'])==old.f32(a['exponent']),'Explicit actual AS coefficient/exponent differs')
    return pars


def load_receiver(spec, src, src_spec, consumed):
    if spec['tag'] == CONTROL: bundle = ORIGINAL_LOAD(spec, src, src_spec, consumed)
    else:
        need(spec['tag'] == CANDIDATE, 'Only the exact n255 candidate may use the narrow reader/profile')
        saved_build, saved_profile = core.BUILD, core.profile_xml
        try:
            core.BUILD, core.profile_xml = BUILD, profile_xml_n255
            bundle = ORIGINAL_LOAD(spec, src, src_spec, consumed)
        finally: core.BUILD, core.profile_xml = saved_build, saved_profile
    need(bundle['count'] == 91 and bundle['runtime_observed']['passed'], 'Only genuinely completed full91 windows may be compared')
    return bundle


def metrics_plot(analyses, prefix):
    labels = {CONTROL: 'Original n=3.825', CANDIDATE: 'Single-factor n=2.55'}
    fig, axes = old.plt.subplots(2, 3, figsize=(13, 8), layout='constrained')
    charts = (('runout_from_PRE_front_m', 'Front advance from PRE [m]', 1.), ('NN_q05_over_dp', '5% nearest distance / dp', 1.), ('pairs_r_lt_0p7dp', 'Pairs at r < .7dp', 1.), ('current_mixture_KE_J_per_m', 'Current mixture KE [J/m]', 1.), ('p_min_Pa', 'Minimum absolute p [kPa]', .001), ('p_RMS_Pa', 'Absolute p RMS [kPa]', .001))
    for ax, (key, title, scale) in zip(axes.flat, charts):
        for a in analyses: ax.plot([q['tau_s'] for q in a['history']], [q[key] * scale for q in a['history']], label=labels[a['summary']['tag']])
        ax.set(title=title, xlabel='Actual time since PRE release [s]'); ax.grid(alpha=.2); ax.legend(fontsize=7)
    fig.suptitle('Wendland psi0, original raw FS: exponent 3.825 versus 2.55\nBoth use AS coefficient 0.5; inspect pressure, spacing and motion together')
    destination = Path(str(prefix) + '_selection.png'); fig.savefig(destination, dpi=170); old.plt.close(fig)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--manifest', type=Path, required=True); parser.add_argument('--execution-authorized', action='store_true'); args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until full runtime91, one separately admitted native read, and root full-read')
    manifest = core.read(args.manifest); tag = manifest['tag']; need(core.re.fullmatch(r'[A-Za-z0-9_]+', tag), 'Safe fresh analysis tag required')
    cases = manifest['cases']; need(len(cases) == 2 and {q['tag'] for q in cases} == {CONTROL, CANDIDATE} and manifest['reference_tag'] == CONTROL, 'Exact original-control/n255 pair and reference required')
    for spec in cases:
        need(core.path(spec['run']) == core.T / 'logs' / (spec['tag'] + '.run.json') and old.f32(spec['actualAS']['coefficient']) == old.f32(.5) and old.f32(spec['actualAS']['exponent']) == old.f32(3.825 if spec['tag'] == CONTROL else 2.55), 'No relabelled run or AS values allowed')
    receipt = core.T / 'logs' / (tag + '.adapter.json'); need(not receipt.exists(), 'Existing adapter record protected')
    before = [core.stat(q) for q in (Path(__file__), NOTE, Path(core.__file__), args.manifest, BUILD)]
    saved_load, saved_plot = core.load_receiver, core.metrics_plot; core.load_receiver, core.metrics_plot = load_receiver, metrics_plot
    try: core.main()
    finally: core.load_receiver, core.metrics_plot = saved_load, saved_plot
    after = [core.stat(q['path']) for q in before]; need(before == after, 'Adapter/core/manifest/native build changed during analysis')
    check = core.T / 'logs' / (tag + '.check.json')
    with receipt.open('x', encoding='utf-8') as handle:
        json.dump(dict(stage=TAG + '.adapter', analysis_check=core.stat(check), before=before, after=after, stats_unchanged=True, physical_acceptance=False), handle, indent=2, allow_nan=False); handle.write('\n')


if __name__ == '__main__': main()
