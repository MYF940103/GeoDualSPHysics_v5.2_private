"""Reuse the already reviewed1065-frame nu=.30 tables,without a solver or another6GB decode."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
TESTS=Path(__file__).resolve().parents[1];CASE=TESTS.parent
sys.path.insert(0,str(CASE/'support'))
import plot_cryer_formal_four_nu_r1 as common

def run():
    tag='030';out=common.table_path(tag,'summary');centerout=common.table_path(tag,'center18');check=TESTS/'logs'/(common.TAG+'_nu030.native.check.json');manifest=check.with_name(check.stem+'.inputs.json')
    assert not any(p.exists() for p in [out,centerout,check,manifest])
    oldpath=TESTS/'logs/cryer_full_native_r1.check.json';old=common.read(oldpath)
    assert old['passed'] and old['native_safety_passed'] and old['checked_frames']==1065
    common.verify(old['inputs_manifest']);inputs=[common.bound(__file__),common.bound(common.__file__),common.bound(oldpath),old['inputs_manifest']]
    records={Path(r['path']).name:r for r in old['artifacts']}
    def table(suffix):
        r=records['cryer_full_native_r1_'+suffix+'.csv'];common.verify(r);inputs.append(r);return pd.read_csv(r['path'],float_precision='round_trip')
    a=table('summary');c=table('center');assert len(a)==1065 and len(c)==18*1065 and a.native_safety_passed.all() and a.center_fixed_material_count.eq(18).all()
    peerpath=TESTS/'logs/cryer_four_nu_identity_peer_r1.check.json';peer=common.read(peerpath);assert peer['passed'] and peer['initial_sample_identity']['all_four_initial_decoded_35_column_numeric_tables_bit_equal'];inputs.append(common.bound(peerpath))
    runtime=common.parameters(CASE/'CaseCryerProblem_PR_symc_nu030_out','CaseCryerProblem_PR_symc_nu030',.3);inputs.append(runtime['runtime'])
    mapping=dict(part='part',time_s='time_s',saved_step='saved_step',native_soil_count='native_soil_count',center_count='center_fixed_material_count',center_pressure_pa='center_pressure_mean_pa',pressure_mean_pa='pressure_mean_pa',pressure_min_pa='pressure_min_pa',pressure_max_pa='pressure_max_pa',shell_inward_mm='shell_inward_mean_mm',material_inward_mean_mm='material_inward_mean_mm',total_mean_compression_pa='total_mean_compression_pa',effective_mean_compression_pa='effective_mean_compression_pa',rho_mean_kg_m3='rho_mean_kg_m3',speed_max_m_s='speed_max_m_s',radius_max_m='saved_radius_max_m',true_surface_count='true_surface_count',true_surface_p_absmax_pa='true_surface_pressure_absmax_pa',actual_radial_force_N='actual_radial_force_N',net_force_norm_N='net_force_norm_N',load_virial_N_m='virial_N_m',volume0_m3='native_reference_volume_m3',current_volume_m3='native_current_volume_m3',dterror_s='dterror_s')
    b=pd.DataFrame({key:a[value] for key,value in mapping.items()});b['symplectic_dt_s']=common.DT;b['center_pressure_std_pa']=c.groupby('part').pressure.std(ddof=0).to_numpy();b['mass_kg']=float(c.mass.iloc[0]);b['dp_m']=float(c.dp.iloc[0]);b['h_m']=float(c.h.iloc[0])
    cloud=table('initial_cloud').set_index('id');r=c.id.astype(int).map(cloud.r0_m);d=pd.DataFrame(dict(part=c.part,time_s=c.time_s,saved_step=c.saved_step,id=c.id.astype(int),x0=c.id.astype(int).map(cloud.x0),y0=c.id.astype(int).map(cloud.y0),z0=c.id.astype(int).map(cloud.z0),r0_m=r,x=c.x,y=c.y,z=c.z,pressure_pa=c.pressure,rho_kg_m3=c.rho,inward_mm=c.inward_mm,total_mean_compression_pa=c.pressure-(c.sigma_xx+c.sigma_yy+c.sigma_zz)/3))
    assert b.time_s.iloc[-1]==963370*common.DT and b.saved_step.iloc[-1]==963369 and np.isfinite(b.to_numpy()).all() and np.isfinite(d.to_numpy()).all()
    for p,data in [(out,b),(centerout,d)]:
        with p.open('x',encoding='utf8',newline='') as f:data.to_csv(f,index=False,float_format='%.17g')
    for r in inputs:common.verify(r)
    common.seal(manifest,dict(inputs=inputs,parameters=runtime,adopted_complete_native_check=common.bound(oldpath),old_raw_manifest=old['inputs_manifest'],old_full_native_series_adopted=True,full_raw_rehashed_this_adoption=False,initial_final_raw_independently_rechecked_by_peer=True,solver_started=False))
    common.seal(check,dict(passed=True,nu=.3,actual_saved_frames=1065,all_native_soil_states=1065*37173,source_manifest=common.bound(manifest),artifacts=[common.bound(out),common.bound(centerout)],old_full_native_series_adopted=True,whole_new_decoder_or_solver_called=False,end_s=float(b.time_s.iloc[-1]),actual_steps=963370,full_half_validation=False,physical_acceptance=False,solver_started=False))
    print(str(check))
if __name__=='__main__':run()
