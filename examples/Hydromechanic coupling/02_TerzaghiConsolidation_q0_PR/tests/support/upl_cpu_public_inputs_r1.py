"""Prepare limited public-CPU runtime inputs only; never execute GenCase or a solver."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import xml.etree.ElementTree as ET

REVISION = 'upl_cpu_public_r1'
A = 2.0 ** -9
END = 2.0 ** -15
CADENCE = 2.0 ** -23
CK = 2.0 ** -13
PUBLIC_KEYS = ('HydroMechDynamicSeepage', 'HydroMechConductivityModel', 'HydroMechConductivityCk')
PRIVATE_KEYS = {'PorosityObserver', 'PorosityFeedback', 'DynamicPorePressure', 'DynamicPoreWall', 'DynamicPoreConductivity'}


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def entry(path):
    path = path.resolve()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def objects(value):
    if isinstance(value, dict):
        if all(key in value for key in ('path', 'bytes', 'sha256')):
            yield value
        for item in value.values():
            yield from objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from objects(item)


def read_receipt(path, passed=False):
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    need(data.get('passed') if passed else data.get('status') == 'seeds_prepared_not_solved',
         'Retained receipt is not admitted: ' + str(path))
    return data


def sealed(path, receipt):
    path = path.resolve()
    records = [item for item in objects(receipt) if Path(item['path']).resolve() == path]
    need(records, 'No retained file binding for ' + str(path))
    actual = entry(path)
    for record in records:
        need(record['bytes'] == actual['bytes'] and record['sha256'].lower() == actual['sha256'],
             'Retained file hash changed: ' + str(path))
    return actual


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def initial_columns(path, count, nz, dp):
    """Read only the accepted J1/p0 constant-wave initial native frame, not mapped-J/private-p128."""
    with path.open('rb') as stream:
        header = stream.read(12)
        need(len(header) == 12 and struct.unpack('<III', header) == (count, 26, 257), 'Wrong accepted weak-wave schema')
        need(struct.unpack('<d', stream.read(8))[0] == 0., 'Initial reference clock is not zero')
        raw = stream.read(count * 26 * 8)
        need(len(raw) == count * 26 * 8, 'Truncated initial reference')
    columns = {}
    points = set()
    for row in struct.iter_unpack('<26d', raw):
        x, y, z, vx, vy, vz = row[:6]
        ix, iz = x / dp - .5, z / dp - .5
        need(y == 0 and ix == round(ix) and iz == round(iz) and 0 <= ix < 32 and 0 <= iz < nz, 'Wrong reference lattice')
        need((ix, iz) not in points, 'Duplicate initial reference position')
        points.add((ix, iz))
        need(vy == vz == row[6] == row[7] == row[9] == row[16] == 0 and row[8] == 1 and all(v == 0 for v in row[10:16]),
             'Reference is not the declared initially stress-free J1/p0 wave')
        need(f32(vx) == vx and abs(vx - A * math.sin(2 * math.pi * x / .125)) <= 2 * 2.0 ** -23 * A,
             'Reference velocity is not the unchanged weak sine')
        if int(ix) in columns:
            need(columns[int(ix)] == vx, 'A reference column has nonuniform velocity')
        columns[int(ix)] = vx
    need(len(points) == count and len(columns) == 32 and max(abs(v) for v in columns.values()) > .5 * A,
         'Velocity initialization is empty')
    return columns


def element_signature(element):
    def plain(node):
        return [node.tag, sorted(node.attrib.items()), (node.text or '').strip(),
                [plain(child) for child in node if isinstance(child.tag, str)]]
    return hashlib.sha256(json.dumps(plain(element), separators=(',', ':'), ensure_ascii=True).encode('ascii')).hexdigest()


def one(parent, tag):
    nodes = parent.findall(tag)
    need(len(nodes) == 1, 'Expected exactly one ' + tag)
    return nodes[0]


def set_parameter(parameters, key, value):
    nodes = [node for node in parameters.findall('parameter') if node.get('key') == key]
    need(len(nodes) == 1, 'Parameter missing or duplicated: ' + key)
    nodes[0].set('value', format(value, '.17g'))
    return nodes[0]


def runtime(source, columns, case):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(source, parser=parser)
    root = tree.getroot()
    definition = one(root, 'casedef')
    before_geometry = element_signature(definition)
    execution = one(root, 'execution')
    special = one(execution, 'special')
    hydro = one(special, 'hydromechanics')
    parameters = one(execution, 'parameters')
    constants = one(execution, 'constants')
    need(float(one(constants, 'dp').get('value')) == case['dp'], 'Sealed runtime dp is not exact')
    for key, value in (('HydroMech', '1'), ('HydroMechInitMode', '0'), ('HydroMechTopLoadMode', '0'), ('HydroMechDrainage', '0')):
        need(one(hydro, key).get('value') == value, 'Unsupported original hydro setting ' + key)
    need(not any(node.tag in PRIVATE_KEYS or node.get('key') in PRIVATE_KEYS for node in root.iter()), 'Private harness controls in a public input')
    need(not any(hydro.findall(key) for key in PUBLIC_KEYS), 'Source already contains new public controls')
    if case['dynamic'] is not None:
        ET.SubElement(hydro, PUBLIC_KEYS[0], value=str(int(case['dynamic'])),
                      comment='Limited fresh 2D zero-gravity CPU mode only; no GPU or restart support')
    if case['dynamic']:
        ET.SubElement(hydro, PUBLIC_KEYS[1], value=str(case['model']),
                      comment='0 constant initial k; 1 smooth exponential k(J)')
        if case['model'] == 1:
            ET.SubElement(hydro, PUBLIC_KEYS[2], value=format(CK, '.17g'),
                          comment='Manufactured sensitivity only; not calibrated permeability data')
    initializers = special.findall('initialize')
    need(len(initializers) <= 1, 'Duplicate initialize node')
    initialize = initializers[0] if initializers else ET.Element('initialize')
    if not initializers:
        special.insert(0, initialize)
    need(not initialize.findall('fluidvelocity'), 'Source already has velocity initialization')
    for index in range(32):
        node = ET.SubElement(initialize, 'fluidvelocity', mkfluid='0')
        limits = ET.SubElement(node, 'onlypos')
        ET.SubElement(limits, 'posmin', x=format((index + .25) * case['dp'], '.17g'))
        ET.SubElement(limits, 'posmax', x=format((index + .75) * case['dp'], '.17g'))
        ET.SubElement(node, 'direction', x='1', y='0', z='0')
        # A double decimal representation of the stored float round-trips through ReadElementFloat.
        ET.SubElement(node, 'velocity', v=format(columns[index], '.17g'))
    dt = case['dt']
    need(float(set_parameter(parameters, 'DtIni', dt).get('value')) == dt, 'Initial dt decimal roundtrip failed')
    set_parameter(parameters, 'DtFixed', dt)
    set_parameter(parameters, 'TimeMax', case['steps'] * dt)
    set_parameter(parameters, 'TimeOut', case['cadence'])
    need(case['steps'] * dt == case['end'] and case['cadence'] / dt == round(case['cadence'] / dt), 'Clock is not dyadic aligned')
    need(element_signature(definition) == before_geometry, 'Preparation changed geometry/material casedef')
    root.insert(0, ET.Comment('Public CPU input copy only: no GenCase run; exact retained BI4 geometry. Not a formal/server release.'))
    ET.indent(tree, space='    ')
    encoded = ET.tostring(root, encoding='utf-8', xml_declaration=True) + b'\n'
    reread = ET.fromstring(encoded)
    need(len(reread.findall('./execution/special/initialize/fluidvelocity')) == 32, 'Initializer count changed')
    return encoded, before_geometry


def cases():
    result = []
    for tag, steps, dt in (('c', 512, 2.0 ** -24), ('h', 1024, 2.0 ** -25)):
        result.append(dict(label='periodic_constant_' + tag, geometry='periodic', tag=tag, steps=steps, dt=dt, model=0, dynamic=True,
                           dp=1./256., native=512, fixed=0, nz=16, cadence=CADENCE, samples=257, end=END, configuration='ReleaseCPU'))
    for model, name in ((0, 'constant'), (1, 'evolving')):
        for tag, steps, dt in (('c', 1024, 2.0 ** -25), ('h', 2048, 2.0 ** -26)):
            result.append(dict(label='wall_' + name + '_' + tag, geometry='wall', tag=tag, steps=steps, dt=dt, model=model, dynamic=True,
                               dp=1./512., native=1024, fixed=256, nz=32, cadence=CADENCE, samples=257, end=END, configuration='ReleaseCPU'))
    result.insert(0, dict(label='debug_wall_evolving_smoke', geometry='wall', tag='c', steps=2, dt=2.0 ** -25, model=1, dynamic=True,
                          dp=1./512., native=1024, fixed=256, nz=32, cadence=2.0 ** -25, samples=3, end=2.0 ** -24, configuration='DebugCPU'))
    for value, name in ((None, 'default'), (False, 'explicit')):
        result.append(dict(label='OFF_' + name, geometry='periodic', tag='c', steps=8, dt=2.0 ** -24, model=0, dynamic=value,
                           dp=1./256., native=512, fixed=0, nz=16, cadence=2.0 ** -24, samples=9, end=2.0 ** -21, configuration='ReleaseCPU'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', required=True, help='Create new input copies only, never launch programs')
    args = parser.parse_args()
    tests = Path(__file__).resolve().parents[1]
    manifest = tests / 'logs' / (REVISION + '.inputs.json')
    note = tests / 'notes' / (REVISION + '.json')
    need(not manifest.exists() and note.is_file(), 'Retained manifest protected or declaration missing')
    seed_paths = {'periodic': tests / 'logs/upl_p3_spatial_seed_r1.inputs.json',
                  'wall': tests / 'logs/upl_p3_wall_wave_seed_r3.inputs.json'}
    control_paths = {'periodic': tests / 'logs/upl_p3_spatial_wave_ReleaseCPU_r5.check.json',
                     'wall': tests / 'logs/upl_p3_wall_wave_ReleaseCPU_r4.check.json'}
    seeds = {key: read_receipt(path) for key, path in seed_paths.items()}
    controls = {key: read_receipt(path, passed=True) for key, path in control_paths.items()}
    bindings = [entry(Path(__file__)), entry(note)] + [entry(path) for path in list(seed_paths.values()) + list(control_paths.values())]
    columns = {}
    for geometry, suffix in (('periodic', 'upl_p3_spatial_wave_ReleaseCPU_r5_n32_c'), ('wall', 'upl_p3_wall_wave_ReleaseCPU_r4_k1_c')):
        path = tests / 'outputs' / suffix / 'physical.bin'
        bindings.append(sealed(path, controls[geometry]))
        columns[geometry] = initial_columns(path, 512 if geometry == 'periodic' else 1024, 16 if geometry == 'periodic' else 32,
                                             1./256. if geometry == 'periodic' else 1./512.)
    prepared = []
    destinations = []
    for case in cases():
        geometry, tag = case['geometry'], case['tag']
        folder = tests / 'outputs' / (('upl_p3_spatial_seed_r1_n32_' if geometry == 'periodic' else 'upl_p3_wall_wave_seed_r3_') + tag)
        basename = 'CaseUplSpatial_n32_' + tag if geometry == 'periodic' else 'CaseUplWall_' + tag
        source_xml, source_bi4 = folder / (basename + '.xml'), folder / (basename + '.bi4')
        source_bindings = [sealed(source_xml, seeds[geometry]), sealed(source_bi4, seeds[geometry])]
        bindings.extend(source_bindings)
        destination = tests / 'outputs' / ('upl_cpu_public_seed_r1_' + case['label'])
        need(destination.parent == tests / 'outputs' and not destination.exists(), 'Retained destination protected: ' + str(destination))
        need(not (tests / 'outputs' / ('upl_cpu_public_r1_' + case['label'])).exists(), 'Planned solver output is already retained')
        encoded, signature = runtime(source_xml, columns[geometry], case)
        prepared.append((case, source_xml, source_bi4, source_bindings, destination, encoded, signature))
        destinations.append(destination)
    need(len(set(destinations)) == 9, 'Duplicate or missing planned input label')
    results = []
    for case, source_xml, source_bi4, source_bindings, destination, encoded, signature in prepared:
        destination.mkdir()
        target_bi4, target_xml = destination / source_bi4.name, destination / source_xml.name
        shutil.copy2(source_bi4, target_bi4)
        need(entry(target_bi4)['sha256'] == source_bindings[1]['sha256'], 'Copied BI4 geometry is not byte-identical')
        with target_xml.open('xb') as stream:
            stream.write(encoded)
        output = tests / 'outputs' / ('upl_cpu_public_r1_' + case['label'])
        need(not output.exists(), 'Planned solver output already exists; no launch or overwrite')
        exe = tests.parents[3] / 'bin/windows' / ('DualSPHysics5.2CPU_win64_debug.exe' if case['configuration'] == 'DebugCPU' else 'DualSPHysics5.2CPU_win64.exe')
        # Program identity and new source-build gates belong to the later root-owned runner.
        command = [str(exe), '-cpu', '-ompthreads:1', '-stable', str(target_xml.with_suffix('')), str(output), '-dirdataout', 'data', '-svres']
        results.append(dict(case, input_prefix=str(target_xml.with_suffix('')), planned_output=str(output), planned_canonical_argv=command,
                            source=source_bindings, copied_geometry=entry(target_bi4), runtime=entry(target_xml), casedef_signature=signature,
                            velocity_initializer_columns=32, initial_J=1., initial_p=0., initial_effective_stress=0.,
                            solver_executed=False, source_program_identity_pending_root_freeze=True))
    # Reverify retained inputs after creating copies; never rewrite old bytes.
    unique = {item['path']: item for item in bindings}
    for record in unique.values():
        actual = entry(Path(record['path']))
        need(actual == record, 'Preparation modified or raced a retained input')
    report = dict(status='runtime_inputs_prepared_not_solved', revision=REVISION, new_gencase_calls=0, new_solver_calls=0,
                  python=sys.version, inputs=list(unique.values()), jobs=results, all_copied_BI4_byte_identical=True,
                  old_geometry_and_outputs_unchanged=True, physical_acceptance=False)
    with manifest.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'prepared_inputs': len(results), 'manifest': str(manifest), 'sha256': sha(manifest)}))


if __name__ == '__main__':
    main()
