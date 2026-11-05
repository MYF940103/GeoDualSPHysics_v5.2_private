"""Prepare one fresh 3-D dynamic Cryer seed; retained geometry and formal data untouched."""
from pathlib import Path
import csv
import json
import re
import shutil

T = Path(__file__).resolve().parents[1]
C = T.parent
TAG = 'upl_cryer_freebody_short_r1'


def replace_value(text, tag, value):
    text, n = re.subn(r'(<'+tag+r'\b[^>]*\bvalue=")[^"]*(")',
                      lambda m: m[1]+value+m[2], text)
    assert n == 1, (tag, n)
    return text


def prepare(text):
    assert '<HydroMechDynamicSeepage' not in text
    text, n = re.subn(r'(^[ \t]*)(<HydroMech value="1"[^\n]*\n)',
        lambda m: m[1]+m[2]+m[1]+'<HydroMechDynamicSeepage value="1" comment="Explicit dynamic seepage; bounded 3-D free-body candidate" />\n',
        text, flags=re.MULTILINE)
    assert n == 1
    text = replace_value(text, 'PoreDarcySymmetricCorr', '0')
    text, n = re.subn(r'^[ \t]*<timeout>.*?</timeout>\s*\n', '', text, flags=re.MULTILINE | re.DOTALL)
    assert n == 1
    values = dict(DtIni='0.00000095367431640625', DtFixed='0.00000095367431640625',
                  TimeMax='0.00830078125', TimeOut='0.0001220703125')
    for key, value in values.items():
        text, n = re.subn(r'(<parameter key="'+key+r'" value=")[^"]*("[^\n]*comment=")[^"]*(")',
            lambda m: m[1]+value+m[2]+'Bounded fresh u-pl short diagnostic; not a formal run'+m[3], text)
        assert n == 1, key
    return text


def main():
    source = C / 'CaseCryerProblem_PR_symc_nu030_out/CaseCryerProblem_PR_symc_nu030'
    definition = C / 'CaseCryerProblem_PR_symc_nu030_Def.xml'
    seed = T / 'outputs' / (TAG+'_seed')
    config = T / 'configs' / (TAG+'_Def.xml')
    receipt = T / 'notes' / (TAG+'.prepare.json')
    clocks = [T / 'configs' / (TAG+suffix+'.clock.csv') for suffix in ('_smoke', '')]
    assert not any(p.exists() for p in [seed, config, receipt, *clocks])
    inputs = [Path(str(source)+suffix) for suffix in ('.xml', '.bi4')]+[definition]
    observations = [dict(path=str(p), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns) for p in inputs]
    runtime, formal = [prepare(p.read_text(encoding='utf-8-sig')) for p in (inputs[0], definition)]
    seed.mkdir()
    (seed/(TAG+'.xml')).write_text(runtime, encoding='utf-8')
    shutil.copy2(inputs[1], seed/(TAG+'.bi4'))
    config.write_text(formal, encoding='utf-8')
    for p, steps in zip(clocks, [[0, 1], list(range(0, 8705, 128))]):
        with p.open('x', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(['part', 'time_s', 'completed_step', 'saved_step', 'dt_s'])
            for part, n in enumerate(steps):
                writer.writerow([part, format(n*2**-20, '.17g'), n, max(0, n-1), format(2**-20, '.17g')])
    result = dict(stage=TAG+'.prepare', prepared_only=True, physical_acceptance=False,
        input_prefix=str(seed/TAG), definition=str(config), source_observations=observations,
        original_native_geometry_copied=True, original_fixed_IDs_not_removed=True,
        dt_s=2**-20, steps=8704, frames=69, end_s=17*2**-11, ramp_s=2**-8, drainage_s=2**-7,
        clocks=[str(p) for p in clocks], constant_cadence_no_special_timeout=True,
        source_whole_framework_change='master1; legacy Darcy switch0 because complete dynamic rate owns its operator',
        no_new_half_chain=True, fresh_SHA_scans=0, solver_launched=False)
    with receipt.open('x', encoding='utf-8') as stream: json.dump(result, stream, indent=2)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
