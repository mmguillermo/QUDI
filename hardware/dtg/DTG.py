import numpy
import struct

from visa import instrument

from pi3diamond import pi3d
import DtgIO

log = pi3d.get_logger()

#import socket
#import time
#class RawTcpIpInstrument(object):
#    def __init__(self, address, port):
#        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#        self.socket.connect((address, port))
#        #self.fil = open('dtg.dat', 'w')
#
#    def write(self, cmd):
#        self.socket.send(cmd + '\n')
#        #self.fil.write(time.asctime() + ' ' + cmd + '\n')
#
#    def ask(self, question):
#        self.write(question)
#        time.sleep(0.2)
#        #self.fil.write(time.asctime() + ' ' + question)
#        answer = self.socket.recv(1024)
#        return answer[:-2]
#DTG = RawTcpIpInstrument('192.168.0.2', 4003)


DTG5334 = False
try: 
    DTG5334 = pi3d.DTG5334      #define DTG5334 in the customfile as True if you use it
except:
    DTG5334 = False




DTG = instrument(pi3d.DTG_visa_device, timeout=60)
DTG.chunk_size=2**20
DTG.timeout=1000
#DTG.term_chars='\n'

ChunkSize = 1000000

# parameters are stored in pi3diamond
ChannelMap = pi3d.channel_map
#NumberOfChannels = pi3d.DTG_number_of_channels
NumberOfChannels = 4
GroupName = pi3d.DTG_channel_group_name

def ChannelsToString(channels):
    bits = numpy.zeros((NumberOfChannels,), dtype=numpy.bool)
    for channel in channels:
        bits[ChannelMap[channel]] = 1
    s = ''
    for bit in bits:
        s += '%i'%bit
    return s

def ChannelsToBinary(channels):
    bits = 0
    for channel in channels:
        bits |= 1 << ChannelMap[channel]
    return struct.pack('B',bits)

def WriteStepIntoBlock(name, channels, length, offset):
    n = int(length)
    DTG.write('BLOCK:SEL "'+name+'"')
    #DTG.write('VECT:IOF "'+GroupName+'"' )
    #DTG.write('VECT:DATA %i, %i, '%(offset, n) + '"'+ChannelsToString(channels)*n+'"' )
    #DTG.write('VECT:BIOF "Group1[0:1]"' )
    DTG.write('VECT:BIOF "'+GroupName+'"' )
#    DTG.write('VECT:BDAT %i,%i,'%(offset,n) + '#%i%i'%(len(str(n)), n) + ChannelsToBinary(channels)*n)
    m = 0
    while m < n:
        k = min(n-m, ChunkSize)
        log.debug('transferring sequence, offset=%i, length=%i ...' % (m,k))
        DTG.write('VECT:BDAT %i,%i,'%(offset+m, k) + '#%i%i'%(len(str(k)), k) + ChannelsToBinary(channels)*k)
        m += k

def WriteSequenceIntoBlock(name, sequence, offset):
    i = offset
    for channels, length in sequence:
        WriteStepIntoBlock(name, channels, length, i)
        i += length
    return i

def WriteBlock(name, sequence):
    # clear existing block with same name
    length = sum([ n for dummy, n in sequence ])
    DTG.write('BLOCK:DEL "'+name+'"')
    DTG.write('BLOC:NEW "'+name+'", %i' % length)
    WriteSequenceIntoBlock(name, sequence, 0)

def Pattern(Blocks, Lines):
    DTG.write('SEQ:LENG %i'%len(Lines))
    DTG.write('BLOC:DEL:ALL')
    for block in Blocks:
        WriteBlock(block[0], block[1])
    for line in Lines:
        DTG.write(line)

def State(flag = None):
    if flag is not None:
        if (flag):
            DTG.write('TBAS:RUN ON')
        else:
            DTG.write('TBAS:RUN OFF')
    return DTG.ask('TBAS:RUN?')

