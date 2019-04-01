# encoding: utf-8
"""
remote_module.py - Interfaces for paramiko functions
@author: Fabian Höb (fabi.ho@web.de)
Current version number: 1.0.4
Current version dated: 11.05.2017
First version dated: 01.04.2017
"""
import errno
import time
import paramiko
import socket
import logging_module as io

_log_id = 3
# how often should sftp operation be retried in case of a failure (currently hardcoded)
# tbd: make it possible to change this value by the config file (setter function)
_wrapper_repeat = 3
# time between wrapper call repeats
# tbd: make it possible to change this value by the config file (setter function)
_wrapper_waittime = 0.2
_curr_ssh = None
_curr_sftp = None


def ssh_connect(host_name, username, passwd):
    """
            Try to connect via paramiko ssh to the host_name. Retry a few times if it fails.

            Parameters
            ----------
            host_name : str
                name of the host to connect to
            username : str
                name of the user to connect
            passwd : str
                password

            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (All ok) -1 (Could not connect) -2 (Authentication failed)

    """
    global _log_id
    global _curr_ssh
    ii = 1
    while True:
        io.log(_log_id, 'c', 'i', "--- Trying to connect to %s (%i/10)" % (host_name, ii))
        io.log(_log_id, 'f',  'i', "ssh_connect: Trying to connect to %s (%i/10)" % (host_name, ii))

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host_name, username=username, password=passwd)
            _curr_ssh = ssh
            io.log(_log_id, 'c', 'i', "+++ Connected to " + host_name)
            io.log(_log_id, 'f', 'i', "ssh_connect: Connected to " + host_name)
            return 0
        except paramiko.AuthenticationException:
            io.log(_log_id, 'c', 'i', "&&& Authentication failed when connecting to " + host_name)
            io.log(_log_id, 'c', 'i', "&&& Check username and password")
            io.log(_log_id, 'f', 'e', "ssh_connect: Authentication failed when connecting to " + host_name +
                                      " . Exit code -2")
            return -2
        except:
            io.log(_log_id, 'c', 'i', "--- Could not connect to " + host_name + " , waiting 3s for another try")
            io.log(_log_id, 'f', 'w', "ssh_connect: Could not connect to" + host_name + " , waiting 3s for another try")
            ii += 1
            time.sleep(3.0)

        # Connection was not successful within 10 tries (30s)
        if ii == 10:
            io.log(_log_id, 'c', 'i', "&&& Could not connect to %s." % host_name)
            io.log(_log_id, 'f', 'e', "ssh_connect: Could not connect to " + host_name + " . Exit code -1")
            return -1


def sftp_connect():
    """
            Opens sftp channel

            Parameters
            ----------

            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (All okay) 2 (Connection error)

    """
    global _curr_ssh
    global _curr_sftp
    global _log_id
    try:
        _curr_sftp = _curr_ssh.open_sftp()
        io.log(_log_id, 'f', 'i', "sftp_connect: Opened ftp channel")
        return 0
    except socket.error:
        io.log(_log_id, 'c', 'i', "&&& Could not connect to host")
        io.log(_log_id, 'f', 'e', "sftp_connect: Failed to open ftp channel. Exit code 2")
        return 2


def set_ftp_channel_timeout(channel_timeout=20.0):
    """
            Opens sftp channel

            Parameters
            ----------
            channel_timeout : int
                timeout for the sftp channel

            Returns
            -------

    """
    global _curr_sftp
    _ftp_channel = _curr_sftp.get_channel()
    _ftp_channel.settimeout(channel_timeout)
    io.log(_log_id, 'f', 'i', "set_ftp_channel_timeout: set ftp channel timeout to: " + str(channel_timeout))


