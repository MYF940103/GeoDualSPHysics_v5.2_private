"""Frozen far-wall pressure -> raw mechanical Ace -> Darcy Jacobian, not a coupled GPU replay."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import upl_c08_pressure_coeff_r1 as p
T=Path(__file__).resolve().parents[1];TAG='upl_c08_pressure_ace_jac_r1';PREFIX=T/'figures'/TAG
need,read,stat=p.need,p.read,p.stat

def write(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('x',encoding='utf-8',newline='') as f:
        out=csv.DictWriter(f,fieldnames=fields);out.writeheader();out.writerows(rows)

def add(target,key,value):target[key]=target.get(key,0.)+float(value)
def combine(*rows):
    out={}
    for row in rows:
        for key,value in row.items():add(out,key,value)
    return out
def action(row,pressure):return sum(value*float(pressure[key]) for key,value in row.items())

class Mechanical:
    def __init__(self,cloud,frame):
        self.c=cloud;self.rho=frame['PoroMixtureDensity'][:,0];self.cache={};self.native_action={}

    def row(self,i):
        if i not in self.cache:
            c=self.c;rho=float(self.rho[i]);need(rho>0 and np.isfinite(rho),'Native double mixture inertia required')
            # One complete6800-point vector, not an NxN matrix: no omitted two-hop edge at a float cutoff.
            d=np.asarray(c.x[i]-c.x,dtype=np.float32)
            rr=np.asarray(d[:,0]*d[:,0]+d[:,1]*d[:,1],dtype=np.float32)
            hits=np.flatnonzero((rr<=p.R2)&(rr>=p.LOWER))
            row={i:np.zeros(2)};ap=np.zeros(2)
            for j in hits:
                if c.ids[j]<2060:raise p.WallStencil('fixed_native_ID_'+str(int(c.ids[j]))+'_in_mechanical_stencil_of_'+str(int(c.ids[i])))
                fac=np.float32(p.g.cubic(float(rr[j]))[1])
                raw=np.asarray(fac*d[j],dtype=np.float32).astype(float)
                edge=-(float(c.V[j])/rho)*raw
                row[i]+=edge;row[int(j)]=row.get(int(j),np.zeros(2))+edge
                ap+=edge*(float(c.p[i])+float(c.p[j]))
            need(all(np.isfinite(v).all() for v in row.values()),'Nonfinite mechanical pressure Jacobian')
            self.cache[i]=row;self.native_action[i]=ap
        return self.cache[i]

    def pressure_acceleration(self,i):
        row=self.row(i)
        return sum((value*float(self.c.p[key]) for key,value in row.items()),np.zeros(2))

def dot_row(target,B,vector):
    for key,value in B.items():add(target,key,float(vector@value))

def metrics(row,i,pressure):
    off=[value for key,value in row.items() if key!=i];negative=[v for v in off if v<0]
    return dict(diagonal_per_s=float(row.get(i,0.)),constant_1Pa_response_Pa_s=float(sum(row.values())),negative_offdiag_count=len(negative),negative_offdiag_abs_sum_per_s=float(-sum(negative)),min_offdiag_per_s=float(min(off)) if off else None,max_offdiag_per_s=float(max(off)) if off else None,unit_local_minimum_worst_rate_Pa_s=float(sum(negative)),unit_local_maximum_worst_rate_Pa_s=float(row.get(i,0.)+sum(v for v in off if v>0)),native_p_channel_contribution_Pa_s=float(action(row,pressure)))

def probe(cloud,mechanical,i):
    jj,raw,taylor,chain,current,desc=cloud.coefficients(i)
    direct={i:-float(current.sum())}
    for j,value in zip(jj,current):add(direct,int(j),value)
    ci=cloud.correction(i)[0];edges=cloud.edges(i,False);div={};fs={};ch={};di=np.zeros(2)
    pref=p.KW/(float(cloud.n[i])*p.GAMMA);ki=float(cloud.k[i]);kp=ki/(p.SOLID0*p.CK);rw=1000.
    first={i,*[int(j) for j in jj]};Bi=mechanical.row(i);ai=mechanical.pressure_acceleration(i)
    direct_div=0.;B_discrepancy=0.
    for j,d,rr2,grad in edges:
        q=float(cloud.V[j])*(ci@grad);di-=q
        Bj=mechanical.row(j);dot_row(div,Bj,pref*rw*ki*q)
        aj=mechanical.pressure_acceleration(j);direct_div+=float(q@(aj-ai))
        B_discrepancy=max(B_discrepancy,float(np.max(np.abs(aj-mechanical.native_action[j]))))
    dot_row(div,Bi,pref*rw*ki*di)
    lx=np.array([desc['lx_x'],desc['lx_z']]);gJ=np.array([desc['reconstructed_gradJ_x'],desc['reconstructed_gradJ_z']])
    active_fs=int(cloud.fs[i]) in (2,3)
    if active_fs:dot_row(fs,Bi,pref*rw*ki*lx)
    dot_row(ch,Bi,pref*rw*kp*gJ)
    total=combine(direct,div,fs,ch)
    ideal_factor=1.-rw/float(mechanical.rho[i]);ideal={key:ideal_factor*value for key,value in direct.items()}
    assembled_ace=action(combine(div,fs,ch),cloud.p)
    unassembled_ace=pref*rw*(ki*direct_div+(ki*float(lx@ai) if active_fs else 0.)+kp*float(gJ@ai))
    B_discrepancy=max(B_discrepancy,float(np.max(np.abs(ai-mechanical.native_action[i]))))
    desc.update(two_hop_pressure_nodes=len(total),mechanical_Ace_rows=1+len(jj),ideal_constant_rho_reduction_factor=ideal_factor,mechanical_B_expansion_roundoff_m_s2=B_discrepancy,Ace_to_Darcy_expansion_roundoff_Pa_s=float(assembled_ace-unassembled_ace))
    rows={'direct_pressure':direct,'via_divAce':div,'via_FS_Ace_lx':fs,'via_chain_Ace':ch,'composite_pressure_channel':total,'ideal_local_constant_rho_scale_only':ideal}
    return rows,first,desc

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one new offline Jacobian observation')
    need(not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial observation protected')
    previous=T/'figures/upl_c08_pressure_coeff_r1.check.json';old=read(previous);need(old['passed'] and old['analysis_completed'] and not old['actual_Ace_theta_or_rate_replayed'],'Closed prior coefficient audit required')
    native=read(p.CHECK);need(native['passed'] and native['original_saved_native_guards_passed'] and native['consumed_stats_unchanged'] and not native['runtime_success_claimed'],'Closed native54 prefix required')
    before=[stat(q) for q in (Path(__file__),T/'notes'/(TAG+'.md'),Path(p.__file__),Path(p.w.__file__),Path(p.g.__file__),T/'support/upl_c08_fsmask_r1.py',previous,p.CHECK)]
    for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):
        q=p.NATIVE/leaf;e=next(e for e in native['files'] if Path(e['path']).samefile(q));need(stat(q)==e,'Closed native binding changed');before.append(e)
    data,done,clocks,history=p.w.load(p.NATIVE,54,4216000)
    need(done['diagnostic_partial'] and not done['runtime_success_claimed'] and done['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly','Actual saved-stage identity differs')
    summaries=[];coefficients=[];accelerations=[];skips=[]
    for part in p.PARTS:
        frame=data[part];cloud=p.Cloud(frame);mechanical=Mechanical(cloud,frame)
        for identity in p.IDS:
            match=np.flatnonzero(cloud.ids==identity);need(len(match)==1,'Material ID absent');i=int(match[0])
            base=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-done['source_actual_time_s'],completed_step=int(clocks[part]['completed_step']),native_ID=identity,FSType=int(cloud.fs[i]),x_m=float(cloud.x[i,0]),z_m=float(cloud.x[i,1]),p_Pa=float(cloud.p[i]),J=float(cloud.J[i]),rho_mixture_kg_m3=float(mechanical.rho[i]))
            try:rows,first,desc=probe(cloud,mechanical,i)
            except p.WallStencil as e:skips.append(dict(**base,reason=str(e)));continue
            for label,row in rows.items():summaries.append(dict(**base,variant=label,**desc,**metrics(row,i,cloud.p)))
            for m in sorted(rows['composite_pressure_channel']):
                row=dict(**base,pressure_node_native_ID=int(cloud.ids[m]),hop=0 if m==i else (1 if m in first else 2),pressure_node_x_m=float(cloud.x[m,0]),pressure_node_z_m=float(cloud.x[m,1]),pressure_node_p_Pa=float(cloud.p[m]))
                row.update({name+'_dRate_dp_per_s':float(values.get(m,0.)) for name,values in rows.items()});coefficients.append(row)
            for j in sorted(first):
                aj=mechanical.pressure_acceleration(j)
                accelerations.append(dict(**base,acceleration_target_native_ID=int(cloud.ids[j]),acceleration_target_x_m=float(cloud.x[j,0]),acceleration_target_z_m=float(cloud.x[j,1]),pressure_only_Ace_x_m_s2=float(aj[0]),pressure_only_Ace_z_m_s2=float(aj[1]),mechanical_full_stencil_nodes=len(mechanical.row(j))-1,not_actual_finished_Ace=True))
    paths=[]
    for name,rows in (('rows',summaries),('coefficients',coefficients),('pressure_Ace',accelerations),('not_evaluated',skips)):
        if rows:
            q=Path(str(PREFIX)+'_'+name+'.csv');write(q,rows);paths.append(q)
    need(all(stat(Path(e['path']))==e for e in before),'Sealed data or immutable helper changed')
    total=[r for r in summaries if r['variant']=='composite_pressure_channel']
    result=dict(stage=TAG,passed=True,analysis_completed=True,selected_parts=list(p.PARTS),selected_native_IDs=list(p.IDS),evaluated_receivers=len(total),not_evaluated_receivers=len(skips),most_negative_native_p_composite_response=min(total,key=lambda r:r['native_p_channel_contribution_Pa_s']) if total else None,mechanical_self_pressure_terms_retained=True,all_two_hop_mechanical_and_C_stencils_checked=True,wall_stencils_never_silently_omitted=True,mechanical_gradient='raw float-component/float-gradient proxy, Vj/rho_i and (p_i+p_j)',Darcy_gradient='Ci corrected direct-double-position gradient; native-coordinate reconstruction proxy',frozen_sigma_theta_J_FS_and_velocity=True,float_accumulation_cast_Jacobian_not_AD=True,actual_finished_Ace_or_rate_replayed=False,packed_GPU_positions_and_unsaved_half_stage_not_recovered=True,ideal_factor_only_valid_for_constant_rho_continuum_limit=True,global_matrix_eigenspectrum_or_time_integration=False,negative_offdiag_not_proof_of_global_instability=True,physical_acceptance=False,dt_changed=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=[stat(q) for q in paths])
    with Path(str(PREFIX)+'.check.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('PRESSURE_ACE_JACOBIAN_OBSERVATION_READY',str(PREFIX)+'.check.json',flush=True)

if __name__=='__main__':main()
