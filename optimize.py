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

    # def func_net_area(self):
    #     top = self.func_volume_flow_vapour("top")/self.func_u_n("top")
    #     bottom = self.func_volume_flow_vapour("bottom")/self.func_u_n("bottom")
    #     return top if top > bottom else bottom
    #     return max(self.func_volume_flow_vapour(section)/self.func_u_n(section) for section in ['top', 'bottom'])

    def func_percent_flooding(self, section):
        u_v = self.func_volume_flow_vapour(section) / self.func_net_area()
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
        gk = GEKKO(remote = False)
        var = [
            gk.Var(self.model.P_cond, lb=0, integer = False, name = 'P_cond'),
            gk.Var(self.model.P_start_1, lb=2, integer = True, name = 'P_start_1'),
            gk.Var(self.model.P_start_2, lb=2, integer = True, name = 'P_start_2'),
            gk.Var(self.model.P_end_1, lb=2, integer = True, name = 'P_end_1'),
            gk.Var(self.model.P_end_2, lb=2, integer = True, name = 'P_end_2'),
            gk.Var(self.model.P_drop_1, lb=0.01, integer = False, name = 'P_drop_1'),
            gk.Var(self.model.P_drop_2, lb=0.01, integer = False, name = 'P_drop_2'),
            gk.Var(self.model.RR, lb=0, ub=1, integer = False, name = 'RR'),
            gk.Var(self.model.N, lb=3, integer = True, name = 'N'),
            gk.Var(self.model.feed_stage, lb=2, integer = True, name = 'feed_stage'),
            gk.Var(self.model.tray_spacing, lb=0, integer = False, name = 'tray_spacing'),
            gk.Var(self.model.num_pass, lb=1, ub=4, integer = True, name = 'num_pass'),
            gk.Var(self.model.tray_eff, lb=0, ub=1, integer = False, name = 'tray_eff'),
            gk.Var(self.model.n_years, lb=1, integer = True, name = 'n_years'),
            ]

        constraints = [            # Manipulated Constraints
            gk.Equations(self.model.P_start_2 - self.model.P_start_1>=0), # P_start_2 - P_start_1
            gk.Equations(self.model.N - self.model.P_end_2>=0),
            # Results Constraint
            gk.Equations(self.model.purity[self.main_component] - self.purityLB>=0),
            gk.Equations(self.purityUB - self.model.purity[self.main_component]>=0),
            gk.Equations(self.model.recovery[self.main_component] - self.recoveryLB>=0),
            gk.Equations(self.recoveryUB - self.model.recovery[self.main_component]>=0),
            gk.Equations(self.weepingCheck('top')>=0),
            gk.Equations(self.downcomerLiquidBackupCheck('top')>=0),
            gk.Equations(self.downcomerResidenceTimeCheck('top')>=0),
            gk.Equations(self.entrainmentCheck('top')>=0),
            gk.Equations(self.entrainmentFracCheck('top')>=0),
            gk.Equations(self.weepingCheck('bottom')>=0),
            gk.Equations(self.downcomerLiquidBackupCheck('bottom')>=0),
            gk.Equations(self.downcomerResidenceTimeCheck('bottom')>=0),
            gk.Equations(self.entrainmentCheck('bottom')>=0),
            gk.Equations(self.entrainmentFracCheck('bottom')>=0)
        ]

        result = opt.minimize(
            self.objective,
            x0, 
            constraints = constraints,
            bounds = bounds,
            method='SLSQP', 
            options={'disp': True}, 
            tol = self.opt_tolerance
        )
        gk.Objective(self.objective(var))
        gk.options.SOLVER = 1
        gk.solve(disp=True)
        # return result

    def objective(self, x):
        self.model.P_cond = float(x[0])
        self.model.P_start_1 = int(x[1])
        self.model.P_start_2 = int(x[2])
        self.model.P_end_1 = int(x[3])
        self.model.P_end_2 = int(x[4])
        self.model.P_drop_1 = float(x[5])
        self.model.P_drop_2 = float(x[6])
        self.model.RR = float(x[7])
        self.model.N = int(x[8])
        self.model.feed_stage = int(x[9])
        self.model.tray_spacing = float(x[10])
        self.model.num_pass = int(x[11])
        self.model.tray_eff = float(x[12])
        self.model.n_years = int(x[13])
        self.model.run()
        return self.model.TAC

    def run(self):
        result = self.optimize()
        print (result)




        


