"""Decode real replay exception inputs; independently re-evaluate, never invent GPU registers."""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_key, '1')
import argparse
import csv
import json
import math
import re
import struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import c08_h18_hg_wall_saved_proxy_r1 as proxy

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_hg_wall_fault_review_r1'
JOB = 'c08_h18_hg_wall_host_replay_GPU_r1'
NOTE = T / 'notes' / (TAG + '.md')
CHECK = T / 'logs' / (TAG + '.check.json')
PREFIX = T / 'figures' / TAG
need, read, stat, bind = proxy.need, proxy.read, proxy.stat, proxy.bind
f32 = np.float32
VECTOR = lambda names: [('{}17'.format(v), '{}_hex'.format(v)) for v in names]
MATRIX = [('a{}_17'.format(v), 'a{}_hex'.format(v)) for v in ('11','12','13','21','22','23','31','32','33')]
# Integers are exact decimal words; floating primary identity is IEEE integer hex bits.
SPECS = {
    'Idp': ('uint32', '<u4', 1, ['value']),
    'Code': (None, None, 1, ['value']),
    'Posxy': ('float64x2', '<f8', 2, VECTOR('xy')),
    'Posz': ('float64', '<f8', 1, [('value17','hex_bits')]),
    'PosCell': ('float32x4_raw_w_cell_bits', '<f4', 4, VECTOR('xyzw')),
    'Dcell': ('uint32', '<u4', 1, ['value']),
    'PoroJ': ('float64', '<f8', 1, [('value17','hex_bits')]),
    'CorrMat': ('float64x9_actual_input', '<f8', 9, MATRIX),
    'BoundNormal': ('float32x3', '<f4', 3, VECTOR('xyz')),
    'BoundMode': ('uint8', '<u1', 1, ['value']),
    'FluidCells': ('int32x2', '<i4', 2, ['begin_sorted_slot','end_sorted_slot_exclusive']),
}


def bits(value, width):
    return struct.pack('<f' if width == 4 else '<d', float(value))


def ieee(value, width):
    need(isinstance(value, str) and re.fullmatch('[0-9a-fA-F]{%d}' % (2 * width), value) is not None,
         'Exact IEEE integer-word hex width differs')
    return struct.unpack('<f' if width == 4 else '<d', int(value, 16).to_bytes(width, 'little'))[0]


def plain(value):
    if isinstance(value, dict): return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)): return [plain(v) for v in value]
    if isinstance(value, np.generic): return plain(value.item())
    if isinstance(value, float) and not math.isfinite(value): return repr(value)
    return value


def csv_write(path, rows, empty_fields=None):
    need(rows or empty_fields, 'No diagnostic rows/schema')
    with path.open('x', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]) if rows else empty_fields); w.writeheader(); w.writerows(rows)


