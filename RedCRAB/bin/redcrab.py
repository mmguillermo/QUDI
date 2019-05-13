"""
redcrab.py - Main program for the Client part of RedCRAB
@author: F. Höb, Jonathan Zoller (jonathan.zoller@gmx.de), S. Montangero, Marco Rossignolo (rossignolomarco@gmail.com), Phila Rembold (phila.rembold@gmail.com)
Current version number: 1.1.1
Current version dated: 31.10.2018
First version dated: 01.04.2017
"""
# encoding: utf-8
import sys
import os
import time
import threading
from shutil import copyfile, rmtree
import opti_instance as oo
import stopper_instance as stp
import remote_module as rc
import logging_module as io
#MarcoR 09.05.2018
from readconfig import readconfigfile

### Like in the opti_instance module the initialization of the optimization loop transmission is also based on
### exit code. The exit code for internal errors during initialization is -4. Additionally Exit codes from
### the remote_module and the opti_instance are also all handled here


# logging id that identifies this module
log_id = 1


def _readkey():
    """
            Reads key file in the Client_config folder

            Parameters
            ----------

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
            keydict : dict
                dictionary containing the parameters in the key file
    """
    global log_id
    try:
        # seperates at " := " and saves elements in dictionary
        keydict = {}
        with open(os.path.join(os.getcwd(), "..", "Config", "Client_config", "key.txt"), "r") as keyfile:
            keylines = keyfile.readlines()
        for ii in range(len(keylines)):
            dummy = [jj for jj in str(keylines[ii]).strip().split(" := ")]
            if ii == 0:
                keydict[str(dummy[0])] = int(dummy[1])
            else:
                keydict[str(dummy[0])] = str(dummy[1])
        return 0, keydict
    except OSError as err:
        io.log(log_id, 'f', 'e', "_readkey : OSError, errno: " + str(err.errno)
               + ", while reading key file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while trying to read key file in: " +
                                  str(os.path.join("Config", "Client_config"))
                                  + ". Make sure, that you have an account on the server and place your key file in the "
                                    "Client_config folder.")
        return -4, {}
    except (TypeError, ValueError):
        io.log(log_id, 'f', 'e', "_readkey : Type/ValueError while reading key file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while reading key file: " +
                                  str(os.path.join( "Config", "Client_config", "key.txt")) +
                                  ". Check if user id is integer")
        return -4, {}
    except IndexError:
        io.log(log_id, 'f', 'e', "_readkey : IndexError while reading key file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while reading key file: " +
               str(os.path.join("Config", "Client_config", "key.txt")) +
               ". Check if all keys have values")
        return -4, {}

def _readclientconfig():
    """
            Reads config file in the Client_config folder

            Parameters
            ----------

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
            clientdict : dict
                dictionary containing the parameters in the config file
    """
    global log_id
    try:
        # seperates at " := " and saves elements in dictionary
        clientdict = {}
        #MarcoR 07.05.2018
        config_name = "chopped.txt"
        with open(os.path.join(os.getcwd(), "..", "Config", "Client_config", config_name), "r") as configfile:
            configlines = configfile.readlines()
        basicswitch = False
        pathswitch = False
        for line in configlines:
            if "###" in str(line).strip():
                continue
            if "Specific" in str(line).strip() and basicswitch:
                basicswitch = False
                pathswitch = True
                continue
            if basicswitch:
                dummy = [jj for jj in str(line).strip().split(" := ")]
                try:
                    if "ServerCheckInterval" in str(dummy[0]):
                        clientdict[str(dummy[0])] = float(dummy[1])
                    elif "UserCheckInterval" in str(dummy[0]):
                        clientdict[str(dummy[0])] = float(dummy[1])
                    elif "LowerThresholdStd" in str(dummy[0]):
                        clientdict[str(dummy[0])] = float(dummy[1])
                    else:
                        clientdict[str(dummy[0])] = int(dummy[1])
                except (TypeError, ValueError):
                    clientdict[str(dummy[0])] = str(dummy[1])
            if pathswitch:
                dummy = [kk for kk in str(line).strip().split(" := ")]
                clientdict[str(dummy[0])] = str(dummy[1])
            if "Basic" in str(line).strip():
                basicswitch = True
        return 0, clientdict
    except OSError as err:
        io.log(log_id, 'f', 'e', "_readclientconfig : OSError, errno: " + str(err.errno) +
               ", while reading client config file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while trying to read client config file in: " +
               str(os.path.join("Config", "Client_config")) + ". Make sure, that it exists.")
        return -4, {}
    #MarcoR 07.05.2018
    except IndexError:
        io.log(log_id, 'f', 'e', "_readclientconfig : IndexError while reading client config file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while reading client config file: " +
               str(os.path.join("Config", "Client_config", config_name)) +
               ". Check if all keys have values")
        return -4, {}

def merge_dicts(x, y):
    """Merges the two dictionaries x and y into a shallow copy"""
    z = x.copy()
    z.update(y)
    return z

def _write_basic_pars(parsdict):
    """
            Writes all the read and during runtime created entries in the parameters dictionary to the basic pars file
            in the tmp folder for possible recovery

            Parameters
            ----------
            parsdict : dict
                Dictionary that contains all important parameters for the initialization

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)

    """
    global log_id
    #
    try:
        with open(os.path.join(os.getcwd(), "tmp", "basic_pars.txt"), "w") as parsfile:
            for key in parsdict:
                parsfile.write(str(key) + " := " + str(parsdict[key]) + "\n")
        return 0
    except OSError:
        io.log(log_id, 'f', 'i', "main : Error: An exception occured while saving the basic parameters")
        io.log(log_id, 'c', 'i', "&&& Error: An exception occured while saving the basic parameters."
                                 " Delete the bin/tmp folder, check permissions and restart "
                                 " RedCRAB to start the job again.")
        return -4


def _read_transmission_status():
    """
            Reads the transmission status file in the tmp folder for recovery

            Parameters
            ----------

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
            t_stat : int
                transmission status (upload/download)
            infolist : list
                info on optimization (curr. SI, NM function eval, etc.)
            watcher : int
                integer on last watcher filechange on server

    """
    global log_id
    try:
        # reads transmission status file for recovery
        infolist = [0,0,0,0]
        with open(os.path.join(os.getcwd(), "tmp", "transmission_status.txt"), "r") as tstatfile:
            t_stat = int(str(tstatfile.readline()).strip())
            if t_stat == 1:
                infoline = str(tstatfile.readline()).strip()
                infolist = [int(ii) for ii in infoline.split()]
                watcher = int(str(tstatfile.readline()).strip())
            else:
                #t_stat == 0
                watcher = int(str(tstatfile.readline()).strip())
        return 0, t_stat, infolist, watcher
    except OSError as err:
        io.log(log_id, 'f', 'e', "_read_transmission_status : OSError, errno: " + str(err.errno) +
               ", while reading transmission status")
        io.log(log_id, 'c', 'e', "&&& Error while reading: ./tmp/transmission_status.txt")
        return -4, 0, [], -1
    except (TypeError, ValueError):
        io.log(log_id, 'f', 'e', "_read_transmission_status : Type/ValueError while reading basic parameter settings")
        io.log(log_id, 'c', 'e', "&&& Error while reading: ./tmp/transmission_status.txt")
        return -4, 0, [], -1
    except EOFError:
        io.log(log_id, 'f', 'e', "_read_transmission_status : EOFError while reading basic parameter settings")
        io.log(log_id, 'c', 'e', "&&& Error while reading: ./tmp/transmission_status.txt")
        return -4, 0, [], -1


def _read_basic_pars():
    """
            Reads the basic_pars file in the tmp folder for recovery

            Parameters
            ----------

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
            parsdict : dict
                dictionary that contains the initialization parameters
    """
    global log_id
    try:
        # reads basic parameters file to dictionary for recovery
        parsdict = {}
        with open(os.path.join(os.getcwd(), "tmp", "basic_pars.txt"), "r") as parsfile:
            parslines = parsfile.readlines()
        for line in parslines:
            dummy = [str(jj) for jj in str(line).strip().split(" := ")]
            try:
                parsdict[dummy[0]] = int(dummy[1])
            except (TypeError, ValueError):
                parsdict[dummy[0]] = str(dummy[1])
        return 0, parsdict
    except OSError as err:
        io.log(log_id, 'f', 'e', "_read_basic_pars : OSError, errno: " + str(err.errno) +
               ", while reading basic parameter settings")
        io.log(log_id, 'c', 'e', "&&& Error while reading: ./tmp/basic_pars.txt.")
        return -4, {}


def _initialize_connection(channel_timeout, username, password, host_name):
    """
            Initialize connection in the remote_module by opening sftp channel.

            Parameters
            ----------

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
                                    From the remote_module: -1, -2
            parsdict : dict
                dictionary that contains the initialization parameters
    """
    global log_id
    internal_exit_code = rc.ssh_connect(host_name, username, password)
    if internal_exit_code != 0:
        return -4
    internal_exit_code = rc.sftp_connect()
    if internal_exit_code != 0:
        return -4
    rc.set_ftp_channel_timeout(channel_timeout=channel_timeout)
    return 0


def _stop_connection():
    """
            Cleanup method for connection stop

            Parameters
            ----------

            Returns
            -------

    """
    global log_id
    try:
        rc.close_sftp_connection()
        rc.close_ssh_connection()
    except Exception:
        # if anything weird happens while trying to close the channels...
        # not woth user notification as program will end after this anyway
        io.log(log_id, 'f', 'i', "opti_instance : Cosing ssh/ftp connection failed for some reason")