def setTimeBase(f):
    DTG.write('TBAS:RUN OFF')
    # Set external 10 MHz reference    
    DTG.write('TBAS:SOURce EXTReference')  
    DTG.write('TBAS:FREQ %f'%f)

def getTimeBase():
    return float(DTG.ask('TBAS:FREQ?'))

def setJumpTiming(mode):
    '''mode = ('SYNC', 'ASYN')'''
    DTG.write('TBAS:JTIM ' + mode)

def Run():
    if DTG5334:
        # 10.04.2012 Set the output DC voltage to 1.7 V for all channels
        # This for our DTG5334 setup 2.
        # THis is a dirty fix!
        # DTG.write('pgena:ch1:high 1.25')
        DTG.write('pgena:ch2:high 1.7')
        DTG.write('pgenb:ch1:high 1.7')
        
        DTG.write('pgena:ch2:AMPLitude 0.6')
        DTG.write('pgenb:ch1:AMPLitude 0.6')
        # DTG.write('pgenb:ch1:high 1.7')
        # DTG.write('pgenb:ch2:high 1.7')

    DTG.write('OUTP:STAT:ALL ON')
    DTG.write('TBAS:RUN ON')
    return bool(DTG.ask('TBAS:RUN?'))

def Stop():
    DTG.write('TBAS:RUN OFF')
                
old_sequence = None
old_timebase = None

def Sequence(sequence, loop=True):
    Stop()  
    global old_sequence, old_timebase  
    timebase = getTimeBase()
    #print "old=",old_sequence,"new=",sequence,'old_tb',old_timebase,"new_tb",timebase
    if not sequence is old_sequence or timebase != old_timebase: 
        sequence_ticks = []
        length = 0  
        # convert ns to clock ticks
        for step in sequence:
            i = int(round(step[1]*1e-9*timebase))
            if i > 0:
                sequence_ticks.append( (step[0],i) )
                length += i
        # adjust total length to integer multiple of 4 by expanding last step
        m = length % 4
        if m != 0:
            sequence_ticks.append( (sequence_ticks[-1][0], 4-m) )
        if length > 32000000: # according to DTG programmer manual block length is limited to 32M for DTG5274
            raise RuntimeError('block length exceeds 32 000 000 samples')  
        # create block
        WriteBlock('SEQUENCE', sequence_ticks)
    old_sequence = sequence
    old_timebase = timebase
    # set sequence length
    DTG.write('SEQ:LENG 1')
    # specify sequence
    DTG.write('SEQ:DATA 0, "",0,"SEQUENCE",0,"",""')   
    return Run()
    
def complete_sequence(blocks, sequence):
    """Writes a complete sequence, needs blocks = [('blockname1', block1), ('blockname2', block2),...], where 
    block_i = [([channels], length), ([channels], length), ...] and sequence = [line1, line2, ...], where
    line_i = ["NAME", wait4trig, "block", repetitions, "event", "goto"]
    """
    Stop()
    DTG.write('BLOC:DEL:ALL')
    for name, block in blocks:
        WriteBlock(name, block)
    DTG.write('SEQ:LENG %s' %len(sequence))
    for i, line in enumerate(sequence):
        line = 'SEQ:DATA %i, '%i  + '"%s",%i,"%s",%i,"%s","%s"' %(line[0], line[1], line[2], line[3], line[4], line[5])
        DTG.write(line)
        
def Adjust_Sequence(linenumber,label,wait4trig,block,repeat,goto_upon_trigger,goto):  
    Stop() 
    linenumber=int(linenumber)
    label=str(label)
    wait4trig=int(wait4trig)
    block=str(block)
    repeat=int(repeat)
    goto_upon_trigger=str(goto_upon_trigger)
    goto=str(goto)   
    DTG.write('SEQ:DATA %i, "%s",%i,"%s",%i,"%s","%s"'%(linenumber,label,wait4trig,block,repeat,goto_upon_trigger,goto))    
    