def decode_array(root, entry, spec, expected_count, typecode_bytes):
    name=entry['array']; declared,kind,width,columns=spec
    if name=='Code':
        kind='<u2' if typecode_bytes==2 else '<u4';declared='uint16' if typecode_bytes==2 else 'uint32'
    dtype=np.dtype(kind); floating=dtype.kind=='f'
    need(entry['dtype']==declared and entry['count']==expected_count
         and entry['element_bytes']==dtype.itemsize*width
         and entry['allocated'] and entry['copied'] and entry['written']
         and entry['cudaMemcpy_status']==0 and not entry['error'], 'Incomplete/incorrect actual copy: '+name)
    leaf=root/entry['file'];need(leaf.resolve()==(root/(name+'.csv')).resolve(), 'Capture leaf must be its actual closed array name')
    index='fluid_table_index' if name=='FluidCells' else 'sorted_slot'
    header=[index]+([v for pair in columns for v in pair] if floating else columns)
    raw=bytearray();decimal_compared=nonfinite_decimal_class_only=0
    with leaf.open(encoding='utf-8-sig', newline='') as f:
        reader=csv.DictReader(f);need(reader.fieldnames==header, 'Actual CSV header differs: '+name)
        rows=0
        for rows,row in enumerate(reader,1):
            need(rows<=expected_count and int(row[index])==rows-1 and None not in row, 'Actual row/index/count differs: '+name)
            for column in columns:
                if floating:
                    dec,hx=column;value=ieee(row[hx],dtype.itemsize)
                    raw.extend(int(row[hx],16).to_bytes(dtype.itemsize,'little'))
                    reported=float(row[dec])
                    if math.isfinite(value):
                        need(bits(reported,dtype.itemsize)==bits(value,dtype.itemsize), 'Decimal/raw floating mismatch: '+name)
                        decimal_compared+=1
                    else:
                        need((math.isnan(value) and math.isnan(reported)) or value==reported, 'Nonfinite decimal/raw class mismatch: '+name)
                        nonfinite_decimal_class_only+=1
                else:
                    value=int(row[column]);lim=np.iinfo(dtype)
                    need(lim.min<=value<=lim.max, 'Actual integer word outside dtype: '+name)
                    raw.extend(value.to_bytes(dtype.itemsize,'little',signed=dtype.kind=='i'))
        need(rows==expected_count, 'Truncated actual array: '+name)
    a=np.frombuffer(bytes(raw),dtype=dtype).reshape(expected_count,width)
    return a,dict(array=name,dtype=declared,count=expected_count,element_bytes=entry['element_bytes'],
        decoded_bytes=len(raw),decimal_raw_finite_comparisons=decimal_compared,
        nonfinite_decimal_class_only=nonfinite_decimal_class_only,raw_bits_primary=floating,
        exact_integer_decimal_words=not floating,finite_physical_acceptance_claimed=False),stat(leaf)


