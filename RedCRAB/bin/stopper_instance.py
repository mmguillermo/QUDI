"""
stopper_instance.py - User abort handling module
@author: Fabian Höb (fabi.ho@web.de)
Current version number: 1.0.4
Current version dated: 11.05.2017
First version dated: 01.04.2017
"""
# encoding: utf-8
import os
import time
import logging_module as io

### Contains the stopper class, that handles user aborts

class Stopper:

    def __init__(self, stopper_sentinel, stopper_waittime):
        """
                CONSTRUCTOR of class Stopper: Sets-up variables required for abort checks

                Parameters
                ----------
                stopper_sentinel : threading.Event
                    Event that is set if the user stopped the program
                server_waittime : int
                    Total time to wait between successive checks for user abort
        """
        # log id for module identification
        self.log_id = 4
        self.stopper_sentinel = stopper_sentinel
        if stopper_waittime < 1 or stopper_waittime > 30:
            stopper_waittime = 3
        self.waittime = stopper_waittime


    def stop_check(self):
        """
                Central stopping check loop that calls _checkfiles and _checkabort. Sets Event if user aborted job
                and stops the loop.

                Parameters
                ----------

                Returns
                -------

        """
        while True:
            if not self.stopper_sentinel.isSet():
                f = self._checkfiles()
                if self._checkabort(f):
                    self.stopper_sentinel.set()
                    io.log(self.log_id, 'f', 'd', "stop_check: User stop of optimization...")
                    break
            time.sleep(self.waittime)

    def _checkfiles(self):
        """
                Checks the Config folder for all files

                Parameters
                ----------

                Returns
                -------

        """
        f = []
        for (dirpath, dirnames, filenames) in os.walk(os.path.join(os.getcwd(), "../", "Config")):
            f.extend(filenames)
        return f

    def _checkabort(self, files):
        """
                Checks if there are files with exit or stop in their names

                Parameters
                ----------
                files : list
                    list of filenames found in the Config folder

                Returns
                -------
                bool
                    is True if one of the files in the input files list contains exit/stop, False if not

        """
        for element in files:
            if "stop" in str(element) or "exit" in str(element):
                return True
        return False
