import numpy as np

def K2(h_w_h_ow):
    # Based on: Graph pg 17.37 pg 878
    return 1.6494 * np.log(h_w_h_ow) + 23.434

def K1(f_lv, plate_spacing):
    # Based on: Graph pg 17.34
    A = (plate_spacing * 0.171) - 0.0178
    B = (plate_spacing * -0.2992) + 0.0168
    C = (plate_spacing * 0.1626) + 0.0156
    return A * (f_lv ** 2) + B * f_lv + C

def orifice(perf_area, plt_thickness_hole_diameter):
    # Based on: Graph pg 17.42 of pg 883
    return (0.8 * perf_area - (0.7667 * plt_thickness_hole_diameter ** 4) + (2.0287 * plt_thickness_hole_diameter ** 3) - (1.6231 * plt_thickness_hole_diameter ** 2) + (0.5431 * plt_thickness_hole_diameter) + 0.5796)

def frac(f_lv, percent_flood):
    # Based on: Graph to get frac entrainment (below 0.1) Towler fig17.36 pg 877
    num = 0.009 * (percent_flood ** 3) - 0.007 * (percent_flood ** 2) + 0.0023 * percent_flood + 0.0005
    pow = - 6.7762 * (percent_flood ** 3) + 14.882 * (percent_flood ** 2) - 11.118 * percent_flood + 1.866
    return num * (f_lv ** pow)
