import pyomo.core as pyomo
import pandas as pd


def MIQP_partload(m):
    # Binary Variable if MILP-cap_min is activated
    m.pro_mode_run = pyomo.Var(
        m.t, m.pro_partial_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if process in run mode')

    m.del_component(m.res_throughput_by_capacity_min)
    m.del_component(m.res_throughput_by_capacity_min_index)
    m.res_throughput_by_capacity_min_MILP = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=res_throughput_by_capacity_min_MILP_rule,
        doc='run[0/1] * cap_pro * min-fraction <= tau_pro')

    m.res_throughput_by_capacity_max_MILP = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=res_throughput_by_capacity_max_MILP_rule,
        doc='tau_pro <= run[0/1] * cap-up')

    # Calculate offset and slope for partload behaviour
    m = calc_offset_slope(m)

    # Calculate start-up costs (MIQP):
    m.pro_mode_startup = pyomo.Var(
        m.tm, m.pro_partial_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if process started')

    m.res_pro_mode_startup = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=res_pro_mode_startup_rule,
        doc='switch on >= run[t] - run [t-1]')

    m.pro_p_startup = pyomo.Var(
        m.tm, m.pro_partial_input_tuples,
        within=pyomo.Reals,
        doc='switch on loss for MILP processes')

    m.def_pro_p_startup = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=def_pro_p_startup_rule,
        doc='pro_p_startup = E_start * cap(t) * R * start[0/1](t)'
            'R = input ratio at maximum operation point')

    m.del_component(m.def_partial_process_input)
    m.del_component(m.def_partial_process_input_index)
    m.del_component(m.def_partial_process_output)
    m.del_component(m.def_partial_process_output_index)
    m.del_component(m.def_partial_process_output_index_1)
    m.del_component(m.def_partial_process_output_index_1_index_1)
    try:
        m.del_component(m.def_process_partial_timevar_output)
        m.del_component(m.def_process_partial_timevar_output_index)
        m.del_component(m.def_process_partial_timevar_output_index_1)
    except AttributeError:
        pass

    m.def_partial_process_input = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=def_partial_process_input_MIQP_rule,
        doc='e_pro_in = offset + slope * tau_pro + startup_costs'
            'slope = (R -  min_fraction * r) / (1 - min_fraction); offset = R - slope')
    m.def_partial_process_output = pyomo.Constraint(
        m.tm,
        (m.pro_partial_output_tuples -
         (m.pro_partial_output_tuples & m.pro_timevar_output_tuples)),
        rule=def_partial_process_output_MIQP_rule,
        doc='e_pro_out = offset + slope * tau_pro'
            'slope = (R -  min_fraction * r) / (1 - min_fraction); offset = R - slope')
    m.def_process_partial_timevar_output = pyomo.Constraint(
        m.tm, m.pro_partial_output_tuples & m.pro_timevar_output_tuples,
        rule=def_pro_partial_timevar_output_MIQP_rule,
        doc='e_pro_out = (offset + slope * tau_pro) * eff_factor'
            'slope = (R -  min_fraction * r) / (1 - min_fraction); offset = R - slope')
    return m


