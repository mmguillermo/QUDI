from numpy import array, tensordot, sqrt, real, dot, pi, exp, cos, trace, linspace

D_gs = 2.87
gamma_nv = 2.8e-3
B = 510


def Fidelity(rho, aim):

    # return real(rho[1][1])
    state = []
    state_aim = []
    for i in range(len(rho)):
        state.append(real(rho[i][i]))
        state_aim.append(real(aim[i][i]))

    state = array(state)
    state_aim = array(state_aim)

    state = state / sqrt(dot(state, state))
    state_aim = state_aim / sqrt(dot(state_aim, state_aim))

    # fid = sqrt(dot(state, state_aim))
    fid = dot(state, state_aim)

    return fid


def Runge_Kutta(rho_0, pulse_amplitude, pulse_freq, pulse_time, detuning, phase,
                rho_end=0, rho_00=0, rho_01=0, rho_10=0, rho_11=0, rho_22=0):

    steps = len(pulse_amplitude)
    dt = pulse_time[1] - pulse_time[0]
    time = pulse_time

    #######################################################################

    pulse_freq = [x * (1 + detuning) for x in pulse_freq]

    w_0 = 2 * pi * (D_gs - B * gamma_nv)
    w_1 = 2 * pi * (D_gs + B * gamma_nv)

    def H(t):
        return 2 * pi * pulse_amplitude[t]/1000 * cos(2*pi * pulse_freq[t] * time[t] + phase) * \
               array([[0, exp(-1j * w_0 * time[t]), exp(-1j * w_1 * time[t])],
                      [exp(1j * w_0 * time[t]), 0, 0],
                      [exp(1j * w_1 * time[t]), 0, 0]])

    def f(t, dm):

        return 1 / 1j * (dot(H(t), dm) - dot(dm, H(t)))


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


def fnct(DcrabPulses, DcrabParas, time_grid):

    rho_0 = array([[1, 0, 0], [0, 0, 0], [0, 0, 0]])
    resonance_freq = D_gs - gamma_nv * B

    aim = array([0, 1, 0])
    aim = tensordot(aim, aim, axes=0)

    # set pulse time in ns
    pulse_time = 50  # ns
    steps = len(time_grid)

    time_grid = time_grid * 1e9

    pulse_phase = 0

    pulse_amplitude = DcrabPulses[0]
    pulse_freq = [resonance_freq] * steps

    detunings = [-0.001, 0.001]
    fid = 0

    for det in detunings:
        rho = Runge_Kutta(rho_0, pulse_amplitude, pulse_freq, time_grid, detuning=det, phase=pulse_phase, rho_end=1)
        fid += Fidelity(rho, aim)

    fom = fid / len(detunings)

    return fom


# TT = 50
# steps = 1001
# ampl = 10
# ampl = [ampl] * steps
# time = linspace(0, TT, steps)
#
# print(fnct([ampl], 0, time))
