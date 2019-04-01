from numpy import trace, sin, array, pi, linspace, real, imag, abs, dot, conjugate, transpose, sqrt, log, exp, einsum
from scipy.linalg import sqrtm
import matplotlib.pyplot as plt
import smtplib, sys


def dagger(m):
    return conjugate(transpose(m))

# adds a line in the beginning of a file
def line_prepender(filename, line):
    with open(filename, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(line.rstrip('\r\n') + '\n' + content)


# adds a line in the end of a file (with new line)
def line_appender(filename, line):
    with open(filename, 'a') as f:
        f.write('\n' + line)


def PartialTrace(rho, num_1, num_2, subsys):

    reshaped_dm = rho.reshape([num_1, num_2, num_1, num_2])

    if subsys is 1:
        return einsum('ijik->jk', reshaped_dm)
    elif subsys is 2:
        return einsum('jiki->jk', reshaped_dm)
    else:
        print('Incorrect use of PartialTrace')


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


def Fidelity_old(rho, aim, subsys=2):

    if aim.ndim is 1:
        # This one only valid for pure states (no decoherence)
        if len(rho[0]) is not len(aim):
            rho = PartialTrace(rho, subsys)
        fid = abs((dot(dagger(aim), dot(rho, aim))))
        return fid

    if aim.ndim is 2:
        if len(rho[0]) is not len(aim[0]):
            rho = PartialTrace(rho, subsys)
        # fid = abs((trace(sqrtm(dot(dot(sqrtm(rho), aim), sqrtm(rho))))) ** 2)
        fid = abs(trace(sqrtm(dot(dot(sqrtm(rho), aim), sqrtm(rho)))))
        return fid


def gaussian(x, FWHM, x_0=0):
    sigma = FWHM/(2*sqrt(2*log(2)))
    return exp(-((x-x_0)/sigma)**2 / 2)


# function to make pulse podulation or whole pulse zero at beginning and end
def lamb(t, steps, width=None):
    # steps = steps-1
    # pulse_lambda = - 2 ** width / steps ** width * (t - steps / 2) ** width + 1

    # x = (t-steps / 2) / (steps / 2 * 0.98)
    # pulse_lambda = exp(-(x**2)**width)

    if width is None:
        width = steps*0.005

    factor_width = 1.6

    if t < factor_width * width:
        x_0 = factor_width * width
        pulse_lambda = gaussian(t, width, x_0)
    elif t > steps - factor_width * width - 1:
        x_0 = steps - factor_width * width - 1
        pulse_lambda = gaussian(t, width, x_0)
    else:
        pulse_lambda = 1

    return pulse_lambda


def pulse_modulation_am(A, phi, w, time):

    steps = len(time)
    temp = [lamb(t, steps) * A * sin(w * time[t] + phi) for t in range(steps)]
    # temp = [A * sin(w * time[t] + phi) for t in range(steps)]

    return array(temp)


def pulse_modulation_fm(A, phi, w, time):

    steps = len(time)
    temp = [A * sin(w * time[t] + phi) for t in range(steps)]

    return array(temp)



####################################################################################################################

def plot_simple(x, y):

    fig = plt.figure(figsize=(11, 7))
    ax = fig.add_subplot(111)
    plt.subplots_adjust(bottom=0.15, top=0.9, right=0.98, left=0.1)

    plt.plot(x, y, color='darkblue', linewidth=1, zorder=10)
    # plt.scatter(x, y, color='k', s=15)

    plt.grid(True, which="both")

    plt.show()


def plot_compare(errors, opt, standard, date, save=0, extension='', prefix='', standard_label='guess'):

    fig = plt.figure(figsize=(11, 7))
    ax = fig.add_subplot(111)
    plt.subplots_adjust(bottom=0.15, top=0.9, right=0.98, left=0.1)

    errors = errors * 100

    plt.plot(errors, standard, color='red', linewidth=1.5, zorder=5, label=standard_label)
    plt.plot(errors, opt, color='darkblue', linewidth=1.5, zorder=10, label='optimized')
    ax.legend(loc='best')

    plt.ylabel('Fidelity', fontsize=20, labelpad=20, rotation=90)
    plt.xlabel('Detuning ($\%$)', fontsize=20, labelpad=20)
    plt.grid(True, which="both")

    if save == 1:
        plt.savefig('Data/' + date + '/' + prefix + 'Compare' + extension + '.png')


def plot_compare_all(errors, opt, standard, short, date, save=0, extension='', prefix=''):

    fig = plt.figure(figsize=(11, 7))
    ax = fig.add_subplot(111)
    plt.subplots_adjust(bottom=0.15, top=0.9, right=0.98, left=0.1)

    errors = errors * 100

    plt.plot(errors, opt, color='darkblue', linewidth=1.5, zorder=10, label='optimized')
    plt.plot(errors, standard, color='darkgreen', linewidth=1.5, zorder=5, label='guess')
    plt.plot(errors, short, color='red', linewidth=1.5, zorder=5, label='short pulse')

    ax.legend(loc='best')
    # plt.ylim(-0.1, 1.1)
    plt.ylabel('Fidelity', fontsize=20, labelpad=20, rotation=90)
    plt.xlabel('Detuning ($\%$)', fontsize=20, labelpad=20)
    plt.grid(True, which="both")

    if save == 1:
        plt.savefig('Data/' + date + '/' + prefix + 'Compare' + extension + '.png')


def plot_time_evol(time, y, names, date='', save=0, filename='Time_Evol', extension=''):

    fig = plt.figure(figsize=(11, 7))
    ax = fig.add_subplot(111)
    plt.subplots_adjust(bottom=0.15, top=0.97, right=0.98, left=0.1)

    colour = ['darkblue', 'red', 'green', 'orange']

    for i in range(0, len(y)):
        if i < 4:
            col = colour[i]
        else:
            col = 'black'

        plt.plot(time, y[i], color=col, linewidth=1.5, zorder=5, label=names[i])

    ax.legend(loc='best')
    plt.ylabel('Re$\left[\\varrho_{ii}\\right]$', fontsize=20, labelpad=20, rotation=90)
    plt.xlabel('Time in ns', fontsize=20, labelpad=20)
    plt.grid(True, which="both")

    if save == 1:
        plt.savefig('Data/' + date + '/' + filename + extension + '.png')


####################################################################################################################



class Logger(object):

    def __init__(self, date):
        self.date = date
        self.terminal = sys.stdout
        self.log = open('Data/' + self.date + '/Output.txt', 'w+')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        pass
