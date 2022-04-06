import os
import model as m
import optimize as opt

model = m.Model ( 
    filepath = os.path.join(os.getcwd(), 'Simulation 2.bkp'), 
    P_drop_1= 0.01,
    P_drop_2= 0.01,
    N = 36,
    RR = 0.924,
    tray_spacing = 0.15,
    feed_stage = 23,
    P_cond = 1.013,
    main_component = "BENZENE"
)

model.run()
print (model.TAC)

# Optimize
optimizer = opt.Optimizer(model, opt_tolerance=0.1, eps = 1e-5, ftol = 0.1)
print (optimizer.run())

# model.obj.Close()