# -*- coding: utf-8 -*-
"""
Created on Tue Oct 01 16:45:46 2013

@author: Admin
"""

from pi3diamond import pi3d
import PulsePattern as PP
import time
import DTG

channel_map = pi3d.channel_map

def clear_block(name):
    """  deletes Block 'name' from DTG """
    DTG.Stop()
    DTG.DTG.write('BLOC:DEL "%s"' %str(name))
    
def clear_all():
    """ clears all blocks """
    DTG.DTG.write('BLOC:DEL:ALL')
    
def DTG_Set_Freq(base):
    DTG.setTimeBase(base)
    
def DTG_Get_Freq():
    DTG.getTimeBase()

def write_Block2DTG(block):
    """ writes a given instance of Block-class to DTG  """
    seq = [(['LASER','MW'], 10000)]
    Laser = PP.Block('LaserMW', seq, PP)
    DTG.FastWrite([block])
    DTG.DTG.ask('TBAS:RUN?')

def select_Block(name):
    """ selects a block in the DTG  """
    DTG.DTG.write('SEQ:LENG 1')
    DTG.DTG.write('SEQ:DATA 0, "",0,"%s",0,"",""' %str(name))
    

def Run():
    "run selected Block"
    DTG.Run()

def Stop():
    DTG.Stop()
    

def Sequence(sequence, freq, name = 'Sequence'):
    """ imitates the PulseBlester.Sequence method """
    Stop()    
    print 'Cleared all Blocks from DTG'
    print type(freq)
    b = PP.Block(name, sequence, PP)
    write_Block2DTG(b)
    DTG_Set_Freq(freq)
    print 'Block ' + name + ' written to DTG'
    select_Block(name)
    Run()
    
def Sequences(sequences, freq, name = 'Sequence'):
    """ imitates the PulseBlester.Sequence method """
    Stop()    
    print 'Cleared all Blocks from DTG'
    print type(freq)
    blocks = []
    for i,s in enumerate(sequences):
       blocks.append(PP.Block(s[1], s[0], PP))
       print 
    write_Blocks2DTG(blocks)
    DTG_Set_Freq(freq)
    print 'Block ' + name + ' written to DTG'
    #select_Block(name)
    #Run()
    
def write_Blocks2DTG(blocks):
    """ writes a given instance of Block-class to DTG  """
    seq = [(['LASER','MW'], 10000)]
    Laser = PP.Block('LaserMW', seq, PP)
    DTG.FastWrite(blocks)
    DTG.DTG.ask('TBAS:RUN?')
    
def High(channels):
    """ sets giben [channels] to high """
    s = []    
    all_channel = []
    for c in channels:
        all_channel.append(c)
    print all_channel
    for c in range(10):
        s.append((all_channel, 1000))
    print s
    Sequence(s, 'high:' + str(channels))
    
def Light():
#    #High(['LASER']) 
##    DTG.DTG.write('PGENA:CH1:AMPLitude 1.3')
##    DTG.DTG.write('PGENA:CH1:OUTPut ON')
#    DTG.DTG.write('PGENA:CH1:LOW 0.25')
#    DTG.DTG.write('PGENA:CH1:HIGH 1.5') 
#    DTG.DTG.write('PGENA:CH1:OUTPut ON')

#    Sequence([(['LASER','MW'], 10000)], 1000000000,'LaserMW')
    select_Block('LaserMW')
    Run()
    
def Night():
    #High([])
    DTG.Stop()
    #DTG.DTG.write('PGENA:CH1:OUTPut OFF')
    
def XYSequence(t_pi2, t_pi, t_3pi2, tau, N, laser = 1500):
    sequence = []
    XY = []
    YX = [] 
        
    for t in tau:
        sequence += [(['MW'],t_pi2)]
        XY = [([],t),(['MW'],t_pi),([],2*t),(['MWy'],t_pi),([],2*t),(['MW'],t_pi),([],2*t),(['MWy'],t_pi),([],2*t)]
        YX = [(['MWy'],t_pi),([],2*t),(['MW'],t_pi),([],2*t),(['MWy'],t_pi),([],2*t),(['MW'],t_pi),([],t)]
        for n in range(N):
            #print n
            sequence += XY+YX
        sequence += [(['MW'],t_pi2),([],90),(['LASER'],laser),([],800)]
        
    for t in tau:
        sequence += [(['MW'],t_pi2)]
        XY = [([],t),(['MW'],t_pi),([],2*t),(['MWy'],t_pi),([],2*t),(['MW'],t_pi),([],2*t),(['MWy'],t_pi),([],2*t)]
        YX = [(['MWy'],t_pi),([],2*t),(['MW'],t_pi),([],2*t),(['MWy'],t_pi),([],2*t),(['MW'],t_pi),([],t)]
        for n in range(N):
            #print n
            sequence += XY+YX
        sequence += [(['MW'],t_3pi2),([],90),(['LASER'],laser),([],800)]
            
    sequence += [  (['sequence'],100)  ]
    Sequence(sequence, 'XY32')
    
    
    
if __name__=='__main__':
    print 'DTG_Blaster start'
    Stop()
    DTG_Set_Freq(1e9)
    s = []
    for i in range(1):
        s.append((['LASER'], 100))
        s.append((['MW'], 100))
        s.append((['MWy'], 100))
        s.append(([], 100))
        s.append((['sequence'], 100))
    print 'seq generated'
    l = []
    seq1 = [s,'s1']
    seq2 = [s,'s2']
    seq3 = [s,'s3']
    
    l.append
#    Sequence(s, 's1')
    #High(['LASER', 'MW'])
    #XYSequence(20, 40, 60, [10,20], 2, 1500)
    Sequences([seq1, seq2, seq3], 1e9)
#    Night()
#    time.sleep(2)    
    #Light()
    #time.sleep(5)
    #Night()
    print 'done'
    