def res_throughput_by_capacity_min_MILP_rule(m, tm, stf, sit, pro):
    # run[0/1] * cap_pro * min - fraction <= tau_pro
    # linearization: tau_pro - cap_pro * min-fraction >= - (1 - run[0/1]) * process.cap-up
    return (m.tau_pro[tm, stf, sit, pro] -
            m.cap_pro[stf, sit, pro] * m.process_dict['min-fraction'][(stf, sit, pro)] * m.dt >=
            - (1 - m.pro_mode_run[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt)


def res_throughput_by_capacity_max_MILP_rule(m, tm, stf, sit, pro):
    # tau_pro <= run[0/1] * cap-up
    return (m.tau_pro[tm, stf, sit, pro] <=
            m.pro_mode_run[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * m.dt)


def calc_offset_slope(m):
    m.pro_p_in_slope = pd.Series(index=m.pro_partial_input_tuples.value_list)
    m.pro_p_in_offset_spec = pd.Series(index=m.pro_partial_input_tuples.value_list)
    for idx in m.pro_p_in_slope.index:
        # input ratio at maximum operation point
        R = m.r_in_dict[(idx[0],)+idx[2:4]]
        # input ratio at lowest operation point
        r = m.r_in_min_fraction_dict[(idx[0],)+idx[2:4]]
        min_fraction = m.process_dict['min-fraction'][idx[0:3]]
        m.pro_p_in_slope[idx] = (R - min_fraction * r) / (1 - min_fraction)
        m.pro_p_in_offset_spec[idx] = R - m.pro_p_in_slope[idx]
    m.pro_p_out_slope = pd.Series(index=m.pro_partial_output_tuples.value_list)
    m.pro_p_out_offset_spec = pd.Series(index=m.pro_partial_output_tuples.value_list)
    for idx in m.pro_p_out_slope.index:
        # output ratio at maximum operation point
        R = m.r_out_dict[(idx[0],)+idx[2:4]]
        # output ratio at lowest operation point
        r = m.r_out_min_fraction_dict[(idx[0],)+idx[2:4]]
        min_fraction = m.process_dict['min-fraction'][idx[0:3]]
        m.pro_p_out_slope[idx] = (R - min_fraction * r) / (1 - min_fraction)
        m.pro_p_out_offset_spec[idx] = R - m.pro_p_out_slope[idx]
    return m


# offset = offset_spec * cap(t) * run[0/1](t)
def def_partial_process_input_MIQP_rule(m, tm, stf, sit, pro, coin):
    # e_pro_in = offset + slope * tau_pro + startup_costs
    return m.e_pro_in[tm, stf, sit, pro, coin] == \
           m.dt * m.pro_p_in_offset_spec[stf, sit, pro, coin] * m.cap_pro[stf, sit, pro] * \
           m.pro_mode_run[tm, stf, sit, pro] + \
           m.pro_p_in_slope[(stf, sit, pro, coin)] * m.tau_pro[tm, stf, sit, pro] \
           + m.dt * m.pro_p_startup[tm, stf, sit, pro,coin]


def def_partial_process_output_MIQP_rule(m, tm, stf, sit, pro, coo):
    # e_pro_out = offset + slope * tau_pro
    return m.e_pro_out[tm, stf, sit, pro, coo] == \
           m.dt * m.pro_p_out_offset_spec[stf, sit, pro, coo] * m.cap_pro[stf, sit, pro] * \
           m.pro_mode_run[tm, stf, sit, pro] + \
           m.pro_p_out_slope[(stf, sit, pro, coo)] * m.tau_pro[tm, stf, sit, pro]

def def_pro_partial_timevar_output_MIQP_rule(m, tm, stf, sit, pro, coo):
    # e_pro_out = (offset + slope * tau_pro) * eff_factor
    return m.e_pro_out[tm, stf, sit, pro, coo] == \
           (m.dt * m.pro_p_out_offset_spec[stf, sit, pro, coo] * m.cap_pro[stf, sit, pro] *
            m.pro_mode_run[tm, stf, sit, pro] +
            m.pro_p_out_slope[(stf, sit, pro, coo)] * m.tau_pro[tm, stf, sit, pro]) * \
           m.eff_factor_dict[(sit, pro)][(stf, tm)]


def res_pro_mode_startup_rule(m, tm, stf, sit, pro):
    # switch on >= run[t] - run[t - 1]
    return m.pro_mode_startup[tm, stf, sit, pro] >= \
           m.pro_mode_run[tm, stf, sit, pro] - m.pro_mode_run[tm - 1, stf, sit, pro]


def def_pro_p_startup_rule(m, tm, stf, sit, pro, coin):
    # pro_p_startup = startup_spec * cap * R * start[0/1]
    return m.pro_p_startup[tm, stf, sit, pro, coin] == \
           m.process_dict['start-up-energy'][(stf, sit, pro)] * m.cap_pro[stf, sit, pro] * \
           m.r_in_dict[(stf, pro, coin)] * m.pro_mode_startup[tm, stf, sit, pro]