import pandas as pd
from .MILP import *
from urbs.pyomoio import get_entity


def add_MILP_equations(m):
    if 'MILP min_cap' in m._data['MILP'].index:
        m = MILP_cap_min(m)

    if 'MILP partload' in m._data['MILP'].index:
        # Choose MILP or MIQP, no clear preference on calculation speed yet
        # m = MIQP_partload(m)
        m = MILP_partload(m)

    return m


def validate_MILP_results(prob):
    # Check if all MILP values are binary
    # Necessary, because values are stored as float
    # If the borders are too big, the values might not be binary anymore
    cap_pro = get_entity(prob, 'cap_pro_build')
    cap_sto = get_entity(prob, 'cap_sto_build')
    cap_tra = get_entity(prob, 'cap_tra_build')
    pro_mode_run = get_entity(prob, 'pro_mode_run')
    pro_mode_startup = get_entity(prob, 'pro_mode_startup')

    for i in cap_pro.index:
        if not (cap_pro.loc[i] == 0 or cap_pro.loc[i] == 1 or pd.isna(cap_pro.loc[i])):
            print('Warning, Boolean Value not 1 or 0:', i, cap_pro.loc[i])

    for i in cap_sto.index:
        if not (cap_sto.loc[i] == 0 or cap_sto.loc[i] == 1 or pd.isna(cap_sto.loc[i]) or cap_sto.loc[i] == 'None'):
            print('Warning, Boolean Value not 1 or 0:', i, cap_sto.loc[i])

    for i in cap_tra.index:
        if not (cap_tra.loc[i] == 0 or cap_tra.loc[i] == 1 or pd.isna(cap_tra.loc[i])):
            print('Warning, Boolean Value not 1 or 0:', i, cap_tra.loc[i])

    for i in pro_mode_run.index:
        if not (pro_mode_run.loc[i] == 0 or pro_mode_run.loc[i] == 1 or pd.isna(pro_mode_run.loc[i])):
            # raise ValueError(i, "Problem with binary value")
            print('Warning, Boolean Value not 1 or 0:', i, pro_mode_run.loc[i])

    for i in pro_mode_startup.index:
        if not (pro_mode_startup.loc[i] == 0 or pro_mode_startup.loc[i] == 1 or pd.isna(pro_mode_startup.loc[i])):
            # raise ValueError(i, "Problem with binary value")
            print('Warning, Boolean Value not 1 or 0:', i, pro_mode_startup.loc[i])