def _manage_config_file():
    """
            Manages config file by:
             1) Searching for it in the folder and retrieving the user job id from it.
             2) Calling the prepare_config_send funtion, that generates a user_stats folder and copies the config file
                there and renames the config file in the original folder by using a new internal job id that coontains
                the current system time in ms
             3) prepare_config_send also calls the _check_transfer method, that checks the TransmissionMethod entry in
                the config file

            Parameters
            ----------

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
            user_job_id  : str
                user job id from the RedCRAB config file name (or varied with current date and time if doubled)
            int_user_job_id : str
                user_job_id with timestamp (curr. system time in ms)
            user_stats_folder : str
                path to user stats folder for the current job
            iujid_cfg_file : str
                Path to the config file that has the internal user job id (user job id with timestamp) in its name
            transmission_method : int
                Transmission method read from the RedCRAB config file
    """
    global log_id
    try:
        for root, dirs, files in os.walk(os.path.join(os.getcwd(), "..", "Config", "RedCRAB_config")):
            if len(files) == 0:
                # no file in configfolder
                io.log(log_id, 'f', 'e', "_get_user_job_id : Error: No file in RedCRAB_config path")
                io.log(log_id, 'c', 'e', "&&& Error: No config file in RedCRAB_config path: "
                       + str(os.path.join("Config", "RedCRAB_config")))
                return -4, 0, "", "", "", 0, 0, 0
            elif len(files) == 1:
                # one file in configfolder -> is config file
                if "Cfg_" in str(files[0]) and ".txt" in str(files[0]):
                    # check if allowed length of user job name was exceeded
                    if len(str(files)) > 16:
                        io.log(log_id, 'f', 'e', "_get_user_job_id : Error: Too long user job name")
                        io.log(log_id, 'c', 'e', "&&& Error: Jobname too long. Use 8 numbers or less.")
                        return -4, 0, "", "", "", 0, 0, 0
                    user_job_id = str(files[0])[4:-4]
                    # changes user_job_id if a job of the same name already exists (to the name of the userstats folder)
                    internal_exit_code, user_job_id, int_user_job_id, user_stats_folder, iujid_cfg_file, \
                    transmission_method, stdavail, gpavail = _prepare_config_send(user_job_id, root, files[0])
                    if internal_exit_code != 0:
                        return -4, 0, "", "", "", 0, 0, 0
                    else:
                        return 0, user_job_id, int_user_job_id, user_stats_folder, \
                               iujid_cfg_file, transmission_method, stdavail, gpavail
                else:
                    io.log(log_id, 'f', 'e', "_get_user_job_id : Error: Wrong filename for config file")
                    io.log(log_id, 'c', 'e', "&&& Error: Wrong filename for config file: "
                           + str(os.path.join(root, files[0])))
                    return -4, 0, "", "", "", 0, 0, 0
            else:
                # more than one file in configfolder  -> error
                io.log(log_id, 'f', 'e', "_get_user_job_id : Error: More than one file in RedCRAB_config path")
                io.log(log_id, 'c', 'e', "&&& Error: More than one config file in RedCRAB_config path: "
                       + str(os.path.join("Config", "RedCRAB_config")))
                return -4, 0, "", "", "", 0, 0, 0
    except OSError as err:
        io.log(log_id, 'f', 'e', "_get_user_job_id : OSError, errno: " + str(err.errno) +
               ", while reading RedCRAB config file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while reading RedCRAB config file in path: " +
               str(os.path.join("Config", "RedCRAB_config")))
        return -4, 0, "", "", "", 0, 0, 0
    except (TypeError, ValueError):
        io.log(log_id, 'f', 'e', "_get_user_job_id : Type/ValueError while reading RedCRAB config file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while reading RedCRAB config file in path: " +
               str(os.path.join("Config", "RedCRAB_config")) +
               ". Check if file is named correctly")
        return -4, 0, "", "", "", 0, 0, 0
    except IndexError:
        io.log(log_id, 'f', 'e', "_get_user_job_id : IndexError while reading RedCRAB config file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while reading RedCRAB config file: " +
               str(os.path.join("Config", "RedCRAB_config")) +
               ". Check if file is named correctly")
        return -4, 0, "", "", "", 0, 0, 0

#MarcoR 22.08.2018
# Manage GuessPulsesFile
def _manage_guesspulses_file():
    """
            Manages guesspulses file by:
             1) Searching for it in the folder and retrieving the user job id from it.
             2) Calling the prepare_config_send funtion, that generates a user_stats folder and copies the config file
                there and renames the config file in the original folder by using a new internal job id that coontains
                the current system time in ms
             3) prepare_config_send also calls the _check_transfer method, that checks the TransmissionMethod entry in
                the config file

            Parameters
            ----------

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
            user_job_id  : str
                user job id from the RedCRAB config file name (or varied with current date and time if doubled)
            int_user_job_id : str
                user_job_id with timestamp (curr. system time in ms)
            user_stats_folder : str
                path to user stats folder for the current job
            iujid_cfg_file : str
                Path to the config file that has the internal user job id (user job id with timestamp) in its name
            transmission_method : int
                Transmission method read from the RedCRAB config file
    """
    global log_id
    try:
        # If GuessPulses.txt exists, do _prepare_config_send()
        exit_code = 0
        if os.path.isfile(os.path.join(os.getcwd(), "..","GuessPulses", "GuessPulses.txt")):
            print("In construction")
        else:
            io.log(log_id, 'f', 'e', "_manage_guesspulses_file() : Error: No GuessPulses file in RedCRAB_config path")
            io.log(log_id, 'c', 'e', "&&& Error: No GuessPulses file in RedCRAB_config path: "
                   + str(os.path.join("Config", "RedCRAB_config")))
            exit_code = -4
            return exit_code
        return exit_code
        #exit_code = _prepare_guesspulses_send()
        #
    except OSError as err:
        io.log(log_id, 'f', 'e', "_get_user_job_id : OSError, errno: " + str(err.errno) +
               ", while reading RedCRAB config file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while reading RedCRAB config file in path: " +
               str(os.path.join("Config", "RedCRAB_config")))
        return -4
    except (TypeError, ValueError):
        io.log(log_id, 'f', 'e', "_get_user_job_id : Type/ValueError while reading RedCRAB config file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while reading RedCRAB config file in path: " +
               str(os.path.join("Config", "RedCRAB_config")) +
               ". Check if file is named correctly")
        return -4
    except IndexError:
        io.log(log_id, 'f', 'e', "_get_user_job_id : IndexError while reading RedCRAB config file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while reading RedCRAB config file: " +
               str(os.path.join("Config", "RedCRAB_config")) +
               ". Check if file is named correctly")
        return -4
#

def _check_transmission_method(redcrab_cfg_file):
    """
                Checks TransmissionMethod parameter in config file

                Parameters
                ----------

                Returns
                -------
                exit_code : int
                    internal exit code. From this method: 0 (All okay) -4 (Error)
                transmission_method : int
                    transmission method read from config file
    """
    global log_id
    # check transfer method entry in redcrab config file
    # idea for the future: Automatically include default value of 0 if TransmissionMethod entry is not in config file
    # second idea, make reading of numeric initial guess possible, then save in entirely in config file
    try:
        with open(redcrab_cfg_file, "r") as rcconfigfile:
            configlines = rcconfigfile.readlines()
        for line in configlines:
            if "TransmissionMethod" in str(line):
                linearray = line.split(" := ")
                transmission_method = int(linearray[1])
            if "StdAvailable" in str(line):
                linearray = line.split(" := ")
                stdavail = int(linearray[1])
            #MarcoR 22.08.2018
            if "GuessPulsesAvailable" in str(line):
                linearray = line.split(" := ")
                gpavail = int(linearray[1])
        #MarcoR 22.08.2018
        if 'transmission_method' in locals() and 'stdavail' in locals() and 'gpavail' in locals():
            return 0, transmission_method, stdavail, gpavail
        io.log(log_id, 'f', 'e', "_check_transmission_method : Error while checking RedCRAB config file. No entry"
                                 " TransmissionMethod, StdAvailable or GuessPulsesAvailable, exit code  -4")
        io.log(log_id, 'c', 'e', "&&& Error while checking RedCRAB config file. Check if entry "
                                 "TransmissionMethod, StdAvailable and GuessPulsesAvailable exists "
                                 "and its value is 0 or 1.")
        return -4, 0, 0

    except OSError as err:
        io.log(log_id, 'f', 'e', "_check_transmission_method : OSError, errno: " + str(err.errno) +
               ", while checking RedCRAB config file" + str(redcrab_cfg_file) + " exit code  -4")
        io.log(log_id, 'c', 'e', "&&& Error while checking RedCRAB config file.")
        return -4, 0, 0
    except (TypeError, ValueError):
        io.log(log_id, 'f', 'e', "_check_transmission_method : Type/ValueError while checking RedCRAB config file,"
                                 " exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while checking RedCRAB config file. Check if entry TransmissionMethod exists "
                                 "and its value is 0 or 1.")
        return -4, 0, 0


