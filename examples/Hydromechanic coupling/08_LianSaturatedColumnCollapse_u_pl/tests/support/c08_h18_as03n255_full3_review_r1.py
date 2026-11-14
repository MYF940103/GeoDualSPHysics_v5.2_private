"""One future AS03 full301 offline review against retained AS05 CSVs; no decoder or solver."""
import argparse, json, struct
from pathlib import Path
from matplotlib.colors import Normalize, TwoSlopeNorm
import c08_h18_n255_full3_review_r1 as retained

core, old = retained.core, retained.old
np, T, need, stat, read, table, bind, path = old.np, old.T, old.need, old.stat, old.read, old.table, old.bind, old.path
TAG = 'c08_h18_as03n255_full3_review_r1'
NOTE = T/'notes'/(TAG+'.md')
RUN, CONTROL = 'c08_h18_as03n255_full3_r1', 'c08_h18_n255_full3_r1'
SHORT = 'c08_h18_as03_n255_r1'
BUILD = T/'logs/c08_h18_as255_native_r1.build.json'
CALL = T/'logs/c08_h18_as03n255_full3_native_r1.call.json'
SNAPSHOTS = [.3, .6, .9, 1.2, 2., 3.]
FIELDS = (('p_Pa','p [kPa]',.001), ('native_p_minus_fixedP0_Pa','Native p-P0 [kPa]',.001),
          ('kappa','Plastic history',1.), ('J','J',1.))


def profile_xml(spec, xml, source_csv):
    need(spec['tag'] == RUN, 'Only the new AS03 full301 receiver is supported')
    rows = table(spec['material_csv']); p = {q['key']:q['value'] for q in rows}
    keys = core.plastic.MATERIAL_KEYS|{'Kernel','ArtificialStressCoef','ArtificialStressExp'}
    need(len(rows) == len(p) == 17 and set(p) == keys and p['group'] == 'psi0'
         and p['fresh_trigger_active'] == '0', 'Exact17-key psi0 profile required')
    soil = xml.find('execution/special/soils')
    pairs = [(q.get('key'),q.get('value')) for q in xml.findall('execution/parameters/parameter')]
    pars = dict(pairs); need(soil is not None and len(pars) == len(pairs), 'Unique actual material/parameter XML required')
    for key in keys-{'group','fresh_trigger_active'}:
        node = soil.find(key)
        value = pars[key] if key in ('Kernel','DPCtes','ArtificialStressCoef','ArtificialStressExp') else (node.get('value') if node is not None else '1.65' if key == 'SoilTriggerFos' else None)
        need(value is not None and old.f32(p[key]) == old.f32(value), 'Actual CSV/XML mismatch: '+key)
    source = {q['key']:q['value'] for q in table(source_csv)}
    for key in core.plastic.MATERIAL_KEYS|{'Kernel'}:
        need(p[key] == source[key] if key in ('group','fresh_trigger_active') else old.f32(p[key]) == old.f32(source[key]), 'Actual same-material source mismatch: '+key)
    need(all(old.f32(p[k]) == old.f32(v) for k,v in dict(Kernel=2,ArtificialStressCoef=.3,ArtificialStressExp=2.55).items())
         and spec['actualAS'] == dict(coefficient=.3, exponent=2.55), 'Only exact AS0.3/n2.55 accepted')
    return pars


def candidate(spec, source, source_spec, consumed):
    need(path(spec['native_build']) == BUILD.resolve() and path(spec['native_call']) == CALL.resolve(), 'Actual AS255 build and unique future full301 call required')
    receipt = path(spec['native_receipt']); check = read(receipt)
    need(check['passed'] and check['consumed_stats_unchanged'] and check['reader_invocations'] == 1
         and check['actual_call'] == stat(CALL) and check['reader_build'] == stat(BUILD), 'Independent completed candidate native receipt required')
    saved_build, saved_profile = core.BUILD, core.profile_xml
    try:
        core.BUILD, core.profile_xml = BUILD, profile_xml
        bundle = core.load_receiver(spec, source, source_spec, consumed)
    finally:
        core.BUILD, core.profile_xml = saved_build, saved_profile
    need(bundle['count'] == 301 and bundle['runtime_observed']['passed'], 'Incomplete/failed candidate is not analyzable as full301')
    need(check['native_completion'] == stat(bundle['root']/'completion.json')
         and check['metadata'] == stat(bundle['root']/'bedkeep_metadata.json'), 'Candidate receipt/native files differ')
    consumed.extend(stat(q) for q in (BUILD, receipt)); return bundle