def inputs(consumed):
    rp=T/'logs'/(JOB+'.run.json');run=read(rp);consumed.append(stat(rp))
    need(not run['passed'] and not run['solver_completed'] and run['actual_exit']==run['actual_Win32_exit']==1
         and run['ownership_failure'] is None and run['solver_identity_matches'], 'Genuine failed replay only; no success promotion')
    bind(run['actual_call']);consumed.append(run['actual_call']);call=read(run['actual_call']['path'])
    need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==1 and call['ownership_failure'] is None
         and call['child']==run['solver_identity'], 'Actual failed owned native handle proof differs')
    for key in ('program','source_build','source_capture','input_xml','planned_steps'):
        bind(run[key]);consumed.append(run[key])
    root=Path(run['output'])/'WallFaultCaptureHostR1';sp=root/'schema.json';schema=read(sp);consumed.append(stat(sp))
    need(schema['schema']==1 and schema['policy']=='HostExceptionOnlyWallInputs' and schema['capture_complete']
         and not schema['capture_error'] and schema['scope']=='actual_replay_aborted_substage_inputs'
         and not schema['committed_native'] and not schema['original_old_unsaved_fault_recovered']
         and not schema['actual_failed_M_or_fitted_C_registers_captured']
         and schema['CorrMat_is_input_array_not_rejected_fitted_wall_value']
         and schema['invalid_slot_CorrMat_may_be_unwritten_or_stale']
         and schema['array_order']=='actual_sorted_slot' and schema['PosCell_w_hex_required']
         and schema['host_constants_mapping_not_direct_GPU_CTE_snapshot']
         and Path(schema['directory']).resolve()==root.resolve(), 'Real complete host-exception packet schema differs')
    n,npb,nb=map(int,(schema['np'],schema['npb'],schema['npbok']));need(n==6805 and npb==1805 and 0<nb<=npb,'Closed C08 active/fixed extents differ')
    need(schema['stage']==1 and schema['field_set_complete_for_stage1_input_review_only']
         and schema['kernel']==2 and schema['simulate2d']==1 and schema['periactive']==0,
         'Only the actual nonperiodic2D Wendland stage1 packet is admitted')
    size=schema['sizeof'];need(size['unsigned']==size['float']==4 and size['double']==8
         and size['typecode'] in (2,4) and size['double2']==16 and size['float4']==16
         and size['float3']==12 and size['byte']==1 and size['int2']==8 and size['tmatrix3d']==72,'Actual ABI sizes differ')
    meta={};parameter_bits={}
    for q in schema['floating_host_parameters']:
        need(q['name'] not in meta and q['bytes'] in (4,8),'Ambiguous floating host parameter')
        v=ieee(q['hex_bits'],q['bytes']);need(math.isfinite(v) and bits(float(q['value17']),q['bytes'])==bits(v,q['bytes']),'Invalid floating host parameter')
        meta[q['name']]=v;parameter_bits[q['name']]=q['hex_bits']
    for a,b in [('Scell','DivData.scell'),('KernelSize2','DivData.kernelsize2'),('PosCellSize','DivData.poscellsize'),
                ('DomPosMin.x','DivData.domposmin.x'),('DomPosMin.y','DivData.domposmin.y'),('DomPosMin.z','DivData.domposmin.z')]:
        need(parameter_bits[a]==parameter_bits[b],'Host/DivData constant mapping differs: '+a)
    d=schema['DivData'];nx,ny,nz,nw=map(int,d['nc']);nct=nx*ny*nz
    need(d['axis']==schema['host_upload_axis']==3 and d['scelldiv'] in (1,2)
         and min(nx,ny,nz)>0 and nw==nx*ny and d['ncells']==[nx,ny,nz]
         and d['logical_Nct']==d['table_entry_count']==nct and d['cellfluid']==nct+1
         and d['fluid_table_copy_validated'] and d['table_start_offset']==d['cellfluid']
         and not d['special_or_bound_tables_copied'], 'Actual logical fluid table closure differs')
    copies={q['array']:q for q in schema['copies']};need(len(copies)==11 and set(copies)==set(SPECS),'Exactly eleven real copies required')
    arrays={};audit=[]
    for name,spec in SPECS.items():
        count=nct if name=='FluidCells' else nb if name in ('BoundNormal','BoundMode') else n
        arrays[name],q,leaf=decode_array(root,copies[name],spec,count,size['typecode']);audit.append(q);consumed.append(leaf)
    ids=arrays['Idp'][:,0];expected=np.r_[np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)]
    need(np.array_equal(np.sort(ids),expected),'Real full sorted-ID population differs; arrays must not be reordered')
    dtype_mask=0x1800 if size['typecode']==2 else 0x30000;fluid_type=dtype_mask
    code=arrays['Code'][:,0].astype(np.uint32);fluid=(code&dtype_mask)==fluid_type;fixed=(code&dtype_mask)==0
    need(np.all(fixed[:nb]) and np.count_nonzero(fluid)==5000,'Actual receiver prefix/code type scope differs')
    target=int(schema['invalid_sorted_slot']);need(0<=target<nb,'Actual selected aggregate invalid slot out of captured wall prefix')
    table=arrays['FluidCells'];nonempty=table[:,1]!=0
    need(np.all(table[nonempty,0]>=0) and np.all(table[nonempty,0]<=table[nonempty,1]) and np.all(table[nonempty,1]<=n),
         'Consumed nonempty cell ranges outside actual sorted arrays')
    need(schema['Nstep_reported_uint32']==(int(schema['Nstep_actual_uint64'])&0xffffffff),'Actual host step uint32 mapping differs')
    c=dict(h=f32(meta['KernelH']),awen=f32(meta['KWend.awen']),bwen=f32(meta['KWend.bwen']),
        radius2=f32(meta['KernelSize2']),volume0=meta['MassFluid']/meta['RhopZero'],solid0=meta['actual_solid0_argument'],
        threshold=meta['MdbcThreshold'],scell=meta['Scell'],dom=np.array([meta['DomPosMin.'+a] for a in 'xyz']),
        poscellsize=f32(meta['PosCellSize']),nc=[nx,ny,nz,nw],cellzero=list(map(int,d['cellzero'])),scelldiv=int(d['scelldiv']))
    need(c['h']>0 and c['radius2']>0 and c['volume0']>0 and c['scell']>0,'Host geometry constants are not admissible')
    return run,schema,meta,arrays,fluid,fixed,target,c,audit


