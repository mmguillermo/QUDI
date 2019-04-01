"""
Macro for read data from a file

"""

import numpy as np
import time
import os

def readCData(pathfile, splitter):
    """
    Read data with a continuous array  of float
    """
    exit_code = 0
    if not os.path.isfile(pathfile):
        print("The file does not exist \n")
        exit_code = -1
        return (np.array([]), [], exit_code)
    time.sleep(0.01)

    try:
        with open(pathfile, "r") as localpulsefile:
            pulselines = localpulsefile.readlines()
        x = []
        y = []
        line = None
        for element in pulselines:
            if splitter == "":
                line = [ii for ii in str(element).strip().split()]
            else:
                line = [ii for ii in str(element).strip().split(splitter)]
            if line[0] == '---':
                continue
            else:
            	y.append(float(line[0]))
        for ii in range(len(y)):
            x.append(float(ii))
        print (str(len(line)))
        x = np.asarray(x)
        y = np.asarray(y)
        return (x, y, exit_code)
    except OSError as err:
        exit_code = 4
        return (np.array([]), [], exit_code)
    except IndexError:
        exit_code = 4
        return (np.array([]), [], exit_code)
    except (TypeError, ValueError) as ex:
        exit_code = 4
        return (np.array([]), [], exit_code)

def readFData(pathfile, splitter, y_pos):
    """
    Read data with only y-values
    """
    exit_code = 0
    if not os.path.isfile(pathfile):
        print("The file does not exist \n")
        exit_code = -1
        return (np.array([]), [], exit_code)
    time.sleep(0.01)

    try:
        with open(pathfile, "r") as localpulsefile:
            pulselines = localpulsefile.readlines()
        x = []
        y = []
        for element in pulselines:
            if splitter == "":
                line = [ii for ii in str(element).strip().split()]
            else:
                line = [ii for ii in str(element).strip().split(splitter)]
            if line[0] == '---':
                continue
            y.append(float(line[y_pos]))
        for ii in range(len(y)):
            x.append(float(ii))
        x = np.asarray(x)
        y = np.asarray(y)
        return (x, y, exit_code)
    except OSError as err:
        exit_code = 4
        return (np.array([]), [], exit_code)
    except IndexError:
        exit_code = 4
        return (np.array([]), [], exit_code)
    except (TypeError, ValueError) as ex:
        exit_code = 4
        return (np.array([]), [], exit_code)
        

def readGData(pathfile, splitter, x_pos, y_pos):
    """
    Read Data from a file with different columns
    """
    exit_code = 0
    if not os.path.isfile(pathfile):
        print("The file does not exist \n")
        exit_code = -1
        return (np.array([]), [], exit_code)
    time.sleep(0.01)
    try:
        with open(pathfile, "r") as localpulsefile:
            pulselines = localpulsefile.readlines()

        x = []
        y = []
        
        for element in pulselines:
            if splitter == "":
                line = [ii for ii in str(element).strip().split()]
            else:
                line = [ii for ii in str(element).strip().split(splitter)]
            x.append(float(line[x_pos]))
            y.append(float(line[y_pos]))
        x = np.asarray(x)
        y = np.asarray(y)
        return (x, y, exit_code)
    except OSError as err:
        exit_code = 4
        return (np.array([]), [], exit_code)
    except IndexError:
        exit_code = 4
        return (np.array([]), [], exit_code)
    except (TypeError, ValueError) as ex:
        exit_code = 4
        return (np.array([]), [], exit_code)

