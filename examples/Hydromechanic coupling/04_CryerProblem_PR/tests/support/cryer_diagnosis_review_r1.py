"""Small-table review of the two new offline audits; no solver or source edit."""
import argparse
import json
import numpy as np
import pandas as pd
from cryer_load_pair_r1 import TESTS,bound,write_json

TAG='cryer_diagnosis_review_r1'


def main():
    target=TESTS/'logs'/(TAG+'.check.json')
    assert not target.exists(),'Retained review exists'
    links=[bound(__file__)];unique={}
    for name in ['cryer_darcy_open_screen_r1','cryer_saved_state_audit_r1','cryer_radial_force_r2']:
        path=TESTS/'logs'/(name+'.check.json');a=json.loads(path.read_text())
        assert a['analysis_checks_passed']
        links.append(bound(path))
        for entry in a['inputs']+a['artifacts']:
            assert entry['path'] not in unique or unique[entry['path']]['sha256']==entry['sha256']
            unique[entry['path']]=entry
    for entry in unique.values():
        assert bound(entry['path'])['sha256']==entry['sha256'],entry['path']
    links+=list(unique.values())
    rates=pd.read_csv(TESTS/'figures/cryer_darcy_open_screen_r1_regions.csv',float_precision='round_trip')
    actual=pd.read_csv(TESTS/'figures/cryer_saved_state_audit_r1_summary.csv',float_precision='round_trip')
    shells=pd.read_csv(TESTS/'figures/cryer_saved_state_audit_r1_shells.csv',float_precision='round_trip')
    assert len(rates)==120 and len(actual)==6 and len(shells)==120
    assert actual.part.tolist()==[64,105,228,408,444,576]
    assert shells.groupby('part')['count'].sum().eq(37173).all()
    assert actual.surface_ids_changed.eq(0).all()
    p=actual.set_index('part').loc[444];s=shells[shells.part==444]
    tau=.0420518020252
    r=rates[(rates.tau_s==tau)&(rates.region=='nondrained')&
        (rates.denominator=='r2_plus_eta2')].set_index('stencil')
    base=float(r.loc['receiver_C','net_error_pa_s_rms']);sym=float(r.loc['symmetric_C','net_error_pa_s_rms'])
    result=dict(analysis_checks_passed=True,solver_executed=False,physical_acceptance=False,
        production_implemented=False,automatic_formal_run_admitted=False,source_links=links,
        open_reference_field_screen=dict(tau_s=tau,receiver_C_net_residual_rms_pa_s=base,
            symmetric_C_net_residual_rms_pa_s=sym,relative_reduction=1-sym/base,
            scope='Exact quasistatic fields on frozen initial nodes, not the native trajectory or a physical accuracy improvement.'),
        actual_native_peak_sample=dict(part=444,tau_s=float(p.tau_s),pressure_pa=float(p.center_pressure_pa),
            max_single_shell_angular_pressure_rms_pa=float(s.pressure_angular_rms_pa.max()),
            count_weighted_within_shell_angular_pressure_rms_pa=float(np.sqrt(np.average(s.pressure_angular_rms_pa**2,weights=s['count']))),
            artificial_viscosity_over_external_power=abs(float(p.artificial_viscosity_W/p.external_load_W)),
            kinematic_damping_over_external_power=abs(float(p.kinematic_damping_W/p.external_load_W)),
            center_compression_pa_s=float(p.center_comp_pa_s),center_Darcy_pa_s=float(p.center_darcy_pa_s),
            center_net_pa_s=float(p.center_net_pa_s),
            corrected_operator_work_defect_without_stress_projection_W=float(p.corrected_coupling_work_defect_W-p.stress_projection_work_difference_W),
            density_vs_conditional_geometry_rms_kg_m3=float(p.density_vs_local_geometry_rms_kg_m3),
            stress_vs_conditional_geometry_strain_rms=float(p.geometry_vs_stress_logstrain_rms)),
        ranked_next_checks=[
            '补齐原方案完整峰窗独立半步；保留5 Pa/.005 mm与原生安全条件，先区分时间/写回敏感性。',
            '仅在隔离CPU实际融合算子中核验Darcy对称C候选，证明压缩和力学路径不变；暂不合入生产或直接长算。',
            '若半步差很小，重点处理近表面扩散一阶矩与力学—应变/压力源离散不兼容；不能只修外载。',
            '密度—几何差需再区分原raw连续式与corrected应变路径及持久float舍入，不能由静态差直接归因。',
            '当前抽样不支持优先反复扫弱阻尼/人工黏性、球壳加密或盲开shifting；启动未保存耗散仍未排除。'],
        limitations=[
            'Six instantaneous powers are not integrated work; Darcy pressure quadratic rate is not total energy.',
            'The reference-field residual does not accumulate along the adapted native trajectory.',
            'The conditional geometric density comes from reconstructed inverse deformation, not an independent exact Jacobian.',
            'Closed-graph symmetry and negative random-field power do not accept full coupled dynamics or boundaries.',
            'Old quartic Neumann tests showed symmetric-C can worsen pointwise errors; no universal consistency claim.',
            'The original 2.4532 percent peak deficit and 10.3085 percent peak-time delay remain unresolved.'])
    write_json(target,result)
    print(json.dumps({k:result[k] for k in ['analysis_checks_passed','open_reference_field_screen','actual_native_peak_sample']},ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:main()
    else:parser.print_help()