def ranges(point,c,table):
    # JCellSearch_iker::InitCte(double position); C++ int is truncation, not floor.
    p=[int((float(point[k])-float(c['dom'][k]))/c['scell'])-c['cellzero'][k] for k in range(3)]
    nx,ny,nz,nw=c['nc'];s=c['scelldiv']
    lo=[p[k]-min(p[k],s) for k in range(3)]
    hi=[p[k]+min(c['nc'][k]-p[k]-1,s)+1 for k in range(3)]
    visits=[]
    for c3 in range(lo[2]*nw,hi[2]*nw,nw):
        for c2 in range(lo[1]*nx,hi[1]*nx,nx):
            start=end=0
            for c1 in range(lo[0],hi[0]):
                index=c1+c2+c3;need(0<=index<len(table),'Actual-source query would leave captured logical fluid table')
                a,b=map(int,table[index])
                if b:
                    if not end:start=a
                    end=b
            if end:
                need(0<=start<=end,'Invalid ParticleRange aggregation')
                visits.extend(range(start,end))
    return visits,dict(query_cells_xyz=p,cell_limits_low=lo,cell_limits_high_exclusive=hi)


def det3(a):
    return (((((a[0,0]*a[1,1]*a[2,2]+a[0,1]*a[1,2]*a[2,0])+a[0,2]*a[1,0]*a[2,1])
        -a[2,0]*a[1,1]*a[0,2])-a[2,1]*a[1,2]*a[0,0])-a[2,2]*a[1,0]*a[0,1])


def inverse3(a,d):
    return np.array([[(a[1,1]*a[2,2]-a[1,2]*a[2,1]),-(a[0,1]*a[2,2]-a[0,2]*a[2,1]),(a[0,1]*a[1,2]-a[0,2]*a[1,1])],
        [-(a[1,0]*a[2,2]-a[1,2]*a[2,0]),(a[0,0]*a[2,2]-a[0,2]*a[2,0]),-(a[0,0]*a[1,2]-a[0,2]*a[1,0])],
        [(a[1,0]*a[2,1]-a[1,1]*a[2,0]),-(a[0,0]*a[2,1]-a[0,1]*a[2,0]),(a[0,0]*a[1,1]-a[0,1]*a[1,0])]],dtype=float)/d


def direction(a):
    """Symmetric-part direction is diagnostic; never alter the consumed matrix."""
    if not np.all(np.isfinite(a)):return (None,None,None,None,None)
    values,vectors=np.linalg.eigh(.5*(a+a.T));v=vectors[:,0]
    if v[0]<0 or (v[0]==0 and v[1]<0):v=-v
    return float(v[0]),float(v[1]),float(math.atan2(v[1],v[0])),float(values[1]-values[0]),bool(values[1]!=values[0])


def participation(a,fluid,target,c):
    xyz=np.c_[a['Posxy'],a['Posz'][:,0]];pc=a['PosCell'];words=pc.view('<u4')[:,3]
    packed=np.c_[words>>19,(words&0x0007fe00)>>9,words&0x1ff].astype(np.int64)
    visits,_=ranges(xyz[target],c,a['FluidCells']);double_min=fs_min=force_min=math.inf;counts=[0,0,0]
    for slot in visits:
        if not fluid[slot]:continue
        d=xyz[target]-xyz[slot];rd=float(d[0]*d[0]+d[2]*d[2])
        local=(pc[target,:3]-pc[slot,:3]).astype(np.float32)
        dr=(local+c['poscellsize']*(packed[target]-packed[slot]).astype(np.float32)).astype(np.float32)
        rf=f32(dr[0]*dr[0]+dr[2]*dr[2]);r3=f32(f32(dr[0]*dr[0]+dr[1]*dr[1])+dr[2]*dr[2])
        double_min=min(double_min,rd);fs_min=min(fs_min,float(rf));force_min=min(force_min,float(r3))
        for k,r in enumerate((rd,float(rf),float(r3))):counts[k]+=int(r<=float(c['radius2']) and r>=float(f32(1e-18)))
    return dict(actual_captured_mode=int(a['BoundMode'][target,0]),recomputed_double_B_support=counts[0],
        recomputed_PosCell_xz_support=counts[1],recomputed_PosCell_xyz_support=counts[2],
        recomputed_union_active=any(counts),min_double_xz_r2=double_min,min_PosCell_xz_r2=fs_min,min_PosCell_xyz_r2=force_min,
        exact_GPU_activation_reproduced=False,poscell_masks='frozen default PSCEL_CONFIG_13_10_9',device_masks_captured=False)


