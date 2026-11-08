"""Saved r5 raw/AS pressure channels and nonlinear AS action; frozen real spectral proxy only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json,math,struct
from pathlib import Path
import numpy as np
import upl_c08_pressure_coeff_r1 as p
import upl_c08_pressure_ace_jac_r1 as ace
from upl_c08_fsmask_r1 import SCHEMA,TYPES
from matplotlib.colors import SymLogNorm
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_r5_pressure_probe_r2';PREFIX=T/'figures'/TAG;CHECK=L/(TAG+'.check.json')
OUT=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out';NATIVE=OUT/'native';RUN=L/'upl_c08_formal_psi0_r5_r1.run.json'
PARTS=(60,61,62,63,64,69);IDS=(5809,4956,4959);need,read,stat=p.need,p.read,p.stat
AS_EPS=float(np.float32(.2));AS_EXP=np.float32(2.55);DP_GPU=np.float32(.04)
WDP=np.float32(p.g.cubic(float(np.float32(DP_GPU*DP_GPU)))[0]);INVWDP=np.float32(np.float32(1)/WDP)

def bind(entry):need(stat(Path(entry['path']))==entry,'Closed file changed: '+entry['path']);return entry
def table(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write(leaf,rows):
    need(rows,'Empty derived '+leaf+' table');path=Path(str(PREFIX)+'_'+leaf+'.csv');ace.write(path,rows);return path

def vector_action(row,pressure):
    return sum((value*float(pressure[key]) for key,value in row.items()),np.zeros(2))

class SpectralAS:
    """Real spectral surrogate at source-float total stress; derivative ignores quantizing casts."""
    def __init__(self,cloud,frame,raw):
        self.c=cloud;self.frame=frame;self.raw=raw;self.rho=raw.rho;self.cache={};self.row_cache={};self.nonlinear={};self.row_nodes={};self.used=set();self.native_action={}

    def tensors(self,i):
        if i not in self.cache:
            diag=self.frame['SigmaState_kk'][i].astype(float);xy,yz,xz=self.frame['SigmaState_ij'][i].astype(float);pw=float(self.c.p[i])
            original=np.array(((diag[0]-pw,xy,xz),(xy,diag[1]-pw,yz),(xz,yz,diag[2]-pw)));S=original.astype(np.float32).astype(float)
            values,U=np.linalg.eigh(S);positive=values>0;R=-AS_EPS*((U*np.maximum(values,0.))@U.T);D=AS_EPS*((U*positive.astype(float))@U.T)
            need(np.isfinite(S).all() and np.isfinite(values).all() and np.isfinite(R).all() and np.isfinite(D).all(),'Nonfinite spectral AS proxy')
            self.cache[i]=dict(values=values,R=R,D=D,rank=int(positive.sum()),zeros=int(np.count_nonzero(values==0)),minabs=float(np.min(np.abs(values))),total_stress_input_float32_max_delta_Pa=float(np.abs(original-S).max()),R_output_float32_cast_max_delta_Pa=float(np.abs(R-R.astype(np.float32).astype(float)).max()))
        return self.cache[i]

    def row(self,i):
        if i not in self.row_cache:
            rawrow=self.raw.row(i) # Original complete float-cutoff and WallStencil guard, before any AS pair is used.
            ti=self.tensors(i);row={i:np.zeros(2)};nonlinear=np.zeros(2);nodes={i};rho=float(self.rho[i]);xz=np.ix_([0,2],[0,2])
            for j in rawrow:
                if j==i:continue
                delta=np.asarray(self.c.x[i]-self.c.x[j],dtype=np.float32);rr2=np.float32(delta[0]*delta[0]+delta[1]*delta[1]);wab,fac=p.g.cubic(float(rr2));grad=np.asarray(np.float32(fac)*delta,dtype=np.float32).astype(float)
                ratio=np.float32(np.float32(wab)*INVWDP);factor=float(np.float32(np.power(ratio,AS_EXP))) if ratio>0 else 0.
                if factor==0:continue
                tj=self.tensors(j);nodes.add(int(j));weight=float(self.c.V[j])/rho*factor
                row[i]+=weight*(ti['D'][xz]@grad);row[int(j)]=row.get(int(j),np.zeros(2))+weight*(tj['D'][xz]@grad)
                nonlinear+=weight*((ti['R'][xz]+tj['R'][xz])@grad)
            need(all(np.isfinite(v).all() for v in row.values()) and np.isfinite(nonlinear).all(),'Nonfinite AS row/action')
            self.row_cache[i]=row;self.nonlinear[i]=nonlinear;self.row_nodes[i]=nodes;self.native_action[i]=vector_action(row,self.c.p)
        self.used.update(self.row_nodes[i]);return self.row_cache[i]

    def pressure_acceleration(self,i):return vector_action(self.row(i),self.c.p) # Jacobian*p, explicitly NOT nonlinear AS acceleration.
    def nonlinear_acceleration(self,i):self.row(i);return self.nonlinear[i]

class RawPlusASJac:
    def __init__(self,raw,art):self.raw=raw;self.art=art;self.rho=raw.rho;self.c=raw.c;self.cache={};self.native_action={}
    def row(self,i):
        ar=self.art.row(i)
        if i not in self.cache:
            row={}
            for source in (self.raw.row(i),ar):
                for key,value in source.items():row[key]=row.get(key,np.zeros(2))+value
            self.cache[i]=row;self.native_action[i]=self.raw.pressure_acceleration(i)+self.art.pressure_acceleration(i)
        return self.cache[i]
    def pressure_acceleration(self,i):return vector_action(self.row(i),self.c.p)

def nonlinear_AS_rate(cloud,art,i,desc):
    ai=art.nonlinear_acceleration(i);ci=cloud.correction(i)[0];div=0.
    for j,delta,rr2,grad in cloud.edges(i,False):div+=float(cloud.V[j]*((art.nonlinear_acceleration(int(j))-ai)@(ci@grad)))
    lx=np.array([desc['lx_x'],desc['lx_z']]);gJ=np.array([desc['reconstructed_gradJ_x'],desc['reconstructed_gradJ_z']]);pref=p.KW/(float(cloud.n[i])*p.GAMMA)*1000.;ki=float(cloud.k[i]);kp=ki/(p.SOLID0*p.CK)
    values=dict(via_divAce=pref*ki*div,via_FS_Ace_lx=pref*ki*float(lx@ai) if int(cloud.fs[i]) in (2,3) else 0.,via_chain_Ace=pref*kp*float(gJ@ai));values['total']=sum(values.values());return values

def load():
    # Same formal bytes as bundle(), with all scalar fields explicitly (6805,1) for the frozen Cloud API.
    before=[stat(q) for q in (Path(__file__),T/'notes'/(TAG+'.md'),Path(p.__file__),Path(ace.__file__),Path(p.w.__file__),Path(p.g.__file__),T/'support/upl_c08_fsmask_r1.py',RUN,OUT/'postprocess_r5.json',OUT/'logs/native.call.json')]
    r,post,call=read(RUN),read(OUT/'postprocess_r5.json'),read(OUT/'logs/native.call.json')
    need(r['passed'] and r['solver_completed'] and r['postprocess_completed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==5200000 and r['saved_frames']==300 and r['consumed_stats_unchanged'],'Closed normal formal solver/postprocessing required')
    before.append(bind(r['actual_call']));actual=read(Path(r['actual_call']['path']));need(actual['actual_wrapper_Popen_wait_exit']==actual['actual_wrapper_Win32_exit']==0 and not actual['ownership_errors'] and len([q for q in actual['children'] if q['role']=='solver' and q['actual_Win32_exit']==0])==1,'Actual owned root solver closure differs')
    need(post['passed'] and post['group']=='psi0' and post['backend_from_Run_csv']=='GPU' and post['global_steps']==5200000 and post['saved_frames']==300 and post['native_completed'] and post['KeepBedOverlap'] and post['actual_native_IDs']==6805 and not post['physical_acceptance'],'Actual formal native/post scope differs')
    need(call['passed'] and call['actual_exit']==call['actual_Win32_exit']==0,'Actual unique native reader exit differs')
    for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv','plane_gaps.csv','bedkeep_metadata.json'):
        path=NATIVE/leaf;before.append(bind(next(e for e in call['outputs'] if Path(e['path']).samefile(path))))
    before.extend(bind(post[k]) for k in ('native_completion','bedkeep_metadata'));d=read(NATIVE/'completion.json');m=read(NATIVE/'bedkeep_metadata.json')
    counts=dict(samples=300,completed_steps=5200000,typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=1500000,fixed_marker_checks=541500,P0_bits_checks=2041500,rho_cache_bits_checks=1500000,kappa_nondecreasing_from_PRE_checks=1500000,nonempty_signed_intervals=300,plane_gap_checks=3000000)
    need(d['passed'] and d['stage']=='upl_c08_bedkeep_formal_native_r1' and all(d[k]==v for k,v in counts.items()) and d['completed_runtime_Run_csv_checked'] and d['saved_steps_checked_against_formal_profile'] and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original300-frame native numerical coverage differs')
    need(m['passed'] and m['stage']=='upl_c08_bedkeep_formal_native_r1.metadata' and m['samples']==m['keep_policy_headers']==m['AS_active_true_headers']==300 and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==AS_EPS and m['AS_exponent_float_reference']==float(AS_EXP),'Original keep/AS header coverage differs')
    layout=table(NATIVE/'typed22_layout.csv');need(len(layout)==22,'Exactly22 fields required');fields=[('time','<f8')]
    for row,(name,kind,width) in zip(layout,SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,TYPES[kind].itemsize*width),'Original formal field schema differs');fields.append((name,TYPES[kind],(6805,width)))
    dtype=np.dtype(fields);need(dtype.itemsize==8+6805*212,'Explicit formal record stride differs')
    with (NATIVE/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(6805,22,300),'Actual300/6805/22 header differs; no rewrite')
    need((NATIVE/'typed22.bin').stat().st_size==12+300*dtype.itemsize,'Actual formal payload length differs');a=np.memmap(NATIVE/'typed22.bin',dtype=dtype,offset=12,mode='r',shape=(300,));clocks=table(NATIVE/'clocks.csv');need(len(clocks)==300,'Actual300 clocks required')
    expected=np.sort(np.r_[np.arange(1800),(1800,1852,1904,1956,2008),np.arange(2060,7060)]).astype('uint32')
    for part,x in enumerate(a):need(np.array_equal(x['Idp'][:,0],expected) and float(clocks[part]['time_s'])==x['time'] and int(clocks[part]['completed_step'])==4000000+(part+1)*4000 and int(clocks[part]['completed_step'])==int(clocks[part]['saved_step'])+1 and clocks[part]['dterror_interval_empty']=='0' and np.isfinite(float(clocks[part]['signed_dterror_s'])) and float(clocks[part]['signed_dterror_s'])<=1e-14,'Original IDs/actual saved clock/signed diagnostic differs')
    need(float(p.g.H)==float(p.H) and p.g.R2==p.R2 and p.g.LOWER==p.LOWER and p.g.VOL0==p.V0,'Frozen Cubic/helper constants differ');return a,d,clocks,before

def state(frame,part,clock,source,identity):
    ids=frame['Idp'][:,0];hits=np.flatnonzero(ids==identity);need(len(hits)==1,'Focus native ID missing');i=int(hits[0]);v=frame['Vel'][i].astype(float)
    row=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-source,completed_step=int(clock['completed_step']),native_ID=identity,x_m=float(frame['Posd'][i,0]),y_m=float(frame['Posd'][i,1]),z_m=float(frame['Posd'][i,2]),vx_m_s=float(v[0]),vy_m_s=float(v[1]),vz_m_s=float(v[2]),speed_m_s=float(np.linalg.norm(v)),FSType=int(frame['FSType'][i,0]))
    for key,field in (('p_Pa','PorePress'),('P0_Pa','PorePress0'),('native_excess_Pa','ExcessPorePress'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho_kg_m3','PoroMixtureDensity'),('k_m_s','PoroHydraulicConductivity'),('kappa','Kplastic'),('saved_last_stage_theta_per_s','PoroThetaLastStage')):row[key]=float(frame[field][i,0])
    for j,name in enumerate(('xx','yy','zz','xy','yz','xz')):row['sigmaeff_'+name+'_Pa']=float(np.r_[frame['SigmaState_kk'][i],frame['SigmaState_ij'][i]][j])
    return i,row

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline probe');need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial probe protected')
    data,d,clock,before=load();states=[];rows=[];pairs=[];jacrows=[];accelerations=[];local=[];scope=[];nonlinear_rows=[];spectra=[]
    for part,frame in enumerate(data):
        for identity in IDS:states.append(state(frame,part,clock[part],d['source_actual_time_s'],identity)[1])
    for part in PARTS:
        print('R5_PRESSURE_PROBE_PART',part,flush=True);frame=data[part];cloud=p.Cloud(frame);mechanical=ace.Mechanical(cloud,frame);art=SpectralAS(cloud,frame,mechanical);augmented=RawPlusASJac(mechanical,art)
        for identity in IDS:
            i,base=state(frame,part,clock[part],d['source_actual_time_s'],identity);soil=cloud.ids>=2060;distance=np.linalg.norm(cloud.x-cloud.x[i],axis=1);others=soil&(cloud.ids!=identity);around=np.flatnonzero(soil&(distance<=2*p.R));near=around[distance[around]<=p.R]
            base.update(nearest_other_soil_distance_m=float(distance[others].min()),soil_within_R_including_self=int(len(near)),FS23_within_R_including_self=int(np.count_nonzero(np.isin(cloud.fs[near],(2,3)))),soil_within_2R_including_self=int(len(around)),nearest_fixed_B_observed_m=float(cloud.walltree.query(cloud.x[i])[0]))
            for j in around:
                _,q=state(frame,part,clock[part],d['source_actual_time_s'],int(cloud.ids[j]));q.update(receiver_native_ID=identity,distance_from_receiver_m=float(distance[j]))
                try:
                    c=cloud.correction(int(j));q.update(C_scope='complete_fluid_moment_stencil',C_moment_det=float(c[1]),C_moment_condition=float(c[2]) if math.isfinite(c[2]) else None,C_moment_min_symmetric_eigenvalue=float(c[3]))
                except p.WallStencil as error:q.update(C_scope='not_evaluated_original_WallStencil:'+str(error),C_moment_det=None,C_moment_condition=None,C_moment_min_symmetric_eigenvalue=None)
                local.append(q)
            try:
                art.used=set();jj,raw,taylor,chain,current,desc=cloud.coefficients(i);channels,first,composite_desc=ace.probe(cloud,mechanical,i);augchannels,augfirst,augdesc=ace.probe(cloud,augmented,i);asprobe,asfirst,asdesc=ace.probe(cloud,art,i);need(first==augfirst==asfirst,'AS added a different first-hop stencil')
            except p.WallStencil as error:
                scope.append(dict(**base,status='not_evaluated_original_WallStencil_scope',reason=str(error)));continue
            scope.append(dict(**base,status='evaluated_fluid_only_saved_geometry_proxy',reason=''))
            ci=cloud.correction(i)[0];gp=sum((cloud.V[j]*(cloud.p[j]-cloud.p[i])*(ci@grad) for j,delta,rr2,grad in cloud.edges(i,False)),np.zeros(2));lx=np.array([desc['lx_x'],desc['lx_z']]);ai=mechanical.pressure_acceleration(i);pref=p.KW/(float(cloud.n[i])*p.GAMMA);ki=float(cloud.k[i])
            switch={i:float(taylor.sum())}
            for j,value in zip(jj,taylor):ace.add(switch,int(j),-value)
            ace.dot_row(switch,mechanical.row(i),pref*1000.*ki*lx);channels['FS_switch_conditional_pressure_only']=switch
            composite_desc.update(conditional_FS_switch_lap_pressure_only_Pa_m2=float((gp+1000.*ai)@lx),conditional_FS_switch_rate_pressure_only_Pa_s=pref*ki*float((gp+1000.*ai)@lx),conditional_FS_switch_expansion_roundoff_Pa_s=ace.action(switch,cloud.p)-pref*ki*float((gp+1000.*ai)@lx))
            aug_switch=ace.combine(switch);ace.dot_row(aug_switch,art.row(i),pref*1000.*ki*lx);augchannels['FS_switch_conditional_pressure_only']=aug_switch
            aschannels={key:asprobe[key] for key in ('via_divAce','via_FS_Ace_lx','via_chain_Ace')};as_switch={};ace.dot_row(as_switch,art.row(i),pref*1000.*ki*lx);aschannels['FS_switch_conditional_pressure_only']=as_switch
            aschannels['ASJac_total']=ace.combine(*(aschannels[key] for key in ('via_divAce','via_FS_Ace_lx','via_chain_Ace')))
            nonlin=nonlinear_AS_rate(cloud,art,i,desc);asai=art.nonlinear_acceleration(i);used=sorted(art.used);need(used,'Empty AS spectral contributor neighborhood');minabs=min(art.tensors(j)['minabs'] for j in used);minid=min(int(cloud.ids[j]) for j in used if art.tensors(j)['minabs']==minabs);receiver=art.tensors(i)
            asinfo=dict(AS_receiver_positive_rank=receiver['rank'],AS_receiver_min_abs_eigenvalue_Pa=receiver['minabs'],AS_neighborhood_nodes=len(used),AS_neighborhood_min_abs_eigenvalue_Pa=minabs,AS_neighborhood_min_abs_eigenvalue_native_ID=minid,AS_neighborhood_exact_zero_eigenvalues=sum(art.tensors(j)['zeros'] for j in used),AS_receiver_lambda0_Pa=float(receiver['values'][0]),AS_receiver_lambda1_Pa=float(receiver['values'][1]),AS_receiver_lambda2_Pa=float(receiver['values'][2]))
            for rank in range(4):asinfo['AS_neighborhood_rank'+str(rank)+'_nodes']=sum(art.tensors(j)['rank']==rank for j in used)
            composite_desc.update(asinfo);augdesc.update(asinfo)
            raw_rate=ace.action(channels['composite_pressure_channel'],cloud.p);as_jac_rate=ace.action(aschannels['ASJac_total'],cloud.p)
            nonlinear_rows.append(dict(**base,**asinfo,AS_nonlinear_via_divAce_Pa_s=nonlin['via_divAce'],AS_nonlinear_via_FS_Ace_lx_Pa_s=nonlin['via_FS_Ace_lx'],AS_nonlinear_via_chain_Ace_Pa_s=nonlin['via_chain_Ace'],AS_nonlinear_total_proxy_Pa_s=nonlin['total'],ASJac_times_saved_p_Pa_s=as_jac_rate,ASJac_times_p_minus_nonlinear_AS_Pa_s=as_jac_rate-nonlin['total'],raw_pressure_composite_Pa_s=raw_rate,raw_pressure_plus_nonlinear_AS_proxy_Pa_s=raw_rate+nonlin['total'],raw_pressure_plus_ASJac_times_p_Pa_s=ace.action(augchannels['composite_pressure_channel'],cloud.p),conditional_FS_switch_lap_raw_plus_nonlinear_AS_Pa_m2=float((gp+1000.*(ai+asai))@lx),nonlinear_AS_is_not_Jacobian_times_p=True,not_actual_finished_rate=True))
            variants={'raw_LP':raw,'Taylor_increment':taylor,'kgrad_increment':chain,'Lstar':raw+taylor,'raw_plus_kgrad':raw+chain,'actual_saved_FS_choice':current}
            for label,coeff in variants.items():
                row={i:-float(coeff.sum())}
                for j,v in zip(jj,coeff):ace.add(row,int(j),v)
                rows.append(dict(**base,channel='direct_pressure',variant=label,**desc,**ace.metrics(row,i,cloud.p)))
            for index,j in enumerate(jj):
                cj=cloud.correction(int(j));pairs.append(dict(**base,neighbor_native_ID=int(cloud.ids[j]),neighbor_FSType=int(cloud.fs[j]),neighbor_p_Pa=float(cloud.p[j]),neighbor_J=float(cloud.J[j]),neighbor_kappa=float(frame['Kplastic'][j,0]),neighbor_saved_last_stage_theta_per_s=float(frame['PoroThetaLastStage'][j,0]),distance_m=float(distance[j]),neighbor_C_det=float(cj[1]),neighbor_C_condition=float(cj[2]) if math.isfinite(cj[2]) else None,a_raw_LP_per_s=float(raw[index]),a_Taylor_increment_per_s=float(taylor[index]),a_kgrad_increment_per_s=float(chain[index]),a_actual_saved_FS_choice_per_s=float(current[index])))
            for label,row in channels.items():rows.append(dict(**base,channel='pressure_to_raw_mechanical_to_Darcy',variant=label,**composite_desc,**ace.metrics(row,i,cloud.p)))
            for label,row in augchannels.items():rows.append(dict(**base,channel='pressure_to_raw_plus_ASJac_to_Darcy',variant=label,**augdesc,**ace.metrics(row,i,cloud.p)))
            for label,row in aschannels.items():rows.append(dict(**base,channel='ASJac_only_to_Darcy',variant=label,**augdesc,**ace.metrics(row,i,cloud.p)))
            for j in sorted(set(channels['composite_pressure_channel'])|set(augchannels['composite_pressure_channel'])):
                q=dict(**base,pressure_node_native_ID=int(cloud.ids[j]),hop=0 if j==i else (1 if j in first else 2),pressure_node_x_m=float(cloud.x[j,0]),pressure_node_z_m=float(cloud.x[j,1]),pressure_node_FSType=int(cloud.fs[j]),pressure_node_p_Pa=float(cloud.p[j]));q.update({key+'_dRate_dp_per_s':float(value.get(j,0.)) for key,value in channels.items()});q.update({'raw_plus_ASJac_'+key+'_dRate_dp_per_s':float(value.get(j,0.)) for key,value in augchannels.items()});q.update({'ASJac_only_'+key+'_dRate_dp_per_s':float(value.get(j,0.)) for key,value in aschannels.items()});jacrows.append(q)
            for j in sorted(first):
                a=mechanical.pressure_acceleration(j);an=art.nonlinear_acceleration(j);aj=art.pressure_acceleration(j);accelerations.append(dict(**base,acceleration_target_native_ID=int(cloud.ids[j]),pressure_only_raw_Ace_x_m_s2=float(a[0]),pressure_only_raw_Ace_z_m_s2=float(a[1]),AS_nonlinear_spectral_proxy_Ace_x_m_s2=float(an[0]),AS_nonlinear_spectral_proxy_Ace_z_m_s2=float(an[1]),ASJac_times_saved_p_Ace_x_m_s2=float(aj[0]),ASJac_times_saved_p_Ace_z_m_s2=float(aj[1]),raw_pressure_plus_nonlinear_AS_Ace_x_m_s2=float(a[0]+an[0]),raw_pressure_plus_nonlinear_AS_Ace_z_m_s2=float(a[1]+an[1]),complete_mechanical_stencil_nonself_nodes=len(mechanical.row(j))-1,not_actual_finished_Ace=True))
        for j,value in sorted(art.cache.items()):
            q=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-d['source_actual_time_s'],native_ID=int(cloud.ids[j]),x_m=float(cloud.x[j,0]),z_m=float(cloud.x[j,1]),p_Pa=float(cloud.p[j]),positive_rank=value['rank'],exact_zero_eigenvalues=value['zeros'],min_abs_eigenvalue_Pa=value['minabs'],total_stress_input_float32_max_delta_Pa=value['total_stress_input_float32_max_delta_Pa'],R_output_float32_cast_max_delta_Pa=value['R_output_float32_cast_max_delta_Pa'])
            for k in range(3):q['lambda'+str(k)+'_Pa']=float(value['values'][k])
            for label,tensor in (('Rraw_Pa',value['R']),('dR_dp',value['D'])):
                for name,(a,b) in dict(xx=(0,0),yy=(1,1),zz=(2,2),xy=(0,1),yz=(1,2),xz=(0,2)).items():q[label+'_'+name]=float(tensor[a,b])
            spectra.append(q)
    files=[write('states_all300',states),write('scope',scope),write('local_points',local)]
    for leaf,values in (('rows',rows),('pairs',pairs),('mechanical_coefficients',jacrows),('pressure_Ace',accelerations)):
        if values:files.append(write(leaf,values))
    if nonlinear_rows:files.append(write('AS_nonlinear_vs_Jacobian',nonlinear_rows))
    if spectra:files.append(write('AS_spectra',spectra))
    plt.rcParams.update({'font.size':8,'figure.dpi':170});fig,axs=plt.subplots(3,2,figsize=(13,11),layout='constrained')
    for r,identity in enumerate(IDS):
        rr=[q for q in states if q['native_ID']==identity]
        for col,selected in ((0,rr),(1,[q for q in rr if 59<=q['part']<=69])):
            ax=axs[r,col];x=[q['tau_s'] for q in selected];y=[q['p_Pa']*.001 for q in selected];ax.plot(x,y,c='C0',lw=1,label='Actual total p');fs=np.array([q['FSType'] in (2,3) for q in selected]);ax.scatter(np.array(x)[fs],np.array(y)[fs],marker='^',c='C1',s=20,label='Saved FS2/3');ax.set_yscale('symlog',linthresh=.1);ax.set(title='Native '+str(identity)+(' all300 states' if col==0 else ' all saved parts59..69'),xlabel='Actual time since source PRE [s]',ylabel='Native p [kPa]');ax.grid(alpha=.25);ax.legend(fontsize=7)
    fig.suptitle('Unclipped raw receiver pressure; symlog display only, no interpolation; saved FS is not a substage replay');path=Path(str(PREFIX)+'_pressure_history.png');fig.savefig(path);plt.close(fig);files.append(path)
    fig,axs=plt.subplots(3,2,figsize=(14,11),layout='constrained')
    for r,identity in enumerate(IDS):
        for col,(channel,variants) in enumerate((('direct_pressure',('raw_LP','Taylor_increment','kgrad_increment','actual_saved_FS_choice')),('pressure_to_raw_mechanical_to_Darcy',('direct_pressure','via_divAce','via_FS_Ace_lx','via_chain_Ace','composite_pressure_channel','FS_switch_conditional_pressure_only')))):
            ax=axs[r,col]
            if col==0:
                for variant in variants:
                    rr=[q for q in rows if q['native_ID']==identity and q['channel']==channel and q['variant']==variant];ax.plot([q['tau_s'] for q in rr],[q['native_p_channel_contribution_Pa_s'] for q in rr],marker='o',ms=3,label=variant)
            else:
                for provider,variant,label in (('pressure_to_raw_mechanical_to_Darcy','composite_pressure_channel','Raw-only Jacobian*p'),('pressure_to_raw_plus_ASJac_to_Darcy','composite_pressure_channel','Raw+AS Jacobian*p'),('ASJac_only_to_Darcy','ASJac_total','AS-only Jacobian*p')):
                    rr=[q for q in rows if q['native_ID']==identity and q['channel']==provider and q['variant']==variant];ax.plot([q['tau_s'] for q in rr],[q['native_p_channel_contribution_Pa_s'] for q in rr],marker='o',ms=3,label=label)
                rr=[q for q in nonlinear_rows if q['native_ID']==identity];ax.plot([q['tau_s'] for q in rr],[q['AS_nonlinear_total_proxy_Pa_s'] for q in rr],marker='x',ms=4,label='AS nonlinear current action')
            ax.set_yscale('symlog',linthresh=1);ax.set(title=str(identity)+' '+('direct pressure decomposition' if col==0 else 'AS nonlinear action differs from Jacobian*p'),xlabel='Actual saved time since PRE [s]',ylabel='Frozen-channel action [Pa/s]');ax.grid(alpha=.25);ax.legend(fontsize=6)
    fig.suptitle('Frozen real spectral AS pressure derivative included; not measured dp/dt; AV/stress/velocity/theta evolution excluded');path=Path(str(PREFIX)+'_channels.png');fig.savefig(path);plt.close(fig);files.append(path)
    low=min(q['p_Pa'] for q in local)*.001;high=max(q['p_Pa'] for q in local)*.001;norm=SymLogNorm(linthresh=.1,vmin=low,vmax=high);fig,axs=plt.subplots(3,6,figsize=(23,11),layout='constrained');mappable=None
    for r,identity in enumerate(IDS):
        for col,part in enumerate(PARTS):
            ax=axs[r,col];rr=[q for q in local if q['receiver_native_ID']==identity and q['part']==part];center=next(q for q in states if q['native_ID']==identity and q['part']==part)
            for surface,marker,label in ((False,'o','Saved FS0/other'),(True,'^','Saved FS2/3')):
                pick=[q for q in rr if (q['FSType'] in (2,3))==surface]
                if pick:mappable=ax.scatter([q['x_m'] for q in pick],[q['z_m'] for q in pick],c=[q['p_Pa']*.001 for q in pick],norm=norm,cmap='RdBu_r',marker=marker,s=16,edgecolors='black',linewidths=.2,label=label)
            ax.scatter([center['x_m']],[center['z_m']],marker='*',s=100,c='gold',edgecolors='black',label='Receiver '+str(identity));ax.set(title='part%d tau=%.6f FS%d'%(part,center['tau_s'],center['FSType']),xlabel='Native x [m]',ylabel='Native z [m]',aspect='equal');ax.legend(fontsize=5);ax.grid(alpha=.2)
    fig.colorbar(mappable,ax=axs.ravel().tolist(),label='Raw native pressure [kPa]; complete shared local range',shrink=.7);fig.suptitle('Every real soil point within2R; common signed symlog scale, no clipping/smoothing; matrices use complete original stencils');path=Path(str(PREFIX)+'_local.png');fig.savefig(path);plt.close(fig);files.append(path)
    need(all(stat(Path(q['path']))==q for q in before),'Closed native exports or frozen helpers changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,selected_parts=list(PARTS),selected_native_IDs=list(IDS),receiver_cases=18,evaluated_receivers=sum(q['status']=='evaluated_fluid_only_saved_geometry_proxy' for q in scope),not_evaluated_receivers=sum(q['status']!='evaluated_fluid_only_saved_geometry_proxy' for q in scope),native_view='Literal300/6805/22 records, scalar shape(6805,1), same original bytes as formal bundle',all300_receiver_states_retained=True,actual_saved_FS_not_unsaved_stage_classification=True,saved_theta_is_last_stage_observation_not_pressure_rate_replay=True,all_original_WallStencil_guards_kept=True,no_fixed_source_fabricated_or_omitted=True,mechanical_complete_two_hop_stencils=True,mechanical_pressure_self_terms_kept=True,raw_only_channels_retained=True,AS1_pressure_dependent_spectral_real_derivative_included=True,AS_nonlinear_current_action_separate_from_Jacobian_times_pressure=True,AS_epsilon_float=AS_EPS,AS_exponent_float=float(AS_EXP),AS_reference_dp_float_m=float(DP_GPU),AS_Wdp_float=float(WDP),AS_total_stress_input='native double sigmaeff minus native p then float32; eigh in float64',AS_output_eigen_or_quantizing_cast_derivatives_are_not_CUDA_Jacobian_bits=True,AS_zero_eigenvalue_policy='lambda>0 projector; exact zero excluded, nondifferentiable point reported without tolerance',AS_spectral_neighborhood_summaries=[{k:v for k,v in q.items() if k in ('part','time_s','tau_s','native_ID') or k.startswith('AS_receiver_') or k.startswith('AS_neighborhood_')} for q in nonlinear_rows],artificial_viscosity_derivative_included=False,effective_stress_velocity_J_theta_evolution_included=False,actual_finished_Ace_or_rate_replayed=False,packed_GPU_positions_or_FMA_bit_replay=False,global_matrix_spectrum_or_time_integration=False,negative_row_coefficient_not_global_instability_or_causation_proof=True,symlog_thresholds_are_display_only=True,no_clipping_fitting_interpolation_or_new_physics_gate=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,files=[stat(q) for q in files])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('R5_PRESSURE_PROBE_READY',CHECK,flush=True)

if __name__=='__main__':main()
