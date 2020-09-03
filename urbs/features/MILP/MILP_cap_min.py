import pyomo.core as pyomo


def MILP_cap_min(m):
    # Binary Variable if MILP-cap_min is activated

    # Process
    m.cap_pro_build = pyomo.Var(
        m.pro_tuples,
        within=pyomo.Boolean,
        doc='Boolean: True if new capacity is build. Needed for minimum new capacity')

    # Change expression m.cap_pro to a variable and an additional constraint (m.cap_pro_abs)
    m.del_component(m.cap_pro)
    m.cap_pro = pyomo.Var(
        m.pro_tuples,
        within=pyomo.NonNegativeReals,
        doc='Total process capacity (MW)')
    m.cap_pro_abs = pyomo.Constraint(
        m.pro_tuples,
        rule=cap_pro_abs_rule,
        doc='capacity = cap_new + cap_installed')

    # Change the constraint m.res_process_capacity to a MILP constraint
    m.del_component(m.res_process_capacity)
    m.res_process_capacity_MILP_low = pyomo.Constraint(
        m.pro_tuples,
        rule=res_process_capacity_rule_low,
        doc='[0/1] * process.cap-lo <= total process capacity <= process.cap-up')
    m.res_process_capacity_MILP_up = pyomo.Constraint(
        m.pro_tuples,
        rule=res_process_capacity_rule_up,
        doc='[0/1] * process.cap-lo <= total process capacity <= process.cap-up')

    # Storage
    if m.mode['sto']:
        m.cap_sto_build = pyomo.Var(
            m.sto_tuples,
            within=pyomo.Boolean,
            doc='Boolean: True if new capacity is build. Needed for minimum new capacity')

        # Change expression m.cap_sto_c to a variable and an additional constraint (m.cap_sto_c_abs)
        m.del_component(m.cap_sto_c)
        m.cap_sto_c = pyomo.Var(
            m.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total storage size (MWh)')
        m.cap_sto_c_abs = pyomo.Constraint(
            m.sto_tuples,
            rule=cap_sto_c_abs_rule,
            doc='capacity = cap_new + cap_installed')

        m.del_component(m.res_storage_capacity)
        m.res_storage_capacity_MILP_low = pyomo.Constraint(
            m.sto_tuples,
            rule=res_storage_capacity_rule_low,
            doc='[0/1] * storage.cap-lo-c <= storage capacity <= storage.cap-up-c')
        m.res_storage_capacity_MILP_up = pyomo.Constraint(
            m.sto_tuples,
            rule=res_storage_capacity_rule_up,
            doc='[0/1] * storage.cap-lo-c <= storage capacity <= storage.cap-up-c')

        # Change expression m.cap_sto_p to a variable and an additional constraint (m.cap_sto_p_abs)
        m.del_component(m.cap_sto_p)
        m.cap_sto_p = pyomo.Var(
            m.sto_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total storage power (MW)')
        m.cap_sto_p_abs = pyomo.Constraint(
            m.sto_tuples,
            rule=cap_sto_p_abs_rule,
            doc='power = power_new + power_installed')

        m.del_component(m.res_storage_power)
        m.res_storage_power_MILP_low = pyomo.Constraint(
            m.sto_tuples,
            rule=res_storage_power_rule_low,
            doc='[0/1] * storage.cap-lo-p <= storage power <= storage.cap-up-p')
        m.res_storage_power_MILP_up = pyomo.Constraint(
            m.sto_tuples,
            rule=res_storage_power_rule_up,
            doc='[0/1] * storage.cap-lo-p <= storage power <= storage.cap-up-p')

    if m.mode['tra']:
        m.cap_tra_build = pyomo.Var(
            m.tra_tuples,
            within=pyomo.Boolean,
            doc='Boolean: True if new capacity is build. Needed for minimum new capacity')
        
        # Change expression m.cap_tra to a variable and an additional constraint (m.cap_tra_abs)
        m.del_component(m.cap_tra)
        m.cap_tra = pyomo.Var(
            m.tra_tuples,
            within=pyomo.NonNegativeReals,
            doc='Total transmission capacity (MW)')
        m.cap_tra_abs = pyomo.Constraint(
            m.tra_tuples,
            rule=cap_tra_abs_rule,
            doc='capacity = cap_new + cap_installed')

        # Change the constraint m.res_process_capacity to a MILP constraint
        m.del_component(m.res_transmission_capacity)
        m.res_transmission_capacity_MILP_low = pyomo.Constraint(
            m.tra_tuples,
            rule=res_transmission_capacity_rule_low,
            doc='[0/1] * transmission.cap-lo <= total transmission capacity <= transmission.cap-up')
        m.res_transmission_capacity_MILP_up = pyomo.Constraint(
            m.tra_tuples,
            rule=res_transmission_capacity_rule_up,
            doc='[0/1] * transmission.cap-lo <= total transmission capacity <= transmission.cap-up')
    return m


# process capacity: capacity = cap_new + cap_installed
def cap_pro_abs_rule(m, stf, sit, pro):
    if m.mode['int']:
        if (sit, pro, stf) in m.inst_pro_tuples:
            if (sit, pro, min(m.stf)) in m.pro_const_cap_dict:
                return m.cap_pro[stf, sit, pro] == m.process_dict['inst-cap'][(stf, sit, pro)]
            else:
                return m.cap_pro[stf, sit, pro] == \
                       (sum(m.cap_pro_new[stf_built, sit, pro]
                            for stf_built in m.stf
                            if (sit, pro, stf_built, stf)
                            in m.operational_pro_tuples) +
                        m.process_dict['inst-cap'][(min(m.stf), sit, pro)])
        else:
            return m.cap_pro[stf, sit, pro] == sum(
                m.cap_pro_new[stf_built, sit, pro]
                for stf_built in m.stf
                if (sit, pro, stf_built, stf) in m.operational_pro_tuples)
    else:
        if (sit, pro, stf) in m.pro_const_cap_dict:
            return m.cap_pro[stf, sit, pro] == m.process_dict['inst-cap'][(stf, sit, pro)]
        else:
            return m.cap_pro[stf, sit, pro] == (m.cap_pro_new[stf, sit, pro] +
                                                m.process_dict['inst-cap'][(stf, sit, pro)])


# [0/1] * lower bound <= process capacity
def res_process_capacity_rule_low(m, stf, sit, pro):
    return m.cap_pro_build[stf, sit, pro] * m.process_dict['cap-lo'][stf, sit, pro] <= m.cap_pro[stf, sit, pro]


# process capacity <= [0/1] * upper bound
def res_process_capacity_rule_up(m, stf, sit, pro):
    return m.cap_pro[stf, sit, pro] <= m.cap_pro_build[stf, sit, pro] * m.process_dict['cap-up'][stf, sit, pro]


# storage capacity: capacity = cap_new + cap_installed
def cap_sto_c_abs_rule(m, stf, sit, sto, com):
    if m.mode['int']:
        if (sit, sto, com, stf) in m.inst_sto_tuples:
            if (min(m.stf), sit, sto, com) in m.sto_const_cap_c_dict:
                return m.cap_sto_c[stf, sit, sto, com] == m.storage_dict['inst-cap-c'][(min(m.stf), sit, sto, com)]
            else:
                return m.cap_sto_c[stf, sit, sto, com] == (
                    sum(m.cap_sto_c_new[stf_built, sit, sto, com]
                        for stf_built in m.stf
                        if (sit, sto, com, stf_built, stf) in
                        m.operational_sto_tuples) +
                    m.storage_dict['inst-cap-c'][(min(m.stf), sit, sto, com)])
        else:
            return m.cap_sto_c[stf, sit, sto, com] == (
                sum(m.cap_sto_c_new[stf_built, sit, sto, com]
                    for stf_built in m.stf
                    if (sit, sto, com, stf_built, stf) in
                    m.operational_sto_tuples))
    else:
        if (stf, sit, sto, com) in m.sto_const_cap_c_dict:
            return m.cap_sto_c[stf, sit, sto, com] == m.storage_dict['inst-cap-c'][(stf, sit, sto, com)]
        else:
            return m.cap_sto_c[stf, sit, sto, com] == (m.cap_sto_c_new[stf, sit, sto, com] +
                                                       m.storage_dict['inst-cap-c'][(stf, sit, sto, com)])


# [0/1] * lower bound <= storage capacity
def res_storage_capacity_rule_low(m, stf, sit, sto, com):
    return (m.cap_sto_build[(stf, sit, sto, com)] * m.storage_dict['cap-lo-c'][(stf, sit, sto, com)] <=
            m.cap_sto_c[stf, sit, sto, com])


# storage capacity <= [0/1] * upper bound
def res_storage_capacity_rule_up(m, stf, sit, sto, com):
    return (m.cap_sto_c[stf, sit, sto, com] <=
            m.cap_sto_build[(stf, sit, sto, com)] * m.storage_dict['cap-up-c'][(stf, sit, sto, com)])


# storage power: power = power_new + power_installed
def cap_sto_p_abs_rule(m, stf, sit, sto, com):
    if m.mode['int']:
        if (sit, sto, com, stf) in m.inst_sto_tuples:
            if (min(m.stf), sit, sto, com) in m.sto_const_cap_p_dict:
                return m.cap_sto_p[stf, sit, sto, com] == m.storage_dict['inst-cap-p'][(min(m.stf), sit, sto, com)]
            else:
                return m.cap_sto_p[stf, sit, sto, com] == (
                    sum(m.cap_sto_p_new[stf_built, sit, sto, com]
                        for stf_built in m.stf
                        if (sit, sto, com, stf_built, stf) in
                        m.operational_sto_tuples) +
                    m.storage_dict['inst-cap-p'][(min(m.stf), sit, sto, com)])
        else:
            return m.cap_sto_p[stf, sit, sto, com] == (
                sum(m.cap_sto_p_new[stf_built, sit, sto, com]
                    for stf_built in m.stf
                    if (sit, sto, com, stf_built, stf)
                    in m.operational_sto_tuples))
    else:
        if (stf, sit, sto, com) in m.sto_const_cap_p_dict:
            return m.cap_sto_p[stf, sit, sto, com] == m.storage_dict['inst-cap-p'][(stf, sit, sto, com)]
        else:
            return m.cap_sto_p[stf, sit, sto, com] == \
                   (m.cap_sto_p_new[stf, sit, sto, com] + m.storage_dict['inst-cap-p'][(stf, sit, sto, com)])


# [0/1] * lower bound <= storage power
def res_storage_power_rule_low(m, stf, sit, sto, com):
    return (m.cap_sto_build[(stf, sit, sto, com)] * m.storage_dict['cap-lo-p'][(stf, sit, sto, com)] <=
            m.cap_sto_p[stf, sit, sto, com])


# storage power <= [0/1] * upper bound
def res_storage_power_rule_up(m, stf, sit, sto, com):
    return (m.cap_sto_p[stf, sit, sto, com] <=
            m.cap_sto_build[(stf, sit, sto, com)] * m.storage_dict['cap-up-p'][(stf, sit, sto, com)])


# transmission capacity: capacity = cap_new + cap_installed
def cap_tra_abs_rule(m, stf, sin, sout, tra, com):
    if m.mode['int']:
        if (sin, sout, tra, com, stf) in m.inst_tra_tuples:
            if (min(m.stf), sin, sout, tra, com) in m.tra_const_cap_dict:
                return m.cap_tra[stf, sin, sout, tra, com] == \
                       m.transmission_dict['inst-cap'][(min(m.stf), sin, sout, tra, com)]
            else:
                return m.cap_tra[stf, sin, sout, tra, com] == (
                    sum(m.cap_tra_new[stf_built, sin, sout, tra, com]
                        for stf_built in m.stf
                        if (sin, sout, tra, com, stf_built, stf) in
                        m.operational_tra_tuples) +
                    m.transmission_dict['inst-cap']
                    [(min(m.stf), sin, sout, tra, com)])
        else:
            return m.cap_tra[stf, sin, sout, tra, com] == (
                sum(m.cap_tra_new[stf_built, sin, sout, tra, com]
                    for stf_built in m.stf
                    if (sin, sout, tra, com, stf_built, stf) in
                    m.operational_tra_tuples))
    else:
        if (stf, sin, sout, tra, com) in m.tra_const_cap_dict:
            return m.cap_tra[stf, sin, sout, tra, com] == m.transmission_dict['inst-cap'][(stf, sin, sout, tra, com)]
        else:
            return m.cap_tra[stf, sin, sout, tra, com] == (m.cap_tra_new[stf, sin, sout, tra, com] +
                                                           m.transmission_dict['inst-cap'][(stf, sin, sout, tra, com)])


# [0/1] * lower bound <= transmission capacity
def res_transmission_capacity_rule_low(m, stf, sin, sout, tra, com):
    return (m.cap_tra_build[stf, sin, sout, tra, com] * m.transmission_dict['cap-lo'][(stf, sin, sout, tra, com)] <=
            m.cap_tra[stf, sin, sout, tra, com])


# transmission capacity <= [0/1] * upper bound
def res_transmission_capacity_rule_up(m, stf, sin, sout, tra, com):
    return(m.cap_tra[stf, sin, sout, tra, com] <=
           m.cap_tra_build[stf, sin, sout, tra, com] * m.transmission_dict['cap-up'][(stf, sin, sout, tra, com)])

