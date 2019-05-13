import numpy as np
from scipy import integrate


def testinterf(xy):
    return xy*2



def fnct(DcrabPulses,time_grid):

    u1 = DcrabPulses[0]

    # hardcode parameters:
    a1 = 1.0
    a2 = 3.0
    Nt = len(time_grid)
    TT = time_grid[-1]
    dt = time_grid[1]-time_grid[0]

    #Propagate system using RK4
    y0 = np.array([1.0])
    YYtt = integrate.odeint(f_vel, y0, time_grid, args=(u1,Nt,TT,), rtol=1.1e-6)
    #xt = YYtt[:,0]
    #yt = YYtt[:,1]
    #Evaluate Cost Functional to be minimized (simple rectangular approx)
    JJ = 0.5*(np.sum(np.square(u1)) + a1*np.sum(np.square(YYtt)))*dt #+ a2*(TT-1.0)**4


    # if JJ < fRecord:  # new record!!
    #     fRecord = JJ
    #     writeRecordList(JJ, -1, -1, basePulseSafe, xx, ww)

    # Minimization return JJ
    # Maximization
    return (-1)*JJ


def f_vel(Y, t, u1, Nt, TT):
    t_ind = int(np.floor(t/TT*(Nt-1)))
    if t_ind>=Nt:
        #print(t_ind)
        t_ind=Nt-1

    return u1[t_ind]
    #return [u1[t_ind] + (c3 + 0.02*u3[t_ind])*Y[0], u2[t_ind] - (c3 + 0.005*u3[t_ind])*Y[1]]
