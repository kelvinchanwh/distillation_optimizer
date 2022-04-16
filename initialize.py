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
    num = np.log((recovery_LB/(1-recovery_LB)) ** 2) # Assume that the recovery is the same for HK and LK
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

def min_RR(model: model, recovery_LB = 0.99):
    """
    Calculate minimum reflux ratio.
    """
    # Assume that all components with K val below LK (LNK) rises to top (100%)
    # Assume that all components with K val above HK (HNK) sinks to bottom (100%)
    LNK_flow = sum([model.mole_flow[component] for component in model.components if model.K[component] > model.K[model.LK]])
    LK_flow = recovery_LB * model.mole_flow[model.LK] 
    HK_flow = (1-recovery_LB) * model.mole_flow[model.HK] 
    D = LNK_flow + LK_flow + HK_flow

    mole_frac = {component: (model.mole_flow[component]/D) for component in model.components if model.K[component] > model.K[model.LK]}
    mole_frac[model.LK] = LK_flow/D
    mole_frac[model.HK] = HK_flow/D

    summation = sum([relative_volatility(model, component) * mole_frac[component] / (relative_volatility(model, component) - theta(model)) for component in mole_frac.keys()])
    return summation - 1

def actual_N (model: model, recovery_LB = 0.99):
    """
    Calculate actual number of stages.
    """
    psi = (1.2 - 1) * min_RR(model) / ((1.2 * min_RR(model)) + 1)
    rhs = 1 - np.exp(((1 + 54.5 * psi) * (psi-1)) / ((11 + 117.2 * psi) * (psi ** 0.5)))
    N = (min_N(model, recovery_LB) + rhs)/(1-rhs)
    return int(math.ceil(N))

def feed_stage(model: model, recovery_LB = 0.99):
    """
    Calculate feed stage.
    """
    # Assume that all components with K val below LK (LNK) rises to top (100%)
    # Assume that all components with K val above HK (HNK) sinks to bottom (100%)
    LNK_flow_D = sum([model.mole_flow[component] for component in model.components if model.K[component] > model.K[model.LK]])
    LK_flow_D = recovery_LB * model.mole_flow[model.LK] 
    HK_flow_D = (1-recovery_LB) * model.mole_flow[model.HK] 
    D = LNK_flow_D + LK_flow_D + HK_flow_D

    HNK_flow_B = sum([model.mole_flow[component] for component in model.components if model.K[component] < model.K[model.HK]])
    HK_flow_B = recovery_LB * model.mole_flow[model.HK] 
    LK_flow_B = (1-recovery_LB) * model.mole_flow[model.LK] 
    B = HNK_flow_B + HK_flow_B + LK_flow_B

    x_hd = (HK_flow_D/D)
    x_lb = (LK_flow_B/B)
    val = 0.206 * np.log((B/D) * (model.mole_frac[model.HK]/model.mole_frac[model.LK]) * ((x_lb/x_hd)**2.))
    nr_ns = np.exp(val)
    ns = int(actual_N(model)/ (1 + nr_ns))
    nr = int(actual_N(model) - ns)
    return nr

def distilate_rate(model: model, recovery_LB = 0.99):
    """
    Calculate distilate rate.
    """
    LNK_flow_D = sum([model.mole_flow[component] for component in model.components if model.K[component] > model.K[model.LK]])
    LK_flow_D = recovery_LB * model.mole_flow[model.LK] 
    HK_flow_D = (1-recovery_LB) * model.mole_flow[model.HK] 
    D = LNK_flow_D + LK_flow_D + HK_flow_D
    return D