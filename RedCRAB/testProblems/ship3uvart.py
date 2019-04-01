import numpy as np
from scipy import integrate


def testinterf(xy):
    return xy*2



#def fnct(u1,u2,u3,time_grid):
#MarcoR, Maybe 
def fnct(DcrabPulses,time_grid):
    u1 = DcrabPulses[0]
    u2 = DcrabPulses[1]
    u3 = DcrabPulses[2]
#
    # ##global fRecord
    # #get time params
    # #T0 = 0.796436
    # TT = T0*xx[4]
    # time_grid = np.linspace(0, TT, Nt)
    # dt = time_grid[1]-time_grid[0]
    #
    # #Build up to be added -> controled pulses
    # u1add = basePulse1 #Longitudinal beam
    # u2add = basePulse2 #Transverse beam
    # u1add = u1add + xx[0]*np.sin(2*np.pi/TT*ww[0][0]*time_grid) + xx[1]*np.cos(2*np.pi/TT*ww[0][0]*time_grid)
    # u2add = u2add + xx[2]*np.sin(2*np.pi/TT*ww[0][1]*time_grid) + xx[3]*np.cos(2*np.pi/TT*ww[0][1]*time_grid)
    # #Fixed preoptimized pulses -> initial guesses
    # u1fix = 2.63*(1+time_grid/0.31)**(-2.0)
    # u2fix = 2.78*(1+time_grid/0.31)**(-2.0)
    # #pulses put together:
    # u1 = np.maximum(np.minimum(u1fix*(1.0+u1add),P1max),0)
    # u2 = np.maximum(np.minimum(u2fix*(1.0+u2add),P2max),0)
    # #Build up magnetic ramp
    # mm = xx[7]
    # c4 = 0.3 #!! ALSO CHANGE IN PLOT
    # B_m = (7.5-0.5*TT*mm-c4*np.abs(mm))+mm*time_grid #!! ALSO CHANGE IN PLOT
    # u3add = basePulse3 + B_m
    # u3add = u3add + xx[5]*np.sin(2*np.pi/TT*ww[0][2]*time_grid) + xx[6]*np.cos(2*np.pi/TT*ww[0][2]*time_grid)
    # u3 = np.maximum(np.minimum(u3add,I3max),0)

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
    #JJ = JJ*(1 + float(np.random.normal(0, 0.01, 1)))
    #update plot
    #if flagPlot >= 1 and superit <= flagPlot:
    #    do_Plot(superit, time_grid, u1, u2, u3, u1fix, u2fix, basePulse1, basePulse2,
    # basePulse3, B_m, P1max, P2max, I3max, Nt, TT, JJ, MaxFunctEv,f_opti_simo,mm_mo)
    #iterfomges = open('bec_dummytest_s1_fom_total_001.txt', 'a')
    #iterfomges.write(str(JJ) + '\n')
    #iterfomges.close()
    #time.sleep(0.0)

    # if JJ < fRecord:  # new record!!
    #     fRecord = JJ
    #     writeRecordList(JJ, -1, -1, basePulseSafe, xx, ww)

    return JJ


def f_vel(Y, t, u1, u2, u3, Nt, TT, c3):
    #t_ind = np.floor(t/TT*(Nt-1))
    #MarcoR 26.04.2018 
    t_ind = int(np.floor(t/TT*(Nt-1)) )
    if t_ind>=Nt:
        #print(t_ind)
        t_ind=Nt-1
    return [u1[t_ind] + (c3 + 0.02*u3[t_ind])*Y[0], u2[t_ind] - (c3 + 0.005*u3[t_ind])*Y[1]]
