import os
import model as m
import optimize as opt

model = m.Model ( 
    filepath = os.path.join(os.getcwd(), 'Simulation 3.bkp'), 
    N = 101,
    RR = 0.924,
    tray_spacing = 0.63636,
    # Tray Type: SIEVE, CAPS
    tray_type="SIEVE",
    tray_eff_1 = 0.5,
    tray_eff_2 = 0.5,
    feed_stage = 51,
    P_cond = 1.013,
    main_component = "BENZENE",
    hydraulics = True,
    const_pres=False
)

model.run()
print (model.TAC)

# Optimize
optimizer = opt.Optimizer(model, opt_tolerance=1e-3, recoveryLB=0.95, purityLB=0.95)
print (optimizer.run())

# model.obj.Close()