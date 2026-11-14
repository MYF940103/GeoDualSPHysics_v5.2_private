"""Offline fourteen-state CPU gradient diagnostics; no executable/native/solver calls."""
import argparse,csv,itertools,json,math,struct,sys
from pathlib import Path
import numpy as np
import c08_h18_storage_review_r2 as u
T,L=u.T,u.L
need,read,stat,bind,entry,owned,same=u.need,u.read,u.stat,u.bind,u.entry,u.owned,u.same
TAG='c08_h18_bed_gradient_review_r1';NOTE=T/'notes'/(TAG+'.md')
COMPONENT=L/'c08_h18_bed_gradient_probe_r1.check.json';NATIVE_REVIEW=L/'c08_h18_rv_radial_window_review_r1.check.json'
OUT=T/'outputs/c08_h18_bed_gradient_probe_r1'
CASES=('original','radial');PARTS=tuple(range(28,35));IDS=(6961,6962,7011,7012);N=5000;DT=5e-6;KW=1e9
REGIONS=('all_soil','near_bed_with_bound_support','nonzero_kappa_history','four_fixed_material_IDs')
NEAR_BED=2*struct.unpack('<f',struct.pack('<f',.072))[0]
STATES=tuple(itertools.product(CASES,PARTS));STATE_INDEX={q:i for i,q in enumerate(STATES)}
HEADERS={"gradient":["case","part","time_s","completed_step","native_id","x_m","z_m","p_Pa","P0_Pa","J","kappa","saved_FS","fresh_FS","saved_prior_stage_theta_s_1","fresh_CPU_theta_s_1","literal_theta_s_1","corrected_gradient_trace_s_1","elastic_Rsigma_trace_over3K_s_1","G1_trace_minus_theta_s_1","elastic_trace_over3K_minus_theta_s_1","Rsigma_xx_Pa_s","Rsigma_yy_Pa_s","Rsigma_zz_Pa_s","Rsigma_xy_Pa_s","Rsigma_yz_Pa_s","Rsigma_xz_Pa_s","Rsigma_trace_Pa_s","ModulusK_float_Pa","C11","C12","C13","C21","C22","C23","C31","C32","C33","fluid_outer_donors","fluid_theta_donors","fluid_theta_support_rejected","fluid_Fac_float_bits_differ","fluid_sum_volume_float_cast_abs_m2","fluid_full_vs_tangent_velocity_bits_differ","fluid_theta_s_1","fluid_raw_grad_xx_s_1","fluid_raw_grad_xy_s_1","fluid_raw_grad_xz_s_1","fluid_raw_grad_yx_s_1","fluid_raw_grad_yy_s_1","fluid_raw_grad_yz_s_1","fluid_raw_grad_zx_s_1","fluid_raw_grad_zy_s_1","fluid_raw_grad_zz_s_1","fluid_corrected_grad_xx_s_1","fluid_corrected_grad_xy_s_1","fluid_corrected_grad_xz_s_1","fluid_corrected_grad_yx_s_1","fluid_corrected_grad_yy_s_1","fluid_corrected_grad_yz_s_1","fluid_corrected_grad_zx_s_1","fluid_corrected_grad_zy_s_1","fluid_corrected_grad_zz_s_1","bound_outer_donors","bound_theta_donors","bound_theta_support_rejected","bound_Fac_float_bits_differ","bound_sum_volume_float_cast_abs_m2","bound_full_vs_tangent_velocity_bits_differ","bound_theta_s_1","bound_raw_grad_xx_s_1","bound_raw_grad_xy_s_1","bound_raw_grad_xz_s_1","bound_raw_grad_yx_s_1","bound_raw_grad_yy_s_1","bound_raw_grad_yz_s_1","bound_raw_grad_zx_s_1","bound_raw_grad_zy_s_1","bound_raw_grad_zz_s_1","bound_corrected_grad_xx_s_1","bound_corrected_grad_xy_s_1","bound_corrected_grad_xz_s_1","bound_corrected_grad_yx_s_1","bound_corrected_grad_yy_s_1","bound_corrected_grad_yz_s_1","bound_corrected_grad_zx_s_1","bound_corrected_grad_zy_s_1","bound_corrected_grad_zz_s_1"],"soil":["case","part","time_s","tau_s","completed_step","native_id","x_m","z_m","p_Pa","P0_Pa","J","kappa","no_fixed_neighbors","saved_FS","fresh_FS","n","V","rho","k","base_Acex","base_Acez","candidate_Acex","candidate_Acez","ideal_da_x","ideal_da_z","committed_da_x","committed_da_z","base_R_Pa_s","candidate_R_Pa_s","delta_R_Pa_s","base_compression","candidate_compression","delta_compression","base_LP","candidate_LP","delta_LP","base_Taylor_pressure","candidate_Taylor_pressure","delta_Taylor_pressure","base_Da","candidate_Da","delta_Da","base_FS_Ace_Lx","candidate_FS_Ace_Lx","delta_FS_Ace_Lx","base_chain_pressure","candidate_chain_pressure","delta_chain_pressure","base_chain_Ace","candidate_chain_Ace","delta_chain_Ace","base_numeric_residual","candidate_numeric_residual","delta_numeric_residual"],"pairs":["case","part","time_s","tau_s","completed_step","ID_i","ID_j","distance_m","distance_over_dp","rdot_m_s","curvature_m_s2","direct_neighbor","beta","dv_affine_n_m_s","rbar_n_m_s","ri_n_m_s","rj_n_m_s","radial_s_m_s","radial_q_m_s","limiter_a_m_s","direct_active","current_vector_direct_Fi_n_shadow_N_m","direct_RV_Fi_n_N_m","direct_RV_relative_a_n_m_s2","allneighbor_ideal_da_n_m_s2","allneighbor_committed_da_n_m_s2","base_relative_a_n_m_s2","candidate_relative_a_n_m_s2","base_rddot_m_s2","candidate_rddot_m_s2"],"focus":["case","part","time_s","tau_s","completed_step","pair_i","pair_j","native_id","p_Pa","P0_Pa","J","kappa","saved_FS","fresh_FS","total_eigen_f32_0","total_eigen_f32_1","total_eigen_f32_2","total_positive_eigen_sum_Pa","total_nn_Pa","effective_nn_Pa","actual_AS_tensor_nn_Pa","base_R_Pa_s","candidate_R_Pa_s","base_Acex","base_Acez","ideal_RV_dax","ideal_RV_daz","committed_RV_dax","committed_RV_daz","Lxx","Lxz","Lzx","Lzz"],"walls":["case","part","time_s","completed_step","soil_id","wall_id","mode","slip_mode","sorted_wall_index","NpbOk","drx_m","drz_m","Vj_m2","outer_Fac","outer_rr2_m2","theta_prr2_m2","normal_x","normal_y","normal_z","ghost_physical_vx","ghost_physical_vy","ghost_physical_vz","full_derivative_vx","full_derivative_vy","full_derivative_vz","tangent_vx","tangent_vy","tangent_vz","wall_Acex","wall_Acey","wall_Acez"]}
# First author observation AFTER the genuinely passed component, not a claim that
# these CSVs carried an end-of-component seal before that observation.
CSV_FIRST_SEALS=[dict(path="D:\\MYF\\SPH\\GeoDualSPHysics_redevelop_f66777b\\examples\\Hydromechanic coupling\\08_LianSaturatedColumnCollapse_u_pl\\tests\\outputs\\c08_h18_bed_gradient_probe_r1\\gradient.csv",bytes=57600186,mtime_ns=1794690632906168700),
 dict(path="D:\\MYF\\SPH\\GeoDualSPHysics_redevelop_f66777b\\examples\\Hydromechanic coupling\\08_LianSaturatedColumnCollapse_u_pl\\tests\\outputs\\c08_h18_bed_gradient_probe_r1\\soil.csv",bytes=57541941,mtime_ns=1794690632906168700),
 dict(path="D:\\MYF\\SPH\\GeoDualSPHysics_redevelop_f66777b\\examples\\Hydromechanic coupling\\08_LianSaturatedColumnCollapse_u_pl\\tests\\outputs\\c08_h18_bed_gradient_probe_r1\\pairs.csv",bytes=37183,mtime_ns=1794690632906168700),
 dict(path="D:\\MYF\\SPH\\GeoDualSPHysics_redevelop_f66777b\\examples\\Hydromechanic coupling\\08_LianSaturatedColumnCollapse_u_pl\\tests\\outputs\\c08_h18_bed_gradient_probe_r1\\focus.csv",bytes=77735,mtime_ns=1794690632906168700),
 dict(path="D:\\MYF\\SPH\\GeoDualSPHysics_redevelop_f66777b\\examples\\Hydromechanic coupling\\08_LianSaturatedColumnCollapse_u_pl\\tests\\outputs\\c08_h18_bed_gradient_probe_r1\\walls.csv",bytes=224289,mtime_ns=1794690632906168700),
 dict(path="D:\\MYF\\SPH\\GeoDualSPHysics_redevelop_f66777b\\examples\\Hydromechanic coupling\\08_LianSaturatedColumnCollapse_u_pl\\tests\\outputs\\c08_h18_bed_gradient_probe_r1\\metrics.csv",bytes=17276,mtime_ns=1794690632906168700),
 dict(path="D:\\MYF\\SPH\\GeoDualSPHysics_redevelop_f66777b\\examples\\Hydromechanic coupling\\08_LianSaturatedColumnCollapse_u_pl\\tests\\outputs\\c08_h18_bed_gradient_probe_r1\\selected_clocks.csv",bytes=2050,mtime_ns=1794690632906168700)]
