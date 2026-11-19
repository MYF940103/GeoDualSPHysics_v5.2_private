"""Build the private Cryer P3 CUDA pressure-row integration and check short native trajectories."""
import argparse
import csv
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

import upl_tpi_cryer_gpu_build_r1 as vs
from cryer_p3_gpu_build_r1 import verify
from cryer_p3_gpu_prepare_r1 import change, read, write


T = Path(__file__).resolve().parents[1]
OUT = T / 'outputs'
LOG = T / 'logs'
PREFIX = 'cryer_row_gpu_r1'
BASE = OUT / 'cryer_p3_gpu_r2_source'
SRC = OUT / (PREFIX + '_source')
ROW = 'upl_tpi_cryer_gpu_r1.cuh'
CUDA_TU = 'JSphGpu_ker.cu'
PROGRAM_PROFILES = {'default128': 'Release', 'b64': 'Release', 'debug2': 'Debug'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, data):
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2, allow_nan=False)


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def identity(path):
    return dict(path=str(path.resolve()), sha256=sha(path), bytes=path.stat().st_size)


def need(ok, message):
    if not ok:
        raise ValueError(message)


def prepare():
    receipt = LOG / (PREFIX + '.source.json')
    need(not receipt.exists() and not SRC.exists(), 'Existing source or receipt')
    text = read(BASE / ROW)
    text = change(text, '#include <cfloat>', '#include "TpiPressureRow.h"')
    text = change(text, '''  o.prediction=alpha==0.?double(o.pn):__dadd_rn(double(o.pn),__dmul_rn(alpha,__dsub_rn(double(o.pn),double(o.previous))));
  if(!isfinite(o.prediction)||fabs(o.prediction)>FLT_MAX){Bad(d,512,id);return;}
  o.half=drained?0.f:__double2float_rn(o.prediction);o.q=o.half;''', '''  const auto scheme=alpha==0.?tpi_pressure::Predictor::Current:tpi_pressure::Predictor::Linear;
  if(!tpi_pressure::Predict(scheme,o.pn,o.previous,o.prediction)){Bad(d,512,id);return;}
  o.half=drained?0.f:tpi_pressure::WritePressure(o.prediction);o.q=o.half;''')
    text = change(text, '__double2float_rn(d.rows[id].prediction)', 'tpi_pressure::WritePressure(d.rows[id].prediction)')
    text = change(text, '''  double raw=0.;if(!o.drained){if(!isfinite(o.S)||o.S<=0||!isfinite(o.R)||!isfinite(o.q)){Bad(d,32768,id);return;}
    raw=__dadd_rn(double(o.q),__ddiv_rn(o.R,o.S));}
  if(!isfinite(raw)||fabs(raw)>FLT_MAX){Bad(d,65536,id);return;}o.raw=__double2float_rn(raw);''', '''  if(!o.drained&&(!isfinite(o.S)||o.S<=0||!isfinite(o.R)||!isfinite(o.q))){Bad(d,32768,id);return;}
  if(!tpi_pressure::Endpoint(o.drained!=0,o.q,o.S,o.R,o.raw)){Bad(d,65536,id);return;}''')
    shutil.copytree(BASE, SRC)
    write(SRC / ROW, text)
    component = T / 'support/TpiPressureRow.h'
    shutil.copy2(component, SRC / component.name)
    base_files = sorted(p for p in BASE.iterdir() if p.is_file())
    changed = [p.name for p in base_files if sha(p) != sha(SRC / p.name)]
    need(changed == [ROW] and sha(component) == sha(SRC / component.name), 'Unexpected source diff')
    save(receipt, dict(base=str(BASE), source=str(SRC), changed=changed, original=identity(BASE / ROW),
                       copied_files=len(base_files)-1, changed_header=identity(SRC / ROW),
                       component=identity(SRC / component.name), tu=identity(SRC / CUDA_TU),
                       original_programs=['cryer_p3_gpu_r2_Debug','cryer_p3_gpu_r2_Release']))


def call(args, cwd, env, log):
    start = time.time()
    with log.open('xb') as f:
        proc = subprocess.Popen(args, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT)
        rc = proc.wait()
        win = wintypes.DWORD()
        handle = wintypes.HANDLE(int(proc._handle))
        if not ctypes.WinDLL('kernel32', use_last_error=True).GetExitCodeProcess(handle, ctypes.byref(win)):
            raise ctypes.WinError(ctypes.get_last_error())
    return dict(argv=args, cwd=str(cwd), pid=proc.pid, popen_exit=rc, win32_exit=win.value,
                start_utc_s=start, wall_s=time.time()-start, log=identity(log))


