import os
import model as m
import optimize as opt

model = m.Model ( 
    # Hydraulics Simulation 3, No Hydraulics: Simulation 4
    filepath = os.path.join(os.getcwd(), 'Simulation 3.bkp'), 
    N = 101,
    RR = 0.924,
    tray_spacing = 0.63636,
    tray_eff_1 = 0.5,
    tray_eff_2 = 0.5,
    feed_stage = 51,
    P_cond = 1.013,
    main_component = "BENZENE"
)

model.run()
print (model.TAC)

# Optimize
optimizer = opt.Optimizer(model, opt_tolerance=1e-3, hydraulics = True)
print (optimizer.run())

# model.obj.Close()