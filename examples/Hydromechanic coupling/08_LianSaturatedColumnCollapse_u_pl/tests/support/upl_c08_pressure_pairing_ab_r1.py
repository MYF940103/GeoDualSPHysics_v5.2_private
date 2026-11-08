"""Saved-state C-weighted mechanical A/B and separately matched dissipative control."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json
from pathlib import Path
import numpy as np
import upl_c08_local_pressure_spectrum_as_r1 as previous

base,old,p,ace=previous.base,previous.old,previous.p,previous.ace
need,read,stat=base.need,base.read,base.stat
T=base.T;TAG='upl_c08_pressure_pairing_ab_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');WATER=1000.;ZREF=2.

def vector_action(row,pressure):return sum((v*float(pressure[j]) for j,v in row.items()),np.zeros(2))

class CWeightedMechanical:
    """A1 only: original raw float geometry, with pi Ci + pj Cj coefficients."""
    def __init__(self,cloud,frame):
        self.c=cloud;self.raw=ace.Mechanical(cloud,frame);self.rho=self.raw.rho;self.cache={};self.native_action={}
    def row(self,i):
        if i not in self.cache:
            c=self.c;neighbors=self.raw.row(i);ci=c.correction(i)[0];row={i:np.zeros(2)}
            for j in neighbors:
                if j==i:continue
                delta=np.asarray(c.x[i]-c.x[j],dtype=np.float32);rr2=np.float32(delta[0]*delta[0]+delta[1]*delta[1]);fac=np.float32(p.g.cubic(float(rr2))[1]);g=np.asarray(fac*delta,dtype=np.float32).astype(float)
                weight=-float(c.V[j])/float(self.rho[i]);row[i]+=weight*(ci@g);row[int(j)]=weight*(c.correction(int(j))[0]@g)
            need(all(np.isfinite(v).all() for v in row.values()),'Nonfinite C-weighted force row');self.cache[i]=row;self.native_action[i]=vector_action(row,c.p)
        return self.cache[i]
    def pressure_acceleration(self,i):return vector_action(self.row(i),self.c.p)

class MatchedD:
    """One Darcy-double receiver-C divergence used on BOTH sides of the control."""
    def __init__(self,cloud):self.c=cloud;self.cache={}
    def row(self,i):
        if i not in self.cache:
            c=self.c;ci=c.correction(i)[0];row={i:np.zeros(2)}
            for j,d,rr2,g in c.edges(i,False):
                v=float(c.V[j])*(ci@g);row[i]-=v;row[int(j)]=v
            need(all(np.isfinite(v).all() for v in row.values()),'Nonfinite matched D');self.cache[i]=row
        return self.cache[i]

class MatchedGadj:
    """Literal weighted transpose: G_j,l = -(Vl/Vj) D_l,j, full inbound rows."""
    def __init__(self,D):self.D=D;self.c=D.c;self.cache={}
    def row(self,j):
        if j not in self.cache:
            c=self.c;row={}
            for l in self.D.row(j):
                inbound=self.D.row(l);need(j in inbound,'Chosen complete Darcy stencil is not bidirectional');row[int(l)]=-(float(c.V[l])/float(c.V[j]))*inbound[j]
            need(all(np.isfinite(v).all() for v in row.values()),'Nonfinite matched weighted transpose');self.cache[j]=row
        return self.cache[j]

def paired_row(cloud,rho,D,G,i):
    row={};B=p.KW/float(cloud.n[i]);coefficients=[]
    for j,value in D.row(i).items():
        coefficient=float(cloud.k[j])/p.GAMMA*(1.-WATER/float(rho[j]));coefficients.append(coefficient);ace.dot_row(row,G.row(j),B*coefficient*value)
    return row,min(coefficients),max(coefficients)

def extend_rows(R,source_nodes,columns):
    out=np.zeros((len(R),len(columns)));out[:,[columns[int(j)] for j in source_nodes]]=R;return out

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline pressure pairing comparison')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial pairing result protected')
    proof=read(previous.CHECK);rawproof=read(base.CHECK);need(proof['passed'] and proof['analysis_completed'] and proof['evaluated_saved_state_blocks']==8 and proof['not_evaluated_WallStencil_blocks']==0 and rawproof['passed'],'Sealed actual-AS and raw eight-block analyses required')
    data,done,clocks,before=old.load();before.extend(stat(q) for q in (Path(__file__),T/'notes'/(TAG+'.md'),previous.CHECK,base.CHECK,T/'notes/upl_c08_pressure_adjoint_candidate_r1.md'))
    before.append(old.bind(next(e for e in proof['consumed'] if Path(e['path']).samefile(base.__file__))))
    before.append(old.bind(next(e for e in proof['consumed'] if Path(e['path']).samefile(previous.__file__))))
    reference_path=Path(str(previous.PREFIX)+'_summary.csv');before.append(old.bind(next(e for e in proof['files'] if Path(e['path']).samefile(reference_path))))
    with reference_path.open(encoding='utf-8',newline='') as f:reference={(int(r['part']),r['patch'],r['variable_view']):r for r in csv.DictReader(f)}
    summary=[];responses=[];files=[];skips=[];rows_info=[];matrix_count=0
    for part in base.PARTS:
        frame=data[part];cloud=p.Cloud(frame);time=float(frame['time']);tau=time-done['source_actual_time_s'];candidate=CWeightedMechanical(cloud,frame);D=MatchedD(cloud);G=MatchedGadj(D);rho=frame['PoroMixtureDensity'][:,0]
        for label,focus in base.FOCI:
            print('PRESSURE_PAIRING_BLOCK',part,label,flush=True)
            rawpath=Path(str(base.PREFIX)+'_part'+str(part).zfill(3)+'_'+label+'.npz');aspath=Path(str(previous.PREFIX)+'_part'+str(part).zfill(3)+'_'+label+'.npz')
            before.extend(old.bind(next(e for e in source['files'] if Path(e['path']).samefile(path))) for source,path in ((rawproof,rawpath),(proof,aspath)))
            with np.load(rawpath,allow_pickle=False) as q,np.load(aspath,allow_pickle=False) as a:
                ids=q['target_native_IDs'].copy();old_pressure_ids=q['pressure_native_IDs'].copy();weights=q['storage_W_nV_over_Kw'].copy();saved_direct=q['full_direct_rows'].copy();saved_AS=a['full_AS_increment_rows'].copy();saved_current=a['full_direct_plus_rawAce_plus_ASJac_rows'].copy();current_A=a['A_direct_plus_rawAce_plus_ASJac'].copy()
                need(np.array_equal(a['target_native_IDs'],ids) and np.array_equal(a['pressure_native_IDs'],old_pressure_ids) and np.array_equal(a['storage_W_nV_over_Kw'],weights) and float(q['time_s'])==float(a['time_s'])==time,'Saved material variables/pressure columns/weights/clock differ')
            targets=np.asarray([base.at(cloud,int(j)) for j in ids]);old_nodes=np.asarray([base.at(cloud,int(j)) for j in old_pressure_ids]);need(len(ids)==rawproof['patch_sizes'][label] and np.array_equal(weights,cloud.n[targets]*cloud.V[targets]/p.KW),'Original patch/storage differs')
            context=dict(part=part,time_s=time,tau_s=tau,completed_step=int(clocks[part]['completed_step']),patch=label,focus_IDs=';'.join(map(str,focus)),all_patch_variables=len(ids));bad_rows=[];pair_rows=[];coefficient_ranges=[];descriptions=[]
            try:
                for i in targets:
                    channels,unused,description=ace.probe(cloud,candidate,int(i));bad_rows.append(ace.combine(channels['via_divAce'],channels['via_FS_Ace_lx'],channels['via_chain_Ace']));pair,low,high=paired_row(cloud,rho,D,G,int(i));pair_rows.append(pair);coefficient_ranges.append((low,high));descriptions.append(description)
            except p.WallStencil as error:
                skips.append(dict(**context,status='not_evaluated_WallStencil',failed_row_native_ID=int(cloud.ids[i]),reason=str(error)));continue
            # The paired product can have different pressure columns. Extend, never drop.
            pressure_nodes=np.asarray(sorted(set(map(int,old_nodes))|set().union(*(set(r) for r in bad_rows+pair_rows))),dtype=int);columns={int(j):k for k,j in enumerate(pressure_nodes)};inside=np.asarray([columns[int(i)] for i in targets]);need(np.all(cloud.ids[pressure_nodes]>=2060),'Fixed source escaped full stencil guards')
            direct=extend_rows(saved_direct,old_nodes,columns);AS=extend_rows(saved_AS,old_nodes,columns);current=extend_rows(saved_current,old_nodes,columns);bad=base.matrix_rows(bad_rows,pressure_nodes);pair=base.matrix_rows(pair_rows,pressure_nodes)
            matrices={'A0_current_same_AS':current,'A1_Cweighted_same_AS':direct+bad+AS,'A_pair_no_AS':pair,'A_pair_same_AS':pair+AS};need(np.array_equal(current[:,inside],current_A),'Sealed current matrix changed while extending columns')
            matrix_path=Path(str(PREFIX)+'_part'+str(part).zfill(3)+'_'+label+'.npz');need(not matrix_path.exists(),'Existing pairing matrix protected')
            np.savez(matrix_path,target_native_IDs=ids,pressure_native_IDs=cloud.ids[pressure_nodes],original_pressure_native_IDs=old_pressure_ids,target_xz_m=cloud.x[targets],target_FSType=cloud.fs[targets],target_p_Pa=cloud.p[targets],storage_W_nV_over_Kw=weights,full_direct_rows=direct,full_same_AS_increment_rows=AS,**{'full_'+key:value for key,value in matrices.items()},**{key:value[:,inside] for key,value in matrices.items()},time_s=np.asarray(time),tau_s=np.asarray(tau),completed_step=np.asarray(int(clocks[part]['completed_step'])))
            files.append(matrix_path);matrix_count+=1
            tests={'constant_1Pa':np.ones(len(pressure_nodes)),'affine_x_1Pa_per_m':cloud.x[pressure_nodes,0],'affine_z_1Pa_per_m':cloud.x[pressure_nodes,1],'hydrostatic_gamma_2_minus_z':p.GAMMA*(ZREF-cloud.x[pressure_nodes,1])}
            for row,i in enumerate(targets):rows_info.append(dict(**context,native_ID=int(cloud.ids[i]),x_m=float(cloud.x[i,0]),z_m=float(cloud.x[i,1]),FSType=int(cloud.fs[i]),C_moment_det=descriptions[row]['C_moment_det'],C_moment_condition=descriptions[row]['C_moment_condition'],nearest_fixed_B_m=descriptions[row]['nearest_fixed_B_m'],A1_force_expansion_roundoff_m_s2=descriptions[row]['mechanical_B_expansion_roundoff_m_s2'],A1_Ace_to_Darcy_expansion_roundoff_Pa_s=descriptions[row]['Ace_to_Darcy_expansion_roundoff_Pa_s'],matched_coefficient_min=coefficient_ranges[row][0],matched_coefficient_max=coefficient_ranges[row][1],original_pressure_columns=len(old_nodes),union_pressure_columns=len(pressure_nodes),added_pressure_columns=len(pressure_nodes)-len(old_nodes)))
            for variant,R in matrices.items():
                A=R[:,inside]
                for view,selected in (('all_patch_variables',np.arange(len(ids))),('FS0_principal',np.flatnonzero(cloud.fs[targets]==0))):
                    b=dict(**context,variant=variant,variable_view=view,variables=len(selected),all_outside_pressure_perturbations_held_zero=True)
                    if not len(selected):summary.append(dict(**b,status='not_evaluated_empty_FS0'));continue
                    ref=reference[(part,label,view)];need(ref['status']=='evaluated_frozen_outside_held' and int(ref['variables'])==len(selected),'Current same-AS baseline view differs');sub=A[np.ix_(selected,selected)]
                    if variant=='A0_current_same_AS':stats={key:float(ref[key]) for key in ('max_real_eigenvalue_per_s','imag_of_max_real_eigenvalue_per_s','max_abs_imag_eigenvalue_per_s','min_real_eigenvalue_per_s','midpoint_R_spectral_radius','max_frozen_storage_symmetric_eigenvalue_per_s')}
                    else:stats,unused=base.spectral(sub,weights[selected]);stats.pop('selected_mode_peak_local_index')
                    outside=np.ones(len(pressure_nodes),dtype=bool);outside[inside[selected]]=False;outside_rows=R[selected][:,outside]
                    summary.append(dict(**b,status='evaluated_frozen_outside_held',**stats,max_real_eigenvalue_minus_current_per_s=stats['max_real_eigenvalue_per_s']-float(ref['max_real_eigenvalue_per_s']),storage_symmetric_eigenvalue_minus_current_per_s=stats['max_frozen_storage_symmetric_eigenvalue_per_s']-float(ref['max_frozen_storage_symmetric_eigenvalue_per_s']),outside_pressure_column_IDs=int(np.count_nonzero(np.any(outside_rows!=0,axis=0))),outside_coupling_abs_sum_per_s=float(np.abs(outside_rows).sum()),constant_full_stencil_max_abs_Pa_s=float(np.max(np.abs(R[selected].sum(axis=1)))),constant_outside_held_max_abs_Pa_s=float(np.max(np.abs(sub.sum(axis=1)))),matched_coefficient_min=min(v[0] for v in coefficient_ranges),matrix_file=matrix_path.name))
                    for field,values in tests.items():
                        complete=R[selected]@values;held=sub@values[inside[selected]]
                        for k,j in enumerate(selected):responses.append(dict(**b,test_field=field,native_ID=int(ids[j]),x_m=float(cloud.x[targets[j],0]),z_m=float(cloud.x[targets[j],1]),full_field_on_complete_stencil_rate_Pa_s=float(complete[k]),test_field_with_outside_perturbations_zero_rate_Pa_s=float(held[k]),hydrostatic_reference_z_m=ZREF if field.startswith('hydrostatic') else '',pressure_operator_action_not_total_hydrostatic_residual=True))
    for leaf,rows in (('summary',summary),('responses',responses),('row_geometry',rows_info),('not_evaluated',skips)):
        if rows:
            path=Path(str(PREFIX)+'_'+leaf+'.csv');base.write(path,rows);files.append(path)
    need(matrix_count+len(skips)==8,'Every original saved-state/focus block must be accounted for');need(all(stat(Path(e['path']))==e for e in before),'Sealed data, matrix or helper changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,requested_saved_state_blocks=8,evaluated_saved_state_blocks=matrix_count,not_evaluated_WallStencil_blocks=len(skips),selected_parts=list(base.PARTS),patch_sizes=rawproof['patch_sizes'],current_matrices_and_same_AS_increment_read_not_recomputed=True,A1='C-weighted/adjoint-inspired mechanical pressure coefficient only; original float geometry/cutoff',A1_strict_Darcy_double_adjoint_claimed=False,A1_current_direct_Lstar_FS_gradk_and_ASJac_preserved=True,mathematical_control='B D diag[k/gamma*(1-rhow/rho)] Gadj, Gadj=-Vv^-1 D.T Vp, one matched Darcy-double D',control_is_not_production_candidate=True,control_no_AS_and_same_AS_reported=True,all_original_WallStencil_guards_kept=True,full_neighbor_C_can_require_three_geometry_hops=True,operator_pressure_columns_are_full_union_no_columns_dropped=True,theta_sigma_packed_float_path_not_identified_with_Darcy_double_D=True,variable_views=['all_patch_variables','FS0_principal'],outside_pressure_perturbations_held_zero=True,storage_W='nV/Kw pressure-storage norm, not full-state energy',midpoint_R='Frozen pressure-only polynomial, not full integrator eigenvalues',hydrostatic_response='Matrix action on gamma*(2-z); excludes gravity/effective-stress source and is not total hydrostatic balance',ASJac_real_proxy_limits_inherited=True,FS23_zero_pressure_projection_not_linearized=True,geometry_J_n_k_sigmaeff_theta_velocity_FS_frozen=True,physical_acceptance=False,thresholds_changed=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=[stat(q) for q in files])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('PRESSURE_PAIRING_AB_READY',CHECK,flush=True)

if __name__=='__main__':main()