def _prepare_config_send(ujid, redcrab_cfg_path, redcrab_cfg_name):
    """
            Prapares for sending the config file by:
            1) Defining the internal user job id with the timestamp
            2) Checking if a job with this id was sent previously and naming the user_stats_folder appropriately
               by adding current date and time if neccessary
            3) Copying the config file to the user stats folder and renaming the old one with its internal user job id

            Parameters
            ----------
            ujid : str
                user job id
            redcrab_cfg_path : str
                path to the redcrab config file in the RedCRAB config folder
            redcrab_cfg_name : str
                name of the redcrab config file

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
            ujid  : str
                input ujid from the RedCRAB config file name (or varied with current date and time if doubled)
            internal_user_job_id : str
                input ujid  with timestamp (curr. system time in ms)
            user_stats : str
                path to user stats folder for the current job
            new_cfg_file : str
                Path to the config file that has the internal user job id (user job id with timestamp) in its name
            transmission_method : int
                Transmission method read from the RedCRAB config file
    """
    global log_id
    systime = int(round(time.time() * 1000))
    # safer internal job id (with current time in ms)
    internal_user_job_id = str(systime) + str(ujid)
    # config file will be renamed with safer id
    new_cfg_file = os.path.join(redcrab_cfg_path, "Cfg_" + str(internal_user_job_id) + ".txt")
    try:
        # create user stats directory
        user_stats = ""
        if os.path.exists(os.path.join(os.getcwd(), "..", "RedCRAB", "userstats", "job_" + str(ujid))):
            # directory with user job id name already exists, append current date/time
            curr_time_and_date = str(time.strftime("%Y%m%d_%H%M%S"))
            new_job_name = str(ujid) + "_" + curr_time_and_date
            io.log(log_id, 'f', 'w', "_prepare_config_send : Job with ID: " + str(ujid) +
                   " already exists. Renaming to: " + new_job_name)
            io.log(log_id, 'c', 'w', "&&& Warning: Job with ID: " + str(ujid) +
                   " already exists. Renaming to: " + new_job_name)
            # also change user job id and config file name (by extending w. current date/time)
            ujid = new_job_name
            prev_redcrab_cfg_name = redcrab_cfg_name
            redcrab_cfg_name = "Cfg_" + str(ujid) + ".txt"
            # rename config file as well
            os.rename(os.path.join(redcrab_cfg_path, prev_redcrab_cfg_name),
                      os.path.join(redcrab_cfg_path, redcrab_cfg_name))
            os.makedirs(os.path.join(os.getcwd(), "..", "RedCRAB", "userstats", "job_" + new_job_name))
            user_stats = os.path.join(os.getcwd(), "..", "RedCRAB", "userstats", "job_" + new_job_name)
        else:
            os.makedirs(os.path.join(os.getcwd(), "..", "RedCRAB", "userstats", "job_" + str(ujid)))
            user_stats = os.path.join(os.getcwd(), "..", "RedCRAB", "userstats", "job_" + str(ujid))

        # check transfer method in config file:
        #MarcoR 22.08.2018 add gpavail
        internal_exit_code, transmission_method, stdavail, gpavail = _check_transmission_method(
            os.path.join(redcrab_cfg_path,redcrab_cfg_name))
        if internal_exit_code != 0:
            return -4, "", 0, "", "", 0
        # move file to user stats directory and rename old file with internal user id ( the one with the current time)
        copyfile(os.path.join(redcrab_cfg_path, redcrab_cfg_name), os.path.join(user_stats, redcrab_cfg_name))
        os.rename(os.path.join(redcrab_cfg_path, redcrab_cfg_name), new_cfg_file)
        return 0, ujid, internal_user_job_id, user_stats, new_cfg_file, transmission_method, stdavail, gpavail
    except OSError as err:
        io.log(log_id, 'f', 'e', "_prepare_config_send : OSError, errno: " + str(err.errno) +
               ", while preparing config files, exit code -4")
        io.log(log_id, 'c', 'e', "Error while preparing RedCRAB config file.")
        return -4, "", 0, "", "", 0
    except (TypeError, ValueError):
        io.log(log_id, 'f', 'e', "_prepare_config_send : Type/ValueError while preparing config files, exit code -4")
        io.log(log_id, 'c', 'e', "Error while preparing RedCRAB config file.")
        return -4, "", 0, "", "", 0

def _move_logging(user_stats_logpath, logfilename):
    """
            Moves the logging from the logconfig folder (temporary solution before the user stats folder was created)
            to the user stats folder

            Parameters
            ----------
            user_stats_logpath : str
                path to the directory in which the lo should be saved
            logfilename : str
                name of the new log file in the user stats dir

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
    """
    global log_id
    # move the logging from the temporary place in the logconfig folder to the user job stats folder
    # create log at userstats to be replaced with old log
    if not os.path.exists(user_stats_logpath):
        os.makedirs(user_stats_logpath)
    logfilepath = user_stats_logpath + "/" + logfilename
    try:
        copyfile(os.path.join(os.getcwd(), "logconfig", "tmp.log"), logfilepath)
        internal_exit_code = io.create_log(user_stats_logpath, logfilename)
        if internal_exit_code != 0:
            return -4
        io.init_logging()
    except (OSError, RuntimeError):
        return -4
    if os.path.exists(os.path.join(os.getcwd(), "logconfig", "tmp.log")):
        os.remove(os.path.join(os.getcwd(), "logconfig", "tmp.log"))
    return 0


def _send_config_to_server(config_filename, internal_user_job_id, userid):
    """
            Sends config file in RedCRAB config to server and removes the local one

            Parameters
            ----------
            config_filename : str
                Full path to the config file which is to be sent
            internal_user_job_id : str
                user job id with timestamp
            userid : int
                user id

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
                                    From the remote_module 2, 3
    """
    global log_id
    internal_exit_code = rc.re_exists("./RedCRAB/configfiles" + str(userid) , checkflag=False)
    if internal_exit_code == 0:
        internal_exit_code = rc.file_put(config_filename, "./RedCRAB/configfiles" +str(userid) +
                                "/Cfg_" + str(internal_user_job_id) + ".txt")
        if internal_exit_code != 0:
            io.log(log_id, 'f', 'e', "_send_config_to_server : Sending config file to server failed, exit code -4")
            io.log(log_id, 'c', 'e', "&&& Error: Sending config file to server failed")
            return -4
        else:
            return 0
    else:
        io.log(log_id, 'f', 'e', "_send_config_to_server : Error while trying to send configfile, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Fatal Error while trying to send configfile")
        return -4
#MarcoR 22.08.2018
# GuessPulses to server
def _send_guesspulses_to_server(userid):
    """
                Sends config file in RedCRAB config to server and removes the local one

                Parameters
                ----------
                config_filename : str
                    Full path to the config file which is to be sent
                internal_user_job_id : str
                    user job id with timestamp
                userid : int
                    user id

                Returns
                -------
                exit_code : int
                    internal exit code. From this method: 0 (All okay) -4 (Error)
                                        From the remote_module 2, 3
    """
    global log_id
    gpulses_filename = os.path.join(os.getcwd(),"..", "GuessPulses", "GuessPulses.txt")
    internal_exit_code = rc.re_exists("./RedCRAB/guesspulses", checkflag=False)
    if internal_exit_code == 0:
        internal_exit_code = rc.file_put(gpulses_filename, "./RedCRAB/guesspulses" +
                                         "/GuessPulses.txt")
        #PH 17.09.2018
        if internal_exit_code != 0:
            io.log(log_id, 'f', 'e', "_send_guesspulses_to_server : Sending guess file to server failed, exit code -4")
            io.log(log_id, 'c', 'e', "&&& Error: Sending guess file to server failed")
            return -4
        else:
            return 0
    else:
        io.log(log_id, 'f', 'e', "_send_guesspulses_to_server : Error while trying to send guess file, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Fatal Error while trying to send guess file")
        return -4

def _check_aborted_jobs(internal_user_job_id):
    """
            Checks aborted_jobs.txt file in local idmap folder for aborted jobs

            Parameters
            ----------
            internal_user_job_id : str
                user job id with timestamp


            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
                                    From the remote_module 2, 3
            bool
                True, if job was aborted, else if false
            str
                message from the server with the abort reason
    """

    global log_id
    local_idmap_dir = os.path.join(os.getcwd(), "..", "exchange", "IDmap")
    if not os.path.exists(local_idmap_dir):
        os.makedirs(local_idmap_dir)
    if os.path.exists(os.path.join(local_idmap_dir, "aborted_jobs.txt")):
        try:
            # check aborted_jobs if current job is somewhere in there
            with open(os.path.join(local_idmap_dir, "aborted_jobs.txt"), "r") as abortfile:
                abortlines = abortfile.readlines()
            for line in abortlines:
                abortelement = [str(ii) for ii in str(line).strip().split(" : ")]
                if str(internal_user_job_id) in abortelement[0]:
                    return 0, True, str(abortelement[1])
            return 0, False, ""
        except OSError as err:
            io.log(log_id, 'f', 'e', "_check_aborted_jobs : OSError, errno: " + str(err.errno) +
                   ", while checking aborted_jobs.txt, exit code -4")
            io.log(log_id, 'c', 'e', "&&& Error while waiting for server answer")
            return -4, False, ""
        except (TypeError, ValueError):
            io.log(log_id, 'f', 'e', "_check_aborted_jobs : Type/ValueError while checking aborted_jobs.txt, exit code -4")
            io.log(log_id, 'c', 'e', "&&& Error while waiting for server answer")
            return -4, False, ""
        except IndexError:
            io.log(log_id, 'f', 'e', "_check_aborted_jobs : IndexError while checking aborted_jobs.txt, exit code -4")
            io.log(log_id, 'c', 'e', "&&& Error while waiting for server answer")
            return -4, False, ""
    else:
        # still fine if it does not exists (might mean timeout but still)
        return 0, False, ""


def _check_if_offline():
    """
            Checks remote idmap folder for aborted_jobs and accepted jobs. Reads job id from accepted job file.

            Parameters
            ----------
            internal_user_job_id : str
                user job id with timestamp

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
                                    From the remote_module 2, 3
            bool
                True if server is offline, False if jobs can be sent
    """
    remote_idmappath = "./RedCRAB/exchange/IDmap"
    offline_exit_code = rc.re_exists(remote_idmappath + "/offline.txt", checkflag=True)
    if offline_exit_code == 0:
        # server is offline
        io.log(log_id, 'f', 'i', "_check_if_offline : The server is currently offline!")
        io.log(log_id, 'c', 'i', "&&& The server is currently offline! No jobs can be sent, wait for exit.")

        return 0, True
    elif offline_exit_code == -3:
        return 0, False
    else:
        io.log(log_id, 'f', 'e', "_get_job_id : Error while checking server status, exit code -4")
        io.log(log_id, 'c', 'e', "Fatal Error while checking server status")
        return -4, False


