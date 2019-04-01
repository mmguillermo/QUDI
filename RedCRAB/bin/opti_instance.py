# encoding: utf-8
"""
opti_instance.py - Class for transmission with the server
@author: Fabian Höb, Jonathan Zoller (jonathan.zoller@gmx.de)
Current version number: 1.0.4
Current version dated: 14.07.2017
First version dated: 01.04.2017
"""

import os
import sys
import time
import logging_module as io
import remote_module as rc
#MarcoR 24.04.2018
import plot_instance as pins
#import pymatinterface -> moved to constructor
import subprocess
import numpy as np
import importlib.util

### Contains the user optimization class, that handles the communication of figure of merit and
### pulses with the server

class UserOpti:
    #MarcoR 30.06.2018 Add (mainpars, algpars, mainflagged, pulsepars, pulseflagged, parapars, paraflagged)
    # parameters from Cfg_#.txt file
    def __init__(self, stopper_sentinel, server_waittime, user_waittime, do_plotting, split_pulses_file,remote_path, local_path, stats_path,
                 transmission_method, stdavail, fom_method, transfer_mode, smsg_watcher,
                 fompath_watcher, user_job_id, opti_info, server_checkinterval,
                 user_checkinterval, pulse_formatters, std_low_thresh, is_recovery, mainpars, algpars, mainflagged,
                 pulsepars, pulseflagged, parapars, paraflagged):
        """
                CONSTRUCTOR of class UserOpti: Sets-up variables for the transmission required for the optimization

                Parameters
                ----------
                stopper_sentinel : threading.Event
                    Event that is set if the user stopped the program
                server_waittime : int
                    Total time to wait until server timed out (no answer)
                user_waittime : int
                    Total time to wait until figure of merit evaluation timed out (no answer)
                remote_path : str
                    Path to the exchange folder on the server
                local_path : str
                    Path to the local exchangefolder
                stats_path : str
                    Path to the local user statistics folder
                transmission_method : int
                    Transmission method set by user (polling or existance checks)
                stdavail : int
                    Will information about standard deviation of fom be provided (then 1 else 0)
                fom_method : list
                    Figure of merit evaluation method ( python module, external command or pure
                    file exchange, matlab evaluation...)
                smsg_watcher : int
                    Last time the server message changed (important for polling)
                fompath_watcher : int
                    Last time the figure of merit file changed (if not fom eval by python mod.)
                user_job_id : str
                    User job id
                opti_info : list
                    List with optimization info (curr. SI, NM eval etc.)
                server_checkinterval : float
                    time between successive checks of the server message (existance or update)
                user_checkinterval : float
                    time between successive checks of the figure of merit file (update)
                pulse_formatters : str
                    formatters for saving the pulse file to stats or for fom evaluation (number of decimals, delimiter)
                is_recovery : bool
                    flag if the optimization is a recovery or not

                Notes
                ----------
                Also contains the exit_code parameter which handles if something went wrong at any point
                during the transmission (notified by a number)
                For errors in this module it is usually exit_code 4, which is a gneral transmission error exit code.
                Errors occurring in the remote_module are passed on (via exit_code)
        """

        # central exit code parameter (0 means nothing went wrong, 6 is normal exit by server)
        self.exit_code = 0
        # logging id that identifies this module
        self.log_id = 2
        # waittimes for occuring waiting cycles
        if server_checkinterval > 30 or server_checkinterval < 0.01:
            server_checkinterval = 2
        self.server_cycletime = server_checkinterval
        if user_checkinterval > 30 or user_checkinterval < 0.01:
            user_checkinterval = 2
        self.user_cycletime = user_checkinterval
        # current pulse
        self.curr_pulse = np.array([])

        #MarcoR 01.06.2018
        is_max = float(algpars['FomFactor2Maximization'] )
        #MarcoR 01.06.2018
        if is_max > 10 ** (- 11):
            is_max = 1
        elif is_max < - 10 ** (- 11):
            is_max = 0
        else:
            io.log(self.log_id, 'f', 'e', "UserOpti initialization: Factor 2 Maximization is too close to zero")
            io.log(self.log_id, 'c', 'e', "&&& Error: Factor 2 Maximization is too close to zero")
            para_exit_code = 1
        #MarcoR 20.06.2018 : check what is para_exit_code
        if is_max: # maximize
            self.curr_fom_record = - 9999 * 10 ** 99
        else: # minimize
            self.curr_fom_record = 9999 * 10 ** 99
        # current fom
        self.curr_fom = self.curr_fom_record
        #current filename record
        self.curr_filename_record = "t.txt"

        #MarcoR 25.04.2018, 01.06.2018
        self.is_First_Plot = True
        # Max number funct evaluation for SI > 1
        self.fund_Max_Num_EV = MaxNumFunctEv = algpars['MaxFunctEvSI22n']
        #
        # stopper instance sentinel
        self.stopper_sentinel = stopper_sentinel
        # time to wait for server answer
        if server_waittime > 18000 or server_waittime < 100:
            #do not wait longer than 30 mins
            server_waittime = 18000
        self.server_waittime = server_waittime
        # time to wait for client fom evaluation
        if user_waittime > 86400 or user_waittime < 100:
            # do not wait longer than a day
            user_waittime = 86400
        self.user_waittime = user_waittime
        # path to exchangefolder on remote host
        #MarcoR 05.06.2018
        # split pulses file in more files: 0 -> No split, 1-> Split
        self.split_pulses_file = split_pulses_file
        #MarcoR 12.12.2018
        self.do_plotting = do_plotting
        self.remote_path = remote_path
        # path to exchangefolder on local system
        self.local_path = local_path
        # path to stats foler on local system
        self.stats_path = stats_path
        # list with info on status of optimization ([current SI, NM Iteration, NM feval, total feval]
        # transfer method ( 0 = by watching changes, 1 = by checking if files exists)
        if transmission_method > 1 or transmission_method < 0:
            io.log(self.log_id, 'f', 'e', "UserOpti initialization: Unknown transmission_method")
            io.log(self.log_id, 'c', 'e', "&&& Error: Transmission method in redcrab config file needs to be 0 or 1")
            self.exit_code = 4
        self.transmission_method = transmission_method
        if stdavail>1 or stdavail<0:
            io.log(self.log_id, 'f', 'e', "UserOpti initialization: Unknown stdavail")
            io.log(self.log_id, 'c', 'e',
                   "&&& Error: StdAvailable in redcrab config file needs to be either 0 or 1")
            self.exit_code = 4
        self.stdavail = stdavail
        #MarcoR 13.06.2018
        # number of re-evaluation steps. It is used to assign fom record
        if self.stdavail == 1:
            reevalsteps = mainflagged['FLAGSPECIFYREEVALSTEPS'][1]['ReEvalSteps']
            nevalsteps = len(reevalsteps)
            self.n_eval_steps = nevalsteps
        # watcher checks for file changes (on remote host)
        self.smsg_watcher = smsg_watcher
        # temporary watchtime when having identified a new server message, but smsg_watcher should only be
        # properly updated once the pulse was successfully downloaded (important for recovery)
        self.tmp_smsg_watcher = -1
        # how fom is recieved from user ( 0 is by py module, 1 is by external compiled ressource, 2 is by pure
        # pulse and fom exchange via files
        self.fom_method = int(fom_method[0])
        if self.fom_method == 0:
            try:
                # fom_method[1] is the path to the python module and fom_method[2] is the module name
                spec = importlib.util.spec_from_file_location(fom_method[2], fom_method[1])
                pymod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(pymod)
                self.pymodname = pymod
            except FileNotFoundError as ex:
                io.log(self.log_id, 'f', 'e',
                       "UserOpti initialization: FileNotFoundError while importing module named " + str(fom_method[1]))
                io.log(self.log_id, 'c', 'e', "&&& Error importing module named " + str(fom_method[1])
                       + " check if it exists.")
                self.exit_code = 4
            except AttributeError as ex:
                io.log(self.log_id, 'f', 'e',
                       "UserOpti initialization: AttributeError importing module named " + str(fom_method[1]))
                io.log(self.log_id, 'c', 'e', "&&& Error importing module named " + str(fom_method[1])
                       + " check if it really is a python module")
                self.exit_code = 4
            except ImportError as ex:
                io.log(self.log_id, 'f', 'e',
                       "UserOpti initialization: ImportError importing module name " + str(fom_method[1]))
                io.log(self.log_id, 'c', 'e', "&&& Error importing module name " + str(fom_method[1])
                       + " check if exists and is in a proper package (folder contains a __init__py)")
                self.exit_code = 4

        elif self.fom_method == 1:
            # command for the user program to be called via commandline
            self.user_command = str(fom_method[1])
            # path to where the pulse should be written
            self.pulsepath = str(fom_method[2])
            # path to the user figure of merit
            self.fompath = os.path.join(str(fom_method[3]), "fom.txt")
            self.stdpath = os.path.join(str(fom_method[3]), "std.txt")
            # get last modified time of fom.txt path which is provided by the user if exists
            if os.path.exists(self.fompath):
                self.fompath_watcher = int(os.stat(self.fompath).st_mtime)
            else:
                self.fompath_watcher = fompath_watcher

        elif self.fom_method == 2:
            # path to where the pulse should be written
            self.pulsepath = str(fom_method[1])
            # get last modified time of fom.txt path which is provided by the user
            self.fompath = os.path.join(str(fom_method[2]), "fom.txt")
            self.stdpath = os.path.join(str(fom_method[2]), "std.txt")
            # get last modified time of fom.txt path which is provided by the user if exists
            if os.path.exists(self.fompath):
                self.fompath_watcher = int(os.stat(self.fompath).st_mtime)
            else:
                self.fompath_watcher = fompath_watcher
        elif self.fom_method == 3: #matlab engine for python
            matlab = importlib.import_module('matlab.engine')
            try:
                self.matprogpath = str(fom_method[1]) #check variable type
                # TDB: check validity of path either here or at some earlierer stage
                self.matlabrestartint = int(fom_method[2])
                self.matlablaststart = int(round(time.time() * 1000))
                #eng = matlab.engine.start_matlab()
                eng = matlab.start_matlab()
                eng.addpath(self.matprogpath)
                self.matlabengine = eng
            except Exception as ex:
                io.log(self.log_id, 'f', 'e',
                       "UserOpti initialization: Error with Matlab engine start or addpath "
                       "command which includes path to: " + str(fom_method[1]))
                io.log(self.log_id, 'c', 'e',
                       "&&& Error with Matlab engine start or addpath command: " + str(
                           fom_method[1]))
                self.exit_code = 4
        else:
            io.log(self.log_id, 'f', 'e',
                   "UserOpti initialization: Unknown fom evaluation method number")
            io.log(self.log_id, 'c', 'e', "&&& Error FOMEvaluation parameter in config needs to "
                                          "be 0, 1, 2 or 3 ")
            self.exit_code = 4

        # transfer status info 0 if currently downloading (pulse), 1 if currently uploading (fom)
        self.transfer_mode = transfer_mode
        # optimization information transmitted by server:
        # [curr_Nr of SI, curr_Nr of NM iteration, curr_NM function evaluation, total_NM function evaluations]
        self.opti_info = opti_info
        # user job id
        self.user_job_id = user_job_id
        # pulse formatters (list containing the seperator and accuracy)
        # seperator settings
        if pulse_formatters[0] == 0:
            self.pulse_sep = "  "
        elif pulse_formatters[0] == 1:
            self.pulse_sep = " , "
        elif pulse_formatters[0] == 2:
            self.pulse_sep = ",  "
        else:
            self.pulse_sep = "  "
        # pulse accuracy settings
        if pulse_formatters[1] > 10 or pulse_formatters[1] < 2:
            pulse_formatters[1] = 9
        self.pulse_format = "%." + str(pulse_formatters[1]) + "f"
        # lower threshold for standard deviation (if given at all)
        self.std_low_thresh = std_low_thresh
        # recovery flag
        self.is_recovery = is_recovery
        #MarcoR 11.05.2018
        self.is_max = is_max
        #MarcoR 30.05.2018
        self.fund_Eval_error = 0


    def opti_loop(self):
        """
                TOP LAYER METHOD that organizes the communication with the server by calling subfuntions

                Handles the loop for the file download, upload and figure of merit evaluation calls

                Parameters
                ----------

                Returns
                -------
                self.exit_code -> The exit code during when the program was quit. If the exit code is at some point != 0
                               -> The loop will be exited and exit_handling in the main program will be started
                               -> The non error exit has exit code 100!
        """
        # central loop for remote communication
        if self.exit_code == 0:
            self._write_transmission_status()
            # precheck (if this is a recovery) for server status
            if self.is_recovery:
                self._server_check()
                if self.exit_code != 0:
                    return self.exit_code
            if self.exit_code == 0:
                #MarcoR 24.04.2018, 11.05.2018
                #Number of previous pulses to visualize in the graph
                if self.do_plotting == 1:
                    Npreviousu = 10
                    plot_inst = pins.PlotGraph(self.is_max,Npreviousu, self.fund_Max_Num_EV)
                #
                while True:
                    # checking for server message and downloading pulse
                    if self.transfer_mode == 0:
                        # _smsgcheck checks if download is ready
                        io.log(self.log_id, 'f', 'i', "opti_loop : Waiting for pulse update...")
                        io.log(self.log_id, 'c', 'i', "--- Waiting for pulse update...")
                        self._smsgcheck()
                        if self.exit_code != 0:
                            break
                        else:
                            io.log(self.log_id, 'f', 'i', "opti_loop : Pulse updated")
                            io.log(self.log_id, 'c', 'i', "+++ Pulse updated")
                            io.log(self.log_id, 'f', 'i', "opti_loop : Downloading pulse...")
                            io.log(self.log_id, 'c', 'i', "--- Downloading pulse...")
                            self._get_pulse_from_server()
                            if self.exit_code != 0:
                                break
                            else:
                                # update smsg_watcher properly (delayed update for recovery)
                                self.smsg_watcher = self.tmp_smsg_watcher
                                self.transfer_mode = 1
                                self._write_transmission_status()
                                io.log(self.log_id, 'f', 'i', "opti_loop : Pulse downloaded")
                                io.log(self.log_id, 'c', 'i', "+++ Pulse downloaded")

                    # download of pulse
                    elif self.transfer_mode == 1:
                        # initial check for message (sent in between modeswitch). In transfer mode 1,
                        # this check happens automaitcally with the first call of _smsgcheck

                        io.log(self.log_id, 'f', 'i', "opti_loop : Preparing figure of merit evaluation...")
                        io.log(self.log_id, 'c', 'i', "--- Preparing figure of merit evaluation...")
                        # important step here! Rename server message for exists checks here (not at the end of
                        # the download, as this may screw recovery).
                        # The server will then later delete the file properly
                        # If the file does not exist, this call does not alter the exit code
                        # If the server tends to fail to delete the renamed ones just use another name
                        # (it does not matter if this spams the exchange folder)
                        if self.transmission_method == 1:
                            self.exit_code = rc.file_rename(self.remote_path + "/Msg_s.txt",
                                                            self.remote_path + "/Del.txt")
                            if self.exit_code != 0:
                                io.log(self.log_id, 'f', 'e',
                                       "opti_loop : Error when trying to rename Msg_s.txt - "
                                       "exit_code = " + str(self.exit_code))
                                io.log(self.log_id, 'c', 'e',
                                       "&&& Error when trying to delete Server message")
                                break

                        # get pulse from file to curr_pulse
                        (self.curr_pulse, self.curr_paras) = self._get_pulse_from_exchange()
                        if self.exit_code != 0:
                            break
                        # save pulse to user stats folder
                        self._pulse_to_stats()
                        # if some other file was transmitted with more info:
                        # self._otherstats_to stats()

                        # check if user message still exists if transmission method is 1
                        # (checking file existance). If it does, then the server did not delete it and that is bad.
                        if self.transmission_method == 1:
                            self._check_for_user_message()
                            if self.exit_code != 0:
                                break
                        io.log(self.log_id, 'f', 'i', "opti_loop : Preparations complete")
                        io.log(self.log_id, 'c', 'i', "+++ Preparations complete")
                        io.log(self.log_id, 'c', 'i', "--- Figure of merit evaluation nr. "
                               + str(self.opti_info[2]) + " for current Superiteration " + str(self.opti_info[0]))
                        io.log(self.log_id, 'f', 'i', "opti_loop : Waiting for figure of merit evaluation...")
                        io.log(self.log_id, 'c', 'i', "--- Waiting for figure of merit evaluation...")
                        # get figure of merit from user
                        if self.fom_method == 0:
                            # via python file
                            if not self.stdavail:
                                self.curr_fom = self._get_fom_from_pymod()[0] # just take first
                                # argument
                            else:
                                (self.curr_fom, self.curr_std) = self._get_fom_from_pymod()
                        elif self.fom_method == 1 or self.fom_method == 2:
                            # via direct file exchange and via Command
                            self._fomcheck()
                            if self.exit_code != 0:
                                break
                            if not self.stdavail:
                                self.curr_fom = self._get_fom_from_file()[0] # just take first arg
                            else:
                                (self.curr_fom, self.curr_std) = self._get_fom_from_file()
                        elif self.fom_method == 3:
                            # via pymatinterface.py file
                            import pymatinterface
                            #check if matlab engine needs to be restarted for floating license
                            currtime = int(round(time.time() * 1000))
                            if (currtime - self.matlablaststart) > 1000*self.matlabrestartint:
                                self.matlabengine.quit()
                                eng = matlab.engine.start_matlab()
                                eng.addpath(self.matprogpath)
                                self.matlabengine = eng
                                self.matlablaststart = currtime
                                io.log(self.log_id, 'f', 'i', "opti_loop/ fom_method 3 : matlab "
                                                              "engine restarted")
                                io.log(self.log_id, 'c', 'i', "+++ opti_loop/ fom_method 3 : "
                                                              "matlab engine restarted")
                            if not self.stdavail:
                                self.curr_fom = self._get_fom_from_pymatinterface()[0] #just 1st
                                #  argument
                            else:
                                (self.curr_fom, self.curr_std) = self._get_fom_from_pymatinterface()
                        else:
                            io.log(self.log_id, 'f', 'e', "ERROR in opti_loop: fom_method " +
                                   str(self.fom_method) + " not defined!")
                            io.log(self.log_id, 'c', 'e', "&&& ERROR in opti_loop: fom_method "
                                   + str(self.fom_method) + " not defined!")
                        #check for too small std standard deviation
                        if self.stdavail:
                            if self.curr_std < self.std_low_thresh:
                                #error message
                                io.log(self.log_id, 'f', 'e', "ERROR in opti_loop: returned "
                                    "standard deviation std = " + str(self.curr_std) +
                                       " is smaller than lower threshold on standard deviation: "
                                        + str(self.std_low_thresh))
                                io.log(self.log_id, 'c', 'e', "ERROR in opti_loop: returned "
                                    "standard deviation std = " + str(self.curr_std) +
                                       " is smaller than lower threshold on standard deviation: "
                                        + str(self.std_low_thresh))
                                #stop optimization by setting exit code other than 0 (and 6 and
                                # 100)
                                self.exit_code = 7

                        # elif
                        # handle fom echange with server
                        #
                        # MarcoR 24.04.2018, 11.05.2018
                        #MarcoR 12.12.2018
                        if self.do_plotting == 1:
                            if self.is_First_Plot:
                                plot_inst.create_figure(len(self.curr_pulse) - 1)
                                self.is_First_Plot = False
                            for ii in range(0, len(self.curr_pulse) - 1):
                                plot_inst.plot_u(self.opti_info[2],self.curr_pulse[0], self.curr_pulse[ii + 1],
                                                 self.opti_info[0],ii)
                        #
                        if self.exit_code != 0:
                            break
                        else:
                            # put fom to stats folder
                            self._fom_to_stats()
                            io.log(self.log_id, 'f', 'i', "opti_loop : Figure of merit recieved")
                            io.log(self.log_id, 'c', 'i', "+++ Figure of merit recieved")

                            #

                            # Check for server status, important for long running jobs!
                            io.log(self.log_id, 'f', 'i', "opti_loop : Checking server status")
                            io.log(self.log_id, 'c', 'i', "--- Checking server status")
                            # basically a timeout check:
                            self._server_check()
                            if self.exit_code != 0:
                                break
                            io.log(self.log_id, 'f', 'i', "opti_loop : Status checked successfully")
                            io.log(self.log_id, 'c', 'i', "+++ Status checked successfully")

                            io.log(self.log_id, 'f', 'i', "opti_loop : Sending figure of merit to server")
                            io.log(self.log_id, 'c', 'i', "--- Sending figure of merit to server")
                            self._update_exchange_fom()
                            if self.exit_code != 0:
                                break
                            else:
                                # do transfer, user message is also sent here
                                self._do_put_transfer()
                                if self.exit_code != 0:
                                    break
                                else:
                                    self.transfer_mode = 0
                                    self._write_transmission_status()
                                    io.log(self.log_id, 'f', 'i', "opti_loop : Figure of merit was sent")
                                    io.log(self.log_id, 'c', 'i', "+++ Figure of merit was sent")
                                    # update curr_f_record with associated pulses into best_folder
                                    # MarcoR 23.04.2018, 11.05.2018
                                    io.log(self.log_id, 'f', 'i',
                                           "opti_loop : Checking if figure of merit record is reached")
                                    io.log(self.log_id, 'c', 'i', "--- Checking if figure of merit record is reached")

                                    # MarcoR 14.06.2018 Check if record is reached from exchange folder
                                    # Here I can put a method something like _get_fom_reached()
                                    #
                                    self._get_fom_reached_from_server()
                                    # MarcoR 17.09.2018
                                    #if self.exit_code != 0:
                                    #    break
                                    (self.curr_fom, is_Opti_reach) = self._get_fomrecord_from_exchange()
                                    if self.exit_code != 0:
                                        continue



                                    # if self.is_max: #maximize
                                    #    if self.curr_fom > self.curr_fom_record:
                                    #        is_Opti_reach = True
                                    # else: #minimize
                                    #    if self.curr_fom < self.curr_fom_record:
                                    #        is_Opti_reach = True

                                    if is_Opti_reach:
                                        self.curr_fom_record = self.curr_fom
                                        io.log(self.log_id, 'f', 'i',
                                               "opti_loop : Fom_record reached. Update record file. ")
                                        io.log(self.log_id, 'c', 'i', "+++ Fom_record reached. Update record file.")
                                        # New Method MarcoR 23.04.2018
                                        self._records_to_stats()
                                    else:
                                        io.log(self.log_id, 'f', 'i',
                                               "opti_loop : Record not reached ")
                                        io.log(self.log_id, 'c', 'i', "+++ Record not reached.")

                                    #MarcoR&PKMR 30.10.2018
                                    #MarcoR 12.12.2018
                                    if self.do_plotting==1:
                                        if (self.curr_fom != None):
                                            plot_inst.plot_fom(self.opti_info[2], self.curr_fom, self.opti_info[0],
                                                           is_Opti_reach)

                #plot_inst.plot_show()
                return self.exit_code
            else:
                return self.exit_code
        else:
            return self.exit_code

    def _server_check(self):
        """
                Check for server status. Used for checks after (perhaps long running) figure of merit evaluations
                and if the opti_loop was called in a recovery

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3. From several called functions 4 (internal error)
                            From _read_server_message 5 (server error/timeout)
                    Aborts: From_read_server_message 5 for server side abort
                    Exit:  From_read_server_message 100 for exit
        """
        if self._exchangepath_exists():
            if self._check_server_message():
                if self.exit_code != 0:
                    return
                self._get_server_message()
                if self.exit_code != 0:
                    return
                self._read_server_message()
                if self.exit_code != 0:
                    return
                # update smsg_watcher properly after the server message was completely checked
                # only important if nothing went wrong. If the server sent abort and an error occurs
                # during exit handling, the smsg_watcer does not matter
                self.smsg_watcher = self.tmp_smsg_watcher
        else:
            # folder does not exists -> likely timeout or connection problems
            return
