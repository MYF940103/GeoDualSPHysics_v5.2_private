"""Build only one polynomial entry +86 original CPU objects; never run it."""
from pathlib import Path
import c08_h18_step_balance_r1_build as bridge

TAG = 'c08_h18_quadratic_r1'


def main():
    # Reuse the full frozen shared-source/archived-header/86-object build closure.
    # No import/build/component execution is authorized by authoring this file.
    m, t = bridge.base.m, bridge.base.T
    extra = [m.stat(Path(__file__)), m.stat(Path(bridge.__file__))]
    checkfile = t / 'logs/c08_h18_step_balance_r1.check.json'
    complete = t / 'outputs/c08_h18_step_balance_r1/completion.json'
    checked, done = m.read(checkfile), m.read(complete)
    m.need(checked['passed'] and checked['consumed_stats_unchanged']
           and done['passed'] and done['balance_rows'] == 5000
           and done['actual_force_calls'] == done['actual_Darcy_calls'] == 2
           and done['physical_steps'] == 1 and not done['physical_acceptance'],
           'Closed original Part60 step balance required before polynomial build')
    extra += [m.stat(checkfile), m.stat(complete)]
    original_save = m.save

    def save(path, value):
        if value.get('stage') == TAG + '.build' and value.get('passed'):
            m.verify(extra)
            value['consumed'] += extra
            value.update(diagnostic_kind='frozen_geometry_polynomial_shadows',
                         physical_steps_authorized_by_build=0,
                         actual_force_calls_authorized_by_build=0,
                         expected_component_force_calls=1,
                         original_step_calls_unmodified=True,
                         polynomial_values_written_to_solver=False,
                         full_u_pl_or_variable_k_claim=False,
                         boundary_accuracy_claim=False,
                         shared_AppInfo_legacy_name='C08H18StepBalance')
        return original_save(path, value)

    try:
        m.verify(extra)
        bridge.TAG = TAG
        m.save = save
        bridge.main()  # Retains --execution-authorized and one compile/link only.
    finally:
        m.save = original_save


if __name__ == '__main__':
    main()