#Stuff for fast-write mode (creating setup file on PC and load in DTG)
def gen_block(length, id, name):
    """
    gen_block: generate a tree for a DTG block of given length, id and name
    'name' is assumed to be packed into a numpy array. 
    'length' and 'id' are integers
    """
    length_entry = numpy.array([int(length)])
    return [
                ['DTG_BLOCK_RECID',
                30,
                [
                ['DTG_ID_RECID', 2, numpy.array([id], dtype=numpy.int16)],
                ['DTG_NAME_RECID', name.nbytes, name],
                ['DTG_SIZE_RECID', length_entry.nbytes, length_entry]]]
            ]
    
def gen_pattern(blockid, pulses):
    """
    gen_pattern: generate a python tree for a pattern command to fill block 'blockid' 
    with the binary sequence 'pulses'
    """
    return [    ['DTG_PATTERN_RECID',
                1,
                [['DTG_GROUPID_RECID', 2, numpy.array([0], dtype=numpy.int16)],
                ['DTG_BLOCKID_RECID', 2, numpy.array([blockid], dtype=numpy.int16)],
                ['DTG_PATTERNDATA_RECID',
                1,
                pulses]
                ]]                    
            ]

def gen_sequence(label, subname, Nrep, goto):
    """
    gen_sequence: generate a python tree for a sequence entry of a given label, 
    name of the subsequence, number of repetitions 'Nrep' and goto label 'goto'. 
    all strings are assumed to by numpy arrays. Nrep is an int
    """
    return  [
                ['DTG_MAINSEQUENCE_RECID',
                 51,
                 [
                 ['DTG_LABEL_RECID', label.nbytes, label],
                 ['DTG_WAITTRIGGER_RECID', 2, numpy.array([0], dtype=numpy.int16)],
                 ['DTG_SUBNAME_RECID', subname.nbytes, subname],
                 ['DTG_REPEATCOUNT_RECID', 4, numpy.array([Nrep], dtype=numpy.int32)], # was 0,0
                 ['DTG_JUMPTO_RECID', 1, numpy.array([0], dtype=numpy.int8)],
                 ['DTG_GOTO_RECID', goto.nbytes, goto]]
                ],                       
             ] 
    
def ChannelsToInt(channels):
    bits = 0
    for channel in channels:
        bits |= 1 << (NumberOfChannels - 1 - ChannelMap[channel])
    return bits
    
def FastWrite(blocks, sequence=None):
    """Fast writes given blocks (and sequence) into DTG using a DTG-setup file
    Blocks must be list of Block-objects defined in Pulsepattern"""
    break_len = 1000 # length of the macrobreak
    break_entry = numpy.array([int(break_len)])
    blocks_tree = []
    patterns_tree = []
    sequence_tree = []
    for i, block in enumerate(blocks):
        blocks_tree.extend( gen_block(block.length, i+1, numpy.array(block.name + '\x00', dtype='|S')) )
        pulses = numpy.array([], dtype=numpy.int8)
        for channels, length in block.sequence:
            pulses = numpy.append(pulses, ChannelsToInt(channels)*numpy.ones((1,length), dtype=numpy.int8))
        patterns_tree.extend( gen_pattern(i+1, pulses) )
        
    binary_pattern = []
    binary_pattern.extend(blocks_tree)
    binary_pattern.extend(sequence_tree)
    binary_pattern.extend(patterns_tree)
    dtgfile = DtgIO.load_scaffold()
    view = dtgfile[-1][-1].pop()
    for node in binary_pattern:
        dtgfile[-1][-1].append(node)
    dtgfile[-1][-1].append(view)
    dtgfile = DtgIO.recalculate_space(dtgfile)[1]
    
    fil = open(pi3d.dtgfile_seq_dis, 'wb')
    DtgIO.dump_tree(dtgfile, fil)
    fil.close()
    fil = open(pi3d.dtgfile_cur_loc, 'wb')
    DtgIO.dump_tree(dtgfile, fil)
    fil.close()
    DTG.write("MMEM:LOAD \""+pi3d.dtgfile_seq_dis_loc+"\"")    
    Run()  