def retained_csvs(spec, consumed):
    """Reuse sealed metrics/snapshots, never load or rescan old AS05 native arrays."""
    need(spec['tag'] == CONTROL, 'Only the retained completed AS05 full3 control is allowed')
    review = read(spec['review']); correction = read(spec['corrected_snapshots_check'])
    need(review['analysis_complete'] and review['consumed_stats_unchanged'] and not review['physical_acceptance']
         and review['actual_samples'] == 301 and review['soil_IDs'] == 5000, 'Sealed descriptive AS05 full301 review required')
    need(correction['passed'] and correction['rows'] == 30000 and correction['native_order'] == 'xy,yz,xz'
         and correction['other_field_strings_unchanged'] and not correction['physical_fields_or_solver_changed'], 'Corrected shear-label CSV proof required')
    run, native = read(spec['run']), read(spec['native_receipt'])
    need(run['passed'] and run['solver_completed'] and run['actual_exit'] == run['actual_Win32_exit'] == 0
         and run['actual_steps'] == 2600000 and run['saved_frames'] == 301
         and native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations'] == 1
         and native['actual_call'] == stat(path(spec['native_call'])) and native['reader_build'] == stat(BUILD), 'Actual retained full301 run/native binding required')
    consumed.extend(stat(path(spec[k])) for k in ('review','corrected_snapshots_check','run','native_receipt','native_call'))
    for key in ('run','native_call'):
        target=path(spec[key]);consumed.append(bind(next(q for q in review['consumed'] if path(q['path'])==target)))
    result = {}
    for key, value in spec['csvs'].items():
        dest = path(value)
        entry = correction['corrected_csv'] if key == 'snapshots' else next(q for q in review['files'] if path(q['path']) == dest)
        need(path(entry['path']) == dest, 'Retained CSV identity differs: '+key)
        consumed.append(bind(entry)); result[key] = table(dest)
    need(len(result['history']) == len(result['geometry']) == 301 and len(result['snapshots']) == 30000
         and all(q['tag'] == CONTROL for q in result['history'])
         and len(result['tracks']) == 301*5, 'Original retained CSV coverage differs')
    result['summary'] = review['summary']; return result


def own_prefix(bundle, analysis, spec, consumed):
    review = read(spec['review']); root = path(spec['native_dir'])
    need(spec['tag'] == SHORT and review['analysis_complete'] and review['consumed_stats_unchanged']
         and not review['physical_acceptance'] and review['exact_matching_option_rows'] == 91, 'Completed actual AS03/AS05 short review required')
    consumed.append(stat(path(spec['review'])))
    for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv'):
        q = root/leaf; consumed.append(bind(next(v for v in review['consumed'] if path(v['path']) == q)))
    done = read(root/'completion.json'); need(done['passed'] and done['samples'] == 91 and done['completed_steps'] == 2180000, 'Preserve original91 completion')
    with (root/'typed22.bin').open('rb') as a, (bundle['root']/'typed22.bin').open('rb') as b:
        old_header, new_header = struct.unpack('<III',a.read(12)), struct.unpack('<III',b.read(12))
        need(old_header == (6805,22,91) and new_header == (6805,22,301), 'Keep genuine91/301 headers')
        total = remaining = 90*bundle['frames'].dtype.itemsize
        while remaining:
            size = min(4*1024*1024,remaining); aa,bb = a.read(size),b.read(size)
            need(len(aa) == len(bb) == size and aa == bb, 'Actual common first90 typed records differ'); remaining -= size
    need((root/'typed22_layout.csv').read_bytes() == (bundle['root']/'typed22_layout.csv').read_bytes(), 'Literal22 layouts differ')
    clocks = table(root/'clocks.csv')
    need(len(clocks) == 91 and clocks[:90] == bundle['clocks'][:90]
         and int(clocks[90]['completed_step']) == 2180000 and int(bundle['clocks'][90]['completed_step']) == 2180001, 'Signed clocks/real forced endpoint differ')
    history = path(spec['history']); consumed.append(bind(next(v for v in review['files'] if path(v['path']) == history)))
    old_rows = [q for q in table(history) if q['tag'] == SHORT]
    need(len(old_rows) == 91 and all((int(a['completed_step']),float(a['time_s'])) == (b['completed_step'],b['time_s']) for a,b in zip(old_rows[:90],analysis['history'][:90])), 'Actual short common90 history differs')
    return dict(old_header=list(old_header),new_header=list(new_header),compared_records=90,
        compared_typed_record_bytes=total,all22_arrays_and_actual_time_bytes_equal=True,
        literal_layout_bytes_equal=True,first90_signed_clock_rows_equal=True,
        old_forced_final_completed_step=2180000,new_part90_completed_step=2180001,
        old_final_not_compared=True,short_native_reanalysis=False)


