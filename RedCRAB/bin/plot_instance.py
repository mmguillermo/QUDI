"""
plot_instance.py - Class for plotting pulses and figure of merit
@author: Marco Rossignolo
Current version number: 0.0.1
Current version dated: 25.04.2018
First version dated: 24.04.2018
"""
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import time
class PlotGraph:

    def __init__(self, is_max, n_view, max_fnct_ev):
        """
        CONSTRUCTOR of Class PlotGraph: Draw the last n_view optimized set of pulses and fom of current SI
        n_view: number of last pulses to draw
        max_fnct_ev: max number of evaluation for SI >1. It's used to draw dotted line in fom canvas
        """
        #
        self.fund_is_max = is_max
        self.fund_limit_u_views = n_view
        self.fund_Max_Fnct_eval = float(max_fnct_ev)
        self.fund_fig = plt.figure()
        # List of u graph
        self.graph_ul = []
        # List of list of Artist for pulses
        self.artist_list = []
        # List of Artist for fom (best ever, previous best, current best)
        self.artist_list_fom = [None, None, None]
        # The worst fom value
        self.worst_fom_value = None
        if self.fund_is_max:
            self.worst_fom_value = - 100**100
        else:
            self.worst_fom_value = 100**100

        #
        self.best_fom_record = None
        #
        self.previous_fom_record = None
        #
        self.curr_fom_record = self.worst_fom_value
        #
        self.curr_Neval = []
        #
        self.curr_lvalue_min = []
        #
        self.curr_lvalue_max = []
        #
        self.do_clear = True
        #
        self.N_pulses = None
        #
        self.is_first_fom_plot = True
    def create_figure(self, Npulses):
        #grid
        for ii in range (0,Npulses): self.curr_Neval.append(0)
        self.N_pulses = Npulses
        gs = gridspec.GridSpec(2, Npulses)
        for ii in range (0,Npulses):
            graph = self.fund_fig.add_subplot(gs[0, ii])  # row 0, col ii
            graph.set_xlabel('t')
            graph.set_ylabel(r'$u_{' + str(ii + 1) + '}$(t)')

            self.graph_ul.append(graph)

            self.artist_list.append([])
            self.curr_lvalue_min.append([])
            self.curr_lvalue_max.append([])

        self.graph_fom = self.fund_fig.add_subplot(gs[1,:])
        self.graph_fom.set_xlabel('Number Evaluation')
        self.graph_fom.set_ylabel('Fom')

    #
    #MarcoR Add self.curr_Neval
    # If self.curr_Neval == Neval we are in a re_evaluation fom. So the pulses are the same, and it makes non sense
    # re-plotting them
    def plot_u(self, Neval, timegrid, pulses, si, n):
        #MarcoR 22.06.2018
        # clear pulse canvas and correlated objects, at the beginning of a new SI
        if Neval == 1 and si>1 and self.do_clear:
            #self.do_clear = False
            self.graph_ul[n].clear()
            self.graph_ul[n].set_xlabel('t')
            self.graph_ul[n].set_ylabel(r'$u_{' + str(n + 1) + '}$(t)')
            # Delete previous min / max values of n-pulse
            self.curr_lvalue_min[n] = []
            #
            self.curr_lvalue_max[n] = []
            #
            # Delete all n-previous-pulse artists reference
            # No! All artists are deleted with graph_ul[n].clear()
            #for ii in range (0, len(self.artist_list[n])):
            #    self.artist_list[n][ii].remove()
            self.artist_list[n] = []

        # n is the number of pulses
        if self.curr_Neval[n] == Neval:
            return
        else:
            self.curr_Neval[n] = Neval
        n_view = self.fund_limit_u_views
        if len(self.artist_list[n]) == n_view:
            # remove the first line appeared
            self.artist_list[n][0].remove()
            # move the artist elements
            self.artist_list[n][0:n_view-1] = self.artist_list[n][1:n_view]
            # move min and max
            self.curr_lvalue_min[n][0:n_view-1] = self.curr_lvalue_min[n][1:n_view]
            self.curr_lvalue_min[n][-1] = pulses.min()
            self.curr_lvalue_max[n][0:n_view-1] = self.curr_lvalue_max[n][1:n_view]
            self.curr_lvalue_max[n][-1] = pulses.max()
        else:
            # add last min and max pulses
            self.curr_lvalue_min[n].append(pulses.min())
            self.curr_lvalue_max[n].append(pulses.max())
        # Get min and max of all min/max pulses
        miny = (np.array(self.curr_lvalue_min[n])).min()
        maxy = (np.array(self.curr_lvalue_max[n])).max()
        # Set ylimit in the picture
        self.graph_ul[n].set_ylim(miny - 0.5, maxy + 0.5)

        # Update graph and get the artist reference
        ll, = self.graph_ul[n].plot(timegrid, pulses)

        # Add new artist reference
        if len(self.artist_list[n]) == n_view:
            self.artist_list[n][-1] = ll
        else:
            self.artist_list[n].append(ll)

        plt.pause(0.00005)