#MarcoR
    def _records_to_stats(self):
        """
                Writes the pulse in self.curr_pulse associated to self.curr_fom_record to the user stats folder.

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From remote_module 2 and 3 and from this function 4
                    Aborts: None
                    Exit: None
        """
        try:
            statspath = os.path.join(self.stats_path ,"Opti_Pulses")
            # Create Folder if doesn't exist
            if not os.path.exists(statspath):
                os.makedirs(statspath)
            pulsepath = os.path.join(statspath, self.curr_filename_record)
            # Remove previous record file
            if os.path.isfile(pulsepath):
                os.remove(pulsepath)
            # New filename record with adjustable number of digits in output
            self.curr_filename_record = "SI=" + str(self.opti_info[0]) + "_Feval_no=" + str(self.opti_info[2]) +\
                       "_FOM=" + str(self.pulse_format % self.curr_fom_record ) + ".txt"
            pulsepath = os.path.join(statspath, self.curr_filename_record)

            to_file = self.curr_pulse.tolist()
            DcrabParas = self.curr_paras
            with open(pulsepath,"w+") as pulse_stat_file:
                linelist = []
                for index in range(len(to_file[0])):
                    for subelement in to_file:
                        linelist.append(subelement[index])
                    if index == 0 and len(DcrabParas) != 0:
                        for para in DcrabParas:
                            linelist.append(para)
                    pulse_stat_file.write('  '.join(map(str, linelist)) + "\n") # TBD:
                    # adjustable number of digits in output
                    linelist.clear()

        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_records_to_stats : OSError, errno: " + str(err.errno) +
                   ", while saving pulse to stats")
            io.log(self.log_id, 'c', 'e', "&&& Error while saving records to stats, wait for exit")
            self.exit_code = 4
        except IndexError:
            io.log(self.log_id, 'f', 'e', "_records_to_stats : IndexError while saving pulse to stats")
            io.log(self.log_id, 'c', 'e', "&&& Error while saving records to stats, wait for exit")
            self.exit_code = 4

    def _pulse_to_stats(self):
        """
                Writes the pulse in self.curr_pulse to the user stats folder.

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From remote_module 2 and 3 and from this function 4
                    Aborts: None
                    Exit: None
        """
        try:
            statspath = os.path.join(self.stats_path ,"Pulses" , "SI_" + str(self.opti_info[0]))

            pulsepath = os.path.join(statspath, "Pulse_FOMeval_" + str(self.opti_info[2]) + ".txt")
            if not os.path.exists(statspath):
                os.makedirs(statspath)
            #pulses_ndarray = self.curr_pulse.T
            #pulses_ndarray_o   = np.append(pulses_ndarray[0],self.curr_paras)
            #pulses_ndarray_ttn = pulses_ndarray[1:]

            to_file = self.curr_pulse.tolist()

            DcrabParas = self.curr_paras
            with open(pulsepath,"w+") as pulse_stat_file:
                linelist = []
                for index in range(len(to_file[0])):
                    for subelement in to_file:
                        linelist.append(subelement[index])
                    if index == 0 and len(DcrabParas) != 0:
                        for para in DcrabParas:
                            linelist.append(para)
                    pulse_stat_file.write('  '.join(map(str, linelist)) + "\n") # TBD:
                    # adjustable number of digits in output
                    linelist.clear()

            #np.savetxt(os.path.join(statspath, pulsepath), pulses_ndarray_o,
            #           fmt=self.pulse_format, delimiter=self.pulse_sep, newline="\r\n")

        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_pulse_to_stats : OSError, errno: " + str(err.errno) +
                   ", while saving pulse to stats")
            io.log(self.log_id, 'c', 'e', "&&& Error while saving pulse to stats, wait for exit")
            self.exit_code = 4
        except IndexError:
            io.log(self.log_id, 'f', 'e', "_pulse_to_stats : IndexError while saving pulse to stats")
            io.log(self.log_id, 'c', 'e', "&&& Error while saving pulse to stats, wait for exit")
            self.exit_code = 4

    def _fom_to_stats(self):
        """
                Writes the figure of merit in curr_fom to files in user stats folder.

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From remote_module 2 and 3 and from this function 4
                    Aborts: None
                    Exit: None
        """
        if not os.path.exists(self.stats_path):
            os.makedirs(self.stats_path)
        simple_fompath = os.path.join(self.stats_path, "Res_" + self.user_job_id + "_FomData.txt")
        full_fompath = os.path.join(self.stats_path, "Res_" + self.user_job_id + "_FullData.txt")
        try:
            simple_new = False
            full_new = False
            if not os.path.exists(simple_fompath):
                open(simple_fompath, "w").close()
            if not os.path.exists(full_fompath):
                open(full_fompath, "w").close()
            if os.stat(simple_fompath).st_size == 0:
                simple_new = True
            if os.stat(full_fompath).st_size == 0:
                full_new = True
            with open(simple_fompath, "a+") as sfomdatafile:
                if simple_new:
                    sfomdatafile.write("Figure of merit results from optimization:\n")
                sfomdatafile.write(str(self.curr_fom) + "\n")
            with open(full_fompath, "a+") as ffomdatafile:
                if full_new:
                    ffomdatafile.write("Figure of merit results from optimization:\n")
                ffomdatafile.write(str(time.strftime("%Y-%m-%d %H:%M:%S")) + ", SI=" + str(self.opti_info[0]) +
                                   ", It_no=" + str(self.opti_info[1]) + ", Feval_no=" + str(self.opti_info[2]) +
                                   ", FOM=" + str(self.curr_fom) + "\n")

        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_fom_to_stats : OSError, errno: " + str(err.errno) +
                   ", while saving figure of merit to stats")
            io.log(self.log_id, 'c', 'e', "&&& Error while saving figure of merit to stats, wait for exit")
            self.exit_code = 4

    def _check_server_message(self):
        """
                Checks if server message Msg_s.txt in remote exchangefolder exists/was updated

                Parameters
                ----------

                Returns
                -------
                bool
                    True if server message exists/ was updated, else false


                Exit Code changes
                -------
                    Errors: From remote_module 2 and 3
                    Aborts: None
                    Exit: None
        """
        if self.transmission_method == 0:
            exit_code, lastchanged = rc.file_stat(self.remote_path + "/Msg_s.txt", checkflag=True)
            if exit_code == 0:
                if int(lastchanged) != self.smsg_watcher:
                    # update temporary message first, then nce the message was read update smsg_watcher properly
                    self.tmp_smsg_watcher = int(lastchanged)
                    io.log(self.log_id, 'f', 'i', "_check_server_message : New server message")
                    return True
            elif exit_code == -3:
                # file does not exist, but no other error
                return False
            else:
                # some other error
                self.exit_code = exit_code
                return False
        elif self.transmission_method == 1:
            exit_code = rc.re_exists(self.remote_path + "/Msg_s.txt", checkflag=True)
            if exit_code == 0:
                # file exists
                io.log(self.log_id, 'f', 'i', "_check_server_message : New server message")
                return True
            elif exit_code == -3:
                # file does not exist, but no other error
                return False
            else:
                # some other error
                self.exit_code = exit_code
                return False

    def _get_server_message(self):
        """
                Downloads server message Msg_s.txt from server to local exchangefolder

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From remote_module 2 and 3
                    Aborts: None
                    Exit: None
                """
        exit_code = rc.file_get(self.remote_path + "/Msg_s.txt", os.path.join(self.local_path, "Msg_s.txt"))
        if self.exit_code != 0:
            io.log(self.log_id, 'f', 'e', "_get_server_message : Error while downloading server message")
            io.log(self.log_id, 'c', 'e', "&&& Error during server communication, wait for exit")
            self.exit_code = exit_code

    def _read_server_message(self):
        """
                Reads the server message file Msg_s.txt in the LOCAL exchangefolder, changes the exit code
                accoringly. Possible entrys in the message file are: 'abort', 'timeout', 'exit', 'error', 'warning'
                corresponding to different server side events.

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From this function: 4 (internal error) 5 for server side error or timeout
                    Aborts: From this function: 5 for server side abort
                    Exit: From this function: 100 for server normal exit at finished optimization
        """

        try:
            #MarcoR 23.08.2018
            # Sleep time to prevent empty file
            time.sleep(0.01)
            with open(self.local_path + "/Msg_s.txt", "r") as smsgfile:
                messagelines = [str(x).strip() for x in smsgfile.readlines()]
        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_read_server_message : OSError, errno: " + str(err.errno) +
                   ", during server communication (Exception)")
            io.log(self.log_id, 'c', 'e', "&&& Error during server communication, wait for exit")
            self.exit_code = 4
        else:
            if len(messagelines) > 0:
                if "abort" in str(messagelines[0]):
                    io.log(self.log_id, 'f', 'w', "_read_server_message : Server sided abort")
                    io.log(self.log_id, 'c', 'w', "+++ Optimization aborted by server, wait for exit")
                    self.exit_code = 5
                    return
                elif "exit" in str(messagelines[0]):
                    try:
                        if "ok" in str(messagelines[1]):
                            io.log(self.log_id, 'f', 'i', "_read_server_message : Optimization finished without errors")
                            io.log(self.log_id, 'c', 'i', "+++ Optimization finished without errors, wait for exit")
                        else:
                            io.log(self.log_id, 'f', 'w', "_read_server_message : Optimization finished with errors")
                            io.log(self.log_id, 'c', 'w', "+++ Optimization finished with server side errors, "
                                                          "wait for exit")
                        self.exit_code = 100
                        return
                    except IndexError:
                        io.log(self.log_id, 'f', 'e', "_read_server_message : Error during server communication, "
                                                      "not enough info")
                        io.log(self.log_id, 'c', 'e', "&&& Error during server communication, wait for exit")
                        self.exit_code = 4
                        return
                elif "error" in str(messagelines[0]):
                    io.log(self.log_id, 'f', 'e', "_read_server_message : Internal server error")
                    io.log(self.log_id, 'c', 'e', "+++ Optimization aborted because of server side error during "
                                                  "optimization. Check your RedCRAB config file, wait for exit")
                    self.exit_code = 5
                    return
                elif "timeout" in str(messagelines[0]):
                    try:
                        if "idle" in str(messagelines[1]):
                            io.log(self.log_id, 'f', 'e', "_read_server_message : Timeout because of idle client")
                            io.log(self.log_id, 'c', 'e', "+++ Optimization stopped because figure of merit evaluation took"
                                                          " too long, wait for exit")
                        else:
                            io.log(self.log_id, 'f', 'e', "_read_server_message : Timeout because of exceeded"
                                                          " optimization time")
                            io.log(self.log_id, 'c', 'e', "+++ Optimization stopped because total allowed optimization time"
                                                          " exceeded, wait for exit")
                        self.exit_code = 5
                        return
                    except IndexError:
                        io.log(self.log_id, 'f', 'e', "_read_server_message : Error during server communication, "
                                                      "not enough info")
                        io.log(self.log_id, 'c', 'e', "&&& Error during server communication, wait for exit")
                # MarcoR 30.10.2018 Handling error messagge
                #elif "crossing" in str(messagelines[0]):
                #    io.log(self.log_id, 'f', 'i', "_read_server_message : Warning iteration numbers do not match")
                #    io.log(self.log_id, 'c', 'i',
                #           "+++ Warning iteration numbers do not match, resetting fom evaluation.")
                #MarcoR 30.05.2018
                else:
                    line_index = 0
                    if "warning" in str(messagelines[0]):
                        io.log(self.log_id, 'f', 'i', "_read_server_message : Warning parametric pulses outside of boundaries")
                        io.log(self.log_id, 'c', 'i', "+++ Warning : Parametric pulses outside of boundaries")
                        line_index = 1
                        self.fund_Eval_error = 1
                    # normal message
                    try:
                        curr_optipars = [int(ii) for ii in (str(messagelines[line_index]).strip()).split()]
                    except (TypeError, ValueError):
                        #MarcoR 21.08.2018
                        # Randomly an Unreadable Server Message occurs
                        io.log(self.log_id, 'f', 'e', "_read_server_message : Server message has wrong format "
                                                      "(TypeError/ValueError)")
                        io.log(self.log_id, 'c', 'e', "&&& Error: Server message unreadable. Wait for exit")
                        self.exit_code = 4
                        return

                    else:
                        if len(curr_optipars) == 4:
                            self.opti_info = curr_optipars
                            io.log(self.log_id, 'f', 'i',
                                   "_read_server_message : Superiteration: " + str(curr_optipars[0]) +
                                   ", NM iteration: " + str(curr_optipars[1]) + ", NM function evaluation: " +
                                   str(curr_optipars[2]) + ", Total function evaluations: " + str(curr_optipars[3]))
                            if self.fund_Eval_error == 1:
                                io.log(self.log_id, 'f', 'i',
                                       " in Superiteration: " + str(curr_optipars[0]) +
                                       ", NM iteration: " + str(curr_optipars[1]) + ", NM function evaluation: " +
                                       str(curr_optipars[2]) + ", Total function evaluations: " + str(curr_optipars[3]))
                                io.log(self.log_id, 'c', 'i',
                                       " in Superiteration: " + str(curr_optipars[0]) +
                                       ", NM iteration: " + str(curr_optipars[1]) + ", NM function evaluation: " +
                                       str(curr_optipars[2]) + ", Total function evaluations: " + str(curr_optipars[3]))
                            return
                        else:
                            io.log(self.log_id, 'f', 'e',
                                   "_read_server_message : Error during server communication (not enough info)")
                            io.log(self.log_id, 'c', 'e', "&&& Error during server communication, wait for exit")
                            self.exit_code = 4
                            return
            else:
                io.log(self.log_id, 'f', 'e', "_read_server_message : Error during server communication (empty file)")
                io.log(self.log_id, 'c', 'e', "&&& Error during server communication, wait for exit")
                self.exit_code = 4
                return

    def _prepare_check_fom_update(self):
        """
                Prepares for checking for user specified figure of merit file location updates (relevant for getting
                figure of merit not by external python module) by setting the self.fom_watcher to the current
                st_mtime of the user specified figure of merit file location (or ift it does not exists to -1)

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        if os.path.exists(self.fompath):
            try:
                self.fompath_watcher = int(os.stat(self.fompath).st_mtime)
            except OSError as err:
                io.log(self.log_id, 'f', 'e', "_prepare_check_fom_update : OSError, errno: " + str(err.errno) +
                       ", during fom check preparation")
                io.log(self.log_id, 'c', 'e', "&&& Error while checking figure of merit file " + str(self.fompath) +
                                              ", check access permission. Wait for exit")
                self.exit_code = 4
        else:
            self.fompath_watcher = -1

    def _check_fom_update(self):
        """
                Checks the user specified figure of merit path for updates (after transferring
                the pulse to the user
                specified path and maybe calling the user specified command).

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        if os.path.exists(self.fompath):
            try:
                fomchanged = int(os.stat(self.fompath).st_mtime)
                if self.fompath_watcher != fomchanged:
                    io.log(self.log_id, 'f', 'i', "_check_fom_update : fom updated")
                    self.fompath_watcher = fomchanged
                    return True
                else:
                    return False
            except OSError as err:
                io.log(self.log_id, 'f', 'e', "_check_fom_update : OSError, errno: " + str(err.errno) +
                       ", during fom check.")
                io.log(self.log_id, 'c', 'e', "&&& Error while checking figure of merit file " + str(self.fompath) +
                                              ", check access permission. Wait for exit")
                self.exit_code = 4
                return False
        else:
            return False

    def _get_pulse_from_exchange(self):
        """
                Reads in the pulses.txt file from the local exchange folder.

                Parameters
                ----------

                Returns
                -------
                pulse : numpy array
                    contains numpy arrays with the time grid (first array) and the pulses (the following ones)


                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        #MarcoR 01.03.2018
        # check if local exchangepath still exists
        if not self._local_exchangepath_exists():
            return (np.array([]), [])
        # check if job was aborted by user
        if self._checkstop():
            return (np.array([]), [])
        try:
            linepulse = []
            with open(os.path.join(self.local_path, "pulses.txt"), "r") as localpulsefile:
                pulselines = localpulsefile.readlines()
            line1 = [float(ii) for ii in str(pulselines[0]).strip().split()]
            line2 = [float(ii) for ii in str(pulselines[1]).strip().split()]
            Nu = len(line2) - 1
            Np = len(line1) - len(line2)

            z=0
            for element in pulselines:
                z += 1
                #PH 17.09.2018
                if z == 1:
                    paras = []
                    line1_float = [float(ii) for ii in str(element).strip().split()]
                    linepulse.append(line1_float[0:(Nu+1)])
                    if Np > 0:
                        paras = line1_float[(Nu+1):]
                else:
                    linepulse.append([float(ii) for ii in str(element).strip().split()])
            # converts pulse in lineformat to pulses and time grid in seperate lists (by transposing the np array)
            pulse = np.array([np.array(ii) for ii in linepulse]).T
            return (pulse, paras)
        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_get_pulse_from_file : OSError, errno: " + str(err.errno) +
                   ", while reading pulse in: " + self.local_path)
            io.log(self.log_id, 'c', 'e', "&&& Error while reading pulse : Check permissions for folder" +
                   str(self.local_path) + ", wait for exit")
            self.exit_code = 4
            return (np.array([]), [])
        except IndexError:
            io.log(self.log_id, 'f', 'e', "_get_pulse_from_file : IndexError while reading pulse: "
                   + str(os.path.join(self.local_path, "pulses.txt")))
            io.log(self.log_id, 'c', 'e', "&&& Error while reading pulse : Index out of bounds "
                                          " (check pulses.txt file in " + str(self.local_path) +
                                          " for equal line/column lengths), wait for exit")
            self.exit_code = 4
            return (np.array([]), [])
        except (TypeError, ValueError):
            io.log(self.log_id, 'f', 'e', "_read_server_message : Type/ValueError while reading pulse file: "
                   + str(os.path.join(self.local_path, "pulses.txt")) + ". Could not convert entry to float")
            io.log(self.log_id, 'c', 'e', "&&& Error while reading pulse file: " +
                  str(os.path.join(self.local_path, "pulses.txt")) + ". Could not convert entry to float, wait for exit")
            self.exit_code = 4
            return (np.array([]), [])

    def _put_pulse_to_user_path(self):
        """
                Writes the the self.curr_pulse to the filepath specified by the user for the figure of merit evaluation

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        try:
            to_file = self.curr_pulse.tolist()
            DcrabParas = self.curr_paras
            #MarcoR 05.06.2018
            if self.split_pulses_file == 1:
                pulsen = len(self.curr_pulse) -1
                TT = self.curr_pulse[0]
                for pindex in range (0, pulsen):
                    with open(self.pulsepath + "_" + str(pindex+1) +".txt", "w+") as pulse_path_file:
                        pulsep = self.curr_pulse[pindex+1]
                        for ii in range (0, len(pulsep)) :
                            pulse_path_file.write(str(TT[ii]) + " " + str(pulsep[ii]) + '\n')
                #PH 17.09.2018
                if len(DcrabParas) != 0:
                    with open(self.pulsepath + "_para.txt", "w+") as para_path_file:
                        for ii in range(0, len(DcrabParas)):
                            para_path_file.write(str(DcrabParas[ii]) + '\n')
                return

            with open(self.pulsepath, "w+") as pulse_path_file:
                linelist = []
                for index in range(len(to_file[0])):
                    for subelement in to_file:
                        linelist.append(subelement[index])
                    if index == 0 and len(DcrabParas) != 0:
                        for para in DcrabParas:
                            linelist.append(para)
                    pulse_path_file.write('  '.join(map(str, linelist)) + "\n")  # TBD:
                    # adjustable number of digits in output
                    linelist.clear()
            #np.savetxt(self.pulsepath, self.curr_pulse.T, fmt=self.pulse_format,
            #           delimiter=self.pulse_sep, newline="\r\n")
        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_put_pulses : OSError, errno: " + str(err.errno) +
                   ", while writing pulse to: " + str(self.pulsepath))
            io.log(self.log_id, 'c', 'e', "&&& Error while writing pulse to: " + str(self.pulsepath) +
                   ". Check permissions and if it is really a file, wait for exit")
            self.exit_code = 4

    def _run_user_command(self):
        """
                Runs the user command (for fom method 1) that was specified by the user for the
                figure of merit evaluation.

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        try:
            subprocess.call([self.user_command], shell=True)
        except subprocess.CalledProcessError:
            io.log(self.log_id, 'f', 'e', "_run_user_command : CalledProcessError while executing command: " +
                                          str(self.user_command))
            io.log(self.log_id, 'c', 'e', "&&& Error while executing command: " + str(self.user_command) +
                   ", wait for exit")
            self.exit_code = 4
        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_run_user_command : OSError, errno: " + str(err.errno) +
                   ", while executing command: " + str(self.user_command) + ". Wrong command")

            io.log(self.log_id, 'c', 'e', "&&& Error while executing command: " + str(self.user_command) +
                   ", wait for exit")
            self.exit_code = 4
        except RuntimeError:
            io.log(self.log_id, 'f', 'e', "_run_user_command : RuntimeError while executing command: " +
                   str(self.user_command))
            io.log(self.log_id, 'c', 'e', "&&& Error while executing command: " + str(self.user_command) +
                   ", wait for exit")
            self.exit_code = 4

    def _get_fom_from_file(self):
        """
                Reads the file in the user specified path, that contains the figure of merit
                after evaluation
                by the user (for transmission method 1 and 2)

                Parameters
                ----------

                Returns
                -------
                fom : float
                    figure of merit read from the file

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        if os.path.exists(self.fompath): #actually self.fompath is path + filename
            fom = None
            try:
                with open(self.fompath, "r") as fomfile:
                    #MarcoR 08.06.2018
                    fom = float(str(fomfile.readline()).strip())
                if self.stdavail:
                    with open(self.stdpath, "r") as stdfile:
                        std = float(str(stdfile.readline()).strip())
                    return (fom, std)
                else: #only fom
                    return (fom, 0.0)
            except OSError as err:
                io.log(self.log_id, 'f', 'e', "_read_server_message : OSError, errno: " + str(err.errno) +
                       ", while reading figure of merit file: " + str(self.fompath))
                io.log(self.log_id, 'c', 'e', "&&& Error while reading figure of merit file: " + str(self.fompath) +
                       ". Check permissions and if it is really a file, wait for exit")
                self.exit_code = 4
                return (0.0, 0.0)
            except (TypeError, ValueError):
                io.log(self.log_id, 'f', 'e', "_read_server_message : Type/ValueError while reading figure of merit file: "
                       + str(self.fompath) + ". Fom = " + str(fom) + "Could not convert to float")
                io.log(self.log_id, 'c', 'e', "&&& Error while reading figure of merit file: " + str(self.fompath) +
                       ". Could not convert to float. Retry another time.")
                time.sleep(0.01)
                #MarcoR 15.06.2018

                # Try to re-read self.fompath file in a different way
                try:
                    with open(self.fompath, "r") as fomfile:
                        # MarcoR 08.06.2018
                        lfom = fomfile.readline().strip().split()
                        fom = float(lfom[0])
                    if self.stdavail:
                        with open(self.stdpath, "r") as stdfile:
                            lstd = stdfile.readline().strip().split()
                            std = float(lstd[0])
                        return (fom, std)
                    else:  # only fom
                        return (fom, 0.0)
                except (TypeError, ValueError):
                    io.log(self.log_id, 'f', 'e',
                           "_read_server_message : Type/ValueError while reading figure of merit file: "
                           + str(self.fompath) + ". Fom = " + str(fom) + "Could not convert to float")
                    io.log(self.log_id, 'c', 'e', "&&& Error while reading figure of merit file: " + str(self.fompath) +
                           ". Could not convert to float, wait for exit")
                    self.exit_code = 4
                    return (0.0, 0.0)
        else:
            self.exit_code = 4
            return (0.0, 0.0)

    def _update_exchange_fom(self):
        """
                Updates the fom.txt in the local exchangepath with self.curr_fom

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        # check if local exchangepath still exists
        if not self._local_exchangepath_exists():
            return
        # check if job was aborted by user
        if self._checkstop():
            return
        try:
            with open(os.path.join(self.local_path, "fom.txt"), "w") as exchangefomfile:
                exchangefomfile.write(str(self.curr_fom))
            #eventually also write std to file
            if self.stdavail:
                with open(os.path.join(self.local_path, "std.txt"), "w") as exchangestdfile:
                    exchangestdfile.write(str(self.curr_std))
        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_update_exchange_fom : OSError, errno: " + str(err.errno) +
                   ", while writing to fom.txt file " + str(os.path.join(self.local_path, "fom.txt")))
            io.log(self.log_id, 'c', 'e', "&&& Error while writing to figure of merit file: " +
                   str(os.path.join(self.local_path, "fom.txt")))
            self.exit_code = 4
     #MarcoR 30.10.2018 Remove fom.txt file when crossing error occurs
    """
        def _remove_exchange_fom(self):
        
                Remove fom.txt file when crossing error occurs

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        
        # check if local exchangepath still exists
        if not self._local_exchangepath_exists():
            return
        # check if job was aborted by user
        if self._checkstop():
            return
        try:
            os.remove(os.path.join(self.local_path, "fom.txt") )
            #eventually also remove std.txt file
            if self.stdavail:
                os.remove(os.path.join(self.local_path, "std.txt"), "w")
        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_remove_exchange_fom : the file" + str(os.path.join(self.local_path, "fom.txt")) +
                                            " does not exist anymore.")
            io.log(self.log_id, 'c', 'e', "&&& Error while deleting the figure of merit file: " +
                   str(os.path.join(self.local_path, "fom.txt")))
            self.exit_code = 4
    """


    def _get_fom_from_pymod(self):
        """
                Retrieves figure of merit from user specified python module that contains a
                fnct(RedCRAB_pulses, timegrid) function, that returns the figure of merit (and,
                if available, the standard deviation)

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """

        if self._checkstop():
            return
        try:
            # fill dcrab pulses and timegrid arrays
            time_grid = self.curr_pulse[0]
            dcrab_pulses = []
            dcrab_paras  = self.curr_paras
            for ii in range(len(self.curr_pulse)-1):
                dcrab_pulses.append(self.curr_pulse[ii+1])

        except IndexError:
            io.log(self.log_id, 'f', 'e', "_get_fom_from_pymod : IndexError while processing pulse")
            io.log(self.log_id, 'c', 'e', "&&& Error while processing pulses : Index out of bounds "
                                          " (check pulses.txt file in " + str(self.local_path) +
                                          " for equal line lengths), wait for exit")
            self.exit_code = 4
            return 0.0, 0.0
        except (TypeError, ValueError):
            io.log(self.log_id, 'f', 'e', "_get_fom_from_pymod : Type/ValueError while processing pulse file: "
                   + str(os.path.join(self.local_path , "pulses.txt")) + ". Could not convert entry to float")
            io.log(self.log_id, 'c', 'e', "&&& Error while processing pulse file: " +
                   str(os.path.join(self.local_path, "pulses.txt")) + ". Could not convert entry to float, wait for exit")
            self.exit_code = 4
            return 0.0, 0.0
        else:
            try:
                #MarcoR 02.03.2018
                if not self.stdavail:
                    fom = self.pymodname.fnct(dcrab_pulses, dcrab_paras, time_grid) #  fnct should be used as standard name
                    #fom = self.pymodname.fnct(dcrab_pulses, time_grid)
                    return (fom, 0.0)
                else:
                    fom, std = self.pymodname.fnct(dcrab_pulses, dcrab_paras, time_grid)
                    #fom,std = self.pymodname.fnct(dcrab_pulses, time_grid)
                    return (fom, std)
            except (OSError, ValueError, RuntimeError, TypeError, NameError):
                io.log(self.log_id, 'f', 'e', " _get_fom_from_pymod : Unhandled exception while calling external "
                                              "python function: " + str(self.pymodname))
                io.log(self.log_id, 'c', 'e', "&&& Error: An unhandled exception occured while calling the python script that "
                                              "evaluates the figure of merit, wait for exit")
                self.exit_code = 4
                return 0.0, 0.0
            except AttributeError as ex:
                io.log(self.log_id, 'f', 'e', " _get_fom_from_pymod : External python module: " + str(self.pymodname) +
                       " has no function fnct(dcrab_pulses, dcrab_paras, time_grid)")
                io.log(self.log_id, 'c', 'e',
                       "&&& Error: An exception occured while calling the python script that "
                       "evaluates the figure of merit, wait for exit. Check, that the module has a function called fnct"
                       "that takes the RedCRAB pulses and the time grid as arguments.")
                self.exit_code = 4

    def _get_fom_from_pymatinterface(self):
        """
                Retrieves figure of merit from module 'pymatinterface.py'

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """

        if self._checkstop():
            return
        try:
            # fill dcrab pulses and timegrid arrays
            time_grid = self.curr_pulse[0]
            dcrab_pulses = []
            for ii in range(len(self.curr_pulse)-1):
                dcrab_pulses.append(self.curr_pulse[ii+1])
            dcrab_paras = self.curr_paras
        except IndexError:
            io.log(self.log_id, 'f', 'e', "_get_fom_from_pymatinterface : IndexError while processing pulse")
            io.log(self.log_id, 'c', 'e', "&&& Error while processing pulses : Index out of bounds "
                                          " (check pulses.txt file in " + str(self.local_path) +
                                          " for equal line lengths), wait for exit")
            self.exit_code = 4
            return 0.0, 0.0
        except (TypeError, ValueError):
            io.log(self.log_id, 'f', 'e', "_get_fom_from_pymatinterface : Type/ValueError while processing pulse file: "
                   + str(os.path.join(self.local_path , "pulses.txt")) + ". Could not convert entry to float")
            io.log(self.log_id, 'c', 'e', "&&& Error while processing pulse file: " +
                   str(os.path.join(self.local_path, "pulses.txt")) + ". Could not convert entry to float, wait for exit")
            self.exit_code = 4
            return 0.0, 0.0
        else:
            try:
                import pymatinterface
                (fom, std) = pymatinterface.fnct(dcrab_pulses, dcrab_paras, time_grid, self.matlabengine)
                return fom, std
            except (OSError, ValueError, RuntimeError, TypeError, NameError):
                io.log(self.log_id, 'f', 'e', " _get_fom_from_pymatinterface : Unhandled exception while calling external "
                                              "python function")
                io.log(self.log_id, 'c', 'e', "&&& Error: An unhandled exception occured while calling the python script that "
                                              "evaluates the figure of merit, wait for exit")
                self.exit_code = 4
                return 0.0, 0.0
            except AttributeError as ex:
                io.log(self.log_id, 'f', 'e', " _get_fom_from_pymatinterface : External matlab module "
                                              "has no function fnct(dcrab_pulses, time_grid)")
                io.log(self.log_id, 'c', 'e',
                       "&&& Error: An exception occured while calling the python script that "
                       "evaluates the figure of merit, wait for exit. Check, that the module has a function called fnct"
                       "that takes the RedCRAB pulses and the time grid as arguments.")
                self.exit_code = 4


    def _check_for_user_message(self):
        """
                Check that is important for self.transmission_method = 1(exist checks). Checks if server properly
                deleted the Msg_u.txt file in the remote exchangefolder.

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3. From this function: 4
                    Aborts: None
                    Exit: None
        """

        if self._checkstop():
            return
        # check if user message was properly deleted by server (for transmission method 1)
        #MarcoR 15.06.2018
        # Error during transmission: Sometimes Server is not rapid enough to delete Msg_u.txt
        #MarcoR 17.11.2018 move count outside While loop 
        count = 0
        while (True):
            exit_code = rc.re_exists(self.remote_path + "/Msg_u.txt", checkflag=True)
            if exit_code == -3 or count>50: break
            else:
                time.sleep(0.01)
                io.log(self.log_id, 'f', 'e', "_check_for_user_message : Error: User message still exists, "
                                              "when it should not. Count = " + str(count +1))
                count += 1

        if exit_code == 0:
            io.log(self.log_id, 'f', 'e', "_check_for_user_message : Error: User message still exists, "
                                          "when it should not")
            io.log(self.log_id, 'c', 'e', "&&& Error during transmission, wait for exit")
            exit_code = rc.file_remove(self.remote_path + "/Msg_u.txt")
            if exit_code != 0:
                self.exit_code = exit_code
                return
            self.exit_code = 4
            return
        elif exit_code == -3:
            # does not exist: Everything okay in this case
            self.exit_code = 0
            return
        else:
            self.exit_code = exit_code
            return

    def _update_user_message(self):
        """
                Updates user message on the remote exchange folder (signaling, that the figure of merit was evaluated
                and sent to the server)

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3
                    Aborts: None
                    Exit: None
        """
        # check if local exchangepath still exists
        if not self._local_exchangepath_exists():
            return
        # check if job was aborted by user
        if self._checkstop():
            return
        # if need be, change message slightly first
        if not os.path.exists(os.path.join(self.local_path, "Msg_u.txt")):
            # create the message file if it does not exist (locally)
            open(os.path.join(self.local_path, "Msg_u.txt"), "w").close()
            io.log(self.log_id, 'f', 'i', "_update_user_message : Had to create Msg_u.txt on "
                                          "client side")
            io.log(self.log_id, 'c', 'i', "_update_user_message : Msg_u.txt was missing")
        exit_code = rc.file_put(os.path.join(self.local_path, "Msg_u.txt"), self.remote_path + "/Msg_u.txt")
        if exit_code != 0:
            io.log(self.log_id, 'f', 'e', "_update_user_message : Error while transferring user message " +
                   os.path.join(self.local_path, "Msg_u.txt") + " from client to server.")
            io.log(self.log_id, 'c', 'e', "&&& Error while transferring user message")
            self.exit_code = exit_code


    def _get_pulse_from_server(self):
        """
                Downloads pulses.txt file from the server to the local exchangepath, that contains time grid and pulses

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3
                    Aborts: None
                    Exit: None
        """
        # can also be used to transfer another file with more info (e.g. info on exact parameters of the pulse etc.)
        # check if local exchangepath still exists
        if not self._local_exchangepath_exists():
            return
        # check if job was aborted by user
        if self._checkstop():
            return
        exit_code = rc.file_get(self.remote_path + "/pulses.txt", os.path.join(self.local_path, "pulses.txt"))
        if exit_code != 0:
            io.log(self.log_id, 'f', 'e', "_get_pulse_from_server : Error while transmitting pulse file " +
                   self.remote_path + "/pulses.txt from server to client.")
            io.log(self.log_id, 'c', 'e', "&&& Error while acquiring pulse from server")
            self.exit_code = exit_code

        # for retrieving another file otherfile.txt from exchange folder
        #if self.exit_code != 0:
        #    return
        #else:
        #    self.exit_code = rc.file_get(self.remote_path + "otherfile.txt",
        #                                 os.path.join(self.local_path, "otherfile.txt"))
        return

    def _put_fom_to_server(self):
        """
                Uploads fom.txt from the local to the remote exchangefolder

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3. From this function: 4
                    Aborts: None
                    Exit: None
        """
        # check if remote exchangepath still exists
        if not self._exchangepath_exists():
            return
        # check if local exchangepath still exists
        if not self._local_exchangepath_exists():
            return
        # check if job was aborted by user
        if self._checkstop():
            return
        if os.path.exists(os.path.join(self.local_path, "fom.txt")):
            #MarcoR 17.09.2018 Add to the fig of merit the #_eval
            with open(os.path.join(self.local_path, "fom.txt"),"a") as fomfile:
                fomfile.write(" " + str(self.opti_info[3]))
                time.sleep(0.01)
            exit_code = rc.file_put(os.path.join(self.local_path, "fom.txt"), self.remote_path + "/fom.txt")
            if exit_code != 0:
                io.log(self.log_id, 'f', 'e', "_put_fom_to_server : Error while putting " +
                       os.path.join(self.local_path, "fom.txt") + " to server")
                io.log(self.log_id, 'c', 'e', "&&& Error while transmitting figure of merit to server.")
                #MarcoR 17.09.2018 Manage a exit_code, probably self.exit_code = 4
            #same possibly for std
            if self.stdavail:
                exit_code = rc.file_put(os.path.join(self.local_path, "std.txt"),
                                        self.remote_path + "/std.txt")
                if exit_code != 0:
                    io.log(self.log_id, 'f', 'e', "_put_fom_to_server : Error while putting " +
                           os.path.join(self.local_path, "std.txt") + " to server")
                    io.log(self.log_id, 'c', 'e',
                           "&&& Error while transmitting standard deviation to server.")
                    #MarcoR 17.09.2018 Manage a exit_code, probably self.exit_code = 4
        else:
            io.log(self.log_id, 'f', 'e', "_put_fom_to_server : Error: fom.txt file does not exist")
            io.log(self.log_id, 'c', 'e', "&&& Error: Figure of merit file " + str(os.path.exists(self.local_path, "fom.txt")) +
                                          " does not exist, wait for exit")
            self.exit_code = 4
            return

    def _smsgcheck(self):
        """
                Loop routine, that handles checking and downloading the server message Msg_s.txt from the remote
                exchangefolder.

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3. From several called functions 4 (internal error)
                            From _read_server_message 5 (server error/timeout)
                    Aborts: From this function: 6 (timeout). From_read_server_message 5 for server side abort
                    Exit: From_read_server_message 100 for exit
        """
        server_timeout_counter = 0
        while True:
            # check if remote exchangepath still exists
            if not self._exchangepath_exists():
                break
            # check if local exchangepath still exists
            if not self._local_exchangepath_exists():
                break
            # check if job was aborted by user
            if self._checkstop():
                break
            if self._check_server_message():
                if self.exit_code != 0:
                    break
                self._get_server_message()
                if self.exit_code != 0:
                    break
                self._read_server_message()
                #MarcoR 30.05.2018
                if self.fund_Eval_error == 0: # Pulses evaluation error does not occur. So it's all ok
                    break

                #break
            time.sleep(self.server_cycletime)
            #MarcoR 30.05.2018
            if self.fund_Eval_error == 1:
                self.fund_Eval_error = 0
                rc._file_rename(self.remote_path + "/Msg_s.txt", self.remote_path + "/Del.txt")
            server_timeout_counter += self.server_cycletime
            # check timeout for server answer
            if server_timeout_counter > self.server_waittime:
                self.exit_code = 6
                break


    def _fomcheck(self):
        """
                Loop routine, that handles checking the user specicfied figure of merit file path
                for updates from the user

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3. From several called funations 4 (internal error)
                    Aborts: From this function: 6 (timeout)
                    Exit: None
        """
        user_timeout_counter = 0
        # check if job was aborted by user
        if self._checkstop():
            return
        self._prepare_check_fom_update()
        if self.exit_code != 0:
            return
        # wait a little to ensure update of os.stat()._st_mtime for fast running jobs
        time.sleep(1.1)
        # put pulse to user specified path
        self._put_pulse_to_user_path()
        if self.exit_code != 0:
            return
        if self.fom_method == 1:
            # if fom evaluation by external command: execute command here
            self._run_user_command()
            if self.exit_code != 0:
                return
        while True:
            # check if job was aborted by user
            if self._checkstop():
                break
            if self._check_fom_update():
                break
            time.sleep(self.user_cycletime)
            user_timeout_counter += self.user_cycletime
            # check timeout for user answer
            if user_timeout_counter > self.server_waittime:
                self.exit_code = 6

                break


    def _do_put_transfer(self):
        """
                Puts fom.txt and Msg_u.txt to server (calls the respective methods)

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3. From sseveral called functions: 4 (internal error)
                    Aborts: None
                    Exit: None
        """
        self._put_fom_to_server()
        if self.exit_code != 0:
            return
        else:
            if self.transmission_method == 0:
                # wait a little to ensure change in st_mtime
                time.sleep(1.1)
            self._update_user_message()
            return


    def _exchangepath_exists(self):
        """
                Checks if the remote exchangepath still exists

                Parameters
                ----------

                Returns
                -------
                bool
                    True if the folder still exists, False if it does not

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3.
                    Aborts: None
                    Exit: None
        """

        ### try for three times: (on cluster) tbd: set configureable switch
        for ii in range(0,3):
            exit_code = rc.re_exists(self.remote_path, checkflag=True)
            if exit_code == 0:
                return True
            else:
                time.sleep(0.5)


        if exit_code == 0:
            return True
        else:
            if exit_code == -3:
                io.log(self.log_id, 'f', 'e', "_remote_exchangepath_exists : Error: Remote exchange folder deleted"
                                              "Job probably exceeded idle or global timelimit.")
                io.log(self.log_id, 'c', 'e', "&&& Error: Remote exchange folder deleted. Check if your job exceeded "
                                              "a timelimit (for figure of merit evaluation or total runtime) "
                                              "Wait for exit")
            else:
                # connection related
                io.log(self.log_id, 'f', 'e', "_remote_exchangepath_exists : Error: Cannot access remote exchange folder")
                io.log(self.log_id, 'c', 'e', "&&& Error: Cannot access remote exchange folder, wait for exit")
            # absolute value as re_exists usually returns -3 if file does not exists
            self.exit_code = abs(exit_code)
            return False

    def _local_exchangepath_exists(self):
        """
                Checks if the local exchangepath still exists

                Parameters
                ----------

                Returns
                -------
                bool
                    True if the folder still exists, False if it does not

                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        if not os.path.exists(self.local_path):
            io.log(self.log_id, 'f', 'e', "_local_exchangepath_exists : Error: Local exchange folder does not exist!")
            io.log(self.log_id, 'c', 'e', "&&& Error: Local exchange folder does not exist anymore!(Will be recreated "
                                          "temporarily for smooth exit). Wait for exit")
            os.makedirs(self.local_path)
            self.exit_code = 4
            return False
        else:
            return True

    def _checkstop(self):
        """
                Checks if stopper event is set (user aborted job)

                Parameters
                ----------

                Returns
                -------


                Exit Code changes
                -------
                    Errors: None
                    Aborts: From this function: 1
                    Exit: None
        """
        if self.stopper_sentinel.isSet():
            io.log(self.log_id, 'f', 'w', "_checkstop : Stopping Optimization because of user abort...")
            io.log(self.log_id, 'c', 'w', "--- Stopping optimization because of user abort, wait for exit")
            self.exit_code = 1
            return True
        else:
            return False

    def _write_transmission_status(self):
        """
                Writes transmission status (0 for download, 1 for upload) and if upload, the  also save the
                self.opti_info parameters

                Parameters
                ----------

                Returns
                -------


                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        try:
            if os.path.exists(os.path.join(os.getcwd(), "tmp")):
                # backcheck on existance for multilaunch
                with open(os.path.join(os.getcwd(), "tmp", "transmission_status.txt"), "w") as statusfile:
                    statusfile.write(str(self.transfer_mode) + "\n")
                    if self.transfer_mode == 1:
                        infoline ='  '.join(map(str,self.opti_info))
                        statusfile.write(infoline + "\n")
                        statusfile.write(str(self.smsg_watcher))
                    else:
                        # transfer mode == 1, need to save watcher time
                        statusfile.write(str(self.smsg_watcher))
            else:
                pass
        except OSError as err:
            # only log this to file, this will screw recovery but nothing beyond that
            io.log(self.log_id, 'f', 'e', "_write_transmission_status : OSError, errno: " + str(err.errno) +
                   ", while writing to transmission status file")
    #MarcoR 14.06.2018
    # Get Yes/No respectively if fom record is reached or not and the value of it
    def _get_fomrecord_from_exchange(self):
        """
                Reads in the fom_record.txt file from the local exchange folder.

                Parameters
                ----------

                Returns
                -------
                pulse : numpy array
                    contains numpy arrays with the time grid (first array) and the pulses (the following ones)


                Exit Code changes
                -------
                    Errors: From this function: 4
                    Aborts: None
                    Exit: None
        """
        #MarcoR 1.03.2018
        # check if local exchangepath still exists
        if not self._local_exchangepath_exists():
            return (None, False)
        # check if job was aborted by user
        if self._checkstop():
            return (None, False)
        #res_fom = None
        try:
            with open(os.path.join(self.local_path, "fom_record.txt"), "r") as localfrecordfile:
                #res_fom = localfrecordfile.readline().split()
                (is_reached, fom) = localfrecordfile.readline().split()
            if is_reached == 'yes':
                is_reached = True
            elif is_reached == 'no':
                is_reached = False
            #MarcoR 18.09.2018
            # Handle by Client the error about two different evaluation numbers

            #elif is_reached =='error':
            #    io.log(self.log_id, 'f', 'w', "_get_fomrecord_from_exchange : "
                                              #"Figures of merit does not correspond to "
                                              #" the current evaluated pulse, cause an error in the communication, "
                #                             "Resetting the fom evaluation")
                # io.log(self.log_id, 'c', 'w',
                #        "&&& Warning while reading fom_record : "
                #        #"Figures of merit does not correspond to "
                #        #                       " the current evaluated pulse, cause an error in the communication."
                #        "Resetting the fom evaluation")
                # #self.exit_code = 4
                # return (None, False)
            else:
                io.log(self.log_id, 'f', 'e', "_get_fomrecord_from_exchange : Error in the keyword is_reached = " +
                       str(is_reached) + " is not recognized")
                io.log(self.log_id, 'c', 'e', "&&& Error while reading fom_record : Error in the keyword is_reached = " +
                       str(is_reached) + " is not recognized" + ", wait for exit")
                self.exit_code = 4
                return (None, False)
            return (float(fom), is_reached)
        except OSError as err:
            io.log(self.log_id, 'f', 'e', "_get_fomrecord_from_exchange : OSError, errno: " + str(err.errno) +
                   ", while reading fom_record in: " + self.local_path)
            io.log(self.log_id, 'c', 'e', "&&& Error while reading fom_record : Check permissions for folder" +
                   str(self.local_path) + ", wait for exit")
            self.exit_code = 4
            return (None, False)
        except IndexError:
            io.log(self.log_id, 'f', 'e', "_get_fomrecord_from_exchange : IndexError while reading pulse: "
                   + str(os.path.join(self.local_path, "fom_record.txt")))
            io.log(self.log_id, 'c', 'e', "&&& Error while reading fom_record : Index out of bounds "
                                          " (check fom_record.txt file in " + str(self.local_path) +
                                          " for equal line/column lengths), wait for exit")
            self.exit_code = 4
            return (None, False)
        except (TypeError, ValueError):
            #try:
            #    fom = res_fom[1]
            #    is_reached = res_fom[0]
            #    return (float(fom), is_reached)
            #except (TypeError, ValueError):
            io.log(self.log_id, 'f', 'e', "_get_fomrecord_from_exchange : Type/ValueError while reading fom_record file: "
                   + str(os.path.join(self.local_path, "fom_record.txt")) + ". Could not convert entry to float")
            io.log(self.log_id, 'c', 'e', "&&& Error while reading fom_record file: " +
                  str(os.path.join(self.local_path, "fom_record.txt")) + ". Could not convert entry to float, wait for exit")
            self.exit_code = 4
            return (None, False)
        except Exception as ex:
            print(ex.args)
            return (None, False)
    #MarcoR 14.06.2018
    def _get_fom_reached_from_server(self):
        """
                Downloads fom_record.txt file from the server to the local exchangepath, that contains time yes/no and fom value

                Parameters
                ----------

                Returns
                -------

                Exit Code changes
                -------
                    Errors: From the remote_module 2 and 3
                    Aborts: None
                    Exit: None
        """
        # can also be used to transfer another file with more info (e.g. info on exact parameters of the pulse etc.)
        # check if local exchangepath still exists
        if not self._local_exchangepath_exists():
            return
        # check if job was aborted by user
        if self._checkstop():
            return
        # wait for fom_record.txt from Server
        user_sleep = 0
        while (True):
            exit_code = rc._re_exists(self.remote_path + "/fom_record.txt")
            if exit_code == 0 or user_sleep == 12: # wait atmost 2 seconds, whereupon break with error
                break
            time.sleep(0.1)
            user_sleep += 1

        exit_code = rc.file_get(self.remote_path + "/fom_record.txt", os.path.join(self.local_path, "fom_record.txt"))
        if exit_code != 0:
            io.log(self.log_id, 'f', 'e', "_get_fom_reached_from_server : Error while transmitting fom_record file " +
                   self.remote_path + "/fom_record.txt from server to client.")
            io.log(self.log_id, 'c', 'e', "&&& Error while acquiring fom_record from server")
            self.exit_code = exit_code
            return
        #remove fom_record.txt
        rc.file_remove(self.remote_path + "/fom_record.txt")
        # for retrieving another file otherfile.txt from exchange folder
        #if self.exit_code != 0:
        #    return
        #else:
        #    self.exit_code = rc.file_get(self.remote_path + "otherfile.txt",
        #                                 os.path.join(self.local_path, "otherfile.txt"))
        return