HEADERS['selected_clocks']='case,part,file,time_s,tau_from_actual_release_s,completed_step,saved_step,dt_s,signed_dterror_s,dterror_interval_empty,native_IDs,phase'.split(',')
ERRORS=('G1_minus_theta','elastic_trace_over3K_minus_theta','fresh_minus_saved_prior_theta','fresh_theta','G1_trace','one_fixed5us_pressure_gap_shadow_Pa')
WORK=('effective_gradient_correction_work_delta','pressure_gradient_correction_delta','pressure_theta_gradient_gap','coupled_conditional_work_delta','effective_D0_abs_scale','effective_D1_abs_scale','p_theta_abs_scale')
def bits(x):return struct.pack('<d',float(x))
def write_csv(path,rows):
    need(rows,'No empty derived scientific table')
    with path.open('x',encoding='utf-8',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def rows(leaf):
    with(OUT/(leaf+'.csv')).open(encoding='utf-8',newline='')as f:
        r=csv.DictReader(f)
        if leaf in HEADERS:need(r.fieldnames==HEADERS[leaf],'Actual closed CSV header differs: '+leaf)
        for q in r:
            need(None not in q and all(v is not None for v in q.values()),'CSV width differs: '+leaf)
            yield q

def numeric(q,text=('case',)):
    out={}
    for k,v in q.items():
        if k in text:out[k]=v
        else:out[k]=float(v);need(math.isfinite(out[k]),'Nonfinite diagnostic value: '+k)
    return out

def key(q,idkey='native_id'):
    state=(q['case'],int(q['part']));need(state in STATE_INDEX,'Only original/radial P28–34 admitted')
    return state,int(q[idkey])
def clock_check(q,clocks):
    state=(q['case'],int(q['part']));c=clocks[state]
    need(bits(q['time_s'])==bits(c['time_s']) and int(q['completed_step'])==int(c['completed_step']),'Actual selected clock differs')
    return state
class Aggregate:
    def __init__(self):self.n=0;self.sum2={k:0. for k in ERRORS};self.maxabs={k:0. for k in ERRORS};self.counters={p+'_'+k:0. for p in('fluid','bound')for k in('outer_donors','theta_donors','theta_support_rejected','Fac_float_bits_differ','sum_volume_float_cast_abs_m2','full_vs_tangent_velocity_bits_differ')};self.work={p+'_'+k:0. for p in('fluid','bound')for k in WORK};self.workabs=dict(self.work)
    def add_error(self,k,v):self.sum2[k]=math.fsum((self.sum2[k],v*v));self.maxabs[k]=max(self.maxabs[k],abs(v))
    def observe(self,values,counters):
        self.n+=1
        for k,v in values.items():self.add_error(k,v)
        for k,v in counters.items():self.counters[k]=math.fsum((self.counters.get(k,0.),v))
    def add_work(self,passname,values):
        for k,v in zip(WORK,values):
            name=passname+'_'+k;self.work[name]=math.fsum((self.work.get(name,0.),v));self.workabs[name]=math.fsum((self.workabs.get(name,0.),abs(v)))
    def result(self):
        q={'material_IDs':self.n}
        for k in ERRORS:q[k+'_RMS']=math.sqrt(self.sum2[k]/self.n)if self.n else None;q[k+'_absmax']=self.maxabs[k]if self.n else None
        q.update(self.counters)
        for k,v in self.work.items():q[k+'_signed_W_m']=v;q[k+'_sum_abs_W_m']=self.workabs[k]
        for p in ('fluid','bound'):
            den=self.workabs.get(p+'_effective_D0_abs_scale',0.)+self.workabs.get(p+'_p_theta_abs_scale',0.)
            q[p+'_conditional_delta_over_abs_scale']=self.work.get(p+'_coupled_conditional_work_delta',0.)/den if den else None
        return q

def inputs(consumed):
    c=read(COMPONENT);need(c['passed']and c['consumed_stats_unchanged']and c['component']is True and c['physical_steps']==c['material_return_calls']==c['filter_calls']==0 and c['new_trajectory']is False,'Passed zero-advance actual component required')
    de=entry(c,'completion');done=read(de['path']);expected=dict(actual_force_calls=14,actual_Darcy_calls=28,actual_DtVariable_false_calls=28,observed_bare_CPU_soil_rows=70000,external_CPU_reference_bit_rows=0,literal_RHS_rows=140000,gradient_rows=70000,literal_theta_bit_rows=70000,literal_Rsigma_component_bit_checks=420000,soil_rows=70000,pair_rows=84,focus_endpoint_rows=168,actual_selected_clock_rows=14,physical_steps=0,material_return_calls=0,filter_calls=0)
    need(done['passed']and done['parts']==list(PARTS)and all(done[k]==v for k,v in expected.items())and done['GPU_stage_force_bit_truth']is False and done['saved_theta_is_current_CPU_stage']is False,'Original internal literal/call/coverage certificate differs')
    ca=entry(c,'actual_call');call=read(ca['path']);owned(call);be=entry(c,'build');b=read(be['path'])
    need(b['passed']and b['consumed_stats_unchanged']and b['actual_link_objects']==87 and b['physical_objects_compiled']==0 and same(call['program'],entry(b,'program')['path']),'Actual CPU-only source/build/handle differs')
    consumed.extend([stat(COMPONENT),de,ca,be,entry(b,'program')]);consumed.extend(bind(q)for q in CSV_FIRST_SEALS)
    clocks={}
    for q in rows('selected_clocks'):
        state=(q['case'],int(q['part']));need(state in STATE_INDEX and state not in clocks and int(q['completed_step'])==2000001+2000*state[1] and int(q['saved_step'])==int(q['completed_step'])-1 and float(q['dt_s'])==DT and float(q['signed_dterror_s'])<=1e-14 and q['dterror_interval_empty']=='0'and int(q['native_IDs'])==6805,'Original selected signed clock differs')
        clocks[state]=q
    need(len(clocks)==14,'All14 actual selected clock rows required')
    nr=read(NATIVE_REVIEW);need(nr['passed']and nr['analysis_complete']and nr['consumed_stats_unchanged'],'Passed actual native scientific source required');consumed.append(stat(NATIVE_REVIEW));sigma={}
    roots=(T/'outputs/c08_h18_as03_n255_r1/native_r1',T/'outputs/c08_h18_rv_radial_window_GPU_r1/native_r1')
    for cs,root in zip(CASES,roots):
        for leaf in('typed22.bin','typed22_layout.csv','clocks.csv'):
            expected=[q for q in nr['consumed']if same(q['path'],root/leaf)];need(expected and all(q==expected[0]for q in expected),'One unchanged native source seal required');consumed.append(bind(expected[0]))
        bundle=u.typed(root,6805,91,consumed)
        for part in PARTS:
            f=bundle['frames'][part];need(bits(f['time'])==bits(clocks[(cs,part)]['time_s']) and np.array_equal(f['Idp'][:,0],bundle['expected']),'Real saved native time/material map differs')
            # This matches ToTSymMatrix3f used by the original CPU force. Soil
            # sigma is certified unchanged by the zero-advance component.
            kk=f['SigmaState_kk'][-N:].astype('<f4').astype(float);ij=f['SigmaState_ij'][-N:].astype('<f4').astype(float)
            sigma[(cs,part)]=np.column_stack((kk[:,0],kk[:,1],kk[:,2],ij[:,0],ij[:,1],ij[:,2]))
    return done,clocks,sigma

def contraction(s,L):
    # Order xx/yy/zz/xy/yz/xz; L is a row-major3x3 and is not assumed symmetric.
    return s[0]*L[0]+s[1]*L[4]+s[2]*L[8]+s[3]*(L[1]+L[3])+s[4]*(L[5]+L[7])+s[5]*(L[2]+L[6])

def analyze(done,clocks,sigma):
    aggregates={(s,r):Aggregate()for s in STATES for r in REGIONS};pending=np.zeros((14,N));work_pending=np.zeros((14,N,12));C_pending=np.zeros((14,N,2,2));members=np.zeros((14,N),dtype=np.uint8);seen=np.zeros((14,N),dtype=bool);focus={};literal=0
    for raw in rows('gradient'):
        q=numeric(raw);state=clock_check(q,clocks);id=int(q['native_id']);need(2060<=id<7060,'Complete soil ID domain required');si=STATE_INDEX[state];j=id-2060;need(not seen[si,j],'Duplicate gradient state/ID');seen[si,j]=True
        need(bits(q['literal_theta_s_1'])==bits(q['fresh_CPU_theta_s_1']),'Exported actual/literal theta bits differ');literal+=1
        # Serialized arithmetic only, not a newly imposed physical tolerance.
        trace=q['Rsigma_xx_Pa_s']+q['Rsigma_yy_Pa_s']+q['Rsigma_zz_Pa_s'];need(bits(trace)==bits(q['Rsigma_trace_Pa_s']),'Actual elastic trace export arithmetic differs')
        g1=0.
        for p in ('fluid','bound'):g1+=q[p+'_corrected_grad_xx_s_1']+q[p+'_corrected_grad_yy_s_1']+q[p+'_corrected_grad_zz_s_1']
        need(bits(g1)==bits(q['corrected_gradient_trace_s_1'])and bits(q['fluid_theta_s_1']+q['bound_theta_s_1'])==bits(q['literal_theta_s_1']),'Source-ordered group arithmetic differs')
        values=dict(G1_minus_theta=q['G1_trace_minus_theta_s_1'],elastic_trace_over3K_minus_theta=q['elastic_trace_over3K_minus_theta_s_1'],fresh_minus_saved_prior_theta=q['fresh_CPU_theta_s_1']-q['saved_prior_stage_theta_s_1'],fresh_theta=q['fresh_CPU_theta_s_1'],G1_trace=g1)
        counter={}
        for p in('fluid','bound'):
            need(q[p+'_theta_donors']+q[p+'_theta_support_rejected']==q[p+'_outer_donors'],'Actual support accounting differs')
            for k in('outer_donors','theta_donors','theta_support_rejected','Fac_float_bits_differ','sum_volume_float_cast_abs_m2','full_vs_tangent_velocity_bits_differ'):counter[p+'_'+k]=q[p+'_'+k]
        mask=1
        if q['z_m']<=NEAR_BED and q['bound_outer_donors']>0:mask|=2
        if q['kappa']>0:mask|=4
        if id in IDS:mask|=8;focus[(state,id)]=dict(q,actual_tau_s=float(clocks[state]['tau_from_actual_release_s']),signed_dterror_s=float(clocks[state]['signed_dterror_s']),saved_step=int(clocks[state]['saved_step']))
        members[si,j]=mask;pending[si,j]=q['G1_trace_minus_theta_s_1'];C_pending[si,j]=((q['C11'],q['C13']),(q['C31'],q['C33']))
        # Keep only per-pass scalar work densities until actual V/n/p join.
        sig=sigma[state][j]
        for passindex,p in enumerate(('fluid','bound')):
            l0=[q[p+'_raw_grad_'+k+'_s_1']for k in('xx','xy','xz','yx','yy','yz','zx','zy','zz')];l1=[q[p+'_corrected_grad_'+k+'_s_1']for k in('xx','xy','xz','yx','yy','yz','zx','zy','zz')];delta=[b-a for a,b in zip(l0,l1)]
            # Four compact per-pass primitives kept separately below.
            if passindex==0:workcache={}
            workcache[p]=(contraction(sig,delta),sum(l1[k]-l0[k]for k in(0,4,8)),sum(l1[k]for k in(0,4,8))-q[p+'_theta_s_1'],contraction(sig,l0),contraction(sig,l1),q[p+'_theta_s_1'])
        # 14x5000x12 doubles: fixed-state expressions, no gradient or native writes.
        work_pending[si,j,:6]=workcache['fluid'];work_pending[si,j,6:]=workcache['bound']
        for bit,r in zip((1,2,4,8),REGIONS):
            if mask&bit:aggregates[(state,r)].observe(values,counter)
    need(literal==70000 and seen.all(),'All70000 actual gradient rows required')
    sv=np.linalg.svd(C_pending,compute_uv=False);cstats={(s,r):dict(max_singular_value=0.,max_finite_condition2=0.,zero_min_singular_values=0)for s in STATES for r in REGIONS}
    for state in STATES:
        si=STATE_INDEX[state]
        for j in range(N):
            largest,smallest=map(float,sv[si,j]);condition=largest/smallest if smallest else None
            for bit,r in zip((1,2,4,8),REGIONS):
                if members[si,j]&bit:
                    a=cstats[(state,r)];a['max_singular_value']=max(a['max_singular_value'],largest)
                    if condition is None:a['zero_min_singular_values']+=1
                    else:a['max_finite_condition2']=max(a['max_finite_condition2'],condition)
            if j+2060 in IDS:focus[(state,j+2060)].update(C_plane_max_singular_value=largest,C_plane_min_singular_value=smallest,C_plane_condition2=condition)
    soilseen=np.zeros_like(seen);soilcount=0
    for raw in rows('soil'):
        q=numeric(raw);state=clock_check(q,clocks);id=int(q['native_id']);need(2060<=id<7060,'Soil ID domain differs');si=STATE_INDEX[state];j=id-2060;need(not soilseen[si,j],'Duplicate actual soil record');soilseen[si,j]=True;soilcount+=1
        need(0<q['n']<1 and q['V']>0,'Actual positive finite ledger weight required')
        gap=(KW/q['n'])*DT*pending[si,j];mask=members[si,j]
        for bit,r in zip((1,2,4,8),REGIONS):
            if mask&bit:
                a=aggregates[(state,r)];a.add_error('one_fixed5us_pressure_gap_shadow_Pa',gap)
                for k,p in enumerate(('fluid','bound')):
                    eff,dtrace,tgap,d0,d1,theta=work_pending[si,j,6*k:6*k+6];we=q['V']*eff;wp=-q['V']*q['p_Pa']*dtrace;wg=q['V']*q['p_Pa']*tgap
                    a.add_work(p,(we,wp,wg,we+wp+wg,q['V']*abs(d0),q['V']*abs(d1),q['V']*abs(q['p_Pa']*theta)))
        if id in IDS:
            f=focus[(state,id)];need(all(bits(q[k])==bits(f[k])for k in('x_m','z_m','p_Pa','P0_Pa','J','kappa')),'Focus primitive join differs');f.update({'soil_'+k:v for k,v in q.items()if k not in('case','part','time_s','completed_step','native_id')});f['one_fixed5us_pressure_gap_shadow_Pa']=gap
    need(soilcount==70000 and soilseen.all(),'All70000 actual soil rows required');history=[]
    for state in STATES:
        for region in REGIONS:
            a=aggregates[(state,region)];q=dict(case=state[0],part=state[1],actual_time_s=float(clocks[state]['time_s']),tau_s=float(clocks[state]['tau_from_actual_release_s']),completed_step=int(clocks[state]['completed_step']),saved_step=int(clocks[state]['saved_step']),signed_dterror_s=float(clocks[state]['signed_dterror_s']),dterror_interval_empty=int(clocks[state]['dterror_interval_empty']),region=region,**a.result(),**{'C_plane_'+k:v for k,v in cstats[(state,region)].items()});q['C_plane_max_condition2']=None if cstats[(state,region)]['zero_min_singular_values']else cstats[(state,region)]['max_finite_condition2'];history.append(q)
    endpoint={};endpointcount=0
    for raw in rows('focus'):
        q=numeric(raw);state=clock_check(q,clocks);id=int(q['native_id']);i,j=int(q['pair_i']),int(q['pair_j']);need(id in(i,j)and i in IDS and j in IDS,'Only actual four-ID pair endpoints required');k=(state,i,j,id);need(k not in endpoint,'Duplicate endpoint');endpoint[k]=q;endpointcount+=1
    pairs=[];pairkeys=set();allowed=set(itertools.combinations(IDS,2))
    for raw in rows('pairs'):
        q=numeric(raw);state=clock_check(q,clocks);i,j=int(q['ID_i']),int(q['ID_j']);need((i,j)in allowed and(state,i,j)not in pairkeys,'Closed actual6pair set differs');pairkeys.add((state,i,j))
        for side,id in(('i',i),('j',j)):
            f=endpoint[(state,i,j,id)];g=focus[(state,id)]
            for k in('p_Pa','J','kappa','total_positive_eigen_sum_Pa','total_nn_Pa','effective_nn_Pa','actual_AS_tensor_nn_Pa'):q[side+'_'+k]=f[k]
            for prefix in('base_','candidate_','delta_'):
                for k in('R_Pa_s','compression','LP','Taylor_pressure','Da','FS_Ace_Lx','chain_pressure','chain_Ace','numeric_residual'):
                    name=prefix+k
                    if 'soil_'+name in g:q[side+'_'+name]=g['soil_'+name]
        pairs.append(q)
    need(endpointcount==168 and len(pairs)==84 and len(pairkeys)==84,'All84 pairs/168 endpoint records required');wallsummary={};wallcount=0
    for raw in rows('walls'):
        q=numeric(raw);state=clock_check(q,clocks);id=int(q['soil_id']);need(id in IDS and q['mode']==1 and 0<=q['sorted_wall_index']<q['NpbOk'],'Only actual defined active-wall scratch required');k=(state,id);a=wallsummary.setdefault(k,dict(rows=0,full_minus_tangent_max_m_s=0.,full_minus_physical_max_m_s=0.,wall_Ace_max_m_s2=0.,NpbOk=q['NpbOk']));need(a['NpbOk']==q['NpbOk'],'Actual state wall ownership differs');a['rows']+=1;wallcount+=1
        a['full_minus_tangent_max_m_s']=max(a['full_minus_tangent_max_m_s'],math.sqrt(sum((q['full_derivative_v'+v]-q['tangent_v'+v])**2 for v in'xyz')))
        a['full_minus_physical_max_m_s']=max(a['full_minus_physical_max_m_s'],math.sqrt(sum((q['full_derivative_v'+v]-q['ghost_physical_v'+v])**2 for v in'xyz')))
        a['wall_Ace_max_m_s2']=max(a['wall_Ace_max_m_s2'],math.sqrt(sum(q['wall_Ace'+v]**2 for v in'xyz')))
    need(wallcount==done['wall_rows'],'Actual wall row coverage differs');wallrows=[]
    for state in STATES:
        for id in IDS:
            a=wallsummary.get((state,id),dict(rows=0,full_minus_tangent_max_m_s=0.,full_minus_physical_max_m_s=0.,wall_Ace_max_m_s2=0.,NpbOk=None));need(a['rows']==int(focus[(state,id)]['bound_outer_donors']),'Focus actual boundary-support rows differ');wallrows.append(dict(case=state[0],part=state[1],native_id=id,**a))
    return history,[focus[(s,id)]for s in STATES for id in IDS],pairs,wallrows,dict(external_exported_theta_bit_rows=literal,internal_Rsigma_component_bit_checks=done['literal_Rsigma_component_bit_checks'],external_Rsigma_bit_reexecution_claimed=False,wall_rows=wallcount)

def plots(history,focus,pairs,prefix):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    colors={'original':'#2166AC','radial':'#D6604D'};files=[];regions=(REGIONS[0],REGIONS[1],REGIONS[3]);titles=('All5000 soil','Current near-bed with wall support','Four fixed material IDs')
    fields=(('G1_minus_theta','G1 trace minus theta [1/s]'),('elastic_trace_over3K_minus_theta','Elastic trace/(3K) minus theta [1/s]'),('fresh_minus_saved_prior_theta','Fresh CPU minus saved prior-stage theta [1/s]'))
    fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained')
    for col,(region,title)in enumerate(zip(regions,titles)):
        for row,(field,ylabel)in enumerate(fields):
            ax=axes[row,col]
            for cs in CASES:
                rr=[q for q in history if q['case']==cs and q['region']==region]
                for suffix,ls in(('_RMS','-'),('_absmax','--')):ax.plot([q['tau_s']for q in rr],[q[field+suffix]for q in rr],color=colors[cs],ls=ls,marker='.',label=cs+' '+suffix[1:])
            ax.set(title=title if row==0 else None,xlabel='Actual saved tau [s]',ylabel=ylabel);ax.grid(alpha=.25);ax.ticklabel_format(axis='y',style='sci',scilimits=(-2,2))
    fig.suptitle('Frozen saved states recomputed on CPU: operator differences and distinct time layers\nSaved theta is a prior native stage, not a current-gradient reference',fontsize=12)
    fig.legend(handles=[Line2D([0],[0],color=colors[c],label=c)for c in CASES]+[Line2D([0],[0],color='.2',ls=s,label=t)for s,t in(('-','RMS'),('--','absolute maximum'))],loc='outside lower center',ncol=4)
    f=Path(str(prefix)+'_operators.png');fig.savefig(f,dpi=175);plt.close(fig);files.append(f)
    fig,axes=plt.subplots(4,4,figsize=(16,12),layout='constrained')
    for col,id in enumerate(IDS):
        for row,(field,scale,label)in enumerate((('p_Pa',.001,'Native p [kPa]'),('kappa',1.,'Cumulative kappa'),('J',1.,'Native J'))):
            ax=axes[row,col]
            for cs in CASES:
                rr=[q for q in focus if q['case']==cs and int(q['native_id'])==id];ax.plot([q['actual_tau_s']for q in rr],[scale*q[field]for q in rr],'.-',color=colors[cs],label=cs)
            ax.set(title='Material ID '+str(id)if row==0 else None,xlabel='Actual saved tau [s]',ylabel=label);ax.grid(alpha=.25)
        ax=axes[3,col]
        for cs in CASES:
            rr=[q for q in focus if q['case']==cs and int(q['native_id'])==id];ax.plot([q['x_m']for q in rr],[q['z_m']for q in rr],'.-',color=colors[cs]);ax.annotate('P28',(rr[0]['x_m'],rr[0]['z_m']),fontsize=7);ax.annotate('P34',(rr[-1]['x_m'],rr[-1]['z_m']),fontsize=7)
        ax.set(xlabel='Actual x [m]',ylabel='Actual z [m]');ax.set_aspect('equal',adjustable='datalim');ax.grid(alpha=.25)
    axes[0,0].legend(fontsize=8);fig.suptitle('Four fixed material IDs: genuine saved trajectory fields\nCPU force recomputations do not advance these points',fontsize=12)
    f=Path(str(prefix)+'_focus.png');fig.savefig(f,dpi=175);plt.close(fig);files.append(f)
    fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained')
    for ax,(i,j)in zip(axes[:2].flat,itertools.combinations(IDS,2)):
        for cs in CASES:
            rr=[q for q in pairs if q['case']==cs and int(q['ID_i'])==i and int(q['ID_j'])==j];ax.plot([q['tau_s']for q in rr],[q['distance_over_dp']for q in rr],'.-',color=colors[cs],label=cs)
        ax.set(title=str(i)+' / '+str(j),xlabel='Actual saved tau [s]',ylabel='Actual pair distance / dp');ax.grid(alpha=.25)
    for ax,region,title in zip(axes[2],regions,titles):
        for cs in CASES:
            rr=[q for q in history if q['case']==cs and q['region']==region]
            for term,ls in(('effective_gradient_correction_work_delta','-'),('pressure_gradient_correction_delta','--'),('coupled_conditional_work_delta',':')):ax.plot([q['tau_s']for q in rr],[q['fluid_'+term+'_signed_W_m']for q in rr],color=colors[cs],ls=ls,marker='.')
        ax.set(title=title+' | fluid pass',xlabel='Actual saved tau [s]',ylabel='Conditional signed work difference [W/m]');ax.grid(alpha=.25);ax.axhline(0,color='.5',lw=.6)
    fig.legend(handles=[Line2D([0],[0],color=colors[c],label=c)for c in CASES]+[Line2D([0],[0],color='.2',ls=s,label=t)for s,t in(('-','effective stress delta'),('--','pressure-gradient delta'),(':','combined conditional delta'))],loc='outside lower center',ncol=3,fontsize=9)
    fig.suptitle('Actual material-pair distances and frozen CPU gradient-field work diagnostics\nWork differences are not actual stress-only Ace power or GPU energy injection',fontsize=12)
    f=Path(str(prefix)+'_pairs_work.png');fig.savefig(f,dpi=175);plt.close(fig);files.append(f)
    return files

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Separate root offline admission required')
    check=L/(TAG+'.check.json');prefix=T/'figures'/TAG;need(not check.exists()and not list(prefix.parent.glob(TAG+'_*')),'Old complete/partial derived outputs protected')
    consumed=[];files=[];result=dict(stage=TAG,passed=False,analysis_complete=False,physical_acceptance=False,solver_invocations=0,native_invocations=0,component_invocations=0,build_invocations=0,SHA_scans=0)
    try:
        consumed=[stat(Path(__file__)),stat(NOTE),stat(Path(u.__file__)),stat(Path(u.core.__file__))];done,clocks,sigma=inputs(consumed)
        history,focus,pairs,walls,proof=analyze(done,clocks,sigma)
        need(all(stat(q['path'])==q for q in consumed),'Bound completed inputs changed during offline review')
        for name,rr in(('history',history),('focus',focus),('pairs',pairs),('wall_summary',walls)):
            f=Path(str(prefix)+'_'+name+'.csv');write_csv(f,rr);files.append(f)
        files+=plots(history,focus,pairs,prefix);need(all(stat(q['path'])==q for q in consumed),'Bound inputs changed while plotting')
        peaks={region:{k:max((q[k]for q in history if q['region']==region and q[k]is not None),default=None)for k in('G1_minus_theta_absmax','elastic_trace_over3K_minus_theta_absmax','one_fixed5us_pressure_gap_shadow_Pa_absmax')}for region in REGIONS}
        result.update(passed=True,analysis_complete=True,source_component=stat(COMPONENT),actual_states=14,actual_soil_rows=70000,actual_gradient_columns=87,history_rows=len(history),unique_focus_rows=len(focus),pair_rows=len(pairs),wall_summary_rows=len(walls),literal_proof=proof,selected_parts=list(PARTS),regions=list(REGIONS),near_bed_definition='current z<=2H_float and actual bound support>0',near_bed_support_height_m=NEAR_BED,nonzero_kappa_is_current_plastic_activity=False,pressure_gap_shadow='(Kw/n)*fixed5us*(G1trace-theta) at frozen current CPU state',pressure_gap_is_trajectory_or_cumulative_bound=False,conditional_work_is_actual_Ace_power_or_GPU_energy=False,wall_pass_is_closed_real_wall_work=False,sigma_used='native double saved effective tensor cast float32 then double; ij=xy,yz,xz',CSV_seals_scope='first author observation after passed component, not retrospectively claimed at tool exit',peak_magnitudes=peaks,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(q)for q in files])
    except Exception as e:result.update(first_failure=str(e),consumed=consumed,partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8')as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
