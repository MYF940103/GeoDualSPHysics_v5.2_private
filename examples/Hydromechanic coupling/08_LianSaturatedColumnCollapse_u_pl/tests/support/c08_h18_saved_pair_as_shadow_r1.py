"""Two saved material IDs: tensor/AS source-form shadows only, never force replay."""
import argparse,csv,math,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import c08_h18_storage_review_r2 as core
T,L=core.T,core.L
need,read,stat,bind,same,bits=core.need,core.read,core.stat,core.bind,core.same,core.bits
TAG='c08_h18_saved_pair_as_shadow_r1';SCRIPT=Path(__file__).resolve();NOTE=T/'notes'/(TAG+'.md');GATE=L/'c08_h18_lstar_window_review_r1.check.json';CHECK=L/(TAG+'.check.json');CSV=T/'figures'/(TAG+'.csv');PNG=T/'figures'/(TAG+'.png')
PAIR=(6817,6866);CASES=(('Original pair-C/Eta','c08_h18_as03_n255_r1'),('Receiver-C/bare','c08_h18_lstar_window_GPU_r1'));F=np.float32
import c08_h18_wend_matrix_r1 as io

def seal(g,path,consumed):
    q=[s for s in(*g['consumed'],*g['files'])if same(s['path'],path)];need(q and all(s==q[0]for s in q),'One existing unambiguous seal required: '+str(path));consumed.append(bind(q[0]));return q[0]
def tensor(diag,off):
    a,b,c=map(float,off);return np.array(((diag[0],a,c),(a,diag[1],b),(c,b,diag[2])),dtype=float)
def wab(rr,h,aw):
    q=F(F(np.sqrt(F(rr)))/F(h));t=F(F(1)-F(F(.5)*q));t2=F(t*t);qq=F(F(q+q)+F(1));return F(F(F(aw*qq)*t2)*t2)
