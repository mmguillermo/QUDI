"""
pymatinterface.py - Matlab engine interface
@author: Jonathan Zoller (jonathan.zoller@gmx.de), Simone Montangero
Current version number: 1.0.3
Current version dated: 19.04.2017
First version dated: 01.04.2017
"""
import matlab.engine

def fnct(pulses, dcrab_paras, timegrid, eng):

    pulses_cat = []
    for el in pulses:
        pulses_cat.append(el.tolist())

    pulses_cat_matlab = matlab.double(pulses_cat)
    timegrid_matlab = matlab.double(timegrid.tolist())

    matout = eng.objectivefunwrap(pulses_cat_matlab, timegrid_matlab, nargout=2)


    print(matout)

    FOM = matout[0]
    if isinstance(FOM, float):
        pass#everything ok
    else:
        FOM = 0.0
    STD = matout[1]

    return FOM, STD



