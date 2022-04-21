import numpy as np
import pandas as pd
import model
import scipy.optimize as opt
import conversions
import graph
import initialize
import time

class Optimizer():
    def __init__(self, model: model.Model, opt_tolerance: float = 1e-5, \
        purityLB: float = 0.99, purityUB: float = 1.0,\
            recoveryLB: float = 0.99, recoveryUB: float = 1.0):
        self.opt_tolerance = opt_tolerance
        self.model = model
        self.time = 0
        self.start_time = time.time()
        self.func_iter = 0
        self.opt_iter = 0

        self.purityLB = purityLB
        self.purityUB = purityUB
        self.recoveryLB = recoveryLB
        self.recoveryUB = recoveryUB

        self.h_w = 50 #mm (Assumption)
        self.hole_diameter = 5 #mm (Assumption)
        self.plate_thickness = 5 #mm (Assumption)
        self.frac_appr_flooding = 0.8 #Assumption

        # Assumptions from "Design of equilibrium stage processes" Pg 527 Table 14.3
        self.slot_shape_ratio = 0.5 #Assume trapezoidal slots
        self.slot_height = conversions.inch_to_m(1.250) #Assume 1.25 inch slot height
        self.riser_area_per_tray = conversions.sqft_to_m2(18.7) #Assume 18.7 sq ft riser area per tray
        self.static_seal = conversions.inch_to_m(0.5) #Assume 0.5 inch static seal
        self.annular_riser_area_ratio = 1.25 #Assume 1.25:1 annular riser area ratio
        self.A_da = conversions.sqft_to_m2(1.0) # Minimum area under downflow apron = 1sqft
        self.slot_area_per_tray = conversions.sqft_to_m2(31.5) #Assume 31.5 sq ft total slot area per tray

    def func_net_area(self):
        return self.model.A_c - self.model.A_d

    def func_active_area(self):
        return self.func_net_area() - self.model.A_d
    
    def func_hole_area(self):
        return 0.1 * self.func_active_area()

    def func_L(self, section):
        if section == "top":
            return self.model.RR * self.model.D[0]
        elif section == "bottom":
            return self.model.RR * self.model.D[0] + self.model.feed_flow_rate
        else:
            raise AssertionError("Section must be either top or bottom")
    
    def func_max_liquid_flow_rate(self, section):
        molecular_weight_liquid = self.model.molecular_weight_liquid[0] if section == "top" else self.model.molecular_weight_liquid[-1]
        return self.func_L(section) * molecular_weight_liquid / 3600 # Conversion from kmol/hr to kg/s
    
    def func_min_liquid_flow_rate(self, section):
        return 0.7 * self.func_max_liquid_flow_rate(section)

    def func_density_liquid(self, section):
        return conversions.gmCc_to_kgM3(self.model.density_liquid[0] if section == "top" else self.model.density_liquid[-1])
    
    def func_density_vapour(self, section):
        return conversions.gmCc_to_kgM3(self.model.density_vapour[0] if section == "top" else self.model.density_vapour[-2])

    def func_volume_flow_vapour(self, section):
        return conversions.lMin_to_m3Sec(self.model.volume_flow_vapour[0] if section == "top" else self.model.volume_flow_vapour[-2])
        
    def func_h_ow(self, value, section):
        if value == 'max':
            return ((self.func_max_liquid_flow_rate(section) / (self.func_density_liquid(section) * self.model.weir_length)) ** (2./3)) * 1000  # Conversion to mm
        else:
            return ((self.func_min_liquid_flow_rate(section) / (self.func_density_liquid(section) * self.model.weir_length)) ** (2./3)) * 1000  # Conversion to mm

    def func_h_w_h_ow_min(self, section):
        return self.h_w + self.func_h_ow('min', section)

    def func_actual_min_vapour_vel(self, section):
        return 0.7 * self.func_volume_flow_vapour(section) / self.func_hole_area()

    def func_min_vapour_vel(self, section):
         return (graph.K2(self.func_h_w_h_ow_min(section))-0.9*(25.4-self.hole_diameter))/(self.func_density_vapour(section)**(1./2))
    
    def func_A_ap(self):
        return (self.h_w - 10) * self.model.weir_length * (10 ** -3) # Change to m

    def func_h_dc(self, section):
        if self.model.tray_type == 'SIEVE':
            return 166 * ((self.func_max_liquid_flow_rate(section) / (self.func_density_liquid(section) * (self.model.A_d if self.model.A_d<self.func_A_ap() else self.func_A_ap())))**2)
        elif self.model.tray_type == 'CAPS':
            return self.func_h_t(section) + self.h_w + self.func_h_ow('max', section) + self.func_delta() + self.func_h_da(section)

    def func_h_da(self, section):
        Lw = conversions.m_to_inch(self.model.weir_length)
        A_da = conversions.m2_to_sqft(self.A_da)
        return conversions.inch_to_m(0.03 * (Lw/2/100/A_da) ** 2)

    def func_max_vapour_vel(self, section):
        return self.func_volume_flow_vapour(section) / self.func_hole_area()

    def func_h_d(self, section):
        # TODO: Bubble Cap Change for Orifice
        orifice_coeff = graph.orifice((self.func_hole_area()/self.func_active_area()), self.plate_thickness/self.hole_diameter)
        return 51 * ((self.func_max_vapour_vel(section) / orifice_coeff) **2) * (self.func_density_vapour(section)/self.func_density_liquid(section))

    def func_h_r(self, section):
        return 12500 / self.func_density_liquid(section)

    def func_h_t(self, section):
        if self.model.tray_type == 'SIEVE':
            return self.func_h_d(section) + self.h_w + self.func_h_ow('max', section) + self.func_h_r(section)
        elif self.model.tray_type == 'CAPS':
            return self.func_h_cd(section) + self.func_h_so(section) + self.func_h_al(section)

    def func_h_al(self, section):
        volume_flow_vapour = conversions.m3Sec_to_cfs(self.func_volume_flow_vapour(section))
        active_area = conversions.m2_to_sqft(self.func_active_area())
        density_vapour = conversions.kgM3_to_lbFt3(self.func_density_vapour(section))
        F_va = volume_flow_vapour / active_area * (density_vapour ** (1./2))
        return graph.aeration_factor(F_va) # Fig 14.15

    def func_h_b(self, section):
        # NOTE: Need to round up h_dc?
        return self.h_w + self.func_h_ow('max', section) + self.func_h_t(section) + self.func_h_dc(section)

    def func_v(self):
        return self.model.D[0] * (1 + self.model.RR)

    def func_f_lv(self, section):
        return (self.func_L(section) / self.func_v()) * ((self.func_density_vapour(section) / self.func_density_liquid(section)) ** (1./2))

    def func_flooding_vapour_velocity(self, section):
        return graph.K1(self.func_f_lv(section), self.model.tray_spacing, self.model.tray_type) * (((self.func_density_liquid(section) - self.func_density_vapour(section))/self.func_density_vapour(section)) ** (1./2))

    def func_u_n(self, section):
        return self.frac_appr_flooding * self.func_flooding_vapour_velocity(section)

    def func_net_area_required(self):
        return max(self.func_volume_flow_vapour(section)/self.func_u_n(section) for section in ['top', 'bottom'])

    def func_percent_flooding(self, section):
        u_v = self.func_volume_flow_vapour(section) / self.func_net_area_required()
        return u_v / self.func_flooding_vapour_velocity(section)

    def func_q_max(self, section):
        As = 0.12 * conversions.m2_to_sqft(self.slot_area_per_tray)
        Rs = self.slot_shape_ratio
        slot_height = conversions.m_to_inch(self.slot_height)
        density_liquid = conversions.kgM3_to_lbFt3(self.func_density_liquid(section))
        density_vapour = conversions.kgM3_to_lbFt3(self.func_density_vapour(section))
        qMax = 2.36 * As * ((2./3) * (Rs/(1+Rs)) + (4./15) * ((1-Rs)/(1+Rs))) * ((slot_height * (density_liquid - density_vapour)/ density_vapour) ** (1./2))
        return conversions.cfs_to_m3Sec(qMax)

    def func_h_cd(self, section):
        density_liquid = conversions.kgM3_to_lbFt3(self.func_density_liquid(section))
        density_vapour = conversions.kgM3_to_lbFt3(self.func_density_vapour(section))
        volume_flow_vapour = conversions.m3Sec_to_cfs(self.func_volume_flow_vapour(section))
        riser_area = conversions.m2_to_sqft(self.riser_area_per_tray)
        h_cd = graph.dry_cap_coeff(self.annular_riser_area_ratio) * density_vapour/density_liquid * (volume_flow_vapour/riser_area)**2
        return conversions.inch_to_m(h_cd)

    def func_h_so(self, section):
        vapour_load = self.func_volume_flow_vapour(section) / self.func_q_max(section)
        slot_opening_slot_height = graph.slot_opening_corelation(vapour_load) # Fuig 14.6 Pg 504
        return self.slot_height * slot_opening_slot_height

    def func_weeping_check(self, section):
        return self.func_percent_flooding(section) > 0.5

    def func_delta(self):
        return conversions.inch_to_m(1.3) #Assume delta of 1.3 inches
    
    def func_q(self, section):
        A_da = conversions.m2_to_sqft(self.A_da)
        h_da = conversions.m_to_inch(self.func_h_da(section))
        g = conversions.m_to_ft(9.81)
        q = 0.6 * A_da * ((2 * g * h_da / 12)**(1./2))
        return conversions.cfs_to_m3Sec(q)

    def func_t_dc (self, section):
        A_d = conversions.m2_to_sqft(self.model.A_d)
        h_dc = conversions.m_to_inch(self.func_h_dc(section))
        t_dc = A_d * h_dc / (12 * conversions.m3Sec_to_cfs(self.func_q(section)))
        return t_dc

    def func_h_c(self, section):
        return self.func_h_cd(section) + self.func_h_so(section)

    def func_h_ds(self, section):
        static_slot_seal = conversions.m_to_inch(self.static_seal)
        h_ow = conversions.m_to_inch(self.func_h_ow('max', section)/1000)
        delta = conversions.m_to_inch(self.func_delta())
        return conversions.inch_to_m(static_slot_seal + h_ow + delta/2)

    def func_h_fd(self, section):
        return self.func_h_dc(section) / 0.5

    def entrainmentCheck(self, section):
        return self.frac_appr_flooding - self.func_percent_flooding(section) # percent of flooding should be less than frac_appr_flooding

    def entrainmentFracCheck(self, section):
        frac_entrainment = graph.frac(self.func_f_lv(section), self.func_percent_flooding(section),self.model.tray_type)
        return 0.1 - frac_entrainment # frac_entrainment should be less than 0.1

    def slotOpeningCheck(self, section):
        vapour_load = self.func_volume_flow_vapour(section) / self.func_q_max(section)
        slot_opening_slot_height = graph.slot_opening_corelation(vapour_load) # Fig 14.6 Pg 504
        return 1 - slot_opening_slot_height

    def slotSealLBCheck(self, section):
        return conversions.m_to_inch(self.func_h_ds(section)) - 1.0

    def slotSealUBCheck(self, section):
        return (2.6 - conversions.m_to_inch(self.func_h_ds(section)))/10.0 # Scale for constraints

    def vapourDistRatioCheck(self, section):
        return (0.5 - (self.func_delta() / self.func_h_c(section)))/10.0 # Scale for constraints

    def weepingCheck(self, section):
        # actual_min_vapour_vel > min_vapour_vel
        return (self.func_actual_min_vapour_vel(section) - self.func_min_vapour_vel(section))/5.0 # Scale for constraints

    def downcomerLiquidBackupCheck(self, section):
        if self.model.tray_type == 'SIEVE':
            return  0.5 * (self.model.tray_spacing + (self.h_w/1000)) - self.func_h_b(section)/1000 # Should be larger than 0 (pg 882 towler sinnot)
        elif self.model.tray_type == 'CAPS':
            return self.model.tray_spacing + (self.h_w/1000) - self.func_h_fd(section)/1000 # Should be larger than 0
    
    def downcomerResidenceTimeCheck(self, section):
        if self.model.tray_type == 'SIEVE':
            self.residence_time = (self.model.A_d * self.func_h_b(section) * (10 ** -3) * self.func_density_liquid(section)) / (self.func_max_liquid_flow_rate(section))
            return (self.residence_time - 3)/10.0 # Should be larger than 3s # Scale for constraints
        elif self.model.tray_type == 'CAPS':
            self.residence_time = self.func_t_dc(section)
            return (self.residence_time - 3)/1000.0 # Should be larger than 3s # Scale for constraints

    def slotOpeningCheckTop(self, x):
        return self.slotOpeningCheck('top')

    def slotOpeningCheckBottom(self, x):
        return self.slotOpeningCheck('bottom')

    def slotSealLBCheckTop(self, x):
        return self.slotSealLBCheck('top')
    
    def slotSealLBCheckBottom(self, x):
        return self.slotSealLBCheck('bottom')

    def slotSealUBCheckTop(self, x):
        return self.slotSealUBCheck('top')
    
    def slotSealUBCheckBottom(self, x):
        return self.slotSealUBCheck('bottom')

    def vapourDistRatioCheckTop(self, x):
        return self.vapourDistRatioCheck('top')

    def vapourDistRatioCheckBottom(self, x):
        return self.vapourDistRatioCheck('bottom')

    def weepingCheckTop(self, x):
        return self.weepingCheck('top')
    
    def weepingCheckBottom(self, x):
        return self.weepingCheck('bottom')
    
    def entrainmentCheckTop(self, x):
        return self.entrainmentCheck('top')
    
    def entrainmentCheckBottom(self, x):
        return self.entrainmentCheck('bottom')

    def entrainmentFracCheckTop(self, x):
        return self.entrainmentFracCheck('top')

    def entrainmentFracCheckBottom(self, x):
        return self.entrainmentFracCheck('bottom')

    def downcomerLiquidBackupCheckTop(self, x):
        return self.downcomerLiquidBackupCheck('top')

    def downcomerLiquidBackupCheckBottom(self, x):
        return self.downcomerLiquidBackupCheck('bottom')

    def downcomerResidenceTimeCheckTop(self, x):
        return self.downcomerResidenceTimeCheck('top')

    def downcomerResidenceTimeCheckBottom(self, x):
        return self.downcomerResidenceTimeCheck('bottom')

    def inputPresCheck(self, x):
        try:
            diff = self.model.stream_input_pres - self.model.P_stage[self.model.feed_stage-1]
        except IndexError as e:
            print (e)
            diff = 0.01
        return diff

    def callback(self, x):
        self.func_iter = 0
        if self.model.hydraulics:
            print ('{0:4d}   {1:3.9f}   {2:3.9f}   {3:3.9f}   {4:3.9f}   {5:3.9f}   {6:3.9f}   {7:3.9f}   {8:3.9f}   {9:3.9f}'.format(self.opt_iter, x[0], x[1], x[2], x[3], x[4], x[5], x[6], self.model.TAC, self.time))
        else:
            if self.model.const_pres:
                print ('{0:4d}   {1:3.9f}   {2:3.9f}   {3:3.9f}   {4:3.9f}   {5:3.9f}   {6:3.9f}'.format(self.opt_iter, x[0], x[1], x[2], x[3], self.model.TAC, self.time))
            else:
                print ('{0:4d}   {1:3.9f}   {2:3.9f}   {3:3.9f}   {4:3.9f}   {5:3.9f}   {6:3.9f}   {7:3.9f}'.format(self.opt_iter, x[0], x[1], x[2], x[3], x[4], self.model.TAC, self.time))
        self.opt_iter += 1

    def optimize(self):
        self.model.distilate_rate = initialize.distilate_rate(self.model, recovery_LB=self.recoveryLB)
        if self.model.hydraulics:
            x0 = [
                self.model.P_cond, 
                self.model.P_drop_1, 
                self.model.P_drop_2, 
                initialize.min_RR(self.model), 
                initialize.feed_stage(self.model, self.recoveryLB) / initialize.actual_N(self.model, self.recoveryLB), 
                1 - (initialize.feed_stage(self.model, self.recoveryLB) / initialize.actual_N(self.model, self.recoveryLB)),
                self.model.tray_spacing,
                ]

            self.model.distilate_rate = initialize.distilate_rate(self.model, recovery_LB=self.recoveryLB)

            if self.model.tray_type == 'SIEVE':
                constraints = (
                    # Results Constraint
                    {'type': 'ineq', 'fun': lambda x: self.model.purity[self.model.main_component] - self.purityLB},
                    {'type': 'ineq', 'fun': lambda x: self.purityUB - self.model.purity[self.model.main_component]},
                    {'type': 'ineq', 'fun': lambda x: self.model.recovery[self.model.main_component] - self.recoveryLB},
                    {'type': 'ineq', 'fun': lambda x: self.recoveryUB - self.model.recovery[self.model.main_component]},
                    {'type': 'ineq', 'fun': self.inputPresCheck},
                    {'type': 'ineq', 'fun': self.weepingCheckTop},
                    {'type': 'ineq', 'fun': self.downcomerLiquidBackupCheckTop},
                    {'type': 'ineq', 'fun': self.downcomerResidenceTimeCheckTop},
                    {'type': 'ineq', 'fun': self.entrainmentCheckTop},
                    {'type': 'ineq', 'fun': self.entrainmentFracCheckTop},
                    {'type': 'ineq', 'fun': self.weepingCheckBottom},
                    {'type': 'ineq', 'fun': self.downcomerLiquidBackupCheckBottom},
                    {'type': 'ineq', 'fun': self.downcomerResidenceTimeCheckBottom},
                    {'type': 'ineq', 'fun': self.entrainmentCheckBottom},
                    {'type': 'ineq', 'fun': self.entrainmentFracCheckBottom},
                )
            elif self.model.tray_type == 'CAPS':
                constraints = (
                    # Results Constraint
                    {'type': 'ineq', 'fun': lambda x: self.model.purity[self.model.main_component] - self.purityLB},
                    {'type': 'ineq', 'fun': lambda x: self.purityUB - self.model.purity[self.model.main_component]},
                    {'type': 'ineq', 'fun': lambda x: self.model.recovery[self.model.main_component] - self.recoveryLB},
                    {'type': 'ineq', 'fun': lambda x: self.recoveryUB - self.model.recovery[self.model.main_component]},
                    {'type': 'ineq', 'fun': self.inputPresCheck},
                    {'type': 'ineq', 'fun': self.entrainmentCheckTop},
                    {'type': 'ineq', 'fun': self.entrainmentFracCheckTop},
                    {'type': 'ineq', 'fun': self.slotOpeningCheckTop},
                    {'type': 'ineq', 'fun': self.slotSealLBCheckTop},
                    {'type': 'ineq', 'fun': self.slotSealUBCheckTop},
                    # {'type': 'ineq', 'fun': self.vapourDistRatioCheckTop},
                    {'type': 'ineq', 'fun': self.downcomerLiquidBackupCheckTop},
                    {'type': 'ineq', 'fun': self.downcomerResidenceTimeCheckTop},
                    {'type': 'ineq', 'fun': self.entrainmentCheckBottom},
                    {'type': 'ineq', 'fun': self.entrainmentFracCheckBottom},
                    {'type': 'ineq', 'fun': self.slotOpeningCheckBottom},
                    {'type': 'ineq', 'fun': self.slotSealLBCheckBottom},
                    {'type': 'ineq', 'fun': self.slotSealUBCheckBottom},
                    # {'type': 'ineq', 'fun': self.vapourDistRatioCheckBottom},
                    {'type': 'ineq', 'fun': self.downcomerLiquidBackupCheckBottom},
                    {'type': 'ineq', 'fun': self.downcomerResidenceTimeCheckBottom},
                )
            bounds = opt.Bounds([1.013, 0.01, 0.01, initialize.min_RR(self.model), 0.1, 0.1, 0.15], [10.0, 1.0, 1.0, 1.2 * initialize.min_RR(self.model), 1.0, 1.0, 1.0], keep_feasible=True),
            print ('{0:4s}   {1:11s}   {2:11s}   {3:11s}   {4:11s}   {5:11s}   {6:11s}   {7:11s}   {8:11s}   {9:11s}'.format('Iter', ' P_cond', 'P_drop_1', 'P_drop_2', 'RR', 'tray_eff_1', 'tray_eff_2', 'tray_spacing', 'TAC', 'Runtime'))
            print ('{0:4s}   {1:3.9f}   {2:3.9f}   {3:3.9f}   {4:3.9f}   {5:3.9f}   {6:3.9f}   {7:3.9f}   {8:11s}   {9:3.9f}'.format("Init", x0[0], x0[1], x0[2], x0[3], x0[4], x0[5], x0[6], "----", self.time))
        else:
            if self.model.const_pres:
                x0 = [
                    self.model.P_cond,
                    initialize.min_RR(self.model), 
                    initialize.feed_stage(self.model, self.recoveryLB) / initialize.actual_N(self.model, self.recoveryLB), 
                    1 - (initialize.feed_stage(self.model, self.recoveryLB) / initialize.actual_N(self.model, self.recoveryLB)),
                    ]

                constraints = (
                    # Results Constraint
                    {'type': 'ineq', 'fun': lambda x: self.model.purity[self.model.main_component] - self.purityLB},
                    {'type': 'ineq', 'fun': lambda x: self.purityUB - self.model.purity[self.model.main_component]},
                    {'type': 'ineq', 'fun': lambda x: self.model.recovery[self.model.main_component] - self.recoveryLB},
                    {'type': 'ineq', 'fun': lambda x: self.recoveryUB - self.model.recovery[self.model.main_component]},
                    {'type': 'ineq', 'fun': self.inputPresCheck},
                    )
                bounds = opt.Bounds([1.013, initialize.min_RR(self.model), 0.1, 0.1], [10.0, 1.2 * initialize.min_RR(self.model), 1.0, 1.0], keep_feasible=True),
                print ('{0:4s}   {1:11s}   {2:11s}   {3:11s}   {4:11s}   {5:11s}   {6:11s}'.format('Iter', ' P_cond', 'RR', 'tray_eff_1', 'tray_eff_2', 'TAC', 'Runtime'))
                print ('{0:4s}   {1:3.9f}   {2:3.9f}   {3:3.9f}   {4:3.9f}   {5:11s}   {6:3.9f}'.format("Init", x0[0], x0[1], x0[2], x0[3], "----", self.time))

            else:
                x0 = [
                    self.model.P_cond,
                    self.model.P_drop_1,
                    initialize.min_RR(self.model), 
                    initialize.feed_stage(self.model, self.recoveryLB) / initialize.actual_N(self.model, self.recoveryLB), 
                    1 - (initialize.feed_stage(self.model, self.recoveryLB) / initialize.actual_N(self.model, self.recoveryLB)),
                    ]

                constraints = (
                    # Results Constraint
                    {'type': 'ineq', 'fun': lambda x: self.model.purity[self.model.main_component] - self.purityLB},
                    {'type': 'ineq', 'fun': lambda x: self.purityUB - self.model.purity[self.model.main_component]},
                    {'type': 'ineq', 'fun': lambda x: self.model.recovery[self.model.main_component] - self.recoveryLB},
                    {'type': 'ineq', 'fun': lambda x: self.recoveryUB - self.model.recovery[self.model.main_component]},
                    {'type': 'ineq', 'fun': self.inputPresCheck},
                    )
                bounds = opt.Bounds([1.013, 0, initialize.min_RR(self.model), 0.1, 0.1], [10.0, 10.0, 1.2 * initialize.min_RR(self.model), 1.0, 1.0], keep_feasible=True)
                print ('{0:4s}   {1:11s}   {2:11s}   {3:11s}   {4:11s}   {5:11s}   {6:11s}   {7:11s}'.format('Iter', ' P_cond', ' P_drop', 'RR', 'tray_eff_1', 'tray_eff_2', 'TAC', 'Runtime'))
                print ('{0:4s}   {1:3.9f}   {2:3.9f}   {3:3.9f}   {4:3.9f}   {5:3.9f}   {6:11s}   {7:3.9f}'.format("Init", x0[0], x0[1], x0[2], x0[3], x0[4], "----", self.time))

        result = opt.minimize(
            self.objective,
            x0, 
            constraints = constraints,
            bounds = bounds,
            callback = self.callback,
            method='SLSQP', 
            options={'disp': True, 'maxiter':2000}, 
            tol = self.opt_tolerance
        )
        return result

    def objective(self, x):
        try:
            if self.model.hydraulics == True:
                self.model.P_cond = float(x[0])
                self.model.P_drop_1 = float(x[1])
                self.model.P_drop_2 = float(x[2])
                self.model.RR = float(x[3])
                self.model.tray_eff_1 = float(x[4])
                self.model.tray_eff_2 = float(x[5])
                self.model.tray_spacing = float(x[6])
            else:
                self.model.P_cond = float(x[0])
                self.model.RR = float(x[1])
                self.model.tray_eff_1 = float(x[2])
                self.model.tray_eff_2 = float(x[3])
            runtime = self.model.run()
            self.time += runtime
            self.func_iter += 1
            return self.model.TAC/1000000
        except Exception as e:
            # If simulation cannot be run, return a large number
            if self.model.hydraulics:
                print ('{0:4d}   {1:3.9f}   {2:3.9f}   {3:3.9f}   {4:3.9f}   {5:3.9f}   {6:3.9f}   {7:3.9f}   {8:11s}   {9:3.9f}'.format(self.func_iter, x[0], x[1], x[2], x[3], x[4], x[5], x[6], "ERROR", self.time))
            else:
                if self.model.const_pres:
                    print ('{0:4d}   {1:3.9f}   {2:3.9f}   {3:3.9f}   {4:3.9f}   {5:11s}   {6:3.9f}'.format(self.func_iter, x[0], x[1], x[2], x[3], "ERROR", self.time))
                else:
                    print ('{0:4d}   {1:3.9f}   {2:3.9f}   {3:3.9f}   {4:3.9f}   {5:3.9f}   {6:11s}   {7:3.9f}'.format(self.func_iter, x[0], x[1], x[2], x[3], x[4], "ERROR", self.time))

            print (e)
            self.func_iter += 1
            return self.model.TAC + 2 * self.opt_tolerance

    def process_results(self):
        x = self.result.x
       
        if self.model.hydraulics == True:
            num_stage = (int(x[4] * 51) + int(x[5] * 50))
            feed_stage = (int(x[4] * 51))
            rr = x[3]
            P_cond = x[0]
            P_drop_1 = x[1]
            P_drop_2 = x[2]
            tray_spacing = x[6]

            self.model.N = num_stage
            self.model.feed_stage = feed_stage
            self.model.RR = rr
            self.model.P_cond = P_cond
            self.model.P_drop_1 = P_drop_1
            self.model.P_drop_2 = P_drop_2
            self.model.tray_spacing = tray_spacing
            self.model.run()

        else:
            num_stage = (int(x[4] * 51) + int(x[5] * 50))
            feed_stage = (int(x[4] * 51))
            rr = x[3]
            P_cond = x[0]
            P_drop_1 = x[1]
            tray_spacing = x[6]

            self.model.N = num_stage
            self.model.feed_stage = feed_stage
            self.model.RR = rr
            self.model.P_cond = P_cond
            self.model.P_drop_1 = P_drop_1
            self.model.tray_spacing = tray_spacing
            self.model.run()

        print ("\n==========")
        print ("Computation")
        print ("==========\n")
        print ("Function Calculations: %d"%self.result.nfev)
        print ("Objective Iterations: %d"%self.result.nit)
        print ("Computational Time: %.2f seconds"%self.time)
        print ("Total ElapsedTime: %.2f seconds"%(time.time() - self.start_time))
        print ("Converged: %s"%self.result.success)

        print ("\n==========")
        print ("General")
        print ("==========\n")
        print ("Total Number of Stages: %d"%num_stage)
        print ("Feed Stage: %d"%feed_stage)
        print ("RR: %.4f"%rr)
        print ("Tray Spacing: %.4f meters"%tray_spacing)
        print ("TAC: $%.2f"%self.model.TAC)

        print ("\n==========")
        print ("Pressure")
        print ("==========\n")
        print ("Condenser Pressure: %.3f bar"%P_cond)
        if self.model.hydraulics:
            print ("Section 1 Pressure Drop: %.3f bar (per stage)"%P_drop_1)
            print ("Section 2 Pressure Drop: %.3f bar (per stage)"%P_drop_2)
        else:
            print ("Column Pressure Drop: %.3f bar"%P_drop_1)


    def run(self):
        self.result = self.optimize()
        self.process_results()
        self.model.close()



        