def recompute(a,fluid,target,c):
    ids=a['Idp'][:,0];xyz=np.c_[a['Posxy'],a['Posz'][:,0]];B=xyz[target].copy();bn=a['BoundNormal'][target].astype(float)
    need(np.all(np.isfinite(B)) and np.all(np.isfinite(bn)),'Selected receiver coordinate/normal nonfinite; preserve packet without invented fit')
    r2=float(sum(float(v)*float(v) for v in bn));need(r2>0,'Selected receiver zero normal; no mirror reconstruction invented')
    Q=np.where(bn*bn>.5*r2,-1.,1.);origin=B+bn;G=origin.copy();shift=np.zeros(3);attempts=[];donors=[]
    if int(a['BoundMode'][target,0])==2:
        return [],[],dict(status='captured_selected_mode_OFF_source_would_return',actual_branch_confirmed=False)
    for attempt in (0,1):
        M=np.zeros((3,3));s=np.zeros(9);gx=np.zeros(9);gz=np.zeros(9);sumw=submerged=0.;near2=float(np.finfo(float).max)
        near=near_k=None;nearx=nearz=0.;nearest=np.zeros(9);local=[];candidate='';bad_J=None;visits,search=ranges(G,c,a['FluidCells'])
        for order,slot in enumerate(visits):
            if not fluid[slot]:continue
            dx=float(G[0]-xyz[slot,0]);dz=float(G[2]-xyz[slot,2]);rr2=f32(dx*dx+dz*dz)
            if not rr2<=c['radius2']:continue  # Preserve actual support/order; do not replace by a tree or ID sort.
            J=float(a['PoroJ'][slot,0])
            if not math.isfinite(J) or J<=c['solid0']:
                candidate='independent_invalid_donor_J';bad_J=(slot,int(ids[slot]),J);break
            wab,fac=proxy.kernel(np.array([rr2],dtype=np.float32),c,True);W,F=float(wab[0]),float(fac[0])
            fx,fz=F*dx,F*dz;volume=c['volume0']*J;w,vx,vz=W*volume,fx*volume,fz*volume
            field=a['CorrMat'][slot].astype(float);distance=dx*dx+dz*dz;nearer=distance<near2
            for k in range(9):
                s[k]=s[k]+w*field[k];gx[k]=gx[k]+vx*field[k];gz[k]=gz[k]+vz*field[k]
                if nearer:nearest[k]=field[k]
            if nearer:near2=distance;near=slot;near_k=len(local);nearx=dx;nearz=dz
            sumw+=w;submerged-=volume*(dx*fx+dz*fz)
            M[0,0]+=w;M[0,1]+=dx*w;M[0,2]+=dz*w;M[1,0]+=vx;M[1,1]+=dx*vx;M[1,2]+=dz*vx;M[2,0]+=vz;M[2,1]+=dx*vz;M[2,2]+=dz*vz
            metric=proxy.matrix_metrics(field.reshape(3,3)[np.ix_([0,2],[0,2])])
            local.append(dict(slot=slot,order=order,dx=dx,dz=dz,rr2=float(rr2),J=J,W=W,F=F,volume=volume,w=w,vx=vx,vz=vz,field=field,metric=metric))
        det=float(det3(M));active=submerged>0 or sumw>=c['threshold'] or (c['threshold']>=2 and sumw+2>=c['threshold'])
        geometry=active and sumw>0 and math.isfinite(det) and abs(det)>=.001
        complete=not candidate;nearfinite=near is not None and math.isfinite(near2) and near2<float(np.finfo(float).max) and np.all(np.isfinite(nearest))
        values=np.full(9,np.nan);alpha=np.full(len(local),np.nan);wall=np.full((3,3),np.nan);metric=dict(det=None,sym_defect=None,sym_eig_min=None,sym_eig_max=None)
        if complete and geometry:
            inv=inverse3(M,det)
            for k in range(9):
                qx=(inv[1,0]*s[k]+inv[1,1]*gx[k])+inv[1,2]*gz[k]
                qz=(inv[2,0]*s[k]+inv[2,1]*gx[k])+inv[2,2]*gz[k]
                values[k]=(nearest[k]-qx*nearx)-qz*nearz
                if attempt:values[k]+=(qx*shift[0]+qz*shift[2])
            if not np.all(np.isfinite(values)):candidate='independent_nonfinite_fitted_component'
            else:
                wall=Q[:,None]*values.reshape(3,3)*Q[None,:];metric=proxy.matrix_metrics(wall[np.ix_([0,2],[0,2])])
                candidate='independent_Cdet_nonpositive_or_nonfinite' if metric['det'] is None or metric['det']<=0 else 'independent_original_C_gate_accepts'
            for k,d in enumerate(local):
                ax=(inv[1,0]*d['w']+inv[1,1]*d['vx'])+inv[1,2]*d['vz']
                az=(inv[2,0]*d['w']+inv[2,1]*d['vx'])+inv[2,2]*d['vz']
                alpha[k]=(1. if k==near_k else 0.)+(shift[0]-nearx)*ax+(shift[2]-nearz)*az
        elif complete:candidate='independent_geometry_rejection'
        row=dict(attempt=attempt,host_input_wall_slot=target,host_input_wall_id=int(ids[target]),Gx=float(G[0]),Gy=float(G[1]),Gz=float(G[2]),
            shiftx=float(shift[0]),shiftz=float(shift[2]),visited_sorted_slots=len(visits),consumed_fluid_donors=len(local),
            complete_geometry_accumulation=complete,sumW=sumw,submerged=submerged,independent_M_det=det,
            original_geometry_gate_margin=abs(det)-.001,independent_geometry_accepts=bool(geometry) if complete else None,
            nearest_slot=near,nearest_native_id=None if near is None else int(ids[near]),nearest_distance2=near2,
            first_invalid_J_slot=None if bad_J is None else bad_J[0],first_invalid_J_native_id=None if bad_J is None else bad_J[1],
            first_invalid_J_value=None if bad_J is None else bad_J[2],
            independent_C_det=metric['det'],independent_C_sym_eig_min=metric['sym_eig_min'],independent_C_sym_eig_max=metric['sym_eig_max'],
            independent_C_sym_defect=metric['sym_defect'],negative_alpha_count=None if not (complete and geometry) else int(np.count_nonzero(alpha<0)),
            alpha_L1=None if not (complete and geometry) else float(np.sum(abs(alpha))),alpha_sum=None if not (complete and geometry) else float(np.sum(alpha)),
            candidate_reason=candidate,actual_GPU_reason_confirmed=False,intermediates_are_independent=True)
        dx,dz,angle,gap,unique=direction(wall[np.ix_([0,2],[0,2])])
        row.update(independent_C_min_eigvec_x=dx,independent_C_min_eigvec_z=dz,independent_C_min_eigvec_angle_rad=angle,
            independent_C_symmetric_eigenvalue_gap=gap,independent_C_direction_numerically_unique=unique)
        for i,v in enumerate(M.reshape(9)):row['independent_M'+str(i)]=float(v)
        for i,v in enumerate(wall.reshape(9)):row['independent_Cwall'+str(i)]=float(v)
        attempts.append(row)
        for k,d in enumerate(local):
            metric=d['metric'];item=dict(attempt=attempt,traversal_order=d['order'],actual_sorted_slot=d['slot'],actual_native_id=int(ids[d['slot']]),
                actual_x=float(xyz[d['slot'],0]),actual_y=float(xyz[d['slot'],1]),actual_z=float(xyz[d['slot'],2]),actual_J=d['J'],
                independent_dx=d['dx'],independent_dz=d['dz'],independent_rr2_float=d['rr2'],independent_W=d['W'],independent_fac=d['F'],
                independent_volume=d['volume'],independent_WV=d['w'],independent_alpha=None if not (complete and geometry) else float(alpha[k]),
                actual_input_C_xz_det=metric['det'],actual_input_C_xz_sym_eig_min=metric['sym_eig_min'],actual_input_C_xz_sym_eig_max=metric['sym_eig_max'],
                actual_input_C_xz_sym_defect=metric['sym_defect'],input_is_captured_not_inferred=True,weight_is_independently_recomputed=True)
            dx,dz,angle,gap,unique=direction(d['field'].reshape(3,3)[np.ix_([0,2],[0,2])])
            item.update(input_C_min_eigvec_x=dx,input_C_min_eigvec_z=dz,input_C_min_eigvec_angle_rad=angle,
                input_C_symmetric_eigenvalue_gap=gap,input_C_direction_numerically_unique=unique)
            for i,v in enumerate(d['field']):item['actual_input_C'+str(i)]=float(v)
            donors.append(item)
        # Original implementation retries ONLY failed geometry, not a rejected matrix.
        if complete and not geometry and not attempt and nearfinite and (nearx!=0 or nearz!=0):
            G[0]-=nearx;G[2]-=nearz;shift[0]-=nearx;shift[2]-=nearz
        else:break
    return attempts,donors,dict(status='independent_source_order_recomputation_complete',actual_branch_confirmed=False,
        original_mirror_point=origin.tolist(),actual_target_C_input_raw_hex=[format(int(v),'016x') for v in a['CorrMat'][target].view('<u8')],
        target_C_input_is_not_rejected_fit=True)


