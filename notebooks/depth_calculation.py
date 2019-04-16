# -*- coding: utf-8 -*-

import numpy as np


def do_normalisation(y_raw, rabi_amplitude, rabi_offset):
    """
    data normalization
    """
    y_norm = 1-(rabi_offset + rabi_amplitude - y_raw)/(2*rabi_amplitude)
    return y_norm


def nu_from_tau(x):
    """
    calculates the frequency nu for given values of tau
    """
    tau = np.array(x)
    nu = 1/(2*tau)
    return nu


def S_from_data(tau, y, N):
    """
    calculates the spectral density S for given coherence data N is the number of pulses
    """
    tau = np.array(tau)
    y = np.array(y)
    chi = -np.log((2*y)-1)
    S = np.pi**2 / (4*N*tau) * chi
    return S


def calculate_depth_simple(mu_0, h, B, gamma_n, rho):
    """
    gets rho in 1/nm^3 and B in T, returns d in nm
    """
    d = (rho * mu_0**2 * h**2 * gamma_n**2 * 5 / (1536 * np.pi * B**2))**(1./3)
    return d


def calculate_density_simple(mu_0, h, B, gamma_n, d):
    """
    gets d in m and B in T, returns rho in 1/m^3
    """
    rho = d**3 * 1536 * np.pi * B**2 / (5 * mu_0**2 * h**2 * gamma_n**2)
    return rho
    
    
def get_data(filename):
    """
    importing data with two or three columns
    """
    data = np.loadtxt(filename)
    x = data[:, 0]
    y1 = data[:, 1]
    if data.shape[1] < 3:
        return x, y1
    if data.shape[1] == 3:
        y2 = data[:, 2]
    elif data.shape[1] == 4:
        y2 = data[:, 3]
    return x, y1, y2


def correct_normalized_spectrum(xy8_y1, xy8_y2):
    """
    Correct values above/below 0.5 for the normalized spectrum by replacing them with the mean
    value of the next and previous point.
    """
    was_corrected = False
    if xy8_y1.mean() > xy8_y2.mean():
        for i in range(1, xy8_y1.size-1):
            if xy8_y1[i] <= 0.5:
                was_corrected = True
                xy8_y1[i] = (xy8_y1[i-1] + xy8_y1[i+1]) / 2
            if xy8_y2[i] >= 0.5:
                was_corrected = True
                xy8_y2[i] = (xy8_y2[i-1] + xy8_y2[i+1]) / 2
    else:
        for i in range(1, xy8_y1.size-1):
            if xy8_y1[i] >= 0.5:
                was_corrected = True
                xy8_y1[i] = (xy8_y1[i-1] + xy8_y1[i+1]) / 2
            if xy8_y2[i] <= 0.5:
                was_corrected = True
                xy8_y2[i] = (xy8_y2[i-1] + xy8_y2[i+1]) / 2
    return was_corrected