def re_exists(remote_path, checkflag=False):
    """
           Wrapper for Paramiko mkdir call. Does *_wrapper_repeat* retrys if neccessary.

            Parameters
            ----------
            remote_path : str
                path to check on remote host
            checkflag : bool
                can be srt True to suppress logging and console output

           Returns
           -------
           exit_code : int
               remote exit code. From the called method: 0 (all okay)  2 (Connection error)
                                                         3 (No permissions/ path to new dir does not exist)

   """
    global _log_id
    global _wrapper_repeat
    global _wrapper_waittime
    # security retrys. Initial try is 1. In place to only retry 2 times (not wrapper_repeat times)
    sec_retry_counter = 1
    exit_code = 0
    for ii in range(_wrapper_repeat):
        exit_code = _re_exists(remote_path, checkflag=checkflag)
        if exit_code == 0 or exit_code == 2:
            break
        elif exit_code == -3 and sec_retry_counter < 2:
            # security retry
            sec_retry_counter += 1
            time.sleep(0.01)
        elif exit_code == -3 and sec_retry_counter >= 2:
            if not checkflag:
                io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission (file not found), wait for exit")
                io.log(_log_id, 'f', 'e', "re_exists: OSError: " + remote_path + " really "
                                                                                 "does not exist, exit code -3")
            break
        else:
            io.log(_log_id, 'f', 'w', "re_exists: OSError while calling _re_exists in try: " + str(ii+1) + "/" +
                                                                                           str(_wrapper_repeat))
            if ii == _wrapper_repeat - 1:
                io.log(_log_id, 'f', 'e', "re_exists: Maximum number of retries reached, pass error to caller")
                io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission (check permissions), wait for exit")
                break
            time.sleep(_wrapper_waittime)
    return exit_code



