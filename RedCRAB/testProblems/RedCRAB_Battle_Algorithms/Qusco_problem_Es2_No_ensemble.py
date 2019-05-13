"""
Code for starting exercise 2, First PART
Before interfacing this code with RedCRAB test it with the statements that you can find below
"""

import numpy as np
from scipy import integrate, linspace
import matplotlib.pyplot as plt


def fnct(DcrabPulses, DcrabParas, time_grid):
    # Control fields
    global u1
    global u2

    # Bins number
    global Nt

    # Drift Hamiltonian
    global H_d

    # Control Hamiltonians
    global H_c_1
    global H_c_2

    # Detuning
    global detuning

    # Total time
    global TT

    # Pulses from RedCRAB
    u1 = DcrabPulses[0]
    u2 = DcrabPulses[1]

    # Parameters:
    Nt = len(time_grid)
    detuning = -0.5

    # Drift Hamiltonian
    H_d = np.asarray([[0, 0, 0], [0, 0, 0], [0, 0, detuning]])

    # Control Hamiltonians
    H_c_1 = 1/2*np.asarray([[0, 1, 0], [1, 0, np.sqrt(2)], [0, np.sqrt(2), 0]])
    H_c_2 = 1j/2 * np.asarray([[0, -1, 0], [1, 0, -np.sqrt(2)], [0, np.sqrt(2), 0]])

    # Initial state
    psi_0 = np.array([1, 0, 0])

    # Final Time
    TT = time_grid[-1]

    # Compute Final State
    psi_fin = Runge_Kutta(psi_0, time_grid, u1, u2)

    # Compute Fidelity
    F = abs(psi_fin[1])

    # Infidelity
    JJ = F
    return JJ


def f_vel(t, Y):
    # Take the field at the correct time
    t_ind = int(np.floor(t / TT * (Nt - 1)))
    if t_ind >= Nt:
        t_ind = Nt - 1
    u_t_1 = u1[t_ind]
    u_t_2 = u2[t_ind]

    H_tot = (H_d + u_t_1 * H_c_1 + u_t_2 * H_c_2)

    Y_t = np.dot(-1j * H_tot, Y)

    return Y_t

def Runge_Kutta(psi_0, time_grid, u1, u2):

    def f(t, v):
        H_tot = (H_d + u1[t] * H_c_1 + u2[t] * H_c_2)
        return 1 / 1j * np.dot(H_tot, v)

    psi = psi_0

    t = 0

    steps = len(time_grid)
    dt = time_grid[-1]/steps

    while t < steps:
        if t < steps - 2:
            h = 2 * dt
            k_1 = h * f(t, psi)
            k_2 = h * f(t + 1, psi + k_1 / 2)
            k_3 = h * f(t + 1, psi + k_2 / 2)
            k_4 = h * f(t + 2, psi + k_3)

            psi = psi + 1 / 2 * (k_1 / 6 + k_2 / 3 + k_3 / 3 + k_4 / 6)

        else:
            psi = psi + f(t, psi) * dt

        t += 1

    return psi


# CODE FOR TESTING
timegrid = np.linspace(0.0, 5.0, 1001)
# u1 = np.exp(-timegrid ** 2)
# u2 = np.exp(-timegrid ** 2)
#
# u1 = [0/100]*len(timegrid)
# u2 = [10000/100]*len(timegrid)



###################################################################


# y = []
# anzahl = 100
#
# r = linspace(0, 10, anzahl)
#
# for i in r:
#     u1 = [i]*len(timegrid)
#     u2 = [1]*len(timegrid)
#     DcrabPulses = []
#     DcrabPulses.append(u1)
#     DcrabPulses.append(u2)
#     DcrabParas = []
#
#     # Calculate figure of merit
#     JJ = fnct(DcrabPulses, DcrabParas, timegrid)
#     # Print Figure of merit
#     y.append(JJ)
#
# plt.plot(r, y)
# plt.show()


################################################################


# DcrabPulses = []
# DcrabPulses.append(u1)
# DcrabPulses.append(u2)
# DcrabParas = []
#
# # Calculate figure of merit
# JJ = fnct(DcrabPulses, DcrabParas, timegrid)
# # Print Figure of merit
# print(JJ)


