import subprocess
import sys
import os

# short script to be able to test if the command in the Config/Client_config/config.txt will work
# very straightforward script
configpath = os.path.join("Config", "Client_config", "config.txt")
command_to_execute = ""
command_found = False
if os.path.exists(configpath):
    print("Reading config file")
    # read config.txt from client config folder
    with open(configpath, "r") as configfile:
        configlines = configfile.readlines()
    for element in configlines:
        if "###" in element:
            continue
        dummy = [jj for jj in str(configlines).strip().split(" := ")]
        if "Command" in str(dummy[0]):
            command_found = True
            command_to_execute = str(dummy[1])
    if command_found:
        print("Command read successfully")
        # now try the command
        try:
            subprocess.call(command_to_execute, shell=True)
        except subprocess.CalledProcessError:
            print("CalledProcessError while executing the command" + command_to_execute)
            sys.exit(1)
        except OSError as err:
            print("OSError, error number: " + str(err.errno) + " while executing the command " + command_to_execute)
            sys.exit(1)
        except RuntimeError as err:
            print("RuntimeError while executing the command " +command_to_execute)
            sys.exit(1)
        except:
            print("Unknown exception while executing the command " + command_to_execute)
            sys.exit(1)
        else:
            print("Command executed successfully! Ready for RedCRAB use.")
    else:
        print("No 'Command' parameter in the current config file")
        sys.exit(0)
else:
    print("There is currently no config file in the config file path : Config/Client_config")
    sys.exit(0)