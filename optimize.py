from operator import contains
import numpy as np
import pandas as pd
import os
import model
import scipy.optimize as opt

class optimizer():
    def __init__(self, model, max_k = 100, max_line = 100, max_j = 100, opt_tolerance = 0.01):
        self.k = 0
        self.j = 0
        self.x_kj = model
        self.x_kj_conv = self.x_kj
        self.x_kj_init = self.x_kj
        self.max_k = max_k
        self.max_line = max_line
        self.max_j = max_j
        self.opt_tolerance = opt_tolerance


    # def initial_values(self):
    #     self.RR = 0.924
    #     self.N = 36
    #     self.feed_stage = 23
    #     self.P_cond = 1.12
    #     self.P_drop = 0


    #     filepath, component, z_feed, T, P, F, condenser_type, \
    #         reboiler_type, D

    # x contains
    #     self.RR = 0.924
    #     self.N = 36
    #     self.feed_stage = 23
    #     self.P_cond = 1.12
    #     self.P_drop = 0
    #  COlumn Temp
    # Condenser & Reboiler Duties
    # Column Diameter

    def reset_to_s0(self):
        self.x_kj = self.x_kj_conv

    def terminate_opt(self):
        return False

    def steady_state_sim(self):
        self.x_kj.run()

    def nlp_optimize(self):
        # newton
        # SQP
        return # optimized x

    def convergence_test(self):
        return True

    def ptc_objective(self):
        sum_of_squares = 0
        for j in range (self.x_kj.N):
            for i in range (len(self.x_kj.components)):
                dM_ij_dt =  self.x_kj.V(j+1) * self.x_kj.components[i].y(j+1) \
                    + self.x_kj.L(j-1) * self.x_kj.components[i].x(j-1) \
                        - self.x_kj.V_eq(j) * self.x_kj.components[i].y_eq(j) \
                            - self.x_kj.L_eq(j) * self.x_kj.components[i].x_eq(j) 
                sum_of_squares += dM_ij_dt**2
            dH_j_dt =  self.x_kj.V(j+1) * self.x_kj.H(j+1) \
                + self.x_kj.L(j-1) * self.x_kj.h(j-1) \
                    - self.x_kj.V_eq(j) * self.x_kj.H_eq(j) \
                        - self.x_kj.L_eq(j) * self.x_kj.h_eq(j) 
            sum_of_squares += dH_j_dt**2
        return sum_of_squares

    def ptc_optimize(self):
        x0 = self.x_kj
        x_opt = opt.minimize(self.ptc_objective, x0, method='SLSQP', options={'disp': True})

    def main(self):
        while self.j < self.max_j:
            self.steady_state_sim()
            self.nlp_optimize()
            self.j += 1
        if self.terminate_opt():
            return self.x_kj
        else:
            if self.x_kj_conv != self.x_kj_init:
                self.steady_state_sim()
                if self.convergence_test():
                    self.k += 1
                    self.j = 0
                    self.main()
            self.reset_to_s0()
            self.ptc_optimize()
            if not self.convergence_test():
                self.reset_to_s0
            self.k += 1
            self.j = 0
            self.main()




        


