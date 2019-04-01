from Parameters import *
from scipy.linalg import expm
from scipy.special import jv as bessel_func
from Functions import PartialTrace
import numpy as np
from numpy import linalg, conjugate, transpose, dot, exp, real, imag, cos, trace
import sys


#########################################################################################

def dagger(m):
    return conjugate(transpose(m))


def bessel(order, argument):
    return bessel_func(order, argument)


#########################################################################################

def pulse(rho_0, pulse_amplitude, pulse_freq, pulse_time, detuning=0, phase=0, method='Runge_Kutta',
          rho_end=0, rho_00=0, rho_01=0, rho_10=0, rho_11=0, rho_22=0,
          lifetime=float('inf'), dephasing_time=float('inf'),
          mw_bandwidth=0):

    if method == 'Runge_Kutta':
        return Runge_Kutta(rho_0, pulse_amplitude, pulse_freq, pulse_time, detuning, phase,
                           rho_end=rho_end, rho_00=rho_00, rho_01=rho_01, rho_10=rho_10, rho_11=rho_11,
                           rho_22=rho_22,
                           lifetime=lifetime, dephasing_time=dephasing_time, mw_bandwidth=mw_bandwidth)

    elif method == 'Runge_Kutta_adaptive':
        return Runge_Kutta_adaptive(rho_0, pulse_amplitude, pulse_freq, pulse_time, detuning, phase,
                                    lifetime=lifetime, dephasing_time=dephasing_time, mw_bandwidth=mw_bandwidth)

    else:
        print('ERROR: pulse method not available')
        sys.exit()



#########################################################################################


def Runge_Kutta(rho_0, pulse_amplitude, pulse_freq, pulse_time, detuning, phase,
                rho_end=0, rho_00=0, rho_01=0, rho_10=0, rho_11=0, rho_22=0, lifetime=float('inf'),
                dephasing_time=float('inf'), mw_bandwidth=0):

    steps = len(pulse_amplitude)
    dt = pulse_time/steps
    time = linspace(0, pulse_time, steps)

    # lifetime should be in ns
    # decay rate gamma (in GHz)
    gamma_1 = 1 / lifetime
    gamma_2 = 1 / dephasing_time

    #######################################################################

    pulse_freq = [x * (1 + detuning) for x in pulse_freq]

    w_0 = 2 * pi * (D_gs - B * gamma_nv)
    w_1 = 2 * pi * (D_gs + B * gamma_nv)

    def H(t):
        return 2 * pi * pulse_amplitude[t]/1000 * cos(2*pi * pulse_freq[t] * time[t] + phase) * \
               array([[0, exp(-1j * w_0 * time[t]), exp(-1j * w_1 * time[t])],
                      [exp(1j * w_0 * time[t]), 0, 0],
                      [exp(1j * w_1 * time[t]), 0, 0]])

    #######################################################################

    # w_0 = (D_gs - B * gamma_nv)
    # w_1 = (D_gs + B * gamma_nv)
    # freq = pulse_freq[0] * (1 + detuning)
    #
    # def H(t):
    #     return 2 * pi * pulse_amplitude[t] / 1000 * \
    #            array([[0, 1/2, 1/2],
    #                   [1/2, w_0-freq, 0],
    #                   [1/2, 0, w_1-freq]])

    #######################################################################

    def f(t, dm):

        lindblad_0 = 2*pi * array([[gamma_1 * dm[1][1], -(0.5*gamma_2 + mw_bandwidth)*dm[0][1], 0],
                                  [-(0.5*gamma_2 + mw_bandwidth)*dm[1][0], -gamma_1 * dm[1][1], 0],
                                   [0, 0, 0]])

        lindblad_1 = 2 * pi * array([[gamma_1 * dm[2][2], 0, -(0.5 * gamma_2 + mw_bandwidth) * dm[0][2]],
                                     [0, 0, 0],
                                     [-(0.5 * gamma_2 + mw_bandwidth) * dm[2][0], 0, -gamma_1 * dm[2][2]]])

        return 1 / 1j * (dot(H(t), dm) - dot(dm, H(t))) + lindblad_0 + lindblad_1


    rho = rho_0
    out = []

    rho_00_temp = []
    rho_01_temp = []
    rho_10_temp = []
    rho_11_temp = []
    rho_22_temp = []

    t = 0

    while t < steps:
        if t < steps - 2:
            h = 2 * dt
            k_1 = h * f(t, rho)
            k_2 = h * f(t + 1, rho + k_1 / 2)
            k_3 = h * f(t + 1, rho + k_2 / 2)
            k_4 = h * f(t + 2, rho + k_3)

            rho = rho + 1 / 2 * (k_1 / 6 + k_2 / 3 + k_3 / 3 + k_4 / 6)

        else:
            rho = rho + f(t, rho) * dt

        rho = rho / trace(rho)

        t += 1
        #
        # if real(rho[0][0]) < 0:
        #     rho[0][0] = 0
        # if real(rho[1][1]) < 0:
        #     rho[1][1] = 0
        # if real(rho[0][0]) > 1:
        #     rho[0][0] = 1
        # if real(rho[1][1]) > 1:
        #     rho[1][1] = 1

        if rho_00 == 1:
            rho_00_temp.append(real(rho[0][0]))
        if rho_01 == 1:
            rho_01_temp.append(rho[0][1])
        if rho_10 == 1:
            rho_10_temp.append(rho[1][0])
        if rho_11 == 1:
            rho_11_temp.append(real(rho[1][1]))
        if rho_22 == 1:
            rho_22_temp.append(real(rho[2][2]))

    if rho_end == 1:
        out.append(rho)
    if rho_00 == 1:
        out.append(rho_00_temp)
    if rho_01 == 1:
        out.append(rho_01_temp)
    if rho_10 == 1:
        out.append(rho_10_temp)
    if rho_11 == 1:
        out.append(rho_11_temp)
    if rho_22 == 1:
        out.append(rho_22_temp)

    else:
        if rho_end == 1:
            out = rho

    return out


