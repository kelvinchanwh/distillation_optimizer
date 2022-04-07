import numpy as np
import pandas as pd
import model
import scipy.optimize as opt
import conversions
import graph
import initialize

class Optimizer():
    def __init__(self, model: model.Model, opt_tolerance: float = 0.01, \
        purityLB: float = 0.99, purityUB: float = 1.0,\
            recoveryLB: float = 0.99, recoveryUB: float = 1.0):
        self.opt_tolerance = opt_tolerance
        self.model = model
        self.time = 0
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
            return (self.func_max_liquid_flow_rate(section) / (self.func_density_liquid(section) * self.func_density_vapour(section)) ** (2./3)) * 1000  # Conversion to mm
        else:
            return (self.func_min_liquid_flow_rate(section) / (self.func_density_liquid(section) * self.func_density_vapour(section)) ** (2./3)) * 1000  # Conversion to mm

    def func_h_w_h_ow_min(self, section):
        return self.h_w + self.func_h_ow('min', section)

    def func_actual_min_vapour_vel(self, section):
        return 0.7 * self.func_volume_flow_vapour(section) / self.func_hole_area()

    def func_min_vapour_vel(self, section):
         return (graph.K2(self.func_h_w_h_ow_min(section))-0.9*(25.4-self.hole_diameter))/(self.func_density_vapour(section)**(1./2))
    
    def func_A_ap(self):
        return (self.h_w - 10) * self.model.weir_length * (10 ** -3) # Change to m

    def func_h_dc(self, section):
        return 166 * ((self.func_max_liquid_flow_rate(section) / (self.func_density_liquid(section) * (self.model.A_d if self.model.A_d<self.func_A_ap() else self.func_A_ap())))**2)

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
        frac_entrainment = graph.frac(self.func_f_lv(section), self.func_percent_flooding(section))
        return 0.1 - frac_entrainment # frac_entrainment should be less than 0.1

    def weepingCheck(self, section):
        # actual_min_vapour_vel > min_vapour_vel
        return (self.func_actual_min_vapour_vel(section) - self.func_min_vapour_vel(section))/5.0 # Scale for constraints

    def downcomerLiquidBackupCheck(self, section):
        return  0.5 * (self.model.tray_spacing + (self.h_w/1000)) - self.func_h_b(section)/1000 # Should be larger than 0 (pg 882 towler sinnot)
    
    def downcomerResidenceTimeCheck(self, section):
        self.residence_time = (self.model.A_d * self.func_h_b(section) * (10 ** -3) * self.func_density_liquid(section)) / (self.func_max_liquid_flow_rate(section))
        return (self.residence_time - 3)/10.0 # Should be larger than 3s # Scale for constraints

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

    def callback(self, x):
        self.func_iter = 0
        print ('{0:4d}   {1:3.3f}   {2:3.3f}   {3:3.3f}   {4:3.3f}   {5:3.3f}   {6:3.3f}   {7:3.3f}   {8:3.3f}   {9:3.3f}'.format(self.opt_iter, x[0], x[1], x[2], x[3], x[4]*100, x[5]*100, x[6], self.model.TAC, self.time))
        self.opt_iter += 1

    def optimize(self):
        x0 = [
            self.model.P_cond, 
            self.model.P_drop_1, 
            self.model.P_drop_2, 
            initialize.min_RR(self.model), 
            initialize.actual_N(self.model, self.recoveryLB)/100, 
            initialize.feed_stage(self.model, self.recoveryLB)/100, 
            self.model.tray_spacing
            ]
        
        min_RR = initialize.min_RR(self.model, self.recoveryLB)
        min_N = 5 #initialize.min_N(self.model, self.recoveryLB)

        bounds = (
            (1.013, 10), # P_cond
            (0.01, 1.0), # P_drop_1
            (0.01, 1.0), # P_drop_2
            (min_RR, 1.1 * min_RR), # RR
            (min_N/100, 300/100), # N
            (3/100, (self.model.N-3)/100), # feed_stage
            (0.15, 1), # tray_spacing
        )

        constraints = (
            # Results Constraint
            {'type': 'ineq', 'fun': lambda x: self.model.purity[self.model.main_component] - self.purityLB},
            {'type': 'ineq', 'fun': lambda x: self.purityUB - self.model.purity[self.model.main_component]},
            #{'type': 'ineq', 'fun': lambda x: self.model.recovery[self.model.main_component] - self.recoveryLB},
            #{'type': 'ineq', 'fun': lambda x: self.recoveryUB - self.model.recovery[self.model.main_component]},
            {'type': 'ineq', 'fun': lambda x: self.model.stream_input_pres - self.model.P_stage[self.model.feed_stage-1]},
            #{'type': 'ineq', 'fun': self.weepingCheckTop},
            #{'type': 'ineq', 'fun': self.downcomerLiquidBackupCheckTop},
            #{'type': 'ineq', 'fun': self.downcomerResidenceTimeCheckTop},
            #{'type': 'ineq', 'fun': self.entrainmentCheckTop},
            #{'type': 'ineq', 'fun': self.entrainmentFracCheckTop},
            #{'type': 'ineq', 'fun': self.weepingCheckBottom},
            #{'type': 'ineq', 'fun': self.downcomerLiquidBackupCheckBottom},
            #{'type': 'ineq', 'fun': self.downcomerResidenceTimeCheckBottom},
            #{'type': 'ineq', 'fun': self.entrainmentCheckBottom},
            #{'type': 'ineq', 'fun': self.entrainmentFracCheckBottom},
        )

        print ('{0:4s}   {1:9s}   {2:9s}   {3:9s}   {4:9s}   {5:9s}   {6:9s}   {7:9s}   {8:9s}   {9:9s}'.format('Iter', ' P_cond', 'P_drop_1', 'P_drop_2', 'RR', 'N', 'feed_stage', 'tray_spacing', 'TAC', 'Runtime'))
        print ('{0:4s}   {1:3.3f}   {2:3.3f}   {3:3.3f}   {4:3.3f}   {5:3.3f}   {6:3.3f}   {7:3.3f}   {8:4s}   {9:3.3f}'.format("Init", x0[0], x0[1], x0[2], x0[3], x0[4]*100, x0[5]*100, x0[6], "----", self.time))
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
            self.model.P_cond = float(x[0])
            self.model.P_drop_1 = float(x[1])
            self.model.P_drop_2 = float(x[2])
            self.model.RR = float(x[3])
            self.model.N = int(x[4]*100)
            self.model.feed_stage = int(x[5]*100)
            self.model.tray_spacing = float(x[6])
            runtime = self.model.run()
            self.time += runtime
            self.func_iter += 1
            return self.model.TAC/1000000
        except Exception as e:
            # If simulation cannot be run, return a large number
            self.time += runtime
            print ('{0:4d}   {1:3.3f}   {2:3.3f}   {3:3.3f}   {4:3.3f}   {5:3.3f}   {6:3.3f}   {7:3.3f}   {8:3.3f}   {9:3.3f}'.format(self.func_iter, x[0], x[1], x[2], x[3], x[4]*100, x[5]*100, x[6], e, self.time))
            self.func_iter += 1
            return np.inf

    def run(self):
        result = self.optimize()
        print (result)




        