def readAllData(pathfile):
    exit_code = 0
    if not os.path.isfile(pathfile):
        print("The file does not exist \n")
        exit_code = -1
        return (np.array([]), [], exit_code)
    time.sleep(0.01)
    try:
        with open(pathfile, "r") as localpulsefile:
            pulselines = localpulsefile.readlines()

        It_no         = []
        fom           = []
        
        splitter = ";"
        for element in pulselines:
            line = [ii for ii in str(element).strip().split(splitter)]
            if len(line) == 6:
            	continue
            It_no.append(float(line[0]))
            fom.append(float(line[6]))
        It_no         = np.asarray(It_no)
        fom = np.asarray(fom)
        return (It_no, fom, exit_code)
    except OSError as err:
        #io.log(self.log_id, 'f', 'e', "_get_pulse_from_file : OSError, errno: " + str(err.errno) +
        #       ", while reading pulse in: " + self.local_path)
        #io.log(self.log_id, 'c', 'e', "&&& Error while reading pulse : Check permissions for folder" +
        #       str(self.local_path) + ", wait for exit")
        exit_code = 4
        return (np.array([]), [], exit_code)
    except IndexError:
        #io.log(self.log_id, 'f', 'e', "_get_pulse_from_file : IndexError while reading pulse: "
        #       + str(os.path.join(self.local_path, "pulses.txt")))
        #io.log(self.log_id, 'c', 'e', "&&& Error while reading pulse : Index out of bounds "
        #                              " (check pulses.txt file in " + str(self.local_path) +
        #       " for equal line/column lengths), wait for exit")
        exit_code = 4
        return (np.array([]), [], exit_code)
    except (TypeError, ValueError):
        #io.log(self.log_id, 'f', 'e', "_read_server_message : Type/ValueError while reading pulse file: "
        #       + str(os.path.join(self.local_path, "pulses.txt")) + ". Could not convert entry to float")
        #io.log(self.log_id, 'c', 'e', "&&& Error while reading pulse file: " +
        #       str(os.path.join(self.local_path, "pulses.txt")) + ". Could not convert entry to float, wait for exit")
        exit_code = 4
        return (np.array([]), [], exit_code)

def readData(pathfile):
    exit_code = 0
    if not os.path.isfile(pathfile):
        print("The file does not exist \n")
        exit_code = -1
        return (np.array([]), [], exit_code)
    time.sleep(0.01)
    #print("Read " + pathfile + '\n')
    try:
        with open(pathfile, "r") as localpulsefile:
            pulselines = localpulsefile.readlines()

        It_no         = []
        fom           = []

        for element in pulselines:
            line = [ii for ii in str(element).strip().split()]
            It_no.append(float(line[0]))
            fom.append(float(line[1]))
        It_no         = np.asarray(It_no)
        fom = np.asarray(fom)
        return (It_no, fom, exit_code)
        return (It_no, fom, exit_code)
    except OSError as err:
        #io.log(self.log_id, 'f', 'e', "_get_pulse_from_file : OSError, errno: " + str(err.errno) +
        #       ", while reading pulse in: " + self.local_path)
        #io.log(self.log_id, 'c', 'e', "&&& Error while reading pulse : Check permissions for folder" +
        #       str(self.local_path) + ", wait for exit")
        exit_code = 4
        return (np.array([]), [], exit_code)
    except IndexError:
        #io.log(self.log_id, 'f', 'e', "_get_pulse_from_file : IndexError while reading pulse: "
        #       + str(os.path.join(self.local_path, "pulses.txt")))
        #io.log(self.log_id, 'c', 'e', "&&& Error while reading pulse : Index out of bounds "
        #                              " (check pulses.txt file in " + str(self.local_path) +
        #       " for equal line/column lengths), wait for exit")
        exit_code = 4
        return (np.array([]), [], exit_code)
    except (TypeError, ValueError):
        #io.log(self.log_id, 'f', 'e', "_read_server_message : Type/ValueError while reading pulse file: "
        #       + str(os.path.join(self.local_path, "pulses.txt")) + ". Could not convert entry to float")
        #io.log(self.log_id, 'c', 'e', "&&& Error while reading pulse file: " +
        #       str(os.path.join(self.local_path, "pulses.txt")) + ". Could not convert entry to float, wait for exit")
        exit_code = 4
        return (np.array([]), [], exit_code)
#pathfile = "Img/Text/Set_Opti_Pulses_th_Robustness.txt"
#splitter = ""
#x_pos = 0
#y_pos = 1
#x, y, exit_code = readGData(pathfile, splitter, x_pos, y_pos)
# Filename
#pathfile = "Img/Text/jobnr3020181029-092612_115mus_best/Res_30_FomData.txt"
#splitter = ""
#y_pos = 0
# Read Data from file
#x, y, exit_code = readFData(pathfile, splitter, y_pos)