def _re_exists(remote_path, checkflag=False):
    """
            os.path.exists for remote files/dirs

            Parameters
            ----------
            remote_path : str
                path to check on remote host
            checkflag : bool
                can be srt True to suppress logging and console output

            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (All okay+ File not found) 2 (Connection error)
                                                    -3 (All okay and file not found) 3 (No permissions)

    """
    global _curr_sftp
    global _log_id
    try:
        _curr_sftp.stat(remote_path)
        return 0
    except socket.timeout:
        io.log(_log_id, 'f', 'e', "_re_exists: Connction lost (socket timeout), exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except paramiko.SSHException:
        io.log(_log_id, 'f', 'e', "_re_exists: Connection lost (SSHException), exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except OSError as err:
        if err.errno == errno.ENOENT:
            # -3 for file not found for checking purposes
            if not checkflag:
                io.log(_log_id, 'f', 'w', "_re_exists: OSError: " + remote_path + " does not exist, exit code -3")
            return -3
        if err.errno == errno.EACCES or err.errno == errno.EPERM:
            io.log(_log_id, 'f', 'w', "_re_exists: OSError: No r/w permissions for  " + remote_path + " , exit code 3")
            return 3
        else:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "_re_exists: OSError: Exit code 2")
            io.log(_log_id, 'f', 'e', "OSError errno: " + str(err.errno))
            return 2

def file_stat(remote_path, checkflag=False):
    """
       Wrapper for Paramiko sftp.stat. Does *_wrapper_repeat* retrys if neccessary. Does security retrys anyway as well.

       Parameters
            ----------
            remote_path : str
                path to check on remote host
            checkflag : bool
                can be set True to suppress logging and console output
       Returns
       -------
       exit_code : int
           remote exit code. From the called method: 0 (all okay)  2 (Connection error)
                                                     3 (No permissions/ path to new dir does not exist)

   """
    global _log_id
    global _wrapper_repeat
    global _wrapper_waittime
    # security retrys. Initial try is 1. In place to only retry 2 times (not wrapper_repeat times)
    sec_retry_counter = 1
    exit_code = 0
    mtime = -1
    for ii in range(_wrapper_repeat):
        exit_code, mtime = _file_stat(remote_path, checkflag=checkflag)
        if exit_code == 0 or exit_code == 2:
            break
        elif exit_code == -3 and sec_retry_counter < 2:
            # security retry
            sec_retry_counter += 1
            time.sleep(0.01)
        elif exit_code == -3 and sec_retry_counter >= 2:
            if not checkflag:
                io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission (file not found), wait for exit")
                io.log(_log_id, 'f', 'e', "file_stat: OSError: " + remote_path + " really "
                                                                                 "does not exist, exit code -3")
            break
        else:
            io.log(_log_id, 'f', 'w', "file_stat: OSError while calling _file_stat in try: " + str(ii+1) + "/" +
                                                                                           str(_wrapper_repeat))
            if ii == _wrapper_repeat - 1:
                io.log(_log_id, 'f', 'e', "file_stat: Maximum number of retries reached, pass error to caller")
                io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
                break
            time.sleep(_wrapper_waittime)
    return exit_code, mtime



def _file_stat(remote_path, checkflag=False):
    """
            Gives information on remote file st_mtime

            Parameters
            ----------
            remote_path : str
                path to check on remote host
            checkflag : bool
                can be set True to suppress logging and console output

            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (All okay+ File not found) 2 (Connection error)
                                                    -3 (All okay and file not found) 3 (No permissions)
            stats.st_mtime : int
                last time the file/dir on the remote host changed

    """
    global _curr_sftp
    global _log_id
    try:
        stats = _curr_sftp.stat(remote_path)
        return 0, stats.st_mtime
    except socket.timeout:
        io.log(_log_id, 'f', 'e', "_file_stat: Connection lost (socket timeout), exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2, 0
    except paramiko.SSHException:
        io.log(_log_id, 'f', 'e', "_file_stat: Connection lost (SSHException), exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2, 0
    except OSError as err:
        if err.errno == errno.ENOENT:
            # -3 for file not found for checking purposes
            if not checkflag:
                io.log(_log_id, 'f', 'w', "_file_stat: OSError: " + remote_path + " does not exist, exit code -3")
            return -3, 0
        if err.errno == errno.EACCES or err.errno == errno.EPERM:
            io.log(_log_id, 'f', 'w', "_file_stat: OSError: No r/w permissions for " + remote_path + " , exit code 3")
            return 3, 0
        else:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "_file_stat: OSError: Exit code 2")
            io.log(_log_id, 'f', 'e', "OSError, errno: " + str(err.errno))
            return 2, 0


def file_remove(remote_path, backcheck=True):
    """
            Interface for _file_remove which checks afterwards via re_exists if the file was really deleted
            Do repeats if necessary

            Parameters
            ----------
            remote_path : str
                path to file to remove on remote host
            backcheck : bool
                backchecks file existance after trying to delete

            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (all okay) 4 (file is still there after trying to delete it)
                                  From _file_remove:  2 (Connection error)  3 (No permissions)

    """
    # try to delete file
    global _log_id
    global _wrapper_repeat
    global _wrapper_waittime
    exit_code = _file_remove(remote_path)
    if backcheck:
        for ii in range(_wrapper_repeat):
            if exit_code == 0:
                # check file existance
                exists_code = re_exists(remote_path, checkflag=True)
                if exists_code == -3:
                    # file does not exist anymore
                    exit_code = 0
                    break
                elif exists_code == 0:
                    # file still exists, try removal again
                    io.log(_log_id, 'f', 'w', "file_remove: File still exists while calling _file_remove in try: " +
                          str(ii + 1) + "/" + str(_wrapper_repeat))
                    exit_code = _file_remove(remote_path)
                if ii == _wrapper_repeat-1:
                    # file still exists after multiple checks
                    io.log(_log_id, 'f', 'e', "file_remove: Maximum number of retries reached, pass error to caller")
                    io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
                    exit_code = 4
                    break
            else:
                # just pass on exit code
                break
            time.sleep(_wrapper_waittime)
    return exit_code


def _file_remove(remote_path):
    """
            Delets file on remote host

            Parameters
            ----------
            remote_path : str
                path to file to remove on remote host

            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (all okay/file does not exist)  2 (Connection error)
                                                    3 (No permissions)

    """

    global _curr_sftp
    global _log_id
    try:
        _curr_sftp.remove(remote_path)
        return 0
    except socket.timeout:
        io.log(_log_id, 'f', 'e', "file_remove: Connection lost (socket timeout), exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except paramiko.SSHException:
        io.log(_log_id, 'f', 'e', "file_remove:  Connection lost (SSHException), exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except OSError as err:
        if err.errno == errno.ENOENT:
            io.log(_log_id, 'f', 'w', "file_remove: OSError: " + remote_path + " does not exist, exit code 0")
            return 0
        if err.errno == errno.EACCES or err.errno == errno.EPERM:
            io.log(_log_id, 'f', 'e', "file_remove: OSError: No r/w permissions for " + remote_path + " , exit code 3")
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission (check server permissions), wait for exit")
            return 3
        if err.errno == errno.EISDIR:
            io.log(_log_id, 'f', 'e', "file_stat: OSError: " + remote_path + " is not a file , exit code 4")
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            return 3
        else:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "file_remove: OSError: Exit code 2")
            io.log(_log_id, 'f', 'e', "OSError errno: " + str(err.errno))
            return 2


def file_rename(old_remote_path, new_remote_path):
    """
           Wrapper for Paramiko sftp rename call. Does *_wrapper_repeat* retrys if neccessary.

           Parameters
           ----------
           remote_path : str
               path to remote dir to create

           Returns
           -------
           exit_code : int
               remote exit code. From the called method: 0 (all okay)  2 (Connection error)
                                                         3 (No permissions/ path to new dir does not exist)

    """
    global _log_id
    global _wrapper_repeat
    global _wrapper_waittime
    exit_code = 0
    for ii in range(_wrapper_repeat):
        exit_code = _file_rename(old_remote_path, new_remote_path)
        if exit_code == 0 or exit_code == 2:
            break
        io.log(_log_id, 'f', 'w', "re_rename: OSError while calling _re_rename in try: " + str(ii + 1) + "/" +
               str(_wrapper_repeat))
        exists_code = re_exists(old_remote_path, checkflag=True)
        if exists_code == 0:
            io.log(_log_id, 'f', 'e', "re_rename: But file: " + str(old_remote_path) + " seems to exist and"
                                                                                   " could be renamed")
        elif exists_code == -3:
            io.log(_log_id, 'f', 'i', "re_rename: And file: " + str(old_remote_path) + " does not seem to exist.")
        if ii == _wrapper_repeat - 1:
            io.log(_log_id, 'f', 'e', "re_rename: Maximum number of retries reached, pass error to caller")
            break
        time.sleep(_wrapper_waittime)
    return exit_code


def _file_rename(old_remote_path, new_remote_path):
    """
            Rename a file in *old_remote_path* to *new_remote_path*.

            Parameters
            ----------
            remote_dir : str
                path to remote dir to create

            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (all okay)  2 (Connection error)
                                                    3 (No permissions/ path to new dir does not exist)

    """
    global _curr_sftp
    global _log_id
    try:
        _curr_sftp.rename(old_remote_path, new_remote_path)
        return 0
    except socket.timeout:
        io.log(_log_id, 'f', 'e', "_re_rename: Connection lost (socket timeout), exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except paramiko.SSHException:
        io.log(_log_id, 'f', 'e', "_re_rename: Connection lost (SSHException) exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except OSError as err:
        if err.errno == errno.ENOENT:
            io.log(_log_id, 'f', 'w', "_re_rename: Path to " + old_remote_path + " does not exist.")
            return 3
        if err.errno == errno.EACCES or err.errno == errno.EPERM:
            io.log(_log_id, 'f', 'w', "_re_rename: OSError: No r/w permissions to create " + new_remote_path +
                   " , exit code 3")
            return 3
        if err.errno == errno.EEXIST:
            io.log(_log_id, 'f', 'w', "_re_rename: OSError: " + new_remote_path + " already exists, exit code 3")
            return 3
        else:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "_re_rename: OSError: Exit code 2")
            io.log(_log_id, 'f', 'e', "OSError errno: " + str(err.errno))
            return 2



def re_mkdir(remote_dir):
    """
           Wrapper for Paramiko mkdir call. Does *_wrapper_repeat* retrys if neccessary.

           Parameters
           ----------
           remote_dir : str
               path to remote dir to create

           Returns
           -------
           exit_code : int
               remote exit code. From the called method: 0 (all okay)  2 (Connection error)
                                                         3 (No permissions/ path to new dir does not exist)

       """
    global _log_id
    global _wrapper_repeat
    global _wrapper_waittime
    exit_code = 0
    for ii in range(_wrapper_repeat):
        exit_code = _re_mkdir(remote_dir)
        if exit_code == 0 or exit_code == 2:
            break
        io.log(_log_id, 'f', 'w', "re_mkdir: OSError while calling _re_mkdir in try: " + str(ii+1) + "/" +
                                                                                       str(_wrapper_repeat))
        if ii == _wrapper_repeat - 1:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "re_mkdir: Maximum number of retries reached, pass error to caller")
            break
        time.sleep(_wrapper_waittime)
    return exit_code


def _re_mkdir(remote_dir):
    """
            os.mkdir on remote host. Not recursive!

            Parameters
            ----------
            remote_dir : str
                path to remote dir to create

            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (all okay)  2 (Connection error)
                                                    3 (No permissions/ path to new dir does not exist)

    """
    global _curr_sftp
    global _log_id
    try:
        _curr_sftp.mkdir(remote_dir, mode=0o775)
        return 0
    except socket.timeout:
        io.log(_log_id, 'f', 'e', "_re_mkdir: Connection lost (socket timeout), exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except paramiko.SSHException:
        io.log(_log_id, 'f', 'e', "_re_mkdir: Connection lost (SSHException) exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except OSError as err:
        if err.errno == errno.ENOENT:
            io.log(_log_id, 'f', 'w', "_re_mkdir: OSError: Path to " + remote_dir + " does not exist, exit code 3")
            return 3
        if err.errno == errno.EACCES or err.errno == errno.EPERM:
            io.log(_log_id, 'f', 'w', "_re_mkdir: OSError: No r/w permissions to create " + remote_dir + " , exit code 3")
            return 3
        if err.errno == errno.EEXIST:
            io.log(_log_id, 'f', 'w', "_re_mkdir: OSError: " + remote_dir + " already exists, exit code 3")
            return 3
        else:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "_re_mkdir: OSError: Exit code 2")
            io.log(_log_id, 'f', 'e', "OSError errno: " + str(err.errno))
            return 2


def file_put(local_path, remote_path):
    """
           Wrapper for Paramiko put call. Does *_wrapper_repeat* retrys if neccessary.

           Parameters
            ----------
            local_path : str
                path to local file to transfer
            remote_path : str
                path to remote file to be transferred to

            Returns
            -------
            exit_code : int
                remote exit code. From the called method: 0 (all okay)  2 (Connection error)
                                                          3 (No permissions/ path to new dir does not exist)

    """
    # note, that the retries here may lead to screwy results (for TM 1), if the file was sent properly
    # but paramiko raises an error anyway. If this tends to happen it is documented in the log.
    # If the error persists one may need to add a way to identify TM 1 transmissions, and return 0 if the file was
    # found to exists by re_exists
    global _log_id
    global _wrapper_repeat
    global _wrapper_waittime
    exit_code = 0
    for ii in range(_wrapper_repeat):
        exit_code =_file_put(local_path, remote_path)
        if exit_code == 0 or exit_code == 2:
            break
        io.log(_log_id, 'f', 'w', "file_put: OSError while calling _file_put in try: " + str(ii+1) + "/" +
                                                                                         str(_wrapper_repeat))
        exists_code = re_exists(remote_path, checkflag=True)
        if exists_code == 0:
            io.log(_log_id, 'f', 'e', "file_put: But file: " + str(remote_path) + " exists. If Transmission mode is 1,"
                                                                                  " this is a possible source of errors")
        elif exists_code == -3:
            io.log(_log_id, 'f', 'i', "file_put: And file: " + str(remote_path) + " does not exist (this is okay, as"
                                                                                  " transmission raised an error).")
        if ii == _wrapper_repeat - 1:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "file_put: Maximum number of retries reached, pass error to caller")
            break
        time.sleep(_wrapper_waittime)
    return exit_code


def _file_put(local_path, remote_path):
    """
            Puts file from local path to remote path

            Parameters
            ----------
            local_path : str
                path to local file to transfer
            remote_path : str
                path to remote file to be transferred to

            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (all okay)  2 (Connection error)
                                                    3 (No permissions/ path to new dir does not exist)

    """
    global _curr_sftp
    global _log_id
    try:
        _curr_sftp.put(local_path, remote_path)
        return 0
    except socket.timeout:
        io.log(_log_id, 'f', 'e', "_file_put: Connection lost (socket timeout), exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except paramiko.SSHException:
        io.log(_log_id, 'f', 'e', "_file_put: Connection lost (SSHException) exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except EOFError:
        io.log(_log_id, 'f', 'e', "_file_put: End of file Error. Possibly related to connection problems "
                                  "during transfer, passing on as exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except OSError as err:
        if err.errno == errno.ENOENT:
            # #try again ONE more time
            # time.sleep(0.01)
            # try:
            #     _curr_sftp.put(local_path, remote_path)
            #     return 0
            # except:
            io.log(_log_id, 'f', 'w', "_file_put: OSError: Local file: " + local_path + " or the folder to which "
                                      "the file: " + remote_path + " is to be transferred does not exist, exit code 3")
            return 3
        if err.errno == errno.EACCES or err.errno == errno.EPERM:
            io.log(_log_id, 'f', 'w', "_file_put: OSError: No r/w permissions, exit code 3")
            return 3
        if err.errno == errno.EISDIR:
            io.log(_log_id, 'f', 'w', "_file_put: OSError: " + local_path + " or  " + remote_path +
                                      " is not a file , exit code 3")
            return 3
        else:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "_file_put: OSError: Exit code 2")
            io.log(_log_id, 'f', 'e', "OSError errno: " + str(err.errno))
            return 2

def file_get(remote_path, local_path):
    """
           Wrapper for Paramiko get call. Does *_wrapper_repeat* retrys if neccessary.

           Parameters
            ----------
            remote_path : str
                path to remote file to transfer
            local_path : str
                path to local file to be transferrred to


            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (all okay)  2 (Connection error)
                                                    3 (No permissions/ path to new dir does not exist)

    """
    global _log_id
    global _wrapper_repeat
    global _wrapper_waittime
    exit_code = 0
    for ii in range(_wrapper_repeat):
        exit_code =_file_get(remote_path, local_path)
        if exit_code == 0 or exit_code == 2:
            break
        io.log(_log_id, 'f', 'w', "file_get: OSError while calling _file_get in try: " + str(ii+1) + "/" +
                                                                                         str(_wrapper_repeat))
        if ii == _wrapper_repeat - 1:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "file_get: Maximum number of retries reached, pass error to caller")
            break
        time.sleep(_wrapper_waittime)
    return exit_code


def _file_get(remote_path, local_path):
    """
            Puts file from remote path to local path

            Parameters
            ----------
            remote_path : str
                path to remote file to transfer
            local_path : str
                path to local file to be transferrred to


            Returns
            -------
            exit_code : int
                remote exit code. From this method: 0 (all okay)  2 (Connection error)
                                                    3 (No permissions/ path to new dir does not exist)

    """
    global _curr_sftp
    global _log_id
    try:
        _curr_sftp.get(remote_path, local_path)
        return 0
    except socket.timeout:
        io.log(_log_id, 'f', 'e', "_file_get: Connection lost (socket timeout) exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except paramiko.SSHException:
        io.log(_log_id, 'f', 'e', "_file_get: Connection lost (SSHException) passing on as exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except EOFError:
        io.log(_log_id, 'f', 'e', "_file_get: End of file Error. Possibly related to connection problems "
                                  "during transfer, passing on as exit code 2")
        io.log(_log_id, 'c', 'e', "&&& Connection lost, wait for exit")
        return 2
    except OSError as err:
        if err.errno == errno.ENOENT:
            io.log(_log_id, 'f', 'w', "_file_get: OSError: Remote file " + remote_path + " or folder to local file: "
                   + local_path + " does not exist, exit code 3")
            return 3
        if err.errno == errno.EACCES or err.errno == errno.EPERM:
            io.log(_log_id, 'c', 'w', "&&& Fatal error during transmission (check server permissions), wait for exit")
            return 3
        if err.errno == errno.EISDIR:
            io.log(_log_id, 'f', 'w', "_file_get: OSError: " + local_path + " or  " + remote_path +
                                      " is not a file , exit code 3")
            return 3
        else:
            io.log(_log_id, 'c', 'e', "&&& Fatal error during transmission, wait for exit")
            io.log(_log_id, 'f', 'e', "_file_get: OSError: Exit code 2")
            io.log(_log_id, 'f', 'e', "OSError errno: " + str(err.errno))
            return 2


def close_sftp_connection():
    """
            Closes ftp channel

            Parameters
            ----------


            Returns
            -------

    """
    global _log_id
    global _curr_sftp
    _curr_sftp.close()
    _curr_sftp = None
    io.log(_log_id, 'f', 'i', "close_sftp_connection: SFTP connection closed")


def close_ssh_connection():
    """
            Closes ssh channel

            Parameters
            ----------


            Returns
            -------

    """
    global _log_id
    global _curr_ssh
    _curr_ssh.close()
    _curr_ssh = None
    io.log(_log_id, 'c', 'i', "+++ Server connection closed")
    io.log(_log_id, 'f', 'i', "close_ssh_connection: SSH connection closed")
