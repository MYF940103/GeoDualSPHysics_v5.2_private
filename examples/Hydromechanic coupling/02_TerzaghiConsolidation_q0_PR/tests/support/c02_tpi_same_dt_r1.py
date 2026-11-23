"""Matched-dt TPI ablation at the first predeclared target, with a conditional full window."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from c02_tpi_cost_r1 import PLAN, PREFIX, TESTS, directory, need, planned_clock, prepare, run, setup_xml, xml_path
from c02_tpi_cost_review_r1 import FIELDS, SOIL, one, read_native, target_rows, write_report
from c02_tpi_cost_ref_review_r1 import against_reference
from c02_tpi_cost_summary_r1 import single
from c02_tpi_r_fixed4_r1 import fields_equal

TAG='c02_tpi_same_dt_r1'


def select_all():
    selection={}
    for side in ('gpu','cpu'):
        anchor=single('kw10',side)[0]
        alternate=single('kw125',side)[0]
        checked=against_reference(anchor,alternate,anchor)
        ref=alternate if checked['predeclared_target_noninferiority_pass'] and alternate['wall_s']<anchor['wall_s'] else anchor
        names=['tpi25','tpi40','tpi100']
        if directory('tpi625',side).exists():names.append('tpi625')
        qualified=[name for name in names if against_reference(ref,single(name,side)[0],anchor)['predeclared_target_noninferiority_pass']]
        need(not qualified,side+' already has an equally accurate TPI lane: '+','.join(qualified))
        selection[side]=(anchor,ref)
    return selection


def register(ref,window):
    lane=f'tpi_same_{ref}_{window}'
    cfg=dict(model=2,R=1.,dt_s=PLAN['lanes'][ref]['dt_s'])
    need(lane not in PLAN['lanes'] or PLAN['lanes'][lane]==cfg,'Lane name already used')
    PLAN['lanes'][lane]=cfg
    tree,n,event=setup_xml(lane)
    # Changing Model 2 back to 1 and removing R must restore the explicit input.
    hydro=tree.find('execution/special/hydromechanics')
    hydro.find('HydroMechModel').set('value','1')
    item=hydro.find('HydroMechTpiR')
    need(item is not None and float(item.get('value'))==1.,'R1 input')
    hydro.remove(item)
    equivalent=ET.canonicalize(ET.tostring(tree.getroot(),encoding='unicode'),strip_text=True)
    reference=ET.canonicalize(from_file=xml_path(ref),strip_text=True)
    need(equivalent==reference and planned_clock(lane)==planned_clock(ref),'Different physical input or save clock')
    need(len(planned_clock(lane))==13 and n==planned_clock(ref)[-1][0] and event==planned_clock(ref)[1][0],
         'Unexpected original plan')
    return lane


def report_path(side,ref,window):
    return TESTS/'logs'/f'{TAG}_{side}_{ref}_{window}.json'


def frame_stats(m,a,ref_result,part):
    _,rm,ra,_=read_native(ref_result/'data'/f'Part_{part:04}.bi4',part,1,1.)
    need(ra.keys()==FIELDS and all(rm[k]==m[k] for k in ('Step','TimeStep','Cpart','SymplecticDtPre','dtmin','dtmax','Nout','Npok')),
         'Actual same-dt clock or reference layout')
    order=np.argsort(ra['Idp'])
    need(np.array_equal(ra['Idp'][order],a['Idp']) and np.array_equal(a['Idp'],np.arange(1040)),
         'Different original material IDs')
    if part==0:fields_equal(ra,a,np.arange(1040))
    def delta(key):
        return a[key][40:].astype(float)-ra[key][order][40:].astype(float)
    dp=delta('PorePress')
    displacement=np.linalg.norm(1000*delta('Posd'),axis=1)
    return dict(part=part,t_s=m['TimeStep'],signed_timestep_s={'explicit':rm['dterror'],'tpi':m['dterror']},
                pressure_difference_RMS_Pa=float(np.sqrt(np.mean(dp**2))),max_abs_pressure_difference_Pa=float(max(abs(dp))),
                max_material_XYZ_displacement_difference_mm=float(max(displacement)),max_displacement_material_id=int(SOIL[np.argmax(displacement)]),
                max_abs_total_zz_difference_Pa=float(max(abs(delta('SigmaState_kk')[:,2]-dp))),
                max_abs_J_difference=float(max(abs(delta('PoroVolumeRatio')))),max_abs_porosity_difference=float(max(abs(delta('PoroPorosity')))))


def short_prefix(short_dir,part,m,a,h):
    _,sm,sa,sh=read_native(short_dir/'data'/f'Part_{part:04}.bi4',part,2,1.)
    for key in ('Step','TimeStep','Cpart','SymplecticDtPre','dtmin','dtmax','dterror','Nout','Npok'):
        need(np.asarray(m[key]).tobytes()==np.asarray(sm[key]).tobytes(),'Shared short prefix clock: '+key)
    fields_equal(sa,a,np.arange(1040))
    if part:
        need(h['types']==sh['types'] and h['array_types']==sh['array_types'],'Shared history field types')
        for key in h['types'].keys()-{'RunCode'}:
            need(np.asarray(h['values'][key]).tobytes()==np.asarray(sh['values'][key]).tobytes(),'Shared pressure history: '+key)
        fields_equal(h['arrays'],sh['arrays'],SOIL)


def passed_rows(rows):
    return all(r['pressure_ok'] and r['top_ok'] and r['bottom_ok'] for r in rows)


def profile(side,window):
    anchor,ref=select_all()[side]
    lane=register(ref['lane'],window)
    folder=directory(lane,side)
    if window=='full':
        src=report_path(side,ref['lane'],'first')
        need(src.is_file() and json.loads(src.read_text())['first_target_pass'],'Full window requires own accepted first target')
    dest=report_path(side,ref['lane'],window)
    need(not dest.exists(),'Existing review is preserved: '+str(dest))
    return anchor,ref,lane,folder,dest


def review(side,window):
    anchor,ref,lane,folder,dest=profile(side,window)
    reference=directory(ref['lane'],side)/'result'
    short=directory(register(ref['lane'],'first'),side)/'result' if window=='full' else None
    pairs=[]
    def compare(part,m,a,h):
        pairs.append(frame_stats(m,a,reference,part))
        if short and part<4:short_prefix(short,part,m,a,h)
    r=one(lane,side,frame_sink=compare,last_part=3 if window=='first' else None)
    need(all(r[k]==ref[k]==anchor[k] for k in ('backend','host','hardware','cuda_driver_runtime','program_identity')),
         'Different backend, hardware, program or host')
    primary=target_rows(ref,r,(3,))
    independent=target_rows(anchor,r,(3,))
    first_pass=passed_rows(primary) and passed_rows(independent)
    summary=dict(backend=side,window=window,explicit_reference=ref['lane'],independent_anchor=anchor['lane'],
                 dt_s=PLAN['lanes'][lane]['dt_s'],R=1.,first_target_pass=first_pass,
                 first_vs_same_dt=primary,first_vs_anchor=independent,elapsed_time_scope=('through first target only' if window=='first' else 'complete 13-frame window'),
                 post_point1s_guard_evaluated=r['early_100Pa_stress_pass'] is not None,matched_material_rows=pairs,
                 tpi=r,explicit_at_shared_saves=ref['rows'][:len(r['rows'])],anchor_at_corresponding_saves=anchor['rows'][:len(r['rows'])])
    if window=='full':
        summary['shared_short_prefix_frames']=4
        summary['full_accuracy']=against_reference(ref,r,anchor)
        if summary['full_accuracy']['predeclared_target_noninferiority_pass']:
            summary['equal_accuracy_wall_ratio_explicit_over_tpi']=ref['wall_s']/r['wall_s']
            summary['equal_accuracy_loop_ratio_explicit_over_tpi']=ref['loop_s']/r['loop_s']
    write_report(dest,summary)
    print(dest,first_pass,r['rows'][3]['pressure_RMS_Pa'],r['rows'][3]['top_error_mm'],r['wall_s'])


def launch(side,window):
    _,ref,lane,folder,_=profile(side,window)
    need(not folder.exists(),'Existing output/failed attempt is preserved')
    oldseed=directory(ref['lane'],side)/'seed'
    for ext in ('.bi4','_Normals.nbi4'):
        name=PLAN['seed_name']+ext
        need((TESTS/PLAN['seed_directory']/name).read_bytes()==(oldseed/name).read_bytes(),'Different original seed '+name)
    identity=ref['program_identity']
    exe=Path(identity['program'])
    info=exe.stat()
    need(info.st_size==identity['size'] and info.st_mtime_ns==identity['mtime_ns'],'Reference executable changed')
    prepare(lane)
    run(lane,side,exe_override=exe,last_part=3 if window=='first' else None)
    review(side,window)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('plans','run','review'))
    parser.add_argument('backend',choices=('cpu','gpu'),nargs='?')
    parser.add_argument('window',choices=('first','full'),nargs='?')
    args=parser.parse_args()
    if args.action=='plans':
        for ref in ('kw10','kw125'):
            for window in ('first','full'):
                lane=register(ref,window)
                print(lane,planned_clock(lane)[3 if window=='first' else -1])
    else:
        if not args.backend or not args.window:parser.error('run and review require backend and window')
        (launch if args.action=='run' else review)(args.backend,args.window)