def _get_job_id(internal_user_job_id):
    """
            Checks remote idmap folder for aborted_jobs and accepted jobs. Reads job id from accepted job file.

            Parameters
            ----------
            internal_user_job_id : str
                user job id with timestamp

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error) -5 (Server aborted job prematurely)
                                    From the remote_module 2, 3
            job_id : int
                job id assigned by the server
    """
    global log_id
    wait_timeout = 0
    remote_idmappath = "./RedCRAB/exchange/IDmap"
    local_idmappath = os.path.join(os.getcwd(), "..", "exchange", "IDmap")
    # check if aborted_jobs was changed. Set to -1 to check at the beginning
    aborted_jobs_watcher = -1
    while True:
        # check if idmap folder exists (still exists)
        internal_exit_code = rc.re_exists(remote_idmappath, checkflag=False)
        if internal_exit_code == 0:
            ## check if the server was set busy
            busy_exit_code = rc.re_exists(remote_idmappath + "/busy.txt", checkflag=True)
            if busy_exit_code == 0:
                # server is busy
                io.log(log_id, 'f', 'w', "_get_job_id : The Server is currently busy and cannot accept further jobs."
                                         ", exit code -4")
                io.log(log_id, 'c', 'w', "+++ The Server is currently busy and cannot accept further jobs. "
                                         "Try again later")

                return -5, 0
            elif busy_exit_code == -3:
                # aborted_jobs file not there, do nothing special
                pass
            else:
                io.log(log_id, 'f', 'e', "_get_job_id : Error while waiting for server answer (during check)"
                        ", exit code -4")
                io.log(log_id, 'c', 'e', "Fatal Error while waiting for server answer")
                return -4, 0

            ## check if aborted jobs file was updated (update check to avoid having to check it too often)
            check_exit_code, aborted_changed = rc.file_stat(remote_idmappath + "/aborted_jobs.txt",
                                                            checkflag=True)
            if check_exit_code == 0:
                if aborted_changed != aborted_jobs_watcher:
                    aborted_jobs_watcher = aborted_changed
                    # download it and check if internal user id is somewhere in there
                    internal_exit_code = rc.file_get(remote_idmappath + "/aborted_jobs.txt",
                                                     os.path.join(local_idmappath, "aborted_jobs.txt"))
                    if internal_exit_code != 0:
                        io.log(log_id, 'f', 'e', "_get_job_id : Error while waiting for server answer (during transfer)"
                                                 ", exit code -4")
                        io.log(log_id, 'c', 'e', "&&& Error while waiting for server answer")
                        return -4, 0
                    else:
                        # check for internal user id in file
                        internal_exit_code, aborted_check, aborted_msg = _check_aborted_jobs(internal_user_job_id)
                        if aborted_check:
                            io.log(log_id, 'f', 'w', "_get_job_id : Job was aborted by server, reason: " + aborted_msg)
                            io.log(log_id, 'c', 'w', "+++ Job was aborted by server, reason: " + aborted_msg + ". Wait for exit")
                            return -5, 0
                        else:
                            if internal_exit_code != 0:
                                return -4, 0
                else:
                    pass
            elif check_exit_code == -3:
                # aborted_jobs file not there, do nothing special
                pass
            else:
                io.log(log_id, 'f', 'e',
                        "_get_job_id : Error while waiting for server answer (during check)"
                        ", exit code -4")
                io.log(log_id, 'c', 'e', "Fatal Error while waiting for server answer")
                return -4, 0

            ## check if a file with the new internal user job id as name is in the IDmap folder
            check_exit_code = rc.re_exists(remote_idmappath + "/" + str(internal_user_job_id) + ".txt",
                                           checkflag=True)
            if check_exit_code == 0:
                # download if it exists
                if not os.path.exists(os.path.join(os.getcwd(), "..", "exchange", "IDmap")):
                    os.makedirs(os.path.join(os.getcwd(), "..", "exchange", "IDmap"))
                internal_exit_code = rc.file_get(remote_idmappath + "/" + str(internal_user_job_id) + ".txt",
                                                 os.path.join(local_idmappath, str(internal_user_job_id) + ".txt"))
                if internal_exit_code != 0:
                    io.log(log_id, 'f', 'e', "_get_job_id : Error while waiting for server answer (during transfer)"
                                             ", exit code -4")
                    io.log(log_id, 'c', 'e', "&&& Error while waiting for server answer")
                    return -4, 0
                else:
                    # read if download successful
                    try:
                        with open(os.path.join(local_idmappath, str(internal_user_job_id) + ".txt"), "r") as confirmfile:
                            int_job_id = int(str(confirmfile.readline()).strip())
                        return 0, int_job_id
                    except OSError as err:
                        io.log(log_id, 'f', 'e', "_get_job_id : OSError, errno: " + str(err.errno) +
                               ", while checking confirmation file: " +
                               str(os.path.join(local_idmappath, str(internal_user_job_id) + ".txt")) + ", exit code -4")
                        io.log(log_id, 'c', 'e', "&&& Error while checking server answer")
                        return -4, 0
                    except (TypeError, ValueError):
                        io.log(log_id, 'f', 'e', "_get_job_id : Type/ValueError while checking confirmation file: " +
                               str(os.path.join(local_idmappath, str(internal_user_job_id) + ".txt")) + ", exit code -4")
                        io.log(log_id, 'c', 'e', "&&& Error while checking server answer")
                        return -4, 0

            elif check_exit_code == -3:
                # file not there, do nothing special
                pass
            else:
                io.log(log_id, 'f', 'e', "_get_job_id : Error while waiting for server answer (during check)"
                                         ", exit code -4")
                io.log(log_id, 'c', 'e', "&&& Fatal Error while waiting for server answer")
                return -4, 0

            time.sleep(3)
            wait_timeout += 3
            # after 30 minutes of no response: end it
            if wait_timeout > 1800:
                io.log(log_id, 'f', 'e', "_get_job_id : Error: No answer from server, exit code -4")
                io.log(log_id, 'c', 'e', "&&& Error: No answer from Server. Check if too many jobs over "
                                         "the job limit were sent simultaneously by the user.")
                return -4, 0
        else:
            io.log(log_id, 'f', 'e', "_get_job_id : Error while waiting for server answer, exit code -4")
            io.log(log_id, 'c', 'e', "&&& Fatal Error while waiting for server answer")
            return -4, 0


def _create_remote_exchangefolder(jobid):
    """
            Creates remote exchangejob + jobid folder

            Parameters
            ----------
            jobid : int
                server assigned job id

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
                                    From the remote_module 2, 3
            remote_exchangefolder : str
                pth to remote exchangefolder
    """
    remote_exchangefolder = "./RedCRAB/exchange/exchangejob" + str(jobid)
    exit_code = rc.re_mkdir(remote_exchangefolder)
    if exit_code != 0:
        io.log(log_id, 'f', 'e', "_create_remote_exchangefolder "
                                 ": Error while creating remote exchangefolder, exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error while creating remote exchangefolder")
        return -4, ""
    else:
        # wait for server response
        exch_timeout = 0
        while True:
            exit_code = rc.re_exists(remote_exchangefolder + "/ok.txt", checkflag=True)
            if exit_code == 0:
                exit_code = rc.file_remove(remote_exchangefolder + "/ok.txt")
                if exit_code != 0:
                    io.log(log_id, 'f', 'e', "_create_remote_exchangefolder "
                                             ": Error while handling server answer, exit code -4")
                    io.log(log_id, 'c', 'e', "&&& Error while handling server answer")
                    return -4, ""
                else:
                    return 0, remote_exchangefolder
            elif exit_code == -3:
                pass
            else:
                io.log(log_id, 'f', 'e', "_create_remote_exchangefolder "
                                         ": Error while waiting for server answer, exit code -4")
                io.log(log_id, 'c', 'e', "&&& Error while waiting for server answer")
                return -4, ""
            time.sleep(2)
            exch_timeout += 2
            if exch_timeout > 900:
                io.log(log_id, 'f', 'e', "_create_remote_exchangefolder "
                                         ": Error: No server answe, exit code -4")
                io.log(log_id, 'c', 'e', "&&& Error: No server answer. Wait some time and try a restart.")
                return -4, ""


def _prepare_optimization(jobid):
    """
            Last preparations for optimizations. Create local exchangejob+jobid folder. Create some dummy files in it.

            Parameters
            ----------
            jobid : int
                server assigned job id

            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay) -4 (Error)
            local_exchangefolder : str
                pth to local exchangefolder
    """
    global log_id
    # check if local exchangefolder already exists, if yes just delete it (probably server error, but should not happen)
    local_exchangefolder = os.path.join(os.getcwd(), "..", "exchange", "exchangejob" + str(jobid))
    try:
        if os.path.exists(local_exchangefolder):
            rmtree(local_exchangefolder)
        os.makedirs(local_exchangefolder)
        # create some initial dummy files
        open(os.path.join(local_exchangefolder, "pulse.txt"), "w").close()
        open(os.path.join(local_exchangefolder, "fom.txt"), "w").close()
        return 0, local_exchangefolder
    except OSError as err:
        io.log(log_id, 'f', 'e', "_prepare_optimization : OSError, errno: " + str(err.errno) +
               ", while preparing local exchange folder exit code -4")
        io.log(log_id, 'c', 'e', "&&& Error preparing local echange folder")
        return -4, ""


def _send_break(ecode):
    """
            Sends break containing exit code to tmp folder (signals failed exit handling at last exit)

            Parameters
            ----------
            ecode : int
                exit code

            Returns
            -------
            exit_code : int
                break exit code: 0 if break was sent sucessfully, 1 if tmp folder does not exist (e.g. for multilaunch)

    """
    global log_id
    # sends break.txt to tmp folder if it exists
    if os.path.exists(os.path.join(os.getcwd(), "tmp")):
        with open(os.path.join(os.getcwd(), "tmp", "break.txt"), "w") as breakfile:
            breakfile.write(str(ecode))
        return 0
    else:
        return 1

