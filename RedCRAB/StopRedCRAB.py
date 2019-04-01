# encoding: utf-8
import os

# simple program, that just puts a stop.txt file in the Config folder, which triggers user abort for RedCRAB
abortpath = os.path.join("Config", "stop.txt")
try:
    with open(abortpath, "w") as abortfile:
        pass
except OSError as err:
    print("OSError, error number " + str(err.errno) + ". Could not stop RedCRAB.")
except:
    print("Unknown exception while stopping RedCRAB. Could not stop RedCRAB.")
else:
    print("Stopping RedCRAB. Wait until the main program reacts and handles exit.")