def snapshot_rows(bundle, analysis, reference):
    rows, schedule = [], []
    for requested,(part,snap) in zip(SNAPSHOTS,analysis['snapshots'].items()):
        x = old.read22(bundle,part)
        need(abs(snap['tau_s']-requested) <= 5.01e-6, 'Nearest genuine save required')
        schedule.append(dict(requested_tau_s=requested,part=part,time_s=snap['time_s'],tau_s=snap['tau_s'],completed_step=int(bundle['clocks'][part]['completed_step'])))
        for local,identity in enumerate(x['Idp'][1805:,0]):
            at=1805+local; pos=x['Posd'][at]; v=x['Vel'][at]; p=float(x['PorePress'][at,0]); sk=x['SigmaState_kk'][at]; si=x['SigmaState_ij'][at]
            row=dict(tag=RUN,part=part,requested_tau_s=requested,time_s=snap['time_s'],tau_s=snap['tau_s'],native_id=int(identity),x_m=float(pos[0]),y_m=float(pos[1]),z_m=float(pos[2]),initial_z_m=float(reference['initial_pos'][identity,2]),dx_from_PRE_m=float(pos[0]-reference['pos'][identity,0]),dz_from_PRE_m=float(pos[2]-reference['pos'][identity,2]),vx_m_s=float(v[0]),vy_m_s=float(v[1]),vz_m_s=float(v[2]),p_Pa=p,fixed_P0_Pa=float(x['PorePress0'][at,0]),native_p_minus_fixedP0_Pa=float(x['ExcessPorePress'][at,0]),kappa=float(x['Kplastic'][at,0]),J=float(x['PoroVolumeRatio'][at,0]),n=float(x['PoroPorosity'][at,0]),rho_kg_m3=float(x['PoroMixtureDensity'][at,0]),k_m_s=float(x['PoroHydraulicConductivity'][at,0]),FS_type=int(x['FSType'][at,0]))
            for j,name in enumerate(('xx','yy','zz')):row['effective_'+name+'_Pa']=float(sk[j]);row['total_'+name+'_Pa']=float(sk[j]-p)
            for j,name in enumerate(('xy','yz','xz')):row['effective_and_total_'+name+'_Pa']=float(si[j])
            rows.append(row)
    need(len(schedule)==6 and len(rows)==30000,'Six complete5000-ID snapshots required');return rows,schedule


