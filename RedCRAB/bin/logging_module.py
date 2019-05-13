"""
logging__module.py - Logging module for the RedCRAb client
@author: Fabian Höb (fabi.ho@web.de)
Current version number: 1.0.4
Current version dated: 11.05.2017
First version dated: 01.04.2017
"""
# encoding: utf-8
import logging
import logging.config
import os

### Contains funations for initialization of logging from a logging.conf file and an interface for logging (log)

# logger objects (one for console output, one for file output. Two different ones to able to select them independently)
_logf = None
_logc = None


def init_logging():
    """
            Initializes logging by acuiring loggers for file and console handling from the logging.conf file

            Parameters
            ----------

            Returns
            -------

    """
    global _logf
    global _logc
    logging.config.fileConfig('./logconfig/logging.conf', disable_existing_loggers=True)
    _logf = logging.getLogger('filelogger')
    _logc = logging.getLogger('consolelogger')


def create_log(path, logfile):
    """
            Writes the path to which logging should be done in the logging.conf file and creates log
            if there is no such file yet

            Parameters
            ----------
            path : str
                path to the directory in which the logfile should be saved
            logfile : str
                name of the logfile to which logging should be done

            Returns
            -------

    """
    # exit codes: 0 no problem, 1 some error occured
    logpath = path + "/" + logfile
    if not os.path.exists(path):
        os.makedirs(path)
    exit_code = 0
    if exit_code == 0:
        linefound = False
        try:
            with open(os.path.join(os.getcwd(),"logconfig","logging.conf"), 'r') as f:
                lines = f.readlines()
                fhandler = False
            for ii in range(len(lines)):
                lines[ii] = str(lines[ii]).strip()
                if 'handler_fileHandler' in lines[ii]:
                    fhandler = True
                if fhandler and 'args=' in lines[ii]:
                    lines[ii] = "args=('" + logpath+ "','a')"
                    linefound = True
                if fhandler and 'args =' in lines[ii]:
                    lines[ii] = "args = ('" + logpath + "','a')"
                    linefound = True
        except OSError:
            exit_code = 1
            return exit_code
        if not linefound:
            exit_code = 1
        if exit_code == 0:
            try:
                with open(os.path.join(os.getcwd(), "logconfig", "logging.conf"), "w") as loggingfile:
                    for element in lines:
                        loggingfile.write(str(element) + "\n")
            except OSError:
                exit_code = 1
                return exit_code
        return exit_code
    return exit_code



def log(logid, spec, level, logentry):
    """
            Central logging interface. Calls _choose_logger and _logging_output functions

            Parameters
            ----------
            logid : int
                Log id of the module that called the log interface
                    1 := redcrab.py
                    2 := opti_instance.py
                    3 := remote_module.py
                    4 := stopper_instance
            spec : str
                Specifies if the logentry should be logged to file ('f') or to console ('c')
            level : str
                shorthand for the logging level 'd' is debug, 'w' is warning, 'e' is error, 'i' is info
            logentry: str
                is the message to be logged as string

            Returns
            -------

    """
    logger, pretext = _choose_logger(str(logid)+str(spec))
    _logging_output(logger, level, pretext + str(logentry))


def _choose_logger(logspec):
    """
            Chooses logger depending on the parameters given to the logging interface function log

            Parameters
            ----------
            logspec : str
                Log id of the module that called the log interface

            Returns
            -------
            logger : logging.Logger
                logger object that handles logging (file or console logger)
            pretext :  str
                Text that is added before the message, that contains the module prefix

    """

    global _logf
    global _logc

    if '1f' in logspec:
        return _logf, "redcrab - "
    elif '1c' in logspec:
        return _logc, ""
    elif '2f' in logspec:
        return _logf, "opti_instance - "
    elif '2c' in logspec:
        return _logc, ""
    elif '3f' in logspec:
        return _logf, "remote_module - "
    elif '3c' in logspec:
        return _logc, ""
    elif '4f' in logspec:
        return _logf, "stopper_instance - "
    elif '4c' in logspec:
        return _logc, ""


def _logging_output(logger, levelspec, logentry):
    """
            Calls logger output with full message

            Parameters
            ----------
            logger : logging.Logger
                logger object that handles logging (file or console logger)
            levelspec : str
                One character string that specifies how the output sould be logged (error, debug, info or warning)
            logentry : str
                full log message

            Returns
            -------

    """
    if 'd' in levelspec:
        logger.debug(logentry)
    elif 'i' in levelspec:
        logger.info(logentry)
    elif 'w' in levelspec:
        logger.warning(logentry)
    elif 'e' in levelspec:
        logger.error(logentry)
