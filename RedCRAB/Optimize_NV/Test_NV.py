from Parameters import *
from Functions import *
from Pulse import pulse
import numpy as np
from scipy import linspace
import matplotlib.pyplot as plt
from numpy import array, tensordot


def fnct(DcrabPulses, DcrabParas, time_grid):

    rho_0 = array([[1, 0, 0], [0, 0, 0], [0, 0, 0]])
    resonance_freq = D_gs - gamma_nv * B

    aim = array([0, 1, 0])
    aim = tensordot(aim, aim, axes=0)

    # set pulse time in ns
    pulse_time = 50  # ns
    steps = len(DcrabPulses)

    pulse_phase = 0

    lifetime = float('inf')  # in ns
    dephasing_time = float('inf')  # in ns
    mw_bandwidth = 0  # in GHz

    pulse_amplitude = DcrabPulses
    pulse_freq = [resonance_freq] * steps

    detunings = [-0.01, 0, 0.01]
    fid = 0

    for det in detunings:
        rho = pulse(rho_0, pulse_amplitude, pulse_freq, pulse_time, detuning=det, phase=pulse_phase,
                    rho_end=1, lifetime=lifetime, dephasing_time=dephasing_time, mw_bandwidth=mw_bandwidth)
        fid += Fidelity(rho, aim)

    fom = fid / len(detunings)

    return fom