def build(config):
    tag = PREFIX + '_' + config
    folder = OUT / tag
    receipt = LOG / (tag + '.build.json')
    old = OUT / ('cryer_p3_gpu_r2_' + config)
    old_info = load(LOG / (old.name + '.build.json'))
    full = load(verify(old_info['original_receipt']))
    source = load(LOG / (PREFIX + '.source.json'))
    for entry in ('changed_header', 'component', 'tu'):
        need(sha(Path(source[entry]['path'])) == source[entry]['sha256'], 'Source changed '+entry)
    need(old_info['passed'] and full['passed'] and not receipt.exists(), 'Base build or receipt')
    out = folder / 'out'
    temp = Path(os.environ['TEMP']) / tag
    need(not folder.exists() and not temp.exists() and ' ' not in str(temp), 'Existing build or invalid temp')
    out.mkdir(parents=True)
    temp.mkdir()
    envproc = subprocess.check_output(['cmd.exe','/d','/c',str(verify(full['environment_batch']))], encoding='mbcs')
    env = {k.upper():v for k,v in (x.split('=',1) for x in envproc.splitlines() if '=' in x and not x.startswith('='))}
    for name in ('CL','_CL_','LINK','_LINK_'):
        env.pop(name, None)
    mslog = LOG / ('upl_tpi_cryer_gpu_' + config + '_r1.msbuild.log')
    flags = vs.nvcc_commands(mslog)[CUDA_TU.lower()]['flags']
    old_flags = list(flags)
    obj = folder / (CUDA_TU + '.obj')
    flags[flags.index('-o')+1] = str(obj)
    flags[flags.index('--keep-dir')+1] = str(temp)
    for i, flag in enumerate(flags):
        if flag.lower() == '-xcompiler' and '/Fd' in flags[i+1]:
            flags[i+1], count = re.subn(r'/Fd\S+', lambda m:'/Fd'+str(temp/'vc143.pdb'), flags[i+1])
            need(count == 1, 'NVCC host PDB')
    need(vs.normalize_nvcc(flags)[0] == vs.normalize_nvcc(old_flags)[0], 'NVCC numerical flags')
    program = out / Path(old_info['program']['path']).name
    result = dict(passed=False, configuration=config, base=identity(verify(old_info['program'])),
                  base_link_recipe=identity(old/'link.rsp'), actual_nvcc_recipe=identity(mslog),
                  source_receipt=identity(LOG/(PREFIX+'.source.json')), calls=[])
    try:
        compile_call = call([str(vs.NVCC), *flags, str(SRC/CUDA_TU)], SRC, env, folder/'nvcc.log')
        result['calls'].append(compile_call)
        need(compile_call['win32_exit'] == compile_call['popen_exit'] == 0 and obj.is_file(), 'CUDA compilation')
        link_flags = vs.b.windows_argv((old/'link.rsp').read_text(encoding='utf-16'))
        frozen = {verify(e).resolve() for e in old_info['retained_objects']}
        frozen.update(old/name for name in ('JSphGpu.obj','JSphGpuSingle.obj'))
        retained = []
        replaced = []
        for i, arg in enumerate(link_flags):
            key = arg.casefold()
            if key.startswith('/out:'):
                link_flags[i] = '/OUT:'+str(program)
            elif key.startswith(('/pdb:', '/implib:', '/ltcgout:', '/ilk:')):
                flag, path = arg.split(':', 1)
                link_flags[i] = flag+':'+str(folder / Path(path).name)
            elif not arg.startswith('/') and key.endswith('.obj'):
                path = Path(arg).resolve(strict=True)
                need(path in frozen, 'Unexpected link object '+arg)
                if path.name.casefold() == obj.name.casefold():
                    replaced.append(identity(path))
                    link_flags[i] = str(obj)
                else:
                    retained.append(identity(path))
        need(len(replaced) == 1 and len(retained) == len({p['path'] for p in retained}) == 110, 'Link closure')
        result.update(replaced_cuda_object=replaced[0], new_cuda_object=identity(obj), retained=retained)
        rsp = folder/'link.rsp'
        rsp.write_text(subprocess.list2cmdline(link_flags), encoding='utf-16')
        link_call = call([old_info['linker'], '@'+str(rsp)], folder, env, folder/'link.log')
        result['calls'].append(link_call)
        need(link_call['win32_exit'] == link_call['popen_exit'] == 0 and program.is_file(), 'GPU relink')
        for entry in old_info['runtime']:
            path = verify(entry)
            shutil.copy2(path, out/path.name)
            need(sha(path) == sha(out/path.name), 'Runtime copy '+path.name)
        result.update(passed=True, program=identity(program))
    finally:
        save(receipt, result)
    print(program, flush=True)


