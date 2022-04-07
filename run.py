import os
import model as m
import optimize as opt

model = m.Model ( 
    filepath = os.path.join(os.getcwd(), 'Simulation 2.bkp'), 
    N = 36,
    RR = 0.924,
    tray_spacing = 0.63636,
    feed_stage = 23,
    P_cond = 1.013,
    main_component = "BENZENE"
)

model.run()
print (model.TAC)

# Optimize
optimizer = opt.Optimizer(model, opt_tolerance=1e-8)
print (optimizer.run())

# model.obj.Close()