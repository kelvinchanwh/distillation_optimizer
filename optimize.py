import numpy as np
import pandas as pd
import model
import scipy.optimize as opt
import conversions
import graph
from gekko import GEKKO

class Optimizer():
    def __init__(self, model: model.Model, opt_tolerance: float = 0.01, \
        main_component: str = None, purityLB: float = 0.8, purityUB: float = 1.0,\
            recoveryLB: float = 0.8, recoveryUB: float = 1.0):
        self.opt_tolerance = opt_tolerance
        self.model = model

        self.main_component = main_component if main_component != None else self.model.components[0]
        self.purityLB = purityLB
        self.purityUB = purityUB
        self.recoveryLB = recoveryLB
        self.recoveryUB = recoveryUB

        self.h_w = 50 #mm (Assumption)
        self.hole_diameter = 5 #mm (Assumption)
        self.plate_thickness = 5 #mm (Assumption)
        self.frac_appr_flooding = 0.8 #Assumption

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
            return self.model.RR * self.model.D[-1] + self.model.feed_flow_rate
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
        return conversions.lMin_to_m3Sec(self.model.volume_flow_vapour[0] if section == "top" else self.model.volume_flow_vapour[-1])
        
    def func_h_ow(self, value, section):
        if value == 'max':
            return self.func_max_liquid_flow_rate(section) / (self.func_density_liquid(section) * self.func_density_vapour(section)) ** (2./3)
        else:
            return self.func_min_liquid_flow_rate(section) / (self.func_density_liquid(section) * self.func_density_vapour(section)) ** (2./3)

    def func_h_w_h_ow_min(self, section):
        return self.h_w + self.func_h_ow('min', section)

    def func_actual_min_vapour_vel(self, section):
        return 0.7 * self.func_volume_flow_vapour(section) / self.func_hole_area()

    def func_min_vapour_vel(self, section):
         return (graph.K2(self.func_h_w_h_ow_min(section))-0.9*(25.4-self.hole_diameter))/(self.func_density_vapour(section)**(1./2))
    
    def func_A_ap(self):
        return (self.h_w - 10) * self.model.weir_length * (10 ** -3) # Change to m

    def func_h_dc(self, section):
        return 166 * (self.func_max_liquid_flow_rate(section)) / (self.func_density_liquid(section) * ((self.model.A_d if self.model.A_d<self.func_A_ap() else self.func_A_ap())**2))

    def func_max_vapour_vel(self, section):
        return self.func_volume_flow_vapour(section) / self.func_hole_area()

    def func_h_d(self, section):
        orifice_coeff = graph.orifice((self.func_hole_area()/self.func_active_area()), self.plate_thickness/self.hole_diameter)
        return 51 * ((self.func_max_vapour_vel(section) / orifice_coeff) **2) * (self.func_density_vapour(section)/self.func_density_liquid(section))

    def func_h_r(self, section):
        return 12500 / self.func_density_liquid(section)

    def func_h_t(self, section):
        return self.func_h_d(section) + self.h_w + self.func_h_ow('max', section) + self.func_h_r(section)

    def func_h_b(self, section):
        # NOTE: Need to round up h_dc?
        return self.h_w + self.func_h_ow('max', section) + self.func_h_t(section) + self.func_h_dc(section)

    def func_v(self):
        return self.model.D[0] * (1 + self.model.RR)

    def func_f_lv(self, section):
        return (self.func_L(section) / self.func_v()) * ((self.func_density_vapour(section) / self.func_density_liquid(section)) ** (1./2))

    def func_flooding_vapour_velocity(self, section):
        return graph.K1(self.func_f_lv(section), self.model.tray_spacing) * (((self.func_density_liquid(section) - self.func_density_vapour(section))/self.func_density_vapour(section)) ** (1./2))

    def func_u_n(self, section):
        return self.frac_appr_flooding * self.func_flooding_vapour_velocity(section)

    def func_net_area_required(self):
        return max(self.func_volume_flow_vapour(section)/self.func_u_n(section) for section in ['top', 'bottom'])

    def func_percent_flooding(self, section):
        u_v = self.func_volume_flow_vapour(section) / self.func_net_area_required()
        return u_v / self.func_flooding_vapour_velocity(section)

    def entrainmentCheck(self, section):
        return self.frac_appr_flooding - self.func_percent_flooding(section) # percent of flooding should be less than frac_appr_flooding

    def entrainmentFracCheck(self, section):
        self.frac_entrainment = graph.frac(self.func_f_lv(section), self.func_percent_flooding(section))
        return self.frac_entrainment - 0.1 # frac_entrainment should be less than 0.1

    def weepingCheck(self, section):
        # actual_min_vapour_vel > min_vapour_vel
        return self.func_actual_min_vapour_vel(section) - self.func_min_vapour_vel(section) 

    def downcomerLiquidBackupCheck(self, section):
        return  0.5 * (self.model.tray_spacing + self.h_w) - self.func_h_b(section) # Should be larger than 0 (pg 882 towler sinnot)
    
    def downcomerResidenceTimeCheck(self, section):
        self.residence_time = (self.model.A_d * self.func_h_b(section) * (10 ** -3) * self.func_density_liquid(section)) / (self.func_max_liquid_flow_rate(section))
        return self.residence_time - 3 # Should be larger than 3s

    def optimize(self):
        x0 = [
            self.model.P_cond, 
            self.model.P_start_1, 
            self.model.P_start_2, 
            self.model.P_end_1, 
            self.model.P_end_2, 
            self.model.P_drop_1, 
            self.model.P_drop_2, 
            self.model.RR, 
            self.model.N, 
            self.model.feed_stage, 
            self.model.tray_spacing, 
            self.model.num_pass, 
            self.model.tray_eff, 
            self.model.n_years
            ]

        bounds = (
            (0, None), # P_cond
            (1, None), # P_start_1
            (1, None), # P_start_2
            (1, None), # P_end_1
            (1, None), # P_end_2
            (0, None), # P_drop_1
            (0, None), # P_drop_2
            (0, 1), # RR
            (3, None), # N
            (2, None), # feed_stage
            (0, None), # tray_spacing
            (1, 4), # num_pass
            (0, 1), # tray_eff
            (1, None) # n_years
        )

        constraints = (
            # Manipulated Constraints
            {'type': 'ineq', 'fun': lambda x: self.model.P_start_2 - self.model.P_start_1}, # P_start_2 - P_start_1
            {'type': 'ineq', 'fun': lambda x: self.model.N - self.model.P_end_2},
            # Results Constraint
            {'type': 'ineq', 'fun': lambda x: self.model.purity[self.main_component] - self.purityLB},
            {'type': 'ineq', 'fun': lambda x: self.purityUB - self.model.purity[self.main_component]},
            {'type': 'ineq', 'fun': lambda x: self.model.recovery[self.main_component] - self.recoveryLB},
            {'type': 'ineq', 'fun': lambda x: self.recoveryUB - self.model.recovery[self.main_component]},
            {'type': 'ineq', 'fun': self.weepingCheck('top')},
            {'type': 'ineq', 'fun': self.downcomerLiquidBackupCheck('top')},
            {'type': 'ineq', 'fun': self.downcomerResidenceTimeCheck('top')},
            {'type': 'ineq', 'fun': self.entrainmentCheck('top')},
            {'type': 'ineq', 'fun': self.entrainmentFracCheck('top')},
            {'type': 'ineq', 'fun': self.weepingCheck('bottom')},
            {'type': 'ineq', 'fun': self.downcomerLiquidBackupCheck('bottom')},
            {'type': 'ineq', 'fun': self.downcomerResidenceTimeCheck('bottom')},
            {'type': 'ineq', 'fun': self.entrainmentCheck('bottom')},
            {'type': 'ineq', 'fun': self.entrainmentFracCheck('bottom')},
        )

        result = opt.minimize(
            self.objective,
            x0, 
            constraints = constraints,
            bounds = bounds,
            method='SLSQP', 
            options={'disp': True}, 
            tol = self.opt_tolerance
        )
        return result

    def objective(self, x):
        self.model.P_cond = x[0]
        self.model.P_start_1 = x[1]
        self.model.P_start_2 = x[2]
        self.model.P_end_1 = x[3]
        self.model.P_end_2 = x[4]
        self.model.P_drop_1 = x[5]
        self.model.P_drop_2 = x[6]
        self.model.RR = x[7]
        self.model.N = x[8]
        self.model.feed_stage = x[9]
        self.model.tray_spacing = x[10]
        self.model.num_pass = x[11]
        self.model.tray_eff = x[12]
        self.model.n_years = x[13]
        self.model.run()
        return self.model.TAC

    def run(self):
        result = self.optimize()
        print (result)




        