###END plot_u
    def plot_fom(self, Neval, fom, si, is_Opti_reach):
        #Adding best ever fom, previous best, current best
        if Neval == 1 and si>1 and self.do_clear:
            #self.do_clear = False
            self.graph_fom.clear()
            for ii in range(0,3): self.artist_list_fom[ii] = None
            self.graph_fom.set_xlabel('Number Evaluation')
            self.graph_fom.set_ylabel('Fom')
            #
            fs = self.best_fom_record
            max_fnc = self.fund_Max_Fnct_eval
            # Dotted line drawing fs best fom record
            if self.artist_list_fom[0] != None: self.artist_list_fom[0].remove()
            ll, =self.graph_fom.plot([0.0, max_fnc + 2.0],[fs,fs], '-', label='best ever', color='blue' )
            self.artist_list_fom[0] = ll
            self.previous_fom_record = self.curr_fom_record
            self.curr_fom_record = self.worst_fom_value
            fsp = self.previous_fom_record
            # Dotted line drawing fs previous fom record
            if self.artist_list_fom[1] != None: self.artist_list_fom[1].remove()
            ll, = self.graph_fom.plot([0.0, max_fnc + 2.0], [fsp, fsp], '--', label='previous best', color='red')
            self.artist_list_fom[1] = ll
        if Neval > 1: self.do_clear = True

        if fom < -10**99 or fom > 10**99: return
        # Update best_fom_record
        if is_Opti_reach:
            self.best_fom_record = fom
        # Update curr_fom_record
        if self.fund_is_max:
            if fom > self.curr_fom_record:
                self.curr_fom_record = fom
                # In case of fluctuations
            if self.best_fom_record != None:
                if self.curr_fom_record > self.best_fom_record: self.curr_fom_record = self.best_fom_record
        else:
            if fom < self.curr_fom_record:
                self.curr_fom_record = fom
                # In case of fluctuations
            if self.best_fom_record != None:
                if self.curr_fom_record < self.best_fom_record: self.curr_fom_record = self.best_fom_record
        fsc = self.curr_fom_record
        max_fnc = self.fund_Max_Fnct_eval
        if self.artist_list_fom[2] != None: self.artist_list_fom[2].remove()
        ll, = self.graph_fom.plot([0.0, max_fnc + 2.0], [fsc, fsc], ':', label='current best', color='green')
        self.artist_list_fom[2] = ll
        #print(str(fom) + "\n")
        if self.do_clear and Neval==1:
            self.graph_fom.scatter(Neval, fom, label='SI_' + str(si), color='black', marker=',')
        else:
            self.graph_fom.scatter(Neval, fom, color='black', marker=',')
        if Neval == 1 and self.do_clear:
            self.do_clear = False
        # Resize box
        if self.is_first_fom_plot:
            box = self.graph_fom.get_position()
            self.graph_fom.set_position([box.x0, box.y0 + box.height * 0.15,
                                 box.width, box.height * 0.85])
            self.is_first_fom_plot = False
        #legend
        self.graph_fom.legend(bbox_to_anchor=(0., -0.3, 1., -0.05),
                          fancybox=True, shadow=True, ncol=4, mode="expand")
        plt.pause(0.00005)
###END plot_fom
    def plot_show(self):
        plt.savefig("test.pdf")
        #plt.close('all')
