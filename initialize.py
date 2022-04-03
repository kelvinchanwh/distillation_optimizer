import numpy as np
import model
import scipy.optimize as opt
import math

def relative_volatility(model: model, component: str):
    """
    Calculate relative volatility of the component.
    """
    return model.K[component] / model.K[model.HK]

def min_N(model: model, recovery_LB = 0.99):
    """
    Calculate minimum number of stages.
    """
    dl = recovery_LB * model.mole_frac[model.LK] * model.feed_flow_rate 
    bl = (1-recovery_LB) * model.mole_frac[model.LK] * model.feed_flow_rate
    dh = model.D[0] - dl
    bh = model.D[-1] - bl
    num = np.log((dl * bh)/(dh * bl))
    den = np.log(model.K[model.LK])
    return int(math.ceil(num/den))

def theta(model: model):
    """
    Calculate theta.
    """
    obj = lambda x: sum([relative_volatility(model, component) * model.mole_frac[component] / (relative_volatility(model, component) - x) for component in model.components])
    result = opt.root_scalar(
        obj,
        x0 = 2.0,
        x1 = 1.5, 
        options={'disp': False},
    )
    return result.root

def min_RR(model: model):
    """
    Calculate minimum reflux ratio.
    """
    summation = sum([relative_volatility(model, component) * (model.streamOutput["2"]["STR_MAIN"]["MOLEFLOW"]["MIXED"][component]/model.D[0]) / (relative_volatility(model, component) - theta(model)) for component in model.components])
    return summation - 1

def actual_N (model: model, recovery_LB = 0.99):
    """
    Calculate actual number of stages.
    """
    psi = (1.1 - 1) * min_RR(model) / ((1.1 * min_RR(model)) + 1)
    rhs = 1 - np.exp(((1 + 54.5 * psi) * (psi-1)) / ((11 + 117.2 * psi) * (psi ** 0.5)))
    N = (min_N(model, recovery_LB) + rhs)/(1-rhs)
    return int(math.ceil(N))

def feed_stage(model: model):
    """
    Calculate feed stage.
    """
    x_hd = (model.streamOutput["2"]["STR_MAIN"]["MOLEFLOW"]["MIXED"][model.HK]/model.D[0])
    x_lb = (model.streamOutput["3"]["STR_MAIN"]["MOLEFLOW"]["MIXED"][model.LK]/model.D[-1])
    val = 0.206 * np.log((model.D[-1]/model.D[0]) * (model.mole_frac[model.HK]/model.mole_frac[model.LK]) * ((x_lb/x_hd)**2.))
    nr_ns = np.exp(val)
    ns = int(actual_N(model)/ (1 + nr_ns))
    nr = int(actual_N(model) - ns)
    return nr

