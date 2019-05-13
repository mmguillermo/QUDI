import os
import numpy as np
from scipy import integrate
import time
import random

def testinterf(xy):
    return xy*2

def fnct(u1, u2,time_grid):
    u3 = u2

    # hardcode parameters:
    (l1, l2, c3) = (1.0, 30.0, 0.5)
    Nt = len(time_grid)
    TT = time_grid[-1]
    dt = time_grid[1]-time_grid[0]

    #Propagate system using RK4
    y0 = np.array([0, 0])
    YYtt = integrate.odeint(f_vel, y0, time_grid, args=(u1,u2,u3,Nt,TT,c3,), rtol=1.1e-6)
    xt = YYtt[:,0]
    yt = YYtt[:,1]
    #Evaluate Cost Functional to be minimized (simple rectangular approx)
    JJ = (0.5*l1*np.sum(np.square(u1) + np.square(u2))  + 0.5*l2*np.sum(np.square(xt-2) + np.square(yt-0.7)) )*dt - 20*(1+TT)**1    + 100000*(-1)*np.min([TT-1,0]) #4*(1+TT)
    JJ += random.uniform(10.0, 20.0)
    return JJ


def f_vel(Y, t, u1, u2, u3, Nt, TT, c3):
    t_ind = int(np.floor(t/TT*(Nt-1)) )
    if t_ind>=Nt:
        t_ind=Nt-1
    return [u1[t_ind] + (c3 + 0.02*u3[t_ind])*Y[0], u2[t_ind] - (c3 + 0.005*u3[t_ind])*Y[1]]

def readData(pathfile):
    exit_code = 0
    if not os.path.isfile(pathfile):
        exit_code = -1
        return (np.array([]), [], exit_code)
    time.sleep(0.1)
    print("Read " + pathfile + '\n')
    try:
        with open(pathfile, "r") as localpulsefile:
            pulselines = localpulsefile.readlines()

        TT = []
        u = []
        for element in pulselines:
            line = [float(ii) for ii in str(element).strip().split()]
            TT.append(line[0])
            u.append(line[1])
        TT = np.asarray(TT)
        u = np.asarray(u)
        return (TT, u, exit_code)
    except OSError as err:
        exit_code = 4
        return (np.array([]), [], exit_code)
    except IndexError:
        exit_code = 4
        return (np.array([]), [], exit_code)
    except (TypeError, ValueError):
        exit_code = 4
        return (np.array([]), [], exit_code)
        
def writestats(fom, pathfile1, std, pathfile2):
    try:
        with open(pathfile1, "w+") as localfomfile:
            localfomfile.write(str(fom))
            #localfomfile.close()
        with open(pathfile2, "w+") as localstdfile:
            localstdfile.write(str(std))
            #localstdfile.close()
    except Exception as ex:
        print(ex.args)
    return
# Here start the program
exit_code1 = -1
exit_code2 = -1
job_code = -1
wait_time = 0
while(True):
    if job_code != 0: 
    	print("Waiting for pulses")
    	job_code = 0
    if wait_time == 600:
    	break
    if exit_code1 != 0:
    	# Change path here
        (TT, u1, exit_code1) = readData("../PulsesTest/pulse_1.txt")
    if exit_code2 != 0:
    	# Change path here
        (TT, u2, exit_code2) = readData("../PulsesTest/pulse_2.txt")
    if exit_code1 == 0 and exit_code2 == 0:
        print("Compute FOM" + '\n')
        fom = fnct(u1, u2, TT)
        #time.sleep(5) Simulated fom experiment-evaluation
        std = random.uniform(0.001, 2.0)
        writestats(fom, "fom.txt", std, "std.txt")
        time.sleep(0.01)
        pathfile = "../PulsesTest/pulse_1.txt"
        if os.path.isfile(pathfile):
            os.remove(pathfile)
            print("Remove ../PulsesTest/pulse_1.txt" + '\n')
        pathfile = "../PulsesTest/pulse_2.txt"
        if os.path.isfile(pathfile):
            os.remove(pathfile)
            print("Remove ../PulsesTest/pulse_1.txt" + '\n')
        exit_code1 = -1
        exit_code2 = -1
        job_code = -1
        wait_time = 0
    time.sleep(1)
    wait_time += 1
print("End")