def Runge_Kutta_adaptive(rho_0, pulse_amplitude, pulse_freq, pulse_time, detuning, phase, lifetime=float('inf'),
                dephasing_time=float('inf'), mw_bandwidth=0):

    steps = len(pulse_amplitude)
    dt = pulse_time/steps
    time = linspace(0, pulse_time, steps)

    # lifetime should be in ns
    # decay rate gamma (in GHz)
    gamma_1 = 1 / lifetime
    gamma_2 = 1 / dephasing_time

    #######################################################################

    pulse_freq = [x * (1 + detuning) for x in pulse_freq]

    w_0 = 2 * pi * (D_gs - B * gamma_nv)
    w_1 = 2 * pi * (D_gs + B * gamma_nv)

    def H(t):
        return 2 * pi * pulse_amplitude[t]/1000 * cos(2*pi * pulse_freq[t] * time[t] + phase) * \
               array([[0, exp(-1j * w_0 * time[t]), exp(-1j * w_1 * time[t])],
                      [exp(1j * w_0 * time[t]), 0, 0],
                      [exp(1j * w_1 * time[t]), 0, 0]])

    #######################################################################

    # w_0 = (D_gs - B * gamma_nv)
    # w_1 = (D_gs + B * gamma_nv)
    # freq = pulse_freq[0] * (1 + detuning)
    #
    # def H(t):
    #     return 2 * pi * pulse_amplitude[t] / 1000 * \
    #            array([[0, 1/2, 1/2],
    #                   [1/2, w_0-freq, 0],
    #                   [1/2, 0, w_1-freq]])

    #######################################################################

    def f(t, dm):

        lindblad_0 = 2*pi * array([[gamma_1 * dm[1][1], -(0.5*gamma_2 + mw_bandwidth)*dm[0][1], 0],
                                  [-(0.5*gamma_2 + mw_bandwidth)*dm[1][0], -gamma_1 * dm[1][1], 0],
                                   [0, 0, 0]])

        lindblad_1 = 2 * pi * array([[gamma_1 * dm[2][2], 0, -(0.5 * gamma_2 + mw_bandwidth) * dm[0][2]],
                                     [0, 0, 0],
                                     [-(0.5 * gamma_2 + mw_bandwidth) * dm[2][0], 0, -gamma_1 * dm[2][2]]])

        return 1 / 1j * (dot(H(t), dm) - dot(dm, H(t))) + lindblad_0 + lindblad_1

    rho = rho_0
    t = 0

    accuracy = 1e-6
    stepsize = 2

    while t < steps:
        if t < steps - 4 * stepsize:

            # half stepsize
            stepsize_half = int(stepsize / 2)
            h_1 = stepsize_half * 2 * dt
            k_1 = h_1 * f(t, rho)
            k_2 = h_1 * f(t + stepsize_half, rho + k_1 / 2)
            k_3 = h_1 * f(t + stepsize_half, rho + k_2 / 2)
            k_4 = h_1 * f(t + 2 * stepsize_half, rho + k_3)
            rho_1 = rho + 1 / 2 * (k_1 / 6 + k_2 / 3 + k_3 / 3 + k_4 / 6)

            k_1 = h_1 * f(t, rho_1)
            k_2 = h_1 * f(t + stepsize_half, rho_1 + k_1 / 2)
            k_3 = h_1 * f(t + stepsize_half, rho_1 + k_2 / 2)
            k_4 = h_1 * f(t + 2 * stepsize_half, rho_1 + k_3)
            rho_1 = rho_1 + 1 / 2 * (k_1 / 6 + k_2 / 3 + k_3 / 3 + k_4 / 6)

            # normal stepsize
            h_2 = stepsize * 2 * dt
            k_1 = h_2 * f(t, rho)
            k_2 = h_2 * f(t + stepsize, rho + k_1 / 2)
            k_3 = h_2 * f(t + stepsize, rho + k_2 / 2)
            k_4 = h_2 * f(t + 2 * stepsize, rho + k_3)
            rho_2 = rho + 1 / 2 * (k_1 / 6 + k_2 / 3 + k_3 / 3 + k_4 / 6)

            error = np.amax(abs(rho_1 - rho_2))
            # print(error)

            if error < accuracy:
                # print(stepsize)
                # print('')
                h_2 = stepsize * 2 * dt
                k_1 = h_2 * f(t, rho_2)
                k_2 = h_2 * f(t + stepsize, rho_2 + k_1 / 2)
                k_3 = h_2 * f(t + stepsize, rho_2 + k_2 / 2)
                k_4 = h_2 * f(t + 2 * stepsize, rho_2 + k_3)
                rho_2 = rho_2 + 1 / 2 * (k_1 / 6 + k_2 / 3 + k_3 / 3 + k_4 / 6)

                # double stepsize
                stepsize_double = stepsize * 2
                h_3 = stepsize_double * 2 * dt
                k_1 = h_3 * f(t, rho)
                k_2 = h_3 * f(t + stepsize_double, rho + k_1 / 2)
                k_3 = h_3 * f(t + stepsize_double, rho + k_2 / 2)
                k_4 = h_3 * f(t + 2 * stepsize_double, rho + k_3)
                rho_3 = rho + 1 / 2 * (k_1 / 6 + k_2 / 3 + k_3 / 3 + k_4 / 6)

                rho = rho_2
                t += 2 * stepsize

                error = np.amax(abs(rho_2 - rho_3))

                if error < accuracy:
                    # print(stepsize)
                    # print('')
                    if stepsize <= steps / 100:
                        stepsize = stepsize * 2

            else:
                if stepsize > 3:
                    stepsize = int(stepsize / 2)
                rho = rho_1
                t += stepsize

        else:
            stepsize = 1
            while t < steps:
                if t < steps - 2 * stepsize:
                    h = stepsize * 2 * dt
                    k_1 = h * f(t, rho)
                    k_2 = h * f(t + stepsize, rho + k_1 / 2)
                    k_3 = h * f(t + stepsize, rho + k_2 / 2)
                    k_4 = h * f(t + 2 * stepsize, rho + k_3)

                    rho = rho + 1 / 2 * (k_1 / 6 + k_2 / 3 + k_3 / 3 + k_4 / 6)
                    t += 1
                else:
                    rho = rho + f(t, rho) * dt
                    t += 1

        rho = rho / trace(rho)

    return rho
