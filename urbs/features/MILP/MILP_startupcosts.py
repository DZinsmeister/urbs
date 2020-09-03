import pyomo.core as pyomo

# to_do: Check, why the startup costs don't work in the MILP problem!

def MILP_startupcosts(m):
    m.pro_mode_startup = pyomo.Var(
        m.tm, m.pro_partial_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if process started')

    m.pro_mode_start_up1 = pyomo.Constraint(
        m.tm, m.pro_partial_tuples,
        rule=pro_mode_start_up1_rule,
        doc='switch on >= run[t] - run [t-1]')

    # m.pro_mode_start_up2 = pyomo.Constraint(
    #     m.tm, m.pro_partial_tuples,
    #     rule=pro_mode_start_up2_rule,
    #     doc='switch on <= run[t]')
    #
    # m.pro_mode_start_up3 = pyomo.Constraint(
    #     m.tm, m.pro_partial_tuples,
    #     rule=pro_mode_start_up3_rule,
    #     doc='switch on <= 1 - run [t-1]')

    m.pro_p_startup = pyomo.Var(
        m.tm, m.pro_partial_input_tuples,
        within=pyomo.Reals,
        doc='switch on loss for MILP processes')

    # calculates the power needed per startup: pro_p_startup = E_start * cap(t) * R start[0/1](t)
    # R = input ratio at maximum operation point
    # linearization:
    # 1. p_startup - (cap * startup_spec * R) <= (1-startup) * cap-max * startup_spec * R
    #    -> p_startup <= (p_startup_spec*cap) if startup = 1
    # 2. p_startup - (cap * startup_spec * R) >= -(1-startup) * cap-max * startup_spec * R
    #    -> p_startup >= (p_startup_spec*cap) if startup = 1
    # 3. p_startup <= startup * startup_spec * cap_max * R
    # 4. p_startup >= startup * startup_spec * cap_max * R
    m.pro_p_in_startup_lt = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=pro_p_in_startup_lt_rule,
        doc='switch on loss must be (lower) equal to E_start * cap(t) * R, when startup = 1'
            'p_startup - (cap * startup_spec * R) <= (1-startup) * cap-max * startup_spec * R'
            '-> p_startup <= (p_startup_spec * cap) if startup = 1.')

    m.pro_p_in_startup_gt = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=pro_p_in_startup_gt_rule,
        doc='switch on loss must be (greater) equal to E_start * cap(t) * R, when run = 1'
            'p_startup - (cap * startup_spec * R) >= -(1-startup) * cap-max * startup_spec * R'
            'p_startup >= (p_startup_spec * cap) if startup = 1.')

    m.pro_p_startup_in_ltzero_when_off = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=pro_p_startup_in_ltzero_when_off_rule,
        doc='p_startup must be (lower) equal to zero when run = 0'
            'p_startup <= startup * cap_max * startup_spec * R')

    m.pro_p_startup_in_gtzero_when_off = pyomo.Constraint(
        m.tm, m.pro_partial_input_tuples,
        rule=pro_p_startup_in_gtzero_when_off_rule,
        doc='p_startup must be (greater) equal to zero when run = 0'
            'p_startup >= -startup * cap_max * startup_spec * R')
    return m


def pro_mode_start_up1_rule(m, tm, stf, sit, pro):
    # switch on >= run[t] - run[t - 1]
    return m.pro_mode_startup[tm, stf, sit, pro] >= \
           m.pro_mode_run[tm, stf, sit, pro] - m.pro_mode_run[tm - 1, stf, sit, pro]


def pro_mode_start_up2_rule(m, tm, stf, sit, pro):
    # switch on <= run[t]
    return m.pro_mode_startup[tm, stf, sit, pro] <= m.pro_mode_run[tm, stf, sit, pro]


def pro_mode_start_up3_rule(m, tm, stf, sit, pro):
    # switch on <= 1 - run [t-1]
    return m.pro_mode_startup[tm, stf, sit, pro] <= 1 - m.pro_mode_run[tm - 1, stf, sit, pro]


def pro_p_in_startup_lt_rule(m, tm, stf, sit, pro, coin):
    # p_startup - (cap * startup_spec * R) <= (1-startup) * cap-max * startup_spec * R
    return m.pro_p_startup[tm, stf, sit, pro, coin] - m.cap_pro[stf, sit, pro] * \
           m.process_dict['start-up-energy'][(stf, sit, pro)] * m.r_in_dict[(stf, pro, coin)] <= \
           (1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * \
           m.process_dict['start-up-energy'][(stf, sit, pro)] * m.r_in_dict[(stf, pro, coin)]


def pro_p_in_startup_gt_rule(m, tm, stf, sit, pro, coin):
    # p_startup - (cap * startup_spec * R) >= -(1-startup) * cap-max * startup_spec * R
    return m.pro_p_startup[tm, stf, sit, pro, coin] - m.cap_pro[stf, sit, pro] * \
           m.process_dict['start-up-energy'][(stf, sit, pro)] * m.r_in_dict[(stf, pro, coin)] >= \
           -(1 - m.pro_mode_startup[tm, stf, sit, pro]) * m.process_dict['cap-up'][(stf, sit, pro)] * \
           m.process_dict['start-up-energy'][(stf, sit, pro)] * m.r_in_dict[(stf, pro, coin)]


def pro_p_startup_in_ltzero_when_off_rule(m, tm, stf, sit, pro, coin):
    # p_startup <= startup * startup_spec * cap_max * R
    return m.pro_p_startup[tm, stf, sit, pro, coin] <= \
           m.pro_mode_startup[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * \
           m.process_dict['start-up-energy'][(stf, sit, pro)] * m.r_in_dict[(stf, pro, coin)]


def pro_p_startup_in_gtzero_when_off_rule(m, tm, stf, sit, pro, coin):
    # p_startup >= -startup * startup_spec * cap_max * R
    return m.pro_p_startup[tm, stf, sit, pro, coin] >= \
           -m.pro_mode_startup[tm, stf, sit, pro] * m.process_dict['cap-up'][(stf, sit, pro)] * \
           m.process_dict['start-up-energy'][(stf, sit, pro)] * m.r_in_dict[(stf, pro, coin)]