def geometry(bundle, analysis, reference):
    initial=reference['initial_pos'][2060:][:,(0,2)]; xs,zs=np.unique(initial[:,0]),np.unique(initial[:,1]);grid=np.full((50,100),-1,dtype=int)
    need(len(xs)==100 and len(zs)==50,'Original100x50 material grid required')
    for i,(xx,zz) in enumerate(zip(np.searchsorted(xs,initial[:,0]),np.searchsorted(zs,initial[:,1]))):need(grid[zz,xx]==-1,'Duplicate original material node');grid[zz,xx]=i
    need((grid>=0).all(),'Missing material node');cells=np.stack((grid[:-1,:-1],grid[:-1,1:],grid[1:,1:],grid[1:,:-1]),axis=-1).reshape(-1,4)
    local=initial[cells]-initial[cells][:,:1];area0=.5*np.sum(retained.material.cross(local,np.roll(local,-1,axis=1)),axis=1)
    need(len(cells)==4851 and np.allclose(area0,.04**2,rtol=0,atol=1e-15),'Original positive quad reference required')
    rows,critical,edges,clusters=[],[],[],[];last_edges={}
    for part,h in enumerate(analysis['history']):
        x=old.read22(bundle,part);pos=x['Posd'][1805:];J=x['PoroVolumeRatio'][1805:,0]
        ratio,tri,mixed,bow,poly=retained.material.measures(pos[:,(0,2)],cells,area0);meanJ=J[cells].mean(axis=1);at=int(ratio.argmin());clock=dict(part=part,time_s=h['time_s'],tau_s=h['tau_s'])
        rows.append(dict(**clock,min_area_ratio=float(ratio.min()),max_area_ratio=float(ratio.max()),nonpositive_area_cells=int((ratio<=0).sum()),chosen_diagonal_triangle_reversal=int(tri.sum()),mixed_turn_cells=int(mixed.sum()),self_cross_cells=int(bow.sum()),area_minus_meanJ_RMS=float(np.sqrt(np.mean((ratio-meanJ)**2))),total_signed_area_ratio=float(np.sum(ratio*area0)/np.sum(area0))))
        critical.append(dict(**clock,cell=at,ID_LL=int(cells[at,0]+2060),ID_LR=int(cells[at,1]+2060),ID_UR=int(cells[at,2]+2060),ID_UL=int(cells[at,3]+2060),signed_area_ratio=float(ratio[at]),native_corner_mean_J=float(meanJ[at])))
        pairs=old.cKDTree(pos[:,(0,2)]).query_pairs(.7*old.DP,output_type='ndarray');current={};dist=np.linalg.norm(pos[pairs[:,0]]-pos[pairs[:,1]],axis=1) if len(pairs) else np.empty(0)
        nodes=np.unique(pairs);tensor=np.zeros((len(nodes),3,3));sk=x['SigmaState_kk'][1805:][nodes];si=x['SigmaState_ij'][1805:][nodes];pressure=x['PorePress'][1805:,0][nodes]
        for j in range(3):tensor[:,j,j]=sk[:,j]-pressure
        for j,(a,b) in enumerate(((0,1),(1,2),(0,2))):tensor[:,a,b]=tensor[:,b,a]=si[:,j]
        principal={int(a):float(v) for a,v in zip(nodes,np.linalg.eigvalsh(tensor)[:,-1])}
        for pair,distance in zip(pairs,dist):
            if distance>=.7*old.DP:continue
            a,b=sorted((int(pair[0]+2060),int(pair[1]+2060)));current[(a,b)]=last_edges.get((a,b),0)+1
            edges.append(dict(**clock,ID_a=a,ID_b=b,distance_over_dp=float(distance/old.DP),below_0p5dp=bool(distance<.5*old.DP),consecutive_saved_occurrences=current[(a,b)],total_max_principal_a_Pa=principal[a-2060],total_max_principal_b_Pa=principal[b-2060],positive_total_principal_a=bool(principal[a-2060]>0),positive_total_principal_b=bool(principal[b-2060]>0)))
        for cut in (.7,.5):
            parents={}
            def find(a):
                parents.setdefault(a,a)
                while parents[a]!=a:parents[a]=parents[parents[a]];a=parents[a]
                return a
            count=0
            for pair,distance in zip(pairs,dist):
                if distance<cut*old.DP:a,b=map(int,pair);parents[find(a)]=find(b);count+=1
            sizes={}
            for a in parents:root=find(a);sizes[root]=sizes.get(root,0)+1
            clusters.append(dict(**clock,descriptive_cutoff_over_dp=cut,near_pairs=count,native_IDs_in_clusters=len(parents),clusters_ge2=len(sizes),largest_cluster_IDs=max(sizes.values(),default=0)))
        need(len(current)==h['pairs_r_lt_0p7dp'],'Candidate descriptive pair count must match its original history')
        last_edges=current
    return rows,critical,edges,clusters


def compare(histories):
    a,b=histories;need(len(a)==len(b)==301,'Two complete301 histories required');rows=[]
    for before,after in zip(a,b):
        need((int(before['part']),int(before['completed_step']),float(before['time_s']))==(after['part'],after['completed_step'],after['time_s']),'All301 actual matched step/time records required; no interpolation')
        row=dict(part=after['part'],completed_step=after['completed_step'],time_s=after['time_s'],tau_s=after['tau_s'])
        for key,value in after.items():
            if key in before and isinstance(value,(int,float)) and not isinstance(value,bool) and before[key]!='':row[key+'_AS03_minus_AS05']=value-float(before[key])
        rows.append(row)
    return rows


