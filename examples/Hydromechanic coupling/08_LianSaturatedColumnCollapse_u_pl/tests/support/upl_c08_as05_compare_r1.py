"""Compare two sealed epsilon windows from typed exports only; no dense trace or solver."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json,struct,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from upl_c08_fsmask_r1 import SCHEMA,TYPES

T=Path(__file__).resolve().parents[1];TAG='upl_c08_as05_compare_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');N=6805;F=66
SPECS=(('epsilon0p2','upl_c08_stage_trace_window_GPU_r1',.2,'upl_c08_stage_trace_window_native_r1'),('epsilon0p5','upl_c08_as05_window_GPU_r2',.5,'upl_c08_as05_window_native_r1'))
FOCUS=(5809,4956,4959,7010,7011);EXPECTED=np.sort(np.r_[np.arange(1800),(1800,1852,1904,1956,2008),np.arange(2060,7060)]).astype('<u4')
def need(b,msg):
    if not b:raise ValueError(msg)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def stat(path):
    p=Path(path).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def bind(e):need(stat(e['path'])==e,'Sealed input changed: '+e['path']);return e
def table(path):
    with Path(path).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write(path,rows):
    with path.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def physics(node):
    need(node is not None,'Missing actual execution section');attrs={k:v for k,v in node.attrib.items() if k!='comment' and not k.endswith('_comment')}
    if node.tag=='parameter' and node.get('key')=='ArtificialStressCoef':attrs['value']='CONTROLLED_EPSILON'
    return node.tag,tuple(sorted(attrs.items())),(node.text or '').strip(),tuple(physics(x) for x in node)

def load(spec):
    label,job,eps,stage=spec;rp=T/'logs'/(job+'.run.json');npth=T/'logs'/(job+'.native_r1.json');r,n=read(rp),read(npth)
    need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==4264000 and r['saved_frames']==66 and r['consumed_stats_unchanged'],'Completed66-frame solver required: '+job)
    need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'] and n['decoder_invocations']==1,'Actual unique native check required: '+job)
    bind(next(e for e in n['consumed'] if Path(e['path']).samefile(rp)));native=Path(bind(n['completion'])['path']).parent;d=read(native/'completion.json');m=read(Path(bind(n['metadata'])['path']))
    counts=dict(samples=66,completed_steps=4264000,typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=330000,fixed_marker_checks=119130,P0_bits_checks=449130,rho_cache_bits_checks=330000,kappa_nondecreasing_from_PRE_checks=330000,nonempty_signed_intervals=66,plane_gap_checks=660000)
    need(d['passed'] and d['stage']==stage and all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['source_completed_step']==4000000,'Original all-frame native coverage differs')
    need(d['kept_bed_IDs']==[1800,1852,1904,1956,2008] and d['actual_retired_count']==255 and m['passed'] and m['stage']==stage+'.metadata' and m['samples']==m['keep_policy_headers']==m['AS_active_true_headers']==66 and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(np.float32(eps)) and m['AS_exponent_float_reference']==float(np.float32(2.55)),'Actual keep/AS coefficient metadata differs')
    c=read(Path(bind(n['actual_call'])['path']));need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==0 and c['ownership_failure'] is None and c['child']['argv']==[c['program'],*c['arguments']] and Path(c['arguments'][-1]).samefile(native),'Actual owned native exit/output differs')
    before=[stat(rp),stat(npth),bind(n['completion']),bind(n['metadata']),bind(n['actual_call'])]+[bind(r[k]) for k in ('program','source_build','input_xml','source_pre_file')]
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):
        path=native/leaf;before.append(bind(next(e for e in n['outputs'] if Path(e['path']).samefile(path))))
    layout=table(native/'typed22_layout.csv');need(len(layout)==22,'Original22-field layout required');fields=[('time','<f8')]
    for row,(name,kind,width) in zip(layout,SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,TYPES[kind].itemsize*width),'Typed schema changed');fields.append((name,TYPES[kind],(N,width)))
    dtype=np.dtype(fields);need(dtype.itemsize==8+N*212 and (native/'typed22.bin').stat().st_size==12+F*dtype.itemsize,'Incomplete/extra literal native payload')
    clocks=table(native/'clocks.csv');history=table(native/'history.csv');need(len(clocks)==len(history)==66,'Actual66 clocks/history required');xml=ET.parse(r['input_xml']['path']).getroot()
    params=[q for q in xml.findall('execution/parameters/parameter') if q.get('key')=='ArtificialStressCoef'];need(len(params)==1 and float(np.float32(params[0].get('value')))==float(np.float32(eps)),'Actual XML epsilon differs')
    return dict(label=label,epsilon=eps,run=r,done=d,native=native,dtype=dtype,clocks=clocks,history=history,before=before,physics=tuple(physics(xml.find('execution/'+key)) for key in ('special','parameters')))

def inspect(frame,context,part):
    need(np.array_equal(frame['Idp'][:,0],EXPECTED),'Original6805/all native IDs changed')
    for name,kind,width in SCHEMA:need(np.isfinite(frame[name]).all(),'Nonfinite native '+name)
    c,h=context['clocks'][part],context['history'][part];time=float(frame['time']);source=context['done']['source_actual_time_s'];step=4000000+4000*(part+1)
    need(int(c['part'])==part and int(c['completed_step'])==step and int(c['saved_step'])==step-1 and float(c['time_s'])==time and float(c['tau_from_actual_release_s'])==time-source and c['dterror_interval_empty']=='0' and np.isfinite(float(c['signed_dterror_s'])) and float(c['signed_dterror_s'])<=1e-14 and float(c['dt_s'])==.0000025,'Actual native clocks/steps/signed diagnostic differ')
    need(int(h['part'])==part and int(h['soil_IDs'])==5000 and float(h['time_s'])==time and float(h['tau_s'])==time-source,'Reader history material/time binding differs')
    return time,time-source,step

def quantities(frame,context,part,tau,step):
    soil=frame['Idp'][:,0]>=2060;need(np.count_nonzero(soil)==5000,'Walls cannot enter soil statistics');x=frame['Posd'][soil];v=frame['Vel'][soil].astype(float);pw=frame['PorePress'][soil,0].astype(float);s=frame['SigmaState_kk'][soil]-pw[:,None];ij=frame['SigmaState_ij'][soil];kap=frame['Kplastic'][soil,0];h=context['history'][part]
    q=dict(group=context['label'],epsilon=context['epsilon'],part=part,time_s=float(frame['time']),tau_s=tau,completed_step=step,soil_IDs=5000,p_mean_Pa=float(pw.mean()),p_min_Pa=float(pw.min()),p_max_Pa=float(pw.max()),p_RMS_Pa=float(np.sqrt(np.mean(pw**2))),negative_p_soil_count=int(np.count_nonzero(pw<0)),velocity_RMS_m_s=float(np.sqrt(np.mean(np.sum(v*v,axis=1)))),max_speed_m_s=float(np.sqrt(np.max(np.sum(v*v,axis=1)))),mean_settlement_from_PRE_mm=-1000*float(h['mean_dz_from_PRE_m']),displacement_RMS_from_PRE_mm=float(h['displacement_RMS_from_PRE_mm']),max_displacement_from_PRE_mm=float(h['max_displacement_from_PRE_mm']),max_kappa=float(kap.max()),plastic_soil_count=int(np.count_nonzero(kap>0)),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(s*s,axis=1)+2*np.sum(ij*ij,axis=1)))),total_zz_min_Pa=float(s[:,2].min()),total_zz_max_Pa=float(s[:,2].max()),front_particle_center_x_m=float(x[:,0].max()),max_particle_center_z_m=float(x[:,2].max()),min_soil_x_m=float(x[:,0].min()),min_soil_z_m=float(x[:,2].min()))
    for label,key in (('J','PoroVolumeRatio'),('n','PoroPorosity'),('k_m_s','PoroHydraulicConductivity')):q['min_'+label]=float(frame[key][soil,0].min());q['max_'+label]=float(frame[key][soil,0].max())
    need(all(np.isfinite(value) for value in q.values() if isinstance(value,(int,float))),'Nonfinite derived quantity');return q

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read after genuine AS.5 run/native completion required');need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial comparison protected')
    groups=[load(s) for s in SPECS];a,b=groups;need(a['physics']==b['physics'],'Execution physics differs beyond epsilon/comments');need(a['run']['program']==b['run']['program'] and a['run']['source_pre_file']==b['run']['source_pre_file'] and a['done']['source_actual_time_s']==b['done']['source_actual_time_s'],'Same program and actual PRE source/clock required')
    before=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(T/'support/upl_c08_fsmask_r1.py')]+[e for g in groups for e in g['before']];history=[];pairs=[];points=[];first={};files=[]
    # Exactly one sequential pass through each typed22 file; no BI4 or dense trace is opened.
    with (a['native']/'typed22.bin').open('rb') as fa,(b['native']/'typed22.bin').open('rb') as fb:
        need(struct.unpack('<III',fa.read(12))==struct.unpack('<III',fb.read(12))==(6805,22,66),'Original literal headers differ')
        for part in range(F):
            frames=[];contexts=[]
            for f,g in zip((fa,fb),groups):
                raw=f.read(g['dtype'].itemsize);need(len(raw)==g['dtype'].itemsize,'Short native record');frame=np.frombuffer(raw,dtype=g['dtype'],count=1)[0];frames.append(frame);contexts.append(inspect(frame,g,part))
            need(contexts[0]==contexts[1],'Only exact common actual clock/tau/Step is admitted; no interpolation');time,tau,step=contexts[0];need(np.array_equal(frames[0]['PorePress0'].view('<u4'),frames[1]['PorePress0'].view('<u4')),'Fixed material P0 bits differ between parameter cases')
            for frame,g in zip(frames,groups):
                history.append(quantities(frame,g,part,tau,step))
                for identity in FOCUS:
                    i=int(np.searchsorted(EXPECTED,identity));x=frame['Posd'][i];v=frame['Vel'][i].astype(float);key=(g['label'],identity)
                    if part==0:first[key]=x.copy()
                    du=1000*(x-first[key]);points.append(dict(group=g['label'],epsilon=g['epsilon'],part=part,time_s=time,tau_s=tau,completed_step=step,native_ID=identity,x_m=float(x[0]),z_m=float(x[2]),dx_since_first_tau0p01_save_mm=float(du[0]),dz_since_first_tau0p01_save_mm=float(du[2]),vx_m_s=float(v[0]),vz_m_s=float(v[2]),speed_m_s=float(np.linalg.norm(v)),p_Pa=float(frame['PorePress'][i,0]),kappa=float(frame['Kplastic'][i,0]),J=float(frame['PoroVolumeRatio'][i,0]),FSType=int(frame['FSType'][i,0])))
            soil=EXPECTED>=2060;dp=frames[1]['PorePress'][soil,0].astype(float)-frames[0]['PorePress'][soil,0];dx=frames[1]['Posd'][soil]-frames[0]['Posd'][soil];dv=frames[1]['Vel'][soil].astype(float)-frames[0]['Vel'][soil].astype(float)
            pairs.append(dict(part=part,time_s=time,tau_s=tau,completed_step=step,soil_IDs=5000,p_RMS_difference_Pa=float(np.sqrt(np.mean(dp*dp))),p_max_abs_difference_Pa=float(np.abs(dp).max()),material_XYZ_max_component_difference_mm=1000*float(np.abs(dx).max()),material_displacement_vector_max_difference_mm=1000*float(np.sqrt(np.max(np.sum(dx*dx,axis=1)))),velocity_vector_difference_RMS_m_s=float(np.sqrt(np.mean(np.sum(dv*dv,axis=1))))))
        need(fa.read(1)==fb.read(1)==b'','Extra native bytes; original headers are never rewritten')
    for leaf,rows in (('history',history),('option_pairs',pairs),('material_points',points)):
        path=Path(str(PREFIX)+'_'+leaf+'.csv');write(path,rows);files.append(path)
    plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained')
    for color,g in zip(('C0','C1'),groups):
        rows=[r for r in history if r['group']==g['label']];t=[r['tau_s'] for r in rows];label='epsilon='+str(g['epsilon']);ax=axes.ravel()
        for key,style in (('p_min_Pa','--'),('p_max_Pa',':'),('p_RMS_Pa','-')):ax[0].plot(t,[r[key]*.001 for r in rows],style,c=color,label=label+' '+key.split('_')[1])
        ax[1].plot(t,[r['mean_settlement_from_PRE_mm'] for r in rows],c=color,label=label+' mean');ax[1].plot(t,[r['displacement_RMS_from_PRE_mm'] for r in rows],'--',c=color,label=label+' displacement RMS')
        for key,style in (('velocity_RMS_m_s','-'),('max_speed_m_s','--')):ax[2].plot(t,[r[key] for r in rows],style,c=color,label=label+' '+('RMS' if style=='-' else 'max'))
        ax[3].plot(t,[r['max_kappa'] for r in rows],c=color,label=label)
        for index,lo,hi,scale in ((4,'min_J','max_J',1.),(5,'min_n','max_n',1.),(6,'min_k_m_s','max_k_m_s',1e4)):
            ax[index].plot(t,[r[lo]*scale for r in rows],'--',c=color,label=label+' min');ax[index].plot(t,[r[hi]*scale for r in rows],c=color,label=label+' max')
        ax[7].plot(t,[r['total_stress_Frobenius_RMS_Pa']*.001 for r in rows],c=color,label=label)
        ax[8].plot(t,[r['front_particle_center_x_m'] for r in rows],c=color,label=label+' front x');ax[8].plot(t,[r['max_particle_center_z_m'] for r in rows],'--',c=color,label=label+' max z')
    axes[0,0].set_yscale('symlog',linthresh=.1)
    labels=(('Saved-state pressure [kPa]','0.01 s native samples; not dense extrema'),('Displacement [mm]','True PRE material reference'),('Speed [m/s]','5000 soil IDs'),('max kappa','Plastic history'),('J','Saved range'),('Porosity','Saved range'),('Conductivity [1e-4 m/s]','Saved range'),('Total-stress RMS [kPa]','sigma_eff minus p I'),('Particle-center coordinate [m]','Front and height'))
    for ax,(ylabel,title) in zip(axes.ravel(),labels):ax.set(xlabel='Actual tau since imported PRE [s]',ylabel=ylabel,title=title,xlim=(pairs[0]['tau_s'],pairs[-1]['tau_s']));ax.grid(alpha=.25);ax.legend(fontsize=6)
    fig.suptitle('Prescribed epsilon .2 versus .5; same actual66 clocks/5000 material IDs; parameter comparison, not theory/half validation');path=Path(str(PREFIX)+'_overview.png');fig.savefig(path);plt.close(fig);files.append(path)
    need(all(stat(e['path'])==e for e in before),'Sealed inputs/helper changed during comparison')
    result=dict(stage=TAG,passed=True,analysis_completed=True,actual_matched_samples=66,soil_IDs_per_sample=5000,fixed_material_focus_IDs=list(FOCUS),actual_tau_first_s=pairs[0]['tau_s'],actual_tau_last_s=pairs[-1]['tau_s'],native_directories={g['label']:str(g['native']) for g in groups},native_directories_derived_from_receipts=True,typed_files_sequential_passes_per_group=1,all22_finite_and_ID_checks=True,clock_and_steps_exact=True,P0_bits_equal=True,PRE_mean_displacement_from_original_reader_history=True,focus_displacements_are_since_first_tau0p01_save_not_PRE=True,dense_trace_read=False,saved_state_extrema_not_continuous_peak=True,parameter_differences_are_not_half_or_theory_errors=True,cross_parameter_5Pa_or_displacement_gates_applied=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,queue_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,files=[stat(p) for p in files])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('AS05_WINDOW_COMPARISON_READY',CHECK,flush=True)

if __name__=='__main__':main()
