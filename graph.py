import numpy as np

def K2(h_w_h_ow):
    # Based on: Graph pg 17.37 pg 878
    return 1.6494 * np.log(h_w_h_ow) + 23.434

def K1(f_lv, plate_spacing, tray_type):
    if tray_type == 'SIEVE':
        # Based on: Graph pg 17.34
        A = (plate_spacing * 0.171) - 0.0178
        B = (plate_spacing * -0.2992) + 0.0168
        C = (plate_spacing * 0.1626) + 0.0156
        return A * (f_lv ** 2) + B * f_lv + C
    elif tray_type == 'CAPS':
        # Based on: Fig 14.4 Pg 500
        num = 0.4114 * plate_spacing + 0.0896
        exp = -1.0949 * (plate_spacing ** 2) + 1.3572 * plate_spacing - 1.3351
        return num * (np.exp(exp * f_lv))

def orifice(perf_area, plt_thickness_hole_diameter):
    # Based on: Graph pg 17.42 of pg 883
    return (0.8 * perf_area - (0.7667 * plt_thickness_hole_diameter ** 4) + (2.0287 * plt_thickness_hole_diameter ** 3) - (1.6231 * plt_thickness_hole_diameter ** 2) + (0.5431 * plt_thickness_hole_diameter) + 0.5796)

def frac(f_lv, percent_flood, tray_type):
    if tray_type == 'SIEVE':
        # Based on: Graph to get frac entrainment (below 0.1) Towler fig17.36 pg 877
        num = 0.009 * (percent_flood ** 3) - 0.007 * (percent_flood ** 2) + 0.0023 * percent_flood + 0.0005
        pow = - 6.7762 * (percent_flood ** 3) + 14.882 * (percent_flood ** 2) - 11.118 * percent_flood + 1.866
        return num * (f_lv ** pow)
    elif tray_type == 'CAPS':
        # Based on: Fig 14.5 Pg 502
        log = - 0.1023 * (percent_flood ** 2) + 0.0952 * percent_flood - 0.0439
        incpt = 0.1238 * (percent_flood ** 2) - 0.12 * percent_flood - 0.0096
        return log * np.log(f_lv) + incpt

def slot_opening_corelation(vapour_load):
    # Based on: Fig 14.6 Pg 504
    return -0.7679 * (vapour_load ** 2) + 1.7107 * vapour_load + 0.0329

def dry_cap_coeff(annular_riser_ratio):
    # Based on: Fig 14.14 Pg 512
    return 0.75 * (annular_riser_ratio ** 2) - 2.3293 * annular_riser_ratio + 2.2379

def aeration_factor(vapour_flow_param):
    # Based on: Fig 14.15 Pg 513
    return 0.0679 * (vapour_flow_param ** 2) - 0.03611 * vapour_flow_param + 0.9875