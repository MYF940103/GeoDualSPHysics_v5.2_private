"""Compare one sealed ReleasedSubstages window with cached n3 CompletedOnly; no physical calls."""
import argparse,json,re,struct,zipfile
from pathlib import Path
from matplotlib.colors import SymLogNorm
import upl_c08_clustering_r1 as cluster
np,c,plt=cluster.np,cluster.c,cluster.plt
T=c.T;TAG='upl_c08_stage_ponding_compare_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')
OLD='upl_c08_asn3_window_GPU_r1';NEW='upl_c08_stage_ponding_window_GPU_r2';CACHE=T/'logs/upl_c08_asn3_compare_r1.check.json'
DIFF=('src/source/JSphCpu.cpp','src/source/JSphGpu.cpp','src/source/JSph.cpp','doc/xml_format/_FmtXML_ElastoplasticSoil.xml')
LABELS=('CompletedOnly','ReleasedSubstages');NAMES=('all_soil','kappa_ge_0p1f','kappa_lt_0p1f','geometric_interior','FS23_or_within_kernelR','within_kernelR_of_fixed_B')

def context(job,stage,label):
    rp=T/'logs'/(job+'.run.json');npth=T/'logs'/(job+'.native_r1.json');r,n=c.read(rp),c.read(npth)
    c.need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==4264000 and r['saved_frames']==66 and r['consumed_stats_unchanged'],'Actual completed normal66-state run required')
    c.need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'] and n['decoder_invocations']==1 and c.bind(n['source_run'])==c.stat(rp),'Actual unique native guard closure required')
    native=Path(c.bind(n['completion'])['path']).parent;d=c.read(native/'completion.json');m=c.read(c.bind(n['metadata'])['path']);call=c.read(c.bind(n['actual_call'])['path'])
    counts=dict(samples=66,completed_steps=4264000,typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=330000,fixed_marker_checks=119130,P0_bits_checks=449130,rho_cache_bits_checks=330000,kappa_nondecreasing_from_PRE_checks=330000,nonempty_signed_intervals=66,plane_gap_checks=660000)
    c.need(d['passed'] and d['stage']==stage and all(d[k]==v for k,v in counts.items()) and d['source_completed_step']==4000000 and d['actual_retired_count']==255 and d['kept_bed_IDs']==[1800,1852,1904,1956,2008] and d['max_scalar_clock_error_s']<=1e-14 and d['max_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13,'Original native counts/domain/clock/ledger/keep guards differ')
    c.need(m['passed'] and m['stage']==stage+'.metadata' and m['samples']==m['keep_policy_headers']==m['AS_active_true_headers']==66 and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==3.,'Same AS.2/n3 typed metadata required')
    if label=='ReleasedSubstages':c.need(m['profile']=='window' and m['planned_cadence_steps']==4000 and m['ponding_policy_active_headers']==66 and m['FreeSeepagePondingPolicy']=='ReleasedSubstages' and m['FreeSeepagePondingActive'],'Actual per-frame released-substage policy metadata required')
    else:c.need('FreeSeepagePondingPolicy' not in m,'Retained n3 must not be relabelled as the new policy')
    c.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and Path(call['arguments'][-1]).samefile(native),'Actual reader exit/output differs')
    before=[c.stat(rp),c.stat(npth),c.bind(n['completion']),c.bind(n['metadata']),c.bind(n['actual_call'])]+[c.bind(r[k]) for k in ('program','source_build','input_xml','source_pre_file')]
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):before.append(c.bind(next(e for e in n['outputs'] if Path(e['path']).samefile(native/leaf))))
    layout=c.table(native/'typed22_layout.csv');fields=[('time','<f8')];c.need(len(layout)==22,'Literal22-array schema required')
    for q,(name,kind,width) in zip(layout,c.SCHEMA):c.need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,width,c.TYPES[kind].itemsize*width),'Typed field layout differs');fields.append((name,c.TYPES[kind],(6805,width)))
    dtype=np.dtype(fields);c.need(dtype.itemsize==8+6805*212 and (native/'typed22.bin').stat().st_size==12+66*dtype.itemsize,'Literal66-record payload extent differs')
    clocks=c.table(native/'clocks.csv');history=c.table(native/'history.csv');c.need(len(clocks)==len(history)==66,'Original66 clocks/history required');xml=c.ET.parse(r['input_xml']['path']).getroot()
    return dict(label=label,epsilon=.2,run=r,done=d,native=native,dtype=dtype,layout=layout,clocks=clocks,history=history,before=before,physics=tuple(c.physics(xml.find('execution/'+key)) for key in ('special','parameters')))