def _wait_for_server_confirm(stats_path, remote_path, local_path):
    """
            Waits for server confirm of sent Msg_u.txt for exit handling. Checks periodically for the server
            message Msg_s and either timeouts or calls successful exit.

            Parameters
            ----------
            remote_path : str
                path to remote exchangefolder
            local_path : str
                path to local exchangefolder

            Returns
            -------
            exit_code : int
                special exit code. From this method: 0 (All okay), 1 (Error), 2 No remote folder anymore (exit case)
    """
    global log_id
    # regardless of transmission type just downloads message file if it exists and reads it.
    # Waits until it contains confirm or alternatively until timeout
    # ecode is the specific exit code
    confirm_time = 0
    while True:
        # check if remote folder still exists
        check_exit_code = rc.re_exists(remote_path, checkflag=True)
        if check_exit_code == 0:
            # check if remote file exists
            check_exit_code = rc.re_exists(remote_path + "/Msg_s.txt", checkflag=True)
            if check_exit_code == 0:
                # remote file exists, dl it and read its first line
                internal_exit_code = rc.file_get(remote_path + "/Msg_s.txt", os.path.join(local_path, "Msg_s.txt"))
                if internal_exit_code != 0:
                    io.log(log_id, 'f', 'e', "_wait_for_server_confirm : Error while recieving message "
                                             "during exit handling.")
                    io.log(log_id, 'c', 'e',
                           "&&& Error while handling exit, check possible connection problems and restart.")
                    return 1
                else:
                    try:
                        with open(os.path.join(local_path, "Msg_s.txt"), "r") as smsgfile:
                            server_confirm = str(smsgfile.readline()).strip()
                        if len(server_confirm) > 0:
                            if "confirm" in server_confirm:
                                return 0
                            elif "abort" in server_confirm or "error" in server_confirm or "timeout" in server_confirm:
                                io.log(log_id, 'f', 'i', "_wait_for_server_confirm : Server aborted during exit handling")
                                io.log(log_id, 'c', 'i', "+++ Server aborted job during exit handling.")
                                return _send_message(stats_path, remote_path, local_path, "confirm")
                            else:
                                pass
                        else:
                            io.log(log_id, 'f', 'e', "_wait_for_server_confirm : Server sent empty file")
                            # this is something strage, that happend rarely while debugging. Randomly.
                            # in this case it usually helps to just wait some more until the server recognizes
                            # a user message
                            pass
                    except OSError as err:
                        io.log(log_id, 'f', 'e', "_wait_for_server_confirm : OSError, errno: " + str(err.errno) +
                               ", while handling exit")
                        io.log(log_id, 'c', 'e', "&&& Error while handling exit, check permissions and restart.")
                        return 1
            elif check_exit_code == -3:
                # do nothing special here, just wait some more
                pass
            else:
                io.log(log_id, 'f', 'e', "_wait_for_server_confirm : Error while recieving message "
                                         "during exit handling.")
                io.log(log_id, 'c', 'e', "&&& Error while handling exit, check possible connection problems and restart.")
                return 1
        elif check_exit_code == -3:
            # server already deleted the folder -> immediate exit
            io.log(log_id, 'f', 'i', "_wait_for_server_confirm : Smooth exit successful. Server "
                                     "exchangefolder was deleted.")
            io.log(log_id, 'c', 'i', "+++ Stopping transmission successful, wait for program exit.")
            return 2
        else:
            # some other error while trying to access folder:
            io.log(log_id, 'f', 'e', "_wait_for_server_confirm : Error while recieving message "
                                     "during exit handling.")
            io.log(log_id, 'c', 'e', "&&& Error while handling exit, check possible connection problems and restart.")
            return 1

        time.sleep(5.0)
        confirm_time += 5
        if confirm_time > 1000:
            io.log(log_id, 'f', 'e', "_wait_for_server_confirm : Error while recieving message "
                                     "during exit handling. (server does not respond)")
            io.log(log_id, 'c', 'e', "&&& Error while handling exit, server does not respond. Wait some time and restart.")
            return 1

def _send_client_logs(stats_path, remote_path):
    """
            Trys to send user logs to server. If it does not succeed there will be no consequences
            other than an entry in the log.

            Parameters
            ----------
            stats_path : str
                path to local stats folder
            remote_path : str
                path to remote exchangefolder

            Returns
            -------
    """
    global log_id
    try:
        logs_path = stats_path + "/logs"
        logs_exit_code = rc.re_exists(remote_path + "/logs", checkflag=True)
        if logs_exit_code  == 0:
            pass
        elif logs_exit_code  == -3:
            log_exit_code = rc.re_mkdir(remote_path + "/logs")
            if log_exit_code != 0:
                raise RuntimeError("Error while creating server side logs folder")
        else:
            raise RuntimeError("Error while creating server side logs folder")
        for logpath, logdirs, logfiles in os.walk(logs_path):
            for log in logfiles:
                log_exit_code = rc.file_put(os.path.join(logpath, log), remote_path + "/logs/" + str(log))
                if log_exit_code != 0:
                    raise RuntimeError("Error while putting log files to server")
    except Exception as e:
        message = "Type: " + str(type(e).__name__) + " Arguments: " + str(e.args)
        io.log(log_id, 'f', 'i', "_send_client_logs : An exception occurred while sending the client "
                                 "log to the server:")
        io.log(log_id, 'f', 'i', "_send_client_logs : " + message)



def _send_message(stats_path, remote_path, local_path, message):
    """
            Sends Msg_u.txt that contains message to the server. Also calls _send_client_logs

            Parameters
            ----------
            stats_path : str
                path to local stats folder
            remote_path : str
                path to remote exchangefolder
            local_path : str
                path to local exchangefolder
            message : str
                message to the server (abort, timeout, exit, error or confirm)

            Returns
            -------
            exit_code : int
                special exit code. From this method: 0 (All okay), 1 (Error), 2 No remote folder anymore (exit case)
    """
    global log_id
    check_exit_code = rc.re_exists(remote_path, checkflag=True)
    if check_exit_code == 0:
        if not os.path.exists(local_path):
            io.log(log_id, 'f', 'i', "_send_message : Local exchangefolder had to be recreated for exit handling")
            os.makedirs(local_path)
            # write to message file
        try:
            with open(os.path.join(local_path, "Msg_u.txt"), "w") as umsgfile:
                umsgfile.write(message)
        except OSError as err:
            io.log(log_id, 'f', 'e', "_send_message : OSError, errno: " + str(err.errno) +
                   ", while writing to user message during exit handling.")
            io.log(log_id, 'c', 'e', "&&& Error while handling exit, inquire about possible problems and restart.")
            return 1
        # try to send log files to server
        _send_client_logs(stats_path, remote_path)
        # send message file to server
        internal_exit_code = rc.file_put(os.path.join(local_path, "Msg_u.txt"), remote_path + "/Msg_u.txt")
        if internal_exit_code != 0:
            # some error while trying to put message file to server:
            io.log(log_id, 'f', 'e', "_send_message : Error while transferring message during exit handling.")
            io.log(log_id, 'c', 'e', "&&& Error while handling exit, inquire about possible problems and restart.")
            return 1
        else:
            return 0
    elif check_exit_code == -3:
        # server already deleted the folder -> immediate exit
        io.log(log_id, 'f', 'i', "_send_message : Smooth exit successful. Server exchangefolder was deleted")
        io.log(log_id, 'c', 'i', "+++ Smooth exit successful, wait for program exit.")
        return 2
    else:
        # some other error while trying to access folder:
        io.log(log_id, 'f', 'e', "_send_message : Error while transferring message during exit handling.")
        io.log(log_id, 'c', 'e', "&&& Error while handling exit, inquire about possible problems and restart.")
        return 1


def _exit_handler(tm_exit_code, remote_path, local_path, stats_path):
    """
            Handles exit with server depending on the exit code:
            1 -> User abort. Sends 'abort', waits for confirm
            2 -> Connection problems. Does nothind. Is ready for restart
            3 -> File not found/access related errors, sends 'error', waits for confirm
            4 -> General internal error during transmission, send 'error', waits for confirm
            5 -> Server aborted, sent timeout or error, send 'confirm'
            6 -> Client side timeout errors, send 'timeout', waits for confirm
            100 -> Normal exit message sent by server. Send 'exit'

            Parameters
            ----------
            tm_exit_code: int
                transmission exit code
            remote_path : str
                path to remote exchangefolder
            local_path : str
                path to local exchangefolder


            Returns
            -------
            exit_code : int
                internal exit code. From this method: 0 (All okay), 1 (Error), 2 No remote folder anymore (exit case)
    """
    global log_id
    # handles exit with server depending on status of transmission exit code
    if tm_exit_code == 1:
        # user break
        special_exit_code = _send_message(stats_path, remote_path, local_path, "abort")
        if special_exit_code == 0:
            special_exit_code = _wait_for_server_confirm(stats_path, remote_path, local_path)
            return special_exit_code
        else:
            return special_exit_code
    elif tm_exit_code == 2:
        # connection lost
        return 1
    elif tm_exit_code == 3:
        # some I/O error (something does not exists or cannot be accessed)
        special_exit_code = _send_message(stats_path, remote_path, local_path, "error")
        if special_exit_code == 0:
            special_exit_code = _wait_for_server_confirm(stats_path, remote_path, local_path)
            return special_exit_code
        else:
            return special_exit_code
    elif tm_exit_code == 4:
        # general internal error
        special_exit_code = _wait_for_server_confirm(stats_path, remote_path, local_path)
        if special_exit_code == 0:
            special_exit_code = _wait_for_server_confirm(remote_path, local_path)
            return special_exit_code
        else:
            return special_exit_code
    elif tm_exit_code == 5:
        # server aborted job
        return _send_message(stats_path, remote_path, local_path, "confirm")
    elif tm_exit_code == 6:
        # client/server timed out (noticed locally)
        special_exit_code = _send_message(stats_path, remote_path, local_path, "timeout")
        if special_exit_code == 0:
            special_exit_code = _wait_for_server_confirm(stats_path, remote_path, local_path)
            return special_exit_code
        else:
            return special_exit_code
    elif tm_exit_code == 100:
        # normal exit
        special_exit_code = _send_message(stats_path, remote_path, local_path, "exit")
        return special_exit_code
    else:
        # that should not happen...
        special_exit_code = _send_message(stats_path, remote_path, local_path, "error")
        if special_exit_code == 0:
            special_exit_code = _wait_for_server_confirm(stats_path, remote_path, local_path)
            return special_exit_code
        else:
            return special_exit_code


