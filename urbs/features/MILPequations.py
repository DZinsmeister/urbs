import math
import pyomo.core as pyomo

def add_MILP_equations(m):

    if 'MILP min_cap' in m._data['MILP'].index:
        m = MILP_cap_min(m)

    return (m)



def MILP_cap_min(m):

    # Binary Variable if MILP-cap_min is activated
    m.cap_pro_build=pyomo.Var(
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

    return (m)

# process capacity: capacity = cap_new + cap_installed
def cap_pro_abs_rule(m,stf, sit, pro):
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
def res_process_capacity_rule_low(m,stf, sit, pro):
    return(m.cap_pro_build[stf, sit, pro] * m.process_dict['cap-lo'][stf, sit, pro] <= m.cap_pro[stf, sit, pro])

# process capacity <= [0/1] * upper bound
def res_process_capacity_rule_up(m,stf, sit, pro):
    return(m.cap_pro[stf, sit, pro] <= m.cap_pro_build[stf, sit, pro] * m.process_dict['cap-up'][stf, sit, pro])

#             m.process_dict['cap-lo'][stf, sit, pro],
#             m.cap_pro[stf, sit, pro],
#             m.process_dict['cap-up'][stf, sit, pro]