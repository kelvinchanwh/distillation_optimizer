def calPerSec_to_GJPerYear(calPerSec):
    return calPerSec * 0.1320349248

def GJPerYear_to_calPerSec(calPerSec):
    return calPerSec / 0.1320349248

def calPerSec_to_kJPerSec(calPerSec):
    return calPerSec * 0.0041868

def kJPerSec_to_calPerSec(kJPerSec):
    return kJPerSec / 0.0041868

def celcius_to_kelvin(celcius):
    return celcius + 273.15

def kelvin_to_celcius(kelvin):
    return kelvin - 273.15

def gmCc_to_kgM3(gm_cc):
    return gm_cc / 1000

def kgM3_to_gmCc(kg_m3):
    return kg_m3 * 1000

def lMin_to_m3Sec(l_min):
    return l_min * 60 / 1000.

def m3Sec_to_lMin(m3_sec):
    return m3_sec * 1000 / 60

def mm_to_m(mm):
    return mm / 1000.

def m_to_mm(m):
    return m * 1000.