def opti_instance(stopper, init_dict):
    """
            Function for the optimization thread. Calls opti_instance constructor and opti_loop for transmission.
            Calls exit handler after exit from transmission.

            Parameters
            ----------
            stopper: threading.Event
                threading event for stopping
            init_dict : dict
                dictionary that contains the parameters for the constructor call

            Returns
            -------

    """
    global log_id
    io.log(log_id, 'f', 'i', "opti_instance : Initializing transmission...")
    io.log(log_id, 'c', 'i', "--- Initializing transmission...")
    opti_inst = oo.UserOpti(stopper_sentinel=stopper, **init_dict)
    io.log(log_id, 'f', 'i', "opti_instance : Starting transmission.")
    io.log(log_id, 'c', 'i', "+++ Starting transmission.")
    try:
        opti_exit_code = opti_inst.opti_loop()
    except Exception as ex:
        message = "Type: " + str(type(ex).__name__) + " Arguments: " +  str(ex.args)
        io.log(log_id, 'f', 'i', "opti_instance : An unhandled exception occurred:")
        io.log(log_id, 'f', 'i', "opti_instance : " + message)
        io.log(log_id, 'c', 'i', "&&& An unhandled exception occurred.")
        opti_exit_code = 4
    io.log(log_id, 'f', 'i', "opti_instance : Handling exit.")
    io.log(log_id, 'c', 'i', "--- Handling exit (This may take several minutes, "
                             "depending on the number of SIs and whether the optimization was successful or not).")
    # special exit_code 0: everything properly handled (smooth exit), 1: error during exit (handle on restart),
    # 2: server exchangepath deleted (still sort of smooth exit). If the exchangepath was deleted during opti_loop:
    # the exit code will be 3 -> error -> will always directly return a 2 as exit code
    special_exit_code = _exit_handler(opti_exit_code, init_dict["remote_path"], init_dict["local_path"],
                                      init_dict["stats_path"])
    _stop_connection()
    if special_exit_code == 0 or special_exit_code == 2:
        if os.path.exists(os.path.join(os.getcwd(), "tmp")):
            rmtree(os.path.join(os.getcwd(), "tmp"))
        if os.path.exists(init_dict["local_path"]):
            rmtree(init_dict["local_path"])
        io.log(log_id, 'f', 'i', "opti_instance : Exit handled successfully.")
        io.log(log_id, 'c', 'i', "+++ Exit handled successfully.")
        io.log(log_id, 'f', 'i', "opti_instance : RedCRAB transmission ended.")
        io.log(log_id, 'c', 'i', "+++ RedCRAB transmission ended.")
    else:
        # only for connection related problems allow full recovery, else just do exit handling
        if opti_exit_code == 2:
            # for opti_exit_code == 2 the exit_handler alwasy returns 1!
            io.log(log_id, 'f', 'i', "opti_instance : Connection problems, allow for recovery.")
            io.log(log_id, 'c', 'i', "+++ Recovery possible, check your connection and restart redcrab if ready.")
            io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB.")
        else:
            break_exit_code = _send_break(opti_exit_code)
            if break_exit_code == 0:
                io.log(log_id, 'f', 'i', "opti_instance : Error during exit handling.")
                io.log(log_id, 'c', 'i', "&&& Error during exit handling. Check your connection and restart for "
                                         "recovery to retry smooth exit.")
                io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB.")
            else:
                if os.path.exists(os.path.join(os.getcwd(), "tmp")):
                    rmtree(os.path.join(os.getcwd(), "tmp"))
                if os.path.exists(pdict["LocalPath"]):
                    rmtree(pdict["LocalPath"])
                io.log(log_id, 'f', 'i', "opti_instance : Error during exit handling.")
                io.log(log_id, 'c', 'i', "&&& Error during exit handling. No restart for recovery possible. "
                                         "Restarting RedCRAB will start a new job")
                io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB.")



def stopper_instance(stopevent,sleep):
    """
            Thread that checks if the user aborted the optimization by placing an exit(stop file in the Config folder

            Parameters
            ----------
            stopevent: threading.Event
                threading event for stopping
            sleep : int
                time between successive checks for user abort

            Returns
            -------

    """
    global log_id
    stp_inst = stp.Stopper(stopevent,sleep)
    io.log(log_id, 'f', 'i', "stopper_instance : Starting stopper instance.")
    retrys = 0
    while True:
        try:
            stp_inst.stop_check()
            break
        except (RuntimeError, OSError):
            if retrys < 3:
                retrys += 1
                continue
            else:
                io.log(log_id, 'c', 'i', "stopper_instance : Too many errors. Stopping module terminated")
                io.log(log_id, 'c', 'i', "+++ Error: Too many errors in stopping module, cnnot stop via 'stop.txt' "
                                         "anymore")
                break


### The actual RedCRAB program starts here
# delete previous temporary log if it exists
if os.path.exists(os.path.join(os.getcwd(), "logconfig", "tmp.log")):
    os.remove(os.path.join(os.getcwd(), "logconfig", "tmp.log"))
# check for stop/exit file and remove it
for (root, dirs, files) in os.walk(os.path.join(os.getcwd(), "../", "Config")):
    for file in files:
        if "stop" in str(file) or "exit" in str(file):
            os.remove(os.path.join(root, file))
exit_code = io.create_log("./logconfig", "tmp.log")
if exit_code != 0:
    print("&&& Error while initializing log file, exiting")
    print("+++ Terminating RedCRAB")
    sys.exit(-4)
