from numpy import array, sqrt, exp, sin, eye, pi, arange, linspace, kron, dot

# zero field splitting of NV center
D_gs = 2.87

# gyromagnetic ratio of NVs electron spin (GHz/Gauss)
# gamma_nv = 2.8e-3 / (2*pi)
gamma_nv = 2.8e-3

# magn field
B = 510
# nu = 2807337536.986019e-9
# B = (D_gs - nu)/gamma_nv