def plots(histories, tracks, fields, quad, prefix):
    plt=old.plt;files=[];labels=('AS=0.5','AS=0.3');charts=[('Pressure [kPa]',('p_mean_Pa','p_RMS_Pa'),.001),('Pressure extrema [kPa]',('p_min_Pa','p_max_Pa'),.001),('Native p-P0 RMS [kPa]',('native_p_minus_fixedP0_RMS_Pa',),.001),('Stress RMS [kPa]',('effective_stress_Frobenius_RMS_Pa','total_stress_Frobenius_RMS_Pa'),.001),('Material settlement [mm]',('top_material_settlement_mm','bottom_material_settlement_mm'),1.),('Speed [m/s]',('velocity_RMS_m_s','max_speed_m_s'),1.),('J',('min_J','max_J'),1.),('Porosity',('min_n','max_n'),1.),('Density [kg/m3]',('min_rho','max_rho'),1.),('Conductivity [m/s]',('min_k_m_s','max_k_m_s'),1.),('Maximum kappa',('max_kappa',),1.),('Front advance from PRE [m]',('runout_from_PRE_front_m',),1.),('NN / dp',('NN_min_over_dp','NN_q05_over_dp','NN_median_over_dp'),1.),('Pairs r < 0.7dp',('pairs_r_lt_0p7dp',),1.),('Material quads',('nonpositive_area_cells','self_cross_cells'),1.)]
    short={'p_mean_Pa':'mean','p_RMS_Pa':'RMS','p_min_Pa':'min','p_max_Pa':'max',
        'effective_stress_Frobenius_RMS_Pa':'effective','total_stress_Frobenius_RMS_Pa':'total',
        'top_material_settlement_mm':'top','bottom_material_settlement_mm':'bottom',
        'velocity_RMS_m_s':'RMS','max_speed_m_s':'max','NN_min_over_dp':'min',
        'NN_q05_over_dp':'q05','NN_median_over_dp':'median',
        'nonpositive_area_cells':'area <= 0','self_cross_cells':'self-crossing'}
    fig,axes=plt.subplots(5,3,figsize=(16,17),layout='constrained')
    for ax,(title,keys,scale) in zip(axes.flat,charts):
        for ci,h in enumerate(histories if title!='Material quads' else quad):
            for ki,key in enumerate(keys):ax.plot([float(q['tau_s']) for q in h],[float(q[key])*scale for q in h],color='C'+str(ci),ls=('-','--',':')[ki],label=labels[ci]+(' '+short.get(key,'min' if key.startswith('min_') else 'max') if len(keys)>1 else ''))
        ax.set(title=title,xlabel='Actual time since PRE [s]');ax.grid(alpha=.2);ax.legend(fontsize=6)
    fig.suptitle('C08 psi=0 | Wendland H/dp=1.8 | AS exponent=2.55 | full301 actual saves\nDifferent AS coefficients are descriptive options, not half errors or theory truth')
    dest=Path(str(prefix)+'_history.png');fig.savefig(dest,dpi=160);plt.close(fig);files.append(dest)
    fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained');trackkeys=(('p_Pa','ID7010 pressure [kPa]',.001),('speed_m_s','Speed [m/s]',1.),('total_trace_Pa','Total stress trace [kPa]',.001),('J','J',1.),('kappa','Plastic history',1.),('z_m','Height [m]',1.))
    for ax,(key,title,scale) in zip(axes.flat,trackkeys):
        for ci,rr in enumerate(tracks):q=[r for r in rr if int(r['native_id'])==7010];need(len(q)==301,'Full301 ID7010 trajectory required');ax.plot([float(r['tau_s']) for r in q],[float(r[key])*scale for r in q],label=labels[ci])
        ax.set(title=title,xlabel='Actual time since PRE [s]');ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Original material ID7010: bottom-front positive-pressure pulse and later motion; no resampling')
    dest=Path(str(prefix)+'_ID7010.png');fig.savefig(dest,dpi=170);plt.close(fig);files.append(dest)
    columns=[q for group in fields for q in group];xmin=min(float(q['x_m']) for q in columns);xmax=max(float(q['x_m']) for q in columns);zmin=min(float(q['z_m']) for q in columns);zmax=max(float(q['z_m']) for q in columns)
    norms={}
    for key,_,scale in FIELDS:
        lo=min(float(q[key])*scale for q in columns);hi=max(float(q[key])*scale for q in columns);norms[key]=TwoSlopeNorm(vmin=lo,vcenter=0.,vmax=hi) if lo<0<hi else Normalize(vmin=lo,vmax=hi)
    for si,requested in enumerate(SNAPSHOTS):
        selected=[[q for q in group if float(q['requested_tau_s'])==requested] for group in fields];need(all(len(q)==5000 for q in selected),'Complete fixed5000-ID selected fields required')
        fig,axes=plt.subplots(4,2,figsize=(12,12),layout='constrained')
        for ri,(key,title,scale) in enumerate(FIELDS):
            for ci,rr in enumerate(selected):
                ax=axes[ri,ci];im=ax.scatter([float(q['x_m']) for q in rr],[float(q['z_m']) for q in rr],c=[float(q[key])*scale for q in rr],s=4,cmap='coolwarm' if key in ('p_Pa','native_p_minus_fixedP0_Pa') else 'viridis',norm=norms[key],rasterized=True);ax.set(xlim=(xmin-.04,xmax+.04),ylim=(zmin-.04,zmax+.04),xlabel='x [m]',ylabel='z [m]',title=labels[ci]+f"; actual tau={float(rr[0]['tau_s']):.9f}s");ax.set_aspect('equal')
            fig.colorbar(im,ax=list(axes[ri]),label=title,shrink=.75)
        fig.suptitle('Raw material points; full shared ranges across both cases/all six times\nNative p-P0 uses fixed initial P0, not paper-defined plastic excess; no clipping/smoothing')
        dest=Path(str(prefix)+f'_fields_{si:02d}.png');fig.savefig(dest,dpi=160);plt.close(fig);files.append(dest)
    return files


