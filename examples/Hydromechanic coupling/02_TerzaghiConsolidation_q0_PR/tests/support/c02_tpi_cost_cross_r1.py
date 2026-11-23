"""Compare a single high-k lane on CPU/GPU at its 13 actual clocks, without starting a solver."""
import argparse

import numpy as np

from c02_tpi_cost_r1 import PLAN, PREFIX, TESTS, directory, need, planned_clock
from c02_tpi_cost_review_r1 import FIELDS, SOIL, one, write_report


def differences(cpu,gpu,ids):
    """CPU/GPU row order is fixed by material ID. Components retain their native order."""
    need(cpu.shape==gpu.shape and cpu.dtype==gpu.dtype and len(cpu)==len(ids),'Mismatched native array type or shape')
    delta=gpu.astype(np.float64)-cpu.astype(np.float64)
    need(np.isfinite(delta).all(),'Nonfinite field difference')
    columns=delta.reshape(len(ids),-1)
    loc=np.argmax(np.abs(columns),axis=0)
    rms=np.sqrt(np.mean(columns*columns,axis=0))
    return dict(component_RMS=rms.tolist(),component_max_abs=np.abs(columns[loc,np.arange(len(loc))]).tolist(),
                component_max_at_id=ids[loc].tolist(),numerically_different_ids=int(np.any(columns!=0,axis=1).sum()),
                bit_identical=cpu.tobytes()==gpu.tobytes())


def paired_frame(part,cpu,gpu):
    mc,a,hc=cpu
    mg,b,hg=gpu
    for key in ('Cpart','Step','TimeStep','SymplecticDtPre','dtmin','dtmax'):
        need(np.asarray(mc[key]).tobytes()==np.asarray(mg[key]).tobytes(),'Cross-backend clock '+key)
    need(mc['Cpart']==part and a.keys()==b.keys()==FIELDS,'Cross native layout')
    allids=np.arange(1040)
    need(np.array_equal(a['Idp'],allids) and np.array_equal(b['Idp'],allids),'Cross-backend IDs')
    if part==0:
        need(np.array_equal(a['Posd'],b['Posd']),'Different original material reference coordinates')
    stats={}
    for key in sorted(FIELDS):
        stats[key]=dict(soil=differences(a[key][40:],b[key][40:],SOIL),
                        fixed=differences(a[key][:40],b[key][:40],allids[:40]))
    # Same original coordinates and material identity allow the position difference
    # to be used directly as the difference in total material displacement.
    delta=1000*(b['Posd'][40:]-a['Posd'][40:])
    distance=np.linalg.norm(delta,axis=1)
    far=int(np.argmax(distance))
    effective_a=np.column_stack((a['SigmaState_kk'][40:],a['SigmaState_ij'][40:]))
    effective_b=np.column_stack((b['SigmaState_kk'][40:],b['SigmaState_ij'][40:]))
    effective=differences(effective_a,effective_b,SOIL)
    effective_a[:,:3]-=a['PorePress'][40:,None]
    effective_b[:,:3]-=b['PorePress'][40:,None]
    total=differences(effective_a,effective_b,SOIL)
    previous=None
    need((hc is None)==(hg is None),'Cross pressure-history presence')
    if hc is not None:
        for key in ('Schema','Scheme','Valid','CompletedUpdates','PreviousTime','SavedTime','Dt'):
            need(hc['values'][key]==hg['values'][key],'Cross TPI history '+key)
        need(np.array_equal(hc['arrays']['Idp'],SOIL) and np.array_equal(hg['arrays']['Idp'],SOIL),'Cross TPI history IDs')
        previous=differences(hc['arrays']['PorePressPrev'],hg['arrays']['PorePressPrev'],SOIL)
    return dict(part=part,completed_step=(mc['Step']+1 if part else 0),t_s=mc['TimeStep'],
                signed_dterror_s={'cpu':mc['dterror'],'gpu':mg['dterror']},
                material_pressure_RMS_Pa=stats['PorePress']['soil']['component_RMS'][0],
                material_max_displacement_diff_mm=float(distance[far]),max_displacement_id=int(SOIL[far]),
                signed_displacement_difference_mm_at_that_id=delta[far].tolist(),
                effective_stress_Pa=effective,total_stress_Pa=total,previous_pressure_Pa=previous,fields=stats)


def observed_max(rows,key):
    row=max(rows,key=lambda r:r[key])
    return dict(value=row[key],part=row['part'],t_s=row['t_s'])


def compare(lane):
    cpu_saved={}
    def collect_cpu(part,meta,arrays,hist):
        cpu_saved[part]=(meta,arrays,hist)
    rows=[]
    def compare_gpu(part,meta,arrays,hist):
        rows.append(paired_frame(part,cpu_saved.pop(part),(meta,arrays,hist)))
    cpu=one(lane,'cpu',frame_sink=collect_cpu)
    gpu=one(lane,'gpu',frame_sink=compare_gpu)
    need(not cpu_saved and len(rows)==13,'All 13 backend pairs required')
    need(cpu['host']==gpu['host'],'Cross comparison was planned on one host')
    for row,(step,t,_) in zip(rows,planned_clock(lane)):
        need(row['completed_step']==step and row['t_s']==t,'Cross pair differs from scalar launch plan')
    max_p=observed_max(rows,'material_pressure_RMS_Pa')
    max_u=observed_max(rows,'material_max_displacement_diff_mm')
    max_u['material_id']=rows[max_u['part']]['max_displacement_id']
    return dict(lane=lane,configuration=PLAN['lanes'][lane],host=cpu['host'],native_pairs=len(rows),
                soil_count=1000,fixed_count=40,fields_per_native_frame=len(FIELDS),all_pair_clocks_exact=True,
                source_dirs={b:str(directory(lane,b)) for b in ('cpu','gpu')},
                hardware={b:s['hardware'] for b,s in [('cpu',cpu),('gpu',gpu)]},
                program_identities={b:s['program_identity'] for b,s in [('cpu',cpu),('gpu',gpu)]},
                stress_component_order=['xx','yy','zz','xy','yz','xz'],signed_differences='GPU minus CPU',
                backend_pressure_RMS_limit_Pa=5.,backend_displacement_limit_mm=.005,
                max_material_pressure_RMS_Pa=max_p,max_material_displacement_diff_mm=max_u,
                cross_backend_field_gate_pass=max_p['value']<=5. and max_u['value']<=.005,
                per_backend_saved_stress_safety={b:s['early_100Pa_stress_pass'] for b,s in [('cpu',cpu),('gpu',gpu)]},
                independent_model_accuracy='See same-backend model comparison at Tv=.005 and .05.',
                rows=rows)


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('lane',choices=PLAN['lanes'])
    args=cli.parse_args()
    dest=TESTS/'logs'/(PREFIX+'_'+args.lane+'_cpu_gpu.json')
    need(not dest.exists(),'Existing comparison is preserved: '+str(dest))
    for backend in ('cpu','gpu'):
        need((directory(args.lane,backend)/'exit.json').is_file(),'Missing completed '+backend+'; no files written')
    result=compare(args.lane)
    write_report(dest,result)
    print(dest)
