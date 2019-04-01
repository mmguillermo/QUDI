"""
Code for starting exercise 1 SECOND PART
Before interfacing this code with RedCRAB test it with the statements that you can find below
"""
import numpy as np
from scipy import integrate

def fnct(DcrabPulses,DcrabParas,time_grid):

  #Control fields
  global u1
  global u2
  global u3
  global u4

  #Bins number
  global Nt

  #Total time
  global TT

  #Pulses from RedCRAB
  u1 = DcrabPulses[0]
  u2 = DcrabPulses[1]
  u3 = DcrabPulses[2]
  u4 = DcrabPulses[3]


  #Bins number
  Nt = len(time_grid)
  #Final time
  TT = time_grid[-1]

  # Cycle on coupling
  x = np.arange("", "", "")
  #Fidelity list
  F_i = []
  for coupling in x:
    #function that returns fidelity_i for each coupling
    F_i.append(fid_i(coupling,time_grid) )

  F_i = np.asarray(F_i)
  # Infidelity
  JJ = 1 - np.mean(F_i)
  return JJ

def fid_i(coupling, time_grid):
  #Drift Hamiltonian
  global H_d
  #Control Hamiltonians
  global H_c_1
  global H_c_2
  global H_c_3
  global H_c_4
  #Drift Hamiltonian
  H_d = np.asarray([["", "", ""], ["", "", ""],["", "", ""] ] )

  #Control Hamiltonians
  H_c_1 = "" * np.asarray([["", "", ""], ["", "", ""], ["", "", ""]])
  H_c_2 = "" * np.asarray([["", "", ""], ["", "", ""], ["", "", ""]])

  # Qutip objects holding the real and imaginary part of the Hamiltoninan H_1S
  H_c_3 = "" * np.asarray([["", "", ""], ["", "", ""], ["", "", ""]])
  H_c_4 = "" * np.asarray([["", "", ""], ["", "", ""], ["", "", ""]])

  #Initial state
  psi_0 = np.asarray(["", "", ""])
  #Finale state
  psi_targ = np.asarray(["", "", ""])


  # Compute Final State
  # Initial and Final time
  time_span = [time_grid[0], time_grid[-1]]
  # Get All the info about temporale evolution. In particular state at final time T with RK45 method

  Psi = integrate.solve_ivp(f_vel, time_span, psi_0, method='RK45', t_eval=[TT], vectorized=True)

  # Take the final time
  psi_T = Psi.y

  psi_T = psi_T.reshape(3,1)
  # Normalize the state
  Psi_n = np.dot(psi_T.conj().T, psi_T )
  psi_T = psi_T / Psi_n

  # Compute Fidelity
  psi_targ = psi_targ.reshape(3,1)
  inner_p = np.dot(psi_targ.conj().T, psi_T )
  F = abs( inner_p )
  
  # Fidelity
  F_def = F[0][0]
  return F_def

def f_vel(t, Y):
  t_ind = int(np.floor(t/TT*(Nt-1)))
  if t_ind >= Nt:
    t_ind = Nt-1
  u_t_1 = u1[t_ind]
  u_t_2 = u2[t_ind]
  u_t_3 = u3[t_ind]
  u_t_4 = u4[t_ind]
  
  H_tot = (H_d + u_t_1*H_c_1 + u_t_2*H_c_2 + u_t_3*H_c_3 + u_t_4*H_c_4)

  Y_t = np.dot(-1j * H_tot, Y)
  return Y_t

# CODE FOR TESTING
timegrid = np.linspace(0.0, 1.0, 101)
u1 = np.exp(-timegrid**2)
u2 = np.exp(-timegrid**2)
u3 = np.exp(-timegrid**2)
u4 = np.exp(-timegrid**2)
DcrabPulses = []
DcrabPulses.append(u1)
DcrabPulses.append(u2)
DcrabPulses.append(u3)
DcrabPulses.append(u4)
DcrabParas = []

#Calculate figure of merit
JJ = fnct(DcrabPulses,DcrabParas,timegrid)
print(JJ)


