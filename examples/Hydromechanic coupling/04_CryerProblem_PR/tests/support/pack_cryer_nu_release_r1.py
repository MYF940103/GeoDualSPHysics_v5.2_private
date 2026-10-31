"""Package the three new nu inputs with unchanged verified Cryer executables."""
import argparse
from decimal import Decimal, localcontext, ROUND_CEILING
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import zipfile

CASE = Path(__file__).resolve().parents[2]
REPO = CASE.parents[2]
PROGRAM_SHA = '652baea4814ddd106b69de11e785664c83802fad04f4965dab10feb35d7e9096'
TAG = 'cryer_nu_release_r1'
TABLE = [('010', '.1', '.001199', '1.20681285858154296875', 1265435),
         ('020', '.2', '.001103625', '1.11143779754638671875', 1165427),
         ('045', '.45', '.00032328409090909091', '.331096649169921875', 347180)]


def binding(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def save(path, data):
    with Path(path).open('x', encoding='utf-8') as stream: json.dump(data, stream, indent=2, allow_nan=False)


def variant(tag, nu, interval, end, steps):
    with localcontext() as ctx:
        ctx.prec = 60
        d = Decimal; n = d(nu); E = d(2000000); mf = d(200000000)/d('.3')
        K = E/(3*(1-2*n)); G = E/(2*(1+n)); H = K+4*G/3
        cv = H*d('1e-5')/(1000*d('9.81'))
        expected_interval = d('.001')*d('.05')**2/cv
        dt = d(2)**-20; target = d(2)**-7+d('.05')**2/cv
        assert abs(d(interval)-expected_interval) < d('1e-19')
        assert int((target/dt).to_integral_value(rounding=ROUND_CEILING)) == steps
        assert d(end) == steps*dt
        return dict(nu_tag=tag, nu=float(n), dt_s=str(dt), end_s=end, steps=steps,
            output_interval_s=interval, expected_frames=1065,
            K_pa=float(K), G_pa=float(G), lambda_pa=float(K-2*G/3), H_pa=float(H),
            finite_storage_B=float(mf/(K+mf)), finite_cv_m2_s=float((H*d('1e-5')/(1000*d('9.80665')))/(1+H/mf)),
            legacy_cv_m2_s=float(cv), expected_initial_soil_cs_m_s=float((H/d(2100)).sqrt()),
            legacy_Tv_final=float(cv*(d(end)-d(2)**-7)/d('.05')**2),
            physical_acceptance=False, independent_full_half_validated=False)


def run():
    manifest_path = CASE/'support/cryer_nu_server_manifest_r1.json'
    package = CASE/'Cryer_release_nu010_020_045_r1_Windows_RTXA6000.zip'
    checksum = package.with_suffix('.zip.sha256')
    check_path = CASE/'tests/logs/cryer_nu_package_r1.check.json'
    assert not any(p.exists() for p in [manifest_path, package, checksum, check_path]), 'Never overwrite retained files'
    old_path = CASE/'support/cryer_server_manifest_r2.json'; old = json.loads(old_path.read_text(encoding='utf-8-sig'))
    old_check = json.loads((CASE/'tests/logs/cryer_release_portable_r2.check.json').read_text())
    assert old_check['passed'] and old_check['smoke_native_verified']
    assert old['verified_program_sha256'] == PROGRAM_SHA
    runtime = [e for e in old['files'] if e['entry'].startswith('support/bin/')]
    assert len(runtime) == 9
    for entry in runtime:
        actual = binding(CASE/entry['entry']); assert all(actual[k] == entry[k] for k in ['bytes', 'sha256'])
    entries = ['support/run_cryer_nu_release_r1.ps1', 'support/README_cryer_nu_release_r1.md', 'LICENSE']
    variants = []; xml_comparisons = []
    baseline_path = CASE/'CaseCryerProblem_PR_release_r2_Def.xml'
    baseline = ET.parse(baseline_path).getroot()
    base_nodes = list(baseline.iter())
    for args in TABLE:
        v = variant(*args); variants.append(v)
        stem = 'CaseCryerProblem_PR_release_nu'+v['nu_tag']+'_r1'
        entries += [stem+'_Def.xml', 'x'+stem+'_win64_GPU.bat']
        root = ET.parse(CASE/(stem+'_Def.xml')).getroot(); nodes = list(root.iter())
        assert len(nodes) == len(base_nodes)
        differences = []
        for a, b in zip(base_nodes, nodes):
            assert a.tag == b.tag
            for key in set(a.attrib)|set(b.attrib):
                if key.startswith('comment'): continue
                if a.get(key) != b.get(key): differences.append((a.tag, a.get('key', a.get('time')), key, a.get(key), b.get(key)))
        assert {(r[0], r[1], r[2]) for r in differences} == {
            ('PRvs', None, 'value'), ('parameter', 'TimeMax', 'value'),
            ('parameter', 'TimeOut', 'value'), ('tout', '0.0078125', 'timeout')}
        assert float(root.find('.//PRvs').get('value')) == v['nu']
        for key, value in [('DtFixed', v['dt_s']), ('DtIni', v['dt_s']), ('TimeMax', v['end_s']), ('TimeOut', v['output_interval_s'])]:
            assert Decimal(root.find('.//parameter[@key="'+key+'"]').get('value')) == Decimal(value)
        assert Decimal(root.find('.//timeout/tout[@time="0.0078125"]').get('timeout')) == Decimal(v['output_interval_s'])
        xml_comparisons.append(dict(nu_tag=v['nu_tag'], allowed_differences=differences))
    entries += [e['entry'] for e in runtime]; assert len(entries) == 18 and len(set(entries)) == 18
    payload = [dict(entry=entry, **{k:v for k,v in binding(CASE/entry).items() if k != 'path'}) for entry in entries]
    head = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    manifest = dict(format='Cryer_nu_release_r1_windows_bundle', packaging_checkpoint_supplied=head,
        checkpoint_scope='Packaging checkpoint, not a newly compiled program or old server execution identity.',
        verified_program_sha256=PROGRAM_SHA, historical_source_checkpoint='7c0006ea9d90571b72a5d691c652577b025f5b83',
        target='Windows x64 / NVIDIA RTX A6000; compatible CUDA11.7 driver and system UCRT required.',
        baseline_manifest=binding(old_path), baseline_portable_check=binding(CASE/'tests/logs/cryer_release_portable_r2.check.json'),
        reviewed_diagnosis=binding(CASE/'tests/logs/cryer_actual_budget_review_r1.check.json'),
        compiled_source_copies=old['compiled_source_copies'], provenance=old['provenance'],
        source_scope=old['compiled_scope'], variants=variants, files=payload,
        physical_acceptance=False, full_cycle_acceptance=False, programs_executed=False,
        manifest_self_hash='Excluded; external package review binds manifest and ZIP.',
        limits='Three nu extensions of the unchanged verified baseline. Their startup/peak/full accuracy is not inherited from nu=.3. No new rho, mass, operator, shifting or full-double correction.')
    save(manifest_path, manifest)
    all_entries = entries+['support/cryer_nu_server_manifest_r1.json']
    with zipfile.ZipFile(package, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for entry in all_entries: archive.write(CASE/entry, entry)
    with zipfile.ZipFile(package) as archive:
        assert len(archive.namelist()) == 19 and set(archive.namelist()) == set(all_entries)
        for entry in all_entries: assert hashlib.sha256(archive.read(entry)).hexdigest() == binding(CASE/entry)['sha256']
    digest = binding(package)
    with checksum.open('x', encoding='ascii', newline='\n') as stream: stream.write(digest['sha256']+'  '+package.name+'\n')
    save(check_path, dict(package_consistency_passed=True, xml_parameter_changes_checked=True,
        packer=binding(__file__), baseline_xml=binding(baseline_path), xml_comparisons=xml_comparisons,
        manifest=binding(manifest_path), zip=digest, checksum=binding(checksum), verified_zip_entries=19,
        programs_executed=False, portable_smoke_passed=False, physical_acceptance=False, full_cycle_acceptance=False))
    print(json.dumps(dict(package_consistency_passed=True, zip=digest, variants=variants), indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--run', action='store_true')
    if p.parse_args().run: run()
    else: p.print_help()