io.init_logging()
# initial branching between completely new job or recovery
io.log(log_id, 'c', 'i', "--- RedCRAB version 1.1.3 ---")
if not os.path.exists(os.path.join(os.getcwd(), "tmp")):
    
    # normal optimization:
    io.log(log_id, 'f', 'i', "main : Starting new RedCRAB optimization run")
    io.log(log_id, 'c', 'i', "--- Starting new RedCRAB optimization run")
    io.log(log_id, 'f', 'i', "main : Initialization...")
    io.log(log_id, 'c', 'i', "--- Initialization...")

    # read key config file
    exit_code, kdict = _readkey()
    if exit_code != 0:
        io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
        io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
        sys.exit(-4)

    # read file with user configurations
    exit_code, cdict = _readclientconfig()
    if exit_code != 0:
        io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
        io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
        sys.exit(-4)


    # combine read data
    # Python 3.5 style pdict = {**kdict, **cdict}, more compatible:
    pdict = merge_dicts(kdict, cdict)

    # handle config file and get user job id (user_j_id), the internal user job id with the timestamp (internal_ujid),
    # the path to the local user stats folder, the path to the config file that contains
    # the internal_ujid (internal_config_file) and transmission, that is the transmission mode (0 or 1)
    #MarcoR 22.08.2018 Add gpavail
    exit_code, user_j_id, internal_ujid, user_stats_path, internal_config_file, transmission, \
    stdavail, gpavail = _manage_config_file()
    #MarcoR 22.08.2018
    # _manage_config_file() should also return FileGuessPulseAvail. If it is true, go to _manage_guesspulse_file()

    #
    if exit_code != 0:
        io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
        io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
        if os.path.exists(internal_config_file):
            os.remove(internal_config_file)
        sys.exit(-4)
    #MarcoR 08.06.2018
    if os.path.exists(os.path.join(os.getcwd(), "tmp")):
        rmtree(os.path.join(os.getcwd(), "tmp"))
    os.makedirs(os.path.join(os.getcwd(), "tmp"))
    # Copy Cfg file into tmp folder for a possible recovery
    copyfile(internal_config_file, os.path.join(os.getcwd(), "tmp", "Cfg_" + str(user_j_id) + ".txt"))


    #MarcoR Cfg path in tmp for recovery
    pdict["PathTmpCfg"] = os.path.join(os.getcwd(), "tmp", "Cfg_" + str(user_j_id) + ".txt")

    pdict["UserStatsPath"] = user_stats_path
    pdict["UserJobID"] = user_j_id
    pdict["TransmissionMethod"] = transmission
    pdict["StdAvailable"] = stdavail
    #MarcoR 22.08.2018
    # Add gpavail
    pdict["GPAvailable"] = gpavail
    io.log(log_id, 'f', 'i', "main : User Job id is: " + str(user_j_id))
    io.log(log_id, 'f', 'i', "main : Internal User Job id is: " + str(internal_ujid))

    io.log(log_id, 'f', 'i', "main : Manage logging...")
    io.log(log_id, 'c', 'i', "--- Manage logging...")

    # move logging to user stats location
    log_user_stats_path = "./../RedCRAB/userstats/job_" + str(user_j_id) + "/logs"
    logname = "log_job" + str(user_j_id) + ".log"
    exit_code = _move_logging(log_user_stats_path, logname)
    if exit_code != 0:
        print("&&& Error while moving log file, exiting")
        print("+++ Terminating RedCRAB")
        if os.path.exists(internal_config_file):
            os.remove(internal_config_file)
        sys.exit(-4)
    io.log(log_id, 'f', 'i', "main : Logging handled")
    io.log(log_id, 'c', 'i', "+++ Logging handled")
    try:
        io.log(log_id, 'f', 'i', "main : Establish server connection...")
        io.log(log_id, 'c', 'i', "--- Establish server connection...")
        # establish connection to server
        if pdict["ChannelTimeout"] > 30 or pdict["ChannelTimeout"] < 10:
            pdict["ChannelTimeout"] = 15
        exit_code = _initialize_connection(pdict["ChannelTimeout"], pdict["Username"], pdict["Password"],
                                           pdict["HostName"])
        if exit_code != 0:
            if os.path.exists(internal_config_file):
                os.remove(internal_config_file)
            io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
            io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
            sys.exit(-4)

        io.log(log_id, 'f', 'i', "main : Checking server status")
        io.log(log_id, 'c', 'i', "--- Checking server status")
        exit_code, offline = _check_if_offline()

        if exit_code != 0:
            _stop_connection()
            if os.path.exists(internal_config_file):
                os.remove(internal_config_file)
            io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
            io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
            sys.exit(-4)
        else:
            if offline:
                _stop_connection()
                if os.path.exists(internal_config_file):
                    os.remove(internal_config_file)
                io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
                io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
                sys.exit(0)
            else:
                io.log(log_id, 'f', 'i', "main : Server status ok")
                io.log(log_id, 'c', 'i', "+++ Server status ok")

        # send config file to server
        io.log(log_id, 'f', 'i', "main : Sending config file to server...")
        io.log(log_id, 'c', 'i', "--- Sending config file to server...")
        exit_code = _send_config_to_server(internal_config_file, internal_ujid, pdict["UserID"])
        #MarcoR 22.08.2018
        # send guesspulses file to server
        if gpavail:
            io.log(log_id, 'f', 'i', "main : Sending guesspulses file to server...")
            io.log(log_id, 'c', 'i', "--- Sending guesspulses file to server...")
            exit_code = _send_guesspulses_to_server(pdict["UserID"])
    except KeyError:
        if os.path.exists(internal_config_file):
            os.remove(internal_config_file)
        io.log(log_id, 'c', 'e', "main : KeyError during recovery. Ensure, that all relevant keys are "
                                 "in the key.txt and config.txt files")
        io.log(log_id, 'c', 'e', "&&& Error during recovery. Ensure, that all relevant keys are "
                                 "in the key.txt and config.txt files. Terminating RedCRAB.")
        sys.exit(-4)

    # delete the local version of the config file now
    if os.path.exists(internal_config_file):
        os.remove(internal_config_file)
    if exit_code != 0:
        _stop_connection()
        io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
        io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
        sys.exit(-4)

    io.log(log_id, 'f', 'i', "main : Config file sent sucessfully...")
    io.log(log_id, 'c', 'i', "+++ Config file sent sucessfully")

    io.log(log_id, 'f', 'i', "main : Waiting for server answer...")
    io.log(log_id, 'c', 'i', "--- Waiting for server answer...")

    # wait for server answer and if answer is that job was accepted carry on, else stop execution
    exit_code, job_id = _get_job_id(internal_ujid)
    if exit_code != 0:
        # remove internal ujid confirm file if it was transferred
        _stop_connection()
        io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
        io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
        if exit_code == -5:
            sys.exit(0)
        else:
            sys.exit(-4)
    pdict["JobID"] = job_id
    io.log(log_id, 'f', 'i', "main : Server job id is: " + str(job_id))
    try:
        with open(os.path.join(user_stats_path, "logs", "server_job_id.txt"), "w") as jobidfile:
            jobidfile.write(str(job_id))
    except OSError:
        # not terribly relevant, therefore do nothing should it does not work
        pass

    io.log(log_id, 'f', 'i', "main : Server answer recieved")
    io.log(log_id, 'c', 'i', "+++ Server answer recieved")

    # prepare for optimization (create remote exchange folder, create local exchange folder)
    io.log(log_id, 'f', 'i', "main : Doing final preparations...")
    io.log(log_id, 'c', 'i', "--- Doing final preparations (may take some time)...")
    # remote exchange folder creation
    exit_code, remote_exchangepath = _create_remote_exchangefolder(job_id)
    if exit_code != 0:
        _stop_connection()
        io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
        io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
        sys.exit(-4)
    pdict["RemotePath"] = remote_exchangepath

    # local exchange folder creation
    exit_code, local_exchangepath = _prepare_optimization(job_id)
    if exit_code != 0:
        io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
        io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
        _stop_connection()
        sys.exit(-4)
    pdict["LocalPath"] = local_exchangepath

    # initialize watcher integers for later
    pdict["SmsgWatcher"] = -1
    pdict["FompathWatcher"] = -1
    # optimization info (SI, NM feval etc.)
    #MarcoR 08.06.2018
    # mv this block up in order to copy the Cfg file into tmp folder.
    # Probably could be exist a better solution. Maybe copying from userStats
    #if os.path.exists(os.path.join(os.getcwd(), "tmp")):
    #    rmtree(os.path.join(os.getcwd(), "tmp"))
    #os.makedirs(os.path.join(os.getcwd(), "tmp"))

    # write basic parameters to file
    exit_code = _write_basic_pars(pdict)

    #MarcoR 09.05.2017
    # read file with opti-parameters
    (mainpars, algpars, mainflagged, pulsepars, pulseflagged, parapars,
     paraflagged, exit_code) = readconfigfile(pdict["PathTmpCfg"])
    kwargs_bib = {'mainpars': mainpars, 'algpars': algpars, 'mainflagged': mainflagged,
                  'pulsepars': pulsepars, 'pulseflagged': pulseflagged,
                  'parapars': parapars, 'paraflagged': paraflagged}
    #MarcoR 08.06.2018
    # Merge dictionary
    pdict = merge_dicts(pdict, kwargs_bib)
    #

    if exit_code != 0:
        _stop_connection()
        if os.path.exists(os.path.join(os.getcwd(), "tmp")):
            rmtree(os.path.join(os.getcwd(), "tmp"))
        io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
        io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
        sys.exit(-4)

    # important parameters for the recovery. Both get their own file, that is updated during
    # the optimization
    # transfer mode to initial download of pulse
    pdict["TransferMode"] = 0
    # not directly convertable to string therefore left out
    pdict["OptiInfo"] = [0, 0, 0, 0]
    # Flag for recovery mode. Only used to perform precheck in opti_instance if a new server message arrived.
    # Set to false to avoid this precheck
    pdict["IsRecovery"] = False

    io.log(log_id, 'f', 'i', "main : Preparations finished...")
    io.log(log_id, 'c', 'i', "+++ Preparations finished...")

else:
    # recovery from previously failed optimization!
    io.log(log_id, 'f', 'i', "main : Starting recovery from previously aborted optimization")
    io.log(log_id, 'c', 'i', "--- Starting recovery from previously aborted optimization")

    # some initial preparations:
    exit_code, pdict = _read_basic_pars()

    #MarcoR 09.05.2017
    # read file with opti-parameters
    (mainpars, algpars, mainflagged, pulsepars, pulseflagged, parapars,
     paraflagged, exit_code) = readconfigfile(pdict["PathTmpCfg"])
    kwargs_bib = {'mainpars': mainpars, 'algpars': algpars, 'mainflagged': mainflagged,
                  'pulsepars': pulsepars, 'pulseflagged': pulseflagged,
                  'parapars': parapars, 'paraflagged': paraflagged}
    #MarcoR 08.06.2018
    # Merge dictionary
    pdict = merge_dicts(pdict, kwargs_bib)
    #
    if exit_code != 0:
        io.log(log_id, 'f', 'i', "main : Error during recovery, basic parameter file could not be read. "
                                 "Terminating RedCRAB.")
        io.log(log_id, 'c', 'i', "&&& Error during recovery, basic parameter file could not be read."
                                 " Terminating RedCRAB. No further recovery possible restart will start a new job")
        if os.path.exists(os.path.join(os.getcwd(), "tmp")):
            rmtree(os.path.join(os.getcwd(), "tmp"))
        if os.path.exists(pdict["LocalPath"]):
            rmtree(pdict["LocalPath"])
        sys.exit(-4)
    try:
        # switch log to the one in usertstats and append old log
        log_user_stats_path = "./../RedCRAB/userstats/job_" + str(pdict["UserJobID"]) + "/logs"
        logname = "log_job" + str(pdict["UserJobID"]) + ".log"
        if not os.path.exists(log_user_stats_path):
            io.log(log_id, 'f', 'i', "main : Needed to create stats folder anew.")
            io.log(log_id, 'c', 'i', "+++ Previous stats folder " + log_user_stats_path +
                   " does not exist anymore. Created a new one")
            os.makedirs(log_user_stats_path)
        exit_code = io.create_log(log_user_stats_path, logname)
        if exit_code != 0:
            print("&&& Error while moving log file, exiting. No further recovery possible")
            if os.path.exists(os.path.join(os.getcwd(), "tmp")):
                rmtree(os.path.join(os.getcwd(), "tmp"))
            if os.path.exists(pdict["LocalPath"]):
                rmtree(pdict["LocalPath"])
            sys.exit(-4)
        try:
            with open(os.path.join(os.getcwd(), "logconfig", "tmp.log"), "r") as templog:
                loglines = templog.readlines()
            with open(log_user_stats_path + "/" + logname, "a+") as usrlog:
                for element in loglines:
                    usrlog.write(str(element).strip() + str("\n"))
            io.init_logging()
        except Exception as ex:
            message = "Type: " + str(type(ex).__name__) + " Arguments: " + str(ex.args)
            print("&&& Error while moving log file, exiting")
            print("Error message is: " + message)
            print("+++ Terminating RedCRAB")
            if os.path.exists(os.path.join(os.getcwd(), "config", "tmp.log")):
                os.remove(os.path.join(os.getcwd(), "config", "tmp.log"))
            sys.exit(-4)

        # start connection to server
        exit_code = _initialize_connection(pdict["ChannelTimeout"], pdict["Username"], pdict["Password"],
                                           pdict["HostName"])
        if exit_code != 0:
            io.log(log_id, 'f', 'i', "main : Terminating RedCRAB")
            io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB")
            sys.exit(-4)

        #Decision branch between unhandled exit and recover running job
        if os.path.exists(os.path.join(os.getcwd(), "tmp", "break.txt")):
            # if previously unhandled exit remains:
            io.log(log_id, 'f', 'i', "main : Unhandled exit. Trying to handle in recovery.")
            io.log(log_id, 'c', 'i', "--- Unhandled exit. Trying to handle in recovery.")
            try:
                with open(os.path.join(os.getcwd(), "tmp", "break.txt"), "r") as breakreadfile:
                    prev_error = int(breakreadfile.readline())
            except (OSError, TypeError, ValueError):
                io.log(log_id, 'f', 'i', "main : Error during exit handling. Exit code could not be read")
                io.log(log_id, 'c', 'i', "&&& Error during exit handling. Exit code could not be read."
                                         " Terminating RedCRAB. No further recovery possible, "
                                         "restart will start a new job")
                if os.path.exists(os.path.join(os.getcwd(), "tmp")):
                    rmtree(os.path.join(os.getcwd(), "tmp"))
                if os.path.exists(pdict["LocalPath"]):
                    rmtree(pdict["LocalPath"])
                _stop_connection()
                sys.exit(-4)
            else:
                handler_exit_code = _exit_handler(prev_error, pdict["RemotePath"], pdict["LocalPath"],
                                                  pdict["UserStatsPath"])
                if handler_exit_code == 0 or handler_exit_code == 2:
                    if os.path.exists(os.path.join(os.getcwd(), "tmp")):
                        rmtree(os.path.join(os.getcwd(), "tmp"))
                    if os.path.exists(pdict["LocalPath"]):
                        rmtree(pdict["LocalPath"])
                    io.log(log_id, 'f', 'i', "main : Exit handled successfully.")
                    io.log(log_id, 'c', 'i', "+++ Exit handled successfully.")
                    io.log(log_id, 'f', 'i', "main : RedCRAB transmission ended.")
                    io.log(log_id, 'c', 'i', "+++ RedCRAB transmission ended.")
                    _stop_connection()
                    sys.exit(0)
                else:
                    io.log(log_id, 'f', 'i', "main : Error during exit handling. No further recovery allowed.")
                    io.log(log_id, 'c', 'i', "&&& Error during recovery exit handling. No further recovery possible."
                                             " Terminating RedCRAB")
                    _stop_connection()
                    sys.exit(-4)
        else:
            # if there is some running job remaining
            io.log(log_id, 'f', 'i', "main : Aborted job remaining.")
            io.log(log_id, 'c', 'i', "--- Aborted job remaining, starting recovery.")
            exit_code, tstat, infostat, smsg_watcher =_read_transmission_status()
            if exit_code != 0:
                if os.path.exists(os.path.join(os.getcwd(), "tmp")):
                    rmtree(os.path.join(os.getcwd(), "tmp"))
                if os.path.exists(pdict["LocalPath"]):
                    rmtree(pdict["LocalPath"])
                io.log(log_id, 'f', 'i', "main : Error during recovery, transmission status could not be read")
                io.log(log_id, 'c', 'i', "&&& Error during recovery, transmission status could not be read."
                                         "Terminating RedCRAB. No further recovery possible, "
                                         "restart will start a new job")
                _stop_connection()
                sys.exit(-4)

            pdict["TransferMode"] = tstat
            pdict["OptiInfo"] = infostat
            pdict["SmsgWatcher"] = smsg_watcher
            # recovery flag for initial server check
            pdict["IsRecovery"] = True

            io.log(log_id, 'c', 'i', "main : Restarting transmission.")
            io.log(log_id, 'c', 'i', "--- Restarting transmission.")
    except KeyError:
        if os.path.exists(os.path.join(os.getcwd(), "tmp")):
            rmtree(os.path.join(os.getcwd(), "tmp"))
        io.log(log_id, 'f', 'i', "main : KeyError during recovery.")
        io.log(log_id, 'c', 'i', "&&& Error during recovery. Terminating RedCRAB. "
                                 "No further recovery possible, restart will start a new job.")
        _stop_connection()
        sys.exit(-4)