def archived_patch(old,new):
    ob,nb=c.read(old['run']['source_build']['path']),c.read(new['run']['source_build']['path']);before=[c.bind(b[k]) for b in (ob,nb) for k in ('source_capture','source_archive')]
    c.need(nb['passed'] and nb['configuration']=='Release' and nb['actual_typed_exit_code']==nb['actual_Win32_exit']==0 and nb['source_stats_unchanged'] and nb['program']==new['run']['program'] and Path(nb['source_capture']['path']).samefile(T/'outputs/upl_c08_stage_ponding_source_r2/source.json'),'New closed Release_r2/source_r2 required')
    source=c.read(nb['source_capture']['path']);de=c.bind(source['production_diff']);before.append(de);text=Path(de['path']).read_text(encoding='utf8');blocks=re.split(r'(?=^diff --git )',text,flags=re.M)[1:]
    paths=[re.match(r'diff --git a/(\S+) b/\1\n',b).group(1) for b in blocks];c.need(set(paths)==set(DIFF) and len(paths)==4 and source['diff_paths']==list(DIFF),'Production diff must contain only the three CPP and one XML guide')
    c.need(sum(l.startswith('+') and not l.startswith('+++') for l in text.splitlines())==17 and sum(l.startswith('-') and not l.startswith('---') for l in text.splitlines())==8,'Reviewed17+/8- patch extent differs')
    def apply(body,block):
        body=body.decode('utf-8-sig').replace('\r\n','\n').splitlines(True);lines=block.splitlines(True);out=[];pos=0;i=0
        while i<len(lines):
            h=re.match(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@',lines[i])
            if not h:i+=1;continue
            start=int(h[1])-1;c.need(start>=pos,'Overlapping archived hunk');out.extend(body[pos:start]);pos=start;i+=1
            while i<len(lines) and not lines[i].startswith('@@ '):
                line=lines[i];i+=1
                if line.startswith((' ','-')):c.need(pos<len(body) and body[pos]==line[1:],'Patch context differs from actual old program archive');pos+=1
                if line.startswith((' ','+')):out.append(line[1:])
        out.extend(body[pos:]);return ''.join(out)
    with zipfile.ZipFile(ob['source_archive']['path']) as oz,zipfile.ZipFile(nb['source_archive']['path']) as nz:
        for path,block in zip(paths,blocks):
            if path.endswith('.cpp'):c.need(apply(oz.read(path),block)==nz.read(path).decode('utf-8-sig').replace('\r\n','\n'),'New archived CPP differs beyond the recorded boundary/metadata patch')
            else:
                changed=[s for s in block.splitlines() if s.startswith(('+','-')) and not s.startswith(('+++','---'))];c.need(len(changed)==2 and all('<!--' in s and 'pressure' in s for s in changed) and b'<HydroMechFreeSeepage value="0"' in nz.read(path),'Guide change must be one explanatory comment/default0')
    return before

def snapshot(state,context,part,tau,step):
    m=cluster.measures(state);soil=state['Idp'][:,0]>=2060;return dict(x=m['x'].copy(),fixed=m['fixed'].copy(),nn=m['nn'].copy(),kappa=m['kappa'].copy(),p=m['p'].copy(),FS=state['FSType'][soil,0].copy(),ids=state['Idp'][soil,0].copy(),time=float(state['time']),tau=tau,step=step,label=context['label'])

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();c.need(args.execution_authorized,'Root full-read after actual normal run/native pass required');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial derived products protected')
    cache=c.read(CACHE);c.need(cache['passed'] and cache['analysis_completed'] and cache['actual_common_frames']==66,'Passed n3 cached observations required');old=context(OLD,'upl_c08_asn3_window_native_r1',LABELS[0]);new=context(NEW,'upl_c08_stage_ponding_native_r1',LABELS[1])
    c.need(old['run']['source_pre_file']==new['run']['source_pre_file'] and old['done']['source_actual_time_s']==new['done']['source_actual_time_s'] and old['layout']==new['layout'] and old['physics']==new['physics'],'Same original PRE, scalar clock,22 layout and complete special/parameters required; programs intentionally differ')
    bp=T/'figures/upl_c08_asn3_compare_r1_body.csv';cp=T/'figures/upl_c08_asn3_compare_r1_cohorts.csv';body=[dict(r,group=LABELS[0],ponding_policy=LABELS[0]) for r in c.table(bp) if r['group']=='epsilon0p2_exponent3'];cohorts=[dict(r,group=LABELS[0],ponding_policy=LABELS[0]) for r in c.table(cp) if r['group']=='epsilon0p2_exponent3'];body.sort(key=lambda r:int(r['part']));oldc={(int(r['part']),r['cohort']):r for r in cohorts}
    c.need(len(body)==66 and len(cohorts)==len(oldc)==396 and all((i,k) in oldc for i in range(66) for k in NAMES),'Exact retained n3 body/six-cohort histories required')
    before=[c.stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),CACHE,Path(cluster.__file__),Path(c.__file__))]+[c.bind(next(e for e in cache['files'] if Path(e['path']).samefile(p))) for p in (bp,cp)]+old['before']+new['before']+archived_patch(old,new);differences=[];new_snap=None
    with (new['native']/'typed22.bin').open('rb') as f:
        c.need(struct.unpack('<III',f.read(12))==(6805,22,66),'Actual new header required; never rewritten')
        for part in range(66):
            raw=f.read(new['dtype'].itemsize);c.need(len(raw)==new['dtype'].itemsize,'Incomplete new record');state=np.frombuffer(raw,dtype=new['dtype'],count=1)[0];time,tau,step=c.inspect(state,new,part);b=body[part]
            c.need(int(b['part'])==part and float(b['time_s'])==time and float(b['tau_s'])==tau and int(b['completed_step'])==step and int(b['soil_IDs'])==5000 and float(old['clocks'][part]['time_s'])==time,'Exact66 actual matched material times/steps required; no interpolation')
            for k in NAMES:r=oldc[(part,k)];c.need(float(r['time_s'])==time and float(r['tau_s'])==tau and int(r['completed_step'])==step,'Cached cohort clock differs')
            q=c.quantities(state,new,part,tau,step);q.update(AS_exponent=3.,ponding_policy=LABELS[1]);body.append(q);m=cluster.measures(state);nr=cluster.summarize(m,dict(group=LABELS[1],epsilon=.2,part=part,time_s=time,tau_s=tau,completed_step=step))
            for r in nr:r.update(AS_exponent=3.,ponding_policy=LABELS[1])
            cohorts.extend(nr);a=next(r for r in nr if r['cohort']=='all_soil');o=oldc[(part,'all_soil')];pair=dict(part=part,time_s=time,tau_s=tau,completed_step=step)
            for key in ('p_mean_Pa','p_min_Pa','p_max_Pa','p_RMS_Pa','mean_settlement_from_PRE_mm','front_particle_center_x_m','velocity_RMS_m_s','max_speed_m_s','total_stress_Frobenius_RMS_Pa','max_kappa','min_J','max_J','min_n','max_n','min_k_m_s','max_k_m_s'):pair[key+'_Released_minus_Completed']=float(q[key])-float(b[key])
            for key in ('rNN_over_dp_min','rNN_over_dp_q05','pair_both_in_cohort_lt_0p5dp','pair_both_in_cohort_lt_0p7dp'):pair[key+'_Released_minus_Completed']=float(a[key])-float(o[key])
            differences.append(pair)
            if part==65:new_snap=snapshot(state,new,part,tau,step)
        c.need(f.read(1)==b'','Extra data beyond original66 records')
    with (old['native']/'typed22.bin').open('rb') as f:
        c.need(struct.unpack('<III',f.read(12))==(6805,22,66),'Original n3 header required');f.seek(12+65*old['dtype'].itemsize);raw=f.read(old['dtype'].itemsize);c.need(len(raw)==old['dtype'].itemsize,'Original endpoint incomplete');state=np.frombuffer(raw,dtype=old['dtype'],count=1)[0];time,tau,step=c.inspect(state,old,65);c.need((time,tau,step)==(new_snap['time'],new_snap['tau'],new_snap['step']),'Actual common endpoint differs');old_snap=snapshot(state,old,65,tau,step)
    files=[]
    for leaf,rows in (('body',body),('cohorts',cohorts),('differences',differences)):
        p=Path(str(PREFIX)+'_'+leaf+'.csv');c.write(p,rows);files.append(p)
    spatial=[]
    for q in (old_snap,new_snap):
        for i in range(5000):spatial.append(dict(group=q['label'],time_s=q['time'],tau_s=q['tau'],completed_step=q['step'],native_id=int(q['ids'][i]),x_m=float(q['x'][i,0]),z_m=float(q['x'][i,1]),p_Pa=float(q['p'][i]),kappa=float(q['kappa'][i]),rNN_over_dp=float(q['nn'][i]),FSType=int(q['FS'][i])))
    p=Path(str(PREFIX)+'_endpoint.csv');c.write(p,spatial);files.append(p);plt.rcParams.update({'font.size':8,'figure.dpi':165});fig,axes=plt.subplots(2,4,figsize=(17,9),layout='constrained')
    for label,color in zip(LABELS,('C0','C1')):
        rr=sorted((r for r in body if r['group']==label),key=lambda r:int(r['part']));cc=sorted((r for r in cohorts if r['group']==label and r['cohort']=='all_soil'),key=lambda r:int(r['part']));t=[float(r['tau_s']) for r in rr];ax=axes.ravel()
        for key,style in (('p_min_Pa','--'),('p_max_Pa',':'),('p_RMS_Pa','-')):ax[0].plot(t,[float(r[key])*.001 for r in rr],style,c=color,label=label+' '+key.split('_')[1])
        for a,key in ((1,'mean_settlement_from_PRE_mm'),(2,'front_particle_center_x_m'),(4,'total_stress_Frobenius_RMS_Pa'),(5,'max_kappa')):ax[a].plot(t,[float(r[key])*(.001 if a==4 else 1.) for r in rr],c=color,label=label)
        for key,style in (('velocity_RMS_m_s','-'),('max_speed_m_s','--')):ax[3].plot(t,[float(r[key]) for r in rr],style,c=color,label=label+(' RMS' if style=='-' else ' max'))
        for key,style in (('pair_both_in_cohort_lt_0p5dp','-'),('pair_both_in_cohort_lt_0p7dp','--')):ax[6].plot(t,[float(r[key]) for r in cc],style,c=color,label=label+(' <.5dp' if style=='-' else ' <.7dp'))
        for key,style in (('rNN_over_dp_min','-'),('rNN_over_dp_q05','--')):ax[7].plot(t,[float(r[key]) for r in cc],style,c=color,label=label+(' min' if style=='-' else ' q05'))
    axes[0,0].set_yscale('symlog',linthresh=1.)
    for ax,(title,unit) in zip(axes.ravel(),(('Saved pressure, not dense extrema','p [kPa]'),('All5000 material mean from true PRE','Settlement [mm]'),('Particle-center front','x [m]'),('All5000 velocity','Speed [m/s]'),('Total stress Frobenius RMS','Stress [kPa]'),('Maximum dev plastic history','kappa'),('Unique close pairs; descriptive','Count'),('Nearest-other spacing; descriptive','rNN / dp'))):ax.set(title=title,xlabel='Actual tau from PRE [s]',ylabel=unit);ax.grid(alpha=.25);ax.legend(fontsize=6)
    fig.suptitle('AS.2/n3 held fixed: completed-only versus released-substage ponding; coupled response, not an accuracy/half gate');p=Path(str(PREFIX)+'_history.png');fig.savefig(p);plt.close(fig);files.append(p)
    pictures=(old_snap,new_snap);xy=np.concatenate([q['x'] for q in pictures]);limits=(float(xy[:,0].min()-2*cluster.DP),float(xy[:,0].max()+2*cluster.DP),float(xy[:,1].min()-2*cluster.DP),float(xy[:,1].max()+2*cluster.DP));fig,axes=plt.subplots(3,2,figsize=(12,13),sharex=True,sharey=True,layout='constrained')
    for row,key in enumerate(('p','kappa','nn')):
        values=np.concatenate([q[key] for q in pictures])*(.001 if key=='p' else 1.);lo,hi=float(values.min()),float(values.max());norm=SymLogNorm(linthresh=1.,vmin=lo,vmax=hi,base=10,clip=False) if key=='p' else cluster.Normalize(lo,hi,clip=False)
        for col,q in enumerate(pictures):
            ax=axes[row,col];ax.scatter(q['fixed'][:,0],q['fixed'][:,1],s=3,c='.7',marker='s',linewidths=0);v=q[key]*(.001 if key=='p' else 1.)
            for mask,marker in ((~np.isin(q['FS'],(2,3)),'o'),(np.isin(q['FS'],(2,3)),'^')):ax.scatter(q['x'][mask,0],q['x'][mask,1],c=v[mask],norm=norm,cmap='coolwarm' if key=='p' else 'viridis',s=6,marker=marker,linewidths=0)
            ax.set(xlim=limits[:2],ylim=limits[2:],xlabel='x [m]',ylabel='z [m]',title=q['label']+' actual tau=%.12g s'%q['tau']);ax.set_aspect('equal',adjustable='box')
        fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='coolwarm' if key=='p' else 'viridis'),ax=axes[row,:].tolist(),label={'p':'Raw p [kPa], signed symlog','kappa':'Kplastic kappa','nn':'rNN / dp'}[key],shrink=.8)
    fig.suptitle('Same actual tau .66: full5000 soil, common raw range per row; triangles FS2/3, grey actual fixed markers\nLower stress/speed or fewer close pairs alone does not establish a physical fix');p=Path(str(PREFIX)+'_endpoint.png');fig.savefig(p);plt.close(fig);files.append(p)
    c.need(all(c.stat(e['path'])==e for e in before),'Closed input changed during offline review');result=dict(stage=TAG,passed=True,analysis_completed=True,actual_common_frames=66,all_soil_IDs=5000,new_typed_payload_sequential_passes=1,old_typed_endpoint_records_read=1,old_full_payload_scan=False,old_body_and_cohorts_from_passed_cache=True,endpoint_soil_rows=len(spatial),same_program_required=False,program_difference_expected=True,archived_three_CPP_recorded_patch_replayed=True,production_diff_scope=list(DIFF),new_typed_policy='ReleasedSubstages',old_policy='CompletedOnly',epsilon=.2,AS_exponent=3.,clock_and_steps_exact=True,original_headers_not_rewritten=True,no_cross_policy_5Pa_or_accuracy_gate=True,dense_trace_read=False,saved_peaks_not_dense_extrema=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,files=[c.stat(p) for p in files])
    with CHECK.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('STAGE_PONDING_COMPARISON_READY',CHECK,flush=True)
if __name__=='__main__':main()
