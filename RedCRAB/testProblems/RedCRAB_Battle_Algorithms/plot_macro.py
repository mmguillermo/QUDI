import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from matplotlib.legend_handler import HandlerLine2D
def plot_xy(x, y, y_min, y_max, x_label, y_label,namefile):
    #fund_fig = plt.figure(figsize=(4,4))
    fund_fig = plt.figure()
    gs = gridspec.GridSpec(1, 1)
    
    graph = fund_fig.add_subplot(gs[0, :])
    graph.plot(x, y)
    
    #plt.gca().get_yaxis().get_major_formatter().set_powerlimits((-5, 5))
    if (x[len(x)-1] > 100.0) :
	print("Sci on x")
    	plt.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
    plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    graph.set_xlabel(x_label, fontsize=20)
    graph.set_ylabel(y_label, fontsize=20)
    
    #graph.xaxis.label.set_fontsize(50)
    graph.yaxis.get_offset_text().set_fontsize(20)
    graph.xaxis.get_offset_text().set_fontsize(20)
    for tick in graph.yaxis.get_major_ticks():
                tick.label.set_fontsize(20)
                # specify integer or one of preset strings, e.g.
                #tick.label.set_fontsize('x-small') 
                #tick.label.set_rotation('vertical')
    for tick in graph.xaxis.get_major_ticks():
                tick.label.set_fontsize(20) 
                # specify integer or one of preset strings, e.g.
                #tick.label.set_fontsize('x-small') 
                #tick.label.set_rotation('vertical')
    plt.ylim(y_min,y_max)
    plt.locator_params(axis='x', nbins=6)
    plt.tight_layout()
    plt.savefig(namefile)
    plt.show()
    return

def plot_hist(x, n_bins, x_label, y_label):
    fund_fig = plt.figure(figsize=(4,2))
    gs = gridspec.GridSpec(1, 1)
    
    hist = fund_fig.add_subplot(gs[0, :])
    
    #n, bins, patches = hist.hist(x, n_bins, density=False)
    n, bins, patches = hist.hist(x, density=True)
    hist.set_xlabel(x_label)
    hist.set_ylabel(y_label)
    
    plt.show()
    return
    
