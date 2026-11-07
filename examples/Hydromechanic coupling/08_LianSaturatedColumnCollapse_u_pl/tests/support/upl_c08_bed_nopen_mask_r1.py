"""Pure saved-native statistics of bed normal/range eligibility; no solver or NoPen scratch replay."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import csv,json,struct
from collections import defaultdict
from pathlib import Path
import numpy as np
import upl_c08_wall_geometry_r1 as g

T=Path(__file__).resolve().parents[1];TAG='upl_c08_bed_nopen_mask_r1';N=T/'outputs/upl_c08_r4_partial_r1';P=T/'figures'/TAG

def write(path,rows):
    with path.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    outputs=[Path(str(P)+suffix) for suffix in ('_bed.csv','_groups.csv','_particles.csv','.json')]
    g.need(not any(p.exists() for p in outputs),'Fresh derived paths required')
    inputs=[Path(__file__),T/'support/upl_c08_wall_geometry_r1.py',N/'CfgInit_NormalsGhost.vtk',N/'typed22_layout.csv',N/'typed22.bin',N/'clocks.csv',N/'completion.json',T/'logs/upl_c08_r4_partial_r1.check.json',T/'figures/upl_c08_r4_wall_review_r1_contacts.csv']
    before=[g.stat(p) for p in inputs];done=json.loads(inputs[6].read_text(encoding='utf-8'));check=json.loads(inputs[7].read_text(encoding='utf-8'))
    g.need(done['passed'] and check['passed'] and check['original_saved_native_guards_passed'] and done['samples']==43,'Closed native43 required')
    B,norm,mk=g.normals_vtk(inputs[2]);bed=np.flatnonzero((np.arange(2060)<1800)&(mk==11)&(norm[:,2]>0)&(norm[:,0]==0)&(norm[:,1]==0))
    g.need(len(bed)==1545,'All1545 remaining actual bed IDs required')
    b=B[bed][:,[0,2]];nf=norm[bed][:,[0,2]].astype(np.float32);length=np.sqrt(np.float32(nf[:,0]*nf[:,0]+nf[:,1]*nf[:,1])).astype(np.float32)
    dp=np.float32(.04);radius=np.float32(np.float32(1.25)*dp);limit=np.float32(np.float32(1.75)*dp);eligible=(length>0)&(length<limit)
    unit=np.float32(nf/length[:,None]);bedrows=[];group=defaultdict(list)
    for k,wall in enumerate(bed):
        side='x_lt4' if b[k,0]<4 else 'x_gt4' if b[k,0]>4 else 'x_eq4'
        row=dict(native_id=int(wall),mk=int(mk[wall]),side=side,B_x_m=float(b[k,0]),B_z_m=float(b[k,1]),raw_normal_x_m=float(nf[k,0]),raw_normal_z_m=float(nf[k,1]),raw_normal_length_float_m=float(length[k]),plane_z_m=float(b[k,1]+float(nf[k,1])/2),norm_gate_eligible=bool(eligible[k]))
        bedrows.append(row);group[(side,float(b[k,1]),float(nf[k,1]),bool(eligible[k]))].append(k)
    groups=[]
    for (side,z,nz,gate),ix in sorted(group.items()):groups.append(dict(side=side,B_z_m=z,raw_normal_z_m=nz,norm_gate_eligible=gate,count=len(ix),x_min_m=float(b[ix,0].min()),x_max_m=float(b[ix,0].max())))
    write(outputs[0],bedrows);write(outputs[1],groups)
    layout=g.table(inputs[3]);g.need([(r['array'],r['type'],int(r['components'])) for r in layout]==g.SCHEMA,'Native22 layout differs')
    names=['time'];formats=['<f8'];offsets=[0];extent=8
    for name,kind,nc in g.SCHEMA:names.append(name);formats.append((g.TYPES[kind],(6800,nc)) if nc>1 else (g.TYPES[kind],(6800,)));offsets.append(extent);extent+=6800*g.TYPES[kind].itemsize*nc
    with inputs[4].open('rb') as f:g.need(struct.unpack('<III',f.read(12))==(6800,22,43),'Actual original header differs')
    raw=np.memmap(inputs[4],mode='r',offset=12,shape=(43,),dtype=np.dtype(dict(names=names,formats=formats,offsets=offsets,itemsize=extent)))
    contacts=g.table(inputs[8]);negative=[r for r in contacts if r['z_lt0']=='True'];first=min(int(r['part']) for r in negative);ids=sorted(int(r['native_id']) for r in negative if int(r['part'])==first)
    parts=(first-1,first,first+1);particle_rows=[]
    for part in parts:
        frame=raw[part]
        for native_id in ids:
            slots=np.flatnonzero(frame['Idp']==native_id);g.need(len(slots)==1,'Material ID missing');slot=int(slots[0]);xyz=np.asarray(frame['Posd'][slot]);v=np.asarray(frame['Vel'][slot]);xz=xyz[[0,2]]
            delta=xz-b;distance=np.linalg.norm(delta,axis=1);nearest=int(np.argmin(distance));allowed=np.flatnonzero(eligible);ne=int(allowed[np.argmin(distance[allowed])])
            d=delta.astype(np.float32);rrmag=np.sqrt(np.float32(d[:,0]*d[:,0]+d[:,1]*d[:,1]));normdist=np.float32(unit[:,0]*d[:,0]+unit[:,1]*d[:,1])
            range_gate=rrmag<radius;plane_gate=normdist<np.float32(np.float32(.75)*length)
            z_gate=(np.float32(d[:,1]*unit[:,1])<np.float32(.75))&(np.abs(unit[:,1])>np.float32(np.float32(.001)*dp))
            geometry_gate=eligible&range_gate&plane_gate&z_gate
            row=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-done['source_actual_time_s'],native_id=native_id,x_m=float(xyz[0]),z_m=float(xyz[2]),vx_m_s=float(v[0]),vz_m_s=float(v[2]),p_Pa=float(frame['PorePress'][slot]),kappa=float(frame['Kplastic'][slot]),J=float(frame['PoroVolumeRatio'][slot]),
                     native_displacement_pattern_geometry_eligible_bed_count=int(geometry_gate.sum()),native_vz_toward_wall=bool(v[2]<0),eligible_bed_IDs=';'.join(str(int(x)) for x in bed[geometry_gate]))
            for label,k in (('nearest_any_bed',nearest),('nearest_norm_eligible_bed',ne)):
                row.update({label+'_id':int(bed[k]),label+'_B_x_m':float(b[k,0]),label+'_B_z_m':float(b[k,1]),label+'_raw_normal_m':float(length[k]),label+'_norm_gate':bool(eligible[k]),label+'_distance_native_double_m':float(distance[k]),label+'_rrmag_native_float_pattern_m':float(rrmag[k]),label+'_range_gate':bool(range_gate[k]),label+'_dx_m':float(delta[k,0]),label+'_dz_m':float(delta[k,1]),label+'_normdist_m':float(normdist[k]),label+'_plane_gate':bool(plane_gate[k])})
            particle_rows.append(row)
    write(outputs[2],particle_rows);regions={}
    for side in ('x_lt4','x_eq4','x_gt4'):
        ix=[i for i,r in enumerate(bedrows) if r['side']==side];good=[i for i in ix if eligible[i]]
        regions[side]=dict(count=len(ix),norm_gate_count=len(good),B_x_min_m=float(b[ix,0].min()) if ix else None,B_x_max_m=float(b[ix,0].max()) if ix else None,
                           eligible_B_x_min_m=float(b[good,0].min()) if good else None,eligible_B_x_max_m=float(b[good,0].max()) if good else None)
    g.need(all(g.stat(e['path'])==e for e in before),'Sealed inputs changed')
    result=dict(stage=TAG,passed=True,consumed=before,outputs=[g.stat(p) for p in outputs[:3]],bed_IDs=len(bed),norm_gate_count=int(eligible.sum()),norm_gate_threshold_float_m=float(limit),range_threshold_float_m=float(radius),regions=regions,groups=groups,
                first_saved_z_lt0_part=first,first_saved_z_lt0_IDs=ids,observed_parts=list(parts),particle_rows=particle_rows,max_abs_inferred_plane_z_m=float(np.max(np.abs(b[:,1]+nf[:,1].astype(float)/2))),
                exact_runtime_GPU_packed_displacements_replayed=False,raw_normal_gate_static_and_velocity_independent=True,range_and_plane_checks_from_native_positions_not_force_substage=True,NoPen_scratch_not_exported=True,no_timelayer_direct_causality_claim=True,
                source_locations=['JSphGpu_ker.cu:1970-1991','JSphGpu_ker.cu:1674-1681'],solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,physical_acceptance=False)
    with outputs[3].open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(stage=TAG,bed_IDs=len(bed),norm_gate_count=int(eligible.sum()),regions=regions,first_saved_z_lt0_part=first,first_saved_z_lt0_IDs=ids,summary=str(outputs[3])),allow_nan=False))

if __name__=='__main__':main()