# Handling the transition to the transmission (syncronizing new optis and recoverys)
# also testing the parameters if the user used wrong data types
para_exit_code = 0
# dummy variable, initialized that pycharm does not bug you with missing var in stopping_thread
# call
stopper_sleep = 1
parameters = {}
try:
    parameters["server_waittime"] = int(pdict["ServerWaittime"])
    parameters["user_waittime"] = int(pdict["UserWaittime"])
    parameters["server_checkinterval"] = float(pdict["ServerCheckInterval"])
    parameters["user_checkinterval"] = float(pdict["UserCheckInterval"])
    parameters["std_low_thresh"] = float(pdict["LowerThresholdStd"])
    parameters["pulse_formatters"] = [int(pdict["PulseFormat"]), int(pdict["PulseAccuracy"])]
    #MarcoR 05.06.2018
    parameters["split_pulses_file"] = int(pdict.setdefault("SplitPulsesFile",0))
    parameters["remote_path"] = str(pdict["RemotePath"])
    parameters["local_path"] = str(pdict["LocalPath"])
    parameters["stats_path"] = str(pdict["UserStatsPath"])
    parameters["transmission_method"] = int(pdict["TransmissionMethod"])
    parameters["stdavail"] = int(pdict["StdAvailable"])
    #MarcoR 12.12.2018
    parameters["do_plotting"] = int(pdict.setdefault("DoPlotting", 1))

    if pdict["FOMEvaluation"] == 0:
        # via python module
        parameters["fom_method"] = [int(pdict["FOMEvaluation"]), str(pdict["PyModPath"]), str(pdict["PyModName"])]
    elif pdict["FOMEvaluation"] == 1:
        parameters["fom_method"] = [int(pdict["FOMEvaluation"]), str(pdict["Command"]), str(pdict["PulsePath"]),
                                    str(pdict["FOMPath"])]
    elif pdict["FOMEvaluation"] == 2:
        parameters["fom_method"] = [int(pdict["FOMEvaluation"]), str(pdict["PulsePath"]), str(pdict["FOMPath"])]
    elif pdict["FOMEvaluation"] == 3: #matlab engine for python
        parameters["fom_method"] = [int(pdict["FOMEvaluation"]), str(pdict["MatlabProgPath"]), int(pdict["MatlabengineRestartInterval"])]
    elif pdict["FOMEvaluation"] == 4: #matlab via txt file
        pass
        para_exit_code = 1 # later: remove
    else:
        io.log(log_id, 'f', 'e', "main : FOMevaluation method number error: not within speecified "
                                 "range {0,1,2,3,4}")
        io.log(log_id, 'c', 'e', "&&& Error: FOMevaluation method number: not within speecified "
                                 "range {0,1,2,3,4}")
        para_exit_code = 1



    parameters["transfer_mode"] = int(pdict["TransferMode"])
    parameters["smsg_watcher"] = int(pdict["SmsgWatcher"])
    parameters["fompath_watcher"] = pdict["FompathWatcher"]
    parameters["user_job_id"] = str(pdict["UserJobID"])
    parameters["opti_info"] = pdict["OptiInfo"]
    parameters["is_recovery"] = pdict["IsRecovery"]
    #MarcoR 08.06.2018
    # Add Cfg informations into parameters mainpars, algpars, mainflagged,
    # pulsepars, pulseflagged, parapars, paraflagged
    parameters["mainpars"] = pdict["mainpars"]
    parameters["algpars"] = pdict["algpars"]
    parameters["mainflagged"] = pdict["mainflagged"]
    parameters["pulsepars"] = pdict["pulsepars"]
    parameters["pulseflagged"] = pdict["pulseflagged"]
    parameters["parapars"] = pdict["parapars"]
    parameters["paraflagged"] = pdict["paraflagged"]
    stopper_sleep = int(pdict["AbortCheck"])

except KeyError:
    io.log(log_id, 'f', 'e', "main : KeyError: Missing config entrys")
    io.log(log_id, 'c', 'e', "&&& Error: There are missing entries in the config.txt file."
                             " Handling exit.")

    para_exit_code = 1
except (TypeError, ValueError):
    io.log(log_id, 'f', 'e', "main : Type/ValueError: Wrong types for the config/key entries")
    io.log(log_id, 'c', 'e', "&&& Error: There are entries with wrong types in the config or key file."
                             " Check that and restart.")
    para_exit_code = 1

if para_exit_code != 0:
    # remote path and local path are generated at runtime and therefore always there
    # (else some error would have occurred already)
    io.log(log_id, 'f', 'i', "main : Handling exit.")
    io.log(log_id, 'c', 'i', "--- Handling exit.")
    handler_exit_code = _exit_handler(4, pdict["RemotePath"], pdict["LocalPath"], pdict["UserStatsPath"])
    if handler_exit_code == 0 or handler_exit_code == 2:
        if os.path.exists(os.path.join(os.getcwd(), "tmp")):
            rmtree(os.path.join(os.getcwd(), "tmp"))
        if os.path.exists(pdict["LocalPath"]):
            rmtree(pdict["LocalPath"])
        io.log(log_id, 'f', 'i', "main : Exit handled successfully.")
        io.log(log_id, 'c', 'i', "+++ Exit handled successfully.")
        io.log(log_id, 'f', 'i', "main : RedCRAB transmission ended.")
        io.log(log_id, 'c', 'i', "+++ RedCRAB transmission ended.")
        _stop_connection()
        sys.exit(0)
    else:
        b_exit_code = _send_break(4)
        if b_exit_code == 0:
            io.log(log_id, 'f', 'i', "opti_instance : Error during exit handling.")
            io.log(log_id, 'c', 'i', "&&& Error during exit handling. Check your connection and restart for recovery "
                                     "to retry smooth exit.")
        else:
            if os.path.exists(os.path.join(os.getcwd(), "tmp")):
                rmtree(os.path.join(os.getcwd(), "tmp"))
            if os.path.exists(pdict["LocalPath"]):
                rmtree(pdict["LocalPath"])
            io.log(log_id, 'f', 'i', "opti_instance : Error during exit handling.")
            io.log(log_id, 'c', 'i', "&&& Error during exit handling. No restart for recovery possible. "
                                     "Restarting RedCRAB will start a new job")
        io.log(log_id, 'c', 'i', "+++ Terminating RedCRAB.")
        _stop_connection()
        sys.exit(-4)
else:
    # checking event if user stopped transmission
    user_stop = threading.Event()
    opti_thread = threading.Thread(name='Optimization', target=opti_instance, args=(user_stop, parameters))
    stopping_thread = threading.Thread(name='Stopper', target=stopper_instance, args=(user_stop, stopper_sleep))
    stopping_thread.setDaemon(True)
    stopping_thread.start()
    opti_thread.start()

#MarcoR 02.06.2018
# Maybe an Try-Exception block could "solve" error about matplotlib