def plot(attempts,donors,arrays,fluid,target,meta):
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained');xyz=np.c_[arrays['Posxy'],arrays['Posz'][:,0]];B=xyz[target]
    near=fluid & np.all(np.isfinite(xyz),axis=1) & (abs(xyz[:,0]-B[0])<.4) & (abs(xyz[:,2]-B[2])<.4)
    axes[0,0].scatter(xyz[near,0],xyz[near,2],c='.75',s=12,label='Captured fluid inputs')
    for attempt in sorted({v['attempt'] for v in donors}):
        r=[v for v in donors if v['attempt']==attempt];axes[0,0].scatter([v['actual_x'] for v in r],[v['actual_z'] for v in r],s=22,facecolors='none',edgecolors='C'+str(attempt),label='Donors attempt '+str(attempt))
    axes[0,0].scatter([B[0]],[B[2]],c='k',marker='s',label='Captured wall B');axes[0,0].set_aspect('equal');axes[0,0].set(title='Actual captured positions; cell traversal preserved',xlabel='x [m]',ylabel='z [m]');axes[0,0].legend(fontsize=8)
    x=[v['attempt'] for v in attempts];axes[0,1].bar(x,[abs(v['independent_M_det']) for v in attempts]);axes[0,1].axhline(.001,c='r',ls='--',label='Original geometry limit');axes[0,1].set(title='Independently recomputed |det M|',yscale='log',xlabel='Attempt');axes[0,1].legend()
    for a in attempts:
        d=[v for v in donors if v['attempt']==a['attempt'] and v['actual_input_C_xz_sym_eig_min'] is not None]
        axes[1,0].scatter([a['attempt']]*len(d),[v['actual_input_C_xz_sym_eig_min'] for v in d],s=12,c='C0',alpha=.5)
        if a['independent_C_sym_eig_min'] is not None:axes[1,0].scatter([a['attempt']],[a['independent_C_sym_eig_min']],marker='x',s=75,c='r')
    axes[1,0].axhline(0,c='k',lw=.8);axes[1,0].set(title='Blue=captured donor min eigen; red=independent fitted min',xlabel='Attempt')
    for attempt in x:
        d=[v for v in donors if v['attempt']==attempt and v['independent_alpha'] is not None];axes[1,1].plot(range(len(d)),[v['independent_alpha'] for v in d],'.-',label='Attempt '+str(attempt))
    axes[1,1].axhline(0,c='k',lw=.8);axes[1,1].set(title='Independent anchored coefficients',xlabel='Actual donor traversal order');axes[1,1].legend()
    for ax in axes.flat:ax.grid(alpha=.2)
    fig.suptitle('Replay host-exception inputs at source t=%.17g; independent M/C, not GPU registers'%meta['TimeStep'],fontsize=12)
    fig.supxlabel('Device FMA/fastmath and host-to-CTE mapping are not independently reproduced. No old unsaved state, committed state or physical acceptance.',fontsize=9)
    out=Path(str(PREFIX)+'_diagnostic.png');fig.savefig(out,dpi=170);plt.close(fig);return out


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Root full review plus explicit offline execution required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'_*')),'Existing complete/partial outputs protected')
    consumed=[stat(Path(__file__)),stat(NOTE),stat(Path(proxy.__file__))]
    result=dict(stage=TAG,analysis_passed=False,physical_acceptance=False,original_full3_still_failed=True,replay_failure_handle_verified=False,actual_GPU_branch_confirmed=False,
        original_old_unsaved_fault_recovered=False,solver_invocations=0,native_decodes=0,build_invocations=0,VTK_invocations=0,SHA_scans=0)
    try:
        run,schema,meta,arrays,fluid,fixed,target,c,audit=inputs(consumed)
        result.update(replay_failure_handle_verified=True,solver_still_failed=True)
        for row in audit:
            name=row['array'];data=arrays[name]
            if data.dtype.kind=='f':
                physical=data[:,:3] if name=='PosCell' else data
                row['raw_nonfinite_scalars']=int(np.count_nonzero(~np.isfinite(physical)))
            else:row['raw_nonfinite_scalars']='not a numeric floating field'
            row['numeric_role_note']='All fixed CorrMat slots uninterpreted, may be stale/unwritten; only actual fluid donors are consumed' if name=='CorrMat' else 'PosCell.w decoded asuint32 bits, never a finite-value gate' if name=='PosCell' else 'Structural audit; numerical admissibility depends on actual consumption'
        part=participation(arrays,fluid,target,c);attempts,donors,summary=recompute(arrays,fluid,target,c)
        need(attempts,'Actual packet could not support the requested independent fit; preserve capture')
        files=[Path(str(PREFIX)+'_arrays.csv'),Path(str(PREFIX)+'_attempts.csv'),Path(str(PREFIX)+'_donors.csv')]
        csv_write(files[0],audit);csv_write(files[1],attempts)
        csv_write(files[2],donors,['attempt','traversal_order','actual_sorted_slot','actual_native_id','no_C_field_donors_consumed'])
        files.append(plot(attempts,donors,arrays,fluid,target,meta))
        need(all(stat(v['path'])==v for v in consumed),'A bound input changed during review')
        result.update(analysis_passed=True,analysis_complete=True,consumed_stats_unchanged=True,
            genuine_replay_exception_inputs_decoded=True,actual_sorted_arrays_preserved=True,capture_schema=1,
            actual_host_step_u64=schema['Nstep_actual_uint64'],actual_host_source_time_s=meta['TimeStep'],
            actual_wall_slot=target,actual_wall_native_id=int(arrays['Idp'][target,0]),actual_np=schema['np'],actual_npbok=schema['npbok'],
            matches_retained_reported_event=(int(arrays['Idp'][target,0])==894 and schema['Nstep_actual_uint64']==2196678 and meta['TimeStep']==10.983389999668779),
            participation=part,recomputation=summary,original_gate_distances_retained=True,
            donor_C_records=len(donors),no_C_field_donors_consumed=(len(donors)==0),
            gate_nearby_classification='All recomputed candidates remain unconfirmed; near gates cannot identify the actual GPU branch',
            not_captured=['actual device CTE snapshot','actual failed GPU M/C registers','PorePress/P0/rho/kappa/stress/full22 ledger'],
            inactive_fixed_C_numeric_admissibility_not_claimed=True,no_full22_or_ledger_certificate_from_packet=True,
            metadata_schema_itself_is_host_mapping_not_device_CTE=True,files=[stat(v) for v in files],visual_QA_pending=True)
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=consumed
    with CHECK.open('x',encoding='utf-8') as f:json.dump(plain(result),f,ensure_ascii=False,indent=2,allow_nan=False)
    need(result['analysis_passed'],result.get('first_failure','Independent analysis incomplete; preserve partials'))


if __name__=='__main__':main()