def paper(fields, prefix, consumed):
    receipt=T/'logs/upl_c08_lian14_outline_r1.check.json';check=read(receipt)
    need(check['passed'] and check['analysis_completed'] and not check['physical_acceptance'] and not check['pressure_values_sampled'],'Original descriptive raster outline required');consumed.append(stat(receipt))
    paths=[T/'figures'/('upl_c08_lian14_outline_r1_'+q+'.csv') for q in ('outline','summary')]
    for q in paths:consumed.append(bind(next(v for v in check['outputs'] if path(v['path'])==q)))
    outline,summaries=[table(q) for q in paths];need(len(summaries)==3,'Original three paper times required');fig,axes=old.plt.subplots(1,3,figsize=(16,5),layout='constrained');rows=[]
    for ax,summary in zip(axes,summaries):
        requested=float(summary['requested_tau_s']);edge=[q for q in outline if float(q['requested_tau_s'])==requested];allx=[float(q['x_m']) for q in edge];allz=[float(q['z_m']) for q in edge]
        for ci,group in enumerate(fields):
            rr=[q for q in group if float(q['requested_tau_s'])==requested];need(len(rr)==5000 and abs(float(rr[0]['tau_s'])-requested)<=5.01e-6,'Actual paper nearby save required');xx=[float(q['x_m']) for q in rr];zz=[float(q['z_m']) for q in rr];allx+=xx;allz+=zz
            ax.scatter(xx,zz,s=2,label=('AS=0.5','AS=0.3')[ci],alpha=.65)
            rows.append(dict(AS_coefficient=(.5,.3)[ci],requested_tau_s=requested,native_part=int(rr[0]['part']),native_actual_tau_s=float(rr[0]['tau_s']),native_particle_center_front_m=max(xx),paper_visible_colored_extent_m=float(summary['front_colored_extent_m']),center_minus_visible_extent_m=max(xx)-float(summary['front_colored_extent_m']),paper_raster_allowance_m=float(summary['front_digitization_allowance_m']),separate_representation_scale_m=.02,difference_is_theory_error=False,pressure_values_compared=False))
        ax.scatter([float(q['x_m']) for q in edge],[float(q['z_m']) for q in edge],s=3,c='k',label='Paper visible bulk edge');ax.set(xlim=(min(allx)-.04,max(allx)+.04),ylim=(min(allz)-.04,max(allz)+.04),xlabel='x [m]',ylabel='z [m]',title=f'Fig14 {requested:g}s');ax.set_aspect('equal');ax.legend(fontsize=7)
    fig.suptitle('Lian2023 Fig14 psi=0: raw native centers versus retained raster edge\nDifferent representations, not an exact shape/theory error; no fitting or pressure-color sampling')
    dest=Path(str(prefix)+'_paper_shape.png');fig.savefig(dest,dpi=170);old.plt.close(fig);return rows,dest


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Author-only until root full-read and separate successful native301');manifest=read(args.manifest)
    need(manifest['tag']==TAG and manifest['snapshots_tau_s']==SNAPSHOTS,'Exact narrow full3 manifest required')
    prefix=T/'figures'/TAG;check=T/'logs'/(TAG+'.check.json');need(not check.exists() and not list(prefix.parent.glob(TAG+'_*')),'Existing complete/partial analysis protected')
    consumed=[stat(q) for q in (args.manifest,Path(__file__),NOTE,BUILD,Path(retained.__file__),Path(core.__file__),Path(core.source.__file__),Path(core.plastic.__file__),Path(old.__file__),Path(retained.material.__file__),Path(retained.narrow.__file__))]
    result=dict(stage=TAG,analysis_complete=False,physical_acceptance=False,winner_selected=False,consumed=consumed)
    try:
        control=retained_csvs(manifest['retained_control'],consumed)
        source=core.source.load(manifest['source'],consumed);reference=old.reference_from(source)
        bundle=candidate(manifest['candidate'],source,manifest['source'],consumed);bundle['_source']=source
        analysis=old.analyze_case(bundle,reference,SNAPSHOTS);definitions=core.add_total_settlement(analysis,reference);first=core.first_step(bundle,reference)
        proof=own_prefix(bundle,analysis,manifest['short_prefix'],consumed);matched=compare([control['history'],analysis['history']])
        fields,schedule=snapshot_rows(bundle,analysis,reference);late,states=retained.late_states(bundle,analysis,reference)
        geo,critical,edges,clusters=geometry(bundle,analysis,reference)
        paperrows,paperpng=paper([control['snapshots'],fields],prefix,consumed)
        files=[paperpng]+plots([control['history'],analysis['history']],[control['tracks'],analysis['tracks']],[control['snapshots'],fields],[control['geometry'],geo],prefix)
        for suffix,rows in [(key,analysis[key]) for key in ('history','extrema','layers','tracks')]+[('matched301',matched),('first_real_step',[first]),('selection_metrics',[core.selection_summary(analysis)]),('snapshot_schedule',schedule),('snapshots',fields),('late_metrics',late),('late_same_ID_states',states),('material_geometry',geo),('material_min_cells',critical),('near_pair_edges',edges),('near_pair_clusters',clusters),('paper_shape',paperrows)]:
            dest=Path(str(prefix)+'_'+suffix+'.csv')
            if rows:old.write_csv(dest,rows);files.append(dest)
            elif suffix=='near_pair_edges':
                with dest.open('x',encoding='utf-8') as f:f.write('part,time_s,tau_s,ID_a,ID_b,distance_over_dp,below_0p5dp,consecutive_saved_occurrences,total_max_principal_a_Pa,total_max_principal_b_Pa,positive_total_principal_a,positive_total_principal_b\n')
                files.append(dest)
        need(all(stat(q['path'])==q for q in consumed),'Consumed evidence/helper changed during analysis')
        result.update(analysis_complete=True,actual_samples=301,exact_matched_option_rows=len(matched),summary=analysis['summary'],reference_definitions=definitions,first_real_step=first,prefix_proof=proof,snapshot_schedule=schedule,late_same_ID_states=states,retained_control_native_scans=0,retained_control_metric_reanalyses=0,source_metric_reanalyses=0,new_candidate_metric_analyses=1,material_quads=4851,descriptive_pair_thresholds_over_dp=[.7,.5],pair_edge_rows=len(edges),candidate_shear_mapping='SigmaState_ij=(xy,yz,xz)',native_fixed_P0_excess_is_not_paper_plastic_excess=True,straight_chord_area_is_not_native_J=True,reaction_J_Darcy_closed=False,no_automatic_winner_or_next_job=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,consumed_stats_unchanged=True,visual_QA_pending=True,files=[stat(q) for q in files])
    except Exception as error:result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