def endpoint(fr,index,n,eps,row,suffix):
    sig=tensor(fr['SigmaState_kk'][index],fr['SigmaState_ij'][index]);p=float(fr['PorePress'][index,0]);total=sig-p*np.eye(3);asinput=total.astype('f4').astype(float);lam,Q=np.linalg.eigh(asinput);positive=(Q*np.maximum(lam,0))@Q.T;R=-eps*positive
    for name,key in(('p_Pa','PorePress'),('P0_Pa','PorePress0'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('V_m2','PoroCurrentVolume'),('rho_mix_kg_m3','PoroMixtureDensity'),('kappa','Kplastic'),('FS','FSType')):row[name+suffix]=float(fr[key][index,0])
    for name,key in(('x_m','Posd'),('v_m_s','Vel')):
        for j,axis in enumerate('xyz'):row[name+'_'+axis+suffix]=float(fr[key][index,j])
    for name,a in(('eff',sig),('total',total)):
        for key,(i,j)in zip(('xx','yy','zz','xy','yz','xz'),((0,0),(1,1),(2,2),(0,1),(1,2),(0,2))):row[name+'_'+key+'_Pa'+suffix]=float(a[i,j])
    row.update({k+suffix:v for k,v in dict(lambda_eff_max_Pa=float(np.linalg.eigvalsh(sig).max()),lambda_total_max_Pa=float(np.linalg.eigvalsh(total).max()),lambda_float_total_max_Pa=float(lam.max()),AS_input_cast_absmax_Pa=float(np.abs(asinput-total).max()),eff_nn_Pa=float(n@sig@n)if n is not None else None,total_nn_Pa=float(n@total@n)if n is not None else None,positive_float_total_nn_Pa=float(n@positive@n)if n is not None else None,R_numpy_nn_Pa=float(n@R@n)if n is not None else None).items()});return sig.astype('f4').astype(float)-p*np.eye(3),R

def collect(g,consumed):
    cohort=next(q for q in g['files']if Path(q['path']).name=='c08_h18_lstar_window_review_r1_cohorts.csv');consumed.append(bind(cohort));initial={int(q['native_id']):q for q in core.table(cohort['path'])if int(q['native_id'])in PAIR};need(set(initial)==set(PAIR),'Actual original selected material IDs required');rows=[];common=None;archive=None
    for case,tag in CASES:
        rp=L/(tag+'.run.json');seal(g,rp,consumed);run=read(rp);need(run['passed']and run['solver_completed']and run['consumed_stats_unchanged']and run['saved_frames']==91 and run['actual_steps']==2180000,'Actual retained91 run required');nd=bind(run['source_native']);source=read(nd['path']);consumed.append(nd)
        npth=L/(tag+'.native_r1.check.json')if tag.startswith('c08_h18_lstar')else L/'c08_h18_as03_n255_native_r1.check.json';seal(g,npth,consumed);native=read(npth);need(native['passed']and native['consumed_stats_unchanged']and native['reader_invocations']==1,'Actual unique native required');ds=core.entry(native,'native_completion');ms=core.entry(native,'metadata');consumed.extend((ds,ms));d,meta=read(ds['path']),read(ms['path']);root=Path(ds['path']).parent;need(d['passed']and d['samples']==91 and d['actual_native_IDs_per_frame']==6805 and d['typed_arrays']==22,'Original qualified typed22 profile required')
        for leaf in('typed22.bin','typed22_layout.csv','clocks.csv'):seal(g,root/leaf,consumed)
        bundle=core.typed(root,6805,91,consumed);at=np.searchsorted(bundle['expected'],PAIR);need(np.array_equal(bundle['expected'][at],PAIR),'Actual pair lookup differs');bs=bind(run['source_build']);b=read(bs['path']);need(b['passed']and b['consumed_stats_unchanged'],'Actual source build required');consumed.extend((bs,bind(run['program']),bind(run['source_capture']),bind(run['source_archive']),bind(run['input_xml'])));arc=run['source_archive'];need(archive is None or arc==archive,'Common frozen source archive required');archive=arc
        h=float(meta['H']);eps=float(meta['AS_coefficient_float_reference']);power=float(meta['AS_exponent_float_reference']);need(meta['declared_Kernel_XML_CSV']==2 and eps==float(F(.3))and power==float(F(2.55))and h==float(F(.072)),'Actual Wendland/AS headers differ');dp=float(ET.parse(run['input_xml']['path']).getroot().find('execution/constants/dp').get('value'));need(dp==.04,'Actual original dp differs');aw=F(.557/(h*h));wdp=wab(F(dp*dp),h,aw);need(wdp>0,'Actual source W(dp) must be positive');size=F(F(h)*F(2));size2=F(size*size)
        for part,c in enumerate(bundle['clocks']):
            step=int(c['completed_step']);fr=bundle['frames'][part];need(int(c['part'])==part and step==(2180000 if part==90 else 2000001+2000*part)and int(c['saved_step'])==step-1 and bits(fr['time'])==bits(c['time_s'])and bits(c['dt_s'])==bits(5e-6)and float(c['signed_dterror_s'])<=1e-14 and c['dterror_interval_empty']=='0'and np.array_equal(fr['Idp'][at,0],PAIR),'Actual selected clock/IDs differ');ck=(step,bits(c['time_s']),bits(c['dt_s']));
            if case==CASES[0][0]:
                if common is None:common=[]
                common.append(ck)
            else:need(ck==common[part],'All91 genuine pair times must match')
            selected=[np.asarray(fr[k][at])for k in('Posd','Vel','PorePress','PorePress0','SigmaState_kk','SigmaState_ij','PoroVolumeRatio','PoroPorosity','PoroCurrentVolume','PoroMixtureDensity','Kplastic','FSType')];need(all(np.isfinite(x).all()for x in selected),'Nonfinite selected native field');pos=fr['Posd'][at].astype(float);dv=fr['Vel'][at[0]].astype(float)-fr['Vel'][at[1]].astype(float);delta=pos[0]-pos[1];r=float(np.linalg.norm(delta));n=delta/r if r>0 else None;df=delta.astype('f4');rr=F(F(F(df[0]*df[0])+F(df[1]*df[1]))+F(df[2]*df[2]));inside=bool(rr>=F(1e-18)and rr<=size2 and r>0);ratio=F(wab(rr,h,aw)*F(F(1)/wdp))if inside else None;weight=float(F(np.power(ratio,F(power))))if ratio is not None and ratio>0 else None
            row=dict(case=case,part=part,completed_step=step,actual_time_s=float(c['time_s']),tau_s=float(c['time_s'])-float(source['actual_end_s']),signed_dterror_s=float(c['signed_dterror_s']),id_i=PAIR[0],id_j=PAIR[1],r_m=r,r_over_dp=r/dp,rdot_m_s=float(dv@n)if n is not None else None,direction_defined=n is not None,source_form_float_rr2_m2=float(rr),within_source_form_support=inside,AS_h_m=h,AS_epsilon=eps,AS_exponent=power,Wdp_source_form_m_2=float(wdp),W_ratio_source_form=float(ratio)if ratio is not None else None,AS_kernel_weight_source_form=weight)
            for suffix,nid in zip(('_i','_j'),PAIR):
                q=initial[nid];row['initial_layer'+suffix]=int(q['initial_layer']);row['initial_x_m'+suffix]=float(q['initial_x_m']);row['initial_z_m'+suffix]=float(q['initial_z_m']);need(bits(float(F(fr['PorePress0'][at[0 if suffix=='_i'else 1],0])))==bits(float(F(q['fixed_P0_Pa']))),'Actual fixed P0 differs')
            Ti,Ri=endpoint(fr,int(at[0]),n,eps,row,'_i');Tj,Rj=endpoint(fr,int(at[1]),n,eps,row,'_j');pref=row['V_m2_j']/row['rho_mix_kg_m3_i']+row['V_m2_i']/row['rho_mix_kg_m3_j'];need(math.isfinite(pref)and pref>0 and all(row[k]>0 for k in('V_m2_i','V_m2_j','rho_mix_kg_m3_i','rho_mix_kg_m3_j')),'Positive native volume/mixture-inertia prefactor required');momentum=float(n@(Ti+Tj)@n)if n is not None else None;AS=float(weight*(n@(Ri+Rj)@n))if inside and weight is not None else None;B=momentum+AS if AS is not None else None;row.update(positive_native_prefactor_m5_kg=pref,momentum_bracket_Pa=momentum,AS_weighted_bracket_numpy_Pa=AS,B_total_numpy_Pa=B,conditional_tendency='undefined_zero_distance'if n is None else'outside_source_form_support'if not inside else'undefined_zero_kernel_weight'if B is None else'conditional_attraction'if B>0 else'conditional_repulsion'if B<0 else'zero_bracket');need(all(math.isfinite(v)for v in row.values()if isinstance(v,float)),'Nonfinite shadow row');rows.append(row)
    need(len(rows)==182,'All2x91 selected states retained');return rows,archive

def source_proof(archive):
    with zipfile.ZipFile(archive['path'])as z:a=z.read('src/source/JSphGpu_ker.cu').decode('utf-8');b=z.read('src/source/FunSphKernel.h').decode('utf-8');c=z.read('src/source/DualSphDef.h').decode('utf-8')
    for s in('float(sig.xx-pw)','1.f,CTE.artificialstresscoef','rp[a]=(eval[a]>0.f? -coef*eval[a]*rrhop2: 0.f);','const double coeff=porovol2/pororhot1;','double(powf(ratio,CTE.artificialstressexp))'):need(a.count(s)==1,'Unique frozen GPU formula anchor differs: '+s)
    need('kc.awen=float(0.557/(h*h));'in b and 'kc.bwen=float(-2.7852/(h*h*h));'in b and '#define ALMOSTZERO 1e-18f'in c,'Original Wendland/support constants differ')
def plot(rows):
    fig,axs=plt.subplots(3,2,figsize=(14,11),layout='constrained');panels=(('r_over_dp','Pair spacing / dp'),('rdot_m_s','Saved relative closing velocity [m/s]'),('total_nn_Pa','Saved total normal stress [Pa]'),('eff_nn_Pa','Saved effective normal stress [Pa]'),('positive_float_total_nn_Pa','Positive spectral directional content [Pa]'),('B_total_numpy_Pa','Pa bracket: positive conditional attraction'))
    for ax,(key,title)in zip(axs.flat,panels):
        for case,_ in CASES:
            q=[r for r in rows if r['case']==case];x=[r['tau_s']for r in q]
            for suffix in(('_i','_j')if key.endswith('nn_Pa')else('',)):
                ax.plot(x,[np.nan if r[key+suffix]is None else r[key+suffix]for r in q],label=case+suffix)
            if key=='B_total_numpy_Pa':
                for component,style in(('momentum_bracket_Pa',':'),('AS_weighted_bracket_numpy_Pa','--')):ax.plot(x,[np.nan if r[component]is None else r[component]for r in q],style,label=case+' '+component.split('_')[0])
        ax.set_title(title);ax.set_xlabel('Actual time after release [s]');ax.grid(alpha=.25);ax.axhline(0,color='.5',lw=.6);ax.legend(fontsize=7)
    fig.suptitle('Fixed material pair6817/6866: saved-state tensor/AS shadows only\nNumPy spectral model; not GPUJacobi/FMA, Pre/Cor force, net acceleration or causality');fig.savefig(PNG,dpi=165);plt.close(fig)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');need(p.parse_args().execution_authorized,'Separate root offline admission required');need(not CHECK.exists()and not CSV.exists()and not PNG.exists(),'Existing complete/partial shadow protected');consumed=[stat(q)for q in(SCRIPT,NOTE,GATE,Path(core.__file__),Path(core.core.__file__),Path(io.__file__))]
    try:
        g=read(GATE);need(g['passed']and g['analysis_complete']and g['consumed_stats_unchanged'],'Passed retained two-case review required');rows,archive=collect(g,consumed);source_proof(archive);io.verify(consumed)
        with CSV.open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        plot(rows);io.verify(consumed);io.save(CHECK,dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,rows=182,pair=PAIR,cases=2,frames_per_case=91,AS_tensor_units='Pa',AS_method='eigh64_of_float_total_input',B_positive_means_conditional_attraction=True,acceleration_amplitude_claimed=False,GPU_bit_truth=False,actual_PreCor_force_proven=False,all_neighbor_net_force_proven=False,zero_or_outside_states_deleted=False,source_zip_members_read=3,new_solver_invocations=0,new_native_invocations=0,new_API_calls=0,SHA_scans=0,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(CSV),stat(PNG)]))
    except Exception as e:
        if not CHECK.exists():io.save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),consumed=consumed,partial_outputs_preserved=True,new_solver_invocations=0,new_native_invocations=0,physical_acceptance=False))
        raise
if __name__=='__main__':main()