def short(profile):
    tag = PREFIX + '_' + profile
    config = PROGRAM_PROFILES[profile]
    old = load(LOG / ('cryer_p3_gpu_'+profile+'_r1.run.json'))
    build_result = load(LOG / (PREFIX+'_'+config+'.build.json'))
    exe = Path(build_result['program']['path'])
    need(build_result['passed'] and identity(exe)==build_result['program'] and old['passed'], 'Program binding')
    output = OUT/tag
    receipt = LOG/(tag+'.run.json')
    need(not output.exists() and not receipt.exists(), 'Existing short run')
    seed, bi4 = [verify(e) for e in old['inputs'][2:]]
    n = {'default128':128, 'b64':64, 'debug2':2}[profile]
    need(old['n']==n and seed.with_suffix('.bi4')==bi4, 'Seed or nsteps')
    solver = [str(exe), '-gpu', '-stable', str(seed.with_suffix('')), str(output), '-dirdataout','data','-svres',f'-nsteps:{n}']
    args = solver
    if profile=='debug2':
        args = [old['args'][0], '--tool','memcheck','--error-exitcode','88','--log-file',str(LOG/(tag+'.memcheck.log')),*solver]
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith('UPL_TPI_')}
    env.update(old['tpi_environment'])
    record = call(args, exe.parent, env, LOG/(tag+'.console.log'))
    record.update(passed=False, dt=old['dt'], n=n, program=identity(exe), inputs=[identity(seed),identity(bi4)],
                  tpi_environment=old['tpi_environment'])
    try:
        need(record['popen_exit']==record['win32_exit']==0, 'Solver exit')
        if profile=='debug2':
            need('ERROR SUMMARY: 0 errors' in (LOG/(tag+'.memcheck.log')).read_text(), 'CUDA memcheck')
        with (output/'Run.csv').open(encoding='utf-8-sig', newline='') as f:
            row, = csv.DictReader(f, delimiter=';')
        need(tuple(int(row[k]) for k in ('Steps','PartFiles','PartsOut','Np'))==(n,2,0,37181), 'Solver counters')
        record.update(passed=True, loop_s=float(row['TSimul']), device=row['Hardware'])
    finally:
        save(receipt, record)
    print(output, flush=True)


def check(profile):
    from cryer_p3_sidecar_review_r1 import inspect
    from cryer_p3_verify_r1 import audit, EXPECTED_TYPES
    tag = PREFIX+'_'+profile
    folder = OUT/tag
    reference = OUT/('cryer_p3_gpu_'+profile+'_r1')
    run = load(LOG/(tag+'.run.json'))
    need(run['passed'], 'Run receipt')
    use_p3 = profile!='default128'
    native = audit(folder/'data', [0,run['n']], run['dt'], reference/'data', exact=True, p3_sidecars=use_p3)
    stage_names = sorted(p.name for p in reference.glob('UplTpi*'))
    need([p.name for p in sorted(folder.glob('UplTpi*'))] == stage_names, 'Sidecar membership')
    equal = []
    for name in stage_names:
        digest = sha(folder/name)
        need(digest == sha(reference/name), 'Ledger changed: '+name)
        equal.append(dict(name=name, sha256=digest))
    result = dict(passed=True, program=run['program'], reference=str(reference), same_step_dt_s=run['dt'],
                  matched_native_fields=list(EXPECTED_TYPES), native_saves=native, byte_equal_sidecars=equal,
                  signed_dterror_bitwise_equal=True)
    if use_p3:
        result['sidecar_checks']=inspect(folder, run['n'])
    save(LOG/(tag+'.check.json'), result)
    print(tag, len(EXPECTED_TYPES), 'native fields and', len(equal),'sidecars matched',flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    cmds = ap.add_subparsers(dest='action', required=True)
    cmds.add_parser('prepare')
    cmds.add_parser('build').add_argument('config', choices=['Debug','Release'])
    for action in ('run','check'):
        cmds.add_parser(action).add_argument('profile', choices=PROGRAM_PROFILES)
    args = ap.parse_args()
    if args.action=='prepare':
        prepare()
    elif args.action=='build':
        build(args.config)
    elif args.action=='run':
        short(args.profile)
    else:
        check(args.profile)
